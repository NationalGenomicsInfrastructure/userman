#!/usr/bin/env python

from setuptools import setup

try:
    with open("requirements.txt", "r") as f:
        install_requires = [x.strip() for x in f.readlines()]
except IOError:
    install_requires = []

setup(name='userman',
      version='14.8.0',
      description='Simple account handling system for use with web services.',
      license='MIT',
      author='Per Kraulis',
      author_email='per.kraulis@scilifelab.se',
      url='https://github.com/NationalGenomicsInfrastructure/userman',
      packages=['userman'],
      include_package_data=True,
      install_requires=install_requires
     )
