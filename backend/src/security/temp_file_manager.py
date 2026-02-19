"""
Secure temporary file management for file processing operations.

This module provides secure handling of temporary files including:
- Secure creation and cleanup
- Orphaned file detection
- Disk space monitoring
- Automatic cleanup on errors

Issue: #576 - Backend: File Processing Security
"""

import atexit
import logging
import os
import shutil
import tempfile
import threading
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set, Generator, Any

logger = logging.getLogger(__name__)


@dataclass
class TempFileConfig:
    """Configuration for temporary file management."""
    # Base directory for temp files
    base_dir: Optional[Path] = None
    
    # Prefix for temp directories
    directory_prefix: str = "modporter_"
    
    # Maximum age of temp files before cleanup (in hours)
    max_file_age_hours: int = 24
    
    # Cleanup interval (in minutes)
    cleanup_interval_minutes: int = 30
    
    # Maximum total temp directory size (in MB)
    max_total_size_mb: int = 1024  # 1GB
    
    # Enable automatic cleanup on exit
    cleanup_on_exit: bool = True
    
    # Track all created temp paths
    track_files: bool = True


@dataclass
class TempFileInfo:
    """Information about a tracked temporary file/directory."""
    path: Path
    created_at: datetime
    job_id: Optional[str] = None
    size_bytes: int = 0
    is_directory: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "path": str(self.path),
            "created_at": self.created_at.isoformat(),
            "job_id": self.job_id,
            "size_bytes": self.size_bytes,
            "is_directory": self.is_directory
        }


