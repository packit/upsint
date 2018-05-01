from tool.conf import Conf
from tool.services.github_service import GithubService


class App:
    def __init__(self):
        self.conf = Conf()

    def get_service(self, service_name):
        map = {
            "github": GithubService
        }
        ServiceClass = map[service_name]
        configuration = self.conf.c[service_name]
        return ServiceClass(**configuration)

