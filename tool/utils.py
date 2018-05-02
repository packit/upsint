import logging
import os
import subprocess
import tempfile

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


def get_remote_url(remote):
    logger.debug("get remote URL for remote %s", remote)
    try:
        url = subprocess.check_output(["git", "remote", "get-url", remote])
    except subprocess.CalledProcessError:
        remote = "origin"
        logger.warning("falling back to %s", remote)
        url = subprocess.check_output(["git", "remote", "get-url", remote])
    return remote, url.decode("utf-8").strip()


def prompt_for_pr_content(commit_msgs):
    t = tempfile.NamedTemporaryFile(delete=False, prefix='gh.')
    try:
        template = "Title of this PR\n\nPR body:\n{}".format(commit_msgs)
        template_b = template.encode("utf-8")
        t.write(template_b)
        t.flush()
        t.close()
        try:
            editor_cmdstring = os.environ['EDITOR']
        except KeyError:
            logger.warning("EDITOR environment variable is not set")
            editor_cmdstring = "/bin/vi"

        logger.debug('using editor: %s', editor_cmdstring)

        cmd = [editor_cmdstring, t.name]

        logger.debug('invoking editor: %s', cmd)
        proc = subprocess.Popen(cmd)
        ret = proc.wait()
        logger.debug('editor returned : %s', ret)
        if ret:
            raise RuntimeError("error from editor")
        with open(t.name) as fd:
            pr_content = fd.read()
        if template == pr_content:
            logger.error("PR description is unchanged")
            raise RuntimeError("The template is not changed, the PR won't be created.")
    finally:
        os.unlink(t.name)
    logger.debug('got: %s', pr_content)
    title, body = pr_content.split("\n", 1)
    logger.debug('title: %s', title)
    logger.debug('body: %s', body)
    return title, body.strip()


def get_current_branch_name():
    return subprocess.check_output(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode("utf-8").strip()


def get_commit_msgs(branch):
    return subprocess.check_output(
        ["git", "log", "--pretty=format:%B%n%n",
         "%s..HEAD" % branch]).decode("utf-8").strip()
