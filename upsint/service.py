class Service:
    def __init__(self, token=None):
        self.token = token

    @classmethod
    def create_from_remote_url(cls, remote_url):
        """ create instance of service from provided remote_url """
        raise NotImplementedError()

    def fork(self, target_repo):
        raise NotImplementedError()

    def create_pull_request(self, target_remote, target_branch, current_branch):
        raise NotImplementedError()

    def list_pull_requests(self):
        raise NotImplementedError()
