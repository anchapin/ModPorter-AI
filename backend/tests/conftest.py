import os
import sys
import pytest

# Mock modules for running pytest without dependencies locally
sys.modules['fastapi'] = type(sys)('fastapi')
sys.modules['fastapi.testclient'] = type(sys)('testclient')
sys.modules['fastapi.testclient'].TestClient = lambda *args, **kwargs: None

sys.modules['sqlalchemy'] = type(sys)('sqlalchemy')
sys.modules['sqlalchemy.ext'] = type(sys)('ext')
sys.modules['sqlalchemy.ext.asyncio'] = type(sys)('asyncio')
sys.modules['sqlalchemy.ext.asyncio'].AsyncSession = type('AsyncSession', (), {})

sys.modules['httpx'] = type(sys)('httpx')
sys.modules['httpx'].AsyncClient = lambda *args, **kwargs: None

