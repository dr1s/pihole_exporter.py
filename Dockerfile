FROM dr1s/exporter_base:latest

COPY pihole_exporter/pihole_exporter.py exporter/

EXPOSE 9311

ENTRYPOINT python3 pihole_exporter.py
