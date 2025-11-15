import sys
from pathlib import Path

# Add the standard library path to the beginning of the sys.path
# to avoid name collision with the local 'types' module.
stdlib_path = str(Path(sys.executable).parent / "Lib")
sys.path.insert(0, stdlib_path)