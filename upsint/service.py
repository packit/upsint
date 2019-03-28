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
class Service:
    def __init__(self, token=None):
        self.token = token

    @classmethod
    def create_from_remote_url(cls, remote_url):
        """ create instance of service from provided remote_url """
        raise NotImplementedError()

    def fork(self, target_repo):
        raise NotImplementedError()

    def create_pull_request(self, target_remote, target_branch, current_branch):
        raise NotImplementedError()

    def list_pull_requests(self):
        raise NotImplementedError()
