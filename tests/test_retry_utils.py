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

import pytest
from unittest.mock import Mock, patch
import requests
import github

from upsint.retry_utils import (
    is_rate_limit_error,
    is_retriable_error,
    calculate_backoff_delay,
    retry_on_github_errors,
    validate_github_token_permissions,
    GitHubAPIError,
    RateLimitExceeded,
    _wrap_github_exception,
    _handle_rate_limit_error
)


class TestErrorDetection:
    """Test error detection functions"""
    
    def test_is_rate_limit_error_with_rate_limit_exception(self):
        """Test detection of GitHub rate limit exception"""
        exception = github.RateLimitExceededException(status=403, data={})
        assert is_rate_limit_error(exception) is True
    
    def test_is_rate_limit_error_with_http_403(self):
        """Test detection of HTTP 403 error"""
        response = Mock()
        response.status_code = 403
        exception = requests.exceptions.HTTPError()
        exception.response = response
        assert is_rate_limit_error(exception) is True
    
    def test_is_rate_limit_error_with_retry_error_403(self):
        """Test detection of RetryError with 403 status"""
        exception = requests.exceptions.RetryError("403 error responses")
        assert is_rate_limit_error(exception) is True
    
    def test_is_rate_limit_error_false_cases(self):
        """Test cases that should not be detected as rate limit errors"""
        # Regular exception
        assert is_rate_limit_error(Exception("test")) is False
        
        # HTTP 404 error
        response = Mock()
        response.status_code = 404
        http_error = requests.exceptions.HTTPError()
        http_error.response = response
        assert is_rate_limit_error(http_error) is False
        
        # RetryError without 403
        retry_error = requests.exceptions.RetryError("500 error responses")
        assert is_rate_limit_error(retry_error) is False
    
    def test_is_retriable_error_rate_limits(self):
        """Test that rate limit errors are retriable"""
        exception = github.RateLimitExceededException(status=403, data={})
        assert is_retriable_error(exception) is True
    
    def test_is_retriable_error_connection_errors(self):
        """Test that connection errors are retriable"""
        assert is_retriable_error(requests.exceptions.ConnectionError()) is True
        assert is_retriable_error(requests.exceptions.Timeout()) is True
        assert is_retriable_error(requests.exceptions.RetryError("test")) is True
    
    def test_is_retriable_error_github_server_errors(self):
        """Test that GitHub server errors are retriable"""
        exception = github.GithubException(status=500, data={})
        assert is_retriable_error(exception) is True
        
        exception_502 = github.GithubException(status=502, data={})
        assert is_retriable_error(exception_502) is True
    
    def test_is_retriable_error_github_403_retriable(self):
        """Test that GitHub 403 errors are retriable"""
        exception = github.GithubException(status=403, data={})
        assert is_retriable_error(exception) is True
    
    def test_is_retriable_error_non_retriable_cases(self):
        """Test cases that should not be retriable"""
        # GitHub 404 error
        exception_404 = github.GithubException(status=404, data={})
        assert is_retriable_error(exception_404) is False
        
        # GitHub 401 error
        exception_401 = github.GithubException(status=401, data={})
        assert is_retriable_error(exception_401) is False
        
        # Regular exception
        assert is_retriable_error(ValueError("test")) is False


class TestBackoffCalculation:
    """Test backoff delay calculation"""
    
    def test_calculate_backoff_delay_exponential(self):
        """Test exponential backoff calculation"""
        # First attempt (attempt=1) should be base_delay
        assert calculate_backoff_delay(1, base_delay=2.0, jitter=False) == 2.0
        
        # Second attempt should be base_delay * 2
        assert calculate_backoff_delay(2, base_delay=2.0, jitter=False) == 4.0
        
        # Third attempt should be base_delay * 4
        assert calculate_backoff_delay(3, base_delay=2.0, jitter=False) == 8.0
    
    def test_calculate_backoff_delay_max_limit(self):
        """Test that delay respects maximum limit"""
        # Large attempt number should cap at max_delay
        delay = calculate_backoff_delay(10, base_delay=1.0, max_delay=10.0, jitter=False)
        assert delay == 10.0
    
    def test_calculate_backoff_delay_minimum(self):
        """Test minimum delay is enforced"""
        # Even with small base_delay and negative jitter, minimum should be 0.1
        with patch('random.uniform', return_value=-1.0):  # Force negative jitter
            delay = calculate_backoff_delay(1, base_delay=0.05, jitter=True)
            assert delay >= 0.1
    
    def test_calculate_backoff_delay_with_jitter(self):
        """Test that jitter adds randomness"""
        with patch('random.uniform', return_value=0.5):  # Fixed jitter
            base_delay = 4.0
            expected_jitter = base_delay * 0.25 * 0.5  # 25% of delay * jitter factor
            delay = calculate_backoff_delay(2, base_delay=2.0, jitter=True)
            assert delay == 4.0 + expected_jitter
    
    def test_calculate_backoff_delay_no_jitter(self):
        """Test calculation without jitter"""
        delay = calculate_backoff_delay(2, base_delay=2.0, jitter=False)
        assert delay == 4.0


