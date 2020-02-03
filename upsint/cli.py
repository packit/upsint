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
import subprocess
import sys

import click
from tabulate import tabulate

from upsint.core import App
from upsint.utils import (
    git_push,
    prompt_for_pr_content,
    get_commit_msgs,
    fetch_all,
    set_origin_remote,
    clone_repo_and_cd_inside,
    set_upstream_remote,
)

logger = logging.getLogger("upsint")


@click.group()
def upsint():
    pass


@click.command(name="fork")
@click.argument("repo", type=click.STRING)
def fork(repo):
    """
    Fork selected repository
    """
    app = App()

    target_repo_org, target_repo_name = repo.split("/", 1)
    # let's default to github if there is only 1 slash in repo

    if "/" in target_repo_name:
        git_project = app.get_git_project(repo)
    else:
        git_project = app.get_git_project(f"https://github.com/{repo}")
    username = git_project.service.user.get_username()
    forked_repo = git_project.fork_create()
    # FIXME: haxxxxx
    forked_repo.repo = target_repo_name
    forked_repo.namespace = username

    forked_repo_ssh_url = forked_repo.get_git_urls()["ssh"]

    clone_repo_and_cd_inside(target_repo_name, forked_repo_ssh_url, target_repo_org)

    set_upstream_remote(
        clone_url=git_project.get_git_urls()["git"],
        ssh_url=git_project.get_git_urls()["ssh"],
        pull_merge_name="pull",
    )
    set_origin_remote(forked_repo_ssh_url, pull_merge_name="pull")
    fetch_all()


@click.command(name="create-pr")
@click.argument("target_remote", type=click.STRING, required=False, default="upstream")
@click.argument("target_branch", type=click.STRING, required=False, default="master")
def create_pr(target_remote, target_branch):
    """
    Fork selected repository
    """
    app = App()

    url = app.guess_remote_url()
    git_project = app.get_git_project(url)

    username = git_project.service.user.get_username()

    base = "{}/{}".format(target_remote, target_branch)

    git_push()

    title, body = prompt_for_pr_content(get_commit_msgs(base))

    pr = git_project.create_pr(
        title, body, target_branch, app.get_current_branch(), fork_username=username
    )

    logger.info("PR link: %s", pr.url)
    print(pr.url)


@click.command(
    name="list-prs",
    help="List open pull requests in current git repository or the one you selected. "
    "This is how you can select a repository for Github: <owner>/<project>.",
)
@click.argument("repo", type=click.STRING, required=False)
def list_prs(repo):
    """
    List pull requests of a selected repository, default to repo in $PWD
    """
    app = App()
    url = repo or app.guess_remote_url()
    git_project = app.get_git_project(url)
    prs = git_project.get_pr_list()
    if not prs:
        print("No open pull requests.")
        return
    print(
        tabulate(
            [("#%s" % pr.id, pr.title, "@%s" % pr.author, pr.url) for pr in prs],
            tablefmt="fancy_grid",
        )
    )


@click.command(
    name="list-branches",
    help="List branches in the local repository. Fields in the table: branch name, "
    "remote tracking branch, date, divergence status and "
    "whether the branch was merged to master.",
)
@click.option(
    "--merged-with",
    type=click.STRING,
    default="master",
    help="Was a branch merged with this one?",
)
def list_branches(merged_with):
    """
    List git branches in current git repository
    """
    a = App()
    print(tabulate(a.list_branches(merged_with=merged_with), tablefmt="fancy_grid"))


@click.command(
    name="list-labels",
    help="List labels for the project. "
    "This is how you can select a repository for Github: <owner>/<project>.",
)
@click.argument("repo", type=click.STRING, required=False)
def list_labels(repo):
    """
    List the labels for the selected repository, default to repo in $PWD
    """
    app = App()
    url = repo or app.guess_remote_url()
    git_project = app.get_git_project(url)
    try:
        repo_labels = git_project.get_labels()
    except AttributeError:
        click.echo(
            f"We don't support repository-wide labels for type {git_project.__class__.__name__}.",
            err=True,
        )
        sys.exit(2)
    if not repo_labels:
        print("No labels.")
        return
    print(
        tabulate(
            [(label.name, label.color, label.description) for label in repo_labels],
            tablefmt="fancy_grid",
        )
    )


