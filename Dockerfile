FROM alpine:3.8

RUN apk add --no-cache python3 && \
    pip3 install --upgrade pip setuptools && \
    pip3 install pipenv

WORKDIR /exporter

COPY pihole_exporter/pihole_exporter.py pihole_exporter.py
COPY Pipfile Pipfile
COPY Pipfile.lock Pipfile.lock

RUN set -ex && pipenv install --deploy --system

EXPOSE 9311

ENTRYPOINT python3 pihole_exporter.py
