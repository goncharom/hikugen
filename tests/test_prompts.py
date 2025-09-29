# ABOUTME: Test suite for Hiku LLM prompt templates
# ABOUTME: Tests prompt generation, formatting, and template structure for Pydantic extraction

from hikugen.prompts import (
    GENERATION_SYSTEM_PROMPT,
    GENERATION_USER_PROMPT,
    REGENERATION_SYSTEM_PROMPT,
    REGENERATION_USER_PROMPT,
    QUALITY_CHECK_SYSTEM_PROMPT,
    QUALITY_CHECK_USER_PROMPT,
    format_generation_prompt,
    format_regeneration_prompt,
    format_quality_check_prompt
)


class TestPromptConstants:
    """Test that prompt template constants exist and have expected content."""

    def test_generation_system_prompt_exists(self):
        """Test that generation system prompt exists and contains key requirements."""
        assert isinstance(GENERATION_SYSTEM_PROMPT, str)
        assert len(GENERATION_SYSTEM_PROMPT) > 100

        # Check for key requirements
        assert "extract_data" in GENERATION_SYSTEM_PROMPT
        assert "html_content" in GENERATION_SYSTEM_PROMPT
        assert "BaseModel" in GENERATION_SYSTEM_PROMPT
        assert "pydantic" in GENERATION_SYSTEM_PROMPT.lower()

    def test_generation_system_prompt_forbids_lxml(self):
        """Test that generation system prompt explicitly forbids lxml."""
        assert "lxml" in GENERATION_SYSTEM_PROMPT.lower()
        assert "forbidden" in GENERATION_SYSTEM_PROMPT.lower() or "not allowed" in GENERATION_SYSTEM_PROMPT.lower()

    def test_generation_user_prompt_template(self):
        """Test that generation user prompt is a proper template."""
        assert isinstance(GENERATION_USER_PROMPT, str)
        assert "{url}" in GENERATION_USER_PROMPT
        assert "{html_sample}" in GENERATION_USER_PROMPT
        assert "{schema}" in GENERATION_USER_PROMPT

    def test_regeneration_prompts_exist(self):
        """Test that regeneration prompts exist and have expected structure."""
        assert isinstance(REGENERATION_SYSTEM_PROMPT, str)
        assert isinstance(REGENERATION_USER_PROMPT, str)

        # System prompt should have similar requirements to generation
        assert "extract_data" in REGENERATION_SYSTEM_PROMPT
        assert "html_content" in REGENERATION_SYSTEM_PROMPT
        assert "BaseModel" in REGENERATION_SYSTEM_PROMPT

        # User prompt should be a template for error handling
        assert "{url}" in REGENERATION_USER_PROMPT
        assert "{error_message}" in REGENERATION_USER_PROMPT
        assert "{old_code}" in REGENERATION_USER_PROMPT
        assert "{html_sample}" in REGENERATION_USER_PROMPT
        assert "{schema}" in REGENERATION_USER_PROMPT

    def test_quality_check_prompts_exist(self):
        """Test that quality check prompts exist and have expected structure."""
        assert isinstance(QUALITY_CHECK_SYSTEM_PROMPT, str)
        assert isinstance(QUALITY_CHECK_USER_PROMPT, str)

        # Quality check should focus on validation
        assert "json" in QUALITY_CHECK_SYSTEM_PROMPT.lower()
        assert "pydantic" in QUALITY_CHECK_SYSTEM_PROMPT.lower()

        # User prompt should be a template
        assert "{extracted_data}" in QUALITY_CHECK_USER_PROMPT
        assert "{schema}" in QUALITY_CHECK_USER_PROMPT


