from setuptools import setup, find_packages

setup(
    name='backend',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'fastapi',
        'uvicorn',
        'pydantic',
        'python-dotenv',
        'httpx',
        'pytest',
        'pytest-asyncio',
        'pytest-cov',
        'sqlalchemy>=2.0.23',
        'asyncpg>=0.29',
        'alembic==1.16.2',
        'redis[asyncio]==5.0.1',
        'pydantic-settings==2.1.0',
        'ruff',
    ],
)
