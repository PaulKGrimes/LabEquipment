#! /usr/bin/env python

from setuptools import setup, find_packages

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='InstrumentDrivers',
      version='0.1',
      description='SMA Receiver Lab drivers for pyvisa instruments',
      long_description=readme(),
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.6',
      ],
      keywords='lab equipment, data acquisition, GPIB drivers',
      url='https://github.com/PaulKGrimes/LabEquipment/InstrumentDrivers',
      author='Paul Grimes',
      author_email='pgrimes@cfa.harvard.edu',
      packages=find_packages(),
      install_requires=[
          'pyvisa', 'numpy', 'matplotlib'
      ],
      include_package_data=True,
      #test_suite='nose.collector',
      #tests_require=['nose'],
      zip_safe=True)
