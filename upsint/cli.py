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

from upsint.core import App

import click
from tabulate import tabulate

logger = logging.getLogger("upsint")


@click.group()
def upsint():
    pass


@click.command(name="fork")
@click.option('--service', "-s", type=click.STRING, default="github",
              help="Name of the git service (e.g. github/gitlab)."
                   "This is how you can select a repository for Github: <owner>/<project>.")
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
                    "This is how you can select a repository for Github: <owner>/<project>.")
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
                    "remote tracking branch, date, divergence status and "
                    "whether the branch was merged to master."
               )
def list_branches():
    """
    List git branches in current git repository
    """
    a = App()
    print(tabulate(a.list_branches(), tablefmt="fancy_grid"))


@click.command(name="list-labels",
               help="List labels for the project. "
                    "This is how you can select a repository for Github: <owner>/<project>.")
@click.option('--service', "-s", type=click.STRING, default="github",
              help="Name of the git service (e.g. github/gitlab).")
@click.argument('repo', type=click.STRING, required=False)
def list_labels(service, repo):
    """
    List the labels for the selected repository, default to repo in $PWD
    """
    app = App()
    if repo:
        serv = app.get_service(service, repo=repo)
    else:
        serv = app.guess_service()
    repo_labels = serv.list_labels()
    if not repo_labels:
        print("No labels.")
        return
    print(tabulate([
        (
            label.name,
            label.color,
            label.description
        )
        for label in repo_labels
    ], tablefmt="fancy_grid"))


@click.command(name="list-tags",
               help="List tags for the project. "
                    "This is how you can select a repository for Github: <owner>/<project>.")
@click.option('--service', "-s", type=click.STRING, default="github",
              help="Name of the git service (e.g. github/gitlab).")
@click.argument('repo', type=click.STRING, required=False)
def list_tags(service, repo):
    """
    List the tags for the selected repository, default to repo in $PWD
    """
    app = App()
    if repo:
        serv = app.get_service(service, repo=repo)
    else:
        serv = app.guess_service()
    repo_tags = serv.list_tags()
    if not repo_tags:
        print("No tags.")
        return
    print(tabulate([
        (
            tag['name'],
            tag['url']
        )
        for tag in repo_tags
    ], tablefmt="fancy_grid"))


@click.command(name="update-labels",
               help="Update labels of other project. "
                    "Multiple destinations can be set by joining them with semicolon. "
                    "This is how you can select a repository for Github: <owner>/<project>.")
@click.option('--source-repo', '-r', type=click.STRING)
@click.option('--source-service', type=click.STRING, default="github",
              help="Name of the git service (e.g. github/gitlab).")
@click.option('--service', "-s", type=click.STRING, default="github",
              help="Name of the git service for destination (e.g. github/gitlab).")
@click.argument('destination', type=click.STRING, nargs=-1)
def update_labels(source_repo, service, source_service, destination):
    """
    Update labels for the selected repository, default to repo in $PWD
    """
    app = App()
    if source_repo:
        serv = app.get_service(source_service, repo=source_repo)
    else:
        serv = app.guess_service()
    repo_labels = serv.list_labels()
    if not repo_labels:
        print("No labels.")
        return

    for repo_for_copy in destination:
        other_serv = app.get_service(service, repo=repo_for_copy)
        changes = other_serv.update_labels(labels=repo_labels)

        click.echo("{changes} labels of {labels_count} copied to {repo_name}".format(
            changes=changes,
            labels_count=len(repo_labels),
            repo_name=repo_for_copy
        ))


upsint.add_command(fork)
upsint.add_command(create_pr)
upsint.add_command(list_prs)
upsint.add_command(list_branches)
upsint.add_command(list_tags)
upsint.add_command(list_labels)
upsint.add_command(update_labels)

if __name__ == '__main__':
    upsint()
