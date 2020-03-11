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
import os
import re
import subprocess
import tempfile
import datetime
from dataclasses import dataclass
from time import sleep
from typing import Iterable, Dict, List

from upsint.constant import CLONE_TIMEOUT

logger = logging.getLogger(__name__)


def clone_repo_and_cd_inside(repo_name, repo_ssh_url, namespace):
    os.makedirs(namespace, exist_ok=True)
    os.chdir(namespace)
    logger.debug("clone %s", repo_ssh_url)

    for _ in range(CLONE_TIMEOUT):
        proc = subprocess.Popen(["git", "clone", repo_ssh_url], stderr=subprocess.PIPE)
        output = proc.stderr.read().decode()
        logger.debug(
            "Clone exited with {} and output: {}".format(proc.returncode, output)
        )
        if "does not exist yet" not in output:
            break
        sleep(1)
    else:
        logger.error("Clone failed.")
        raise Exception("Clone failed")

    # if the repo is already cloned, it's not an issue
    os.chdir(repo_name)


def set_upstream_remote(clone_url, ssh_url, pull_merge_name):
    logger.debug("set remote upstream to %s", clone_url)
    try:
        subprocess.check_call(["git", "remote", "add", "upstream", clone_url])
    except subprocess.CalledProcessError:
        subprocess.check_call(["git", "remote", "set-url", "upstream", clone_url])
    try:
        subprocess.check_call(["git", "remote", "add", "upstream-w", ssh_url])
    except subprocess.CalledProcessError:
        subprocess.check_call(["git", "remote", "set-url", "upstream-w", ssh_url])
    logger.debug("adding fetch rule to get PRs for upstream")
    subprocess.check_call(
        [
            "git",
            "config",
            "--local",
            "--add",
            "remote.upstream.fetch",
            "+refs/{}/*/head:refs/remotes/upstream/{}r/*".format(
                pull_merge_name, pull_merge_name[0]
            ),
        ]
    )


def set_origin_remote(ssh_url, pull_merge_name):
    logger.debug("set remote origin to %s", ssh_url)
    subprocess.check_call(["git", "remote", "set-url", "origin", ssh_url])
    logger.debug("adding fetch rule to get PRs for origin")
    subprocess.check_call(
        [
            "git",
            "config",
            "--local",
            "--add",
            "remote.origin.fetch",
            "+refs/{}/*/head:refs/remotes/origin/{}r/*".format(
                pull_merge_name, pull_merge_name[0]
            ),
        ]
    )


def fetch_all():
    logger.debug("fetching everything")
    with open("/dev/null", "w") as fd:
        subprocess.check_call(["git", "fetch", "--all"], stdout=fd)


def get_remote_url(remote):
    logger.debug("get remote URL for remote %s", remote)
    try:
        url = subprocess.check_output(["git", "remote", "get-url", remote])
    except subprocess.CalledProcessError:
        remote = "origin"
        logger.warning("falling back to %s", remote)
        url = subprocess.check_output(["git", "remote", "get-url", remote])
    return url.decode("utf-8").strip()


def prompt_for_pr_content(commit_msgs):
    t = tempfile.NamedTemporaryFile(delete=False, prefix="gh.")
    try:
        template = "Title of this PR\n\nPR body:\n{}".format(commit_msgs)
        template_b = template.encode("utf-8")
        t.write(template_b)
        t.flush()
        t.close()
        try:
            editor_cmdstring = os.environ["EDITOR"]
        except KeyError:
            logger.warning("EDITOR environment variable is not set")
            editor_cmdstring = "/bin/vi"

        logger.debug("using editor: %s", editor_cmdstring)

        cmd = [editor_cmdstring, t.name]

        logger.debug("invoking editor: %s", cmd)
        proc = subprocess.Popen(cmd)
        ret = proc.wait()
        logger.debug("editor returned : %s", ret)
        if ret:
            raise RuntimeError("error from editor")
        with open(t.name) as fd:
            pr_content = fd.read()
        if template == pr_content:
            logger.error("PR description is unchanged")
            raise RuntimeError("The template is not changed, the PR won't be created.")
    finally:
        os.unlink(t.name)
    logger.debug("got: %s", pr_content)
    title, body = pr_content.split("\n", 1)
    logger.debug("title: %s", title)
    logger.debug("body: %s", body)
    return title, body.strip()


