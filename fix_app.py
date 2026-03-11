import re

with open('frontend/src/App.tsx', 'r') as f:
    content = f.read()

content = content.replace("  usePageViewTracking(true);", "  // usePageViewTracking(true); // Must be inside Router")

with open('frontend/src/App.tsx', 'w') as f:
    f.write(content)
