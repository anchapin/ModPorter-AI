from setuptools import setup, find_packages

setup(
    name='ai-engine',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'crewai>=0.140.0',
        'crewai-tools',
        'python-dotenv',
        'fastapi',
        'uvicorn',
        'pydantic',
        'httpx',
        'pytest',
        'pytest-asyncio',
        'pytest-cov',
        'pytest-mock',
        'pytest-timeout',
        'langchain-openai',
        'langchain-anthropic',
        'ruff',
    ],
)