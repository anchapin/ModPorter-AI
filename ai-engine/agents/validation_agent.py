# ai-engine/src/agents/validation_agent.py
import uuid
import os
import time
import random
import json
import re
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

try:
    import javalang
except ImportError:
    javalang = None

from models.validation import (
    ManifestValidationResult,
    SemanticAnalysisResult,
    BehaviorPredictionResult,
    AssetValidationResult,
    ValidationReport as AgentValidationReport,
)


@dataclass
class SyntaxValidationResult:
    """Result of syntax validation for a code snippet."""
    is_valid: bool
    language: str
    errors: List[str]
    warnings: List[str]
    line_count: int
    complexity_score: float


class JavaSyntaxValidator:
    """Validates Java code syntax using javalang."""
    
    def __init__(self):
        self.javalang_available = javalang is not None
        if not self.javalang_available:
            print("WARNING: javalang not available. Java syntax validation will use fallback.")
    
    def validate(self, java_code: str) -> SyntaxValidationResult:
        """Validate Java code syntax."""
        errors = []
        warnings = []
        
        if not java_code or not java_code.strip():
            return SyntaxValidationResult(
                is_valid=False,
                language="java",
                errors=["Empty Java code provided"],
                warnings=[],
                line_count=0,
                complexity_score=0.0
            )
        
        line_count = len(java_code.split('\n'))
        
        # Calculate complexity based on code features
        complexity = self._calculate_complexity(java_code)
        
        if self.javalang_available:
            try:
                tree = javalang.parse.parse(java_code)
                
                # Check for common issues
                if not tree:
                    errors.append("Failed to parse Java code - empty AST")
                
                # Walk the tree to check for basic issues
                has_class = False
                has_imports = bool(tree.imports)
                
                for path, node in tree:
                    if isinstance(node, javalang.tree.ClassDeclaration):
                        has_class = True
                        # Check class name
                        if not node.name:
                            errors.append("Class declaration missing name")
                
                if not has_class:
                    warnings.append("No class declaration found in code")
                    
            except javalang.parser.JavaSyntaxError as e:
                errors.append(f"Java syntax error: {str(e)}")
            except Exception as e:
                errors.append(f"Failed to parse Java: {str(e)}")
        else:
            # Fallback: basic syntax checks
            errors, warnings = self._fallback_validation(java_code)
        
        # Check for common Java issues
        self._check_common_issues(java_code, errors, warnings)
        
        return SyntaxValidationResult(
            is_valid=len(errors) == 0,
            language="java",
            errors=errors,
            warnings=warnings,
            line_count=line_count,
            complexity_score=complexity
        )
    
    def _calculate_complexity(self, code: str) -> float:
        """Calculate a simple complexity score based on code features."""
        score = 0.0
        
        # Count control structures
        keywords = ['if', 'else', 'for', 'while', 'switch', 'case', 'try', 'catch', 'throw']
        for kw in keywords:
            score += len(re.findall(r'\b' + kw + r'\b', code))
        
        # Count method declarations
        score += len(re.findall(r'\b(public|private|protected)\s+', code)) * 2
        
        # Normalize by line count
        lines = code.split('\n')
        if len(lines) > 0:
            score = score / len(lines) * 10
        
        return min(score, 10.0)
    
    def _fallback_validation(self, code: str) -> Tuple[List[str], List[str]]:
        """Fallback validation when javalang is not available."""
        errors = []
        warnings = []
        
        # Check balanced braces
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            errors.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")
        
        # Check balanced parentheses
        open_parens = code.count('(')
        close_parens = code.count(')')
        if open_parens != close_parens:
            errors.append(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")
        
        # Check for semicolons
        lines = code.split('\n')
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if line and not line.startswith('//') and not line.startswith('/*'):
                if not line.endswith(';') and not line.endswith('{') and not line.endswith('}'):
                    if i < len(lines) and lines[i].strip():
                        pass  # Allow multi-line statements
        
        return errors, warnings
    
    def _check_common_issues(self, code: str, errors: List[str], warnings: List[str]):
        """Check for common Java code issues."""
        # Check for System.out.println in production code
        if 'System.out.println' in code:
            warnings.append("System.out.println found - consider using a logger")
        
        # Check for empty catch blocks
        if re.search(r'catch\s*\([^)]+\)\s*\{\s*\}', code):
            warnings.append("Empty catch block found - errors may be silently swallowed")
        
        # Check for TODO/FIXME
        if 'TODO' in code:
            warnings.append("TODO comment found - code may be incomplete")
        if 'FIXME' in code:
            warnings.append("FIXME comment found - code needs fixing")


class BedrockSyntaxValidator:
    """Validates Bedrock add-on code (JavaScript/JSON)."""
    
    def __init__(self):
        self.js_keywords = {'function', 'var', 'let', 'const', 'if', 'else', 'for', 'while', 
                          'return', 'true', 'false', 'null', 'undefined', 'try', 'catch',
                          'throw', 'new', 'this', 'class', 'import', 'export', 'async', 'await'}
    
    def validate(self, code: str, file_type: str = "javascript") -> SyntaxValidationResult:
        """Validate Bedrock code based on file type."""
        errors = []
        warnings = []
        
        if not code or not code.strip():
            return SyntaxValidationResult(
                is_valid=False,
                language="bedrock",
                errors=["Empty Bedrock code provided"],
                warnings=[],
                line_count=0,
                complexity_score=0.0
            )
        
        line_count = len(code.split('\n'))
        complexity = self._calculate_complexity(code)
        
        if file_type == "json" or file_type == "behavior":
            # Validate as JSON
            errors, warnings = self._validate_json(code)
        else:
            # Validate as JavaScript
            errors, warnings = self._validate_javascript(code)
        
        return SyntaxValidationResult(
            is_valid=len(errors) == 0,
            language="bedrock",
            errors=errors,
            warnings=warnings,
            line_count=line_count,
            complexity_score=complexity
        )
    
    def _validate_json(self, code: str) -> Tuple[List[str], List[str]]:
        """Validate JSON structure."""
        errors = []
        warnings = []
        
        try:
            data = json.loads(code)
            # Check for required Bedrock fields
            if isinstance(data, dict):
                if 'format_version' not in data and 'minecraft_format_version' not in data:
                    warnings.append("Missing format_version field")
        except json.JSONDecodeError as e:
            errors.append(f"JSON syntax error: {str(e)}")
        
        return errors, warnings
    
    def _validate_javascript(self, code: str) -> Tuple[List[str], List[str]]:
        """Validate JavaScript syntax."""
        errors = []
        warnings = []
        
        # Check balanced braces
        open_braces = code.count('{')
        close_braces = code.count('}')
        if open_braces != close_braces:
            errors.append(f"Unbalanced braces: {open_braces} open, {close_braces} close")
        
        # Check balanced brackets
        open_brackets = code.count('[')
        close_brackets = code.count(']')
        if open_brackets != close_brackets:
            errors.append(f"Unbalanced brackets: {open_brackets} open, {close_brackets} close")
        
        # Check balanced parentheses
        open_parens = code.count('(')
        close_parens = code.count(')')
        if open_parens != close_parens:
            errors.append(f"Unbalanced parentheses: {open_parens} open, {close_parens} close")
        
        # Check for common issues
        if 'var ' in code:
            warnings.append("Using 'var' - consider 'let' or 'const' for better scoping")
        
        if '==' in code and '===' not in code:
            warnings.append("Using '==' - consider '===' for strict equality")
        
        return errors, warnings
    
    def _calculate_complexity(self, code: str) -> float:
        """Calculate complexity score."""
        score = 0.0
        
        keywords = ['if', 'else', 'for', 'while', 'switch', 'case', 'try', 'catch', 'function']
        for kw in keywords:
            score += len(re.findall(r'\b' + kw + r'\b', code))
        
        # Count function declarations
        score += len(re.findall(r'\bfunction\s+', code)) * 2
        
        lines = code.split('\n')
        if len(lines) > 0:
            score = score / len(lines) * 10
        
        return min(score, 10.0)


class StructureValidator:
    """Validates the structure of Bedrock add-on packages."""
    
    REQUIRED_MANIFEST_FIELDS = {'format_version', 'header', 'modules'}
    REQUIRED_HEADER_FIELDS = {'name', 'description', 'uuid', 'version'}
    
    def validate_structure(self, manifest: Dict[str, Any], modules: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate the structure of a Bedrock add-on."""
        errors = []
        warnings = []
        
        # Validate manifest
        manifest_errors, manifest_warnings = self._validate_manifest(manifest)
        errors.extend(manifest_errors)
        warnings.extend(manifest_warnings)
        
        # Validate modules
        module_errors, module_warnings = self._validate_modules(modules)
        errors.extend(module_errors)
        warnings.extend(module_warnings)
        
        return {
            "is_valid": len(errors) == 0,
            "structure_errors": errors,
            "structure_warnings": warnings,
            "manifest_valid": len(manifest_errors) == 0,
            "modules_valid": len([e for e in errors if 'module' in e.lower()]) == 0
        }
    
    def _validate_manifest(self, manifest: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Validate manifest.json structure."""
        errors = []
        warnings = []
        
        if not manifest:
            errors.append("Manifest is empty or missing")
            return errors, warnings
        
        # Check required top-level fields
        missing_fields = self.REQUIRED_MANIFEST_FIELDS - set(manifest.keys())
        if missing_fields:
            errors.append(f"Missing manifest fields: {missing_fields}")
        
        # Validate header
        if 'header' in manifest:
            header = manifest['header']
            missing_header = self.REQUIRED_HEADER_FIELDS - set(header.keys())
            if missing_header:
                errors.append(f"Missing header fields: {missing_header}")
            
            # Validate version format
            if 'version' in header:
                version = header['version']
                if isinstance(version, list):
                    if not all(isinstance(v, int) for v in version):
                        errors.append("Version must be a list of integers")
                else:
                    errors.append("Version must be a list")
        else:
            errors.append("Missing 'header' section in manifest")
        
        # Validate format_version
        if 'format_version' in manifest:
            fv = manifest['format_version']
            if not isinstance(fv, (int, float, str)):
                errors.append("format_version must be a number or string")
        
        return errors, warnings
    
    def _validate_modules(self, modules: List[Dict[str, Any]]) -> Tuple[List[str], List[str]]:
        """Validate module definitions."""
        errors = []
        warnings = []
        
        if not modules:
            warnings.append("No modules defined in add-on")
            return errors, warnings
        
        valid_types = {'data', 'resources', 'script', 'javascript', 'client_data', 'world_template'}
        
        for i, module in enumerate(modules):
            if not isinstance(module, dict):
                errors.append(f"Module {i} is not a dictionary")
                continue
            
            # Check required fields
            if 'type' not in module:
                errors.append(f"Module {i} missing 'type' field")
            elif module['type'] not in valid_types:
                warnings.append(f"Module {i} has non-standard type: {module['type']}")
            
            if 'uuid' not in module:
                errors.append(f"Module {i} missing 'uuid' field")
            
            if 'version' not in module:
                warnings.append(f"Module {i} missing 'version' field")
        
        return errors, warnings


class CrossReferenceValidator:
    """Validates cross-references between files in a Bedrock add-on."""
    
    def __init__(self):
        self.entity_pattern = re.compile(r'"minecraft:entity"\s*:\s*"([^"]+)"')
        self.item_pattern = re.compile(r'"minecraft:item"\s*:\s*"([^"]+)"')
        self.block_pattern = re.compile(r'"minecraft:block"\s*:\s*"([^"]+)"')
        self.function_pattern = re.compile(r'"script"\s*:\s*"([^"]+)"')
        self.animation_pattern = re.compile(r'"animation"\s*:\s*"([^"]+)"')
    
    def validate_references(self, java_definitions: Dict[str, List[str]], 
                           bedrock_files: Dict[str, str]) -> Dict[str, Any]:
        """Validate that references between files are consistent."""
        errors = []
        warnings = []
        
        # Collect all referenced entities/items/blocks from Bedrock files
        referenced_entities = set()
        referenced_items = set()
        referenced_blocks = set()
        referenced_functions = set()
        
        for content in bedrock_files.values():
            referenced_entities.update(self.entity_pattern.findall(content))
            referenced_items.update(self.item_pattern.findall(content))
            referenced_blocks.update(self.block_pattern.findall(content))
            referenced_functions.update(self.function_pattern.findall(content))
        
        # Check if Java definitions match Bedrock references
        java_entities = set(java_definitions.get('entities', []))
        java_items = set(java_definitions.get('items', []))
        java_blocks = set(java_definitions.get('blocks', []))
        
        # Find unreferenced definitions (defined but not used)
        unused_entities = java_entities - referenced_entities
        unused_items = java_items - referenced_items
        unused_blocks = java_blocks - referenced_blocks
        
        if unused_entities:
            warnings.append(f"Defined entities not referenced: {unused_entities}")
        if unused_items:
            warnings.append(f"Defined items not referenced: {unused_items}")
        if unused_blocks:
            warnings.append(f"Defined blocks not referenced: {unused_blocks}")
        
        # Find broken references (referenced but not defined)
        broken_entities = referenced_entities - java_entities
        broken_items = referenced_items - java_items
        broken_blocks = referenced_blocks - java_blocks
        
        if broken_entities:
            errors.append(f"References to undefined entities: {broken_entities}")
        if broken_items:
            errors.append(f"References to undefined items: {broken_items}")
        if broken_blocks:
            errors.append(f"References to undefined blocks: {broken_blocks}")
        
        return {
            "is_valid": len(errors) == 0,
            "reference_errors": errors,
            "reference_warnings": warnings,
            "total_references": len(referenced_entities) + len(referenced_items) + len(referenced_blocks),
            "broken_count": len(broken_entities) + len(broken_items) + len(broken_blocks)
        }


class LLMSemanticAnalyzer:
    def __init__(self, api_key: str = "MOCK_API_KEY"):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("API key for LLM Semantic Analyzer is required.")
        print("LLMSemanticAnalyzer initialized (mock). API Key: " + self.api_key[:10] + "...")

    def analyze(self, code_snippet: str) -> dict:
        if not code_snippet:
            print("LLMSemanticAnalyzer: No code snippet provided.")
            return {
                "intent_preserved": False,
                "confidence": 0.1,
                "findings": ["No code provided for analysis."],
            }
        print(
            "LLMSemanticAnalyzer: Analyzing code snippet (first 50 chars): '"
            + code_snippet[:50]
            + "...'"
        )
        # Use asyncio.sleep in async context, time.sleep in sync context
        # Since this is called from a synchronous context, we'll keep time.sleep but with a shorter duration
        time.sleep(random.uniform(0.05, 0.1))  # Reduced sleep time
        intent_preserved = True
        confidence = random.uniform(0.75, 0.95)
        findings = []
        if "TODO" in code_snippet or "FIXME" in code_snippet:
            intent_preserved = False
            confidence *= 0.7
            findings.append("Code contains 'TODO'/'FIXME' markers.")
        if "unsafe" in code_snippet.lower() or "danger" in code_snippet.lower():
            confidence *= 0.8
            findings.append("Code contains 'unsafe'/'danger' keywords.")
        if len(code_snippet) < 50 and "simple" not in code_snippet.lower():
            confidence *= 0.9
            findings.append("Code snippet is very short.")
        if "complex_logic_pattern" in code_snippet:
            confidence *= 0.85
            findings.append("Identified complex logic pattern.")
        if (
            "error" in code_snippet.lower()
            or "exception" in code_snippet.lower()
            and "handle" not in code_snippet.lower()
        ):
            intent_preserved = False
            confidence *= 0.6
            findings.append("Code mentions unhandled 'error'/'exception'.")
        confidence = min(max(confidence, 0.0), 1.0)
        if not findings and intent_preserved and confidence > 0.8:
            findings.append("Code appears semantically sound (mock).")
        elif not findings:
            findings.append("Mock analysis complete.")
        print(
            "LLMSemanticAnalyzer: Analysis complete. Intent preserved: %s, Confidence: %.2f"
            % (intent_preserved, confidence)
        )
        return {
            "intent_preserved": intent_preserved,
            "confidence": round(confidence, 2),
            "findings": findings,
        }


class BehaviorAnalysisEngine:
    def __init__(self):
        print("BehaviorAnalysisEngine initialized (mock).")

    def predict_behavior(self, java_code: str, bedrock_code: str) -> dict:
        if not java_code and not bedrock_code:
            print("BehaviorAnalysisEngine: No Java or Bedrock code provided.")
            return {
                "behavior_diff": "No code provided for comparison.",
                "confidence": 0.0,
                "potential_issues": ["Cannot analyze behavior without code inputs."],
            }

        print("BehaviorAnalysisEngine: Predicting behavior differences...")
        print("Java (first 50): '" + java_code[:50] + "...'")
        print("Bedrock (first 50): '" + bedrock_code[:50] + "...'")

        # Reduced sleep time for mock processing
        time.sleep(random.uniform(0.05, 0.1))

        behavior_diff = "No significant differences predicted (mock)."
        confidence = random.uniform(0.70, 0.90)
        potential_issues = []

        if (
            "thread" in java_code.lower()
            and "thread" not in bedrock_code.lower()
            and "async" not in bedrock_code.lower()
        ):
            behavior_diff = "Potential difference in concurrency model (Java uses threads, Bedrock may need async/event-driven)."
            confidence *= 0.7
            potential_issues.append(
                "Java code mentions 'thread'; ensure Bedrock equivalent handles concurrency correctly."
            )

        if "file IO" in java_code.lower() or "java.io" in java_code:
            if "http" not in bedrock_code.lower() and "script.storage" not in bedrock_code.lower():
                behavior_diff = (
                    "Difference in data persistence/IO. Java file IO may not map directly."
                )
                confidence *= 0.6
                potential_issues.append(
                    "Java code uses file IO. Bedrock has limited local storage or requires HTTP for external data."
                )

        if "reflection" in java_code.lower():
            behavior_diff = "Java reflection usage has no direct equivalent in Bedrock scripting."
            confidence *= 0.5
            potential_issues.append(
                "Java's reflection capabilities are not available in Bedrock's JavaScript environment."
            )

        if "complex_event_handling" in java_code.lower() and "simple_event" in bedrock_code.lower():
            behavior_diff = "Potential simplification or loss of nuance in event handling."
            confidence *= 0.75
            potential_issues.append(
                "Java code indicates complex event handling; ensure Bedrock script captures all necessary event triggers."
            )

        if not bedrock_code and java_code:
            behavior_diff = "Bedrock code is empty or missing; Java functionality will be lost."
            confidence = 0.1
            potential_issues.append("No Bedrock code provided to match Java functionality.")

        confidence = min(max(confidence, 0.0), 1.0)

        if not potential_issues and confidence > 0.8:
            potential_issues.append(
                "Behavior prediction suggests good correspondence (mock analysis)."
            )
        elif not potential_issues:
            potential_issues.append("Mock behavior prediction complete; review confidence.")

        print("BehaviorAnalysisEngine: Prediction complete. Confidence: %.2f" % confidence)

        return {
            "behavior_diff": behavior_diff,
            "confidence": round(confidence, 2),
            "potential_issues": potential_issues,
        }


class AssetIntegrityChecker:
    def __init__(self):
        self.supported_image_extensions = {".png", ".jpg", ".jpeg", ".tga"}
        self.supported_sound_extensions = {".ogg", ".wav", ".mp3"}
        self.supported_model_extensions = {".json"}
        print("AssetIntegrityChecker initialized.")

    def validate_assets(self, asset_files: list, base_path: str = "") -> dict:
        print("Validating %d asset files. Base path: '%s'" % (len(asset_files), base_path))
        corrupted_files, asset_specific_issues = [], {}
        if not asset_files:
            return {
                "all_assets_valid": True,
                "corrupted_files": [],
                "asset_specific_issues": {"general": ["No asset files provided."]},
            }
        for asset_path in asset_files:
            full_path = (
                os.path.join(base_path, asset_path)
                if base_path and base_path != "."
                else asset_path
            )
            if "missing" in asset_path.lower():
                corrupted_files.append(asset_path)
                asset_specific_issues.setdefault(asset_path, []).append(
                    "File missing: '%s'." % full_path
                )
                continue
            _, ext = os.path.splitext(asset_path)
            ext = ext.lower()
            issues = []
            if ext in self.supported_image_extensions:
                if "corrupt_texture" in asset_path:
                    issues.append("Mock: Texture corrupt.")
                if "oversized_texture" in asset_path:
                    issues.append("Mock: Texture oversized.")
            elif ext in self.supported_sound_extensions:
                if ext != ".ogg" and "allow_non_ogg" not in asset_path:
                    issues.append("Mock: Non-preferred sound format '%s'." % ext)
                if "corrupt_sound" in asset_path:
                    issues.append("Mock: Sound corrupt.")
            elif ext in self.supported_model_extensions:
                if "invalid_geo" in asset_path:
                    issues.append("Mock: Model geo invalid.")
            elif not ext:
                issues.append("Warning: File '%s' no extension." % asset_path)
            else:
                issues.append("Warning: Unrecognized extension '%s' for '%s'." % (ext, asset_path))
            if issues:
                corrupted_files.append(asset_path)
                asset_specific_issues.setdefault(asset_path, []).extend(issues)
        return {
            "all_assets_valid": not corrupted_files,
            "corrupted_files": list(set(corrupted_files)),
            "asset_specific_issues": asset_specific_issues,
        }


class ManifestValidator:
    def __init__(self):
        pass

    def validate_manifest(self, md: dict) -> ManifestValidationResult:
        err, warn = [], []
        if not isinstance(md, dict):
            return ManifestValidationResult(
                is_valid=False, errors=["Manifest not dict."], warnings=warn
            )
        fv = md.get("format_version")
        if fv is None:
            err.append("Missing 'format_version'.")
        elif not isinstance(fv, int):
            if isinstance(fv, str) and fv.isdigit():
                warn.append("format_version (%s) is str, should be int." % str(fv))
                fv = int(fv)
            else:
                err.append("format_version (%s) must be int." % str(fv))
        if isinstance(fv, int) and fv != 2:
            warn.append("format_version (%s) not typical (2)." % str(fv))
        hd = md.get("header")
        if hd is None:
            err.append("Missing 'header'.")
        elif not isinstance(hd, dict):
            err.append("'header' not dict.")
        else:
            for field in ["name", "description", "uuid", "version"]:
                if field not in hd:
                    err.append("Header missing '%s'." % field)
            if hd.get("uuid"):
                try:
                    uuid.UUID(str(hd.get("uuid")))
                except ValueError:
                    err.append("Header uuid (%s) invalid." % str(hd.get("uuid")))
            v = hd.get("version")
            if v and not (
                isinstance(v, list) and len(v) == 3 and all(isinstance(i, int) for i in v)
            ):
                err.append("Header version (%s) invalid." % str(v))
            mev = hd.get("min_engine_version")
            if mev and not (
                isinstance(mev, list) and len(mev) >= 3 and all(isinstance(i, int) for i in mev)
            ):
                warn.append("Header min_engine_version (%s) invalid." % str(mev))
        mods = md.get("modules")
        if mods is None:
            err.append("Missing 'modules'.")
        elif not isinstance(mods, list):
            err.append("'modules' not list.")
        else:
            if not mods:
                warn.append("'modules' empty.")
            for i, m in enumerate(mods):
                if not isinstance(m, dict):
                    err.append("Module %d not dict." % i)
                    continue
                for field in ["type", "uuid", "version"]:
                    if field not in m:
                        err.append("Module %d missing '%s'." % (i, field))
                if m.get("uuid"):
                    try:
                        uuid.UUID(str(m.get("uuid")))
                    except ValueError:
                        err.append("Module %d uuid (%s) invalid." % (i, str(m.get("uuid"))))
                mv = m.get("version")
                if mv and not (
                    isinstance(mv, list) and len(mv) == 3 and all(isinstance(x, int) for x in mv)
                ):
                    err.append("Module %d version (%s) invalid." % (i, str(mv)))
                mt = m.get("type")
                ok = [
                    "data",
                    "resources",
                    "script",
                    "client_data",
                    "world_template",
                    "skin_pack",
                    "javascript",
                ]
                if mt and mt not in ok:
                    warn.append("Module %d type ('%s') non-standard." % (i, mt))
                if mt in ["script", "javascript"] and "entry" not in m:
                    warn.append("Module %d type '%s' missing 'entry'." % (i, mt))
        return ManifestValidationResult(is_valid=not err, errors=err, warnings=warn)


class ValidationAgent:
    def __init__(self):
        # Syntax validators
        self.java_validator = JavaSyntaxValidator()
        self.bedrock_validator = BedrockSyntaxValidator()
        self.structure_validator = StructureValidator()
        self.crossref_validator = CrossReferenceValidator()
        
        # Original validators
        self.semantic_analyzer = LLMSemanticAnalyzer()
        self.behavior_predictor = BehaviorAnalysisEngine()
        self.asset_validator = AssetIntegrityChecker()
        self.manifest_validator = ManifestValidator()
        print("ValidationAgent initialized with all components including syntax validators.")

    def validate_conversion(self, conversion_artifacts: dict) -> AgentValidationReport:
        print("Starting validation process...")
        conversion_id = conversion_artifacts.get("conversion_id", "unknown_conversion")
        java_code = conversion_artifacts.get("java_code", "")
        bedrock_code = conversion_artifacts.get("bedrock_code", "")
        asset_files = conversion_artifacts.get("asset_files", [])
        asset_base_path = conversion_artifacts.get("asset_base_path", "")
        manifest_data = conversion_artifacts.get("manifest_data", {})
        
        # Run syntax validations (Phase 09-01)
        java_syntax = self.java_validator.validate(java_code)
        bedrock_syntax = self.bedrock_validator.validate(bedrock_code)
        
        # Run structure validation
        modules = manifest_data.get("modules", []) if manifest_data else []
        structure_result = self.structure_validator.validate_structure(manifest_data, modules)
        
        # Run cross-reference validation if definitions provided
        java_definitions = conversion_artifacts.get("java_definitions", {})
        bedrock_files = conversion_artifacts.get("bedrock_files", {})
        if java_definitions and bedrock_files:
            crossref_result = self.crossref_validator.validate_references(java_definitions, bedrock_files)
        else:
            crossref_result = {"is_valid": True, "reference_errors": [], "reference_warnings": []}
        
        # Run original validations
        semantic_raw = self.semantic_analyzer.analyze(bedrock_code)
        behavior_raw = self.behavior_predictor.predict_behavior(java_code, bedrock_code)
        asset_raw = self.asset_validator.validate_assets(asset_files, base_path=asset_base_path)
        manifest_result_model = self.manifest_validator.validate_manifest(manifest_data)

        semantic_model = SemanticAnalysisResult(**semantic_raw)
        behavior_model = BehaviorPredictionResult(**behavior_raw)
        asset_model = AssetValidationResult(**asset_raw)

        # Calculate confidence with syntax validation weights
        conf_semantic = semantic_model.confidence
        conf_behavior = behavior_model.confidence
        conf_asset = 1.0 if asset_model.all_assets_valid else 0.3
        conf_manifest = 1.0 if manifest_result_model.is_valid else 0.3
        
        # Add syntax validation confidence
        conf_java_syntax = 1.0 if java_syntax.is_valid else 0.3
        conf_bedrock_syntax = 1.0 if bedrock_syntax.is_valid else 0.3
        conf_structure = 1.0 if structure_result["is_valid"] else 0.3
        conf_crossref = 1.0 if crossref_result["is_valid"] else 0.3

        # Original weights: semantic (0.3), behavior (0.4), assets (0.15), manifest (0.15)
        # New weights with syntax validation (total = 1.0)
        overall_confidence = (
            (conf_semantic * 0.20)
            + (conf_behavior * 0.30)
            + (conf_asset * 0.10)
            + (conf_manifest * 0.10)
            + (conf_java_syntax * 0.10)
            + (conf_bedrock_syntax * 0.10)
            + (conf_structure * 0.05)
            + (conf_crossref * 0.05)
        )
        overall_confidence = round(min(max(overall_confidence, 0.0), 1.0), 2)

        recommendations = []
        
        # Add syntax validation recommendations
        if not java_syntax.is_valid:
            recommendations.append(f"Java syntax errors: {', '.join(java_syntax.errors[:3])}")
        if java_syntax.warnings:
            recommendations.append(f"Java syntax warnings: {', '.join(java_syntax.warnings[:2])}")
        
        if not bedrock_syntax.is_valid:
            recommendations.append(f"Bedrock syntax errors: {', '.join(bedrock_syntax.errors[:3])}")
        if bedrock_syntax.warnings:
            recommendations.append(f"Bedrock syntax warnings: {', '.join(bedrock_syntax.warnings[:2])}")
        
        if not structure_result["is_valid"]:
            recommendations.append(f"Structure errors: {', '.join(structure_result['structure_errors'][:2])}")
        
        if not crossref_result["is_valid"]:
            recommendations.append(f"Cross-reference errors: {', '.join(crossref_result['reference_errors'][:2])}")
        
        # Original recommendations
        if not semantic_model.intent_preserved or semantic_model.confidence < 0.7:
            recommendations.append(
                "Semantic analysis suggests potential issues; manual review of code logic advised."
            )
        for finding in semantic_model.findings:
            if (
                "appears semantically sound" not in finding
                and "Mock analysis complete" not in finding
            ):
                recommendations.append("Semantic finding: " + finding)

        if (
            behavior_model.confidence < 0.7
            or "No significant differences predicted" not in behavior_model.behavior_diff
        ):
            recommendations.append(
                "Behavior prediction indicates potential differences: "
                + behavior_model.behavior_diff
            )
        for issue in behavior_model.potential_issues:
            if (
                "good correspondence" not in issue
                and "Mock behavior prediction complete" not in issue
            ):
                recommendations.append("Behavioral issue: " + issue)

        if not asset_model.all_assets_valid and asset_model.corrupted_files:
            recommendations.append(
                "Review " + str(len(asset_model.corrupted_files)) + " asset(s) with issues."
            )
        if asset_model.asset_specific_issues.get("general"):
            recommendations.extend(asset_model.asset_specific_issues["general"])
        if not manifest_result_model.is_valid:
            recommendations.append("Manifest has errors. Please check details.")
        if manifest_result_model.warnings:
            recommendations.append("Manifest has warnings. Review for optimal compatibility.")

        # Add syntax validation results to recommendations
        syntax_validation = {
            "java_syntax": {
                "is_valid": java_syntax.is_valid,
                "errors": java_syntax.errors,
                "warnings": java_syntax.warnings,
                "line_count": java_syntax.line_count,
                "complexity_score": java_syntax.complexity_score
            },
            "bedrock_syntax": {
                "is_valid": bedrock_syntax.is_valid,
                "errors": bedrock_syntax.errors,
                "warnings": bedrock_syntax.warnings,
                "line_count": bedrock_syntax.line_count,
                "complexity_score": bedrock_syntax.complexity_score
            },
            "structure": structure_result,
            "cross_references": crossref_result
        }

        report = AgentValidationReport(
            conversion_id=conversion_id,
            semantic_analysis=semantic_model,
            behavior_prediction=behavior_model,
            asset_integrity=asset_model,
            manifest_validation=manifest_result_model,
            overall_confidence=overall_confidence,
            recommendations=list(set(recommendations)),
        )
        
        # Add syntax validation as raw_data for backward compatibility
        if hasattr(report, 'raw_data'):
            report.raw_data = syntax_validation
        else:
            # Store in recommendations for visibility
            if syntax_validation.get("java_syntax", {}).get("errors") or \
               syntax_validation.get("bedrock_syntax", {}).get("errors"):
                recommendations.append("Syntax validation found errors - review detailed report")

        print("Validation process completed.")
        return report


if __name__ == "__main__":
    agent = ValidationAgent()

    valid_manifest_for_tests = {
        "format_version": 2,
        "header": {
            "name": "Test Pack",
            "description": "Valid.",
            "uuid": str(uuid.uuid4()),
            "version": [1, 0, 0],
        },
        "modules": [{"type": "data", "uuid": str(uuid.uuid4()), "version": [1, 0, 0]}],
    }

    behavior_code_samples = {
        "simple_match": {
            "java": 'System.out.println("Hello");',
            "bedrock": 'console.log("Hello");',
        },
        "threading_diff": {"java": "new Thread().start();", "bedrock": "// Needs async solution"},
        "file_io_java": {
            "java": 'import java.io.File; new File("test.txt");',
            "bedrock": "// Script storage or HTTP",
        },
        "reflection_java": {"java": "obj.getClass().getMethods();", "bedrock": "// No equivalent"},
        "empty_bedrock": {"java": "int main() { return 0; }", "bedrock": ""},
    }

    for test_name, codes in behavior_code_samples.items():
        print("\n--- Test Case (Agent - Behavior - %s) ---" % test_name)
        mock_artifacts_behavior = {
            "conversion_id": "conv_behavior_" + test_name,
            "java_code": codes["java"],
            "bedrock_code": codes["bedrock"],
            "asset_files": [],
            "manifest_data": valid_manifest_for_tests,
        }
        report_behavior_test = agent.validate_conversion(mock_artifacts_behavior)
        print(report_behavior_test.model_dump_json(indent=2))

    behavior_analyzer = BehaviorAnalysisEngine()
    print("\n--- Test Case (Direct Behavior Analyzer): Simple Match ---")
    direct_behavior_simple = behavior_analyzer.predict_behavior(
        behavior_code_samples["simple_match"]["java"],
        behavior_code_samples["simple_match"]["bedrock"],
    )
    print(BehaviorPredictionResult(**direct_behavior_simple).model_dump_json(indent=2))

    print("\n--- Test Case (Direct Behavior Analyzer): Threading Difference ---")
    direct_behavior_thread = behavior_analyzer.predict_behavior(
        behavior_code_samples["threading_diff"]["java"],
        behavior_code_samples["threading_diff"]["bedrock"],
    )
    print(BehaviorPredictionResult(**direct_behavior_thread).model_dump_json(indent=2))

    print("\n--- Test Case (Direct Behavior Analyzer): No Code ---")
    direct_behavior_none = behavior_analyzer.predict_behavior("", "")
    print(BehaviorPredictionResult(**direct_behavior_none).model_dump_json(indent=2))

    good_java_code = behavior_code_samples["simple_match"]["java"]
    good_semantic_code = "// Simple and clear Bedrock script\nlet value = 100;\nfunction activate() { console.log('Activated: ' + value); }"

    mock_artifacts_all_good = {
        "conversion_id": "conv_all_good_001",
        "java_code": good_java_code,
        "bedrock_code": good_semantic_code,
        "asset_files": ["textures/block.png"],
        "asset_base_path": "mock/path",
        "manifest_data": valid_manifest_for_tests,
    }
    print("\n--- Test Case (Agent): All Components Good/Simple ---")
    report_all_good = agent.validate_conversion(mock_artifacts_all_good)
    print(report_all_good.model_dump_json(indent=2))
