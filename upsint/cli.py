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
import re
import subprocess
import sys

import click
from ogr.abstract import CommitStatus
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
    get_commits_in_range,
    get_commit_metadata,
    get_commits_in_a_merge,
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
@click.argument("target_branch", type=click.STRING, required=False, default=None)
def create_pr(target_remote, target_branch):
    """
    Create a pull or a merge request against upstream remote.

    The default projects's branch is used implicitly
    (which everyone can configure in their project settings).
    """
    app = App()

    url = app.guess_remote_url()
    git_project = app.get_git_project(url)

    username = git_project.service.user.get_username()

    if not target_branch:
        target_branch = git_project.default_branch
        logger.info(f"Branch not specified, using {target_branch}.")

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
    "whether the branch was merged to the main branch.",
)
@click.option(
    "--merged-with",
    type=click.STRING,
    default=None,
    help="Was a branch merged with this one?",
)
@click.option(
    "--remote",
    type=click.STRING,
    default="upstream",
    help="List branches of this project specified as git-remote name",
)
def list_branches(merged_with, remote):
    """
    List git branches in current git repository
    """
    a = App()
    print(
        tabulate(
            a.list_branches(merged_with=merged_with, remote=remote),
            tablefmt="fancy_grid",
        )
    )


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


@click.command(name="get-changes")
@click.argument("lower-bound", type=click.STRING)
@click.argument("upper-bound", type=click.STRING, default="HEAD")
def get_changes(lower_bound, upper_bound):
    """
    Get changelog-like changes in a commit range
    """
    app = App()
    url = app.guess_remote_url()
    git_project = app.get_git_project(url)
    commits = get_commits_in_range(lower_bound=lower_bound, upper_bound=upper_bound)
    reg = re.compile(r"Merge pull request #(\d+) from (\w+)/\w+")

    for com in commits:
        # we could get all the commit messages in a single git call,
        # but parsing that would be pretty hard and prone to errors
        commit_metadata = get_commit_metadata(com)
        match = reg.match(commit_metadata.message)
        if match:
            pr_id = match.group(1)
            author = match.group(2)

            pr = git_project.get_pr(int(pr_id))

            print(
                f"* {commit_metadata.body}, by [@{author}](https://github.com/{author}), "
                f"[#{pr_id}](https://github.com/{git_project.namespace}"
                f"/{git_project.repo}/pull/{pr_id})"
            )
            print(f"  * description: {pr.description!r}")
            for m_commit in get_commits_in_a_merge(com):
                m = get_commit_metadata(m_commit)
                print(f"  * commit: {m.message}")

        else:
            print(f"* {commit_metadata.message}")


@click.command(name="status")
@click.option(
    "--with-pr-comments",
    type=click.BOOL,
    default=False,
    help="If on a PR branch, show all the comments",
)
def status(with_pr_comments):
    """
    Get information about project. If not on master,
    figure out if the branch is associated with a PR and get status of that PR.
    """
    app = App()
    url = app.guess_remote_url()
    git_project = app.get_git_project(url)

    pr = app.get_current_branch_pr(git_project)
    if pr:
        click.echo(f"#{pr.id} ", nl=False)
        click.echo(click.style(pr.title, fg="white"), nl=False)
        click.echo(", by @", nl=False)
        click.echo(click.style(pr.author, bold=True))
        if len(pr.description) > 255:
            click.echo(click.style(f"{pr.description[:255]}...", fg="yellow"))
        else:
            click.echo(click.style(pr.description, fg="yellow"))
        top_commit = pr.get_all_commits()[-1]

        commit_statuses = git_project.get_commit_statuses(top_commit)
        # github returns all statuses, not just the latest:
        # so let's just display the latest ones
        processed = set()
        for cs in commit_statuses:
            if cs.context in processed:
                continue
            if cs.state in (CommitStatus.pending, CommitStatus.running):
                color, symbol = "yellow", "🚀"
            elif cs.state in (CommitStatus.failure, CommitStatus.error):
                color, symbol = "red", "🞭"
            elif cs.state == CommitStatus.success:
                color, symbol = "green", "✓"
            elif cs.state == CommitStatus.canceled:
                color, symbol = "orange", "🗑"
            else:
                logger.warning(
                    f"I don't know this type of commit status: {cs.state.value}, {cs.comment}"
                )
                continue
            processed.add(cs.context)
            click.echo(
                click.style(f"{symbol} {cs.context} - {cs.comment} {cs.url}", fg=color)
            )
        if with_pr_comments:
            pr_comments = pr.get_comments()
            if pr_comments:
                click.echo()
                for comment in pr_comments:
                    click.echo(
                        click.style(f"{comment.author} ({comment.created})", bold=True)
                    )
                    click.echo(click.style(comment.body))
                    click.echo(click.style(40 * "-"))
    else:
        open_issues = git_project.get_issue_list()
        click.echo(f"Open issues: {len(open_issues)}")
        open_prs = git_project.get_pr_list()
        click.echo(f"Open PRs: {len(open_prs)}")
        latest_release = git_project.get_latest_release()
        click.echo(f"Latest release: {latest_release.title}")
        # TODO: printing latest commit would be nice


upsint.add_command(fork)
upsint.add_command(create_pr)
upsint.add_command(list_prs)
upsint.add_command(list_branches)
upsint.add_command(list_tags)
upsint.add_command(list_labels)
upsint.add_command(update_labels)
upsint.add_command(remove_merged_branches)
upsint.add_command(checkout_pr)
upsint.add_command(get_changes)
upsint.add_command(status)


if __name__ == "__main__":
    upsint()