@click.command(
    name="list-tags",
    help="List tags for the project. "
    "This is how you can select a repository for Github: <owner>/<project>.",
)
@click.argument("repo", type=click.STRING, required=False)
def list_tags(repo):
    """
    List the tags for the selected repository, default to repo in $PWD
    """
    app = App()
    url = repo or app.guess_remote_url()
    git_project = app.get_git_project(url)
    repo_tags = git_project.get_tags()
    if not repo_tags:
        print("No tags.")
        return
    print(
        tabulate(
            [(tag.name, tag.commit_sha) for tag in repo_tags], tablefmt="fancy_grid"
        )
    )


@click.command(
    name="update-labels",
    help="Update labels of other project. "
    "Multiple destinations can be set by joining them with semicolon. "
    "This is how you can select a repository for Github: <owner>/<project>.",
)
@click.option("--source-repo", "-r", type=click.STRING)
@click.option(
    "--source-service",
    type=click.STRING,
    default="github",
    help="Name of the git service (e.g. github/gitlab).",
)
@click.option(
    "--service",
    "-s",
    type=click.STRING,
    default="github",
    help="Name of the git service for destination (e.g. github/gitlab).",
)
@click.argument("destination", type=click.STRING, nargs=-1)
def update_labels(source_repo, service, source_service, destination):
    """
    Update labels for the selected repository, default to repo in $PWD
    """
    app = App()
    url = app.guess_remote_url()
    git_project = app.get_git_project(url)
    try:
        repo_labels = git_project.get_labels()
    except AttributeError:
        click.echo(
            f"Project {git_project.__class__.__name__} does not support repository-wide labels.",
            err=True,
        )
        sys.exit(2)
    if not repo_labels:
        print("No labels.")
        return

    for repo_for_copy in destination:
        other_serv = app.get_service(service, repo=repo_for_copy)
        changes = other_serv.update_labels(labels=repo_labels)

        click.echo(
            "{changes} labels of {labels_count} copied to {repo_name}".format(
                changes=changes, labels_count=len(repo_labels), repo_name=repo_for_copy
            )
        )


@click.command(name="remove-merged-branches")
@click.argument("merged_with_branch", type=click.STRING, default="master")
def remove_merged_branches(merged_with_branch):
    """
    Remove branches which are already merged (in master by default)

    Argument MERGED_WITH_BRANCH defaults to master and checks whether
    a branch was merged with this one
    """
    a = App()
    to_remove = []
    for branch_dict in a.list_branches(merged_with_branch):
        branch_name = branch_dict["name"]
        if (
            branch_name == merged_with_branch
            or branch_name == branch_dict["remote_tracking"]
        ):
            # don't remove self or a local copy of remote branch
            continue
        if branch_dict["merged"] == "merged":
            to_remove.append(branch_name)
    if not to_remove:
        print("Nothing to remove.")
        return
    print("Shall we remove these local branches?")
    for b in to_remove:
        print(f"* {b}")
    inp = input("Y/N? ")
    if inp in ("y", "Y", "yolo"):
        print("Removing...")
        for b in to_remove:
            a.remove_branch(b)
    else:
        print("Doing nothing, stay safe my friend.")


@click.command(name="checkout-pr")
@click.option(
    "--remote",
    type=click.STRING,
    default="upstream",
    help="Check out a pull request from this remote",
)
@click.argument("pr", type=click.INT)
def checkout_pr(remote, pr):
    """
    `git checkout` a pull request locally
    """
    local_refspec = f"{remote}/pr/{pr}"

    # we only need to fetch the ref for the PR
    subprocess.check_call(
        ["git", "fetch", remote, f"+refs/pull/{pr}/head:refs/remotes/{local_refspec}"]
    )

    # doing -B in case it exists already
    subprocess.check_call(["git", "checkout", "-B", f"pr/{pr}", local_refspec])


upsint.add_command(fork)
upsint.add_command(create_pr)
upsint.add_command(list_prs)
upsint.add_command(list_branches)
upsint.add_command(list_tags)
upsint.add_command(list_labels)
upsint.add_command(update_labels)
upsint.add_command(remove_merged_branches)
upsint.add_command(checkout_pr)


if __name__ == "__main__":
    upsint()
