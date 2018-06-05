import logging

import gitlab
from tool.service import Service
from tool.utils import (clone_repo_and_cd_inside, fetch_all, set_origin_remote,
                        set_upstream_remote)

logger = logging.getLogger(__name__)


class GitlabService(Service):
    name = "gitlab"

    def __init__(self, token=None, repo_name=None, url=None, remote_url=None):
        super().__init__(token=token, repo_name=repo_name, url=url, remote_url=remote_url)
        self.g = gitlab.Gitlab(url=self.url, private_token=self.token)
        self.g.auth()
        self.user = self.g.users.list(username=self.g.user.username)[0]
        self.repo = None
        if self.repo_name:
            self.repo = self.g.projects.get(self.repo_name)

    @classmethod
    def is_this_the_service(cls, remote_url):
        """ given the remote URL, is this the service which can handle the repo? """
        if "gitlab.com" not in remote_url:
            return False
        return True

    @classmethod
    def create_from_remote_url(cls, remote_url, **kwargs):
        """ create instance of service from provided remote_url """
        pass

    def _is_fork_of(self, user_repo, target_repo):
        """ is provided repo fork of the {parent_repo}/? """
        return user_repo.forked_from_project['id'] == target_repo.id

    def fork(self, target_repo):
        target_repo_org, target_repo_name = target_repo.split("/", 1)

        target_repo_gl = self.g.projects.get(target_repo)

        try:
            # is it already forked?
            user_repo = self.g.projects.get("{}/{}".format(self.user.username, target_repo_name))
            if not self._is_fork_of(user_repo, target_repo_gl):
                raise RuntimeError("repo %s is not a fork of %s" % (target_repo_gl, user_repo))
        except Exception as ex:
            # nope
            user_repo = None

        if self.user.username == target_repo_org:
            # user wants to fork its own repo; let's just set up remotes 'n stuff
            if not user_repo:
                raise RuntimeError("repo %s not found" % target_repo_name)
            clone_repo_and_cd_inside(user_repo.path, user_repo.attributes['ssh_url_to_repo'], target_repo_org)
        else:
            user_repo = user_repo or self._fork_gracefully(target_repo_gl)

            clone_repo_and_cd_inside(user_repo.path, user_repo.attributes['ssh_url_to_repo'], target_repo_org)

            set_upstream_remote(clone_url=target_repo_gl.attributes['http_url_to_repo'],
                                ssh_url=target_repo_gl.attributes['ssh_url_to_repo'],
                                pull_merge_name="merge-requests")
        set_origin_remote(user_repo.attributes['ssh_url_to_repo'],
                          pull_merge_name="merge-requests")
        fetch_all()

    def _fork_gracefully(self, target_repo):
        """ fork if not forked, return forked repo """
        try:
            logger.info("forking repo %s", target_repo)
            fork = target_repo.forks.create({})
        except gitlab.GitlabCreateError as ex:
            logger.error("repo %s cannot be forked" % target_repo)
            raise RuntimeError("repo %s not found" % target_repo)

        return fork

    def create_pull_request(self, target_remote, target_branch, current_branch):
        raise NotImplementedError("Creating PRs for GitLab is not implemented yet.")
