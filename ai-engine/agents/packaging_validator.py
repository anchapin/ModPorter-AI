"""
Enhanced Packaging Validator for comprehensive .mcaddon validation
Validates structure, schemas, file integrity, and Bedrock compatibility

Issue #325: Validate and Fix Packaging Agent Structure
"""

import json
import logging
import zipfile
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import jsonschema
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    CRITICAL = "critical"  # Package will fail to import
    ERROR = "error"  # Package may import but will not work
    WARNING = "warning"  # Package works but has issues
    INFO = "info"  # Informational message


@dataclass
class ValidationIssue:
    """Represents a single validation issue."""
    severity: ValidationSeverity
    category: str  # e.g., "structure", "manifest", "schema"
    message: str
    file_path: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Complete validation result for an .mcaddon package."""
    is_valid: bool
    overall_score: int  # 0-100
    issues: List[ValidationIssue]
    stats: Dict[str, Any]
    compatibility: Dict[str, Any]
    file_structure: Dict[str, Any]

    def get_issues_by_severity(self, severity: ValidationSeverity) -> List[ValidationIssue]:
        """Get all issues of a specific severity."""
        return [issue for issue in self.issues if issue.severity == severity]

    def get_issues_by_category(self, category: str) -> List[ValidationIssue]:
        """Get all issues in a specific category."""
        return [issue for issue in self.issues if issue.category == category]


class PackagingValidator:
    """
    Comprehensive validator for Bedrock .mcaddon packages.

    Validates:
    - Folder structure (behavior_packs/, resource_packs/)
    - Manifest.json files against official schemas
    - Block, item, and entity definitions
    - File integrity and format compliance
    - UUID uniqueness and validity
    - Version compatibility
    """

    def __init__(self, schema_dir: Optional[Path] = None):
        """
        Initialize validator with JSON schemas.

        Args:
            schema_dir: Directory containing JSON schema files
        """
        if schema_dir is None:
            # Default to schemas directory relative to this file
            schema_dir = Path(__file__).parent.parent / "schemas"

        self.schema_dir = Path(schema_dir)
        self.schemas = self._load_schemas()

        # Bedrock structure requirements
        self.required_top_level_dirs = {
            "behavior_packs": "Behavior packs (plural)",
            "resource_packs": "Resource packs (plural)"
        }

        self.forbidden_patterns = [
            "behavior_pack/",  # Old incorrect singular form
            "resource_pack/",  # Old incorrect singular form
            ".tmp",
            ".temp",
            "~$",
            "Thumbs.db",
            ".DS_Store"
        ]

        # Allowed directories within each pack type
        self.behavior_pack_dirs = {
            "animations", "animation_controllers", "blocks", "entities",
            "functions", "items", "loot_tables", "recipes", "scripts",
            "spawn_rules", "texts", "trading", "dialogs"
        }

        self.resource_pack_dirs = {
            "animations", "animation_controllers", "attachables", "blocks",
            "entity", "fogs", "font", "models", "particles", "render_controllers",
            "sounds", "textures", "texts", "ui"
        }

        # File format constraints
        self.max_texture_size = 1024  # pixels
        self.max_file_size_mb = 500  # Total package size
        self.max_script_size_kb = 500

    def _load_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Load JSON schemas from schema directory."""
        schemas = {}

        if not self.schema_dir.exists():
            logger.warning(f"Schema directory not found: {self.schema_dir}")
            return schemas

        schema_files = {
            "manifest": "bedrock_manifest_schema.json",
            "block": "bedrock_block_schema.json",
            "item": "bedrock_item_schema.json"
        }

        for schema_name, filename in schema_files.items():
            schema_path = self.schema_dir / filename
            if schema_path.exists():
                try:
                    with open(schema_path, 'r') as f:
                        schemas[schema_name] = json.load(f)
                    logger.debug(f"Loaded schema: {schema_name}")
                except Exception as e:
                    logger.error(f"Failed to load schema {filename}: {e}")
            else:
                logger.warning(f"Schema file not found: {schema_path}")

        return schemas

    def validate_mcaddon(self, mcaddon_path: Path) -> ValidationResult:
        """
        Perform comprehensive validation of a .mcaddon file.

        Args:
            mcaddon_path: Path to the .mcaddon file

        Returns:
            ValidationResult with detailed findings
        """
        logger.info(f"Starting validation of {mcaddon_path}")

        issues = []
        stats = {}
        compatibility = {}
        file_structure = {}

        try:
            # Basic file validation
            if not mcaddon_path.exists():
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="file",
                    message=f"File does not exist: {mcaddon_path}"
                ))
                return self._create_result(False, issues, stats, compatibility, file_structure)

            # Validate ZIP format
            try:
                with zipfile.ZipFile(mcaddon_path, 'r') as zipf:
                    zipf.testzip()
            except zipfile.BadZipFile as e:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="file",
                    message=f"Invalid ZIP file: {e}"
                ))
                return self._create_result(False, issues, stats, compatibility, file_structure)

            # Open and analyze package
            with zipfile.ZipFile(mcaddon_path, 'r') as zipf:
                # Collect statistics
                stats = self._analyze_package_stats(zipf)

                # Validate structure
                structure_issues, file_structure = self._validate_structure(zipf)
                issues.extend(structure_issues)

                # Validate manifests
                manifest_issues = self._validate_manifests(zipf)
                issues.extend(manifest_issues)

                # Validate component files
                component_issues = self._validate_components(zipf)
                issues.extend(component_issues)

                # Check compatibility
                compatibility = self._check_compatibility(zipf)

                # Check for forbidden files
                forbidden_issues = self._check_forbidden_files(zipf)
                issues.extend(forbidden_issues)

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="validation",
                message=f"Validation error: {e}"
            ))

        # Calculate score and validity
        score = self._calculate_score(issues, stats)
        is_valid = not any(issue.severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR]
                          for issue in issues)

        return self._create_result(is_valid, score, issues, stats, compatibility, file_structure)

    def _analyze_package_stats(self, zipf: zipfile.ZipFile) -> Dict[str, Any]:
        """Analyze package statistics."""
        namelist = zipf.namelist()

        stats = {
            "total_files": len(namelist),
            "total_size_compressed": sum(info.compress_size for info in zipf.infolist()),
            "total_size_uncompressed": sum(info.file_size for info in zipf.infolist()),
            "behavior_packs": set(),
            "resource_packs": set(),
            "file_types": {},
            "largest_files": []
        }

        for info in zipf.infolist():
            if not info.is_dir():
                ext = Path(info.filename).suffix.lower()
                stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1

                if info.filename.startswith('behavior_packs/'):
                    parts = info.filename.split('/')
                    if len(parts) > 1:
                        stats['behavior_packs'].add(parts[1])
                elif info.filename.startswith('resource_packs/'):
                    parts = info.filename.split('/')
                    if len(parts) > 1:
                        stats['resource_packs'].add(parts[1])

                if info.file_size > 1024 * 1024:
                    stats['largest_files'].append({
                        'filename': info.filename,
                        'size_mb': info.file_size / (1024 * 1024)
                    })

        # Convert sets to lists
        stats['behavior_packs'] = list(stats['behavior_packs'])
        stats['resource_packs'] = list(stats['resource_packs'])

        stats['largest_files'].sort(key=lambda x: x['size_mb'], reverse=True)
        stats['largest_files'] = stats['largest_files'][:10]

        return stats

    def _validate_structure(self, zipf: zipfile.ZipFile) -> Tuple[List[ValidationIssue], Dict[str, Any]]:
        """Validate package folder structure."""
        issues = []
        structure = {
            "behavior_packs": [],
            "resource_packs": [],
            "unexpected_files": []
        }

        namelist = zipf.namelist()

        # Check for required directories (plural forms)
        has_behavior_packs = any(name.startswith('behavior_packs/') for name in namelist)
        has_resource_packs = any(name.startswith('resource_packs/') for name in namelist)

        if not has_behavior_packs and not has_resource_packs:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="structure",
                message="Package must contain behavior_packs/ or resource_packs/ directory",
                suggestion="Ensure you're using plural directory names (behavior_packs/, resource_packs/)"
            ))

        # Check for old incorrect singular forms
        has_old_behavior = any(name.startswith('behavior_pack/') for name in namelist)
        has_old_resource = any(name.startswith('resource_pack/') for name in namelist)

        if has_old_behavior or has_old_resource:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="structure",
                message="Found incorrect directory structure (singular form)",
                suggestion="Use 'behavior_packs/' and 'resource_packs/' (plural) instead of singular forms"
            ))

        # Identify pack directories
        for name in namelist:
            if name.startswith('behavior_packs/'):
                parts = name.split('/')
                if len(parts) > 1:
                    pack_name = parts[1]
                    if pack_name not in structure['behavior_packs']:
                        structure['behavior_packs'].append(pack_name)

            elif name.startswith('resource_packs/'):
                parts = name.split('/')
                if len(parts) > 1:
                    pack_name = parts[1]
                    if pack_name not in structure['resource_packs']:
                        structure['resource_packs'].append(pack_name)

        # Validate each pack's internal structure
        for pack_name in structure['behavior_packs']:
            pack_issues = self._validate_behavior_pack_structure(zipf, pack_name, namelist)
            issues.extend(pack_issues)

        for pack_name in structure['resource_packs']:
            pack_issues = self._validate_resource_pack_structure(zipf, pack_name, namelist)
            issues.extend(pack_issues)

        # Check for unexpected root-level files
        root_files = [name for name in namelist if '/' not in name.strip('/')]
        if root_files:
            structure['unexpected_files'] = root_files
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                category="structure",
                message=f"Found {len(root_files)} files in package root",
                suggestion="Files should be in behavior_packs/ or resource_packs/ subdirectories"
            ))

        return issues, structure

    def _validate_behavior_pack_structure(
        self,
        zipf: zipfile.ZipFile,
        pack_name: str,
        namelist: List[str]
    ) -> List[ValidationIssue]:
        """Validate behavior pack structure."""
        issues = []
        prefix = f'behavior_packs/{pack_name}/'

        # Check for manifest.json
        manifest_path = f'{prefix}manifest.json'
        if manifest_path not in namelist:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="structure",
                message=f"Missing manifest.json in behavior pack '{pack_name}'",
                file_path=manifest_path
            ))

        # Check for unexpected directories
        pack_files = [name for name in namelist if name.startswith(prefix)]
        for file_path in pack_files:
            parts = file_path.split('/')
            if len(parts) > 2:
                dir_name = parts[2]
                if dir_name not in self.behavior_pack_dirs:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category="structure",
                        message=f"Unexpected directory '{dir_name}' in behavior pack",
                        file_path=file_path,
                        suggestion=f"Valid directories: {', '.join(sorted(self.behavior_pack_dirs))}"
                    ))

        return issues

    def _validate_resource_pack_structure(
        self,
        zipf: zipfile.ZipFile,
        pack_name: str,
        namelist: List[str]
    ) -> List[ValidationIssue]:
        """Validate resource pack structure."""
        issues = []
        prefix = f'resource_packs/{pack_name}/'

        # Check for manifest.json
        manifest_path = f'{prefix}manifest.json'
        if manifest_path not in namelist:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="structure",
                message=f"Missing manifest.json in resource pack '{pack_name}'",
                file_path=manifest_path
            ))

        # Check for unexpected directories
        pack_files = [name for name in namelist if name.startswith(prefix)]
        for file_path in pack_files:
            parts = file_path.split('/')
            if len(parts) > 2:
                dir_name = parts[2]
                if dir_name not in self.resource_pack_dirs:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.INFO,
                        category="structure",
                        message=f"Unexpected directory '{dir_name}' in resource pack",
                        file_path=file_path,
                        suggestion=f"Valid directories: {', '.join(sorted(self.resource_pack_dirs))}"
                    ))

        return issues

    def _validate_manifests(self, zipf: zipfile.ZipFile) -> List[ValidationIssue]:
        """Validate all manifest.json files."""
        issues = []
        manifest_files = [name for name in zipf.namelist() if name.endswith('manifest.json')]

        if not manifest_files:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.CRITICAL,
                category="manifest",
                message="No manifest.json files found in package"
            ))
            return issues

        uuids = set()

        for manifest_path in manifest_files:
            try:
                with zipf.open(manifest_path) as f:
                    manifest = json.load(f)

                # Schema validation
                if "manifest" in self.schemas:
                    try:
                        jsonschema.validate(manifest, self.schemas["manifest"])
                    except jsonschema.ValidationError as e:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="manifest",
                            message=f"Schema validation failed: {e.message}",
                            file_path=manifest_path,
                            suggestion=f"Check {e.path[0] if e.path else 'root'} field"
                        ))

                # UUID validation
                pack_uuid = manifest.get('header', {}).get('uuid')
                if pack_uuid:
                    try:
                        uuid.UUID(pack_uuid)
                        if pack_uuid in uuids:
                            issues.append(ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                category="manifest",
                                message=f"Duplicate UUID: {pack_uuid}",
                                file_path=manifest_path
                            ))
                        uuids.add(pack_uuid)
                    except ValueError:
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            category="manifest",
                            message=f"Invalid UUID format: {pack_uuid}",
                            file_path=manifest_path
                        ))
                else:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        category="manifest",
                        message="Missing UUID in header",
                        file_path=manifest_path
                    ))

                # Module validation
                modules = manifest.get('modules', [])
                if not modules:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.CRITICAL,
                        category="manifest",
                        message="No modules defined",
                        file_path=manifest_path
                    ))

                for i, module in enumerate(modules):
                    module_uuid = module.get('uuid')
                    if module_uuid:
                        try:
                            uuid.UUID(module_uuid)
                            if module_uuid in uuids:
                                issues.append(ValidationIssue(
                                    severity=ValidationSeverity.ERROR,
                                    category="manifest",
                                    message=f"Duplicate module UUID: {module_uuid}",
                                    file_path=manifest_path
                                ))
                            uuids.add(module_uuid)
                        except ValueError:
                            issues.append(ValidationIssue(
                                severity=ValidationSeverity.ERROR,
                                category="manifest",
                                message=f"Invalid module UUID: {module_uuid}",
                                file_path=manifest_path
                            ))

            except json.JSONDecodeError as e:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.CRITICAL,
                    category="manifest",
                    message=f"Invalid JSON: {e}",
                    file_path=manifest_path
                ))
            except Exception as e:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    category="manifest",
                    message=f"Validation error: {e}",
                    file_path=manifest_path
                ))

        return issues

    def _validate_components(self, zipf: zipfile.ZipFile) -> List[ValidationIssue]:
        """Validate component files (blocks, items, entities)."""
        issues = []

        for info in zipf.infolist():
            if info.is_dir():
                continue

            file_path = info.filename

            # Validate block definitions
            if '/blocks/' in file_path and file_path.endswith('.json'):
                issues.extend(self._validate_block_file(zipf, file_path))

            # Validate item definitions
            elif '/items/' in file_path and file_path.endswith('.json'):
                issues.extend(self._validate_item_file(zipf, file_path))

            # Validate JSON syntax
            elif file_path.endswith('.json'):
                issues.extend(self._validate_json_syntax(zipf, file_path))

        return issues

    def _validate_block_file(self, zipf: zipfile.ZipFile, file_path: str) -> List[ValidationIssue]:
        """Validate a block definition file."""
        issues = []

        try:
            with zipf.open(file_path) as f:
                block_data = json.load(f)

            if "block" in self.schemas:
                try:
                    jsonschema.validate(block_data, self.schemas["block"])
                except jsonschema.ValidationError as e:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="schema",
                        message=f"Block schema validation: {e.message}",
                        file_path=file_path
                    ))

        except json.JSONDecodeError as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="schema",
                message=f"Invalid JSON in block file: {e}",
                file_path=file_path
            ))

        return issues

    def _validate_item_file(self, zipf: zipfile.ZipFile, file_path: str) -> List[ValidationIssue]:
        """Validate an item definition file."""
        issues = []

        try:
            with zipf.open(file_path) as f:
                item_data = json.load(f)

            if "item" in self.schemas:
                try:
                    jsonschema.validate(item_data, self.schemas["item"])
                except jsonschema.ValidationError as e:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="schema",
                        message=f"Item schema validation: {e.message}",
                        file_path=file_path
                    ))

        except json.JSONDecodeError as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="schema",
                message=f"Invalid JSON in item file: {e}",
                file_path=file_path
            ))

        return issues

    def _validate_json_syntax(self, zipf: zipfile.ZipFile, file_path: str) -> List[ValidationIssue]:
        """Validate JSON syntax."""
        issues = []

        try:
            with zipf.open(file_path) as f:
                json.load(f)
        except json.JSONDecodeError as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                category="syntax",
                message=f"Invalid JSON: {e}",
                file_path=file_path
            ))

        return issues

    def _check_forbidden_files(self, zipf: zipfile.ZipFile) -> List[ValidationIssue]:
        """Check for forbidden files and patterns."""
        issues = []

        for name in zipf.namelist():
            for pattern in self.forbidden_patterns:
                if pattern in name:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        category="cleanup",
                        message=f"Found forbidden pattern: {pattern}",
                        file_path=name,
                        suggestion="Remove temporary/system files before packaging"
                    ))
                    break

        return issues

    def _check_compatibility(self, zipf: zipfile.ZipFile) -> Dict[str, Any]:
        """Check Bedrock version compatibility."""
        compatibility = {
            "min_version": [1, 16, 0],
            "detected_features": [],
            "experimental_features": [],
            "platform_support": {
                "bedrock": True,
                "education": True,
                "preview": True
            }
        }

        manifest_files = [name for name in zipf.namelist() if name.endswith('manifest.json')]

        for manifest_path in manifest_files:
            try:
                with zipf.open(manifest_path) as f:
                    manifest = json.load(f)

                capabilities = manifest.get('capabilities', [])
                for cap in capabilities:
                    if 'experimental' in cap.lower():
                        compatibility['experimental_features'].append(cap)
                    compatibility['detected_features'].append(cap)

                min_engine = manifest.get('header', {}).get('min_engine_version', [])
                if min_engine:
                    # Store highest minimum version
                    if self._compare_versions(min_engine, compatibility['min_version']) > 0:
                        compatibility['min_version'] = min_engine

            except Exception:
                continue

        # Check platform-specific restrictions
        script_files = [name for name in zipf.namelist() if name.endswith('.js')]
        if script_files:
            compatibility['platform_support']['education'] = False

        return compatibility

    def _compare_versions(self, v1: List[int], v2: List[int]) -> int:
        """Compare version arrays. Returns -1, 0, or 1."""
        max_len = max(len(v1), len(v2))
        for i in range(max_len):
            a = v1[i] if i < len(v1) else 0
            b = v2[i] if i < len(v2) else 0
            if a < b:
                return -1
            elif a > b:
                return 1
        return 0

    def _calculate_score(self, issues: List[ValidationIssue], stats: Dict[str, Any]) -> int:
        """Calculate overall quality score (0-100)."""
        score = 100

        # Deduct points based on severity
        for issue in issues:
            if issue.severity == ValidationSeverity.CRITICAL:
                score -= 20
            elif issue.severity == ValidationSeverity.ERROR:
                score -= 10
            elif issue.severity == ValidationSeverity.WARNING:
                score -= 3

        # Bonus for complete addon
        if stats.get('behavior_packs') and stats.get('resource_packs'):
            score += 5

        return max(0, min(100, score))

    def _create_result(
        self,
        is_valid: bool,
        score: int,
        issues: List[ValidationIssue],
        stats: Dict[str, Any],
        compatibility: Dict[str, Any],
        file_structure: Dict[str, Any]
    ) -> ValidationResult:
        """Create ValidationResult object."""
        # If score is passed as int, use it; otherwise calculate from issues
        if isinstance(score, int) and score >= 0:
            overall_score = score
        else:
            overall_score = self._calculate_score(issues, stats)

        return ValidationResult(
            is_valid=is_valid,
            overall_score=overall_score,
            issues=issues,
            stats=stats,
            compatibility=compatibility,
            file_structure=file_structure
        )

    def generate_report(self, result: ValidationResult) -> str:
        """Generate human-readable validation report."""
        lines = []
        lines.append("=" * 80)
        lines.append("Bedrock .mcaddon Validation Report")
        lines.append("=" * 80)
        lines.append("")

        # Overall status
        status = "PASS" if result.is_valid else "FAIL"
        lines.append(f"Overall Status: {status} (Score: {result.overall_score}/100)")
        lines.append("")

        # Issues by severity
        for severity in [ValidationSeverity.CRITICAL, ValidationSeverity.ERROR,
                        ValidationSeverity.WARNING, ValidationSeverity.INFO]:
            issues = result.get_issues_by_severity(severity)
            if issues:
                lines.append(f"{severity.value.upper()} ({len(issues)}):")
                for issue in issues:
                    location = f" [{issue.file_path}]" if issue.file_path else ""
                    lines.append(f"  - {issue.message}{location}")
                    if issue.suggestion:
                        lines.append(f"    Suggestion: {issue.suggestion}")
                lines.append("")

        # Statistics
        lines.append("Package Statistics:")
        lines.append(f"  Total Files: {result.stats.get('total_files', 0)}")
        lines.append(f"  Behavior Packs: {len(result.stats.get('behavior_packs', []))}")
        lines.append(f"  Resource Packs: {len(result.stats.get('resource_packs', []))}")
        lines.append("")

        # Compatibility
        lines.append("Compatibility:")
        comp = result.compatibility
        lines.append(f"  Minimum Version: {'.'.join(map(str, comp.get('min_version', [1, 16, 0])))}")
        lines.append(f"  Experimental Features: {len(comp.get('experimental_features', []))}")
        lines.append("")

        return "\n".join(lines)
