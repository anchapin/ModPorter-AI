"""
Entry point for python -m modporter.cli
"""

import sys
from pathlib import Path

# Add ai-engine/src to the path so we can import the CLI
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ai-engine" / "src"))

from cli.main import main

if __name__ == '__main__':
    main()