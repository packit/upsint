from tool.conf import Conf, GitlabServiceConfiguration, GithubServiceConfiguration
from tool.services import GithubService, GitlabService
from tool.utils import get_current_branch_name, get_remote_url, list_local_branches


service_classes = {
    GithubService.name: GithubService,
    GitlabService.name: GitlabService,
}


def get_from_service_or_raise(d, key, service_name):
    try:
        return d[key]
    except KeyError:
        raise RuntimeError(
            "No value %s specified in service %s" % (key, service_name))


class App:
    def __init__(self):
        self.conf = Conf()

    def get_service(self, service_name, repo=None):
        """ provide instance of selected service """
        services = self.conf.get_services_list()

        # find the particular service
        # FIXME: handle len(...) == 0
        the_service_dict = [x for x in services if x["name"] == service_name][0]
        token = get_from_service_or_raise(the_service_dict, "token", service_name)
        service_id = get_from_service_or_raise(the_service_dict, "service", service_name)
        try:
            service_kls = service_classes[service_id]
        except KeyError:
            raise RuntimeError("No such service: %s" % service_name)
        data = {
            "token": token,
            "repo_name": repo,
        }
        url = the_service_dict.get("url")
        if url:
            data["url"] = url
        service_instance = service_kls(**data)

        return service_instance

    # TODO: change to remote=None and iterate over all remotes fallback to upstream and origin
    def guess_service(self, remote="upstream"):
        remote, remote_url = get_remote_url(remote)
        for k in service_conf_classes:
            i = k.is_this_the_service(remote_url)
            if i:
                return self.get_service(i.name)

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
