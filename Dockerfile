FROM dr1s/pipenv-alpine:3.8-python3.7

COPY pihole_exporter/pihole_exporter.py /app

EXPOSE 9311

ENTRYPOINT python3 pihole_exporter.py
