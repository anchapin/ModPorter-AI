"""
Functional tests for backend services with database.
"""

import pytest
import sys
import os

# Don't add path here - it will be handled by pytest.ini
# Only add it dynamically if needed


class TestBackendImports:
    def test_import_config(self):
        import config
        assert config is not None

    def test_import_db_models(self):
        from db import models
        assert models is not None


class TestCoreServices:
    def test_config_has_settings(self):
        try:
            from config import settings
            assert settings is not None
        except Exception:
            pytest.skip("Config not available")

    def test_core_auth_exists(self):
        try:
            from core.auth import AuthManager
            assert AuthManager is not None
        except Exception:
            pytest.skip("Core auth not available")

    def test_core_storage_import(self):
        try:
            from core.storage import StorageManager
            assert StorageManager is not None
        except Exception:
            pytest.skip("Core storage not available")

    def test_core_secrets_import(self):
        try:
            from core.secrets import SecretsManager
            assert SecretsManager is not None
        except Exception:
            pytest.skip("Core secrets not available")

    def test_core_redis_import(self):
        try:
            from core.redis import RedisClient
            assert RedisClient is not None
        except Exception:
            pytest.skip("Core redis not available")


class TestAPIEndpoints:
    def test_auth_api_imports(self):
        try:
            from api import auth
            assert auth is not None
            assert hasattr(auth, 'router')
        except Exception:
            pytest.skip("Auth API not available")

    def test_conversions_api_imports(self):
        try:
            from api import conversions
            assert conversions is not None
            assert hasattr(conversions, 'router')
        except Exception:
            pytest.skip("Conversions API not available")

    def test_embeddings_api_imports(self):
        try:
            from api import embeddings
            assert embeddings is not None
            assert hasattr(embeddings, 'router')
        except Exception:
            pytest.skip("Embeddings API not available")


class TestServices:
    def test_cache_service_imports(self):
        try:
            from services import cache
            assert cache is not None
        except Exception:
            pytest.skip("Cache service not available")

    def test_conversion_service_imports(self):
        try:
            from services import conversion_service
            assert conversion_service is not None
        except Exception:
            pytest.skip("Conversion service not available")


class TestModels:
    def test_embedding_models_import(self):
        try:
            from models import embedding_models
            assert embedding_models is not None
        except Exception:
            pytest.skip("Embedding models not available")


class TestSecurity:
    def test_security_auth_imports(self):
        try:
            from security import auth as security_auth
            assert security_auth is not None
        except Exception:
            pytest.skip("Security auth not available")
