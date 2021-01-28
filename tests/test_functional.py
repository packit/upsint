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
from pathlib import Path

from upsint.utils import clone_repo_and_cd_inside, set_upstream_remote


def call_upsint(parameters, envs=None, cwd=None, return_output=False):
    """ invoke packit in a subprocess """
    cmd = ["python3", "-m", "upsint.cli"] + parameters
    if return_output:
        return subprocess.check_output(cmd, env=envs, cwd=cwd).decode()
    return subprocess.check_call(cmd, env=envs, cwd=cwd)


def test_checkout_pr(tmpdir):
    t = Path(str(tmpdir))
    os.chdir(t)
    repo_name = "hello-world"
    namespace = "packit-service"
    fork_ssh_url = f"git@github.com:TomasTomecek/{repo_name}"
    repo_clone_url = f"https://github.com/{namespace}/{repo_name}"
    pr = "1"
    clone_repo_and_cd_inside(repo_name, fork_ssh_url, namespace)
    set_upstream_remote(repo_clone_url, fork_ssh_url, "pull")

    call_upsint(["checkout-pr", pr])

    assert (
        subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        == b"pr/1\n"
    )
    commit = b"1e89e7e23d408506f7b192c07014e27572990a0f\n"
    assert subprocess.check_output(["git", "rev-parse", "HEAD"]) == commit

    # now let's change head, call co-pr again and see if we still get the same result
    subprocess.check_output(["git", "reset", "--hard", "HEAD^"])

    call_upsint(["checkout-pr", pr])

    assert (
        subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        == b"pr/1\n"
    )
    assert subprocess.check_output(["git", "rev-parse", "HEAD"]) == commit


def test_list_branches(tmp_path):
    os.chdir(tmp_path)
    repo_name = "research"
    namespace = "packit-service"
    repo_clone_url = f"https://github.com/{namespace}/{repo_name}"
    clone_repo_and_cd_inside(repo_name, repo_clone_url, namespace)

    out = call_upsint(["list-branches"], return_output=True)
    assert "╒═" in out
    assert "│ main" in out
