# ABOUTME: Test suite for HikuCodeGenerator LLM integration
# ABOUTME: Tests code generation, regeneration, execution, and quality validation

from unittest.mock import patch
import pytest
from pydantic import BaseModel
from hikugen.code_generator import HikuCodeGenerator


class TestHikuCodeGeneratorInit:
    """Test HikuCodeGenerator initialization."""

    def test_init_with_api_key_and_model(self):
        """Test initialization with API key and custom model."""
        generator = HikuCodeGenerator(api_key="test-key", model="custom-model")

        assert generator.api_key == "test-key"
        assert generator.model == "custom-model"

    def test_init_with_default_model(self):
        """Test initialization uses default model when not specified."""
        generator = HikuCodeGenerator(api_key="test-key")

        assert generator.api_key == "test-key"
        assert generator.model == "google/gemini-2.5-flash"

    def test_init_sets_timeout_values(self):
        """Test initialization sets correct timeout values."""
        generator = HikuCodeGenerator(api_key="test-key")

        assert generator.api_timeout == 300
        assert generator.execution_timeout == 30


class TestExtractCodeFromResponse:
    """Test code extraction from LLM responses."""

    def test_extract_code_from_markdown_python_block(self):
        """Test extracting code from ```python markdown block."""
        generator = HikuCodeGenerator(api_key="test-key")

        response = """Here's the code:
```python
def extract_data(html_content):
    return data
```
That should work!"""

        code = generator._extract_code_from_response(response)
        assert code == "def extract_data(html_content):\n    return data"

    def test_extract_code_from_plain_markdown_block(self):
        """Test extracting code from ``` markdown block without language."""
        generator = HikuCodeGenerator(api_key="test-key")

        response = """```
def extract_data(html_content):
    return data
```"""

        code = generator._extract_code_from_response(response)
        assert "def extract_data(html_content):" in code

    def test_extract_code_from_plain_text(self):
        """Test extracting code from plain text response."""
        generator = HikuCodeGenerator(api_key="test-key")

        response = "def extract_data(html_content):\n    return data"

        code = generator._extract_code_from_response(response)
        assert "def extract_data(html_content):" in code

    def test_extract_code_prioritizes_python_blocks(self):
        """Test that Python markdown blocks are prioritized."""
        generator = HikuCodeGenerator(api_key="test-key")

        response = """```
some text
```

```python
def extract_data(html_content):
    return data
```"""

        code = generator._extract_code_from_response(response)
        assert "def extract_data(html_content):" in code


class TestExtractJsonFromResponse:
    """Test JSON extraction from LLM responses."""

    def test_extract_json_from_markdown_block(self):
        """Test extracting JSON from ```json markdown block."""
        generator = HikuCodeGenerator(api_key="test-key")

        response = """```json
{"has_issues": true, "issues": ["Missing field"]}
```"""

        json_str = generator._extract_json_from_response(response)
        assert '"has_issues": true' in json_str

    def test_extract_json_from_plain_block(self):
        """Test extracting JSON from plain markdown block."""
        generator = HikuCodeGenerator(api_key="test-key")

        response = """```
{"has_issues": false, "issues": []}
```"""

        json_str = generator._extract_json_from_response(response)
        assert '"has_issues"' in json_str

    def test_extract_json_from_text(self):
        """Test extracting JSON object from plain text."""
        generator = HikuCodeGenerator(api_key="test-key")

        response = 'The result is {"has_issues": true, "issues": ["error"]}'

        json_str = generator._extract_json_from_response(response)
        assert '"has_issues"' in json_str

    def test_extract_json_returns_content_as_fallback(self):
        """Test that full content is returned if no JSON found."""
        generator = HikuCodeGenerator(api_key="test-key")

        response = "No JSON here"

        json_str = generator._extract_json_from_response(response)
        assert json_str == "No JSON here"


