from setuptools import setup, find_packages

setup(
    name='pihole_exporter',
    version='0.2.dev0',
    url='https://github.com/dr1s/pihole_exporter.py',
    author='dr1s',
    license='MIT',
    description='Export pihole metrics for prometheus',
    install_requires=["Flask", "prometheus_client"],
    packages=find_packages(),
    include_package_data = True,
    entry_points={'console_scripts': ['pihole_exporter=pihole_exporter.pihole_exporter:main']},
)
