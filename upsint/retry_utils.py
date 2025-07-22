#!/usr/bin/python3
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
#

import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional, Type, Union

import github
import requests

from upsint.exceptions import UpsintException

logger = logging.getLogger(__name__)


class GitHubAPIError(UpsintException):
    """Custom exception for GitHub API related errors"""
    pass


class RateLimitExceeded(GitHubAPIError):
    """Exception raised when GitHub API rate limit is exceeded"""
    
    def __init__(self, message: str, reset_time: Optional[int] = None):
        super().__init__(message)
        self.reset_time = reset_time


def is_rate_limit_error(exception: Exception) -> bool:
    """Check if the exception is related to rate limiting"""
    if isinstance(exception, github.RateLimitExceededException):
        return True
    
    if isinstance(exception, requests.exceptions.HTTPError):
        if hasattr(exception, 'response') and exception.response.status_code == 403:
            return True
    
    if isinstance(exception, requests.exceptions.RetryError):
        # Check if it's specifically a 403 retry error
        error_msg = str(exception).lower()
        return '403' in error_msg
    
    return False


def is_retriable_error(exception: Exception) -> bool:
    """Check if the exception is retriable"""
    # Rate limiting errors are retriable
    if is_rate_limit_error(exception):
        return True
    
    # Connection errors are retriable
    if isinstance(exception, (
        requests.exceptions.ConnectionError,
        requests.exceptions.Timeout,
        requests.exceptions.RetryError
    )):
        return True
    
    # Some GitHub API errors are retriable
    if isinstance(exception, github.GithubException):
        # Server errors (5xx) are retriable
        if hasattr(exception, 'status') and exception.status >= 500:
            return True
        # Some 403 errors might be temporary
        if hasattr(exception, 'status') and exception.status == 403:
            return True
    
    return False


def calculate_backoff_delay(attempt: int, base_delay: float = 1.0, max_delay: float = 60.0, jitter: bool = True) -> float:
    """Calculate exponential backoff delay with optional jitter"""
    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
    
    if jitter:
        # Add random jitter (±25% of delay)
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)
    
    return max(delay, 0.1)  # Minimum 100ms delay


