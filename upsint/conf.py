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

import json
import os


class Conf:
    def __init__(self):
        self._c = None

    @property
    def c(self):
        if self._c is None:
            with open(os.path.expanduser("~/.upsint.json")) as fd:
                self._c = json.load(fd)
        return self._c

    def get_github_configuration(self):
        # TODO: implement proper validation
        return self.c["github"]

    def get_gitlab_configuration(self):
        # TODO: implement proper validation
        return self.c["gitlab"]
