#!/usr/bin/env python3

__VERSION__ = "0.2"

import json
import argparse
import urllib.request
import logging
import threading

from io import StringIO
from prometheus_client import Gauge, generate_latest
from wsgiref.simple_server import make_server, WSGIRequestHandler

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

        self.summary_raw_url = self.api_url + '?summaryRaw'
        self.top_item_url = self.api_url + '?topItems'
        self.top_sources_url = self.api_url + '?getQuerySources'
        self.forward_destinations_url = self.api_url + '?getForwardDestinations'
        self.query_types_url = self.api_url + '?getQueryTypes'



    def get_json(self, url):
        if self.auth:
            url += "&auth=%s" % self.auth
        response = urllib.request.urlopen(url)
        data = response.read()
        text = data.decode('utf-8')
        io = StringIO(text)
        json_text = json.load(io)
        return json_text

    def get_summary(self, url):
        summary_raw = self.get_json(url)
        for i in summary_raw:
            if not i in self.metrics:
                self.metrics[i] = Gauge('pihole_%s' % i.lower(),
                                        i.replace('_',' '))
            if i == "status":
                if summary_raw[i] == 'enabled':
                    self.metrics[i].set(1)
                else:
                    self.metrics[i].set(0)
            elif i == "gravity_last_updated":
            #the relative time can be calculated
                self.metrics[i].set(summary_raw[i]['absolute'])
            else:
                self.metrics[i].set(summary_raw[i])

    def convert_json(self, json_data, name, option):
        for i in json_data:
            if name not in self.metrics:
                self.metrics[name] = Gauge( 'pihole_%s' % name,
                                    name.replace('_', ' '),
                                    [ option ])
            self.metrics[name].labels(i).set(json_data[i])

    def get_metrics(self):
        self.get_summary(self.summary_raw_url)

        top_items = self.get_json(self.top_item_url)
        if top_items:
            top_queries = top_items['top_queries']
            self.convert_json(top_queries, 'top_queries', 'domain')
            top_ads = top_items['top_ads']
            self.convert_json(top_ads, 'top_ads', 'domain')

        top_sources = self.get_json(self.top_sources_url)
        if top_sources:
            self.convert_json(  top_sources['top_sources'],
                                'top_sources',
                                'client')

        fw_dest = self.get_json(self.forward_destinations_url)
        if fw_dest:
            self.convert_json(fw_dest['forward_destinations'],
                        'forward_destinations', 'resolver')

        qt = self.get_json(self.query_types_url)
        if qt:
            self.convert_json(qt['querytypes'], 'query_type', 'type')

        return generate_latest()

    def make_prometheus_app(self):

        def prometheus_app(environ, start_response):
            output = self.get_metrics()
            status = str('200 OK')
            headers = [(str('Content-type'), str('text/plain'))]
            start_response(status, headers)
            return [output]
        return prometheus_app

    def make_server(self, interface, port):
        print("* Listening on %s:%s" % (interface, port))
        self.httpd = make_server(   interface,
                                    port,
                                    self.make_prometheus_app(),
                                    handler_class=self._SilentHandler)
        t = threading.Thread(target=self.httpd.serve_forever)
        t.start()


def main():
    parser = argparse.ArgumentParser(
        description='pihole_exporter')
    parser.add_argument('-o', '--pihole',
        help='pihole adress',
        default='localhost:80')
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

    exporter = pihole_exporter(args.pihole, args.auth)
    exporter.make_server(args.interface, args.port)


if __name__ == '__main__':
    main()