def list_local_branches(merged_with: str) -> Iterable[Dict]:
    """
    provide a list of local git branches with additional metadata

    :param merged_with: was a branch merged into this one?
    :return: list of dicts
    """
    fmt = (
        "%(refname:short);%(upstream:short);%(authordate:iso-strict);%(upstream:track)"
    )
    for_each_ref = (
        subprocess.check_output(["git", "for-each-ref", "--format", fmt, "refs/heads/"])
        .decode("utf-8")
        .strip()
        .split("\n")
    )
    response = []
    was_merged = (
        subprocess.check_output(
            ["git", "branch", "--merged", merged_with, "--format", "%(refname:short)"]
        )
        .decode("utf-8")
        .strip()
        .split("\n")
    )
    for li in for_each_ref:
        fields = li.split(";")
        response.append(
            {
                "name": fields[0],
                "remote_tracking": fields[1],
                "date": datetime.datetime.strptime(fields[2][:-6], "%Y-%m-%dT%H:%M:%S"),
                "tracking_status": fields[3],
                "merged": "merged" if fields[0] in was_merged else "",
            }
        )
    return response


def get_current_branch_name():
    return (
        subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        .decode("utf-8")
        .strip()
    )


def get_commit_msgs(branch):
    return (
        subprocess.check_output(
            ["git", "log", "--pretty=format:%B%n%n", "%s..HEAD" % branch]
        )
        .decode("utf-8")
        .strip()
    )


def git_push():
    """ perform `git push` """
    # FIXME: this command NEEDS to be configurable
    subprocess.check_call(["git", "push", "-qu"])


def git_branch_d(branch_name: str):
    return subprocess.check_call(["git", "branch", "--delete", branch_name])


def get_commits_in_range(lower_bound: str, upper_bound: str = "HEAD") -> List[str]:
    """
    get commits in a range of commits

    :param lower_bound: commits starting here
    :param upper_bound: and ending here
    :return: list of commit hashes
    """
    # "--" - to separate reviions from paths
    cmd = [
        "git",
        "log",
        "--pretty=format:%H",
        "--first-parent",
        f"{lower_bound}..{upper_bound}",
        "--",
    ]
    out: str = subprocess.check_output(cmd).decode()
    commit_list: List[str] = out.strip().split("\n")
    return commit_list


def get_commits_in_a_merge(commit_hash: str) -> List[str]:
    """
    get commits included in a merge

    :param commit_hash: a pony
    :return: list of commit hashes
    """
    # "--" - to separate reviions from paths
    cmd = ["git", "log", "--pretty=format:%H", f"{commit_hash}^..{commit_hash}", "--"]
    out: str = subprocess.check_output(cmd).decode()
    commit_list: List[str] = out.strip().split("\n")
    # the first one is the merge commit, we don't care about that
    return commit_list[1:]


@dataclass
class CommitMetadata:
    message: str
    body: str


def get_commit_metadata(commit_hash: str) -> CommitMetadata:
    commit_subject = (
        subprocess.check_output(["git", "show", "--quiet", "--format=%s", commit_hash])
        .decode()
        .strip()
    )
    commit_body = subprocess.check_output(
        ["git", "show", "--quiet", "--format=%b", commit_hash]
    ).decode()
    reg = r"Reviewed\-by:.+"
    commit_body = re.sub(reg, "", commit_body, flags=re.DOTALL).strip()
    return CommitMetadata(message=commit_subject, body=commit_body)
