"""Tests for config.py module."""

import pytest
import os
from unittest.mock import patch

from src.config import Settings


class TestSettings:
    """Test cases for Settings class."""

    def test_settings_initialization_with_defaults(self):
        """Test Settings initialization with default values."""
        settings = Settings()
        
        assert "postgresql://" in settings.database_url_raw
        assert settings.redis_url == "redis://localhost:6379"
        assert settings.neo4j_uri == "bolt://localhost:7687"
        assert settings.neo4j_user == "neo4j"
        assert settings.neo4j_password == "password"

    def test_settings_from_environment(self):
        """Test Settings loading from environment variables."""
        with patch.dict(os.environ, {
            'DATABASE_URL': 'postgresql://user:pass@host:5432/db',
            'REDIS_URL': 'redis://redis:6380',
            'NEO4J_URI': 'bolt://neo4j:7688',
            'NEO4J_USER': 'admin',
            'NEO4J_PASSWORD': 'adminpass'
        }):
            settings = Settings()
            
            assert settings.database_url_raw == 'postgresql://user:pass@host:5432/db'
            assert settings.redis_url == 'redis://redis:6380'
            assert settings.neo4j_uri == 'bolt://neo4j:7688'
            assert settings.neo4j_user == 'admin'
            assert settings.neo4j_password == 'adminpass'

    def test_database_url_property_postgresql(self):
        """Test database_url property conversion for PostgreSQL."""
        with patch.dict(os.environ, {}, clear=True):  # Clear TESTING env
            settings = Settings()
            settings.database_url_raw = "postgresql://user:pass@host:5432/db"
            
            # Should convert to async format
            assert settings.database_url == "postgresql+asyncpg://user:pass@host:5432/db"

    def test_database_url_property_non_postgresql(self):
        """Test database_url property for non-PostgreSQL URLs."""
        with patch.dict(os.environ, {}, clear=True):  # Clear TESTING env
            settings = Settings()
            settings.database_url_raw = "sqlite:///test.db"
            
            # Should return as-is for non-PostgreSQL
            assert settings.database_url == "sqlite:///test.db"

    def test_database_url_property_testing_mode(self):
        """Test database_url property in testing mode."""
        with patch.dict(os.environ, {'TESTING': 'true'}):
            settings = Settings()
            
            # Should use SQLite in testing mode by default
            assert "sqlite+aiosqlite" in settings.database_url
            assert "test.db" in settings.database_url

    def test_database_url_property_testing_mode_custom(self):
        """Test database_url property in testing mode with custom URL."""
        with patch.dict(os.environ, {
            'TESTING': 'true',
            'TEST_DATABASE_URL': 'sqlite+aiosqlite:///test_custom.db'
        }):
            settings = Settings()
            
            assert settings.database_url == 'sqlite+aiosqlite:///test_custom.db'

    def test_sync_database_url_property(self):
        """Test sync_database_url property for migrations."""
        # Test with PostgreSQL async URL
        settings = Settings()
        settings.database_url_raw = "postgresql+asyncpg://user:pass@host:5432/db"
        
        # Should convert to sync format
        assert settings.sync_database_url == "postgresql://user:pass@host:5432/db"

    def test_sync_database_url_property_already_sync(self):
        """Test sync_database_url property with already sync URL."""
        settings = Settings()
        settings.database_url_raw = "postgresql://user:pass@host:5432/db"
        
        # Should return as-is
        assert settings.sync_database_url == "postgresql://user:pass@host:5432/db"

    def test_settings_model_config(self):
        """Test that model config includes env_file settings."""
        settings = Settings()
        
        # Check that the model_config exists
        assert hasattr(settings, 'model_config')
        assert 'env_file' in settings.model_config
        assert '../.env' in settings.model_config['env_file']
        assert '../.env.local' in settings.model_config['env_file']

    def test_settings_extra_ignore(self):
        """Test that extra environment variables are ignored."""
        with patch.dict(os.environ, {'EXTRA_VAR': 'should_be_ignored'}):
            # Should not raise error for extra variables
            settings = Settings()
            assert not hasattr(settings, 'extra_var')

    def test_database_url_field_alias(self):
        """Test that DATABASE_URL field uses proper alias."""
        with patch.dict(os.environ, {'DATABASE_URL': 'custom://url'}):
            settings = Settings()
            assert settings.database_url_raw == 'custom://url'

    def test_redis_url_field_alias(self):
        """Test that REDIS_URL field uses proper alias."""
        with patch.dict(os.environ, {'REDIS_URL': 'redis://custom:6379'}):
            settings = Settings()
            assert settings.redis_url == 'redis://custom:6379'

    def test_neo4j_field_aliases(self):
        """Test Neo4j field aliases."""
        with patch.dict(os.environ, {
            'NEO4J_URI': 'bolt://custom:7687',
            'NEO4J_USER': 'custom_user',
            'NEO4J_PASSWORD': 'custom_pass'
        }):
            settings = Settings()
            assert settings.neo4j_uri == 'bolt://custom:7687'
            assert settings.neo4j_user == 'custom_user'
            assert settings.neo4j_password == 'custom_pass'

    def test_database_url_property_edge_case(self):
        """Test database_url property with edge case URLs."""
        with patch.dict(os.environ, {}, clear=True):  # Clear TESTING env
            settings = Settings()
            
            # Test with complex PostgreSQL URL
            complex_url = "postgresql://user:p@ss:w0rd@host:5432/db?sslmode=require"
            settings.database_url_raw = complex_url
            assert settings.database_url == "postgresql+asyncpg://user:p@ss:w0rd@host:5432/db?sslmode=require"

    def test_sync_database_url_property_edge_case(self):
        """Test sync_database_url property with edge case URLs."""
        settings = Settings()
        
        # Test with complex PostgreSQL async URL
        complex_async_url = "postgresql+asyncpg://user:p@ss:w0rd@host:5432/db?sslmode=require"
        settings.database_url_raw = complex_async_url
        assert settings.sync_database_url == "postgresql://user:p@ss:w0rd@host:5432/db?sslmode=require"
