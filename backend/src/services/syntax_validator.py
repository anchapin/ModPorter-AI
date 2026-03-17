"""
Syntax Validation Service for ModPorter AI

Provides:
- JavaScript/TypeScript syntax validation using tree-sitter
- JSON schema validation for Bedrock files
- Auto-fix for common syntax errors
- Error reporting with line numbers
"""

import logging
from typing import List, Dict, Any, Optional
import json
import re

logger = logging.getLogger(__name__)

# Try to import tree-sitter for JavaScript
try:
    import tree_sitter_typescript as ts_typescript
    from tree_sitter import Language, Parser

    TREE_SITTER_TS_AVAILABLE = True
    logger.info("Tree-sitter TypeScript parser available")
except ImportError as e:
    logger.warning(f"Tree-sitter TypeScript not available: {e}")
    TREE_SITTER_TS_AVAILABLE = False
    ts_typescript = None
    Parser = None
    Language = None

# Also try JavaScript
try:
    import tree_sitter_javascript as ts_javascript

    TREE_SITTER_JS_AVAILABLE = True
    logger.info("Tree-sitter JavaScript parser available")
except ImportError as e:
    logger.warning(f"Tree-sitter JavaScript not available: {e}")
    TREE_SITTER_JS_AVAILABLE = False
    ts_javascript = None


# Bedrock JSON Schema definitions (simplified)
BEDROCK_SCHEMAS = {
    "manifest": {
        "type": "object",
        "required": ["format_version", "header", "modules"],
        "properties": {
            "format_version": {"type": "integer", "enum": [1, 2]},
            "header": {
                "type": "object",
                "required": ["name", "uuid", "version"],
                "properties": {
                    "name": {"type": "string"},
                    "uuid": {
                        "type": "string",
                        "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
                    },
                    "version": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                },
            },
            "modules": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["type", "uuid"],
                },
            },
        },
    },
    "block": {
        "type": "object",
        "required": ["format_version", "minecraft:block"],
        "properties": {
            "format_version": {"type": "integer"},
            "minecraft:block": {
                "type": "object",
                "required": ["description"],
                "properties": {
                    "identifier": {"type": "string", "pattern": "^[a-z_]+:[a-z_]+$"},
                    "category": {"type": "string"},
                },
            },
        },
    },
    "item": {
        "type": "object",
        "required": ["format_version", "minecraft:item"],
        "properties": {
            "format_version": {"type": "integer"},
            "minecraft:item": {
                "type": "object",
                "required": ["description"],
                "properties": {
                    "identifier": {"type": "string", "pattern": "^[a-z_]+:[a-z_]+$"},
                },
            },
        },
    },
    "entity": {
        "type": "object",
        "required": ["format_version", "minecraft:entity"],
        "properties": {
            "format_version": {"type": "integer"},
            "minecraft:entity": {
                "type": "object",
                "required": ["description", "components"],
                "properties": {
                    "identifier": {"type": "string", "pattern": "^[a-z_]+:[a-z_]+$"},
                },
            },
        },
    },
}


class SyntaxError:
    """Represents a syntax error with location information."""

    def __init__(
        self,
        message: str,
        line: int,
        column: int,
        file_path: str,
        severity: str = "error",
    ):
        self.message = message
        self.line = line
        self.column = column
        self.file_path = file_path
        self.severity = severity  # "error", "warning", "info"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "line": self.line,
            "column": self.column,
            "file_path": self.file_path,
            "severity": self.severity,
        }


