#! /usr/bin/env python

from setuptools import setup, find_packages

def readme():
    with open('README.md') as f:
        return f.read()

setup(name='MCCDAQ',
      version='0.1',
      description='SMA Receiver Lab Equipment drivers for MCC DAQ',
      long_description=readme(),
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3.6',
      ],
      keywords='lab equipment, data acquisition',
      url='https://github.com/PaulKGrimes/LabEquipment',
      author='Paul Grimes',
      author_email='pgrimes@cfa.harvard.edu',
      packages=find_packages(),
      install_requires=[
        'mcculw', 'hjson', 'jsonmerge', 'numpy', 'matplotlib'
      ],
      include_package_data=True,
      },
      #test_suite='nose.collector',
      #tests_require=['nose'],
      zip_safe=True)
