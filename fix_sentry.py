import re

with open('frontend/src/main.tsx', 'r') as f:
    content = f.read()

content = content.replace("Sentry.addCaptureConsoleIntegration();", "// Sentry.addCaptureConsoleIntegration(); // Commented out to fix dev build")

with open('frontend/src/main.tsx', 'w') as f:
    f.write(content)
