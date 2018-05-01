import logging

from tool.service import Service
from tool.utils import clone_repo_and_cd_inside, set_upstream_remote, set_origin_remote, fetch_all

import github


logger = logging.getLogger(__name__)


class GithubService(Service):
    def __init__(self, token=None):
        super().__init__(token=token)

        self.g = github.Github(login_or_token=self.token)
        self.user = self.g.get_user()

    def _is_fork_of(self, user_repo, target_repo):
        """ is provided repo fork of gh.com/{parent_repo}/? """
        return user_repo.fork and user_repo.parent and \
            user_repo.parent.full_name == target_repo.full_name

    def fork(self, target_repo):

        target_repo_org, target_repo_name = target_repo.split("/", 1)

        target_repo_gh = self.g.get_repo(target_repo)

        try:
            # is it already forked?
            user_repo = self.user.get_repo(target_repo_name)
            if not self._is_fork_of(user_repo, target_repo):
                raise RuntimeError("repo %s is not a fork of %s" % (target_repo_gh, user_repo))
        except github.UnknownObjectException:
            # nope
            user_repo = None

        if self.user.login == target_repo_org:
            # user wants to fork its own repo; let's just set up remotes 'n stuff
            if not user_repo:
                raise RuntimeError("repo %s not found" % target_repo_name)
            clone_repo_and_cd_inside(user_repo, target_repo_org)
        else:
            user_repo = self._fork_gracefully(target_repo_gh)

            clone_repo_and_cd_inside(user_repo, target_repo_org)

            set_upstream_remote(target_repo_gh.clone_url, target_repo_gh.ssh_url)
        set_origin_remote(user_repo.ssh_url)
        fetch_all()

    def _fork_gracefully(self, target_repo):
        """ fork if not forked, return forked repo """
        try:
            target_repo.full_name
        except github.GithubException.UnknownObjectException:
            logger.error("repository doesn't exist")
            raise RuntimeError("repo %s not found" % target_repo)
        logger.info("forking repo %s", target_repo)
        return self.user.create_fork(target_repo)


