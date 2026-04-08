import os

upload_dir = os.path.realpath("/tmp/uploads")
safe_path = os.path.realpath(os.path.join(upload_dir, "../etc/passwd"))

try:
    if os.path.commonpath([safe_path, upload_dir]) != upload_dir:
        print("Blocked!")
    else:
        print("Allowed!")
except ValueError as e:
    # commonpath raises ValueError if paths are on different drives in Windows,
    # but also can be caught
    print(f"Blocked by ValueError: {e}")

safe_path2 = os.path.realpath(os.path.join(upload_dir, "my_mod.jar"))
if os.path.commonpath([safe_path2, upload_dir]) != upload_dir:
    print("Blocked safe file!")
else:
    print("Allowed safe file!")
