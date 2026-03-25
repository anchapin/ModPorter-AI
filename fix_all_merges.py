import os
import glob

def fix_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    if not any('<<<<<<< HEAD' in line for line in lines):
        return False

    new_lines = []
    skip = False
    for line in lines:
        if line.startswith('<<<<<<< HEAD'):
            pass
        elif line.startswith('======='):
            skip = True
        elif line.startswith('>>>>>>> '):
            skip = False
        elif not skip:
            new_lines.append(line)

    with open(filepath, 'w') as f:
        f.writelines(new_lines)
    return True

for root, _, files in os.walk('backend/src'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            if fix_file(path):
                print(f"Fixed {path}")

for root, _, files in os.walk('backend/tests'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            if fix_file(path):
                print(f"Fixed {path}")

for root, _, files in os.walk('ai-engine/tests'):
    for file in files:
        if file.endswith('.py'):
            path = os.path.join(root, file)
            if fix_file(path):
                print(f"Fixed {path}")
