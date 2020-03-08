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
import os
import subprocess
from contextlib import contextmanager
from pathlib import Path
from typing import Union

from upsint.utils import get_commits_in_range, get_commits_in_a_merge

GIT_TAG = "0.1.0"


def initiate_git_repo(directory: str,):
    """
    Initiate a git repo for testing.

    :param directory: path to the git repo
    """
    subprocess.check_call(["git", "init", "."], cwd=directory)
    readme_file = Path(directory).joinpath("README")
    readme_file.write_text("Best upstream project ever!\n")
    subprocess.check_call(["git", "add", "."], cwd=directory)
    subprocess.check_call(["git", "commit", "-m", "initial commit"], cwd=directory)
    subprocess.check_call(
        ["git", "tag", "-a", "-m", f"tag {GIT_TAG}, tests", GIT_TAG], cwd=directory
    )

    readme_file.write_text("line 1")
    subprocess.check_call(["git", "commit", "-a", "-m", "line 1"], cwd=directory)

    subprocess.check_call(["git", "checkout", "-b", "branch"], cwd=directory)
    readme_file.write_text("created on a branch")
    subprocess.check_call(["git", "commit", "-a", "-m", "branch change"], cwd=directory)
    readme_file.write_text("more branch changes")
    subprocess.check_call(
        ["git", "commit", "-a", "-m", "branch change #2"], cwd=directory
    )

    subprocess.check_call(["git", "checkout", "master"], cwd=directory)
    subprocess.check_call(
        ["git", "merge", "--no-ff", "-m", "merge time!", "branch"], cwd=directory
    )


@contextmanager
def cwd(target: Union[str, Path]):
    """
    Manage cwd in a pushd/popd fashion.

    Usage:
        with cwd(tmpdir):
          do something in tmpdir
    """
    curdir = os.getcwd()
    os.chdir(target)
    try:
        yield
    finally:
        os.chdir(curdir)


def test_get_commits_in_range(tmpdir):
    with cwd(str(tmpdir)):
        initiate_git_repo(str(tmpdir))
        commits = get_commits_in_range(GIT_TAG)
        assert len(commits) == 2
        bot_commit_id = (
            subprocess.check_output(["git", "rev-parse", GIT_TAG]).strip().decode()
        )
        up_commit_id = (
            subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode()
        )
        assert bot_commit_id not in commits
        assert up_commit_id in commits


def test_get_commits_in_merge(tmpdir):
    with cwd(str(tmpdir)):
        initiate_git_repo(str(tmpdir))
        commits = get_commits_in_a_merge("HEAD")
        merge_commit_hash = (
            subprocess.check_output(["git", "rev-parse", "HEAD"]).strip().decode()
        )
        _, in_merge_commit = (
            subprocess.check_output(["git", "show", "--quiet", "--format=%P", "HEAD"])
            .decode()
            .strip()
            .split(" ")
        )
        assert merge_commit_hash not in commits
        assert in_merge_commit in commits
        assert len(commits) == 2
