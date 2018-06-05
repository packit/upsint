"""
Sample config:
{
    "instances": [
        {
            url: "...",
            name: "...",  # to reference in CLI
            service: "..."  # which class we should pair this with
            token: "..."
        },

    ]
}
"""
import json
import os
from urllib.parse import urlsplit

from tool.services import GithubService, GitlabService


default_config = {
    "push_when_creating_pr": True,
    "instances": [
        {
            "name": "github",
            "service": "github"
        },
        {
            "name": "gitlab",
            "service": "gitlab",
            "url": "https://gitlab.com"
        }
    ]
}


class ConfigurationErrorException(Exception):
    """ There was an error during processing configuration. """


class ServiceConfiguration:
    """ logic for configuration of a service """
    service = None

    def __init__(self, d):
        """
        :param d: dict, configuration of a service obtained from a config file
        """
        self.d = d

    def can_handle(self, remote_url):
        """ given the remote URL, is this the service which can handle the provided repo? """
        raise NotImplementedError("method can_handle is not implemented")


class GithubServiceConfiguration(ServiceConfiguration):
    service = GithubService

    def is_this_the_service(self, remote_url):
        """ given the remote URL, is this the service which can handle the repo? """
        if "github.com" not in remote_url:
            return False
        return True


class GitlabServiceConfiguration(ServiceConfiguration):
    service = GitlabService

    def is_this_the_service(self, remote_url):
        """ given the remote URL, is this the service which can handle the repo? """
        url = self.d["url"]
        url_split_tuple = urlsplit(url)
        remote_split_tuple = urlsplit(remote_url)
        return url_split_tuple[1] == remote_split_tuple[1]


class Conf:
    def __init__(self):
        self._c = None
        self._instances = None

    @property
    def c(self):
        if self._c is None:
            # TODO: raise an exception if not present
            # TODO: add a way to create default configuration
            with open(os.path.expanduser("~/.tool.json")) as fd:
                # TODO: merge with default config
                self._c = json.load(fd)
        return self._c

    # helper methods to access configuration

    def get_service_configurations(self):
        """ provide a list of instances of *ServiceConf """
        service_configurations = {
            GithubServiceConfiguration.service.name: GithubServiceConfiguration,
            GitlabServiceConfiguration.service.name: GitlabServiceConfiguration,
        }
        services = self._c["instances"]
        # TODO: do json schema
        if not isinstance(services, list):
            raise ConfigurationErrorException(
                "instances should be a list, not %s" % services.__class__)
        return services

    def get_push_when_creating_pr(self):
        val = self.c["push_when_creating_pr"]
        # TODO: do json schema
        if not isinstance(val, bool):
            raise ConfigurationErrorException(
                "push_when_creating_pr should be bool, not %s" % val.__class__)
        return val
