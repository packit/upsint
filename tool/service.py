class Service:
    def __init__(self, token=None, repo_name=None, url=None, remote_url=None):
        """
        :param token: secret API key
        :param repo_name: name of the repository
        :param url: url to the service instance
        :param remote_url: url to the remote set in the git repo
        """
        self.token = token
        self.url = url
        self.repo_name = repo_name
        self.remote_url = remote_url

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
