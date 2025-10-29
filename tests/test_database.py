# ABOUTME: Test suite for Hiku database schema and operations
# ABOUTME: Tests SQLite database functionality for Pydantic schema caching

import pytest
import sqlite3
from datetime import datetime
from hikugen.database import HikuDatabase


class TestDatabaseSchema:
    """Test database table creation and schema."""

    def test_create_tables(self, temp_db):
        """Test that extraction_cache table is created with correct schema."""
        temp_db.create_tables()

        cursor = temp_db.connection.cursor()

        # Check that extraction_cache table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "extraction_cache" in tables

        # Check extraction_cache table schema
        cursor.execute("PRAGMA table_info(extraction_cache)")
        cache_columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert "cache_key" in cache_columns
        assert "schema_hash" in cache_columns
        assert "extraction_code" in cache_columns
        assert "last_successful_run" in cache_columns
        assert cache_columns["cache_key"] == "TEXT"
        assert cache_columns["schema_hash"] == "TEXT"


class TestSchemaHashing:
    """Test Pydantic schema hashing for cache keys."""

    def test_generate_schema_hash(self, temp_db, sample_pydantic_schema):
        """Test that schema hash is generated consistently."""
        hash1 = temp_db.generate_schema_hash(sample_pydantic_schema)
        hash2 = temp_db.generate_schema_hash(sample_pydantic_schema)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex length
        assert isinstance(hash1, str)

    def test_different_schemas_different_hashes(self, temp_db):
        """Test that different schemas produce different hashes."""
        schema1 = "class Model1(BaseModel): field1: str"
        schema2 = "class Model2(BaseModel): field2: int"

        hash1 = temp_db.generate_schema_hash(schema1)
        hash2 = temp_db.generate_schema_hash(schema2)

        assert hash1 != hash2


class TestCacheOperations:
    """Test extraction code caching operations."""

    def test_save_and_get_cached_code(self, temp_db, sample_pydantic_schema, sample_extraction_code):
        """Test saving and retrieving cached extraction code."""
        temp_db.create_tables()

        cache_key = "https://example.com"
        schema_hash = temp_db.generate_schema_hash(sample_pydantic_schema)

        # Save extraction code
        temp_db.save_extraction_code(cache_key, sample_pydantic_schema, sample_extraction_code)

        # Retrieve cached code
        cached_code = temp_db.get_cached_code(cache_key, sample_pydantic_schema)

        assert cached_code is not None
        assert cached_code["extraction_code"] == sample_extraction_code
        assert cached_code["cache_key"] == cache_key
        assert cached_code["schema_hash"] == schema_hash
        assert cached_code["last_successful_run"] is None

    def test_get_cached_code_not_found(self, temp_db, sample_pydantic_schema):
        """Test getting cached code for non-existent URL/schema combination."""
        temp_db.create_tables()

        cached_code = temp_db.get_cached_code("https://nonexistent.com", sample_pydantic_schema)
        assert cached_code is None

    def test_update_existing_cache_entry(self, temp_db, sample_pydantic_schema):
        """Test updating existing cache entry with new code."""
        temp_db.create_tables()

        url = "https://example.com"
        code1 = "def extract_data(html): return Model(field='v1')"
        code2 = "def extract_data(html): return Model(field='v2')"

        # Save initial code
        temp_db.save_extraction_code(url, sample_pydantic_schema, code1)

        # Update with new code
        temp_db.save_extraction_code(url, sample_pydantic_schema, code2)

        # Should get updated code
        cached_code = temp_db.get_cached_code(url, sample_pydantic_schema)
        assert cached_code["extraction_code"] == code2

    def test_update_last_successful_run(self, temp_db, sample_pydantic_schema, sample_extraction_code):
        """Test updating last successful run timestamp."""
        temp_db.create_tables()

        url = "https://example.com"
        temp_db.save_extraction_code(url, sample_pydantic_schema, sample_extraction_code)

        now = datetime.now()
        temp_db.update_last_successful_run(url, sample_pydantic_schema, now)

        cached_code = temp_db.get_cached_code(url, sample_pydantic_schema)
        assert cached_code["last_successful_run"] == now.isoformat()


class TestCacheKeyGeneration:
    """Test cache key generation logic."""

    def test_cache_key_generation(self, temp_db, sample_pydantic_schema):
        """Test that cache key combines URL and schema hash correctly."""
        url = "https://example.com"
        schema_hash = temp_db.generate_schema_hash(sample_pydantic_schema)

        # The cache key should be deterministic
        key1 = temp_db.generate_cache_key(url, sample_pydantic_schema)
        key2 = temp_db.generate_cache_key(url, sample_pydantic_schema)

        assert key1 == key2
        assert url in key1 or schema_hash in key1  # Should involve both components

    def test_different_urls_different_keys(self, temp_db, sample_pydantic_schema):
        """Test that different URLs produce different cache keys."""
        key1 = temp_db.generate_cache_key("https://site1.com", sample_pydantic_schema)
        key2 = temp_db.generate_cache_key("https://site2.com", sample_pydantic_schema)

        assert key1 != key2


