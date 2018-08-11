#!/usr/bin/env python3

__VERSION__ = "0.2.dev0"

import json
import argparse
import urllib.request
import logging
import threading


from io import StringIO
from flask import Flask
from flask import Response
from prometheus_client import Gauge, generate_latest
from wsgiref.simple_server import make_server, WSGIRequestHandler

app = Flask(__name__)

api_url = None
auth = None
metrics = dict()

class _SilentHandler(WSGIRequestHandler):
    """WSGI handler that does not log requests."""

    def log_message(self, format, *args):
        """Log nothing."""

def get_json(url):
    if auth:
        url += "&auth=%s" % auth
    response = urllib.request.urlopen(url)
    data = response.read()
    text = data.decode('utf-8')
    io = StringIO(text)
    json_text = json.load(io)
    return json_text

def get_summary(url):
    summary_raw = get_json(url)
    for i in summary_raw:
        if not i in metrics:
            metrics[i] = Gauge('pihole_%s' % i, i.replace('_',' '))
        if i == "status":
            if summary_raw[i] == 'enabled':
                metrics[i].set(1)
            else:
                metrics[i].set(0)
        elif i == "gravity_last_updated":
        #the relative time can be calculated
            metrics[i].set(summary_raw[i]['absolute'])
        else:
            metrics[i].set(summary_raw[i])

def convert_json(json_data, name, option):
    for i in json_data:
        if name not in metrics:
            metrics[name] = Gauge( 'pihole_%s' % name,
                                name.replace('_', ' '),
                                [ option ])
        metrics[name].labels(i).set(json_data[i])

@app.route('/metrics', methods=['GET'])
def get_metrics():
    summary_raw_url = api_url + '?summaryRaw'
    top_item_url = api_url + '?topItems'
    top_sources_url = api_url + '?getQuerySources'
    forward_destinations_url = api_url + '?getForwardDestinations'
    query_types_url = api_url + '?getQueryTypes'

    get_summary(summary_raw_url)

    top_items = get_json(top_item_url)
    if top_items:
        top_queries = top_items['top_queries']
        convert_json(top_queries, 'top_queries', 'domain')
        top_ads = top_items['top_ads']
        convert_json(top_ads, 'top_ads', 'domain')

    top_sources = get_json(top_sources_url)
    if top_sources:
        convert_json(top_sources['top_sources'], 'top_sources', 'client')

    fw_dest = get_json(forward_destinations_url)
    if fw_dest:
        convert_json(fw_dest['forward_destinations'],
                    'forward_destinations', 'resolver')

    qt = get_json(query_types_url)
    if qt:
        convert_json(qt['querytypes'], 'query_type', 'type')

    return Response(generate_latest(), mimetype="text/plain")


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

    url = "http://%s" % (args.pihole)
    port = args.port
    interface = args.interface
    global auth
    auth = args.auth
    global api_url
    api_url = url + '/admin/api.php'

    print("* Listening on %s:%s" % (interface, port))
    httpd = make_server(interface, port, app, handler_class=_SilentHandler)
    t = threading.Thread(target=httpd.serve_forever)
    t.start()

if __name__ == '__main__':
    main()
