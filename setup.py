#!/usr/bin/python3
# -*- coding: utf-8 -*-

from pathlib import Path
from setuptools import setup


setup(
    install_requires=Path("./requirements.txt").read_text(),
)
