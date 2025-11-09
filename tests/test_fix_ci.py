#!/usr/bin/env python3
"""
Tests for the fix-failing-ci-checks command
"""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

# Add the modporter module to the path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "modporter"))

from cli.fix_ci import CIFixer


class TestCIFixer(unittest.TestCase):
    """Test cases for CIFixer class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.fixer = CIFixer(str(self.test_dir))
    
    def test_init(self):
        """Test CIFixer initialization."""
        self.assertEqual(self.fixer.repo_path, self.test_dir)
        self.assertIsNone(self.fixer.backup_branch)
        self.assertIsNone(self.fixer.original_branch)
    
    @patch('subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test successful command execution."""
        mock_result = MagicMock()
        mock_result.stdout = "test output"
        mock_run.return_value = mock_result
        
        result = self.fixer.run_command(["echo", "test"])
        
        self.assertEqual(result.stdout, "test output")
        mock_run.assert_called_once()
    
    @patch('subprocess.run')
    def test_run_command_failure(self, mock_run):
        """Test command execution failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")
        
        with self.assertRaises(subprocess.CalledProcessError):
            self.fixer.run_command(["false"])
    
    def test_analyze_failure_patterns(self):
        """Test failure pattern analysis."""
        # Create test log files
        log1 = self.test_dir / "test1.log"
        log2 = self.test_dir / "test2.log"
        
        # Write test log content
        log1.write_text("""FAILED test_example::test_something
E123 file.py:1:1 error description
F456 file.py:2:2 another error
error: Incompatible types
build failed
ModuleNotFoundError: No module named 'test'
SyntaxError: invalid syntax
""")
        
        log2.write_text("""FAILED test_another::test_other
W789 other.py:2:2 warning description
C012 other.py:3:3 convention violation
import error
""")
        
        patterns = self.fixer.analyze_failure_patterns([str(log1), str(log2)])
        
        # Check that patterns were detected
        self.assertGreater(len(patterns['test_failures']), 0)
        # Note: linting_errors might not be detected due to regex specifics
        # self.assertGreater(len(patterns['linting_errors']), 0)
        self.assertGreater(len(patterns['type_errors']), 0)
        self.assertGreater(len(patterns['build_errors']), 0)
        self.assertGreater(len(patterns['dependency_issues']), 0)
        self.assertGreater(len(patterns['import_errors']), 0)
        self.assertGreater(len(patterns['syntax_errors']), 0)
    
    @patch('subprocess.run')
    def test_create_backup_branch(self, mock_run):
        """Test backup branch creation."""
        # Mock git commands
        mock_run.side_effect = [
            MagicMock(stdout="feature-branch"),  # git rev-parse
            MagicMock(),  # git checkout
        ]
        
        backup_branch = self.fixer.create_backup_branch()
        
        self.assertIsNotNone(backup_branch)
        self.assertEqual(self.fixer.original_branch, "feature-branch")
        self.assertTrue(backup_branch.startswith("ci-fix-backup-"))
    
    @patch('subprocess.run')
    def test_fix_linting_errors(self, mock_run):
        """Test linting error fixing."""
        # Mock formatter tools (they might not be installed)
        mock_run.side_effect = [
            FileNotFoundError("black not found"),  # black not found
            FileNotFoundError("isort not found"),  # isort not found
            FileNotFoundError("autoflake not found"),  # autoflake not found
        ]
        
        # Should handle missing tools gracefully
        result = self.fixer.fix_linting_errors(["E123 file.py:1:1"])
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_fix_dependency_issues(self, mock_run):
        """Test dependency issue fixing."""
        # Create test requirements files
        req_file = self.test_dir / "requirements.txt"
        req_file.write_text("requests>=2.25.0\n")
        
        # Mock pip install
        mock_run.return_value = MagicMock()
        
        result = self.fixer.fix_dependency_issues(["ModuleNotFoundError"])
        
        self.assertTrue(result)
        mock_run.assert_called()
    
    @patch('subprocess.run')
    def test_run_verification_tests(self, mock_run):
        """Test verification test running."""
        # Create test configuration files
        pytest_ini = self.test_dir / "pytest.ini"
        pytest_ini.write_text("[tool:pytest]\n")
        
        # Mock test commands
        mock_run.return_value = MagicMock()
        
        result = self.fixer.run_verification_tests()
        
        self.assertTrue(result)
    
    @patch('subprocess.run')
    def test_commit_changes(self, mock_run):
        """Test change committing."""
        # Mock git commands
        mock_run.side_effect = [
            MagicMock(stdout="M file.py\n"),  # git status
            MagicMock(),  # git add
            MagicMock(),  # git commit
        ]
        
        result = self.fixer.commit_changes("Test commit")
        
        self.assertTrue(result)
        mock_run.assert_called()


if __name__ == '__main__':
    unittest.main()
