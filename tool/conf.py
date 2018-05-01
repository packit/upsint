import json


class Conf:
    def __init__(self):
        self._c = None

    @property
    def c(self):
        if self._c is None:
            with open("tool.json") as fd:
                self._c = json.load(fd)
        return self._c

    def get_github_configuration(self):
        return self.c["github"]