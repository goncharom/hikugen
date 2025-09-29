# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Hikugen is an AI-powered web scraping library that generates Python code to extract structured data into Pydantic-compliant objects. The system uses LLMs (via OpenRouter) to generate custom extraction code for any website, validates it, executes it with safety constraints, and caches generated code for reuse.

## Development Commands

### Setup and Installation
```bash
# Install dependencies using uv
uv sync

# Activate virtual environment
source .venv/bin/activate
```

### Running Tests
```bash
# Run all tests
uv run pytest

# Run tests for a specific module
uv run pytest tests/test_extractor.py

# Run a specific test function
uv run pytest tests/test_extractor.py::test_extract_basic

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=src/hikugen tests/
```

### Code Quality
```bash
# Lint code with ruff
uv run ruff check src/ tests/

# Format code with ruff
uv run ruff format src/ tests/

# Check specific file
uv run ruff check src/hikugen/extractor.py
```

### Building and Distribution
```bash
# Build distribution (wheel and source)
uv build

# Install in development mode
uv pip install -e .
```

## Architecture

### Core Components

1. **HikuExtractor** (`src/hikugen/extractor.py`)
   - Main API entry point for users
   - Orchestrates database caching, code generation, and data extraction
   - Handles both URL-based extraction (`extract()`) and pre-fetched HTML (`extract_from_html()`)
   - Implements retry/regeneration logic with configurable max attempts
   - Manages LLM quality validation of extracted data

2. **HikuCodeGenerator** (`src/hikugen/code_generator.py`)
   - Generates extraction code via OpenRouter LLM API
   - Handles code generation, regeneration (with error feedback), and execution
   - Uses AST-based code validation (whitelist imports)
   - Executes generated code with timeout protection (30 seconds by default)
   - Performs optional LLM-based quality checks on extracted data

3. **HikuDatabase** (`src/hikugen/database.py`)
   - SQLite-based caching for generated extraction code
   - Uses schema_hash (SHA256 of Pydantic schema JSON) + cache_key as composite primary key
   - Enables efficient code reuse across multiple extraction calls
   - Provides `clear_cache_for_key()` and `clear_all_cache()` methods

4. **Code Validation** (`src/hikugen/code_validation.py`)
   - AST-based validation of generated code
   - Whitelist-based import control (only allows BeautifulSoup and safe built-ins)
   - Validates function definitions and return statements

5. **Prompts** (`src/hikugen/prompts.py`)
   - System and user prompt templates for:
     - Initial code generation
     - Code regeneration (with error feedback)
     - Data quality validation
   - Formats Pydantic schemas and HTML content for LLM context

6. **HTTP Client** (`src/hikugen/http_client.py`)
   - Fetches web content with optional cookie/authentication support
   - Calls OpenRouter API for LLM requests
   - Handles connection pooling and timeout management

### Data Flow

1. **Cache Check**: Extract request first checks SQLite cache using (cache_key, schema_hash)
2. **Code Generation**: If cache miss, LLM generates extraction code, validates AST, stores in cache
3. **Execution**: Generated code runs against HTML with timeout protection
4. **Quality Check**: For fresh code, optional LLM validates extracted data against schema
5. **Regeneration**: On failure, error message sent back to LLM for code improvement (up to `max_regenerate_attempts` times)
6. **Result**: Returns Pydantic model instance with extracted data

### Key Design Patterns

- **TDD Approach**: All functionality tested with unit, integration, and end-to-end tests
- **Schema-Driven Caching**: Uses Pydantic schema hash for cache keys, enabling same URL with different schemas to generate different code
- **Safety-First Code Execution**: AST validation + whitelist imports + timeout protection
- **Regeneration Loop**: Automatic code improvement based on LLM error analysis
- **Stateless Design**: Database is the only persistent state; HikuExtractor instances are stateless after initialization

## Testing Structure

Tests are located in `tests/` and configured via `pytest.ini`:

- **Unit Tests**: Test individual components in isolation (code validation, database operations, API calls)
- **Integration Tests**: Test interactions between components (extractor with database, code generator with OpenRouter)
- **End-to-End Tests**: Test full extraction workflows with real HTML content

Key test files:
- `test_extractor.py`: HikuExtractor API and extraction workflows
- `test_code_generator.py`: Code generation, regeneration, and execution
- `test_database.py`: Cache operations and schema handling
- `test_code_validation.py`: AST validation and import whitelisting
- `test_openrouter_api.py`: OpenRouter API integration
- `conftest.py`: Shared fixtures and test configuration

## Important Notes

- **No Mock Implementations**: All tests use real data and real APIs (not mocks), following the project's philosophy
- **Schema Hashing**: The database uses SHA256 hash of the Pydantic schema JSON to cache appropriately for different schemas
- **OpenRouter API**: Requires valid API key set in environment or passed to HikuExtractor initialization
- **Timeout Protection**: Code execution has 30-second timeout; API requests have 300-second timeout
- **Cache Management**: Use `clear_cache_for_key()` when page structure changes, or `clear_all_cache()` during development
