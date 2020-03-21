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
import re
from typing import Optional, Iterable

from ogr import get_instances_from_dict, get_project
from ogr.abstract import GitProject, GitService, PullRequest

from upsint.conf import Conf
from upsint.utils import (
    get_current_branch_name,
    get_remote_url,
    list_local_branches,
    git_branch_d,
)


class App:
    def __init__(self):
        self.conf = Conf()
        self._git_services: Optional[Iterable[GitService]] = None

    @property
    def git_services(self):
        if self._git_services is None:
            self._git_services = get_instances_from_dict(
                self.conf.get_auth_configuration()
            )
        return self._git_services

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
        return sorted(
            list_local_branches(merged_with), key=lambda x: x["date"], reverse=True
        )

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

    def get_current_branch_pr(self, git_project: GitProject) -> PullRequest:
        """
        If the current branch is assoctiated with a PR, get it, otherwise return None
        """
        current_branch = self.get_current_branch()

        pr_re = re.compile(r"^pr/(\d+)$")
        m = pr_re.match(current_branch)
        if m:
            pr_id = int(m.group(1))
            pr = git_project.get_pr(pr_id)
            return pr

        # FIXME: could this logic be in ogr? input: branch + repo, output: pr
        for pr in git_project.get_pr_list():
            if (
                pr.source_branch == current_branch
                and pr.author == git_project.service.user.get_username()
            ):
                return pr
