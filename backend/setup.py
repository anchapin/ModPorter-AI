from setuptools import setup, find_packages

setup(
    name='backend',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'fastapi==0.116.1',
        'uvicorn[standard]==0.35.0',
        'pydantic==2.11.7',
        'pydantic-settings==2.10.1',
        'python-dateutil==2.9.0.post0',
        'sqlalchemy>=2.0.23',
        'asyncpg>=0.29',
        'psycopg2-binary>=2.9.7',
        'alembic==1.16.4',
        'pgvector>=0.1.1',
        'aiosqlite>=0.19.0',
        'redis[asyncio]==6.2.0',
        'python-multipart==0.0.20',
        'tomli==2.2.1',
        'python-magic==0.4.27',
        'httpx==0.28.1',
        'pytest>=8.2',
        'pytest-asyncio==1.1.0',
        'pytest-cov==6.2.1',
        'pytest-timeout==2.4.0',
        'ruff==0.12.4',
        'black==25.1.0',
        'python-dotenv==1.1.1',
    ],
)