class JavaScriptSyntaxValidator:
    """Validates JavaScript/TypeScript syntax using tree-sitter."""

    def __init__(self):
        self.parser = None
        if TREE_SITTER_JS_AVAILABLE:
            try:
                self.parser = Parser(ts_javascript.language())
                logger.debug("JavaScript parser initialized")
            except Exception as e:
                logger.error(f"Failed to initialize JavaScript parser: {e}")
                self.parser = None
        elif TREE_SITTER_TS_AVAILABLE:
            # Fallback to TypeScript parser which can parse JavaScript
            try:
                self.parser = Parser(ts_typescript.language())
                logger.debug("TypeScript parser initialized (fallback for JavaScript)")
            except Exception as e:
                logger.error(f"Failed to initialize TypeScript parser: {e}")
                self.parser = None

    def validate(self, source_code: str, file_path: str = "") -> List[SyntaxError]:
        """
        Validate JavaScript/TypeScript syntax.

        Args:
            source_code: Source code to validate
            file_path: Optional file path for error reporting

        Returns:
            List of syntax errors found
        """
        errors = []

        if self.parser is None:
            # Fallback: basic syntax check
            return self._basic_syntax_check(source_code, file_path)

        try:
            tree = self.parser.parse(bytes(source_code, "utf8"))

            # Check for syntax errors in the tree
            if tree.root_node.has_error:
                error_node = self._find_error_node(tree.root_node)
                if error_node:
                    line = error_node.start_point[0] + 1  # 1-indexed
                    column = error_node.start_point[1]
                    errors.append(
                        SyntaxError(
                            message="Syntax error detected",
                            line=line,
                            column=column,
                            file_path=file_path,
                        )
                    )

            return errors

        except Exception as e:
            errors.append(
                SyntaxError(
                    message=f"Parser error: {str(e)}",
                    line=1,
                    column=0,
                    file_path=file_path,
                )
            )
            return errors

    def _find_error_node(self, node) -> Optional[Any]:
        """Find the first error node in the AST."""
        if node.has_error:
            for child in node.children:
                result = self._find_error_node(child)
                if result:
                    return result
            return node
        return None

    def _basic_syntax_check(
        self, source_code: str, file_path: str
    ) -> List[SyntaxError]:
        """Basic syntax check without tree-sitter."""
        errors = []

        # Check for common syntax errors
        lines = source_code.split("\n")

        # Check for unmatched braces
        brace_count = 0
        for i, line in enumerate(lines, 1):
            brace_count += line.count("{") - line.count("}")
            if brace_count < 0:
                errors.append(
                    SyntaxError(
                        message="Unmatched closing brace '}'",
                        line=i,
                        column=0,
                        file_path=file_path,
                    )
                )
                break

        if brace_count > 0:
            errors.append(
                SyntaxError(
                    message=f"Unclosed braces: {brace_count} opening brace(s) without closing",
                    line=len(lines),
                    column=0,
                    file_path=file_path,
                )
            )

        # Check for unmatched parentheses
        paren_count = 0
        for i, line in enumerate(lines, 1):
            paren_count += line.count("(") - line.count(")")
            if paren_count < 0:
                errors.append(
                    SyntaxError(
                        message="Unmatched closing parenthesis ')'",
                        line=i,
                        column=0,
                        file_path=file_path,
                    )
                )
                break

        if paren_count > 0:
            errors.append(
                SyntaxError(
                    message=f"Unclosed parentheses: {paren_count} opening parenthesis(es) without closing",
                    line=len(lines),
                    column=0,
                    file_path=file_path,
                )
            )

        return errors


class JSONSchemaValidator:
    """Validates JSON files against Bedrock schemas."""

    def __init__(self):
        self.schemas = BEDROCK_SCHEMAS

    def validate(
        self, json_data: Dict, schema_name: str, file_path: str = ""
    ) -> List[SyntaxError]:
        """
        Validate JSON data against a schema.

        Args:
            json_data: JSON data to validate
            schema_name: Name of schema to use (e.g., "manifest", "block")
            file_path: Optional file path for error reporting

        Returns:
            List of validation errors
        """
        errors = []

        if schema_name not in self.schemas:
            errors.append(
                SyntaxError(
                    message=f"Unknown schema: {schema_name}",
                    line=1,
                    column=0,
                    file_path=file_path,
                    severity="error",
                )
            )
            return errors

        schema = self.schemas[schema_name]
        errors.extend(self._validate_object(json_data, schema, "", file_path))

        return errors

    def _validate_object(
        self, data: Any, schema: Dict, path: str, file_path: str
    ) -> List[SyntaxError]:
        """Recursively validate object against schema."""
        errors = []

        # Type check
        expected_type = schema.get("type")
        if expected_type:
            if expected_type == "object" and not isinstance(data, dict):
                errors.append(
                    SyntaxError(
                        message=f"Expected object, got {type(data).__name__}",
                        line=1,
                        column=0,
                        file_path=file_path,
                    )
                )
                return errors
            elif expected_type == "array" and not isinstance(data, list):
                errors.append(
                    SyntaxError(
                        message=f"Expected array, got {type(data).__name__}",
                        line=1,
                        column=0,
                        file_path=file_path,
                    )
                )
                return errors
            elif expected_type == "string" and not isinstance(data, str):
                errors.append(
                    SyntaxError(
                        message=f"Expected string, got {type(data).__name__}",
                        line=1,
                        column=0,
                        file_path=file_path,
                    )
                )
                return errors
            elif expected_type == "integer" and not isinstance(data, int):
                errors.append(
                    SyntaxError(
                        message=f"Expected integer, got {type(data).__name__}",
                        line=1,
                        column=0,
                        file_path=file_path,
                    )
                )
                return errors

        # Required fields check
        if expected_type == "object" and isinstance(data, dict):
            required = schema.get("required", [])
            missing = [f for f in required if f not in data]
            if missing:
                errors.append(
                    SyntaxError(
                        message=f"Missing required fields: {', '.join(missing)}",
                        line=1,
                        column=0,
                        file_path=file_path,
                    )
                )

            # Validate properties
            properties = schema.get("properties", {})
            for key, value in data.items():
                if key in properties:
                    field_path = f"{path}.{key}" if path else key
                    errors.extend(
                        self._validate_object(
                            value, properties[key], field_path, file_path
                        )
                    )

        # Pattern check
        if "pattern" in schema and isinstance(data, str):
            if not re.match(schema["pattern"], data):
                errors.append(
                    SyntaxError(
                        message=f"Value '{data}' does not match pattern '{schema['pattern']}'",
                        line=1,
                        column=0,
                        file_path=file_path,
                    )
                )

        # Enum check
        if "enum" in schema and data not in schema["enum"]:
            errors.append(
                SyntaxError(
                    message=f"Value '{data}' not in allowed values: {schema['enum']}",
                    line=1,
                    column=0,
                    file_path=file_path,
                )
            )

        return errors


