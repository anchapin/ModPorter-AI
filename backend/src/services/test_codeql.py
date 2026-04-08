import os
import re

def is_safe_filename(filename: str) -> bool:
    # Strict regex for filename only
    return bool(re.match(r'^[\w\-. ]+$', filename))

def get_safe_path(user_input: str) -> str:
    # Reject outright if not a safe filename
    if not is_safe_filename(user_input):
        raise ValueError("Invalid filename")

    upload_dir = os.environ.get("UPLOAD_DIR", "/tmp/uploads")
    # Because we've used a strict regex, os.path.join is unconditionally safe
    safe_path = os.path.join(upload_dir, user_input)

    return safe_path

print(get_safe_path("my_mod.jar"))
