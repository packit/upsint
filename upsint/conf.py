#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import logging
from pathlib import Path

import yaml

from upsint.exceptions import UpsintException


logger = logging.getLogger(__name__)

CONFIG_FILE_CANDIDATES = (
    "~/.upsint.yaml",
    "~/.upsint.yml",
    "~/.upsint.json",
    "~/.config/packit.yaml",
)


class Conf:
    def __init__(self):
        self._c = None

    @property
    def c(self):
        if self._c is None:
            for c in CONFIG_FILE_CANDIDATES:
                try:
                    content = Path(c).expanduser().read_text()
                except FileNotFoundError:
                    logger.debug(f"file {c} does not exist")
                    continue
                self._c = yaml.safe_load(content)
        return self._c

    def get_auth_configuration(self):
        auth_conf = self.c.get("authentication")
        if not auth_conf:
            raise UpsintException("No authentication defined in the config file.")
        return auth_conf