def retry_on_github_errors(
    max_retries: int = 5,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
):
    """
    Decorator to retry GitHub API calls on retriable errors with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Multiplier for exponential backoff
        jitter: Whether to add random jitter to delays
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        # Last attempt failed, raise the error
                        logger.error(f"All {max_retries} retry attempts failed for {func.__name__}")
                        raise _wrap_github_exception(e)
                    
                    if not is_retriable_error(e):
                        # Not a retriable error, fail immediately
                        logger.error(f"Non-retriable error in {func.__name__}: {e}")
                        raise _wrap_github_exception(e)
                    
                    # Calculate delay for next attempt
                    delay = calculate_backoff_delay(
                        attempt + 1, base_delay, max_delay, jitter
                    )
                    
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    # Handle rate limiting specifically
                    if is_rate_limit_error(e):
                        _handle_rate_limit_error(e, delay)
                    else:
                        time.sleep(delay)
            
            # This should never be reached, but just in case
            raise _wrap_github_exception(last_exception)
        
        return wrapper
    return decorator


def _wrap_github_exception(exception: Exception) -> Exception:
    """Convert various exceptions to our custom exceptions with helpful messages"""
    if is_rate_limit_error(exception):
        reset_time = None
        if isinstance(exception, github.RateLimitExceededException):
            reset_time = getattr(exception, 'reset_time', None)
        
        message = (
            "GitHub API rate limit exceeded. This usually means:\n"
            "1. Your API token has reached its hourly rate limit\n"
            "2. The token might not have sufficient permissions\n"
            "3. There might be network connectivity issues\n\n"
            "Solutions:\n"
            "- Wait for rate limit to reset (usually within an hour)\n"
            "- Check your token has 'repo' or 'public_repo' scope\n"
            "- Verify your token is still valid\n"
            "- Check network connectivity to api.github.com"
        )
        
        if reset_time:
            reset_datetime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(reset_time))
            message += f"\n- Rate limit resets at: {reset_datetime}"
        
        return RateLimitExceeded(message, reset_time)
    
    if isinstance(exception, requests.exceptions.ConnectionError):
        return GitHubAPIError(
            f"Failed to connect to GitHub API: {exception}\n"
            "Please check your internet connection and try again."
        )
    
    if isinstance(exception, requests.exceptions.RetryError):
        return GitHubAPIError(
            f"GitHub API request failed after multiple retries: {exception}\n"
            "This might be a temporary issue. Please try again later."
        )
    
    if isinstance(exception, github.GithubException):
        if hasattr(exception, 'status') and exception.status == 401:
            return GitHubAPIError(
                "GitHub API authentication failed. Please check:\n"
                "1. Your token is correctly set in ~/.upsint.json\n"
                "2. The token is still valid (not expired)\n"
                "3. The token has necessary permissions (repo scope)"
            )
        
        if hasattr(exception, 'status') and exception.status == 404:
            return GitHubAPIError(
                f"GitHub resource not found: {exception}\n"
                "Please check that the repository exists and you have access to it."
            )
    
    # Return original exception if we don't have a specific handler
    return exception


def _handle_rate_limit_error(exception: Exception, delay: float) -> None:
    """Handle rate limit errors specifically"""
    if isinstance(exception, github.RateLimitExceededException):
        reset_time = getattr(exception, 'reset_time', None)
        if reset_time:
            time_until_reset = reset_time - time.time()
            if time_until_reset > 0 and time_until_reset < delay:
                # If rate limit resets sooner than our calculated delay, wait for reset
                logger.info(f"Rate limit resets in {time_until_reset:.0f} seconds, waiting...")
                time.sleep(time_until_reset + 1)  # Add 1 second buffer
                return
    
    # Default to calculated delay
    time.sleep(delay)


def validate_github_token_permissions(github_client: github.Github, repo_full_name: str) -> Dict[str, Any]:
    """
    Validate GitHub token permissions for repository operations
    
    Args:
        github_client: Authenticated GitHub client
        repo_full_name: Repository in format "owner/repo"
    
    Returns:
        Dictionary with validation results
    """
    validation_result = {
        'valid': True,
        'issues': [],
        'permissions': {},
        'rate_limit': {}
    }
    
    try:
        # Check rate limit status
        rate_limit = github_client.get_rate_limit()
        validation_result['rate_limit'] = {
            'remaining': rate_limit.core.remaining,
            'limit': rate_limit.core.limit,
            'reset_time': rate_limit.core.reset.timestamp()
        }
        
        if rate_limit.core.remaining < 10:
            validation_result['issues'].append(
                f"Low rate limit remaining: {rate_limit.core.remaining}/{rate_limit.core.limit}"
            )
        
        # Check if user can access repository
        try:
            repo = github_client.get_repo(repo_full_name)
            validation_result['permissions']['repo_access'] = True
            
            # Check specific permissions
            validation_result['permissions']['can_push'] = repo.permissions.push
            validation_result['permissions']['can_create_pr'] = repo.permissions.push or repo.permissions.pull
            
            if not validation_result['permissions']['can_create_pr']:
                validation_result['issues'].append(
                    "Token doesn't have permission to create pull requests in this repository"
                )
                validation_result['valid'] = False
                
        except github.UnknownObjectException:
            validation_result['issues'].append(f"Repository {repo_full_name} not found or not accessible")
            validation_result['valid'] = False
            validation_result['permissions']['repo_access'] = False
            
    except github.BadCredentialsException:
        validation_result['issues'].append("GitHub token is invalid or expired")
        validation_result['valid'] = False
        
    except Exception as e:
        validation_result['issues'].append(f"Unexpected error during validation: {e}")
        validation_result['valid'] = False
    
    return validation_result