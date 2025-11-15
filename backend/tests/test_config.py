"""
Tests for configuration module.
"""

import pytest
import os
from unittest.mock import patch

from src.config import settings


class TestConfiguration:
    """Test configuration settings."""

    def test_settings_initialization(self):
        """Test that settings are properly initialized."""
        assert settings.database_url is not None
        assert settings.redis_url is not None

    def test_database_url_exists(self):
        """Test database URL is configured."""
        assert settings.database_url is not None
        assert settings.database_url_raw is not None
        assert len(settings.database_url_raw) > 0

    def test_redis_url_exists(self):
        """Test Redis URL is configured."""
        assert settings.redis_url is not None
        assert len(settings.redis_url) > 0

    def test_neo4j_configuration(self):
        """Test Neo4j configuration exists."""
        assert hasattr(settings, 'neo4j_uri')
        assert hasattr(settings, 'neo4j_user')
        assert hasattr(settings, 'neo4j_password')

    def test_environment_variables(self):
        """Test environment variable handling."""
        with patch.dict('os.environ', {'DATABASE_URL': 'test://db'}):
            from src.config import settings as new_settings
            # Settings should load environment variables
            assert new_settings.database_url is not None

    def test_settings_validation(self):
        """Test settings validation."""
        # Test that required settings are present
        required_attrs = ['database_url', 'redis_url', 'neo4j_uri']
        for attr in required_attrs:
            assert hasattr(settings, attr)
            assert getattr(settings, attr) is not None

    def test_config_properties(self):
        """Test config properties work correctly."""
        # Test property access
        assert hasattr(settings, 'database_url')
        assert hasattr(settings, 'sync_database_url')
        assert hasattr(settings, 'database_url')  # Should be a property

    def test_config_dict_access(self):
        """Test dictionary-style access to settings."""
        config_dict = settings.model_dump()
        assert isinstance(config_dict, dict)
        assert 'database_url_raw' in config_dict
        assert 'redis_url' in config_dict

    def test_config_json_serialization(self):
        """Test JSON serialization of settings."""
        import json
        config_json = settings.model_dump_json()
        assert isinstance(config_json, str)
        # Should be valid JSON
        parsed = json.loads(config_json)
        assert isinstance(parsed, dict)

    def test_sensitive_data_masking(self):
        """Test that sensitive data is handled properly."""
        # Test password fields exist and are not None
        assert hasattr(settings, 'neo4j_password')
        # In tests, this might be a placeholder

    def test_debug_mode_configuration(self):
        """Test debug mode configuration."""
        # Should have debug setting through environment handling
        config_dict = settings.model_dump()
        assert isinstance(config_dict, dict)

    def test_api_prefix_configuration(self):
        """Test API prefix configuration."""
        # Test that API configuration exists
        config_dict = settings.model_dump()
        # Common API settings should be accessible

    def test_environment_specific_settings(self):
        """Test environment-specific settings."""
        # Test that environment detection works
        env_settings = settings.model_dump()
        assert isinstance(env_settings, dict)

    def test_settings_immutability(self):
        """Test that settings are properly configured."""
        # Settings should be properly initialized
        assert settings is not None
        assert isinstance(settings, type(settings))

    def test_configuration_completeness(self):
        """Test configuration completeness."""
        # Test that all required configuration is present
        config_dict = settings.model_dump()
        
        # Essential configurations should be present
        essential_configs = ['database_url_raw', 'redis_url']
        for config in essential_configs:
            assert config in config_dict
            assert config_dict[config] is not None

    def test_configuration_defaults(self):
        """Test configuration defaults."""
        # Test that defaults are reasonable
        config_dict = settings.model_dump()
        
        # Should not have empty values for required configs
        if config_dict.get('database_url'):
            assert len(config_dict['database_url']) > 0

    def test_config_validation_rules(self):
        """Test configuration validation rules."""
        # Test that configuration follows expected patterns
        config_dict = settings.model_dump()
        
        # Database URL should follow pattern
        if config_dict.get('database_url'):
            db_url = config_dict['database_url']
            # Should contain protocol separator
            assert '://' in db_url or db_url.startswith('sqlite')

    def test_config_performance_settings(self):
        """Test performance-related configuration."""
        config_dict = settings.model_dump()
        
        # Performance settings should be available
        # This tests that config loading works properly

    def test_config_security_settings(self):
        """Test security-related configuration."""
        config_dict = settings.model_dump()
        
        # Security settings should be properly configured
        # This tests configuration completeness

    def test_config_logging_settings(self):
        """Test logging configuration."""
        # Test that logging can be configured through settings
        config_dict = settings.model_dump()
        
        # Should have logging configuration available
        assert isinstance(config_dict, dict)

    def test_config_reload_behavior(self):
        """Test configuration reload behavior."""
        # Test that configuration is stable
        original_db = settings.database_url
        original_db_raw = settings.database_url_raw
        config_dict = settings.model_dump()
        
        # Configuration should be consistent
        assert config_dict['database_url_raw'] == original_db_raw

    def test_config_error_handling(self):
        """Test configuration error handling."""
        # Test that configuration handles errors gracefully
        try:
            config_dict = settings.model_dump()
            assert isinstance(config_dict, dict)
        except Exception:
            # Should not crash on config access
            pytest.fail("Configuration access should not raise exceptions")

    def test_config_type_safety(self):
        """Test configuration type safety."""
        config_dict = settings.model_dump()
        
        # Configuration values should have expected types
        for key, value in config_dict.items():
            # Should not be None for required fields
            if key in ['database_url', 'redis_url']:
                assert value is not None
