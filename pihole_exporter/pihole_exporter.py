#!/usr/bin/env python3

import json
import argparse
import urllib.request
import logging

from io import StringIO
from flask import Flask
from flask import Response

app = Flask(__name__)

version = 0.1

api_url = None
auth = None

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
    summary = "pihole_exporter_version %s\n" % (version)
    for i in summary_raw:
        if i != "status":
            summary += "pihole_%s %s\n" % (i, summary_raw[i])
        elif summary_raw[i] == 'enabled':
            summary += "pihole_status 1\n"
        else:
            summary += "pihole_status 0\n"

    return summary

def convert_json(json_data, name, option):
    items = str()
    for i in json_data:
        items += "pihole_%s{%s=\"%s\"} %s\n" % (name, option, i, json_data[i])
    return items

@app.route('/metrics', methods=['GET'])
def metrics():
    summary_raw_url = api_url + '?summaryRaw'
    top_item_url = api_url + '?topItems'
    top_sources_url = api_url + '?getQuerySources'
    forward_destinations_url = api_url + '?getForwardDestinations'
    query_types_url = api_url + '?getQueryTypes'

    items = get_summary(summary_raw_url)

    top_items = get_json(top_item_url)
    if top_items:
        top_queries = top_items['top_queries']
        items += convert_json(top_queries, 'top_queries', 'domain')
        top_ads = top_items['top_ads']
        items += convert_json(top_ads, 'top_ads', 'domain')

    top_sources = get_json(top_sources_url)
    if top_sources:
        items += convert_json(top_sources['top_sources'],
            'top_sources', 'client')

    fw_dest = get_json(forward_destinations_url)
    if fw_dest:
        items += convert_json(fw_dest['forward_destinations'],
            'forward_destinations', 'resolver')

    qt = get_json(query_types_url)
    if qt:
        items += convert_json(qt['querytypes'], 'query_type', 'type')

    return Response(items, mimetype="text/plain")


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

    # Disable werkzeug logging to avoid syslog spam
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)

    print("* Listening on %s:%s" % (interface, port))
    app.run(host=interface, port=port)


if __name__ == '__main__':
    main()
