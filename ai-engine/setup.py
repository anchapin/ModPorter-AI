from setuptools import setup, find_packages

setup(
    name='ai-engine',
    version='0.1.0',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'crewai==0.1.24',
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
        'langchain-openai',
        'langchain-anthropic',
        'ruff',
    ],
)
