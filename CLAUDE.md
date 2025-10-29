# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hikugen is a Python library that uses AI (via OpenRouter LLMs) to generate code for web scraping, extracting data into Pydantic schemas. The architecture is inspired by the IMA project but adapted for generic web extraction rather than RSS-specific extraction.

**Core Concept**: Given a URL, HTML content, and a Pydantic schema, Hikugen generates Python code that extracts structured data from the HTML into the specified schema. Generated code is cached in SQLite for reuse.

## Development Commands

### Running Tests
```bash
# Run all tests
uv run pytest

# Run all tests with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_code_generator.py

# Run a specific test class
uv run pytest tests/test_code_generator.py::TestHikuCodeGenerator

# Run a specific test
uv run pytest tests/test_code_generator.py::TestHikuCodeGenerator::test_init_with_api_key

# Run tests and show coverage
uv run pytest --cov=hikugen --cov-report=term-missing
```

### Code Quality
```bash
# Check code with ruff linter
uv run ruff check src/hikugen/

# Auto-fix ruff issues
uv run ruff check --fix src/hikugen/

# Format code with ruff
uv run ruff format src/hikugen/

# Check formatting without making changes
uv run ruff format --check src/hikugen/

# Run all checks (lint + format)
uv run ruff check src/hikugen/ && uv run ruff format --check src/hikugen/
```

## Architecture Overview

### Core Workflow
1. **Input**: URL, HTML content, Pydantic schema
2. **Cache Check**: Query SQLite DB for existing extraction code (keyed by URL + schema hash)
3. **Code Generation**: If cache miss, use LLM (OpenRouter) to generate `extract_data(html_content)` function
4. **Validation**: AST-based validation ensures generated code:
   - Has correct function signature: `def extract_data(html_content)`
   - Only imports allowed modules (stdlib + requests + bs4 + pydantic, NO lxml)
   - Returns Pydantic BaseModel instance
5. **Execution**: Run generated code in isolated environment with 30-second timeout
6. **Cache**: Store successful code for reuse

### Module Architecture

**Layer 1: Foundation**
- `database.py` - SQLite caching with schema hashing (HikuDatabase class)
- `http_client.py` - HTTP fetching with cookie support + OpenRouter API client

**Layer 2: Code Intelligence**
- `prompts.py` - LLM prompt templates for generation/regeneration/quality checking
- `code_validation.py` - AST-based security validation for generated code
- `code_generator.py` - HikuCodeGenerator orchestrates LLM interaction and execution

**Layer 3: Main API**
- `extractor.py` - HikuExtractor provides main `extract()` API with auto-regeneration and quality validation

### Key Design Patterns

**Auto-Regeneration Workflow**:
1. Get code (cached or fresh from LLM)
2. Execute code with timeout protection
3. Pydantic validation (automatic via BaseModel)
4. LLM quality check (conditional - only for fresh/regenerated code)
5. If any step fails: regenerate with error context (configurable max_regenerate_attempts)
6. If succeeds: cache fresh code and return result

**Code Reuse Pattern**:
- `_try_code()` helper method provides single unified execution path for initial, cached, and regenerated code
- Eliminates duplication across execution attempts
- Handles execution, Pydantic validation, and conditional LLM quality checks

**Security by Validation**:
- No `eval()` or `exec()` without prior AST validation
- Whitelist-based import checking
- Threading-based timeout prevents infinite loops
- Generated code runs in isolated namespace

**Cache Key Generation**:
```python
# Schema is serialized with sorted keys for consistent hashing
schema_json = json.dumps(schema.model_json_schema(), sort_keys=True)
# Cache key combines URL with schema JSON
cache_key = (url, schema_json)
```

**Code Execution & Validation**:
- Generated code returns a `dict` (not BaseModel directly)
- Dict is validated via `schema.model_validate(dict)` for type safety
- This approach allows LLM to generate simpler code while maintaining validation

## Critical Constraints

### Import Restrictions
Generated code **MUST NOT** import:
- `lxml` (explicitly forbidden - use BeautifulSoup with html.parser instead)
- System modules: `os`, `subprocess`, `sys`, `importlib`
- Any third-party libraries except: `requests`, `bs4`, `beautifulsoup4`, `pydantic`

### Function Signature
All generated extraction functions MUST have **exact** signature:
```python
def extract_data(html_content):
    # ...
    return {"field1": value1, "field2": value2}  # Returns dict, not BaseModel
```

**Critical Requirements**:
- Parameter MUST be named `html_content` (not `html`, `content`, or `htmlContent`)
- Function MUST return a `dict`, not a BaseModel instance
- Dict is validated via `schema.model_validate(dict)` after execution

## Development Workflow

### TDD Approach
This project follows strict Test-Driven Development:
1. Write failing tests first
2. Implement minimal code to pass tests
3. Refactor while keeping tests green
4. Commit after each step

### File Conventions
- All files start with 2-line `# ABOUTME:` comments explaining the file's purpose
- Use ruff for linting and formatting
- Python 3.11+ required
- No pre-commit hooks configured (per user preference)

## Testing Patterns

### Mock-Based LLM Testing
Use mocks for OpenRouter API calls to avoid real API usage in tests:
```python
@patch('hikugen.code_generator.call_openrouter_api')
def test_code_generation(self, mock_api):
    mock_api.return_value = "```python\ndef extract_data(html_content): ...\n```"
    # Test logic
```