class TestGenerateExtractionCode:
    """Test code generation functionality."""

    @patch('hikugen.code_generator.call_openrouter_api')
    def test_successful_code_generation(self, mock_api):
        """Test successful code generation with valid response."""
        generator = HikuCodeGenerator(api_key="test-key")

        mock_api.return_value = """```python
def extract_data(html_content):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, 'html.parser')
    return {"title": soup.find('title').text}
```"""

        schema = "class DataModel(BaseModel): title: str"
        code, success = generator.generate_extraction_code(
            url="https://example.com",
            html_content="<html><title>Test</title></html>",
            schema=schema
        )

        assert success is True
        assert "def extract_data(html_content):" in code
        assert mock_api.called

    @patch('hikugen.code_generator.call_openrouter_api')
    def test_code_generation_with_invalid_code(self, mock_api):
        """Test code generation when LLM returns invalid code."""
        generator = HikuCodeGenerator(api_key="test-key")

        mock_api.return_value = """```python
def wrong_function_name(html_content):
    return None
```"""

        schema = "class DataModel(BaseModel): title: str"
        code, success = generator.generate_extraction_code(
            url="https://example.com",
            html_content="<html></html>",
            schema=schema
        )

        assert success is False

    @patch('hikugen.code_generator.call_openrouter_api')
    def test_code_generation_uses_prompts(self, mock_api):
        """Test that code generation uses proper prompts."""
        generator = HikuCodeGenerator(api_key="test-key")

        mock_api.return_value = """```python
def extract_data(html_content):
    from pydantic import BaseModel
    class DataModel(BaseModel):
        title: str
    return DataModel(title="test")
```"""

        schema = "class DataModel(BaseModel): title: str"
        generator.generate_extraction_code(
            url="https://example.com",
            html_content="<html></html>",
            schema=schema
        )

        call_args = mock_api.call_args
        messages = call_args[0][2]
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert 'https://example.com' in messages[1]['content']


class TestRegenerateCode:
    """Test code regeneration functionality."""

    @patch('hikugen.code_generator.call_openrouter_api')
    def test_successful_regeneration(self, mock_api):
        """Test successful code regeneration with error context."""
        generator = HikuCodeGenerator(api_key="test-key")

        mock_api.return_value = """```python
def extract_data(html_content):
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, 'html.parser')
    title_elem = soup.find('h1')
    return {"title": title_elem.text if title_elem else ""}
```"""

        schema = "class DataModel(BaseModel): title: str"
        old_code = "def extract_data(html_content): return None"

        code, success = generator.regenerate_code(
            url="https://example.com",
            html_content="<html></html>",
            schema=schema,
            old_code=old_code,
            error_message="AttributeError: 'NoneType' has no attribute 'text'"
        )

        assert success is True
        assert "def extract_data(html_content):" in code

    @patch('hikugen.code_generator.call_openrouter_api')
    def test_regeneration_includes_error_context(self, mock_api):
        """Test that regeneration prompt includes error and old code."""
        generator = HikuCodeGenerator(api_key="test-key")

        mock_api.return_value = """```python
def extract_data(html_content):
    return {"title": "test"}
```"""

        schema = "class DataModel(BaseModel): title: str"
        old_code = "def extract_data(html_content): return None"
        error = "Some error"

        generator.regenerate_code(
            url="https://example.com",
            html_content="<html></html>",
            schema=schema,
            old_code=old_code,
            error_message=error
        )

        call_args = mock_api.call_args
        messages = call_args[0][2]
        user_message = messages[1]['content']

        assert error in user_message
        assert old_code in user_message


class TestExecuteExtractionCode:
    """Test code execution functionality."""

    def test_successful_code_execution(self):
        """Test successful execution of valid code."""
        generator = HikuCodeGenerator(api_key="test-key")

        code = """
def extract_data(html_content):
    return {"title": "Test Title"}
"""

        class DataModel(BaseModel):
            title: str

        result = generator.execute_extraction_code(code, "<html></html>", DataModel)

        assert isinstance(result, BaseModel)
        assert result.title == "Test Title"

    def test_code_execution_timeout(self):
        """Test that infinite loops are terminated with timeout."""
        generator = HikuCodeGenerator(api_key="test-key")
        generator.execution_timeout = 1

        code = """
def extract_data(html_content):
    while True:
        pass
"""

        class DataModel(BaseModel):
            title: str

        with pytest.raises(TimeoutError):
            generator.execute_extraction_code(code, "<html></html>", DataModel)

    def test_code_execution_validates_schema(self):
        """Test that execution validates returned data matches schema."""
        generator = HikuCodeGenerator(api_key="test-key")

        code = """
def extract_data(html_content):
    return {"title": 123}
"""

        class DataModel(BaseModel):
            title: str

        with pytest.raises(Exception):
            generator.execute_extraction_code(code, "<html></html>", DataModel)

    def test_code_execution_validates_imports(self):
        """Test that execution blocks forbidden imports."""
        generator = HikuCodeGenerator(api_key="test-key")

        code = """
import os

def extract_data(html_content):
    return {"title": "test"}
"""

        class DataModel(BaseModel):
            title: str

        with pytest.raises(Exception):
            generator.execute_extraction_code(code, "<html></html>", DataModel)

    def test_code_execution_with_html_parsing(self):
        """Test execution with actual HTML parsing using BeautifulSoup."""
        generator = HikuCodeGenerator(api_key="test-key")

        code = """
from bs4 import BeautifulSoup

def extract_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    title_tag = soup.find('title')
    return {"title": title_tag.text if title_tag else ""}
"""

        class DataModel(BaseModel):
            title: str

        html = "<html><head><title>My Page</title></head></html>"
        result = generator.execute_extraction_code(code, html, DataModel)

        assert isinstance(result, BaseModel)
        assert result.title == "My Page"

    def test_code_execution_empty_code_raises_error(self):
        """Test that empty code raises ValueError."""
        generator = HikuCodeGenerator(api_key="test-key")

        class DataModel(BaseModel):
            title: str

        with pytest.raises(ValueError, match="Empty code"):
            generator.execute_extraction_code("", "<html></html>", DataModel)