class TestDatabaseContextManager:
    """Test database connection management."""

    def test_context_manager(self, sample_pydantic_schema, sample_extraction_code):
        """Test database can be used as context manager."""
        with HikuDatabase(":memory:") as db:
            db.create_tables()
            db.save_extraction_code("https://test.com", sample_pydantic_schema, sample_extraction_code)
            cached_code = db.get_cached_code("https://test.com", sample_pydantic_schema)
            assert cached_code is not None

    def test_close_connection(self, temp_db):
        """Test that database connection can be closed."""
        temp_db.create_tables()
        temp_db.close()

        # Connection should be closed
        with pytest.raises(sqlite3.ProgrammingError):
            temp_db.connection.execute("SELECT 1")


class TestGenericCacheKeys:
    """Test generic cache key functionality for name-based caching."""

    def test_schema_uses_cache_key_column(self, temp_db):
        """Test that extraction_cache table has cache_key column instead of url."""
        temp_db.create_tables()

        cursor = temp_db.connection.cursor()
        cursor.execute("PRAGMA table_info(extraction_cache)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}

        assert "cache_key" in columns
        assert columns["cache_key"] == "TEXT"
        assert "url" not in columns

    def test_save_with_cache_key(self, temp_db, sample_pydantic_schema, sample_extraction_code):
        """Test saving extraction code with generic cache_key."""
        temp_db.create_tables()

        cache_key = "my_extraction_task"
        temp_db.save_extraction_code(cache_key, sample_pydantic_schema, sample_extraction_code)

        cached_code = temp_db.get_cached_code(cache_key, sample_pydantic_schema)
        assert cached_code is not None
        assert cached_code["extraction_code"] == sample_extraction_code
        assert cached_code["cache_key"] == cache_key

    def test_get_cached_code_with_cache_key(self, temp_db, sample_pydantic_schema, sample_extraction_code):
        """Test retrieving cached code with generic cache_key."""
        temp_db.create_tables()

        cache_key = "another_task"
        temp_db.save_extraction_code(cache_key, sample_pydantic_schema, sample_extraction_code)

        cached_code = temp_db.get_cached_code(cache_key, sample_pydantic_schema)
        assert cached_code["cache_key"] == cache_key
        assert cached_code["extraction_code"] == sample_extraction_code

    def test_different_cache_keys_separate_entries(self, temp_db, sample_pydantic_schema):
        """Test that different cache keys create separate cache entries."""
        temp_db.create_tables()

        code1 = "def extract_data(html): return {'field': 'v1'}"
        code2 = "def extract_data(html): return {'field': 'v2'}"

        temp_db.save_extraction_code("task1", sample_pydantic_schema, code1)
        temp_db.save_extraction_code("task2", sample_pydantic_schema, code2)

        cached1 = temp_db.get_cached_code("task1", sample_pydantic_schema)
        cached2 = temp_db.get_cached_code("task2", sample_pydantic_schema)

        assert cached1["extraction_code"] == code1
        assert cached2["extraction_code"] == code2

    def test_url_cache_keys_still_work(self, temp_db, sample_pydantic_schema, sample_extraction_code):
        """Test that URL-style cache keys (backwards compatibility) still work."""
        temp_db.create_tables()

        url_cache_key = "https://example.com"
        temp_db.save_extraction_code(url_cache_key, sample_pydantic_schema, sample_extraction_code)

        cached_code = temp_db.get_cached_code(url_cache_key, sample_pydantic_schema)
        assert cached_code is not None
        assert cached_code["cache_key"] == url_cache_key
        assert cached_code["extraction_code"] == sample_extraction_code


class TestCacheClearingOperations:
    """Test cache clearing operations."""

    def test_clear_all_cache_empty_database(self, temp_db):
        """Test that clearing empty database returns 0."""
        temp_db.create_tables()
        count = temp_db.clear_all_cache()
        assert count == 0

    def test_clear_all_cache_removes_all_entries(self, temp_db, sample_pydantic_schema, sample_extraction_code):
        """Test that clearing all cache removes all entries."""
        temp_db.create_tables()

        # Save multiple entries
        temp_db.save_extraction_code("key1", sample_pydantic_schema, sample_extraction_code)
        temp_db.save_extraction_code("key2", sample_pydantic_schema, sample_extraction_code)

        # Verify entries exist
        assert temp_db.get_cached_code("key1", sample_pydantic_schema) is not None
        assert temp_db.get_cached_code("key2", sample_pydantic_schema) is not None

        # Clear all cache
        count = temp_db.clear_all_cache()
        assert count == 2

        # Verify entries are deleted
        assert temp_db.get_cached_code("key1", sample_pydantic_schema) is None
        assert temp_db.get_cached_code("key2", sample_pydantic_schema) is None

    def test_clear_all_cache_returns_correct_count(self, temp_db, sample_pydantic_schema, sample_extraction_code):
        """Test that clearing all cache returns accurate deletion count."""
        temp_db.create_tables()

        # Save 5 entries
        for i in range(5):
            temp_db.save_extraction_code(f"key{i}", sample_pydantic_schema, sample_extraction_code)

        count = temp_db.clear_all_cache()
        assert count == 5

    def test_clear_cache_for_key_single_schema(self, temp_db, sample_pydantic_schema, sample_extraction_code):
        """Test clearing cache key with single schema variant."""
        temp_db.create_tables()

        cache_key = "https://example.com"
        temp_db.save_extraction_code(cache_key, sample_pydantic_schema, sample_extraction_code)

        # Verify entry exists
        assert temp_db.get_cached_code(cache_key, sample_pydantic_schema) is not None

        # Clear specific key
        count = temp_db.clear_cache_for_key(cache_key)
        assert count == 1

        # Verify entry is deleted
        assert temp_db.get_cached_code(cache_key, sample_pydantic_schema) is None

    def test_clear_cache_for_key_multiple_schemas(self, temp_db, sample_pydantic_schema, sample_extraction_code):
        """Test clearing cache key with multiple schema variants."""
        temp_db.create_tables()

        cache_key = "https://example.com"
        schema2 = "class Model2(BaseModel): field: int"

        # Save same cache_key with different schemas
        temp_db.save_extraction_code(cache_key, sample_pydantic_schema, sample_extraction_code)
        temp_db.save_extraction_code(cache_key, schema2, sample_extraction_code)

        # Verify both entries exist
        assert temp_db.get_cached_code(cache_key, sample_pydantic_schema) is not None
        assert temp_db.get_cached_code(cache_key, schema2) is not None

        # Clear specific key (should delete all variants)
        count = temp_db.clear_cache_for_key(cache_key)
        assert count == 2

        # Verify both entries are deleted
        assert temp_db.get_cached_code(cache_key, sample_pydantic_schema) is None
        assert temp_db.get_cached_code(cache_key, schema2) is None

    def test_clear_cache_for_key_nonexistent(self, temp_db):
        """Test clearing non-existent cache key returns 0."""
        temp_db.create_tables()
        count = temp_db.clear_cache_for_key("nonexistent_key")
        assert count == 0

    def test_clear_cache_for_key_preserves_others(self, temp_db, sample_pydantic_schema, sample_extraction_code):
        """Test that clearing specific key preserves other keys."""
        temp_db.create_tables()

        # Save entries with different keys
        temp_db.save_extraction_code("key1", sample_pydantic_schema, sample_extraction_code)
        temp_db.save_extraction_code("key2", sample_pydantic_schema, sample_extraction_code)
        temp_db.save_extraction_code("key3", sample_pydantic_schema, sample_extraction_code)

        # Clear key2
        count = temp_db.clear_cache_for_key("key2")
        assert count == 1

        # Verify key1 and key3 still exist
        assert temp_db.get_cached_code("key1", sample_pydantic_schema) is not None
        assert temp_db.get_cached_code("key2", sample_pydantic_schema) is None
        assert temp_db.get_cached_code("key3", sample_pydantic_schema) is not None

    def test_clear_cache_for_key_url_style(self, temp_db, sample_pydantic_schema, sample_extraction_code):
        """Test clearing cache with URL-style cache keys."""
        temp_db.create_tables()

        url_key = "https://example.com/page"
        temp_db.save_extraction_code(url_key, sample_pydantic_schema, sample_extraction_code)

        count = temp_db.clear_cache_for_key(url_key)
        assert count == 1
        assert temp_db.get_cached_code(url_key, sample_pydantic_schema) is None

    def test_clear_cache_for_key_task_style(self, temp_db, sample_pydantic_schema, sample_extraction_code):
        """Test clearing cache with task-name style cache keys."""
        temp_db.create_tables()

        task_key = "amazon_scraper_task"
        temp_db.save_extraction_code(task_key, sample_pydantic_schema, sample_extraction_code)

        count = temp_db.clear_cache_for_key(task_key)
        assert count == 1
        assert temp_db.get_cached_code(task_key, sample_pydantic_schema) is None