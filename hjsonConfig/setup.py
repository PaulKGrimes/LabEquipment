#! /usr/bin/env python

from setuptools import setup, find_packages

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='hjsonConfig',
      version='0.1',
      description='hjsonConfig library for parsing hjson configuration files',
      long_description=readme(),
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.6',
      ],
      keywords='config, hjson',
      url='https://github.com/PaulKGrimes/LabEquipment/hjsonConfig',
      author='Paul Grimes',
      author_email='pgrimes@cfa.harvard.edu',
      packages=find_packages(),
      install_requires=[
          'hjson', 'jsonmerge'
      ],
      include_package_data=True,
      #test_suite='nose.collector',
      #tests_require=['nose'],
      zip_safe=True)
