import re

with open('backend/src/services/error_handler.py', 'r') as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith('<<<<<<< HEAD'):
        # Keep the HEAD version
        pass
    elif line.startswith('======='):
        # Skip the other version
        skip = True
    elif line.startswith('>>>>>>> '):
        skip = False
    elif not skip:
        new_lines.append(line)

with open('backend/src/services/error_handler.py', 'w') as f:
    f.writelines(new_lines)
