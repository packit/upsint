import logging
import os
import subprocess


logger = logging.getLogger(__name__)


def clone_repo_and_cd_inside(repo, namespace):
    os.makedirs(namespace, exist_ok=True)
    os.chdir(namespace)
    logger.debug("clone %s", repo.ssh_url)
    retcode = subprocess.call(["git", "clone", repo.ssh_url])
    # if the repo is already cloned, it's not an issue
    logger.debug("clone return code: %s", retcode)
    os.chdir(repo.name)


def set_upstream_remote(clone_url, ssh_url):
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
    subprocess.check_call(["git", "config", "--local", "--add", "remote.upstream.fetch",
                           "+refs/pull/*/head:refs/remotes/upstream/pr/*"])


def set_origin_remote(ssh_url):
    logger.debug("set remote origin to %s", ssh_url)
    subprocess.check_call(["git", "remote", "set-url", "origin", ssh_url])
    logger.debug("adding fetch rule to get PRs for origin")
    subprocess.check_call(["git", "config", "--local", "--add", "remote.origin.fetch",
                           "+refs/pull/*/head:refs/remotes/origin/pr/*"])


def fetch_all():
    logger.debug("fetching everything")
    with open("/dev/null", "w") as fd:
        subprocess.check_call(["git", "fetch", "--all"], stdout=fd)
