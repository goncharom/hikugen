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

No manual parsing code needed just define your schema, and Hikugen handles the rest.

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

### Parameters

- **url** - URL to extract from
- **schema** - Pydantic BaseModel defining the extraction structure
- **use_cached_code** - Use cached extraction code if available (default: `True`)
- **cookies_path** - Path to cookies.txt for authenticated requests (optional)
- **max_regenerate_attempts** - Max regeneration attempts on failure (default: `1`)
- **validate_quality** - Run LLM quality check on fresh code (default: `True`)

## Key Features

- **LLM-powered extraction** - Automatically generates extraction code via OpenRouter LLMs
- **Security validated** - AST-based validation ensures no dangerous imports or code patterns
- **Intelligent caching** - Generated code cached by URL + schema hash for reuse
- **Auto-regeneration** - Automatically regenerates on extraction failures
- **Quality validation** - Optional LLM quality check for extracted data
- **Timeout protected** - 30-second execution timeout prevents infinite loops
- **Type safe** - Full Pydantic integration for schema validation

## Development

### Running Tests

```bash
# All tests
uv run pytest

# Specific test file
uv run pytest tests/test_code_generator.py

# With coverage
uv run pytest --cov=hikugen --cov-report=term-missing
```

### Code Quality

```bash
# Lint and format
uv run ruff check src/hikugen/
uv run ruff format src/hikugen/

# Run all checks
uv run ruff check src/hikugen/ && uv run ruff format --check src/hiku/
```

## Architecture

### Layered Design

- **Layer 1 (Foundation)** - Database caching and HTTP client
- **Layer 2 (CodeGen)** - Prompts, validation, and generation
- **Layer 3 (Main API)** - HikuExtractor with auto-regeneration and quality validation

### Workflow

```
URL + Schema
    |
Cache Check
    |
[Cache Hit] -> Cached Code
[Cache Miss] -> LLM generates code
    |
AST Validation
    |
Execute with Timeout
    |
Pydantic Validation
    |
LLM Quality Check (optional)
    |
Return Result or Regenerate
```

## Constraints

### Generated Code Requirements

Generated extraction functions must:
- Have exact signature: `def extract_data(html_content):`
- Return a `dict` (validated against schema afterward)
- Only import from allowed modules (stdlib + requests + bs4 + pydantic)
- NOT import system modules (`os`, `subprocess`, `sys`, etc.)

### Execution

- 30-second timeout per extraction
- Runs in isolated namespace
- Returns data as dict (not BaseModel instance)


## See Also

- [CLAUDE.md](./CLAUDE.md) - Development guide for AI contributors

## License

See LICENSE file for details.
