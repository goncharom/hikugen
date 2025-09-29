# ABOUTME: Main HikuExtractor class for AI-powered web scraping
# ABOUTME: Orchestrates database caching, LLM code generation, and data extraction into Pydantic schemas

import json
import logging
from typing import Optional
from pydantic import BaseModel

from hikugen.database import HikuDatabase
from hikugen.code_generator import HikuCodeGenerator
from hikugen.http_client import fetch_page_content

logger = logging.getLogger(__name__)


class HikuExtractor:
    """Main API for extracting web data into Pydantic schemas using AI-generated code."""

    def __init__(
        self,
        api_key: str,
        model: str = "google/gemini-2.5-flash",
        db_path: str = "hikugen.db",
    ):
        """Initialize HikuExtractor.

        Args:
            api_key: OpenRouter API key for LLM access
            model: Model name (default: google/gemini-2.5-flash)
            db_path: Path to SQLite database for code caching (default: hikugen.db)
        """
        self.api_key = api_key
        self.model = model
        self.db_path = db_path
        self.database = HikuDatabase(db_path=db_path)
        self.database.create_tables()
        self.code_generator = HikuCodeGenerator(api_key=api_key, model=model)

    def extract(
        self,
        url: str,
        schema: type[BaseModel],
        cache_key: Optional[str] = None,
        use_cached_code: bool = True,
        cookies_path: Optional[str] = None,
        max_regenerate_attempts: int = 1,
        validate_quality: bool = True,
    ) -> BaseModel:
        """Extract data from URL into Pydantic schema.

        Args:
            url: URL to extract from
            schema: Pydantic BaseModel class to extract data into
            cache_key: Custom cache key (uses URL if not provided)
            use_cached_code: Use cached extraction code if available (default: True)
            cookies_path: Path to a Netscape cookies.txt file for authentication (default: None)
            max_regenerate_attempts: Max regeneration attempts (default: 1, use 0 to disable)
            validate_quality: Run LLM quality check on fresh code (default: True)

        Returns:
            BaseModel instance with extracted data

        Raises:
            RuntimeError: If code generation or execution fails
            Various: HTTP, LLM, or validation errors
        """
        return self._extract_single_url(
            url=url,
            schema=schema,
            cache_key=cache_key,
            use_cached_code=use_cached_code,
            cookies_path=cookies_path,
            max_regenerate_attempts=max_regenerate_attempts,
            validate_quality=validate_quality,
        )

    def extract_from_html(
        self,
        html_content: str,
        cache_key: str,
        schema: type[BaseModel],
        use_cached_code: bool = True,
        max_regenerate_attempts: int = 1,
        validate_quality: bool = True,
    ) -> BaseModel:
        """Extract data from HTML content into Pydantic schema.

        Args:
            html_content: HTML content to extract from
            cache_key: Unique identifier for caching (e.g., task name, document ID)
            schema: Pydantic BaseModel class to extract data into
            use_cached_code: Use cached extraction code if available (default: True)
            max_regenerate_attempts: Max regeneration attempts (default: 1, use 0 to disable)
            validate_quality: Run LLM quality check on fresh code (default: True)

        Returns:
            BaseModel instance with extracted data

        Raises:
            RuntimeError: If code generation or execution fails
            ValidationError: If validation fails
        """
        return self._extract_core(
            cache_key=cache_key,
            html_content=html_content,
            schema=schema,
            use_cached_code=use_cached_code,
            max_regenerate_attempts=max_regenerate_attempts,
            validate_quality=validate_quality,
        )

    def _extract_single_url(
        self,
        url: str,
        schema: type[BaseModel],
        cache_key: Optional[str],
        use_cached_code: bool,
        cookies_path: Optional[str],
        max_regenerate_attempts: int = 1,
        validate_quality: bool = True,
    ) -> BaseModel:
        """Extract data from a single URL with auto-regeneration.

        Args:
            url: URL to extract from
            schema: Pydantic BaseModel class
            cache_key: Custom cache key (uses URL if not provided)
            use_cached_code: Use cache if available
            cookies_path: Path to cookies file
            max_regenerate_attempts: Maximum regeneration attempts (0 to disable)
            validate_quality: Enable LLM quality check for fresh code

        Returns:
            Pydantic BaseModel instance with extracted data

        Raises:
            RuntimeError: If code generation fails
            ValidationError: If validation fails after max attempts
        """
        html_content = fetch_page_content(url, cookies_path=cookies_path, timeout=10)

        return self._extract_core(
            cache_key=cache_key or url,
            html_content=html_content,
            schema=schema,
            use_cached_code=use_cached_code,
            max_regenerate_attempts=max_regenerate_attempts,
            validate_quality=validate_quality,
        )

    def _extract_core(
        self,
        cache_key: str,
        html_content: str,
        schema: type[BaseModel],
        use_cached_code: bool,
        max_regenerate_attempts: int = 1,
        validate_quality: bool = True,
    ) -> BaseModel:
        """Core extraction logic that works with pre-fetched HTML.

        Args:
            cache_key: Cache identifier (URL, task name, etc.)
            html_content: HTML content to extract from
            schema: Pydantic BaseModel class
            use_cached_code: Use cache if available
            max_regenerate_attempts: Maximum regeneration attempts (0 to disable)
            validate_quality: Enable LLM quality check for fresh code

        Returns:
            Pydantic BaseModel instance with extracted data

        Raises:
            RuntimeError: If code generation fails
            ValidationError: If validation fails after max attempts
        """
        schema_json = json.dumps(schema.model_json_schema(), sort_keys=True)

        # Step 1: Get initial code (cached or fresh)
        cached_code = None
        if use_cached_code:
            cached_entry = self.database.get_cached_code(cache_key, schema_json)
            if cached_entry:
                cached_code = cached_entry["extraction_code"]
                logger.debug("Cache hit for %s", cache_key)
            else:
                logger.debug("Cache miss for %s", cache_key)

        if cached_code:
            extraction_code = cached_code
            is_fresh = False
            logger.debug("Using cached code for %s", cache_key)
        else:
            logger.info("Generating extraction code for %s", cache_key)
            code, success = self.code_generator.generate_extraction_code(
                url=cache_key, html_content=html_content, schema=schema_json
            )
            if not success:
                logger.error("Code generation failed for %s: %s", cache_key, code)
                raise RuntimeError(
                    f"Failed to generate valid extraction code for {cache_key}. Details: {code}"
                )
            extraction_code = code
            is_fresh = True

        # Step 2: Execute with regeneration loop
        for attempt in range(max_regenerate_attempts + 1):
            logger.debug(
                "Attempt %d/%d for %s", attempt + 1, max_regenerate_attempts + 1, cache_key
            )

            result, success, error_msg = self._try_code(
                code=extraction_code,
                html_content=html_content,
                schema=schema,
                schema_json=schema_json,
                is_fresh=is_fresh,
                validate_quality=validate_quality,
            )

            if success:
                if is_fresh:
                    logger.debug("Caching extraction code for %s", cache_key)
                    self.database.save_extraction_code(
                        cache_key, schema_json, extraction_code
                    )
                    logger.info(
                        "Success after %d regeneration attempts for %s", attempt, cache_key
                    )
                return result

            logger.warning("Attempt %d failed for %s: %s", attempt + 1, cache_key, error_msg)

            if attempt >= max_regenerate_attempts:
                raise RuntimeError(
                    f"Extraction failed after {attempt + 1} attempts: {error_msg}"
                )

            logger.info(
                "Regenerating code for %s (attempt %d/%d)",
                cache_key,
                attempt + 1,
                max_regenerate_attempts,
            )

            new_code, regen_success = self.code_generator.regenerate_code(
                url=cache_key,
                html_content=html_content,
                schema=schema_json,
                old_code=extraction_code,
                error_message=error_msg,
            )

            if not regen_success:
                logger.error("Regeneration failed: %s", new_code)
                continue

            extraction_code = new_code
            is_fresh = True

        # Should never reach here - loop should return or raise
        raise RuntimeError(f"Extraction failed after exhausting all attempts for {cache_key}")

    def _try_code(
        self,
        code: str,
        html_content: str,
        schema: type[BaseModel],
        schema_json: str,
        is_fresh: bool,
        validate_quality: bool,
    ) -> tuple[Optional[BaseModel], bool, Optional[str]]:
        """Try executing code with validation. Reusable for initial + regenerated code.

        Args:
            code: Extraction code to execute
            html_content: HTML content to extract from
            schema: Pydantic BaseModel class
            schema_json: Schema as JSON string
            is_fresh: Whether this is freshly generated/regenerated code
            validate_quality: Whether to run LLM quality check

        Returns:
            Tuple of (result, success, error_message)
            - result: BaseModel instance if successful, None if failed
            - success: True if extraction succeeded and passed all validation
            - error_message: Error description if failed, None if succeeded
        """
        try:
            result = self.code_generator.execute_extraction_code(
                code=code,
                html_content=html_content,
                schema=schema,
            )

            if is_fresh and validate_quality:
                logger.debug("Running LLM quality check")
                quality_ok, quality_issues = self.code_generator.check_data_quality_with_llm(
                    result, schema_json
                )

                if not quality_ok and quality_issues:
                    error_msg = f"ValidationError: Data quality issues: {'; '.join(quality_issues)}"
                    logger.warning("Quality check failed: %s", error_msg)
                    return None, False, error_msg

            return result, True, None

        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            logger.debug("Code execution failed: %s", error_msg)
            return None, False, error_msg
