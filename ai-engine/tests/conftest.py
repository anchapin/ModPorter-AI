"""
pytest configuration and fixtures for ai-engine tests.

This file imports the plugin that applies necessary mocks before any tests are
imported to avoid dependency issues with heavy libraries like chromadb and sentence-transformers.
"""

import sys
import os

# Import the plugin that applies mocks early
import tests.plugin
