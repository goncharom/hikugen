# ABOUTME: SQLite database operations for Hikugen extraction code caching
# ABOUTME: Implements CRUD operations for Pydantic schema-based extraction code caching

import sqlite3
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional

EXTRACTION_CACHE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS extraction_cache (
        cache_key TEXT,
        schema_hash TEXT,
        extraction_code TEXT,
        last_successful_run TEXT,
        PRIMARY KEY (cache_key, schema_hash)
    )
"""


class HikuDatabase:
    """SQLite database manager for Hiku extraction code caching."""

    def __init__(self, db_path: str = "hikugen.db"):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.connection = sqlite3.connect(db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        # Enable foreign key constraints
        self.connection.execute("PRAGMA foreign_keys = ON")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()

    def create_tables(self):
        """Create extraction_cache table for Pydantic schema caching."""
        cursor = self.connection.cursor()

        # Create extraction cache table
        cursor.execute(EXTRACTION_CACHE_TABLE_SQL)

        self.connection.commit()

    def generate_schema_hash(self, pydantic_schema: str) -> str:
        """Generate SHA-256 hash of Pydantic schema for cache key.

        Args:
            pydantic_schema: String representation of Pydantic schema

        Returns:
            SHA-256 hash of the schema as hex string
        """
        # Normalize schema by removing extra whitespace for consistent hashing
        normalized_schema = " ".join(pydantic_schema.split())
        return hashlib.sha256(normalized_schema.encode('utf-8')).hexdigest()

    def generate_cache_key(self, name: str, pydantic_schema: str) -> str:
        """Generate cache key combining name and schema hash.

        Args:
            name: Identifier (URL, task name, or any unique identifier)
            pydantic_schema: Pydantic schema string

        Returns:
            Cache key combining name and schema
        """
        schema_hash = self.generate_schema_hash(pydantic_schema)
        return f"{name}:{schema_hash}"

    def save_extraction_code(self, cache_key: str, pydantic_schema: str, extraction_code: str):
        """Save or update extraction code for cache_key and schema combination.

        Args:
            cache_key: Generic cache identifier (URL, task name, etc.)
            pydantic_schema: Pydantic schema string
            extraction_code: Python extraction code
        """
        cursor = self.connection.cursor()
        schema_hash = self.generate_schema_hash(pydantic_schema)

        cursor.execute(
            """INSERT OR REPLACE INTO extraction_cache
               (cache_key, schema_hash, extraction_code, last_successful_run)
               VALUES (?, ?, ?, ?)""",
            (cache_key, schema_hash, extraction_code, None),
        )

        self.connection.commit()

    def get_cached_code(self, cache_key: str, pydantic_schema: str) -> Optional[Dict[str, Any]]:
        """Get cached extraction code for cache_key and schema combination.

        Args:
            cache_key: Generic cache identifier (URL, task name, etc.)
            pydantic_schema: Pydantic schema string

        Returns:
            Cached entry dictionary or None if not found
        """
        cursor = self.connection.cursor()
        schema_hash = self.generate_schema_hash(pydantic_schema)

        cursor.execute(
            "SELECT * FROM extraction_cache WHERE cache_key = ? AND schema_hash = ?",
            (cache_key, schema_hash),
        )
        row = cursor.fetchone()
        return dict(row) if row else None

    def update_last_successful_run(self, cache_key: str, pydantic_schema: str, timestamp: datetime):
        """Update last successful run timestamp for cache_key and schema combination.

        Args:
            cache_key: Generic cache identifier (URL, task name, etc.)
            pydantic_schema: Pydantic schema string
            timestamp: Last successful extraction timestamp
        """
        cursor = self.connection.cursor()
        schema_hash = self.generate_schema_hash(pydantic_schema)

        cursor.execute(
            """UPDATE extraction_cache
               SET last_successful_run = ?
               WHERE cache_key = ? AND schema_hash = ?""",
            (timestamp.isoformat(), cache_key, schema_hash),
        )
        self.connection.commit()

    def get_all_cached_entries(self) -> list[Dict[str, Any]]:
        """Get all cached extraction entries.

        Returns:
            List of all cached entry dictionaries
        """
        cursor = self.connection.cursor()
        cursor.execute("SELECT * FROM extraction_cache")
        return [dict(row) for row in cursor.fetchall()]