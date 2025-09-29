# ABOUTME: Test suite for Hiku code validation functionality
# ABOUTME: Tests validation of Pydantic extraction code for imports, signatures, and security

from hikugen.code_validation import (
    validate_code_imports,
    validate_function_usage,
    validate_code_complete,
    is_stdlib_module,
    ALLOWED_THIRD_PARTY
)


class TestStdlibModuleChecking:
    """Test standard library module identification."""

    def test_safe_stdlib_modules(self):
        """Test that safe stdlib modules are recognized."""
        safe_modules = ["json", "re", "datetime", "math", "hashlib", "urllib", "html"]
        for module in safe_modules:
            assert is_stdlib_module(module), f"Module {module} should be recognized as safe stdlib"

    def test_dangerous_modules_blocked(self):
        """Test that dangerous modules are blocked even if they're stdlib."""
        dangerous_modules = ["os", "subprocess", "sys", "importlib", "exec", "eval"]
        for module in dangerous_modules:
            assert not is_stdlib_module(module), f"Module {module} should be blocked for security"

    def test_third_party_modules(self):
        """Test that third-party modules are not considered stdlib."""
        third_party = ["numpy", "pandas", "django", "flask", "lxml"]
        for module in third_party:
            assert not is_stdlib_module(module), f"Module {module} should not be considered stdlib"


class TestImportValidation:
    """Test validation of imports in extraction code."""

    def test_valid_imports_pass(self):
        """Test that valid imports pass validation."""
        valid_code = """
import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

def extract_data(html_content):
    return {"data": "test"}
"""
        is_valid, error = validate_code_imports(valid_code)
        assert is_valid
        assert error == ""

    def test_forbidden_third_party_imports_fail(self):
        """Test that forbidden third-party imports fail validation."""
        invalid_codes = [
            "import lxml",
            "from lxml import etree",
            "import numpy as np",
            "from pandas import DataFrame",
            "import django",
            "import pydantic",
            "from pydantic import BaseModel"
        ]

        for code in invalid_codes:
            is_valid, error = validate_code_imports(code)
            assert not is_valid
            assert "Forbidden import" in error

    def test_dangerous_stdlib_imports_fail(self):
        """Test that dangerous stdlib imports fail validation."""
        dangerous_codes = [
            "import os",
            "import subprocess",
            "import sys",
            "from os import system",
            "import importlib"
        ]

        for code in dangerous_codes:
            is_valid, error = validate_code_imports(code)
            assert not is_valid
            assert "Forbidden import" in error

    def test_syntax_error_handling(self):
        """Test that syntax errors are caught."""
        invalid_syntax = "import json import re"  # Invalid syntax
        is_valid, error = validate_code_imports(invalid_syntax)
        assert not is_valid
        assert "Syntax error" in error

    def test_allowed_third_party_override(self):
        """Test that allowed third-party imports can be overridden."""
        code = "import custom_module"
        custom_allowed = {"custom_module"}

        # Should fail with default allowed set
        is_valid, error = validate_code_imports(code)
        assert not is_valid

        # Should pass with custom allowed set
        is_valid, error = validate_code_imports(code, custom_allowed)
        assert is_valid
        assert error == ""


class TestFunctionSignatureValidation:
    """Test validation of extract_data function signature and usage."""

    def test_valid_function_signature(self):
        """Test that correct function signature passes validation."""
        valid_codes = [
            """
def extract_data(html_content):
    return SomeModel(title=html_content)
""",
            """
from pydantic import BaseModel

def extract_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    return ArticleModel(title=soup.title.string)
""",
            """
def extract_data(html_content):
    # Process html_content
    data = parse_content(html_content)
    return MyModel(data=data)
"""
        ]

        for code in valid_codes:
            is_valid, error = validate_function_usage(code)
            assert is_valid, f"Code should be valid: {error}"
            assert error == ""

    def test_missing_function_fails(self):
        """Test that missing extract_data function fails validation."""
        code_without_function = """
import json

def some_other_function():
    return "hello"
"""
        is_valid, error = validate_function_usage(code_without_function)
        assert not is_valid
        assert "Function 'extract_data' not found" in error

    def test_wrong_parameter_name_fails(self):
        """Test that wrong parameter names fail validation."""
        wrong_param_codes = [
            "def extract_data(htmlContent): return None",
            "def extract_data(html): return None",
            "def extract_data(content): return None",
            "def extract_data(page_content): return None",
            "def extract_data(data): return None"
        ]

        for code in wrong_param_codes:
            is_valid, error = validate_function_usage(code)
            assert not is_valid
            assert "must be 'html_content'" in error

    def test_wrong_parameter_count_fails(self):
        """Test that wrong parameter count fails validation."""
        wrong_param_count_codes = [
            "def extract_data(): return None",  # No parameters
            "def extract_data(html_content, extra_param): return None",  # Too many parameters
        ]

        for code in wrong_param_count_codes:
            is_valid, error = validate_function_usage(code)
            assert not is_valid
            assert "exactly one parameter" in error

    def test_syntax_error_in_function_validation(self):
        """Test that syntax errors are caught in function validation."""
        invalid_syntax = """
def extract_data(html_content
    return Model()  # Missing closing parenthesis
"""
        is_valid, error = validate_function_usage(invalid_syntax)
        assert not is_valid
        assert "Syntax error" in error


class TestCompleteValidation:
    """Test complete validation combining imports and function checks."""

    def test_valid_complete_code(self):
        """Test that completely valid code passes all validation."""
        valid_code = """
import json
import re
from datetime import datetime
import requests
from bs4 import BeautifulSoup

def extract_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')

    title = soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
    content = soup.find('div', class_='content').get_text(strip=True) if soup.find('div', class_='content') else ""

    return {
        "title": title,
        "content": content,
        "published_date": datetime.now().isoformat()
    }
"""
        is_valid, error = validate_code_complete(valid_code)
        assert is_valid
        assert error == ""

    def test_invalid_imports_in_complete_validation(self):
        """Test that invalid imports fail complete validation."""
        code_with_lxml = """
from lxml import etree

def extract_data(html_content):
    return {"data": "test"}
"""
        is_valid, error = validate_code_complete(code_with_lxml)
        assert not is_valid
        assert "lxml" in error

    def test_invalid_function_in_complete_validation(self):
        """Test that invalid function fails complete validation."""
        code_with_wrong_function = """
import requests
from bs4 import BeautifulSoup

def wrong_function_name(html_content):
    return Model()
"""
        is_valid, error = validate_code_complete(code_with_wrong_function)
        assert not is_valid
        assert "Function 'extract_data' not found" in error


class TestAllowedThirdPartyConstants:
    """Test the allowed third-party imports constant."""

    def test_pydantic_allowed_third_party_contents(self):
        """Test that PYDANTIC_ALLOWED_THIRD_PARTY contains expected modules."""
        expected_modules = {"requests", "bs4", "beautifulsoup4"}
        assert ALLOWED_THIRD_PARTY == expected_modules

    def test_lxml_not_in_allowed(self):
        """Test that lxml is explicitly not in allowed third-party imports."""
        assert "lxml" not in ALLOWED_THIRD_PARTY
        assert "xml" not in ALLOWED_THIRD_PARTY  # xml is stdlib, but checking lxml variants