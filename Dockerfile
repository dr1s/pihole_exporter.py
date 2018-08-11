FROM python:3-alpine

WORKDIR /pihole_exporter

COPY . /pihole_exporter

RUN pip install virtualenv

RUN virtualenv /env && /env/bin/python setup.py install

EXPOSE 9311

ENTRYPOINT ["/env/bin/pihole_exporter"]
