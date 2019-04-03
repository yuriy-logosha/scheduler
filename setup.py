#!/usr/bin/env python

import os.path
import sys

if sys.version_info < (3, 5, 0):
    sys.stderr.write("ERROR: You need Python 3.5 or later to use scheduler.\n")
    exit(1)

# we'll import stuff from the source tree, let's ensure is on the sys path
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from distutils.core import setup

setup(name='scheduler',
      version='1.0',
      description='Implementation of launcher/runner application with scheduler.',
      long_description='Scheduler app responsible for execution of python scripts.',
      author='Iurii Logosha',
      author_email='yuriy.logosha@gmail.com',
      url='',
      license='MIT License',
      py_modules=['scheduler'],
      include_package_data=True,
      )
