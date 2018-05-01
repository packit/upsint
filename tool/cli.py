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

import click

from tool.core import App

logger = logging.getLogger("tool")


@click.group()
def tool():
    pass


@click.command(name="fork")
@click.argument('service', type=click.STRING)  # TODO: this could be optional, we can have default
@click.argument('repo', type=click.STRING)
def fork(service, repo):
    """
    Fork selected repository
    """
    a = App()
    s = a.get_service(service)
    s.fork(repo)


tool.add_command(fork)


if __name__ == '__main__':
    tool()
