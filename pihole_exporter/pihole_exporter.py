#!/usr/bin/env python3

import json
import argparse
import urllib.request
import threading
import socket

from io import StringIO
from prometheus_client import Gauge, generate_latest
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer

name = 'pihole_exporter'
__VERSION__ = '0.4.5'


class metric:
    def __init__(self, name, value):
        self.name = name
        self.value = value
        self.metric = Gauge('pihole_%s' % name.lower(), name.replace('_', ' '))
        self.metric.set(value)

    def update_value(self, value):
        self.value = value
        self.metric.set(value)


class metric_label:
    def __init__(self, name, value):
        self.name = name
        label = [*value.keys()][0]
        self.values = dict()
        self.values[label] = value[label]
        self.label_values = list()
        self.label_values.append(label)
        self.metric = Gauge('pihole_%s' % name.lower(), name.replace('_', ' '),
                            [self.get_label(name)])
        self.metric.labels(label).set(value[label])

    @classmethod
    def get_label(self, name):
        if name in ['top_queries', 'top_ads']:
            return 'domain'
        elif name == 'top_sources':
            return 'client'
        elif name == 'forward_destinations':
            return 'resolver'
        elif name == 'query_type':
            return 'type'

    def update_value(self, value):
        for label in value:
            self.values[label] = value[label]
            self.metric.labels(label).set(value[label])
            if label not in self.label_values:
                self.label_values.append(label)
        for label in self.label_values:
            if not label in value:
                self.metric.labels(label).set(0)


class metric_labels:
    def __init__(self, name, labels, values):
        self.name = name
        self.values = values
        self.labels = labels
        self.metric = Gauge('pihole_%s' % name.lower(), name.replace('_', ' '),
                            labels)
        self.update_value(values)

    def zero_missing_value(self, values, key):
        if isinstance(values, dict):
            for label in values:
                values[label] = self.zero_missing_value(values[label], label)
        else:
            values = 0
        return values

    def update_old_values(self, old_values, values):

        for label in old_values:
            if not label in values:
                old_values[label] = self.zero_missing_value(old_values[label], label)
            else:
                if isinstance(old_values[label], dict):
                    old_values[label] = self.update_old_values(
                        old_values[label], values[label])
        return old_values

    def add_new_values(self, old_values, values):

        for label in values:
            if not isinstance(values[label], dict):
                old_values[label] = values[label]
            else:
                if label in old_values:
                    old_values[label] = self.add_new_values(
                        old_values[label], values[label])
                else:
                    old_values[label] = values[label]

        return old_values

    def update_metrics(self, values, labels=[]):

        for label in values:
            labels_tmp = list()
            for i in labels:
                labels_tmp.append(i)
            labels_tmp.append(label)

            if not isinstance(values[label], dict):

                self.metric.labels(*labels_tmp).set(values[label])
                labels_tmp.pop()
            else:
                labels.append(label)
                self.update_metrics(values[label], labels)
                labels.pop()

    def update_value(self, values):
        values_tmp = self.values
        values_tmp = self.add_new_values(values_tmp, values)
        values_tmp = self.update_old_values(values_tmp, values)
        self.update_metrics(values_tmp)


