# pihole_exporter
A prometheus exporter for Pi-Hole written in Python 3.


# Table of Contents
<!-- TOC depthFrom:1 depthTo:6 withLinks:1 updateOnSave:1 orderedList:0 -->

- [pihole_exporter](#piholeexporter)
- [Table of Contents](#table-of-contents)
- [Available metrics](#available-metrics)
	- [Example](#example)
- [Setup](#setup)
	- [pip](#pip)
	- [manual](#manual)
- [Usage](#usage)
	- [Example](#example)
	- [Authentication](#authentication)
- [Prometheus config](#prometheus-config)
- [Grafana dashboard](#grafana-dashboard)

<!-- /TOC -->

# Available metrics
* Queries forwarded (24h)
* Domains being blocked
* Ads percentage today
* Ads blocked today
* DNS queries today
* Total clients
* Unique clients
* Queries cached
* Unique Domains
* Top Queries
* Top Ads
* Top clients
* Forward destinations
* Query type

## Example
Some metrics have been redacted.

    pihole_exporter_version 0.1
    pihole_queries_forwarded 6447
    pihole_domains_being_blocked 717100
    pihole_ads_percentage_today 2.697061
    pihole_ads_blocked_today 646
    pihole_dns_queries_today 23952
    pihole_clients_ever_seen 10
    pihole_unique_clients 9
    pihole_queries_cached 16799
    pihole_unique_domains 1211
    pihole_top_queries{domain="google.com"} 13739
    pihole_top_queries{domain="grafana.com"} 292
    pihole_top_queries{domain="www.google.com"} 221
    pihole_top_queries{domain="raw.githubusercontent.com"} 294
    pihole_top_ads{domain="brahe.apptimize.com"} 11
    pihole_top_ads{domain="app-measurement.com"} 65
    pihole_top_ads{domain="e.reddit.com"} 21
    pihole_top_ads{domain="s.youtube.com"} 37
    pihole_top_ads{domain="api-analytics.metaps.com"} 18
    pihole_top_ads{domain="www.googletagservices.com"} 8
    pihole_top_ads{domain="www.google-analytics.com"} 11
    pihole_top_ads{domain="device-metrics-us.amazon.com"} 197
    pihole_top_ads{domain="rpc-php.trafficfactory.biz"} 27
    pihole_top_ads{domain="e.crashlytics.com"} 76
    pihole_top_sources{client="192.168.0.105"} 25
    pihole_top_sources{client="192.168.0.112"} 167
    pihole_top_sources{client="192.168.0.106"} 740
    pihole_top_sources{client="192.168.0.100"} 1502
    pihole_top_sources{client="localhost|127.0.0.1"} 1713
    pihole_forward_destinations{resolver="google-public-dns-a.google.com|8.8.8.8"} 12.23
    pihole_forward_destinations{resolver="local|::1"} 73.02
    pihole_forward_destinations{resolver="google-public-dns-b.google.com|8.8.4.4"} 14.75
    pihole_query_type{type="A (IPv4)"} 62.28
    pihole_query_type{type="AAAA (IPv6)"} 37.72

# Setup
## pip
    pip3 install git+https://github.com/dr1s/pihole_exporter.py.git
## manual
    git clone https://github.com/dr1s/pihole_exporter.py.git
    cd pihole_exporter.py
    pip3 install -r requirements.txt
    cd src
    ./pihole_exporter.py
# Usage
	usage: pihole_exporter.py [-h] [-o PIHOLE] [-p PORT] [-i INTERFACE] [-a AUTH]

	pihole_exporter

	optional arguments:
	-h, --help            show this help message and exit
	-o PIHOLE, --pihole PIHOLE
											pihole adress
	-p PORT, --port PORT  port pihole_exporter is listening on
	-i INTERFACE, --interface INTERFACE
									interface pihole_exporter will listen on
	-a AUTH, --auth AUTH  Pihole password hash
## Example

    pihole_exporter --pihole localhost:80 --interface 0.0.0.0 --port 9311

The previous used arguements are the default options. If nothing needs to be changed, pihole_exporter can be started without arguments.

	pihole_exporter

## Authentication
To use pihole_exporter with authentication enabled, get the hashed password from setupVars.conf

	$ grep WEBPASSWORD /etc/pihole/setupVars.conf
	WEBPASSWORD=da1a51f575cd740be233d22548ecac1dbcc96ffa297283a6a204f9213a8aca71

Use this hash as the argument for `--auth`

	pihole_exporter --auth da1a51f575cd740be233d22548ecac1dbcc96ffa297283a6a204f9213a8aca71


# Prometheus config
    - job_name: 'pihole'
      static_configs:
      - targets: ['localhost:9311']

# Grafana dashboard
![Grafana Dashboard](grafana.png)

See [grafana_dashboard.json](grafana_dashboard.json)
