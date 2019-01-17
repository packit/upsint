import json
import os


class Conf:
    def __init__(self):
        self._c = None

    @property
    def c(self):
        if self._c is None:
            with open(os.path.expanduser("~/.tool.json")) as fd:
                self._c = json.load(fd)
        return self._c

    def get_github_configuration(self):
        # TODO: implement proper validation
        return self.c["github"]

    def get_gitlab_configuration(self):
        # TODO: implement proper validation
        return self.c["gitlab"]
