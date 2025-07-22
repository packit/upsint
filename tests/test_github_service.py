# -*- coding: utf-8 -*-
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from unittest.mock import Mock, patch

from upsint.services.github_service import GithubService, get_github_full_name


class TestGithubFullName:
    """Test GitHub URL parsing functionality"""
    
    def test_get_github_full_name_https(self):
        """Test parsing HTTPS GitHub URLs"""
        url = "https://github.com/owner/repo.git"
        result = get_github_full_name(url)
        assert result == "owner/repo"
    
    def test_get_github_full_name_ssh(self):
        """Test parsing SSH GitHub URLs"""
        url = "git@github.com:owner/repo.git"
        result = get_github_full_name(url)
        assert result == "owner/repo"
    
    def test_get_github_full_name_no_git_suffix(self):
        """Test parsing GitHub URLs without .git suffix"""
        url = "https://github.com/owner/repo"
        result = get_github_full_name(url)
        assert result == "owner/repo"
    
    def test_get_github_full_name_complex_prefix(self):
        """Test parsing with complex URL prefix"""
        url = "https://user:token@github.com/owner/repo.git"
        result = get_github_full_name(url)
        assert result == "owner/repo"


class TestGithubServiceInit:
    """Test GithubService initialization"""
    
    @patch('upsint.services.github_service.github.Github')
    def test_init_without_repo(self, mock_github):
        """Test initialization without specifying a repository"""
        mock_github_instance = Mock()
        mock_user = Mock()
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_user.return_value = mock_user
        
        service = GithubService(token="test_token")
        
        assert service.token == "test_token"
        assert service.g == mock_github_instance
        assert service.user == mock_user
        assert service.repo is None
        mock_github.assert_called_once_with(login_or_token="test_token")
    
    @patch('upsint.services.github_service.github.Github')
    def test_init_with_repo(self, mock_github):
        """Test initialization with a specific repository"""
        mock_github_instance = Mock()
        mock_user = Mock()
        mock_repo = Mock()
        
        mock_github.return_value = mock_github_instance
        mock_github_instance.get_user.return_value = mock_user
        mock_github_instance.get_repo.return_value = mock_repo
        
        service = GithubService(token="test_token", full_repo_name="owner/repo")
        
        assert service.repo == mock_repo
        mock_github_instance.get_repo.assert_called_once_with("owner/repo")
