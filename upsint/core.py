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
from typing import Optional, Iterable

from ogr import get_instances_from_dict, get_project
from ogr.abstract import GitProject, GitService

from upsint.conf import Conf
from upsint.utils import get_current_branch_name, get_remote_url, list_local_branches, git_branch_d


class App:
    def __init__(self):
        self.conf = Conf()
        self._git_services: Optional[Iterable[GitService]] = None

    @property
    def git_services(self):
        if self._git_services is None:
            self._git_services = get_instances_from_dict(self.conf.get_auth_configuration())
        return self._git_services

    def get_service(self, service_name, repo=None):
        service_map = {
            GithubService.name: GithubService,
            GitlabService.name: GitlabService
        }
        _class = service_map[service_name]
        configuration = self.conf.c[service_name]
        configuration["full_repo_name"] = repo
        return _class(**configuration)

    def guess_remote_url(self, remote=None):
        if remote is None:
            return get_remote_url("upstream")
        else:
            return get_remote_url(remote)

    def get_current_branch(self):
        return get_current_branch_name()

    def list_branches(self, merged_with: str = "master"):
        """
        provide a list of branches with additional metadata

        :param merged_with: was a branch merged into this one?
        :return dict {
            "name": "master",
            "remote_tracking": "origin",  # can be None
        }
        """
        return sorted(list_local_branches(merged_with), key=lambda x: x["date"], reverse=True)

    def remove_branch(self, branch_name: str):
        """
        remove selected local branch

        :param branch_name: guess what?
        """
        git_branch_d(branch_name)

    def get_git_project(self, url: str) -> GitProject:
        if not url:
            url = self.guess_remote_url()
        return get_project(url, custom_instances=self.git_services)
