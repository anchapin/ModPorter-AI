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
    ],
)
