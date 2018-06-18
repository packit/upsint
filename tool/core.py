from tool.conf import Conf
from tool.services.github_service import GithubService
from tool.services.gitlab_service import GitlabService
from tool.utils import get_current_branch_name, get_remote_url, list_local_branches


class App:
    def __init__(self):
        self.conf = Conf()

    def get_service(self, service_name, repo=None):
        service_map = {
            GithubService.name: GithubService,
            GitlabService.name: GitlabService
        }
        _class = service_map[service_name]
        configuration = self.conf.c[service_name]
        configuration["full_repo_name"] = repo
        return _class(**configuration)

    # TODO: change to remote=None and iterate over all remotes fallback to upstream and origin
    def guess_service(self, remote="upstream"):
        service_classes = [
            GithubService
        ]
        remote, remote_url = get_remote_url(remote)
        for k in service_classes:
            i = k.create_from_remote_url(remote_url, **self.conf.c[k.name])
            if i:
                return i

    def get_current_branch(self):
        return get_current_branch_name()

    def list_branches(self):
        """
        provide a list of branches with additional metadata

        :return dict {
            "name": "master",
            "remote_tracking": "origin",  # can be None
        }
        """
        return sorted(list_local_branches(), key=lambda x: x["date"], reverse=True)