class pihole_exporter:
    class _SilentHandler(WSGIRequestHandler):
        """WSGI handler that does not log requests."""

        def log_message(self, format, *args):
            """Log nothing."""

    def __init__(self, url, auth, extended=False):
        self.url = url
        self.auth = auth
        self.api_url = 'http://%s/admin/api.php' % self.url
        self.metrics = dict()
        self.httpd = None
        self.extended = extended

        self.summary_raw_url = self.api_url + '?summaryRaw'
        self.top_item_url = self.api_url + '?topItems=100'
        self.top_sources_url = self.api_url + '?getQuerySources=100'
        self.forward_destinations_url = self.api_url + '?getForwardDestinations'
        self.query_types_url = self.api_url + '?getQueryTypes'
        self.get_all_queries_url = self.api_url + '?getAllQueries'

    def get_json(self, url):
        if self.auth:
            url += "&auth=%s" % self.auth
        response = urllib.request.urlopen(url)
        data = response.read()
        text = data.decode('utf-8')
        io = StringIO(text)
        json_text = json.load(io)
        return json_text

    def add_update_metric(self, name, value):
        if not name in self.metrics:
            self.metrics[name] = metric(name, value)
        self.metrics[name].update_value(value)

    def add_update_metric_label(self, name, value):
        if not name in self.metrics:
            self.metrics[name] = metric_label(name, value)
        self.metrics[name].update_value(value)

    def add_update_metric_labels(self, name, labels, value):
        if not name in self.metrics:
            self.metrics[name] = metric_labels(name, labels, value)
        self.metrics[name].update_value(value)

    def get_summary(self):
        summary_raw = self.get_json(self.summary_raw_url)

        for i in summary_raw:
            if i == "status":
                if summary_raw[i] == 'enabled':
                    self.add_update_metric(i, 1)
                else:
                    self.add_update_metric(i, 1)
            elif i == "gravity_last_updated":
                self.add_update_metric(i, summary_raw[i]['absolute'])
            else:
                self.add_update_metric(i, summary_raw[i])

    def get_exteneded_metrics(self):
        aq = self.get_json(self.get_all_queries_url)
        if aq:
            client_data = dict()
            for i in aq['data']:
                hostname = i[3]
                domain = i[2]
                answer_type = i[4]
                if not hostname in client_data:
                    client_data[hostname] = dict()
                if not domain in client_data[hostname]:
                    client_data[hostname][domain] = dict()
                if not answer_type in client_data[hostname][domain]:
                    client_data[hostname][domain][answer_type] = 1
                else:
                    client_data[hostname][domain][answer_type] += 1
            self.add_update_metric_labels(
                'client_queries', ['hostname', 'domain', 'answer_type'],
                client_data)

    def generate_latest(self):
        self.get_summary()

        top_items = self.get_json(self.top_item_url)
        if top_items:
            for item in top_items:
                self.add_update_metric_label(item, top_items[item])
        top_sources = self.get_json(self.top_sources_url)
        if top_sources:
            self.add_update_metric_label('top_sources',
                                         top_sources['top_sources'])

        fw_dest = self.get_json(self.forward_destinations_url)
        if fw_dest:
            self.add_update_metric_label('forward_destinations',
                                         fw_dest['forward_destinations'])

        qt = self.get_json(self.query_types_url)
        if qt:
            self.add_update_metric_label('query_type', qt['querytypes'])

        if self.extended:
            self.get_exteneded_metrics()

        return generate_latest()

    def make_prometheus_app(self):
        def prometheus_app(environ, start_response):
            output = self.generate_latest()
            status = str('200 OK')
            headers = [(str('Content-type'), str('text/plain'))]
            start_response(status, headers)
            return [output]

        return prometheus_app

    def make_server(self, interface, port):
        server_class = WSGIServer

        if ':' in interface:
            if getattr(server_class, 'address_family') == socket.AF_INET:
                server_class.address_family = socket.AF_INET6

        print("* Listening on %s:%s" % (interface, port))
        self.httpd = make_server(
            interface,
            port,
            self.make_prometheus_app(),
            server_class=server_class,
            handler_class=self._SilentHandler)
        t = threading.Thread(target=self.httpd.serve_forever)
        t.start()


def get_authentication_token():
    token = None
    filename = '/etc/pihole/setupVars.conf'
    try:
        with open(filename) as f:
            lines = f.readlines()
            for line in lines:
                if line.startswith('WEBPASSWORD'):
                    token = line.split('=')[1]
                    return token
            return None
    except (FileNotFoundError):
        print("Unable to find: %s" % filename)


def main():
    parser = argparse.ArgumentParser(description='pihole_exporter')
    parser.add_argument(
        '-o', '--pihole', help='pihole adress', default='pi.hole')
    parser.add_argument(
        '-p',
        '--port',
        type=int,
        help='port pihole_exporter is listening on',
        default=9311)
    parser.add_argument(
        '-i',
        '--interface',
        help='interface pihole_exporter will listen on',
        default='0.0.0.0')
    parser.add_argument(
        '-a', '--auth', help='Pihole password hash', default=None)
    parser.add_argument(
        '-e',
        '--extended-metrics',
        help="Extended pihole metrics",
        action='store_true',
        default=False)
    args = parser.parse_args()

    auth_token = args.auth
    if auth_token == None:
        auth_token = get_authentication_token()

    exporter = pihole_exporter(args.pihole, auth_token, args.extended_metrics)
    exporter.make_server(args.interface, args.port)


if __name__ == '__main__':
    main()
