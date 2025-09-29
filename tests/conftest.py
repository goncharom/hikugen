# ABOUTME: Pytest configuration and fixtures for Hiku tests
# ABOUTME: Provides shared test fixtures and configuration for all tests

import pytest
from hikugen.database import HikuDatabase


@pytest.fixture
def temp_db():
    """Create an in-memory database for testing."""
    db = HikuDatabase(":memory:")
    yield db
    db.close()


@pytest.fixture
def mock_openrouter_api_key():
    """Fixture providing mock OpenRouter API key for testing."""
    return "test-openrouter-api-key-12345"


@pytest.fixture
def sample_pydantic_schema():
    """Fixture providing sample Pydantic schema for testing."""
    return """
from pydantic import BaseModel
from typing import List

class ArticleData(BaseModel):
    title: str
    content: str
    author: str
    published_date: str
"""


@pytest.fixture
def sample_extraction_code():
    """Fixture providing sample extraction code for testing."""
    return """
from bs4 import BeautifulSoup
from pydantic import BaseModel
from typing import List

def extract_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    title = soup.find('title').get_text(strip=True) if soup.find('title') else ""
    content = soup.find('div', class_='content').get_text(strip=True) if soup.find('div', class_='content') else ""

    return ArticleData(
        title=title,
        content=content,
        author="Unknown",
        published_date="2023-01-01"
    )
"""