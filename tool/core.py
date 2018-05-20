from tool.conf import Conf
from tool.services.github_service import GithubService
from tool.services.gitlab_service import GitlabService
from tool.utils import get_current_branch_name, get_remote_url


class App:
    def __init__(self):
        self.conf = Conf()

    def get_service(self, service_name, repo=None):
        map = {
            "github": GithubService
        }
        if service_name.startswith("gitlab"):
            ServiceClass = GitlabService
        else:
            ServiceClass = map[service_name]
        configuration = self.conf.c[service_name]
        configuration["full_repo_name"] = repo
        return ServiceClass(**configuration)

    # TODO: change to remote=None and iterate over all remotes
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