class TestRetryDecorator:
    """Test the retry decorator functionality"""
    
    def test_successful_execution_no_retry(self):
        """Test successful function execution without retries"""
        mock_func = Mock(return_value="success")
        
        @retry_on_github_errors(max_retries=3)
        def test_func():
            return mock_func()
        
        result = test_func()
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_retry_on_retriable_error(self):
        """Test retry behavior on retriable errors"""
        mock_func = Mock()
        # First two calls fail, third succeeds
        mock_func.side_effect = [
            requests.exceptions.ConnectionError("Connection failed"),
            requests.exceptions.ConnectionError("Connection failed"),
            "success"
        ]
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            @retry_on_github_errors(max_retries=3, base_delay=0.1)
            def test_func():
                return mock_func()
            
            result = test_func()
            assert result == "success"
            assert mock_func.call_count == 3
    
    def test_max_retries_exceeded(self):
        """Test behavior when max retries are exceeded"""
        mock_func = Mock()
        mock_func.side_effect = requests.exceptions.ConnectionError("Always fails")
        
        with patch('time.sleep'):
            @retry_on_github_errors(max_retries=2, base_delay=0.1)
            def test_func():
                return mock_func()
            
            with pytest.raises(GitHubAPIError):
                test_func()
            
            # Should be called max_retries + 1 times (initial + retries)
            assert mock_func.call_count == 3
    
    def test_non_retriable_error_no_retry(self):
        """Test that non-retriable errors are not retried"""
        mock_func = Mock()
        mock_func.side_effect = ValueError("Non-retriable error")
        
        @retry_on_github_errors(max_retries=3)
        def test_func():
            return mock_func()
        
        with pytest.raises(ValueError):
            test_func()
        
        assert mock_func.call_count == 1
    
    @patch('time.sleep')
    def test_rate_limit_specific_handling(self, mock_sleep):
        """Test specific handling of rate limit errors"""
        mock_func = Mock()
        rate_limit_error = github.RateLimitExceededException(status=403, data={})
        mock_func.side_effect = [rate_limit_error, "success"]
        
        with patch('upsint.retry_utils._handle_rate_limit_error') as mock_handle:
            @retry_on_github_errors(max_retries=2, base_delay=1.0)
            def test_func():
                return mock_func()
            
            result = test_func()
            assert result == "success"
            assert mock_handle.called
    
    def test_preserves_function_metadata(self):
        """Test that decorator preserves function metadata"""
        @retry_on_github_errors(max_retries=1)
        def test_function():
            """Test docstring"""
            return "test"
        
        assert test_function.__name__ == "test_function"
        assert test_function.__doc__ == "Test docstring"


