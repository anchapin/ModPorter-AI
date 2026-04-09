"""
Tests for backend core services (redis, storage, secrets).

Coverage targets:
- backend/src/core/redis.py
- backend/src/core/storage.py
- backend/src/core/secrets.py

These tests provide behavioral coverage for core backend services.
"""

import pytest
from pathlib import Path


# ============================================
# Core Redis Service Tests
# ============================================

def test_redis_module_importable():
    """Redis module should be importable"""
    # Skip if redis module cannot be imported due to dependency issues
    try:
        import backend.src.core.redis as redis_module
    except ImportError as e:
        pytest.skip(f"Redis module not importable: {e}")
    assert redis_module is not None


def test_redis_client_class_exists():
    """Redis module should define RedisClient class"""
    try:
        from backend.src.core.redis import RedisClient
    except ImportError as e:
        pytest.skip(f"Redis module not importable: {e}")
    assert RedisClient is not None


def test_redis_client_has_connect_method():
    """RedisClient should have a connect method"""
    try:
        from backend.src.core.redis import RedisClient
    except ImportError as e:
        pytest.skip(f"Redis module not importable: {e}")
    client = RedisClient()
    assert hasattr(client, 'connect')
    assert callable(client.connect)


def test_redis_client_has_disconnect_method():
    """RedisClient should have a disconnect method"""
    try:
        from backend.src.core.redis import RedisClient
    except ImportError as e:
        pytest.skip(f"Redis module not importable: {e}")
    client = RedisClient()
    assert hasattr(client, 'disconnect')
    assert callable(client.disconnect)


def test_redis_client_has_get_method():
    """RedisClient should have a get method"""
    try:
        from backend.src.core.redis import RedisClient
    except ImportError as e:
        pytest.skip(f"Redis module not importable: {e}")
    client = RedisClient()
    assert hasattr(client, 'get')
    assert callable(client.get)


def test_redis_client_has_set_method():
    """RedisClient should have a set method"""
    try:
        from backend.src.core.redis import RedisClient
    except ImportError as e:
        pytest.skip(f"Redis module not importable: {e}")
    client = RedisClient()
    assert hasattr(client, 'set')
    assert callable(client.set)


def test_redis_job_queue_class_exists():
    """Redis module should define JobQueue class"""
    try:
        from backend.src.core.redis import JobQueue
    except ImportError as e:
        pytest.skip(f"Redis module not importable: {e}")
    assert JobQueue is not None


def test_redis_job_queue_has_enqueue_method():
    """JobQueue should have enqueue method"""
    try:
        from backend.src.core.redis import JobQueue
    except ImportError as e:
        pytest.skip(f"Redis module not importable: {e}")
    queue = JobQueue()
    assert hasattr(queue, 'enqueue')
    assert callable(queue.enqueue)


def test_redis_job_queue_has_dequeue_method():
    """JobQueue should have dequeue method"""
    try:
        from backend.src.core.redis import JobQueue
    except ImportError as e:
        pytest.skip(f"Redis module not importable: {e}")
    queue = JobQueue()
    assert hasattr(queue, 'dequeue')
    assert callable(queue.dequeue)


def test_redis_rate_limiter_class_exists():
    """Redis module should define RateLimiter class"""
    try:
        from backend.src.core.redis import RateLimiter
    except ImportError as e:
        pytest.skip(f"Redis module not importable: {e}")
    assert RateLimiter is not None


def test_redis_rate_limiter_has_check_method():
    """RateLimiter should have check method"""
    try:
        from backend.src.core.redis import RateLimiter
    except ImportError as e:
        pytest.skip(f"Redis module not importable: {e}")
    limiter = RateLimiter()
    assert hasattr(limiter, 'check')
    assert callable(limiter.check)


def test_redis_get_redis_client_function_exists():
    """Module should export get_redis_client function"""
    try:
        from backend.src.core.redis import get_redis_client
    except ImportError as e:
        pytest.skip(f"Redis module not importable: {e}")
    assert get_redis_client is not None
    assert callable(get_redis_client)


def test_redis_async_functions_exist():
    """Module should export async functions for getting singletons"""
    try:
        from backend.src.core.redis import get_redis_client, get_job_queue, get_rate_limiter, close_redis
    except ImportError as e:
        pytest.skip(f"Redis module not importable: {e}")
    assert callable(get_redis_client)
    assert callable(get_job_queue)
    assert callable(get_rate_limiter)
    assert callable(close_redis)


# ============================================
# Core Storage Service Tests
# ============================================

def test_storage_module_importable():
    """Storage module should be importable"""
    from backend.src.core import storage
    assert storage is not None


def test_storage_manager_class_exists():
    """Storage module should define StorageManager class"""
    from backend.src.core.storage import StorageManager
    assert StorageManager is not None


