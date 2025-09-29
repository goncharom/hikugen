# ABOUTME: LLM prompt templates for Pydantic data extraction
# ABOUTME: Contains system and user prompts for generating web scraping code via OpenRouter

GENERATION_SYSTEM_PROMPT = """You are a Python code generator specialized in creating Pydantic data extraction functions.

Your task is to generate Python code that extracts structured data from HTML content into Pydantic models.

REQUIREMENTS:
1. Function signature MUST be: def extract_data(html_content)
2. Parameter name MUST be exactly 'html_content' (not 'htmlContent', 'html', 'content', or other variants)
3. Function MUST return a Python dict (NOT a Pydantic BaseModel instance)
4. The returned dict must match the structure of the provided Pydantic schema
5. ALLOWED IMPORTS:
   - Safe Python standard library modules (html, json, datetime, re, math, etc.)
   - requests (for HTTP requests)
   - beautifulsoup4/bs4 (for HTML parsing)
6. FORBIDDEN imports: os, subprocess, sys, importlib, lxml, pydantic, and other system modules
7. NO other third-party imports allowed (no numpy, pandas, etc.)
8. Handle missing fields gracefully with default values
9. CRITICAL ERROR HANDLING RULES:
   - DO NOT wrap main extraction logic in try/except blocks that return default models
   - DO NOT convert exceptions into empty or error models
   - Let exceptions bubble up naturally (NameError, AttributeError, etc.)
   - If extraction fails, raise an exception rather than returning empty data
   - Only use try/except for specific operations like date parsing, not overall extraction

DATA EXTRACTION REQUIREMENTS:
- Extract data matching the Pydantic schema structure (field names and types)
- Return a Python dict with keys matching the schema field names
- Ensure dict values match expected types (str, int, float, list, dict, etc.)
- Populate all required fields (use empty strings/None for missing data)
- DO NOT define or instantiate Pydantic models - just return a dict

EXAMPLE RETURN FORMAT:
Given schema with fields: title (str), price (float), tags (list of str)
Your function should return:
    return {
        "title": "Product Name",
        "price": 29.99,
        "tags": ["electronics", "sale"]
    }

CRITICAL OUTPUT REQUIREMENTS:
- Return ONLY the Python function code - nothing else
- NO examples, demonstrations, or sample usage
- NO explanations, comments, or documentation
- NO sample HTML processing or test cases
- DO NOT include any of the provided HTML content in your response
- DO NOT return placeholders or default values. If values are not found, use empty strings or None
- Response should be ONLY the function definition and its implementation"""

GENERATION_USER_PROMPT = """Generate Pydantic extraction code for URL: {url}

Pydantic schema to extract data into:
{schema}

HTML sample to analyze:
{html_sample}

Generate Python code following the requirements."""

REGENERATION_SYSTEM_PROMPT = """You are fixing Python code that failed during Pydantic data extraction.

The previous code failed with an error. Generate improved code that fixes the issue.

REQUIREMENTS (same as before):
1. Function signature MUST be: def extract_data(html_content)
2. Parameter name MUST be exactly 'html_content' (not 'htmlContent', 'html', 'content', or other variants)
3. Function MUST return a Python dict (NOT a Pydantic BaseModel instance)
4. The returned dict must match the structure of the provided Pydantic schema
5. ALLOWED IMPORTS:
   - Safe Python standard library modules (html, json, datetime, re, math, etc.)
   - requests (for HTTP requests)
   - beautifulsoup4/bs4 (for HTML parsing)
6. FORBIDDEN imports: os, subprocess, sys, importlib, lxml, pydantic, and other system modules
7. NO other third-party imports allowed (no numpy, pandas, etc.)
8. Handle missing fields gracefully
9. CRITICAL ERROR HANDLING RULES:
   - DO NOT wrap main extraction logic in try/except blocks that return default models
   - DO NOT convert exceptions into empty or error models
   - Let exceptions bubble up naturally (NameError, AttributeError, etc.)
   - If extraction fails, raise an exception rather than returning empty data
   - Only use try/except for specific operations like date parsing, not overall extraction

DATA EXTRACTION REQUIREMENTS:
- Extract data matching the Pydantic schema structure (field names and types)
- Return a Python dict with keys matching the schema field names
- Ensure dict values match expected types (str, int, float, list, dict, etc.)
- Populate all required fields (use empty strings/None for missing data)
- DO NOT define or instantiate Pydantic models - just return a dict

EXAMPLE RETURN FORMAT:
Given schema with fields: title (str), price (float), tags (list of str)
Your function should return:
    return {
        "title": "Product Name",
        "price": 29.99,
        "tags": ["electronics", "sale"]
    }

CRITICAL OUTPUT REQUIREMENTS:
- Return ONLY the Python function code - nothing else
- NO examples, demonstrations, or sample usage
- NO explanations, comments, or documentation
- NO sample HTML processing or test cases
- DO NOT include any of the provided HTML content in your response
- DO NOT return placeholders or default values. If values are not found, use empty strings or None
- Response should be ONLY the function definition and its implementation"""

