"""
JavaScript Code Validator for Generated Bedrock Scripts

This module provides comprehensive validation for JavaScript code generated
during Java to Bedrock translation, including:
- Syntax validation
- Semantic analysis
- API correctness checks
- Bedrock compatibility verification
- Security scanning

Issue #570: AI Engine Logic Translation - Java OOP to Bedrock Event-Driven JavaScript
"""

from __future__ import annotations

import re
import json
from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum


class Severity(Enum):
    """Severity levels for validation issues"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    severity: Severity
    category: str
    message: str
    line_number: Optional[int] = None
    column: Optional[int] = None
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None


@dataclass
class ValidationResult:
    """Complete validation result"""
    is_valid: bool
    issues: List[ValidationIssue]
    syntax_errors: List[ValidationIssue]
    semantic_errors: List[ValidationIssue]
    api_warnings: List[ValidationIssue]
    security_warnings: List[ValidationIssue]
    score: float  # 0.0 to 1.0
    statistics: Dict[str, Any]


class JavaScriptValidator:
    """
    Comprehensive JavaScript code validator for Bedrock scripts.

    Validates:
    - Syntax correctness
    - API usage against documented mappings
    - Bedrock compatibility
    - Common JavaScript pitfalls
    - Security vulnerabilities
    - Performance issues
    """

    def __init__(self, api_mappings: Optional[Dict[str, str]] = None):
        """Initialize validator with API mappings"""
        self.api_mappings = api_mappings or self._load_default_api_mappings()
        self.validation_patterns = self._load_validation_patterns()
        self.bedrock_apis = self._load_bedrock_apis()
        self.unsupported_patterns = self._load_unsupported_patterns()

    def validate(self, javascript_code: str, context: Optional[Dict] = None) -> ValidationResult:
        """
        Perform comprehensive validation of JavaScript code.

        Args:
            javascript_code: The JavaScript code to validate
            context: Optional context about the code (e.g., feature type)

        Returns:
            ValidationResult with all validation findings
        """
        issues = []
        syntax_errors = []
        semantic_errors = []
        api_warnings = []
        security_warnings = []

        # Split code into lines for line number tracking
        lines = javascript_code.split('\n')

        # 1. Syntax Validation
        syntax_issues = self._validate_syntax(javascript_code, lines)
        syntax_errors.extend(syntax_issues)
        issues.extend(syntax_issues)

        # Only continue with semantic validation if syntax is mostly valid
        critical_syntax = [i for i in syntax_issues if i.severity == Severity.ERROR]
        if len(critical_syntax) > 5:
            # Too many syntax errors, skip semantic checks
            return self._create_result(False, issues, syntax_errors, semantic_errors,
                                   api_warnings, security_warnings)

        # 2. Semantic Analysis
        semantic_issues = self._validate_semantics(javascript_code, lines)
        semantic_errors.extend(semantic_issues)
        issues.extend(semantic_issues)

        # 3. API Compatibility
        api_issues = self._validate_apis(javascript_code, lines)
        api_warnings.extend(api_issues)
        issues.extend(api_issues)

        # 4. Security Checks
        security_issues = self._check_security(javascript_code, lines)
        security_warnings.extend(security_issues)
        issues.extend(security_issues)

        # 5. Performance Checks
        perf_issues = self._check_performance(javascript_code, lines)
        issues.extend(perf_issues)

        # 6. Bedrock-Specific Checks
        bedrock_issues = self._validate_bedrock_compatibility(javascript_code, lines)
        issues.extend(bedrock_issues)

        # Calculate overall score
        score = self._calculate_score(issues, lines)

        # Create result
        return self._create_result(
            is_valid=score > 0.5,
            issues=issues,
            syntax_errors=syntax_errors,
            semantic_errors=semantic_errors,
            api_warnings=api_warnings,
            security_warnings=security_warnings
        )

    def _validate_syntax(self, code: str, lines: List[str]) -> List[ValidationIssue]:
        """Validate JavaScript syntax"""
        issues = []

        # Check for balanced braces
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            issues.append(ValidationIssue(
                severity=Severity.ERROR,
                category="syntax",
                message=f"Unbalanced braces: {open_braces} opening, {close_braces} closing",
                suggestion="Check that all opening braces have matching closing braces"
            ))

        # Check for balanced parentheses
        open_parens = code.count('(')
        close_parens = code.count(')')
        if open_parens != close_parens:
            issues.append(ValidationIssue(
                severity=Severity.ERROR,
                category="syntax",
                message=f"Unbalanced parentheses: {open_parens} opening, {close_parens} closing",
                suggestion="Check that all opening parentheses have matching closing parentheses"
            ))

        # Check for balanced brackets
        open_brackets = code.count('[')
        close_brackets = code.count(']')
        if open_brackets != close_brackets:
            issues.append(ValidationIssue(
                severity=Severity.ERROR,
                category="syntax",
                message=f"Unbalanced brackets: {open_brackets} opening, {close_brackets} closing",
                suggestion="Check that all opening brackets have matching closing brackets"
            ))

        # Check for semicolons after statements
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped and not stripped.startswith('//') and not stripped.startswith('/*'):
                # Lines that should end with semicolon
                if (re.search(r'\b(const|let|var)\s+\w+\s*=', stripped) or
                    re.search(r'\w+\.\w+\s*\(', stripped)):
                    if not stripped.endswith(';') and not stripped.endswith('{') and not stripped.endswith('}'):
                        # May be missing semicolon (but it's not required in JS)
                        pass

        # Check for arrow function syntax
        arrow_count = code.count('=>')
        if arrow_count > 0:
            # Validate arrow function usage
            for i, line in enumerate(lines, 1):
                if '=>' in line:
                    # Check if arrow function is properly formatted
                    if not re.search(r'\([^)]*\)\s*=>\s*\{?', line):
                        issues.append(ValidationIssue(
                            severity=Severity.WARNING,
                            category="syntax",
                            message="Potentially malformed arrow function",
                            line_number=i,
                            code_snippet=line.strip(),
                            suggestion="Ensure arrow functions are formatted as: (params) => { body }"
                        ))

        return issues

    def _validate_semantics(self, code: str, lines: List[str]) -> List[ValidationIssue]:
        """Validate code semantics and common issues"""
        issues = []

        # Check for undefined variables (basic heuristic)
        defined_vars = set()
        used_vars = set()

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('//') or stripped.startswith('/*'):
                continue

            # Track variable definitions
            for match in re.finditer(r'\b(const|let|var)\s+(\w+)', stripped):
                defined_vars.add(match.group(2))

            # Track variable usage
            for match in re.finditer(r'\b([a-zA-Z_$][a-zA-Z0-9_$]*)\s*(?:\(|\.|\[|=|;|\))', stripped):
                var = match.group(1)
                if var not in ['if', 'else', 'for', 'while', 'return', 'function', 'class', 'import']:
                    used_vars.add(var)

        # Check for use of undefined variables
        for var in used_vars:
            if var not in defined_vars and var not in ['event', 'world', 'player', 'entity', 'block']:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    category="semantic",
                    message=f"Variable '{var}' may be used before definition",
                    suggestion="Ensure all variables are defined before use or are available from event context"
                ))

        # Check for common JavaScript issues

        # Comparison with assignment
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(if|while|for)\s*\([^)]*=[^=)]*\)', line):
                issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    category="semantic",
                    message="Assignment (=) used instead of comparison (== or ===)",
                    line_number=i,
                    code_snippet=line.strip(),
                    suggestion="Use === for strict comparison or == for loose comparison"
                ))

        # Check for potential null/undefined access
        for i, line in enumerate(lines, 1):
            if re.search(r'\b\w+\.\w+\.\w+', line) and '?' not in line:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    category="semantic",
                    message="Potential null/undefined access without optional chaining",
                    line_number=i,
                    code_snippet=line.strip(),
                    suggestion="Consider using optional chaining (?.) or adding null checks"
                ))

        # Check for 'this' usage (should be minimized in event handlers)
        for i, line in enumerate(lines, 1):
            if re.search(r'\bthis\.', line):
                issues.append(ValidationIssue(
                    severity=Severity.INFO,
                    category="semantic",
                    message="Use of 'this' detected - may not work as expected in event handlers",
                    line_number=i,
                    code_snippet=line.strip(),
                    suggestion="Avoid using 'this' in event handlers; use parameters instead"
                ))

        return issues

    def _validate_apis(self, code: str, lines: List[str]) -> List[ValidationIssue]:
        """Validate API usage against documented mappings"""
        issues = []

        # Extract API calls from code
        api_calls = self._extract_api_calls(code)

        # Check each API call
        for api_call, line_info in api_calls:
            # Check if API is documented
            if api_call not in self.bedrock_apis:
                # Check if it's a potential Java API that wasn't translated
                if any(pattern in api_call for pattern in ['getHealth()', 'setHealth(',
                                                          'getLocation()', 'getBlockAt(',
                                                          'player.', 'world.',
                                                          'entity.']):
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        category="api",
                        message=f"Potential untranslated Java API: {api_call}",
                        line_number=line_info['line'],
                        code_snippet=line_info['snippet'],
                        suggestion=f"Refer to API_MAPPING_DOCUMENTATION.md for correct Bedrock API"
                    ))
            else:
                # API is supported, check for correct usage
                usage_issues = self._validate_api_usage(api_call, line_info)
                issues.extend(usage_issues)

        # Check for unsupported Java APIs
        for pattern, description in self.unsupported_patterns.items():
            for i, line in enumerate(lines, 1):
                if pattern.search(line):
                    issues.append(ValidationIssue(
                        severity=Severity.ERROR,
                        category="api",
                        message=f"Unsupported API: {description}",
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion="See API_MAPPING_DOCUMENTATION.md for alternatives or smart assumptions"
                    ))

        return issues

    def _check_security(self, code: str, lines: List[str]) -> List[ValidationIssue]:
        """Check for potential security issues"""
        issues = []

        # Check for eval() usage
        for i, line in enumerate(lines, 1):
            if re.search(r'\beval\s*\(', line):
                issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    category="security",
                    message="Use of eval() is dangerous and should be avoided",
                    line_number=i,
                    code_snippet=line.strip(),
                    suggestion="Replace eval() with safer alternatives"
                ))

        # Check for Function constructor
        for i, line in enumerate(lines, 1):
            if re.search(r'\bnew\s+Function\s*\(', line):
                issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    category="security",
                    message="Use of Function constructor is dangerous",
                    line_number=i,
                    code_snippet=line.strip(),
                    suggestion="Use regular function definitions instead"
                ))

        # Check for hardcoded credentials or sensitive data
        sensitive_patterns = [
            (r'password\s*[=:]\s*["\'].*["\']', "Hardcoded password"),
            (r'api[_-]?key\s*[=:]\s*["\'].*["\']', "Hardcoded API key"),
            (r'secret\s*[=:]\s*["\'].*["\']', "Hardcoded secret"),
        ]

        for pattern, description in sensitive_patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        category="security",
                        message=f"{description} detected in code",
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion="Remove sensitive data or use environment variables"
                    ))

        # Check for infinite loop patterns
        for i, line in enumerate(lines, 1):
            if re.search(r'\bwhile\s*\(\s*true\s*\)', line, re.IGNORECASE):
                issues.append(ValidationIssue(
                    severity=Severity.ERROR,
                    category="security",
                    message="Infinite loop detected (while(true))",
                    line_number=i,
                    code_snippet=line.strip(),
                    suggestion="Add a break condition or use event-driven approach"
                ))

        return issues

    def _check_performance(self, code: str, lines: List[str]) -> List[ValidationIssue]:
        """Check for performance issues"""
        issues = []

        # Check for expensive operations in tick events
        in_tick_handler = False
        for i, line in enumerate(lines, 1):
            stripped = line.strip()

            if 'beforeEvents.tick' in stripped or 'afterEvents.tick' in stripped:
                in_tick_handler = True
            elif stripped.startswith('});'):
                in_tick_handler = False

            if in_tick_handler:
                # Check for expensive operations
                if re.search(r'\bfor\s*\(', stripped):
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        category="performance",
                        message="Loop in tick handler - may cause performance issues",
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion="Avoid heavy loops in tick handlers; use events instead"
                    ))

                if re.search(r'\b(world|dimension)\.', stripped):
                    issues.append(ValidationIssue(
                        severity=Severity.INFO,
                        category="performance",
                        message="Frequent world access in tick handler",
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion="Cache results or use event-driven approach"
                    ))

        # Check for nested loops
        loop_depth = 0
        for i, line in enumerate(lines, 1):
            if re.search(r'\b(for|while)\s*\(', line):
                loop_depth += 1
                if loop_depth > 2:
                    issues.append(ValidationIssue(
                        severity=Severity.WARNING,
                        category="performance",
                        message=f"Deeply nested loops (depth {loop_depth}) detected",
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion="Consider optimizing or restructuring the code"
                    ))
            elif line.strip() == '}' and loop_depth > 0:
                loop_depth -= 1

        return issues

    def _validate_bedrock_compatibility(self, code: str, lines: List[str]) -> List[ValidationIssue]:
        """Validate Bedrock-specific compatibility"""
        issues = []

        # Check for proper event subscription
        event_subscriptions = re.findall(r'(\w+)\.afterEvents\.(\w+)\.subscribe', code)

        for event_obj, event_name in event_subscriptions:
            # Validate event object
            if event_obj not in ['world', 'system']:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    category="bedrock",
                    message=f"Unknown event object: {event_obj}",
                    suggestion="Use 'world' for game events or 'system' for system events"
                ))

        # Check for correct event names
        known_events = {
            'playerBreakBlock', 'blockPlace', 'itemUse', 'itemUseOn',
            'entitySpawn', 'entityDie', 'playerJoin', 'playerLeave',
            'chatSend', 'commandExecute', 'itemCompleteUse', 'projectileHit'
        }

        for _, event_name in event_subscriptions:
            if event_name not in known_events:
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    category="bedrock",
                    message=f"Unknown or unsupported event: {event_name}",
                    suggestion="Check Bedrock Script API documentation for valid event names"
                ))

        # Check for component access patterns
        component_patterns = [
            r'\.getComponent\("minecraft:[^"]+"\)',
            r'\.getComponent\(\'minecraft:[^\']+\)',
        ]

        for pattern in component_patterns:
            for i, line in enumerate(lines, 1):
                if re.search(pattern, line):
                    # Check if component exists
                    match = re.search(r'"minecraft:([^"]+)"|\'minecraft:([^\']+)\'', line)
                    if match:
                        component = match.group(1) or match.group(2)
                        known_components = [
                            'health', 'food', 'equipped_item', 'item', 'equipment',
                            'movement', 'navigation', 'attack', 'damageable', 'enchantable'
                        ]
                        if component not in known_components:
                            issues.append(ValidationIssue(
                                severity=Severity.WARNING,
                                category="bedrock",
                                message=f"Unknown component: minecraft:{component}",
                                line_number=i,
                                code_snippet=line.strip(),
                                suggestion="Verify component name in Bedrock documentation"
                            ))

        # Check for proper return statements in subscribe handlers
        for i, line in enumerate(lines, 1):
            if 'subscribe' in line and '=>' in line:
                # Check if handler is a function
                if not re.search(r'subscribe\(\s*\(\s*\w+\s*\)\s*=>', line):
                    issues.append(ValidationIssue(
                        severity=Severity.INFO,
                        category="bedrock",
                        message="Event handler should be an arrow function or function expression",
                        line_number=i,
                        code_snippet=line.strip(),
                        suggestion="Format: event.subscribe((event) => { /* handler */ })"
                    ))

        return issues

    def _extract_api_calls(self, code: str) -> List[Tuple[str, Dict]]:
        """Extract API calls from code with line information"""
        api_calls = []
        lines = code.split('\n')

        for i, line in enumerate(lines, 1):
            # Match patterns like: object.method(, world.something(
            matches = re.finditer(r'(\w+)\.(\w+)\s*\(', line)
            for match in matches:
                api_call = f"{match.group(1)}.{match.group(2)}"
                api_calls.append((api_call, {
                    'line': i,
                    'snippet': line.strip()
                }))

        return api_calls

    def _validate_api_usage(self, api_call: str, line_info: Dict) -> List[ValidationIssue]:
        """Validate specific API usage patterns"""
        issues = []

        # Check for common mistakes
        if api_call == 'player.getComponent':
            # Should specify which component
            if 'component' not in line_info.get('snippet', '').lower() or \
               'minecraft:' not in line_info.get('snippet', ''):
                issues.append(ValidationIssue(
                    severity=Severity.WARNING,
                    category="api",
                    message="getComponent() requires component identifier",
                    line_number=line_info['line'],
                    suggestion='Use: getComponent("minecraft:component_name")'
                ))

        return issues

    def _calculate_score(self, issues: List[ValidationIssue], lines: List[str]) -> float:
        """Calculate validation score (0.0 to 1.0)"""
        if not issues:
            return 1.0

        # Weight errors more heavily
        error_weight = 2.0
        warning_weight = 1.0
        info_weight = 0.5

        total_weight = 0
        weighted_sum = 0

        for issue in issues:
            if issue.severity == Severity.ERROR:
                weight = error_weight
            elif issue.severity == Severity.WARNING:
                weight = warning_weight
            else:
                weight = info_weight

            total_weight += weight
            weighted_sum += weight

        # Normalize by code length (longer code tolerates more issues)
        normalization_factor = max(1, len(lines) / 50)
        normalized_issues = weighted_sum / normalization_factor

        # Calculate score (inverse of issues)
        score = max(0.0, 1.0 - (normalized_issues / 20.0))

        return score

    def _create_result(
        self,
        is_valid: bool,
        issues: List[ValidationIssue],
        syntax_errors: List[ValidationIssue],
        semantic_errors: List[ValidationIssue],
        api_warnings: List[ValidationIssue],
        security_warnings: List[ValidationIssue]
    ) -> ValidationResult:
        """Create ValidationResult with statistics"""
        return ValidationResult(
            is_valid=is_valid,
            issues=issues,
            syntax_errors=syntax_errors,
            semantic_errors=semantic_errors,
            api_warnings=api_warnings,
            security_warnings=security_warnings,
            score=self._calculate_score(issues, []),
            statistics={
                "total_issues": len(issues),
                "error_count": sum(1 for i in issues if i.severity == Severity.ERROR),
                "warning_count": sum(1 for i in issues if i.severity == Severity.WARNING),
                "info_count": sum(1 for i in issues if i.severity == Severity.INFO),
                "by_category": {
                    "syntax": len(syntax_errors),
                    "semantic": len(semantic_errors),
                    "api": len(api_warnings),
                    "security": len(security_warnings)
                }
            }
        )

    def _load_default_api_mappings(self) -> Dict[str, str]:
        """Load default API mappings"""
        # This would be loaded from the comprehensive API mapping document
        return {
            'player.getHealth()': 'player.getComponent("minecraft:health").currentValue',
            'world.getBlockAt(': 'world.getBlock(',
            'world.setBlock(': 'dimension.setBlockPermutation(',
        }

    def _load_validation_patterns(self) -> Dict[str, Any]:
        """Load validation patterns"""
        return {}

    def _load_bedrock_apis(self) -> Set[str]:
        """Load set of valid Bedrock APIs"""
        # Common Bedrock APIs (expanded from API mapping documentation)
        return {
            # Player APIs
            'player.getComponent', 'player.teleport', 'player.kill',
            # World APIs
            'world.getBlock', 'world.spawnEntity', 'world.spawnParticle',
            'world.afterEvents', 'world.beforeEvents', 'world.getTime',
            # Entity APIs
            'entity.kill', 'entity.teleport', 'entity.getComponent',
            # Block APIs
            'block.destroy', 'block.setType',
            # Component APIs
            'getComponent', 'hasComponent',
        }

    def _load_unsupported_patterns(self) -> Dict[re.Pattern, str]:
        """Load patterns for unsupported Java APIs"""
        return {
            re.compile(r'\bDimension\b.*?\bManager\b'): "Custom dimension management",
            re.compile(r'\bTileEntity\b'): "Tile entities (block entities)",
            re.compile(r'\bCapability\b'): "Capability system",
            re.compile(r'\bNetworkManager\b'): "Network packet management",
            re.compile(r'\bPacket\b.*?\bHandler\b'): "Packet handlers",
        }
