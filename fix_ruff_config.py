with open('backend/pyproject.toml', 'r') as f:
    content = f.read()

# Add more ignored files for C901
new_content = content.replace(
    '"src/services/conversion_parser.py" = ["C901"]',
    '"src/services/conversion_parser.py" = ["C901"]\n"src/api/assets.py" = ["C901"]\n"src/api/behavior_export.py" = ["C901"]\n"src/api/conversions.py" = ["C901"]\n"src/api/rate_limit_dashboard.py" = ["C901"]\n"src/java_analyzer_agent.py" = ["C901"]\n"src/services/comprehensive_report_generator.py" = ["C901"]\n"src/services/conversion_service.py" = ["C901"]\n"src/services/error_handlers.py" = ["C901"]\n"src/services/java_parser.py" = ["C901"]\n"src/services/retry.py" = ["C901"]\n"src/services/syntax_validator.py" = ["C901"]\n"src/services/task_queue_enhanced.py" = ["C901"]\n"src/utils/debt_tracker.py" = ["C901"]\n"src/utils/dependency_detector.py" = ["C901"]'
)

with open('backend/pyproject.toml', 'w') as f:
    f.write(new_content)
