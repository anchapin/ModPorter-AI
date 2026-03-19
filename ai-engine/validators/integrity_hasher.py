"""
Integrity Hasher

Generates checksums for output files.
"""

import logging
import zipfile
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class HashResult:
    """Result of hash generation."""
    package_hash: str
    file_hashes: Dict[str, str] = field(default_factory=dict)
    hash_algorithm: str = "sha256"
    generated_at: str = ""
    total_files: int = 0
    total_size: int = 0


class IntegrityHasher:
    """
    Generates checksums for output files.
    
    Creates SHA256 hashes for all files in a package and
    generates a package-level hash for verification.
    """
    
    def __init__(self, algorithm: str = "sha256"):
        self.algorithm = algorithm.lower()
        
        if self.algorithm not in ['sha256', 'sha1', 'md5']:
            logger.warning(f"Unsupported algorithm {algorithm}, defaulting to sha256")
            self.algorithm = 'sha256'
    
    def generate_hashes(self, package_path: str) -> HashResult:
        """
        Generate SHA256 hashes for all files.
        
        Args:
            package_path: Path to the .mcaddon package
            
        Returns:
            HashResult with all file hashes and package hash
        """
        file_hashes = {}
        total_size = 0
        
        try:
            with zipfile.ZipFile(package_path, 'r') as zf:
                for file_path in zf.namelist():
                    if file_path.endswith('/'):
                        continue
                    
                    try:
                        file_data = zf.read(file_path)
                        file_hash = self._hash_data(file_data)
                        file_hashes[file_path] = file_hash
                        total_size += len(file_data)
                    except Exception as e:
                        logger.warning(f"Failed to hash {file_path}: {e}")
                        file_hashes[file_path] = f"ERROR: {str(e)}"
        
        except Exception as e:
            logger.error(f"Failed to generate hashes: {e}")
            return HashResult(
                package_hash="ERROR",
                file_hashes={},
                hash_algorithm=self.algorithm,
                generated_at=datetime.utcnow().isoformat(),
                error=str(e)
            )
        
        # Generate package hash from all file hashes
        package_hash = self._generate_package_hash(file_hashes)
        
        return HashResult(
            package_hash=package_hash,
            file_hashes=file_hashes,
            hash_algorithm=self.algorithm,
            generated_at=datetime.utcnow().isoformat(),
            total_files=len(file_hashes),
            total_size=total_size
        )
    
    def _hash_data(self, data: bytes) -> str:
        """Hash data using the configured algorithm."""
        if self.algorithm == 'sha256':
            return hashlib.sha256(data).hexdigest()
        elif self.algorithm == 'sha1':
            return hashlib.sha1(data).hexdigest()
        elif self.algorithm == 'md5':
            return hashlib.md5(data).hexdigest()
        else:
            return hashlib.sha256(data).hexdigest()
    
    def _generate_package_hash(self, file_hashes: Dict[str, str]) -> str:
        """Generate a single hash for the entire package from file hashes."""
        # Sort keys for deterministic hashing
        sorted_hashes = sorted(file_hashes.values())
        
        # Combine all hashes
        combined = ''.join(sorted_hashes)
        
        return self._hash_data(combined.encode('utf-8'))
    
    def verify_hashes(
        self,
        package_path: str,
        expected_hashes: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Verify hashes against expected values.
        
        Args:
            package_path: Path to the package
            expected_hashes: Expected hash values
            
        Returns:
            Verification result with matches/mismatches
        """
        actual_hashes = self.generate_hashes(package_path)
        
        matches = {}
        mismatches = {}
        
        for file_path, expected_hash in expected_hashes.items():
            actual_hash = actual_hashes.file_hashes.get(file_path, 'NOT_FOUND')
            
            if actual_hash == expected_hash:
                matches[file_path] = actual_hash
            else:
                mismatches[file_path] = {
                    'expected': expected_hash,
                    'actual': actual_hash
                }
        
        all_match = len(mismatches) == 0
        
        return {
            'verified': all_match,
            'total_files': len(expected_hashes),
            'matched_count': len(matches),
            'mismatched_count': len(mismatches),
            'matches': matches,
            'mismatches': mismatches,
            'package_hash': actual_hashes.package_hash
        }
    
    def generate_manifest(
        self,
        package_path: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Generate a hash manifest JSON file.
        
        Args:
            package_path: Path to the package
            metadata: Optional metadata to include
            
        Returns:
            JSON string of hash manifest
        """
        hash_result = self.generate_hashes(package_path)
        
        manifest = {
            'hash_algorithm': hash_result.hash_algorithm,
            'generated_at': hash_result.generated_at,
            'package_hash': hash_result.package_hash,
            'total_files': hash_result.total_files,
            'total_size': hash_result.total_size,
            'files': hash_result.file_hashes,
        }
        
        if metadata:
            manifest['metadata'] = metadata
        
        return json.dumps(manifest, indent=2)
