import os
import sys
import pytest
from pathlib import Path

# Add the src directory to the Python path
src_dir = Path(__file__).parent.parent
sys.path.insert(0, str(src_dir))

# Set testing environment variable
os.environ["TESTING"] = "true"

# Import fixtures and setup code here
