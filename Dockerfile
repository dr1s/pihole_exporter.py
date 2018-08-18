FROM alpine:latest

RUN apk add --no-cache python3 && \
    pip3 install --upgrade pip setuptools && \
    pip3 install virtualenv

WORKDIR /pihole_exporter

COPY . /pihole_exporter

RUN virtualenv -p python3 /env && /env/bin/python setup.py install

EXPOSE 9311

ENTRYPOINT ["/env/bin/pihole_exporter"]
