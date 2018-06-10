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

from tool.core import App

import click
from tabulate import tabulate


logger = logging.getLogger("tool")


@click.group()
def tool():
    pass


@click.command(name="fork")
@click.option('--service', "-s", type=click.STRING, default="github",
              help="Name of the git service (e.g. github/gitlab).")
@click.argument('repo', type=click.STRING)
def fork(service, repo):
    """
    Fork selected repository
    """
    a = App()
    s = a.get_service(service)
    s.fork(repo)


@click.command(name="create-pr")
@click.argument('target_remote', type=click.STRING, required=False, default="upstream")
@click.argument('target_branch', type=click.STRING, required=False, default="master")
def create_pr(target_remote, target_branch):
    """
    Fork selected repository
    """
    a = App()
    s = a.guess_service(remote=target_remote)
    pr_url = s.create_pull_request(target_remote, target_branch, a.get_current_branch())
    print(pr_url)


@click.command(name="list-prs",
               help="List open pull requests in current git repository or the one you selected. "
                    "This is how you can select a repository for Github: <namespace>/<project>.")
@click.option('--service', "-s", type=click.STRING, default="github",
              help="Name of the git service (e.g. github/gitlab).")
@click.argument('repo', type=click.STRING, required=False)
def list_prs(service, repo):
    """
    List pull requests of a selected repository, default to repo in $PWD
    """
    a = App()
    if repo:
        s = a.get_service(service, repo=repo)
    else:
        s = a.guess_service()
    prs = s.list_pull_requests()
    if not prs:
        print("No open pull requests.")
        return
    print(tabulate([
        (
            "#%s" % pr['id'],
            pr['title'],
            "@%s" % pr['author'],
            pr['url']
        )
        for pr in prs
    ], tablefmt="fancy_grid"))


@click.command(name="list-branches",
               help="List branches in the local repository. Fields in the table: branch name, "
                    "remote tracking branch, date, divergance status and "
                    "whether the branch was merged to master."
               )
def list_branches():
    """
    List git branches in current git repository
    """
    a = App()
    print(tabulate(a.list_branches(), tablefmt="fancy_grid"))


tool.add_command(fork)
tool.add_command(create_pr)
tool.add_command(list_prs)
tool.add_command(list_branches)


if __name__ == '__main__':
    tool()
