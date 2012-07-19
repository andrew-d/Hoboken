#!/usr/bin/env python

import os
import sys
from setuptools import setup

sys.path.insert(0, os.path.abspath(__file__))
import hoboken

setup(name='Hoboken',
      version=hoboken.__version__,
      description='A Sinatra-inspired web framework for Python',
      author='Andrew Dunham',
      url='http://github.com/andrew-d/hoboken',
      license='Apache',
      platforms='any',
      zip_safe=False,
      install_requires=[
        'WebOb==1.2'
      ],
      packages=['hoboken'],
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules'
      ],
      test_suite = 'hoboken.tests',
     )