class TestPromptFormatting:
    """Test prompt formatting functions."""

    def test_format_generation_prompt(self):
        """Test generation prompt formatting with sample data."""
        url = "https://example.com/article"
        html_sample = "<html><body><h1>Test Title</h1></body></html>"
        pydantic_schema = "class Article(BaseModel): title: str"

        system_prompt, user_prompt = format_generation_prompt(url, html_sample, pydantic_schema)

        # Check that system prompt is returned correctly
        assert system_prompt == GENERATION_SYSTEM_PROMPT

        # Check that user prompt is formatted with provided data
        assert url in user_prompt
        assert html_sample in user_prompt
        assert pydantic_schema in user_prompt
        assert "{url}" not in user_prompt  # Template placeholders should be replaced
        assert "{html_sample}" not in user_prompt
        assert "{pydantic_schema}" not in user_prompt

    def test_format_regeneration_prompt(self):
        """Test regeneration prompt formatting with sample data."""
        url = "https://example.com/article"
        html_sample = "<html><body><h1>Test Title</h1></body></html>"
        pydantic_schema = "class Article(BaseModel): title: str"
        error_message = "AttributeError: 'NoneType' object has no attribute 'text'"
        old_code = "def extract_data(html_content): return None"

        system_prompt, user_prompt = format_regeneration_prompt(
            url, html_sample, pydantic_schema, error_message, old_code
        )

        # Check that system prompt is returned correctly
        assert system_prompt == REGENERATION_SYSTEM_PROMPT

        # Check that user prompt is formatted with all provided data
        assert url in user_prompt
        assert html_sample in user_prompt
        assert pydantic_schema in user_prompt
        assert error_message in user_prompt
        assert old_code in user_prompt

        # Template placeholders should be replaced
        assert "{url}" not in user_prompt
        assert "{html_sample}" not in user_prompt
        assert "{pydantic_schema}" not in user_prompt
        assert "{error_message}" not in user_prompt
        assert "{old_code}" not in user_prompt

    def test_format_quality_check_prompt(self):
        """Test quality check prompt formatting with sample data."""
        extracted_data = '{"title": "Test Article", "content": "Some content"}'
        pydantic_schema = "class Article(BaseModel): title: str; content: str"

        system_prompt, user_prompt = format_quality_check_prompt(extracted_data, pydantic_schema)

        # Check that system prompt is returned correctly
        assert system_prompt == QUALITY_CHECK_SYSTEM_PROMPT

        # Check that user prompt is formatted with provided data
        assert extracted_data in user_prompt
        assert pydantic_schema in user_prompt
        assert "{extracted_data}" not in user_prompt
        assert "{pydantic_schema}" not in user_prompt


class TestPromptContent:
    """Test specific content requirements in prompts."""

    def test_generation_prompt_function_signature(self):
        """Test that generation prompt specifies correct function signature."""
        system_prompt = GENERATION_SYSTEM_PROMPT

        # Should specify exact function signature
        assert "def extract_data(html_content)" in system_prompt
        assert "html_content" in system_prompt
        assert "BaseModel" in system_prompt

    def test_generation_prompt_allowed_imports(self):
        """Test that generation prompt lists allowed imports correctly."""
        system_prompt = GENERATION_SYSTEM_PROMPT

        # Should allow key imports
        assert "requests" in system_prompt
        assert "beautifulsoup4" in system_prompt or "bs4" in system_prompt
        assert "pydantic" in system_prompt

        # Should forbid lxml
        assert "lxml" in system_prompt.lower()

    def test_regeneration_prompt_error_context(self):
        """Test that regeneration prompt provides proper error context."""
        user_prompt_template = REGENERATION_USER_PROMPT

        # Should reference error and old code
        assert "error" in user_prompt_template.lower()
        assert "failed" in user_prompt_template.lower()
        assert "{old_code}" in user_prompt_template
        assert "{error_message}" in user_prompt_template

    def test_quality_check_prompt_json_response(self):
        """Test that quality check prompt requests JSON response."""
        system_prompt = QUALITY_CHECK_SYSTEM_PROMPT

        # Should specify JSON response format
        assert "json" in system_prompt.lower()
        assert "has_issues" in system_prompt or "issues" in system_prompt


class TestPromptIntegration:
    """Test integration aspects of prompts."""

    def test_all_prompt_functions_return_tuples(self):
        """Test that all formatting functions return (system, user) tuples."""
        # Test generation prompt
        result = format_generation_prompt("url", "html", "schema")
        assert isinstance(result, tuple)
        assert len(result) == 2

        # Test regeneration prompt
        result = format_regeneration_prompt("url", "html", "schema", "error", "code")
        assert isinstance(result, tuple)
        assert len(result) == 2

        # Test quality check prompt
        result = format_quality_check_prompt("data", "schema")
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_prompt_consistency(self):
        """Test that prompts have consistent requirements."""
        # Both generation and regeneration should have similar core requirements
        gen_system = GENERATION_SYSTEM_PROMPT
        regen_system = REGENERATION_SYSTEM_PROMPT

        # Common requirements that should appear in both
        common_requirements = ["extract_data", "html_content", "BaseModel", "pydantic"]

        for requirement in common_requirements:
            assert requirement in gen_system, f"Missing {requirement} in generation prompt"
            assert requirement in regen_system, f"Missing {requirement} in regeneration prompt"

    def test_prompt_templates_complete(self):
        """Test that all required template variables are present."""
        # Generation user prompt
        gen_user = GENERATION_USER_PROMPT
        required_gen_vars = ["{url}", "{html_sample}", "{schema}"]
        for var in required_gen_vars:
            assert var in gen_user, f"Missing template variable {var} in generation user prompt"

        # Regeneration user prompt
        regen_user = REGENERATION_USER_PROMPT
        required_regen_vars = ["{url}", "{html_sample}", "{schema}", "{error_message}", "{old_code}"]
        for var in required_regen_vars:
            assert var in regen_user, f"Missing template variable {var} in regeneration user prompt"

        # Quality check user prompt
        quality_user = QUALITY_CHECK_USER_PROMPT
        required_quality_vars = ["{extracted_data}", "{schema}"]
        for var in required_quality_vars:
            assert var in quality_user, f"Missing template variable {var} in quality check user prompt"