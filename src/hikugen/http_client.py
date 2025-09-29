# ABOUTME: HTTP client utilities for fetching web pages with cookie support
# ABOUTME: Provides web scraping HTTP functionality with consistent headers and error handling

import json
import requests
from http.cookiejar import MozillaCookieJar
from pathlib import Path
from typing import Optional


def _load_cookies(cookie_file_path: Optional[str]) -> Optional[MozillaCookieJar]:
    """Load cookies from Netscape cookies.txt file.

    Args:
        cookie_file_path: Path to cookies.txt file

    Returns:
        MozillaCookieJar instance or None if file doesn't exist/is invalid
    """
    if not cookie_file_path:
        return None

    cookie_path = Path(cookie_file_path)
    if not cookie_path.exists():
        return None

    try:
        jar = MozillaCookieJar(cookie_path)
        jar.load(ignore_discard=True, ignore_expires=True)
        return jar
    except Exception:
        return None


def fetch_page_content(
    url: str, cookies_path: Optional[str] = None, timeout: int = 10
) -> str:
    """Fetch content from URL with optional cookie support.

    Args:
        url: URL to fetch content from
        cookies_path: Optional path to Netscape cookies.txt file
        timeout: Request timeout in seconds (default: 10)

    Returns:
        Response text content

    Raises:
        ValueError: If URL is empty
        requests.exceptions.*: Various request-related errors
    """
    if not url:
        raise ValueError("URL cannot be empty")

    # Load cookies if provided
    cookies = _load_cookies(cookies_path)

    # Firefox browser headers
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:141.0) Gecko/20100101 Firefox/141.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Priority": "u=0, i",
        "TE": "trailers",
    }

    response = requests.get(url, timeout=timeout, cookies=cookies, headers=headers)
    response.raise_for_status()
    return response.text


def call_openrouter_api(
    api_key: str, model: str, messages: list, timeout: int = 300
) -> str:
    """Make API call to OpenRouter.

    Args:
        api_key: OpenRouter API key
        model: Model name (e.g. "google/gemini-2.5-flash")
        messages: List of message dicts with role and content
        timeout: Request timeout in seconds

    Returns:
        Response content from API

    Raises:
        requests.exceptions.HTTPError: If API returns error status
        requests.exceptions.Timeout: If request times out
    """
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    data = {"model": model, "messages": messages, "transforms": ["middle-out"]}

    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers=headers,
        data=json.dumps(data),
        timeout=timeout,
    )

    response.raise_for_status()
    response_data = response.json()
    return response_data["choices"][0]["message"]["content"]