class TestCheckDataQualityWithLLM:
    """Test LLM data quality checking."""

    @patch('hikugen.code_generator.call_openrouter_api')
    def test_quality_check_with_valid_data(self, mock_api):
        """Test quality check passes for valid data."""
        from hikugen.code_generator import HikuCodeGenerator
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            title: str

        generator = HikuCodeGenerator(api_key="test-key")
        result = TestSchema(title="Valid Title")

        mock_api.return_value = '{"has_issues": false, "issues": []}'

        is_valid, issues = generator.check_data_quality_with_llm(result, "{}")

        assert is_valid is True
        assert issues == []

    @patch('hikugen.code_generator.call_openrouter_api')
    def test_quality_check_with_issues(self, mock_api):
        """Test quality check detects issues."""
        from hikugen.code_generator import HikuCodeGenerator
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            title: str

        generator = HikuCodeGenerator(api_key="test-key")
        result = TestSchema(title="")

        mock_api.return_value = '''{
            "has_issues": true,
            "issues": ["Required field 'title' is empty"]
        }'''

        is_valid, issues = generator.check_data_quality_with_llm(result, "{}")

        assert is_valid is False
        assert len(issues) == 1
        assert "title" in issues[0]

    @patch('hikugen.code_generator.call_openrouter_api')
    def test_quality_check_graceful_degradation(self, mock_api):
        """Test quality check handles errors gracefully."""
        from hikugen.code_generator import HikuCodeGenerator
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            title: str

        generator = HikuCodeGenerator(api_key="test-key")
        result = TestSchema(title="Test")

        # Invalid JSON response
        mock_api.return_value = "invalid json"

        is_valid, issues = generator.check_data_quality_with_llm(result, "{}")

        # Should degrade gracefully
        assert is_valid is True
        assert issues == []


class TestDictReturnBehavior:
    """Test that generated code returns dict and user validators execute."""

    def test_execution_accepts_dict_return(self):
        """Test that execute_extraction_code accepts dict returns."""
        from pydantic import BaseModel
        generator = HikuCodeGenerator(api_key="test-key")

        code = """
def extract_data(html_content):
    return {"title": "Test Title", "url": "https://example.com"}
"""

        class Article(BaseModel):
            title: str
            url: str

        result = generator.execute_extraction_code(
            code=code,
            html_content="<html></html>",
            schema=Article
        )

        assert isinstance(result, Article)
        assert result.title == "Test Title"
        assert result.url == "https://example.com"

    def test_user_validators_execute_on_dict_return(self):
        """Test that user's field validators execute when validating dict."""
        from pydantic import BaseModel, field_validator
        generator = HikuCodeGenerator(api_key="test-key")

        code = """
def extract_data(html_content):
    return {"title": "  Untrimmed Title  ", "url": "https://example.com"}
"""

        class Article(BaseModel):
            title: str
            url: str

            @field_validator('title')
            @classmethod
            def strip_title(cls, v: str) -> str:
                return v.strip()

        result = generator.execute_extraction_code(
            code=code,
            html_content="<html></html>",
            schema=Article
        )

        assert isinstance(result, Article)
        assert result.title == "Untrimmed Title"  # Should be stripped
        assert result.url == "https://example.com"

    def test_validation_error_raised_on_invalid_dict(self):
        """Test that ValidationError is raised when dict fails validation."""
        from pydantic import BaseModel, field_validator, ValidationError
        generator = HikuCodeGenerator(api_key="test-key")

        code = """
def extract_data(html_content):
    return {"title": "", "url": "https://example.com"}
"""

        class Article(BaseModel):
            title: str
            url: str

            @field_validator('title')
            @classmethod
            def not_empty(cls, v: str) -> str:
                if not v or not v.strip():
                    raise ValueError('Title cannot be empty')
                return v

        with pytest.raises(ValidationError) as exc_info:
            generator.execute_extraction_code(
                code=code,
                html_content="<html></html>",
                schema=Article
            )

        assert "Title cannot be empty" in str(exc_info.value)
