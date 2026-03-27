"""
Pattern validation logic.

Validates Java and Bedrock patterns for syntax, structure, and security.
"""

import logging
import json
import re
from dataclasses import dataclass, field
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of pattern validation."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self):
        """If there are errors, is_valid must be False."""
        if self.errors and self.is_valid:
            raise ValueError("Cannot have errors and be valid")


class PatternValidator:
    """
    Validates pattern submissions.

    Checks for:
    - Minimum code length
    - Syntax validity (Java class/structure, JSON or JavaScript)
    - Malicious content
    - Description quality
    """

    # Validation thresholds
    MIN_JAVA_LINES = 3
    MIN_BEDROCK_LINES = 3
    MIN_DESCRIPTION_LENGTH = 20

    # Malicious content patterns
    MALICIOUS_PATTERNS = [
        r'\beval\s*\(',  # eval(
        r'__import__\s*\(',  # __import__(
        r'\bexec\s*\(',  # exec(
        r'<script[^>]*>',  # <script> tags
        r'javascript:',  # javascript: protocol
        r'document\.cookie',  # document.cookie
        r'Runtime\.getRuntime',  # Java Runtime.exec()
        r'ProcessBuilder\s*\(',  # ProcessBuilder(
        r'\bSystem\.exec',  # System.exec (doesn't exist but looks suspicious)
        r'\.getClass\(\)\s*\.forName',  # Reflection-based class loading
    ]

    def __init__(self):
        """Initialize validator."""
        # Compile malicious patterns for performance
        self.malicious_regex = re.compile(
            '|'.join(self.MALICIOUS_PATTERNS),
            re.IGNORECASE | re.MULTILINE
        )

    async def validate_pattern(
        self,
        java_pattern: str,
        bedrock_pattern: str,
        description: str,
    ) -> ValidationResult:
        """
        Validate a complete pattern submission.

        Args:
            java_pattern: Java code example
            bedrock_pattern: Bedrock code example (JSON or JavaScript)
            description: Pattern description

        Returns:
            ValidationResult with errors/warnings
        """
        errors = []
        warnings = []

        # Validate Java pattern
        java_result = self._validate_java_pattern(java_pattern)
        errors.extend(java_result.errors)
        warnings.extend(java_result.warnings)

        # Validate Bedrock pattern
        bedrock_result = self._validate_bedrock_pattern(bedrock_pattern)
        errors.extend(bedrock_result.errors)
        warnings.extend(bedrock_result.warnings)

        # Validate description
        desc_result = self._validate_description(description)
        errors.extend(desc_result.errors)
        warnings.extend(desc_result.warnings)

        # Check for malicious content across all inputs
        if self._contains_malicious_content(java_pattern, bedrock_pattern, description):
            errors.append("Pattern contains potentially malicious code")
            logger.warning("Malicious content detected in pattern submission")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_java_pattern(self, pattern: str) -> ValidationResult:
        """
        Validate Java pattern.

        Checks:
        - Minimum line count
        - Contains class/interface/enum keyword
        - Contains access modifier (public/private/protected)
        """
        errors = []
        warnings = []

        lines = pattern.strip().split('\n')

        # Check minimum line count
        if len(lines) < self.MIN_JAVA_LINES:
            errors.append(
                f"Java pattern too short: {len(lines)} lines, "
                f"minimum {self.MIN_JAVA_LINES}"
            )

        # Check for class/interface/enum keyword
        java_keywords = ['class ', 'interface ', 'enum ']
        if not any(keyword in pattern for keyword in java_keywords):
            errors.append(
                "Java pattern must contain class, interface, or enum keyword"
            )

        # Check for access modifiers (warning only)
        if not any(mod in pattern for mod in ['public ', 'private ', 'protected ']):
            warnings.append(
                "Java pattern missing access modifier (public/private/protected)"
            )

        # Check for package or import statements (good practice)
        if 'package ' not in pattern and 'import ' not in pattern:
            warnings.append(
                "Java pattern missing package or import statements"
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_bedrock_pattern(self, pattern: str) -> ValidationResult:
        """
        Validate Bedrock pattern.

        Checks:
        - Minimum line count
        - Valid JSON or JavaScript syntax
        """
        errors = []
        warnings = []

        lines = pattern.strip().split('\n')

        # Check minimum line count
        if len(lines) < self.MIN_BEDROCK_LINES:
            errors.append(
                f"Bedrock pattern too short: {len(lines)} lines, "
                f"minimum {self.MIN_BEDROCK_LINES}"
            )

        # Try to parse as JSON first
        try:
            json.loads(pattern)
            # Valid JSON
            return ValidationResult(is_valid=True, errors=[], warnings=[])
        except json.JSONDecodeError:
            # Not JSON, check if it's JavaScript
            pass

        # Check for JavaScript keywords
        js_keywords = ['function ', 'const ', 'let ', 'var ', 'import ', 'class ']
        if not any(keyword in pattern for keyword in js_keywords):
            errors.append(
                "Bedrock pattern must be valid JSON or JavaScript"
            )

        # Check for common Bedrock patterns
        bedrock_indicators = [
            'minecraft:',
            'format_version',
            'components',
            'description',
        ]
        if not any(indicator in pattern for indicator in bedrock_indicators):
            warnings.append(
                "Bedrock pattern may not follow standard format"
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_description(self, description: str) -> ValidationResult:
        """
        Validate pattern description.

        Checks:
        - Minimum length
        - Not empty or just whitespace
        """
        errors = []
        warnings = []

        # Check minimum length
        if len(description) < self.MIN_DESCRIPTION_LENGTH:
            errors.append(
                f"Description too short: {len(description)} characters, "
                f"minimum {self.MIN_DESCRIPTION_LENGTH}"
            )

        # Check for meaningful content
        if not description.strip():
            errors.append("Description cannot be empty or whitespace")

        # Check for placeholder text
        placeholders = [
            'TODO',
            'FIXME',
            'example',
            'test',
            'placeholder',
        ]
        if any(placeholder.lower() in description.lower() for placeholder in placeholders):
            warnings.append(
                "Description may contain placeholder text"
            )

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _contains_malicious_content(self, *patterns: str) -> bool:
        """
        Check if any pattern contains malicious content.

        Uses regex patterns to detect potentially dangerous code.

        Args:
            *patterns: Variable number of pattern strings to check

        Returns:
            True if malicious content detected, False otherwise
        """
        combined = '\n'.join(patterns)
        matches = self.malicious_regex.findall(combined)

        if matches:
            logger.warning(f"Malicious patterns detected: {matches}")
            return True

        return False
