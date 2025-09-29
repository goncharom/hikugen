# ABOUTME: Main Hikugen package for AI-powered web scraping
# ABOUTME: Provides HikuExtractor class and utilities for extracting data into Pydantic schemas

__version__ = "0.1.0"
__author__ = "goncharom"
__description__ = "AI-powered web scraping library with Pydantic schema extraction"

# Main exports
from .extractor import HikuExtractor
from .database import HikuDatabase
from .code_generator import HikuCodeGenerator
from .http_client import fetch_page_content
from .code_validation import validate_code_complete
from .prompts import (
    format_generation_prompt,
    format_regeneration_prompt,
    format_quality_check_prompt,
)

__all__ = [
    "HikuExtractor",
    "HikuDatabase",
    "HikuCodeGenerator",
    "fetch_page_content",
    "validate_code_complete",
    "format_generation_prompt",
    "format_regeneration_prompt",
    "format_quality_check_prompt",
]
