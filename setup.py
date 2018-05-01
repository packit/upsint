#!/usr/bin/python3
# -*- coding: utf-8 -*-

import os

from setuptools import find_packages, setup

BASE_PATH = os.path.dirname(__file__)

# https://packaging.python.org/guides/single-sourcing-package-version/
version = {}
with open("./tool/version.py") as fp:
    exec(fp.read(), version)

long_description = ''.join(open('README.md').readlines())

setup(
    name='tool',
    version=version["__version__"],
    description="Easy way to git",
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=find_packages(),
    install_requires=[
        'Click',
    ],
    entry_points='''
        [console_scripts]
        tool=tool.cli:tool
    ''',
    # data_files=[("share/colin/rulesets/", ["rulesets/default.json",
    license='GPLv3+',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v2 or later (GPLv2+)',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Topic :: Software Development',
    ],
    keywords='git,github',
    url='https://github.com/user-cont/tool',
)
