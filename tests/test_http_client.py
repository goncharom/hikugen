# ABOUTME: Test suite for Hiku HTTP client functionality
# ABOUTME: Tests web page fetching, cookie support, timeout handling, and error conditions

import pytest
import requests
from unittest.mock import Mock, patch
from pathlib import Path
from hikugen.http_client import fetch_page_content, _load_cookies


class TestCookieLoading:
    """Test cookie loading from Netscape cookies.txt format."""

    def test_load_cookies_success(self):
        """Test successful cookie loading from valid cookies.txt file."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('hikugen.http_client.MozillaCookieJar') as mock_jar:
                mock_jar_instance = Mock()
                mock_jar.return_value = mock_jar_instance

                result = _load_cookies("/path/to/cookies.txt")

                assert result == mock_jar_instance
                mock_jar.assert_called_once_with(Path("/path/to/cookies.txt"))
                mock_jar_instance.load.assert_called_once_with(ignore_discard=True, ignore_expires=True)

    def test_load_cookies_file_not_exist(self):
        """Test cookie loading when file doesn't exist."""
        with patch('pathlib.Path.exists', return_value=False):
            result = _load_cookies("/nonexistent/cookies.txt")
            assert result is None

    def test_load_cookies_empty_path(self):
        """Test cookie loading with empty path."""
        result = _load_cookies("")
        assert result is None

        result = _load_cookies(None)
        assert result is None

    def test_load_cookies_invalid_file(self):
        """Test cookie loading with invalid cookie file."""
        with patch('pathlib.Path.exists', return_value=True):
            with patch('hikugen.http_client.MozillaCookieJar') as mock_jar:
                mock_jar_instance = Mock()
                mock_jar_instance.load.side_effect = Exception("Invalid cookie file")
                mock_jar.return_value = mock_jar_instance

                result = _load_cookies("/path/to/invalid_cookies.txt")
                assert result is None


class TestPageFetching:
    """Test web page content fetching."""

    @patch('hikugen.http_client._load_cookies')
    @patch('requests.get')
    def test_fetch_page_success(self, mock_get, mock_load_cookies):
        """Test successful page fetching."""
        # Setup mocks
        mock_response = Mock()
        mock_response.text = "<html><body>Test content</body></html>"
        mock_get.return_value = mock_response
        mock_load_cookies.return_value = None

        result = fetch_page_content("https://httpbin.org/html")

        assert result == "<html><body>Test content</body></html>"
        mock_get.assert_called_once()
        mock_response.raise_for_status.assert_called_once()

    def test_fetch_page_empty_url(self):
        """Test error handling for empty URL."""
        with pytest.raises(ValueError, match="URL cannot be empty"):
            fetch_page_content("")

        with pytest.raises(ValueError, match="URL cannot be empty"):
            fetch_page_content(None)

    @patch('hikugen.http_client._load_cookies')
    @patch('requests.get')
    def test_fetch_page_with_cookies(self, mock_get, mock_load_cookies):
        """Test page fetching with cookie support."""
        # Setup mocks
        mock_response = Mock()
        mock_response.text = "Content with auth"
        mock_get.return_value = mock_response

        mock_cookies = Mock()
        mock_load_cookies.return_value = mock_cookies

        result = fetch_page_content("https://httpbin.org/cookies", cookies_path="/path/to/cookies.txt")

        assert result == "Content with auth"
        mock_load_cookies.assert_called_once_with("/path/to/cookies.txt")

        # Check that cookies were passed to requests.get
        call_args = mock_get.call_args
        assert call_args[1]['cookies'] == mock_cookies

    @patch('hikugen.http_client._load_cookies')
    @patch('requests.get')
    def test_fetch_page_firefox_headers(self, mock_get, mock_load_cookies):
        """Test that Firefox headers are included in requests."""
        mock_response = Mock()
        mock_response.text = "content"
        mock_get.return_value = mock_response
        mock_load_cookies.return_value = None

        fetch_page_content("https://httpbin.org/headers")

        call_args = mock_get.call_args
        headers = call_args[1]['headers']

        # Check key Firefox headers
        assert "Mozilla/5.0" in headers["User-Agent"]
        assert "Firefox" in headers["User-Agent"]
        assert headers["Accept"] == "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        assert headers["Accept-Language"] == "en-US,en;q=0.5"

    @patch('hikugen.http_client._load_cookies')
    @patch('requests.get')
    def test_fetch_page_timeout(self, mock_get, mock_load_cookies):
        """Test timeout parameter is passed correctly."""
        mock_response = Mock()
        mock_response.text = "content"
        mock_get.return_value = mock_response
        mock_load_cookies.return_value = None

        fetch_page_content("https://httpbin.org/delay/1", timeout=5)

        call_args = mock_get.call_args
        assert call_args[1]['timeout'] == 5

    @patch('hikugen.http_client._load_cookies')
    @patch('requests.get')
    def test_fetch_page_http_error(self, mock_get, mock_load_cookies):
        """Test HTTP error handling."""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("404 Not Found")
        mock_get.return_value = mock_response
        mock_load_cookies.return_value = None

        with pytest.raises(requests.exceptions.HTTPError):
            fetch_page_content("https://httpbin.org/status/404")

    @patch('hikugen.http_client._load_cookies')
    @patch('requests.get')
    def test_fetch_page_timeout_error(self, mock_get, mock_load_cookies):
        """Test timeout error handling."""
        mock_get.side_effect = requests.exceptions.Timeout("Request timed out")
        mock_load_cookies.return_value = None

        with pytest.raises(requests.exceptions.Timeout):
            fetch_page_content("https://httpbin.org/delay/10", timeout=1)


class TestIntegrationWithHttpbin:
    """Integration tests using httpbin.org for reliable testing."""

    def test_fetch_real_page(self):
        """Test fetching real page from httpbin.org."""
        try:
            result = fetch_page_content("https://httpbin.org/html", timeout=10)
            assert "<html>" in result
            assert "<body>" in result
        except requests.exceptions.RequestException:
            pytest.skip("Network unavailable for integration test")

    def test_fetch_json_endpoint(self):
        """Test fetching JSON data (still returns as text)."""
        try:
            result = fetch_page_content("https://httpbin.org/json", timeout=10)
            assert '"slideshow"' in result  # Part of httpbin's sample JSON
        except requests.exceptions.RequestException:
            pytest.skip("Network unavailable for integration test")