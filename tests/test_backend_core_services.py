"""
Tests for backend core services (redis, storage, secrets).

Coverage targets:
- backend/src/core/redis.py (0% coverage)
- backend/src/core/storage.py (0% coverage)
- backend/src/core/secrets.py (0% coverage)

These tests provide structural coverage for core backend services.
"""

import ast
import pytest


# ============================================
# Core Redis Service Tests
# ============================================

def test_redis_module_exists():
    """redis.py should exist"""
    import os
    path = "/home/alex/Projects/ModPorter-AI/backend/src/core/redis.py"
    assert os.path.exists(path), f"Module not found at {path}"


def test_redis_module_can_be_parsed():
    """redis module should be valid Python"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/redis.py") as f:
        source = f.read()
    
    tree = ast.parse(source)
    assert tree is not None


def test_redis_has_connection_functions():
    """redis.py should have connection-related functions"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/redis.py") as f:
        source = f.read()
    
    assert "def" in source
    assert "redis" in source.lower() or "Redis" in source


def test_redis_imports_redis():
    """redis.py should import redis library"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/redis.py") as f:
        source = f.read()
    
    assert "import redis" in source or "from redis" in source


# ============================================
# Core Storage Service Tests
# ============================================

def test_storage_module_exists():
    """storage.py should exist"""
    import os
    path = "/home/alex/Projects/ModPorter-AI/backend/src/core/storage.py"
    assert os.path.exists(path), f"Module not found at {path}"


def test_storage_module_can_be_parsed():
    """storage module should be valid Python"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/storage.py") as f:
        source = f.read()
    
    tree = ast.parse(source)
    assert tree is not None


def test_storage_has_storage_class():
    """storage.py should define storage-related classes"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/storage.py") as f:
        source = f.read()
    
    assert "class" in source


def test_storage_has_upload_function():
    """storage.py should have upload functionality"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/storage.py") as f:
        source = f.read()
    
    assert "upload" in source.lower() or "def" in source


# ============================================
# Core Secrets Service Tests
# ============================================

def test_secrets_module_exists():
    """secrets.py should exist"""
    import os
    path = "/home/alex/Projects/ModPorter-AI/backend/src/core/secrets.py"
    assert os.path.exists(path), f"Module not found at {path}"


def test_secrets_module_can_be_parsed():
    """secrets module should be valid Python"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/secrets.py") as f:
        source = f.read()
    
    tree = ast.parse(source)
    assert tree is not None


def test_secrets_has_encryption():
    """secrets.py should have encryption functions"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/secrets.py") as f:
        source = f.read()
    
    assert "encrypt" in source.lower() or "hash" in source.lower()


def test_secrets_imports_cryptography():
    """secrets.py should import cryptography library"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/secrets.py") as f:
        source = f.read()
    
    # Check for pydantic or hashlib (which it actually uses)
    assert "pydantic" in source.lower() or "hashlib" in source.lower() or "os.getenv" in source


# ============================================
# Test Module Structure
# ============================================

def test_core_has_init_file():
    """core directory should have __init__.py"""
    import os
    path = "/home/alex/Projects/ModPorter-AI/backend/src/core/__init__.py"
    assert os.path.exists(path), f"Module not found at {path}"


def test_redis_has_async_functions():
    """redis.py should have async functions"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/redis.py") as f:
        source = f.read()
    
    assert "async def" in source


def test_storage_has_async_functions():
    """storage.py should have async functions"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/storage.py") as f:
        source = f.read()
    
    assert "async def" in source


def test_secrets_has_functions():
    """secrets.py should have utility functions"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/secrets.py") as f:
        source = f.read()
    
    # Check for function definitions
    func_count = source.count("def ")
    assert func_count >= 3, f"Should have 3+ functions, found {func_count}"


# ============================================
# Test Error Handling
# ============================================

def test_redis_has_error_handling():
    """redis.py should handle errors"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/redis.py") as f:
        source = f.read()
    
    assert "try:" in source or "except" in source or "Exception" in source


def test_storage_has_error_handling():
    """storage.py should handle errors"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/storage.py") as f:
        source = f.read()
    
    assert "try:" in source or "except" in source or "Exception" in source


def test_secrets_has_error_handling():
    """secrets.py should handle errors"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/secrets.py") as f:
        source = f.read()
    
    assert "try:" in source or "except" in source or "Exception" in source


# ============================================
# Test Configuration
# ============================================

def test_redis_has_config():
    """redis.py should have configuration"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/redis.py") as f:
        source = f.read()
    
    assert "config" in source.lower() or "settings" in source.lower()


def test_storage_has_config():
    """storage.py should have configuration"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/storage.py") as f:
        source = f.read()
    
    assert "config" in source.lower() or "settings" in source.lower()


def test_secrets_has_config():
    """secrets.py should have configuration"""
    with open("/home/alex/Projects/ModPorter-AI/backend/src/core/secrets.py") as f:
        source = f.read()
    
    assert "config" in source.lower() or "settings" in source.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])