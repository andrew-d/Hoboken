#!/usr/bin/env python
from __future__ import print_function

import os
import re
import sys
from setuptools import setup

version_file = os.path.join('hoboken', '_version.py')
with open(version_file, 'rb') as f:
    version_data = f.read().strip()

if sys.version_info[0] >= 3:
    version_data = version_data.decode('ascii')

version_re = re.compile(r'((?:\d+)\.(?:\d+)\.(?:\d+))')
version = version_re.search(version_data).group(0)

setup(name='Hoboken',
      version=version,
      description='A Sinatra-inspired web framework for Python',
      author='Andrew Dunham',
      url='http://github.com/andrew-d/hoboken',
      license='Apache',
      platforms='any',
      zip_safe=False,
      install_requires=[
        'WebOb>=1.2',
        'Shift==0.0.4'
      ],
      tests_require=[
          'Mock',
          'PyYAML'
      ],
      packages=[
          'hoboken',
          'hoboken.tests',
      ],
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.2',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
      ],
      test_suite = 'hoboken.tests.suite',
     )

