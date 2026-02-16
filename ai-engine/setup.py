"""
AI Engine package setup.

This setup.py provides a simple way to install the ai-engine package.
For production use, we recommend using pyproject.toml which provides
more comprehensive dependency management and optional dependency groups.

Usage:
    pip install -e .              # Install with core dependencies
    pip install -e .[dev]        # Install with development dependencies
    pip install -e .[gpu-nvidia] # Install with NVIDIA GPU support

For full GPU support (all platforms), use:
    pip install -e .[gpu-all]
"""

from setuptools import setup, find_packages

# Read requirements from pyproject.toml for consistency
# This ensures setup.py and pyproject.toml stay in sync
def get_install_requires():
    """Get core install requirements from pyproject.toml equivalent."""
    return [
        # Core FastAPI for AI Engine API
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "python-multipart>=0.0.6",

        # AI Framework
        "crewai>=0.11.0",
        "langchain>=0.3.0",
        "langchain-openai>=0.2.0",
        "langchain-ollama>=0.1.0",
        "openai>=1.0.0",
        
        # Embeddings - Using sentence-transformers for local embeddings
        # Note: This is a core dependency for RAG functionality
        "sentence-transformers>=2.2.0",

        # Vector Database (pin version for embedchain compatibility)
        "chromadb<1.2.0",

        # Data Processing
        "numpy",
        "python-dotenv",

        # Java analysis
        "javalang>=0.13.0",

        # File processing
        "Pillow>=10.0.0",
        "pydub",
        
        # HTTP Client
        "httpx",
        
        # Redis for job management
        "redis>=4.5.0",
        
        # Configuration Management
        "pydantic>=2.0.0",
        "pydantic-settings",
        
        # Monitoring
        "prometheus-client",
        "psutil",
    ]


setup(
    name='ai-engine',
    version='0.1.0',
    description='AI Engine with GPU acceleration support for ModPorter',
    author='ModPorter AI',
    author_email='ai@modporter.dev',
    license='MIT',
    packages=find_packages(where='.'),
    python_requires='>=3.9',
    install_requires=get_install_requires(),
    extras_require={
        # Development dependencies
        'dev': [
            'pytest',
            'pytest-asyncio',
            'pytest-mock',
            'pytest-cov',
            'pytest-timeout',
            'black',
            'ruff',
            'isort',
        ],
        # NVIDIA GPU support
        'gpu-nvidia': [
            'torch>=2.5.0',
            'torchvision>=0.20.0',
            'torchaudio>=2.5.0',
            'onnxruntime-gpu>=1.19.0',
            'accelerate>=0.24.0',
        ],
        # AMD GPU support
        'gpu-amd': [
            'torch>=2.5.0',
            'torchvision>=0.20.0',
            'torchaudio>=2.5.0',
            'onnxruntime-rocm>=1.19.0; sys_platform=="linux"',
            'onnxruntime-directml>=1.19.0; sys_platform=="win32"',
            'accelerate>=0.24.0',
        ],
        # CPU-only
        'cpu-only': [
            'torch>=2.5.0',
            'torchvision>=0.20.0',
            'torchaudio>=2.5.0',
            'onnxruntime>=1.19.0',
        ],
    },
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
        'Programming Language :: Python :: 3.12',
    ],
    entry_points={
        'console_scripts': [
            'ai-engine=ai_engine.main:main',
        ],
    },
)
