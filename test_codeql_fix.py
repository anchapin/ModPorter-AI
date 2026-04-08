import os
from pathlib import Path

def test_codeql_path_fix(request_file_path):
    # Simulate how CodeQL might prefer the sanitization
    filename = os.path.basename(request_file_path)
    if not filename or filename != request_file_path:
        raise ValueError("Only plain filenames are allowed, no paths")

    upload_dir = os.environ.get("UPLOAD_DIR", "/tmp/uploads")
    safe_path = os.path.join(upload_dir, filename)

    print(f"Safe path: {safe_path}")

test_codeql_path_fix("my_mod.jar")
try:
    test_codeql_path_fix("../etc/passwd")
except ValueError as e:
    print(f"Caught expected error: {e}")