class SyntaxAutoFix:
    """Auto-fix common syntax errors."""

    @staticmethod
    def fix_missing_semicolons(source_code: str) -> str:
        """Add missing semicolons at end of statements."""
        lines = source_code.split("\n")
        fixed_lines = []

        for line in lines:
            stripped = line.strip()
            # Skip empty lines, comments, and lines already ending with semicolon
            if (
                stripped
                and not stripped.startswith("//")
                and not stripped.startswith("/*")
                and not stripped.startswith("*")
                and not stripped.endswith(("{", "}", ";", "(", ")", ","))
            ):
                # Check if it's a statement that should end with semicolon
                if re.match(
                    r"^(var|let|const|function|return|if|for|while|class|import|export)\b",
                    stripped,
                ):
                    line = line.rstrip() + ";"
            fixed_lines.append(line)

        return "\n".join(fixed_lines)

    @staticmethod
    def fix_missing_commas(source_code: str) -> str:
        """Add missing commas in object/array literals."""
        # This is a simplified fix - real implementation would need AST parsing
        # Add comma before closing brace/bracket if previous line doesn't end with comma
        source_code = re.sub(r'(\s*"[^"]*"\s*:\s*[^,}]+)(\s*})', r"\1,\2", source_code)
        return source_code

    @staticmethod
    def fix_unmatched_braces(source_code: str) -> str:
        """Fix unmatched braces by adding missing closing braces."""
        brace_count = source_code.count("{") - source_code.count("}")
        if brace_count > 0:
            source_code += "\n" + "}" * brace_count
        return source_code


def validate_javascript_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Validate a JavaScript file.

    Args:
        file_path: Path to JavaScript file

    Returns:
        List of error dictionaries
    """
    validator = JavaScriptSyntaxValidator()

    try:
        with open(file_path, "r") as f:
            source_code = f.read()
    except Exception as e:
        return [
            SyntaxError(
                message=f"Failed to read file: {e}",
                line=1,
                column=0,
                file_path=file_path,
            ).to_dict()
        ]

    errors = validator.validate(source_code, file_path)
    return [error.to_dict() for error in errors]


def validate_json_file(file_path: str, schema_name: str) -> List[Dict[str, Any]]:
    """
    Validate a JSON file against a schema.

    Args:
        file_path: Path to JSON file
        schema_name: Schema name (e.g., "manifest", "block")

    Returns:
        List of error dictionaries
    """
    validator = JSONSchemaValidator()

    try:
        with open(file_path, "r") as f:
            json_data = json.load(f)
    except json.JSONDecodeError as e:
        return [
            SyntaxError(
                message=f"Invalid JSON: {e}",
                line=e.lineno,
                column=e.colno,
                file_path=file_path,
            ).to_dict()
        ]

    errors = validator.validate(json_data, schema_name, file_path)
    return [error.to_dict() for error in errors]


def auto_fix_javascript(source_code: str) -> str:
    """
    Auto-fix common JavaScript syntax errors.

    Args:
        source_code: JavaScript source code

    Returns:
        Fixed source code
    """
    fixed = source_code
    fixed = SyntaxAutoFix.fix_missing_semicolons(fixed)
    fixed = SyntaxAutoFix.fix_missing_commas(fixed)
    fixed = SyntaxAutoFix.fix_unmatched_braces(fixed)
    return fixed
