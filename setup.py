import os
from setuptools import setup, find_packages


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


with open('requirements.txt', 'r') as f:
    requirements = f.readlines()

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    name='pihole_exporter',
    version='0.4.6.7',
    url='https://github.com/dr1s/pihole_exporter.py',
    author='dr1s',
    author_email='dr1s@drs.li',
    license='MIT',
    description='Export pihole metrics for prometheus',
    long_description=long_description,
    long_description_content_type="text/markdown",
    install_requires=requirements,
    packages=find_packages(),
    include_package_data=True,
    entry_points={'console_scripts': ['pihole_exporter=pihole_exporter:main']},
)
