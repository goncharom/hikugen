# ABOUTME: Test suite for OpenRouter API integration
# ABOUTME: Tests API calls, error handling, and response parsing for LLM interactions

from unittest.mock import Mock, patch
import pytest
import requests
from hikugen.http_client import call_openrouter_api


class TestCallOpenRouterAPI:
    """Test OpenRouter API client functionality."""

    @patch('hikugen.http_client.requests.post')
    def test_successful_api_call(self, mock_post):
        """Test successful API call returns content from response."""
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {"message": {"content": "Generated code here"}}
            ]
        }
        mock_post.return_value = mock_response

        # Call API
        result = call_openrouter_api(
            api_key="test-key",
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": "test"}],
            timeout=300
        )

        # Verify result
        assert result == "Generated code here"

        # Verify request was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args.kwargs['url'] == "https://openrouter.ai/api/v1/chat/completions"
        assert call_args.kwargs['timeout'] == 300
        assert "Bearer test-key" in call_args.kwargs['headers']['Authorization']

    @patch('hikugen.http_client.requests.post')
    def test_api_authentication_error(self, mock_post):
        """Test API call with invalid API key raises HTTPError."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            call_openrouter_api(
                api_key="invalid-key",
                model="google/gemini-2.5-flash",
                messages=[{"role": "user", "content": "test"}],
                timeout=300
            )

    @patch('hikugen.http_client.requests.post')
    def test_api_server_error(self, mock_post):
        """Test API call with server error raises HTTPError."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Internal Server Error")
        mock_post.return_value = mock_response

        with pytest.raises(requests.exceptions.HTTPError):
            call_openrouter_api(
                api_key="test-key",
                model="google/gemini-2.5-flash",
                messages=[{"role": "user", "content": "test"}],
                timeout=300
            )

    @patch('hikugen.http_client.requests.post')
    def test_api_timeout(self, mock_post):
        """Test API call timeout raises Timeout exception."""
        mock_post.side_effect = requests.exceptions.Timeout("Request timed out")

        with pytest.raises(requests.exceptions.Timeout):
            call_openrouter_api(
                api_key="test-key",
                model="google/gemini-2.5-flash",
                messages=[{"role": "user", "content": "test"}],
                timeout=1
            )

    @patch('hikugen.http_client.requests.post')
    def test_api_message_format(self, mock_post):
        """Test API call sends messages in correct format."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "response"}}]
        }
        mock_post.return_value = mock_response

        messages = [
            {"role": "system", "content": "You are a code generator"},
            {"role": "user", "content": "Generate code"}
        ]

        call_openrouter_api(
            api_key="test-key",
            model="google/gemini-2.5-flash",
            messages=messages,
            timeout=300
        )

        # Verify message structure was sent correctly
        call_args = mock_post.call_args
        import json
        sent_data = json.loads(call_args.kwargs['data'])
        assert sent_data['messages'] == messages
        assert sent_data['model'] == "google/gemini-2.5-flash"

    @patch('hikugen.http_client.requests.post')
    def test_api_custom_timeout(self, mock_post):
        """Test API call respects custom timeout parameter."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "response"}}]
        }
        mock_post.return_value = mock_response

        call_openrouter_api(
            api_key="test-key",
            model="google/gemini-2.5-flash",
            messages=[{"role": "user", "content": "test"}],
            timeout=600
        )

        # Verify custom timeout was used
        call_args = mock_post.call_args
        assert call_args.kwargs['timeout'] == 600
