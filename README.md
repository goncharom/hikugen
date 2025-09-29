# Hikugen - minimalistic AI-powered web scraping

[![PyPI](https://img.shields.io/pypi/v/hikugen?style=flat-square&logo=pypi)](https://pypi.org/project/hikugen/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

AI-powered web scraping library that generates Python code to extract structured data into Pydantic-compliant objects.

## Overview

Hikugen uses LLMs (via OpenRouter) to generate extraction code for any website. Given a URL and a Pydantic schema, Hikugen:

1. Generates extraction code via LLM
2. Validates code (AST-based, whitelist imports)
3. Executes with timeout protection
4. Validates extracted data against your schema
5. Caches generated code for reuse

No manual parsing code needed, just define your schema, and Hikugen handles the rest.

## Quick Start

### Installation

```bash
uv add hikugen
```

### Basic Usage

```python
from hikugen import HikuExtractor
from pydantic import BaseModel, Field
from typing import List

# Define nested extraction schema
class Article(BaseModel):
    title: str = Field(description="Article title")
    author: str = Field(description="Author name")
    published_date: str = Field(description="Publication date")
    content: str = Field(description="Article body content")

class ArticlePage(BaseModel):
    articles: List[Article] = Field(description="List of articles on the page")

# Initialize extractor
extractor = HikuExtractor(
    api_key="your-openrouter-api-key",
    model="google/gemini-2.5-flash"  # Optional, this is default
)

# Extract data from a URL
result = extractor.extract(
    url="https://example.com/articles",
    schema=ArticlePage,
    cache_key="articles-page"  # Optional: custom cache key
)

for article in result.articles:
    print(f"{article.title} by {article.author}")
```

### Working with Pre-fetched HTML

```python
# Extract from HTML you already have
html_content = """
<div class="articles">
    <article>
        <h2>First Article</h2>
        <span class="author">Jane Smith</span>
        <time>2024-01-15</time>
        <p>Article content here...</p>
    </article>
    <article>
        <h2>Second Article</h2>
        <span class="author">John Doe</span>
        <time>2024-01-14</time>
        <p>More article content...</p>
    </article>
</div>
"""

result = extractor.extract_from_html(
    html_content=html_content,
    cache_key="articles-page",  # Unique identifier for caching
    schema=ArticlePage
)

for article in result.articles:
    print(f"{article.title} by {article.author}")
```

### Cache Management

Clear cached extraction code when page structures change or during testing:

```python
# Clear cache for a specific URL or task
count = extractor.clear_cache_for_key("https://example.com/articles")
print(f"Deleted {count} cache entries")

# Clear all cached extraction code
total = extractor.clear_all_cache()
print(f"Deleted {total} total cache entries")
```

Use `clear_cache_for_key()` when page structure changes, or `clear_all_cache()` during development to reset cache state.

## See Also

- [CLAUDE.md](./CLAUDE.md) - Development guide for AI contributors

## License

See LICENSE file for details.