### Timeout Testing
HikuCodeGenerator uses threading for timeout protection:
```python
generator.execution_timeout = 1  # Override for fast tests
with pytest.raises(TimeoutError):
    generator.execute_extraction_code(infinite_loop_code, html, schema)
```

## HikuExtractor API

The main API provides two methods for extraction with auto-regeneration and quality validation:

### `extract()` - Extract from URL

```python
from hikugen.extractor import HikuExtractor
from pydantic import BaseModel

extractor = HikuExtractor(
    api_key="your-openrouter-key",
    model="google/gemini-2.5-flash",  # Optional, this is default
)

result = extractor.extract(
    url="https://example.com/article",
    schema=Article,
    cache_key=None,  # Optional: custom cache key (uses URL if not provided)
    use_cached_code=True,
    cookies_path="/path/to/cookies.txt",  # Optional
    max_regenerate_attempts=1,
    validate_quality=True
)

# Example with custom cache_key for parameterized URLs:
result = extractor.extract(
    url="https://example.com/search?q=power+banks",
    schema=ProductList,
    cache_key="amazon-search"  # Reuse code for all search results
)
```

### `extract_from_html()` - Extract from HTML Content

Use this when you already have HTML (e.g., from a file, custom fetcher, or in-memory document):

```python
html_content = "<html>...</html>"

result = extractor.extract_from_html(
    html_content=html_content,
    cache_key="document-id",  # Unique cache key for caching
    schema=Article,
    use_cached_code=True,
    max_regenerate_attempts=1,
    validate_quality=True
)
```

### Parameters

Common to both methods:
- **schema**: Pydantic BaseModel class defining extraction schema
- **cache_key**: Optional custom cache key for caching generated code (both methods use this)
- **use_cached_code**: Use cached extraction code if available (default: True)
- **max_regenerate_attempts**: Maximum regeneration attempts (default: 1, use 0 to disable)
- **validate_quality**: Run LLM quality check on fresh/regenerated code (default: True, advisory only)

`extract()` specific:
- **url**: URL to extract from
- **cache_key**: Overrides URL as cache key (optional, defaults to URL)
- **cookies_path**: Path to cookies.txt for authenticated requests (optional)

`extract_from_html()` specific:
- **html_content**: HTML content string to extract from
- **cache_key**: Unique identifier for caching (e.g., task name, document ID)

### Return Value

- **Returns**: A single BaseModel instance with extracted data

### Validation Workflow

1. **AST Validation**: Pre-execution validation of generated code structure and imports
2. **Code Execution**: Generated code returns dict via `extract_data(html_content)`
3. **Pydantic Validation**: Dict validated via `schema.model_validate(dict)` - validates types and user-defined validators
4. **LLM Quality Check** (conditional, advisory): Only runs on fresh/regenerated code when `validate_quality=True`
   - Checks for empty required fields, data format issues, schema compliance
   - **Non-blocking**: Failures trigger regeneration but don't block on LLM API errors
   - **Graceful degradation**: LLM API failures are logged as warnings, extraction continues

### Cache Management

Clear cached extraction code when page structures change or during development:

```python
extractor = HikuExtractor(api_key="your-openrouter-key")

# Clear cache for a specific URL or task name
count = extractor.clear_cache_for_key("https://example.com")
print(f"Deleted {count} cache entries")

# Clear all cached extraction code
total = extractor.clear_all_cache()
print(f"Deleted {total} total cache entries")
```

**Methods:**
- **`clear_cache_for_key(cache_key: str) -> int`**: Clear all cached code for a specific cache_key (URL, task name, etc.)
  - Returns number of entries deleted
  - Removes all schema variants for the given cache_key
  - Useful when page structure changes or schema is updated

- **`clear_all_cache() -> int`**: Clear all cached extraction code
  - Returns total number of entries deleted
  - Use during development/testing to reset cache state

**Use cases:**
- Page structure changed: Clear specific URL/task cache to force regeneration
- Schema updated: Clear cache to regenerate code with new schema
- Development: Clear all cache to test full generation workflow
- Debugging: Clear cache to isolate generation logic

## Common Development Tasks

### Adding a New Feature

1. **Identify the layer**: Determine if it's a foundation layer change (database/http_client), code intelligence layer (prompts/validation/generation), or main API change (extractor)
2. **Write tests first**: Add failing tests in the appropriate test file following TDD
3. **Implement minimal code**: Write only what's needed to pass the tests
4. **Update API documentation**: If the change affects the HikuExtractor API, update the docstrings and the API reference section
5. **Commit**: Use conventional detailed commit.

### Debugging Generated Code

When generated extraction code fails:
1. Check `test_extractor.py` and `test_code_generator.py` for existing test patterns
2. Enable logging: Set `logging.getLogger("hiku").setLevel(logging.DEBUG)`
3. Inspect the generated code: It's available in the SQLite cache at `cache_key = (url, schema_json)`
4. Use `code_validation.py` to understand what constraints were validated
5. Regenerate with error context: The `_try_code()` method in HikuExtractor passes error details to the LLM

### Modifying Prompts

Prompts are critical to code generation quality:
- `format_generation_prompt()` - Used for initial code generation
- `format_regeneration_prompt()` - Used when regenerating after failures
- `format_quality_check_prompt()` - Used for LLM quality validation

### Adding Allowed Imports

To allow a new import in generated code:
1. Update the `ALLOWED_IMPORTS` whitelist in `code_validation.py`
2. Add tests to `test_code_validation.py` that verify the import passes validation
3. Update the prompt templates to mention the new import capability
4. Test with manual_test.py to ensure the LLM actually uses it appropriately
