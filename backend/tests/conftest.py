import os
import sys
import pytest
from pathlib import Path

# Add the backend directory to the Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

# Set testing environment variable
os.environ["TESTING"] = "true"
