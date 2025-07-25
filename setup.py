"""
Setup script for ModPorter AI
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="modporter-ai",
    version="0.1.0",
    author="ModPorter AI",
    author_email="info@modporter.ai",
    description="Convert Java Minecraft mods to Bedrock add-ons",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/anchapin/ModPorter-AI",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        # Core dependencies from ai-engine
        "sentence-transformers",
        "pillow",
        "numpy",
        "pathlib",
    ],
    entry_points={
        "console_scripts": [
            "modporter=modporter.cli.__main__:main",
        ],
    },
    include_package_data=True,
)