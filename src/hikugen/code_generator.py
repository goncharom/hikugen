# ABOUTME: LLM-powered code generation for Pydantic data extraction
# ABOUTME: Handles code generation, regeneration, execution, and quality validation via OpenRouter

import logging
import re
import threading
from typing import Tuple
from pydantic import BaseModel

from hikugen.http_client import call_openrouter_api
from hikugen.code_validation import validate_code_complete
from hikugen.prompts import (
    GENERATION_SYSTEM_PROMPT,
    GENERATION_USER_PROMPT,
    REGENERATION_SYSTEM_PROMPT,
    REGENERATION_USER_PROMPT,
)

logger = logging.getLogger(__name__)


class HikuCodeGenerator:
    """Generates Pydantic extraction code using LLM."""

    def __init__(self, api_key: str, model: str = "google/gemini-2.5-flash"):
        """Initialize HikuCodeGenerator.

        Args:
            api_key: OpenRouter API key
            model: Model name (default: google/gemini-2.5-flash)
        """
        self.api_key = api_key
        self.model = model
        self.api_timeout = 300
        self.execution_timeout = 30

    def _extract_code_from_response(self, response_content: str) -> str:
        """Extract Python code from LLM response.

        Args:
            response_content: Raw LLM response text

        Returns:
            Extracted Python code as string
        """
        code_block_pattern = r"```python\s*\n(.*?)\n```"
        matches = re.findall(code_block_pattern, response_content, re.DOTALL)

        if matches:
            return matches[0].strip()

        code_block_pattern = r"```\s*\n(.*?)\n```"
        matches = re.findall(code_block_pattern, response_content, re.DOTALL)

        if matches:
            code = matches[0].strip()
            if "def extract_data" in code:
                return code

        if "def extract_data" in response_content:
            return response_content.strip()

        return response_content.strip()

    def _extract_json_from_response(self, response_content: str) -> str:
        """Extract JSON from LLM response.

        Args:
            response_content: Raw LLM response text

        Returns:
            Extracted JSON string
        """
        json_block_pattern = r"```json\s*\n(.*?)\n```"
        matches = re.findall(json_block_pattern, response_content, re.DOTALL)

        if matches:
            return matches[0].strip()

        json_block_pattern = r"```\s*\n(\{.*?\})\s*\n```"
        matches = re.findall(json_block_pattern, response_content, re.DOTALL)

        if matches:
            return matches[0].strip()

        json_pattern = r'(\{[^{}]*"has_issues"[^{}]*\})'
        matches = re.findall(json_pattern, response_content, re.DOTALL)

        if matches:
            return matches[0].strip()

        return response_content.strip()

    def _call_llm_and_validate(
        self, system_prompt: str, user_prompt: str
    ) -> Tuple[str, bool]:
        """Call LLM API and validate returned code.

        Args:
            system_prompt: System prompt for LLM
            user_prompt: User prompt for LLM

        Returns:
            Tuple of (code, success). success is True if code is valid.
        """
        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response_content = call_openrouter_api(
                self.api_key, self.model, messages, self.api_timeout
            )

            code = self._extract_code_from_response(response_content)

            is_valid, error_msg = validate_code_complete(code)

            if not is_valid:
                logger.warning("Generated code failed validation: %s", error_msg)
                return code, False

            return code, True

        except Exception as e:
            return str(e), False

    def generate_extraction_code(
        self, url: str, html_content: str, schema: str
    ) -> Tuple[str, bool]:
        """Generate Pydantic extraction code for a URL.

        Args:
            url: Source URL for context
            html_content: HTML content to analyze
            schema: Pydantic model schema definition

        Returns:
            Tuple of (code, success). success is True if code is valid.
        """
        user_prompt = GENERATION_USER_PROMPT.format(
            url=url, html_sample=html_content, schema=schema
        )
        return self._call_llm_and_validate(GENERATION_SYSTEM_PROMPT, user_prompt)

    def regenerate_code(
        self,
        url: str,
        html_content: str,
        schema: str,
        old_code: str,
        error_message: str,
    ) -> Tuple[str, bool]:
        """Regenerate Pydantic extraction code with error context.

        Args:
            url: Source URL for context
            html_content: HTML content to analyze
            schema: Pydantic model schema definition
            old_code: Previous code that failed
            error_message: Error from previous execution

        Returns:
            Tuple of (code, success). success is True if code is valid.
        """
        user_prompt = REGENERATION_USER_PROMPT.format(
            url=url,
            html_sample=html_content,
            schema=schema,
            error_message=error_message,
            old_code=old_code,
        )
        return self._call_llm_and_validate(REGENERATION_SYSTEM_PROMPT, user_prompt)

    def check_data_quality_with_llm(
        self, result: BaseModel, schema: str
    ) -> tuple[bool, list[str]]:
        """Check extracted data quality using LLM (non-deterministic, advisory).

        This is an advisory check, not validation. LLM may identify quality issues
        like empty required fields or malformed data. Failures in LLM API or
        parsing are handled gracefully by assuming quality is acceptable.

        Args:
            result: Extracted Pydantic BaseModel instance
            schema: Pydantic model schema JSON

        Returns:
            Tuple of (looks_good, potential_issues)
            - looks_good: False if LLM identified quality concerns
            - potential_issues: List of LLM-identified issues
        """
        import json
        from hikugen.prompts import format_quality_check_prompt

        try:
            # Convert result to JSON
            result_json = result.model_dump_json(indent=2)

            # Get prompts
            system_prompt, user_prompt = format_quality_check_prompt(
                extracted_data=result_json,
                schema=schema
            )

            # Call LLM
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            response_content = call_openrouter_api(
                self.api_key, self.model, messages, self.api_timeout
            )

            # Parse JSON response
            json_content = self._extract_json_from_response(response_content)
            validation_result = json.loads(json_content)

            has_issues = validation_result.get("has_issues", False)
            issues = validation_result.get("issues", [])

            if has_issues and issues:
                logger.debug("LLM found %d quality issues", len(issues))
                return False, issues

            logger.debug("LLM quality check passed")
            return True, []

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LLM quality response: %s", e)
            # On parse failure, assume valid (don't block on LLM issues)
            return True, []

        except Exception as e:
            logger.warning("LLM quality check failed: %s", e)
            # On LLM failure, assume valid (don't block on API issues)
            return True, []

    def execute_extraction_code(
        self, code: str, html_content: str, schema: type[BaseModel]
    ) -> BaseModel:
        """Execute extraction code and validate result with Pydantic model.

        Args:
            code: Python code to execute (must return dict)
            html_content: HTML content to pass to the function
            schema: Pydantic BaseModel class for validation

        Returns:
            Validated Pydantic BaseModel instance with extracted data

        Raises:
            ValueError: If code is empty or validation fails
            TimeoutError: If execution exceeds timeout
            RuntimeError: If execution fails
            ValidationError: If dict fails Pydantic validation
        """
        if not code or not code.strip():
            raise ValueError("Empty code provided")

        is_valid, error_message = validate_code_complete(code)
        if not is_valid:
            raise ValueError(error_message)

        dict_result = self._execute_with_timeout(code, html_content)

        if not isinstance(dict_result, dict):
            raise RuntimeError(
                f"Function returned {type(dict_result).__name__} instead of dict"
            )

        return schema.model_validate(dict_result)

    def _execute_with_timeout(self, code: str, html_content: str) -> dict:
        """Execute code with timeout protection using threading.

        Args:
            code: Python code to execute
            html_content: HTML content for the function

        Returns:
            Dict with extracted data

        Raises:
            TimeoutError: If execution exceeds timeout
            RuntimeError: If execution fails
        """
        result = [None]
        exception = [None]

        def target():
            try:
                exec_globals = dict(globals())
                exec_globals["html_content"] = html_content

                compiled_code = compile(code, "<generated_code>", "exec")
                exec(compiled_code, exec_globals)

                if "extract_data" not in exec_globals:
                    raise RuntimeError("Function 'extract_data' not found in code")

                extract_func = exec_globals["extract_data"]
                extraction_result = extract_func(html_content)

                if extraction_result is None:
                    raise RuntimeError("Function returned None instead of BaseModel")

                result[0] = extraction_result
            except Exception as e:
                exception[0] = e

        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()
        thread.join(timeout=self.execution_timeout)

        if thread.is_alive():
            logger.error(
                "Code execution timed out after %d seconds", self.execution_timeout
            )
            raise TimeoutError(
                f"Code execution timed out after {self.execution_timeout} seconds"
            )

        if exception[0]:
            raise exception[0]

        return result[0]
