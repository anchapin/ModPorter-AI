"""
File Integrity Checker

Checks file integrity within generated Bedrock packages.
"""

import logging
import zipfile
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class IntegrityResult:
    """Result of file integrity check."""
    is_valid: bool
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    file_count: int = 0
    json_valid_count: int = 0
    json_invalid_count: int = 0
    js_valid_count: int = 0
    js_invalid_count: int = 0
    file_hashes: Dict[str, str] = field(default_factory=dict)
    path_traversal_detected: bool = False


class FileIntegrityChecker:
    """
    Checks file integrity within packages.
    
    Validates JSON/JavaScript syntax, checks for path traversal,
    and generates checksums.
    """
    
    SUPPORTED_JSON_EXTENSIONS = {'.json', '.jsonc'}
    SUPPORTED_JS_EXTENSIONS = {'.js', '.ts', '.mjs'}
    SUPPORTED_ASSET_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.ogg', '.wav'}
    
    # Required directory structure for Bedrock add-ons
    REQUIRED_DIRS = [
        'manifest.json',  # Root level required
    ]
    
    # Dangerous patterns for path traversal
    DANGEROUS_PATTERNS = ['..', '~/', '/absolute/']
    
    def __init__(self, strict_validation: bool = True):
        self.strict_validation = strict_validation
    
    def check_integrity(self, package_path: str) -> IntegrityResult:
        """
        Check all files in package for integrity.
        
        Args:
            package_path: Path to the .mcaddon package
            
        Returns:
            IntegrityResult with validation status and details
        """
        errors = []
        warnings = []
        file_hashes = {}
        
        if not zipfile.is_zipfile(package_path):
            return IntegrityResult(
                is_valid=False,
                errors=[{
                    "type": "invalid_package",
                    "message": "Package is not a valid ZIP archive"
                }]
            )
        
        json_valid_count = 0
        json_invalid_count = 0
        js_valid_count = 0
        js_invalid_count = 0
        path_traversal_detected = False
        
        try:
            with zipfile.ZipFile(package_path, 'r') as zf:
                file_list = zf.namelist()
                
                # Check for path traversal
                for file_path in file_list:
                    if any(pattern in file_path for pattern in self.DANGEROUS_PATTERNS):
                        path_traversal_detected = True
                        errors.append({
                            "type": "path_traversal",
                            "file": file_path,
                            "message": f"Potentially dangerous path traversal detected: {file_path}"
                        })
                
                # Validate each file
                for file_path in file_list:
                    # Skip directories
                    if file_path.endswith('/'):
                        continue
                    
                    # Generate hash for each file
                    try:
                        file_data = zf.read(file_path)
                        file_hash = hashlib.sha256(file_data).hexdigest()
                        file_hashes[file_path] = file_hash
                    except Exception as e:
                        warnings.append({
                            "type": "hash_error",
                            "file": file_path,
                            "message": f"Failed to generate hash: {e}"
                        })
                    
                    # Validate JSON files
                    file_ext = Path(file_path).suffix.lower()
                    if file_ext in self.SUPPORTED_JSON_EXTENSIONS:
                        if self._is_json_valid(zf, file_path):
                            json_valid_count += 1
                        else:
                            json_invalid_count += 1
                    
                    # Validate JS files (basic syntax check)
                    elif file_ext in self.SUPPORTED_JS_EXTENSIONS:
                        if self._is_js_valid(zf, file_path):
                            js_valid_count += 1
                        else:
                            js_invalid_count += 1
                
                # Check for required files
                if 'manifest.json' not in file_list:
                    errors.append({
                        "type": "missing_required_file",
                        "file": "manifest.json",
                        "message": "manifest.json is required in package root"
                    })
        
        except zipfile.BadZipFile:
            errors.append({
                "type": "corrupt_zip",
                "message": "Package ZIP file is corrupted"
            })
        except Exception as e:
            errors.append({
                "type": "read_error",
                "message": f"Failed to read package: {e}"
            })
        
        is_valid = len(errors) == 0
        
        # Warn about invalid JSON/JS in strict mode
        if self.strict_validation and json_invalid_count > 0:
            warnings.append({
                "type": "invalid_json_files",
                "count": json_invalid_count,
                "message": f"Found {json_invalid_count} invalid JSON files"
            })
        
        if self.strict_validation and js_invalid_count > 0:
            warnings.append({
                "type": "invalid_js_files",
                "count": js_invalid_count,
                "message": f"Found {js_invalid_count} invalid JavaScript files"
            })
        
        return IntegrityResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            file_count=len(file_hashes),
            json_valid_count=json_valid_count,
            json_invalid_count=json_invalid_count,
            js_valid_count=js_valid_count,
            js_invalid_count=js_invalid_count,
            file_hashes=file_hashes,
            path_traversal_detected=path_traversal_detected
        )
    
    def _is_json_valid(self, zf: zipfile.ZipFile, file_path: str) -> bool:
        """Check if a JSON file is valid."""
        try:
            data = zf.read(file_path)
            # Try UTF-8 first, then fallback
            try:
                text = data.decode('utf-8')
            except UnicodeDecodeError:
                text = data.decode('latin-1')
            
            # Remove comments for JSONC files
            if file_path.endswith('.jsonc'):
                text = self._strip_json_comments(text)
            
            json.loads(text)
            return True
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.warning(f"Invalid JSON in {file_path}: {e}")
            return False
        except Exception as e:
            logger.warning(f"Error validating JSON {file_path}: {e}")
            return False
    
    def _is_js_valid(self, zf: zipfile.ZipFile, file_path: str) -> bool:
        """Basic JavaScript syntax validation."""
        try:
            data = zf.read(file_path)
            text = data.decode('utf-8')
            
            # Basic syntax checks
            # Check for balanced braces
            open_braces = text.count('{')
            close_braces = text.count('}')
            if open_braces != close_braces:
                logger.warning(f"Unbalanced braces in {file_path}")
                return False
            
            # Check for balanced brackets
            open_brackets = text.count('[')
            close_brackets = text.count(']')
            if open_brackets != close_brackets:
                logger.warning(f"Unbalanced brackets in {file_path}")
                return False
            
            # Check for balanced parentheses
            open_parens = text.count('(')
            close_parens = text.count(')')
            if open_parens != close_parens:
                logger.warning(f"Unbalanced parentheses in {file_path}")
                return False
            
            return True
        except Exception as e:
            logger.warning(f"Error validating JS {file_path}: {e}")
            return False
    
    def _strip_json_comments(self, text: str) -> str:
        """Strip JSON comments for JSONC validation."""
        # Remove single-line comments
        text = ''.join(
            line.split('//')[0] for line in text.split('\n')
        )
        # Remove multi-line comments
        import re
        text = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
        return text
    
    def generate_package_hash(self, package_path: str) -> str:
        """
        Generate SHA256 hash for entire package.
        
        Args:
            package_path: Path to the package
            
        Returns:
            SHA256 hash as hex string
        """
        sha256 = hashlib.sha256()
        
        with open(package_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        
        return sha256.hexdigest()
