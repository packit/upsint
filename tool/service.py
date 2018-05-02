class Service:
    def __init__(self, token=None):
        self.token = token

    @classmethod
    def create_from_remote_url(cls, remote_url):
        """ create instance of service from provided remote_url """
        pass

    def fork(self, target_repo):
        pass

    def create_pull_request(self, target_remote, target_branch, current_branch):
        pass

    def list_pull_requests(self):
        pass