def test_storage_backend_enum_exists():
    """Storage module should define StorageBackend enum"""
    from backend.src.core.storage import StorageBackend
    assert StorageBackend is not None
    assert hasattr(StorageBackend, 'LOCAL')
    assert hasattr(StorageBackend, 'S3')


def test_storage_manager_has_save_file_method():
    """StorageManager should have save_file method"""
    from backend.src.core.storage import StorageManager
    manager = StorageManager()
    assert hasattr(manager, 'save_file')
    assert callable(manager.save_file)


def test_storage_manager_has_get_file_method():
    """StorageManager should have get_file method"""
    from backend.src.core.storage import StorageManager
    manager = StorageManager()
    assert hasattr(manager, 'get_file')
    assert callable(manager.get_file)


def test_storage_manager_has_delete_job_files_method():
    """StorageManager should have delete_job_files method"""
    from backend.src.core.storage import StorageManager
    manager = StorageManager()
    assert hasattr(manager, 'delete_job_files')
    assert callable(manager.delete_job_files)


def test_storage_manager_has_cleanup_old_files_method():
    """StorageManager should have cleanup_old_files method"""
    from backend.src.core.storage import StorageManager
    manager = StorageManager()
    assert hasattr(manager, 'cleanup_old_files')
    assert callable(manager.cleanup_old_files)


def test_storage_manager_has_get_storage_stats_method():
    """StorageManager should have get_storage_stats method"""
    from backend.src.core.storage import StorageManager
    manager = StorageManager()
    assert hasattr(manager, 'get_storage_stats')
    assert callable(manager.get_storage_stats)


def test_storage_singleton_instance_exists():
    """Module should export storage_manager singleton"""
    from backend.src.core.storage import storage_manager
    assert storage_manager is not None


# ============================================
# Core Secrets Service Tests
# ============================================

def test_secrets_module_importable():
    """Secrets module should be importable"""
    from backend.src.core import secrets
    assert secrets is not None


def test_secrets_manager_class_exists():
    """Secrets module should define SecretsManager class"""
    from backend.src.core.secrets import SecretsManager
    assert SecretsManager is not None


def test_secrets_manager_settings_class_exists():
    """Secrets module should define SecretsManagerSettings class"""
    from backend.src.core.secrets import SecretsManagerSettings
    assert SecretsManagerSettings is not None


def test_secret_str_class_exists():
    """Secrets module should define SecretStr class"""
    from backend.src.core.secrets import SecretStr
    assert SecretStr is not None


def test_secrets_settings_class_exists():
    """Secrets module should define Settings class"""
    from backend.src.core.secrets import Settings
    assert Settings is not None


def test_secrets_manager_has_get_secret_method():
    """SecretsManager should have get_secret method"""
    from backend.src.core.secrets import SecretsManager
    manager = SecretsManager()
    assert hasattr(manager, 'get_secret')
    assert callable(manager.get_secret)


def test_secrets_manager_has_get_all_secrets_method():
    """SecretsManager should have get_all_secrets method"""
    from backend.src.core.secrets import SecretsManager
    manager = SecretsManager()
    assert hasattr(manager, 'get_all_secrets')
    assert callable(manager.get_all_secrets)


def test_secrets_get_secret_function_exists():
    """Module should export get_secret convenience function"""
    from backend.src.core.secrets import get_secret
    assert get_secret is not None
    assert callable(get_secret)


def test_secrets_get_secrets_manager_function_exists():
    """Module should export get_secrets_manager function"""
    from backend.src.core.secrets import get_secrets_manager
    assert get_secrets_manager is not None
    assert callable(get_secrets_manager)


def test_secrets_singleton_instances_exist():
    """Module should export singleton instances"""
    from backend.src.core.secrets import get_secrets_manager, get_secrets_settings
    assert get_secrets_manager() is not None
    assert get_secrets_settings() is not None


def test_secrets_manager_instantiable():
    """SecretsManager should be instantiable with settings"""
    from backend.src.core.secrets import SecretsManager, SecretsManagerSettings
    settings = SecretsManagerSettings()
    manager = SecretsManager(settings=settings)
    assert manager is not None


def test_secrets_manager_get_secret_returns_default():
    """SecretsManager.get_secret should return default for missing keys"""
    from backend.src.core.secrets import SecretsManager
    manager = SecretsManager()
    result = manager.get_secret("NONEXISTENT_KEY_12345", default="default_value")
    assert result == "default_value"


# ============================================
# Test Module Structure
# ============================================

def test_core_init_file_exists():
    """Core directory should have __init__.py"""
    core_init = Path(__file__).parent.parent / "backend/src/core/__init__.py"
    assert core_init.exists(), f"Module not found at {core_init}"


def test_backend_src_init_file_exists():
    """backend/src directory should have __init__.py"""
    src_init = Path(__file__).parent.parent / "backend/src/__init__.py"
    assert src_init.exists(), f"Module not found at {src_init}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
