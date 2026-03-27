"""Quality validator placeholder."""

class ValidationResult:
    def __init__(self, is_valid, errors, warnings):
        self.is_valid = is_valid
        self.errors = errors
        self.warnings = warnings

class QualityValidator:
    def validate(self, content, metadata):
        return ValidationResult(is_valid=True, errors=[], warnings=[])
