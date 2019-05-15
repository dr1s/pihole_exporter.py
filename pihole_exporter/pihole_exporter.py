#!/usr/bin/env python3

#
#   Copyright (c) 2018 Daniel Schmitz
#
#   Permission is hereby granted, free of charge, to any person obtaining a copy
#   of this software and associated documentation files (the "Software"), to deal
#   in the Software without restriction, including without limitation the rights
#   to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#   copies of the Software, and to permit persons to whom the Software is
#   furnished to do so, subject to the following conditions:
#
#   The above copyright notice and this permission notice shall be included in all
#   copies or substantial portions of the Software.
#
#   THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#   IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#   FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#   AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#   LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#   OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#   SOFTWARE.

import json
import argparse
import urllib.request
import socket

from io import StringIO
from prometheus_metrics import exporter, generate_latest


class pihole_exporter(exporter):
    def __init__(self, url, auth, extended=False):
        super().__init__()
        self.url = url
        self.auth = auth
        self.api_url = 'http://%s/admin/api.php' % self.url
        self.httpd = None
        self.extended = extended

        self.summary_raw_url = self.api_url + '?summaryRaw'
        self.top_item_url = self.api_url + '?topItems=100'
        self.top_sources_url = self.api_url + '?getQuerySources=100'
        self.forward_destinations_url = self.api_url + '?getForwardDestinations'
        self.query_types_url = self.api_url + '?getQueryTypes'
        self.get_all_queries_url = self.api_url + '?getAllQueries'
        self.metrics_handler.add('pihole_top_sources', 'client')
        self.metrics_handler.add('pihole_top_queries', 'domain')
        self.metrics_handler.add('pihole_top_ads', 'domain')
        self.metrics_handler.add('pihole_forward_destinations', 'resolver')
        self.metrics_handler.add('pihole_query_type', 'query_type')
        self.metrics_handler.add('pihole_client_queries',
                                 ['hostname', 'domain', 'answer_type'])

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

        for i in summary_raw:
            if i == "status":
                if summary_raw[i] == 'enabled':
                    self.metrics_handler.add_update('pihole_%s' % i, 1)
                else:
                    self.metrics_handler.add_update('pihole_%s' % i, 0)
            elif i == "gravity_last_updated":
                self.metrics_handler.add_update('pihole_%s' % i,
                                                summary_raw[i]['absolute'])
            else:
                self.metrics_handler.add_update('pihole_%s' % i,
                                                summary_raw[i])

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
            self.metrics_handler.update('pihole_client_queries', client_data)

    def generate_latest(self):
        self.get_summary()

        top_items = self.get_json(self.top_item_url)
        if top_items:
            for item in top_items:
                self.metrics_handler.update(
                    'pihole_%s' % item,
                    top_items[item],
                )
        top_sources = self.get_json(self.top_sources_url)
        if top_sources:
            self.metrics_handler.update('pihole_top_sources',
                                        top_sources['top_sources'])

        fw_dest = self.get_json(self.forward_destinations_url)
        if fw_dest:
            self.metrics_handler.update('pihole_forward_destinations',
                                        fw_dest['forward_destinations'])

        qt = self.get_json(self.query_types_url)
        if qt:
            self.metrics_handler.update('pihole_query_type', qt['querytypes'])

        if self.extended:
            self.get_exteneded_metrics()

        return generate_latest()

    def make_wsgi_app(self):
        def prometheus_app(environ, start_response):
            output = self.generate_latest()
            status = str('200 OK')
            headers = [(str('Content-type'), str('text/plain'))]
            start_response(status, headers)
            return [output]

        return prometheus_app


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