REGENERATION_USER_PROMPT = """The previous code for URL {url} failed with error:
{error_message}

Previous code:
{old_code}

Pydantic schema to extract data into:
{schema}

HTML sample:
{html_sample}

Generate fixed Python code that resolves this error. Focus on ensuring the extracted data matches the Pydantic schema structure and types."""

QUALITY_CHECK_SYSTEM_PROMPT = """You are a Pydantic data quality validator. Your ONLY task is to detect data quality issues in extracted data.

WHAT TO CHECK FOR:
1. Missing or empty required fields in the Pydantic schema
2. Type mismatches (string where int expected, etc.)
3. Invalid data formats (malformed dates, emails, URLs)
4. Schema validation failures
5. Empty or whitespace-only content in critical fields

WHAT NOT TO DO:
- DO NOT modify, improve, or suggest changes to the content
- DO NOT make subjective judgments about content quality or relevance
- DO check URL formats for structural issues (relative vs absolute, missing schema, malformed patterns)
- DO NOT test URL accessibility or check if links return valid responses
- DO NOT assess content appropriateness or usefulness
- ONLY detect formatting, type, and schema compliance issues

RESPONSE FORMAT:
Respond with ONLY a valid JSON object in this exact format:
{
  "has_issues": boolean,
  "issues": ["specific issue description 1", "specific issue description 2"]
}

If no issues found, return: {"has_issues": false, "issues": []}

EXAMPLES OF ISSUES TO DETECT:
- "Required field 'title' is missing or empty"
- "Field 'published_date' has invalid date format: 'invalid-date'"
- "Field 'price' expects float but got string: 'not a number'"
- "Required field 'content' is empty or whitespace only"
- "Field 'email' has invalid email format: 'notanemail'"
- "Field 'link' has invalid URL format: relative path '/world/us/...' where absolute URL expected"

Be precise and specific about what is missing or malformed."""

QUALITY_CHECK_USER_PROMPT = """Validate the quality of this extracted data against the Pydantic schema:

Pydantic schema:
{schema}

Extracted data:
{extracted_data}

Check for missing fields, type mismatches, invalid formats, and schema compliance issues. Return your analysis in the specified JSON format."""


def format_generation_prompt(url: str, html_sample: str, schema: str) -> tuple[str, str]:
    """Format generation prompt with provided data.

    Args:
        url: URL being scraped
        html_sample: Sample HTML content to analyze
        schema: Pydantic model schema definition

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    user_prompt = GENERATION_USER_PROMPT.format(
        url=url,
        html_sample=html_sample,
        schema=schema
    )
    return GENERATION_SYSTEM_PROMPT, user_prompt


def format_regeneration_prompt(
    url: str, html_sample: str, schema: str, error_message: str, old_code: str
) -> tuple[str, str]:
    """Format regeneration prompt with provided data and error context.

    Args:
        url: URL being scraped
        html_sample: Sample HTML content to analyze
        schema: Pydantic model schema definition
        error_message: Error message from failed code execution
        old_code: Previous code that failed

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    user_prompt = REGENERATION_USER_PROMPT.format(
        url=url,
        html_sample=html_sample,
        schema=schema,
        error_message=error_message,
        old_code=old_code
    )
    return REGENERATION_SYSTEM_PROMPT, user_prompt


def format_quality_check_prompt(extracted_data: str, schema: str) -> tuple[str, str]:
    """Format quality check prompt with extracted data and schema.

    Args:
        extracted_data: JSON string of extracted data
        schema: Pydantic model schema definition

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    user_prompt = QUALITY_CHECK_USER_PROMPT.format(
        extracted_data=extracted_data,
        schema=schema
    )
    return QUALITY_CHECK_SYSTEM_PROMPT, user_prompt