"""
QA Validation Framework for Bedrock Add-on Output Verification

This module validates generated .mcaddon files against Bedrock specifications
before delivery to users.

Validation Rules:
- manifest: format_version, required fields (uuid, name, version)
- blocks: required fields (format_version, minecraft:block), textures must exist
- textures: PNG format, power of 2 dimensions
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class ValidationStatus(Enum):
    """Validation result status."""
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    SKIP = "skip"


@dataclass
class ValidationResult:
    """Result of a single validation check."""
    check_name: str
    status: ValidationStatus
    message: str
    details: Optional[Dict[str, Any]] = None
    file_path: Optional[str] = None


@dataclass
class QAReport:
    """QA validation report for a Bedrock add-on."""
    pack_name: str
    results: List[ValidationResult] = field(default_factory=list)
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    warning_checks: int = 0
    skipped_checks: int = 0
    
    @property
    def quality_score(self) -> float:
        """Calculate overall quality score (0-100%)."""
        if self.total_checks == 0:
            return 0.0
        # Weight: pass = 1, warning = 0.5, fail = 0
        score = (self.passed_checks * 1.0 + self.warning_checks * 0.5) / self.total_checks * 100
        return round(score, 2)
    
    def add_result(self, result: ValidationResult):
        """Add a validation result and update counters."""
        self.results.append(result)
        self.total_checks += 1
        
        if result.status == ValidationStatus.PASS:
            self.passed_checks += 1
        elif result.status == ValidationStatus.FAIL:
            self.failed_checks += 1
        elif result.status == ValidationStatus.WARNING:
            self.warning_checks += 1
        elif result.status == ValidationStatus.SKIP:
            self.skipped_checks += 1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "pack_name": self.pack_name,
            "quality_score": self.quality_score,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "warning_checks": self.warning_checks,
            "skipped_checks": self.skipped_checks,
            "results": [
                {
                    "check_name": r.check_name,
                    "status": r.status.value,
                    "message": r.message,
                    "details": r.details,
                    "file_path": r.file_path,
                }
                for r in self.results
            ]
        }


class QAValidator:
    """Main QA validator for Bedrock add-ons."""
    
    def __init__(self, output_dir: str):
        """
        Initialize validator with output directory.
        
        Args:
            output_dir: Path to the generated Bedrock add-on directory
        """
        self.output_dir = Path(output_dir)
        self.manifest_path = self.output_dir / "manifest.json"
        self.blocks_dir = self.output_dir / "blocks"
        self.items_dir = self.output_dir / "items"
        self.textures_dir = self.output_dir / "textures"
    
    def validate_all(self, pack_name: str = "Bedrock Add-on") -> QAReport:
        """
        Run all validation checks.
        
        Args:
            pack_name: Name of the pack for the report
            
        Returns:
            QAReport with all validation results
        """
        report = QAReport(pack_name=pack_name)
        
        # Run all validation checks
        self._validate_manifest(report)
        self._validate_blocks(report)
        self._validate_items(report)
        self._validate_textures(report)
        
        return report
    
    def _validate_manifest(self, report: QAReport):
        """Validate manifest.json against schema."""
        # Check manifest exists
        if not self.manifest_path.exists():
            report.add_result(ValidationResult(
                check_name="manifest_exists",
                status=ValidationStatus.FAIL,
                message="manifest.json not found",
                file_path=str(self.manifest_path)
            ))
            return
        
        # Try to load and validate manifest
        try:
            with open(self.manifest_path, 'r') as f:
                manifest = json.load(f)
        except json.JSONDecodeError as e:
            report.add_result(ValidationResult(
                check_name="manifest_valid_json",
                status=ValidationStatus.FAIL,
                message=f"Invalid JSON in manifest.json: {e}",
                file_path=str(self.manifest_path)
            ))
            return
        
        # Check required fields
        required_fields = ["format_version", "header", "modules"]
        missing_fields = [f for f in required_fields if f not in manifest]
        
        if missing_fields:
            report.add_result(ValidationResult(
                check_name="manifest_required_fields",
                status=ValidationStatus.FAIL,
                message=f"Missing required fields: {', '.join(missing_fields)}",
                details={"missing": missing_fields},
                file_path=str(self.manifest_path)
            ))
        else:
            report.add_result(ValidationResult(
                check_name="manifest_required_fields",
                status=ValidationStatus.PASS,
                message="All required fields present",
                file_path=str(self.manifest_path)
            ))
        
        # Validate header
        if "header" in manifest:
            header = manifest["header"]
            header_required = ["name", "uuid", "version"]
            missing_header = [f for f in header_required if f not in header]
            
            if missing_header:
                report.add_result(ValidationResult(
                    check_name="header_required_fields",
                    status=ValidationStatus.FAIL,
                    message=f"Missing required header fields: {', '.join(missing_header)}",
                    details={"missing": missing_header},
                    file_path=str(self.manifest_path)
                ))
            else:
                # Validate UUID format
                uuid = header.get("uuid", "")
                uuid_pattern = "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
                import re
                if re.match(uuid_pattern, uuid):
                    report.add_result(ValidationResult(
                        check_name="header_uuid_format",
                        status=ValidationStatus.PASS,
                        message="UUID format is valid",
                        file_path=str(self.manifest_path)
                    ))
                else:
                    report.add_result(ValidationResult(
                        check_name="header_uuid_format",
                        status=ValidationStatus.FAIL,
                        message="Invalid UUID format",
                        details={"uuid": uuid},
                        file_path=str(self.manifest_path)
                    ))
                
                # Validate version format
                version = header.get("version", [])
                if isinstance(version, list) and len(version) == 3:
                    report.add_result(ValidationResult(
                        check_name="header_version_format",
                        status=ValidationStatus.PASS,
                        message="Version format is valid",
                        details={"version": version},
                        file_path=str(self.manifest_path)
                    ))
                else:
                    report.add_result(ValidationResult(
                        check_name="header_version_format",
                        status=ValidationStatus.FAIL,
                        message="Invalid version format (expected [major, minor, patch])",
                        details={"version": version},
                        file_path=str(self.manifest_path)
                    ))
        
        # Validate modules
        if "modules" in manifest:
            modules = manifest["modules"]
            if len(modules) > 0:
                report.add_result(ValidationResult(
                    check_name="modules_exist",
                    status=ValidationStatus.PASS,
                    message=f"Found {len(modules)} module(s)",
                    details={"module_count": len(modules)},
                    file_path=str(self.manifest_path)
                ))
                
                # Check each module has required fields
                for i, module in enumerate(modules):
                    module_required = ["type", "uuid", "version"]
                    missing_module_fields = [f for f in module_required if f not in module]
                    
                    if missing_module_fields:
                        report.add_result(ValidationResult(
                            check_name=f"module_{i}_required_fields",
                            status=ValidationStatus.FAIL,
                            message=f"Module {i} missing required fields",
                            details={"missing": missing_module_fields},
                            file_path=str(self.manifest_path)
                        ))
            else:
                report.add_result(ValidationResult(
                    check_name="modules_exist",
                    status=ValidationStatus.FAIL,
                    message="No modules defined in manifest",
                    file_path=str(self.manifest_path)
                ))
    
    def _validate_blocks(self, report: QAReport):
        """Validate block definitions."""
        if not self.blocks_dir.exists():
            report.add_result(ValidationResult(
                check_name="blocks_directory_exists",
                status=ValidationStatus.SKIP,
                message="No blocks directory found (optional)",
                file_path=str(self.blocks_dir)
            ))
            return
        
        block_files = list(self.blocks_dir.glob("*.json"))
        
        if not block_files:
            report.add_result(ValidationResult(
                check_name="blocks_exist",
                status=ValidationStatus.WARNING,
                message="No block definition files found",
                file_path=str(self.blocks_dir)
            ))
            return
        
        report.add_result(ValidationResult(
            check_name="blocks_exist",
            status=ValidationStatus.PASS,
            message=f"Found {len(block_files)} block file(s)",
            details={"block_count": len(block_files)},
            file_path=str(self.blocks_dir)
        ))
        
        # Validate each block file
        for block_file in block_files:
            try:
                with open(block_file, 'r') as f:
                    block = json.load(f)
                
                # Check for required block fields
                required = ["format_version"]
                has_block_definition = "minecraft:block" in block
                
                if not has_block_definition:
                    report.add_result(ValidationResult(
                        check_name=f"block_{block_file.stem}_definition",
                        status=ValidationStatus.FAIL,
                        message=f"Block {block_file.stem} missing minecraft:block definition",
                        file_path=str(block_file)
                    ))
                else:
                    # Check block description
                    block_def = block.get("minecraft:block", {})
                    if "description" not in block_def:
                        report.add_result(ValidationResult(
                            check_name=f"block_{block_file.stem}_description",
                            status=ValidationStatus.FAIL,
                            message=f"Block {block_file.stem} missing description",
                            file_path=str(block_file)
                        ))
                    else:
                        report.add_result(ValidationResult(
                            check_name=f"block_{block_file.stem}_valid",
                            status=ValidationStatus.PASS,
                            message=f"Block {block_file.stem} is valid",
                            file_path=str(block_file)
                        ))
                        
            except json.JSONDecodeError as e:
                report.add_result(ValidationResult(
                    check_name=f"block_{block_file.stem}_valid_json",
                    status=ValidationStatus.FAIL,
                    message=f"Invalid JSON in block file: {e}",
                    file_path=str(block_file)
                ))
    
    def _validate_items(self, report: QAReport):
        """Validate item definitions."""
        if not self.items_dir.exists():
            report.add_result(ValidationResult(
                check_name="items_directory_exists",
                status=ValidationStatus.SKIP,
                message="No items directory found (optional)",
                file_path=str(self.items_dir)
            ))
            return
        
        item_files = list(self.items_dir.glob("*.json"))
        
        if not item_files:
            report.add_result(ValidationResult(
                check_name="items_exist",
                status=ValidationStatus.WARNING,
                message="No item definition files found",
                file_path=str(self.items_dir)
            ))
            return
        
        report.add_result(ValidationResult(
            check_name="items_exist",
            status=ValidationStatus.PASS,
            message=f"Found {len(item_files)} item file(s)",
            details={"item_count": len(item_files)},
            file_path=str(self.items_dir)
        ))
        
        # Validate each item file
        for item_file in item_files:
            try:
                with open(item_file, 'r') as f:
                    item = json.load(f)
                
                # Check for required item fields
                has_item_definition = "minecraft:item" in item
                
                if not has_item_definition:
                    report.add_result(ValidationResult(
                        check_name=f"item_{item_file.stem}_definition",
                        status=ValidationStatus.FAIL,
                        message=f"Item {item_file.stem} missing minecraft:item definition",
                        file_path=str(item_file)
                    ))
                else:
                    report.add_result(ValidationResult(
                        check_name=f"item_{item_file.stem}_valid",
                        status=ValidationStatus.PASS,
                        message=f"Item {item_file.stem} is valid",
                        file_path=str(item_file)
                    ))
                        
            except json.JSONDecodeError as e:
                report.add_result(ValidationResult(
                    check_name=f"item_{item_file.stem}_valid_json",
                    status=ValidationStatus.FAIL,
                    message=f"Invalid JSON in item file: {e}",
                    file_path=str(item_file)
                ))
    
    def _validate_textures(self, report: QAReport):
        """Validate texture files."""
        if not self.textures_dir.exists():
            report.add_result(ValidationResult(
                check_name="textures_directory_exists",
                status=ValidationStatus.SKIP,
                message="No textures directory found (optional)",
                file_path=str(self.textures_dir)
            ))
            return
        
        texture_files = []
        for ext in ['.png', '.jpg', '.jpeg']:
            texture_files.extend(self.textures_dir.glob(f"*{ext}"))
        
        if not texture_files:
            report.add_result(ValidationResult(
                check_name="textures_exist",
                status=ValidationStatus.WARNING,
                message="No texture files found",
                file_path=str(self.textures_dir)
            ))
            return
        
        report.add_result(ValidationResult(
            check_name="textures_exist",
            status=ValidationStatus.PASS,
            message=f"Found {len(texture_files)} texture file(s)",
            details={"texture_count": len(texture_files)},
            file_path=str(self.textures_dir)
        ))
        
        # Validate each texture
        for texture_file in texture_files:
            # Check file format
            if texture_file.suffix.lower() != '.png':
                report.add_result(ValidationResult(
                    check_name=f"texture_{texture_file.stem}_format",
                    status=ValidationStatus.WARNING,
                    message=f"Texture {texture_file.name} is not PNG format",
                    file_path=str(texture_file)
                ))
                continue
            
            # Check dimensions are power of 2
            try:
                from PIL import Image
                with Image.open(texture_file) as img:
                    width, height = img.size
                    
                    # Check power of 2
                    def is_power_of_2(n):
                        return n > 0 and (n & (n - 1)) == 0
                    
                    width_pow2 = is_power_of_2(width)
                    height_pow2 = is_power_of_2(height)
                    
                    if width_pow2 and height_pow2:
                        report.add_result(ValidationResult(
                            check_name=f"texture_{texture_file.stem}_dimensions",
                            status=ValidationStatus.PASS,
                            message=f"Texture {texture_file.name} has valid power-of-2 dimensions ({width}x{height})",
                            details={"width": width, "height": height},
                            file_path=str(texture_file)
                        ))
                    else:
                        report.add_result(ValidationResult(
                            check_name=f"texture_{texture_file.stem}_dimensions",
                            status=ValidationStatus.WARNING,
                            message=f"Texture {texture_file.name} dimensions are not power of 2 ({width}x{height})",
                            details={"width": width, "height": height},
                            file_path=str(texture_file)
                        ))
                        
            except ImportError:
                # PIL not available, skip dimension check
                report.add_result(ValidationResult(
                    check_name=f"texture_{texture_file.stem}_dimensions",
                    status=ValidationStatus.SKIP,
                    message=f"Cannot validate dimensions - Pillow not installed",
                    file_path=str(texture_file)
                ))
            except Exception as e:
                report.add_result(ValidationResult(
                    check_name=f"texture_{texture_file.stem}_valid",
                    status=ValidationStatus.FAIL,
                    message=f"Error validating texture: {e}",
                    file_path=str(texture_file)
                ))


def validate_output(output_dir: str, pack_name: str = "Bedrock Add-on") -> QAReport:
    """
    Convenience function to validate a Bedrock add-on output.
    
    Args:
        output_dir: Path to the generated Bedrock add-on directory
        pack_name: Name of the pack for the report
        
    Returns:
        QAReport with all validation results
    """
    validator = QAValidator(output_dir)
    return validator.validate_all(pack_name)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m ai-engine.tools.qa_validator <output_dir>")
        sys.exit(1)
    
    output_dir = sys.argv[1]
    pack_name = sys.argv[2] if len(sys.argv) > 2 else "Bedrock Add-on"
    
    report = validate_output(output_dir, pack_name)
    
    print(f"\n{'='*60}")
    print(f"QA Validation Report: {report.pack_name}")
    print(f"{'='*60}")
    print(f"Quality Score: {report.quality_score}%")
    print(f"Total Checks: {report.total_checks}")
    print(f"  Passed: {report.passed_checks}")
    print(f"  Failed: {report.failed_checks}")
    print(f"  Warnings: {report.warning_checks}")
    print(f"  Skipped: {report.skipped_checks}")
    print(f"{'='*60}\n")
    
    for result in report.results:
        status_icon = {
            ValidationStatus.PASS: "✅",
            ValidationStatus.FAIL: "❌",
            ValidationStatus.WARNING: "⚠️",
            ValidationStatus.SKIP: "⏭️"
        }.get(result.status, "?")
        
        print(f"{status_icon} [{result.status.value.upper()}] {result.check_name}")
        print(f"   {result.message}")
        if result.file_path:
            print(f"   File: {result.file_path}")
        print()
    
    # Exit with error code if any failures
    sys.exit(1 if report.failed_checks > 0 else 0)
