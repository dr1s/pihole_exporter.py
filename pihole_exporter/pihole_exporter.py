#!/usr/bin/env python3

import json
import argparse
import urllib.request
import threading
import socket

from io import StringIO
from prometheus_client import Gauge, generate_latest
from wsgiref.simple_server import make_server, WSGIRequestHandler, WSGIServer

class pihole_exporter:

    class _SilentHandler(WSGIRequestHandler):
        """WSGI handler that does not log requests."""

        def log_message(self, format, *args):
            """Log nothing."""

    def __init__(self, url, auth):
        self.url = url
        self.auth = auth
        self.api_url = 'http://%s/admin/api.php' % self.url
        self.metrics = dict()
        self.httpd = None
        self.metrics_data = dict()

        self.summary_raw_url = self.api_url + '?summaryRaw'
        self.top_item_url = self.api_url + '?topItems'
        self.top_sources_url = self.api_url + '?getQuerySources'
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

    def get_summary(self):

        summary_raw = self.get_json(self.summary_raw_url)
        metrics_data = dict()

        for i in summary_raw:
            if i == "status":
                if summary_raw[i] == 'enabled':
                    metrics_data[i] = 1
                else:
                    metrics_data[i] = 0
            elif i == "gravity_last_updated":
                metrics_data[i] = summary_raw[i]['absolute']
            else:
                metrics_data[i] = summary_raw[i]
        return metrics_data

    def get_label(self, name):
        if name in ['top_queries', 'top_ads']:
            return 'domain'
        elif name in ['top_sources', 'all_queries']:
            return 'client'
        elif name == 'forward_destinations':
            return 'resolver'
        elif name == 'query_type':
            return 'type'

    def get_all_queries_data(self):
        aq = self.get_json(self.get_all_queries_url)
        if aq:
            client_metrics = dict()
            for i in aq['data']:
                hostname = i[3]
                domain = i[2]
                if not hostname in client_metrics:
                    client_metrics[hostname] = dict()
                if not domain in client_metrics[hostname]:
                    client_metrics[hostname][domain] = 1
                else:
                    client_metrics[hostname][domain] += 1
        return client_metrics

    def get_metrics(self):
        metrics_data = self.get_summary()

        top_items = self.get_json(self.top_item_url)
        if top_items:
            top_queries = top_items['top_queries']
            metrics_data['top_queries'] = top_queries
            top_ads = top_items['top_ads']
            metrics_data['top_ads'] = top_ads

        top_sources = self.get_json(self.top_sources_url)
        if top_sources:
            metrics_data['top_sources'] = top_sources['top_sources']

        fw_dest = self.get_json(self.forward_destinations_url)
        if fw_dest:
            fwd = fw_dest['forward_destinations']
            metrics_data['forward_destinations'] = fwd

        qt = self.get_json(self.query_types_url)
        if qt:
            metrics_data['query_type'] = qt['querytypes']


        metrics_data['all_queries'] = self.get_all_queries_data()
        return metrics_data


    def update_value(self, data_dict, value):
        if value in data_dict:
            return data_dict[value]
        return 0


    def update_existing_metrics(self, data_dict, overall_data_dict=None):

        if overall_data_dict is None:
            overall_data_dict = self.metrics_data

        for key in overall_data_dict:
            if not isinstance(overall_data_dict[key], dict):
                overall_data_dict[key] = self.update_value(overall_data_dict, key)
            else:
                overall_data_dict[key] = self.update_existing_metrics(
                                                data_dict[key],
                                                overall_data_dict[key])
        return overall_data_dict


    def update_new_metrics(self, data_dict, overall_data_dict=None):

        if overall_data_dict is None:
            overall_data_dict = self.metrics_data

        for key in data_dict:
            if not key in overall_data_dict:
                overall_data_dict[key] = data_dict[key]
            else:
                if isinstance(data_dict[key], dict):
                    overall_data_dict[key] = self.update_new_metrics(
                                                    data_dict[key],
                                                    overall_data_dict[key])
        return overall_data_dict

    def update_metrics_data(self, metrics_data):

        if len(self.metrics_data) == 0:
            self.metrics_data = metrics_data
        else:
            self.metrics_data = self.update_existing_metrics(metrics_data)
            self.metrics_data = self.update_new_metrics(metrics_data)

    def generate_latest(self):
        data = self.get_metrics()
        self.update_metrics_data(data)

        for source in self.metrics_data:
            if not isinstance(self.metrics_data[source], dict):
                if not source in self.metrics:
                    self.metrics[source] = Gauge(
                        'pihole_%s' % source.lower(),
                        source.replace('_',' '))
                self.metrics[source].set(
                    self.metrics_data[source])
            else:
                for i in self.metrics_data[source]:
                    if not source in self.metrics:
                        label = self.get_label(source)
                        if not isinstance(self.metrics_data[source][i], dict):
                            self.metrics[source] = Gauge( 'pihole_%s' % source,
                                source.replace('_', ' '),
                                [ label ])
                        else:
                            self.metrics[source] = Gauge( 'pihole_%s' % source,
                                source.replace('_', ' '),
                                [ label, 'domain' ])
                    else:
                        if not isinstance(self.metrics_data[source][i], dict):
                            self.metrics[source].labels(i).set(
                                self.metrics_data[source][i])
                        else:
                            for d in self.metrics_data[source][i]:
                                self.metrics[source].labels(i, d).set(
                                    self.metrics_data[source][i][d])
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
        self.httpd = make_server(   interface,
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
    except (FileNotFoundError):
        print("Unable to find: %s" % filename)
    return token


def main():
    parser = argparse.ArgumentParser(
        description='pihole_exporter')
    parser.add_argument('-o', '--pihole',
        help='pihole adress',
        default='pi.hole')
    parser.add_argument('-p', '--port', type=int,
        help='port pihole_exporter is listening on',
        default=9311)
    parser.add_argument('-i', '--interface',
        help='interface pihole_exporter will listen on',
        default='0.0.0.0')
    parser.add_argument('-a', '--auth',
        help='Pihole password hash',
        default=None)
    args = parser.parse_args()

    auth_token = args.auth
    if auth_token == None:
        auth_token = get_authentication_token()


    exporter = pihole_exporter(args.pihole, auth_token)
    exporter.make_server(args.interface, args.port)


if __name__ == '__main__':
    main()