class SecureTempFileManager:
    """
    Secure manager for temporary file operations.
    
    This class provides:
    - Secure temporary directory creation
    - Automatic cleanup of old files
    - Orphaned file detection
    - Disk space monitoring
    - Thread-safe operations
    """
    
    def __init__(self, config: Optional[TempFileConfig] = None):
        """Initialize with optional custom config."""
        self.config = config or TempFileConfig()
        
        # Set base directory
        if self.config.base_dir:
            self._base_dir = Path(self.config.base_dir)
        else:
            self._base_dir = Path(tempfile.gettempdir()) / "modporter_conversions"
        
        # Ensure base directory exists
        self._base_dir.mkdir(parents=True, exist_ok=True)
        
        # Track created files/directories
        self._tracked_files: Dict[str, TempFileInfo] = {}
        self._lock = threading.Lock()
        
        # Register cleanup on exit
        if self.config.cleanup_on_exit:
            atexit.register(self.cleanup_all)
        
        # Start background cleanup thread
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()
    
    def start_background_cleanup(self) -> None:
        """Start the background cleanup thread."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._stop_cleanup.clear()
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_loop,
                daemon=True
            )
            self._cleanup_thread.start()
            logger.info("Started background temp file cleanup thread")
    
    def stop_background_cleanup(self) -> None:
        """Stop the background cleanup thread."""
        self._stop_cleanup.set()
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)
            logger.info("Stopped background temp file cleanup thread")
    
    def create_temp_directory(
        self,
        job_id: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> Path:
        """
        Create a secure temporary directory.
        
        Args:
            job_id: Optional job ID to associate with the directory
            prefix: Optional custom prefix
            
        Returns:
            Path to the created directory
        """
        # Generate unique directory name
        dir_prefix = prefix or self.config.directory_prefix
        unique_id = str(uuid.uuid4())[:8]
        dir_name = f"{dir_prefix}{unique_id}"
        
        if job_id:
            dir_name = f"{dir_prefix}{job_id}_{unique_id}"
        
        dir_path = self._base_dir / dir_name
        
        # Create directory with secure permissions
        dir_path.mkdir(parents=True, exist_ok=True)
        
        # Set restrictive permissions (owner only)
        try:
            os.chmod(dir_path, 0o700)
        except Exception as e:
            logger.warning(f"Could not set directory permissions: {e}")
        
        # Track the directory
        if self.config.track_files:
            with self._lock:
                self._tracked_files[str(dir_path)] = TempFileInfo(
                    path=dir_path,
                    created_at=datetime.utcnow(),
                    job_id=job_id,
                    is_directory=True
                )
        
        logger.debug(f"Created temp directory: {dir_path}")
        return dir_path
    
    def create_temp_file(
        self,
        suffix: Optional[str] = None,
        prefix: Optional[str] = None,
        job_id: Optional[str] = None,
        directory: Optional[Path] = None
    ) -> Path:
        """
        Create a secure temporary file.
        
        Args:
            suffix: Optional file suffix/extension
            prefix: Optional file prefix
            job_id: Optional job ID to associate
            directory: Optional parent directory
            
        Returns:
            Path to the created file
        """
        # Use provided directory or create one
        if directory is None:
            directory = self.create_temp_directory(job_id=job_id)
        
        # Generate unique filename
        file_prefix = prefix or "temp_"
        unique_id = str(uuid.uuid4())[:8]
        file_name = f"{file_prefix}{unique_id}"
        
        if suffix:
            file_name = f"{file_name}{suffix}"
        
        file_path = directory / file_name
        
        # Create the file
        file_path.touch()
        
        # Set restrictive permissions
        try:
            os.chmod(file_path, 0o600)
        except Exception as e:
            logger.warning(f"Could not set file permissions: {e}")
        
        # Track the file
        if self.config.track_files:
            with self._lock:
                self._tracked_files[str(file_path)] = TempFileInfo(
                    path=file_path,
                    created_at=datetime.utcnow(),
                    job_id=job_id,
                    is_directory=False
                )
        
        logger.debug(f"Created temp file: {file_path}")
        return file_path
    
    @contextmanager
    def temp_directory(
        self,
        job_id: Optional[str] = None,
        prefix: Optional[str] = None
    ) -> Generator[Path, None, None]:
        """
        Context manager for a temporary directory that auto-cleans.
        
        Args:
            job_id: Optional job ID
            prefix: Optional custom prefix
            
        Yields:
            Path to the temporary directory
        """
        dir_path = self.create_temp_directory(job_id=job_id, prefix=prefix)
        try:
            yield dir_path
        finally:
            self.cleanup_directory(dir_path)
    
    @contextmanager
    def temp_file(
        self,
        suffix: Optional[str] = None,
        prefix: Optional[str] = None,
        job_id: Optional[str] = None
    ) -> Generator[Path, None, None]:
        """
        Context manager for a temporary file that auto-cleans.
        
        Args:
            suffix: Optional file suffix
            prefix: Optional file prefix
            job_id: Optional job ID
            
        Yields:
            Path to the temporary file
        """
        file_path = self.create_temp_file(
            suffix=suffix,
            prefix=prefix,
            job_id=job_id
        )
        try:
            yield file_path
        finally:
            self.cleanup_file(file_path)
    
    def cleanup_directory(self, dir_path: Path) -> bool:
        """
        Clean up a temporary directory.
        
        Args:
            dir_path: Path to the directory to clean up
            
        Returns:
            True if cleanup was successful
        """
        try:
            if not dir_path.exists():
                return True
            
            # Remove directory and all contents
            shutil.rmtree(dir_path)
            
            # Remove from tracking
            with self._lock:
                self._tracked_files.pop(str(dir_path), None)
            
            logger.debug(f"Cleaned up temp directory: {dir_path}")
            return True
        
        except PermissionError as e:
            logger.error(f"Permission error cleaning up {dir_path}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error cleaning up {dir_path}: {e}")
            return False
    
    def cleanup_file(self, file_path: Path) -> bool:
        """
        Clean up a temporary file.
        
        Args:
            file_path: Path to the file to clean up
            
        Returns:
            True if cleanup was successful
        """
        try:
            if not file_path.exists():
                return True
            
            file_path.unlink()
            
            # Remove from tracking
            with self._lock:
                self._tracked_files.pop(str(file_path), None)
            
            logger.debug(f"Cleaned up temp file: {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error cleaning up {file_path}: {e}")
            return False
    
    def cleanup_job_files(self, job_id: str) -> int:
        """
        Clean up all files associated with a job.
        
        Args:
            job_id: Job ID to clean up
            
        Returns:
            Number of files/directories cleaned
        """
        cleaned = 0
        
        with self._lock:
            # Find all files for this job
            job_files = [
                info for info in self._tracked_files.values()
                if info.job_id == job_id
            ]
        
        for info in job_files:
            if info.is_directory:
                if self.cleanup_directory(info.path):
                    cleaned += 1
            else:
                if self.cleanup_file(info.path):
                    cleaned += 1
        
        logger.info(f"Cleaned up {cleaned} temp files/directories for job {job_id}")
        return cleaned
    
    def cleanup_old_files(self, max_age_hours: Optional[int] = None) -> int:
        """
        Clean up files older than the specified age.
        
        Args:
            max_age_hours: Maximum age in hours (uses config if not specified)
            
        Returns:
            Number of files/directories cleaned
        """
        max_age = max_age_hours or self.config.max_file_age_hours
        cutoff = datetime.utcnow() - timedelta(hours=max_age)
        cleaned = 0
        
        with self._lock:
            old_files = [
                info for info in self._tracked_files.values()
                if info.created_at < cutoff
            ]
        
        for info in old_files:
            if info.is_directory:
                if self.cleanup_directory(info.path):
                    cleaned += 1
            else:
                if self.cleanup_file(info.path):
                    cleaned += 1
        
        # Also check for orphaned files in base directory
        cleaned += self._cleanup_orphaned_files(cutoff)
        
        logger.info(f"Cleaned up {cleaned} old temp files/directories")
        return cleaned
    
    def cleanup_all(self) -> int:
        """
        Clean up all tracked temporary files.
        
        Returns:
            Number of files/directories cleaned
        """
        cleaned = 0
        
        with self._lock:
            all_files = list(self._tracked_files.values())
        
        for info in all_files:
            if info.is_directory:
                if self.cleanup_directory(info.path):
                    cleaned += 1
            else:
                if self.cleanup_file(info.path):
                    cleaned += 1
        
        logger.info(f"Cleaned up all {cleaned} temp files/directories")
        return cleaned
    
    def find_orphaned_files(self) -> List[Path]:
        """
        Find orphaned temp files that aren't being tracked.
        
        Returns:
            List of orphaned file paths
        """
        orphaned = []
        
        if not self._base_dir.exists():
            return orphaned
        
        # Get all tracked paths
        with self._lock:
            tracked_paths = {str(info.path) for info in self._tracked_files.values()}
        
        # Check all files in base directory
        for entry in self._base_dir.iterdir():
            if str(entry) not in tracked_paths:
                orphaned.append(entry)
        
        return orphaned
    
    def get_total_size(self) -> int:
        """
        Get total size of all temp files in bytes.
        
        Returns:
            Total size in bytes
        """
        total_size = 0
        
        if not self._base_dir.exists():
            return total_size
        
        for entry in self._base_dir.rglob('*'):
            if entry.is_file():
                try:
                    total_size += entry.stat().st_size
                except Exception:
                    pass
        
        return total_size
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about temp file usage.
        
        Returns:
            Dictionary with stats
        """
        with self._lock:
            tracked_count = len(self._tracked_files)
            directories = sum(1 for info in self._tracked_files.values() if info.is_directory)
            files = tracked_count - directories
        
        total_size = self.get_total_size()
        orphaned = self.find_orphaned_files()
        
        return {
            "base_directory": str(self._base_dir),
            "tracked_files": files,
            "tracked_directories": directories,
            "total_size_bytes": total_size,
            "total_size_mb": total_size / (1024 * 1024),
            "orphaned_files": len(orphaned),
            "max_size_mb": self.config.max_total_size_mb
        }
    
    def _cleanup_orphaned_files(self, cutoff: datetime) -> int:
        """
        Clean up orphaned files older than the cutoff.
        
        Args:
            cutoff: Cutoff datetime
            
        Returns:
            Number of files cleaned
        """
        cleaned = 0
        orphaned = self.find_orphaned_files()
        
        for path in orphaned:
            try:
                # Check age
                stat = path.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                
                if mtime < cutoff:
                    if path.is_dir():
                        shutil.rmtree(path)
                    else:
                        path.unlink()
                    cleaned += 1
                    logger.debug(f"Cleaned up orphaned: {path}")
            except Exception as e:
                logger.warning(f"Could not clean orphaned file {path}: {e}")
        
        return cleaned
    
    def _cleanup_loop(self) -> None:
        """Background cleanup loop."""
        while not self._stop_cleanup.wait(
            self.config.cleanup_interval_minutes * 60
        ):
            try:
                self.cleanup_old_files()
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")


# Global temp file manager instance
_temp_file_manager: Optional[SecureTempFileManager] = None


def get_temp_file_manager() -> SecureTempFileManager:
    """Get or create the global temp file manager instance."""
    global _temp_file_manager
    if _temp_file_manager is None:
        _temp_file_manager = SecureTempFileManager()
    return _temp_file_manager


# Convenience functions
def create_temp_directory(job_id: Optional[str] = None) -> Path:
    """Create a temporary directory using the global manager."""
    return get_temp_file_manager().create_temp_directory(job_id=job_id)


def cleanup_job_files(job_id: str) -> int:
    """Clean up all files for a job using the global manager."""
    return get_temp_file_manager().cleanup_job_files(job_id)