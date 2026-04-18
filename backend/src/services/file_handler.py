"""
File Handler Service for ModPorter-AI.

Provides:
- JAR/ZIP file validation
- Metadata extraction from JAR files
- Mod loader identification (Forge/Fabric/NeoForge)
- Malware scanning via ClamAV
- Auto-deletion of uploaded files after conversion

Issue: #973 - File upload security: sandboxing, validation, and virus scanning
"""

import os
import json
import zipfile
import logging
import asyncio
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from services.malware_scanner import scan_file_for_malware, ScanStatus, get_scanner
from services.audit_logger import get_audit_logger, AuditEventType
from core.storage import storage_manager

logger = logging.getLogger(__name__)


class ModLoader(Enum):
    """Minecraft mod loader types"""

    FORGE = "forge"
    FABRIC = "fabric"
    NEOFORGE = "neoforge"
    UNKNOWN = "unknown"


@dataclass
class ModMetadata:
    """Metadata extracted from a mod JAR"""

    modid: Optional[str] = None
    name: Optional[str] = None
    version: Optional[str] = None
    description: Optional[str] = None
    author: Optional[str] = None
    mod_loader: ModLoader = ModLoader.UNKNOWN
    mc_version: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of file validation"""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class ProcessingResult:
    """Result of file processing"""

    success: bool
    job_id: str
    metadata: Optional[ModMetadata] = None
    validation: Optional[ValidationResult] = None
    error: Optional[str] = None


class FileHandler:
    """
    Service for handling JAR file operations.

    Responsibilities:
    - Validate JAR/ZIP structure
    - Extract metadata from mods
    - Identify mod loader
    - Provide virus scanning placeholder
    """

    # Required files in a valid JAR
    REQUIRED_FILES = []

    # Manifest file path in JAR
    MANIFEST_PATH = "META-INF/MANIFEST.MF"

    # Mod metadata file paths
    FABRIC_MOD_JSON = "fabric.mod.json"
    FORGE_MOD_TOML = "META-INF/mods.toml"
    NEOFORGE_MOD_TOML = "META-INF/neoforge.mods.toml"

    def __init__(self):
        self._upload_status: Dict[str, Dict[str, Any]] = {}

    async def process_file(self, job_id: str, file_path: str) -> ProcessingResult:
        """
        Process an uploaded JAR file.

        Steps:
        1. Validate file structure
        2. Extract metadata
        3. Identify mod loader
        4. Run virus scan placeholder

        Args:
            job_id: Unique job identifier
            file_path: Path to the uploaded file

        Returns:
            ProcessingResult with metadata and validation status
        """
        logger.info(f"Processing file for job {job_id}: {file_path}")

        # Update status
        self._upload_status[job_id] = {
            "status": "processing",
            "progress": 0,
            "message": "Starting file validation",
        }

        try:
            # Step 1: Validate file
            validation = await self.validate_jar(file_path)
            if not validation.is_valid:
                self._upload_status[job_id] = {
                    "status": "failed",
                    "progress": 0,
                    "message": f"Validation failed: {', '.join(validation.errors)}",
                }
                return ProcessingResult(
                    success=False,
                    job_id=job_id,
                    validation=validation,
                    error=f"Validation failed: {', '.join(validation.errors)}",
                )

            self._upload_status[job_id] = {
                "status": "processing",
                "progress": 30,
                "message": "Validating file structure",
            }

            # Step 2: Extract metadata
            metadata = await self.extract_metadata(file_path)

            self._upload_status[job_id] = {
                "status": "processing",
                "progress": 60,
                "message": "Extracting metadata",
            }

            # Step 3: Identify mod loader
            mod_loader = await self.identify_mod_loader(file_path)
            metadata.mod_loader = mod_loader

            self._upload_status[job_id] = {
                "status": "processing",
                "progress": 80,
                "message": "Identifying mod loader",
            }

            # Step 4: Malware scan via ClamAV
            scan_passed, scan_status = await self.virus_scan(file_path, job_id)
            if not scan_passed:
                self._upload_status[job_id] = {
                    "status": "failed",
                    "progress": 0,
                    "message": f"Security scan failed: {scan_status}",
                }
                # Delete the infected/malicious file
                await self.delete_uploaded_file(
                    job_id, file_path, reason=f"security_scan_failed: {scan_status}"
                )
                return ProcessingResult(
                    success=False,
                    job_id=job_id,
                    validation=validation,
                    error=f"Security scan failed: {scan_status}",
                )

            self._upload_status[job_id] = {
                "status": "completed",
                "progress": 100,
                "message": "File processed successfully",
            }

            logger.info(f"File processed successfully for job {job_id}")

            return ProcessingResult(
                success=True, job_id=job_id, metadata=metadata, validation=validation
            )

        except Exception as e:
            logger.error(f"Error processing file for job {job_id}: {str(e)}")
            self._upload_status[job_id] = {
                "status": "failed",
                "progress": 0,
                "message": f"Processing error: {str(e)}",
            }
            return ProcessingResult(success=False, job_id=job_id, error=str(e))

    async def validate_jar(self, file_path: str) -> ValidationResult:
        """
        Validate JAR/ZIP file structure.

        Checks:
        - File exists and is readable
        - Valid ZIP/JAR format
        - Contains required structure
        - Manifest file present
        """
        errors = []
        warnings = []

        # Check file exists
        if not os.path.exists(file_path):
            errors.append(f"File not found: {file_path}")
            return ValidationResult(is_valid=False, errors=errors)

        # Check file is not empty
        if os.path.getsize(file_path) == 0:
            errors.append("File is empty")
            return ValidationResult(is_valid=False, errors=errors)

        # Check valid ZIP format
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                # Check ZIP is valid
                bad_file = zf.testzip()
                if bad_file is not None:
                    errors.append(f"Corrupt file in archive: {bad_file}")

                # Check for manifest (recommended but not strictly required)
                file_list = zf.namelist()
                if self.MANIFEST_PATH not in file_list:
                    warnings.append("No META-INF/MANIFEST.MF found - may not be a valid mod")

        except zipfile.BadZipFile:
            errors.append("Invalid ZIP/JAR file format")
            return ValidationResult(is_valid=False, errors=errors)
        except Exception as e:
            errors.append(f"Error reading file: {str(e)}")
            return ValidationResult(is_valid=False, errors=errors)

        return ValidationResult(is_valid=len(errors) == 0, errors=errors, warnings=warnings)

    async def extract_metadata(self, file_path: str) -> ModMetadata:
        """
        Extract metadata from a mod JAR file.

        Tries multiple sources:
        - fabric.mod.json (Fabric)
        - META-INF/mods.toml (Forge)
        - META-INF/MANIFEST.MF
        """
        metadata = ModMetadata()

        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                file_list = zf.namelist()

                # Try Fabric mod.json
                if self.FABRIC_MOD_JSON in file_list:
                    try:
                        fabric_json = json.loads(zf.read(self.FABRIC_MOD_JSON))
                        metadata.modid = fabric_json.get("id")
                        metadata.name = fabric_json.get("name")
                        metadata.version = fabric_json.get("version")
                        metadata.description = fabric_json.get("description")
                        metadata.author = ", ".join(fabric_json.get("authors", []))
                        metadata.mc_version = fabric_json.get("schema_version")
                        # Get dependencies
                        deps = fabric_json.get("depends", {})
                        metadata.dependencies = list(deps.keys()) if deps else []
                    except (json.JSONDecodeError, KeyError) as e:
                        logger.warning(f"Error parsing fabric.mod.json: {e}")

                # Try Forge mods.toml
                elif self.FORGE_MOD_TOML in file_list:
                    try:
                        toml_content = zf.read(self.FORGE_MOD_TOML).decode("utf-8")
                        # Basic TOML parsing (simplified)
                        metadata = self._parse_forge_mods_toml(toml_content, metadata)
                    except Exception as e:
                        logger.warning(f"Error parsing mods.toml: {e}")

                # Fallback to manifest
                if not metadata.modid and self.MANIFEST_PATH in file_list:
                    try:
                        manifest = zf.read(self.MANIFEST_PATH).decode("utf-8")
                        metadata = self._parse_manifest(manifest, metadata)
                    except Exception as e:
                        logger.warning(f"Error parsing manifest: {e}")

        except Exception as e:
            logger.error(f"Error extracting metadata: {str(e)}")

        return metadata

    def _parse_forge_mods_toml(self, content: str, metadata: ModMetadata) -> ModMetadata:
        """Parse Forge mods.toml content (simplified)"""
        lines = content.split("\n")
        current_section = ""

        for line in lines:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                current_section = line[1:-1]
            elif current_section == "mod" and "=" in line:
                key, value = line.split("=", 1)
                key = key.strip().strip('"')
                value = value.strip().strip('"')

                if key == "modId":
                    metadata.modid = value
                elif key == "displayName":
                    metadata.name = value
                elif key == "version":
                    metadata.version = value
                elif key == "description":
                    metadata.description = value

        return metadata

    def _parse_manifest(self, content: str, metadata: ModMetadata) -> ModMetadata:
        """Parse MANIFEST.MF content"""
        lines = content.split("\n")

        for line in lines:
            if line.startswith("Manifest-Version:"):
                continue
            elif line.startswith("ModId:"):
                metadata.modid = line.split(":", 1)[1].strip()
            elif line.startswith("Mod-Name:"):
                metadata.name = line.split(":", 1)[1].strip()
            elif line.startswith("Version:"):
                metadata.version = line.split(":", 1)[1].strip()
            elif line.startswith("Author:"):
                metadata.author = line.split(":", 1)[1].strip()
            elif line.startswith("Description:"):
                metadata.description = line.split(":", 1)[1].strip()
            elif line.startswith("MCVersion:"):
                metadata.mc_version = line.split(":", 1)[1].strip()

        return metadata

    async def identify_mod_loader(self, file_path: str) -> ModLoader:
        """
        Identify the mod loader from JAR contents.

        Checks for:
        - fabric.mod.json -> Fabric
        - META-INF/neoforge.mods.toml -> NeoForge
        - META-INF/mods.toml -> Forge
        - Known class patterns -> Forge/Fabric
        """
        try:
            with zipfile.ZipFile(file_path, "r") as zf:
                file_list = zf.namelist()

                # Check for loader-specific files
                if self.FABRIC_MOD_JSON in file_list:
                    return ModLoader.FABRIC

                if self.NEOFORGE_MOD_TOML in file_list:
                    return ModLoader.NEOFORGE

                if self.FORGE_MOD_TOML in file_list:
                    return ModLoader.FORGE

                # Check for common class patterns
                has_fabric = any("net/fabricmc" in f for f in file_list)
                has_forge = any("net/minecraftforge" in f for f in file_list)

                if has_fabric and not has_forge:
                    return ModLoader.FABRIC
                elif has_forge:
                    return ModLoader.FORGE

        except Exception as e:
            logger.error(f"Error identifying mod loader: {str(e)}")

        return ModLoader.UNKNOWN

    async def virus_scan(self, file_path: str, job_id: str) -> tuple[bool, str]:
        """
        Scan a file for malware using ClamAV.

        Args:
            file_path: Path to the file to scan
            job_id: Job ID for audit logging

        Returns:
            Tuple of (is_safe, status_message)
        """
        audit = get_audit_logger()

        try:
            scanner = get_scanner()

            # Check if ClamAV is available
            if not scanner.is_available:
                # Try health check
                is_healthy = await scanner.health_check()
                if not is_healthy:
                    logger.warning(f"ClamAV unavailable, skipping malware scan for {file_path}")
                    audit.log_file_scanned(
                        job_id=job_id,
                        filename=file_path,
                        scan_result="skipped",
                        threats_found=[],
                        metadata={"reason": "scanner_unavailable"},
                    )
                    return True, "scanner_unavailable"

            # Perform scan
            result = await scanner.scan_file(file_path)

            if result.status == ScanStatus.CLEAN:
                logger.info(f"File scanned clean: {file_path}")
                audit.log_file_scanned(
                    job_id=job_id,
                    filename=file_path,
                    scan_result="clean",
                    duration_ms=result.scan_duration_ms,
                )
                return True, "clean"

            elif result.status == ScanStatus.INFECTED:
                logger.error(f"INFECTED file detected: {file_path} - {result.threats_found}")
                audit.log_file_scanned(
                    job_id=job_id,
                    filename=file_path,
                    scan_result="infected",
                    threats_found=result.threats_found,
                    duration_ms=result.scan_duration_ms,
                )
                return False, f"infected: {', '.join(result.threats_found)}"

            elif result.status == ScanStatus.SKIPPED:
                logger.warning(f"Scan skipped for {file_path}: {result.error_message}")
                audit.log_file_scanned(
                    job_id=job_id,
                    filename=file_path,
                    scan_result="skipped",
                    metadata={"reason": result.error_message},
                )
                return True, "skipped"

            else:  # ERROR
                logger.error(f"Scan error for {file_path}: {result.error_message}")
                audit.log_file_scanned(
                    job_id=job_id,
                    filename=file_path,
                    scan_result="error",
                    metadata={"error": result.error_message},
                )
                # On error, we fail safe - reject the file
                return False, f"scan_error: {result.error_message}"

        except Exception as e:
            logger.error(f"Virus scan exception for {file_path}: {e}")
            return False, f"scan_exception: {str(e)}"

    async def delete_uploaded_file(
        self, job_id: str, file_path: str, reason: str = "conversion_complete"
    ) -> bool:
        """
        Delete an uploaded file and log the deletion.

        Args:
            job_id: Job ID
            file_path: Path to the file to delete
            reason: Reason for deletion

        Returns:
            True if deleted successfully
        """
        audit = get_audit_logger()

        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(
                    f"Deleted uploaded file: {file_path} (job_id={job_id}, reason={reason})"
                )
                audit.log_file_deleted(
                    job_id=job_id,
                    filename=file_path,
                    deleted_by="system",
                    reason=reason,
                )
                return True
            else:
                logger.warning(f"File not found for deletion: {file_path}")
                return False
        except Exception as e:
            logger.error(f"Error deleting file {file_path}: {e}")
            return False

    async def get_upload_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the current status of an upload job"""
        return self._upload_status.get(job_id)


# Singleton instance
file_handler = FileHandler()

__all__ = [
    "FileHandler",
    "file_handler",
    "ModLoader",
    "ModMetadata",
    "ValidationResult",
    "ProcessingResult",
]