class TestExceptionWrapping:
    """Test exception wrapping and error message creation"""
    
    def test_wrap_rate_limit_exception(self):
        """Test wrapping of rate limit exceptions"""
        original = github.RateLimitExceededException(status=403, data={})
        wrapped = _wrap_github_exception(original)
        
        assert isinstance(wrapped, RateLimitExceeded)
        assert "rate limit exceeded" in str(wrapped).lower()
        assert "Solutions:" in str(wrapped)
    
    def test_wrap_connection_error(self):
        """Test wrapping of connection errors"""
        original = requests.exceptions.ConnectionError("Connection failed")
        wrapped = _wrap_github_exception(original)
        
        assert isinstance(wrapped, GitHubAPIError)
        assert "Failed to connect to GitHub API" in str(wrapped)
        assert "internet connection" in str(wrapped)
    
    def test_wrap_retry_error(self):
        """Test wrapping of retry errors"""
        original = requests.exceptions.RetryError("Multiple retries failed")
        wrapped = _wrap_github_exception(original)
        
        assert isinstance(wrapped, GitHubAPIError)
        assert "failed after multiple retries" in str(wrapped)
    
    def test_wrap_github_401(self):
        """Test wrapping of GitHub authentication errors"""
        original = github.GithubException(status=401, data={})
        wrapped = _wrap_github_exception(original)
        
        assert isinstance(wrapped, GitHubAPIError)
        assert "authentication failed" in str(wrapped).lower()
        assert "token is correctly set" in str(wrapped)
    
    def test_wrap_github_404(self):
        """Test wrapping of GitHub not found errors"""
        original = github.GithubException(status=404, data={})
        wrapped = _wrap_github_exception(original)
        
        assert isinstance(wrapped, GitHubAPIError)
        assert "resource not found" in str(wrapped).lower()
    
    def test_wrap_unknown_exception(self):
        """Test that unknown exceptions are returned unchanged"""
        original = ValueError("Unknown error")
        wrapped = _wrap_github_exception(original)
        
        assert wrapped is original


class TestRateLimitHandling:
    """Test rate limit specific handling"""
    
    @patch('time.sleep')
    def test_handle_rate_limit_with_reset_time(self, mock_sleep):
        """Test handling rate limit with reset time"""
        current_time = 1000
        reset_time = 1010  # 10 seconds in future
        
        exception = Mock()
        exception.reset_time = reset_time
        
        with patch('time.time', return_value=current_time):
            _handle_rate_limit_error(exception, delay=1.0)
            
            # Should sleep until reset time + 1 second buffer
            mock_sleep.assert_called_once_with(1.0)
    
    @patch('time.sleep')
    def test_handle_rate_limit_without_reset_time(self, mock_sleep):
        """Test handling rate limit without reset time"""
        exception = Mock()
        del exception.reset_time  # No reset_time attribute
        
        _handle_rate_limit_error(exception, delay=5.0)
        
        # Should use provided delay
        mock_sleep.assert_called_once_with(5.0)
    
    @patch('time.sleep')
    def test_handle_rate_limit_past_reset_time(self, mock_sleep):
        """Test handling when reset time is in the past"""
        current_time = 1000
        reset_time = 990  # 10 seconds in past
        
        exception = Mock()
        exception.reset_time = reset_time
        
        with patch('time.time', return_value=current_time):
            _handle_rate_limit_error(exception, delay=5.0)
            
            # Should use provided delay since reset time is past
            mock_sleep.assert_called_once_with(5.0)


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


class TestCustomExceptions:
    """Test custom exception classes"""
    
    def test_github_api_error(self):
        """Test GitHubAPIError exception"""
        error = GitHubAPIError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_rate_limit_exceeded_without_reset_time(self):
        """Test RateLimitExceeded without reset time"""
        error = RateLimitExceeded("Rate limit exceeded")
        assert str(error) == "Rate limit exceeded"
        assert error.reset_time is None
    
    def test_rate_limit_exceeded_with_reset_time(self):
        """Test RateLimitExceeded with reset time"""
        reset_time = 1234567890
        error = RateLimitExceeded("Rate limit exceeded", reset_time=reset_time)
        assert str(error) == "Rate limit exceeded"
        assert error.reset_time == reset_time


# Integration-style tests
class TestRetryIntegration:
    """Integration tests for retry functionality"""
    
    @patch('time.sleep')
    def test_real_world_retry_scenario(self, mock_sleep):
        """Test a realistic retry scenario with multiple error types"""
        call_count = 0
        
        def failing_function():
            nonlocal call_count
            call_count += 1
            
            if call_count == 1:
                raise requests.exceptions.ConnectionError("Network issue")
            elif call_count == 2:
                raise github.RateLimitExceededException(status=403, data={})
            elif call_count == 3:
                raise requests.exceptions.Timeout("Request timeout")
            else:
                return "success"
        
        @retry_on_github_errors(max_retries=5, base_delay=0.1)
        def test_function():
            return failing_function()
        
        result = test_function()
        assert result == "success"
        assert call_count == 4
        assert mock_sleep.call_count >= 3  # Should have slept between attempts