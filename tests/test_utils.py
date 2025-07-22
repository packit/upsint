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
import requests
import github

from upsint.utils import validate_github_token_permissions


class TestTokenValidation:
    """Test GitHub token validation functionality"""
    
    def test_validate_github_token_permissions_success(self):
        """Test successful token validation"""
        mock_client = Mock()
        mock_rate_limit = Mock()
        mock_rate_limit.core.remaining = 500
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.reset.timestamp.return_value = 1234567890
        
        mock_repo = Mock()
        mock_repo.permissions.push = True
        mock_repo.permissions.pull = True
        
        mock_client.get_rate_limit.return_value = mock_rate_limit
        mock_client.get_repo.return_value = mock_repo
        
        result = validate_github_token_permissions(mock_client, "owner/repo")
        
        assert result['valid'] is True
        assert result['permissions']['repo_access'] is True
        assert result['permissions']['can_push'] is True
        assert result['permissions']['can_create_pr'] is True
        assert result['rate_limit']['remaining'] == 500
        assert len(result['issues']) == 0
    
    def test_validate_github_token_low_rate_limit(self):
        """Test validation with low rate limit"""
        mock_client = Mock()
        mock_rate_limit = Mock()
        mock_rate_limit.core.remaining = 5  # Low rate limit
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.reset.timestamp.return_value = 1234567890
        
        mock_repo = Mock()
        mock_repo.permissions.push = True
        mock_repo.permissions.pull = True
        
        mock_client.get_rate_limit.return_value = mock_rate_limit
        mock_client.get_repo.return_value = mock_repo
        
        result = validate_github_token_permissions(mock_client, "owner/repo")
        
        assert result['valid'] is True
        assert len(result['issues']) == 1
        assert "Low rate limit remaining" in result['issues'][0]
    
    def test_validate_github_token_no_permissions(self):
        """Test validation when token lacks permissions"""
        mock_client = Mock()
        mock_rate_limit = Mock()
        mock_rate_limit.core.remaining = 500
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.reset.timestamp.return_value = 1234567890
        
        mock_repo = Mock()
        mock_repo.permissions.push = False
        mock_repo.permissions.pull = False
        
        mock_client.get_rate_limit.return_value = mock_rate_limit
        mock_client.get_repo.return_value = mock_repo
        
        result = validate_github_token_permissions(mock_client, "owner/repo")
        
        assert result['valid'] is False
        assert result['permissions']['can_create_pr'] is False
        assert "doesn't have permission to create pull requests" in result['issues'][0]
    
    def test_validate_github_token_repo_not_found(self):
        """Test validation when repository is not found"""
        mock_client = Mock()
        mock_rate_limit = Mock()
        mock_rate_limit.core.remaining = 500
        mock_rate_limit.core.limit = 5000
        mock_rate_limit.core.reset.timestamp.return_value = 1234567890
        
        mock_client.get_rate_limit.return_value = mock_rate_limit
        mock_client.get_repo.side_effect = github.UnknownObjectException(status=404, data={})
        
        result = validate_github_token_permissions(mock_client, "owner/repo")
        
        assert result['valid'] is False
        assert result['permissions']['repo_access'] is False
        assert "not found or not accessible" in result['issues'][0]
    
    def test_validate_github_token_bad_credentials(self):
        """Test validation with bad credentials"""
        mock_client = Mock()
        mock_client.get_rate_limit.side_effect = github.BadCredentialsException(status=401, data={})
        
        result = validate_github_token_permissions(mock_client, "owner/repo")
        
        assert result['valid'] is False
        assert "token is invalid or expired" in result['issues'][0]
    
    def test_validate_github_token_unexpected_error(self):
        """Test validation with unexpected error"""
        mock_client = Mock()
        mock_client.get_rate_limit.side_effect = Exception("Unexpected error")
        
        result = validate_github_token_permissions(mock_client, "owner/repo")
        
        assert result['valid'] is False
        assert "Unexpected error during validation" in result['issues'][0]