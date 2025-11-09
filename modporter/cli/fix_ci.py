#!/usr/bin/env python3
"""
Fix Failing CI Checks - Automated CI failure detection and resolution
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import requests
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class CIFixer:
    """Automated CI failure detection and resolution tool."""
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.backup_branch = None
        self.original_branch = None
        
    def run_command(self, cmd: List[str], check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a shell command and return the result."""
        logger.debug(f"Running command: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd, 
                cwd=self.repo_path,
                check=check,
                capture_output=capture_output,
                text=True
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)}")
            logger.error(f"Error output: {e.stderr}")
            raise
    
    def detect_current_pr(self) -> Optional[Dict[str, Any]]:
        """Detect the current pull request."""
        try:
            # Get current branch name
            result = self.run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            branch_name = result.stdout.strip()
            
            if branch_name == "HEAD":
                # Detached HEAD, try to get the branch we're on
                result = self.run_command(["git", "branch", "--show-current"])
                branch_name = result.stdout.strip()
            
            if branch_name == "main" or branch_name == "master":
                logger.warning("You appear to be on the main branch. CI fixes are typically done on feature branches.")
                return None
            
            # Find PR for this branch
            result = self.run_command(["gh", "pr", "list", "--head", branch_name, "--json", "number,title,state,url"])
            prs = json.loads(result.stdout)
            
            if not prs:
                logger.error(f"No PR found for branch '{branch_name}'. Please create a PR first.")
                return None
            
            pr = prs[0]
            logger.info(f"Detected PR #{pr['number']}: {pr['title']}")
            return pr
            
        except subprocess.CalledProcessError as e:
            logger.error("Failed to detect current PR. Make sure 'gh' CLI is installed and authenticated.")
            return None
    
    def get_failing_jobs(self, pr_number: int) -> List[Dict[str, Any]]:
        """Get list of failing CI jobs for the PR."""
        try:
            result = self.run_command(["gh", "pr", "checks", "--json", "name,conclusion,detailsUrl,status,workflowName"])
            checks = json.loads(result.stdout)
            
            failing_jobs = []
            for check in checks:
                if check.get('conclusion') == 'failure' or check.get('status') == 'failure':
                    failing_jobs.append(check)
            
            logger.info(f"Found {len(failing_jobs)} failing jobs")
            for job in failing_jobs:
                logger.info(f"  - {job.get('workflowName', 'Unknown')}: {job.get('name', 'Unknown')} - {job.get('conclusion', 'Unknown')}")
            
            return failing_jobs
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to fetch CI job status: {e}")
            return []
    
    def download_job_logs(self, job: Dict[str, Any]) -> str:
        """Download logs for a failing job."""
        log_dir = self.repo_path / "logs"
        log_dir.mkdir(exist_ok=True)
        
        job_name = re.sub(r'[^a-zA-Z0-9_-]', '_', job.get('name', 'job'))
        log_file = log_dir / f"{job_name}_{int(time.time())}.log"
        
        try:
            # Get the workflow run URL
            details_url = job.get('detailsUrl')
            if not details_url:
                logger.warning(f"No details URL found for job {job.get('name')}")
                return ""
            
            # Use gh CLI to get logs
            # Extract workflow run ID from details URL
            # Format: https://github.com/owner/repo/actions/runs/1234567
            match = re.search(r'/runs/(\d+)', details_url)
            if not match:
                logger.warning(f"Could not extract run ID from URL: {details_url}")
                return ""
            
            run_id = match.group(1)
            
            # Get job name and attempt to download logs
            result = self.run_command(["gh", "run", "view", run_id, "--log", "--job", job.get('name', '')])
            
            with open(log_file, 'w') as f:
                f.write(result.stdout)
            
            logger.info(f"Downloaded logs for {job.get('name')} to {log_file}")
            return str(log_file)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to download logs for {job.get('name')}: {e}")
            return ""
    
    def analyze_failure_patterns(self, log_files: List[str]) -> Dict[str, List[str]]:
        """Analyze failure patterns from log files."""
        patterns = {
            'test_failures': [],
            'linting_errors': [],
            'type_errors': [],
            'build_errors': [],
            'dependency_issues': [],
            'import_errors': [],
            'syntax_errors': []
        }
        
        for log_file in log_files:
            if not Path(log_file).exists():
                continue
                
            with open(log_file, 'r') as f:
                content = f.read()
            
            # Test failures
            if re.search(r'(FAILED|ERROR).*test', content, re.IGNORECASE):
                test_matches = re.findall(r'(FAILED|ERROR).*test.*?::[^\\n]+', content, re.IGNORECASE)
                patterns['test_failures'].extend(test_matches)
            
            # Linting errors (flake8, pylint, etc.)
            if re.search(r'(E\d+|W\d+|F\d+|C\d+)', content):
                lint_matches = re.findall(r'[A-Z]\d+.*?\\d+:\\d+.*', content)
                patterns['linting_errors'].extend(lint_matches)
            
            # Type checking errors (mypy)
            if re.search(r'(error|Error).*type', content):
                type_matches = re.findall(r'error:.*?type.*', content, re.IGNORECASE)
                patterns['type_errors'].extend(type_matches)
            
            # Build errors
            if re.search(r'(build|Build).*failed|error', content):
                build_matches = re.findall(r'(build|Build).*failed.*|error.*', content)
                patterns['build_errors'].extend(build_matches)
            
            # Dependency issues
            if re.search(r'(dependency|Dependency|import|Import).*error', content):
                dep_matches = re.findall(r'(dependency|Dependency|import|Import).*error.*', content, re.IGNORECASE)
                patterns['dependency_issues'].extend(dep_matches)
            
            # Import errors
            if re.search(r'ModuleNotFoundError|ImportError', content):
                import_matches = re.findall(r'ModuleNotFoundError.*|ImportError.*', content)
                patterns['import_errors'].extend(import_matches)
            
            # Syntax errors
            if re.search(r'SyntaxError|syntax error', content):
                syntax_matches = re.findall(r'SyntaxError.*|syntax error.*', content)
                patterns['syntax_errors'].extend(syntax_matches)
        
        return patterns
    
    def create_backup_branch(self) -> str:
        """Create a backup branch before making changes."""
        try:
            # Get current branch
            result = self.run_command(["git", "rev-parse", "--abbrev-ref", "HEAD"])
            current_branch = result.stdout.strip()
            self.original_branch = current_branch
            
            # Create backup branch name
            timestamp = int(time.time())
            backup_branch = f"ci-fix-backup-{timestamp}"
            
            # Create backup branch
            self.run_command(["git", "checkout", "-b", backup_branch])
            self.backup_branch = backup_branch
            
            logger.info(f"Created backup branch: {backup_branch}")
            return backup_branch
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to create backup branch: {e}")
            return ""
    
    def fix_linting_errors(self, errors: List[str]) -> bool:
        """Fix linting errors using auto-formatters."""
        if not errors:
            return True
            
        logger.info("Attempting to fix linting errors...")
        
        try:
            # Try black formatting
            try:
                self.run_command(["black", "."], check=False)
                logger.info("Applied black formatting")
            except FileNotFoundError:
                logger.warning("black not found, skipping formatting")
            
            # Try isort
            try:
                self.run_command(["isort", "."], check=False)
                logger.info("Applied isort formatting")
            except FileNotFoundError:
                logger.warning("isort not found, skipping import sorting")
            
            # Try autoflake
            try:
                self.run_command(["autoflake", "--in-place", "--remove-all-unused-imports", "--remove-unused-variables", "-r", "."], check=False)
                logger.info("Applied autoflake cleanup")
            except FileNotFoundError:
                logger.warning("autoflake not found, skipping unused import removal")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to fix linting errors: {e}")
            return False
    
    def fix_type_errors(self, errors: List[str]) -> bool:
        """Fix type checking errors."""
        if not errors:
            return True
            
        logger.info("Attempting to fix type errors...")
        
        # For now, just log the errors - automatic type error fixing is complex
        logger.warning("Type errors require manual fixing:")
        for error in errors[:5]:  # Show first 5 errors
            logger.warning(f"  - {error}")
        
        return False
    
    def fix_test_failures(self, failures: List[str]) -> bool:
        """Fix test failures by updating tests."""
        if not failures:
            return True
            
        logger.info("Analyzing test failures...")
        
        # Parse test failures to extract file and test names
        test_files = set()
        for failure in failures:
            # Extract file path from failure message
            match = re.search(r'test_([^:]+)::', failure)
            if match:
                test_file = match.group(1)
                test_files.add(f"test_{test_file}.py")
        
        logger.warning(f"Test failures found in files: {', '.join(test_files)}")
        logger.warning("Test failures require manual investigation and fixing.")
        
        return False
    
    def fix_dependency_issues(self, issues: List[str]) -> bool:
        """Fix dependency issues."""
        if not issues:
            return True
            
        logger.info("Attempting to fix dependency issues...")
        
        try:
            # Try to install missing dependencies
            requirements_files = [
                "requirements.txt",
                "requirements-test.txt", 
                "requirements-dev.txt",
                "pyproject.toml"
            ]
            
            for req_file in requirements_files:
                if Path(self.repo_path / req_file).exists():
                    if req_file.endswith('.txt'):
                        self.run_command(["pip", "install", "-r", req_file], check=False)
                    elif req_file == "pyproject.toml":
                        self.run_command(["pip", "install", "-e", "."], check=False)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to fix dependency issues: {e}")
            return False
    
    def run_verification_tests(self) -> bool:
        """Run local tests to verify fixes."""
        logger.info("Running verification tests...")
        
        test_commands = []
        
        # Check for pytest
        if Path(self.repo_path / "pytest.ini").exists() or Path(self.repo_path / "pyproject.toml").exists():
            test_commands.append(["pytest", "--cov=quantchain", "tests/"])
        
        # Check for linting
        try:
            self.run_command(["which", "flake8"], check=False, capture_output=True)
            if Path(self.repo_path / ".flake8").exists() or Path(self.repo_path / "pyproject.toml").exists():
                test_commands.append(["flake8", "quantchain", "tests/"])
        except:
            pass
        
        # Check for mypy
        try:
            self.run_command(["which", "mypy"], check=False, capture_output=True)
            if Path(self.repo_path / "mypy.ini").exists() or Path(self.repo_path / "pyproject.toml").exists():
                test_commands.append(["mypy", "quantchain"])
        except:
            pass
        
        # Check formatting
        try:
            self.run_command(["which", "black"], check=False, capture_output=True)
            test_commands.append(["black", "--check", "quantchain", "tests/"])
        except:
            pass
        
        success = True
        for cmd in test_commands:
            try:
                logger.info(f"Running: {' '.join(cmd)}")
                self.run_command(cmd)
                logger.info(f"✅ {' '.join(cmd)} passed")
            except subprocess.CalledProcessError:
                logger.error(f"❌ {' '.join(cmd)} failed")
                success = False
        
        return success
    
    def commit_changes(self, message: str) -> bool:
        """Commit changes with a descriptive message."""
        try:
            # Stage all changes
            self.run_command(["git", "add", "."])
            
            # Check if there are changes to commit
            result = self.run_command(["git", "status", "--porcelain"])
            if not result.stdout.strip():
                logger.info("No changes to commit")
                return True
            
            # Commit changes
            self.run_command(["git", "commit", "-m", message])
            logger.info(f"Committed changes: {message}")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to commit changes: {e}")
            return False
    
    def rollback_if_needed(self, verification_passed: bool) -> bool:
        """Rollback changes if verification failed."""
        if verification_passed:
            return True
            
        logger.warning("Verification failed, attempting to rollback...")
        
        try:
            if self.backup_branch and self.original_branch:
                # Switch back to original branch
                self.run_command(["git", "checkout", self.original_branch])
                
                # Delete the working branch (we're currently on it)
                self.run_command(["git", "branch", "-D", self.backup_branch])
                
                logger.info("Successfully rolled back changes")
                return True
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to rollback changes: {e}")
        
        return False
    
    def fix_failing_ci(self) -> bool:
        """Main method to fix failing CI checks."""
        logger.info("🔧 Starting CI fix process...")
        
        # Step 1: Detect current PR
        pr = self.detect_current_pr()
        if not pr:
            logger.error("Could not detect current PR. Please create a PR first.")
            return False
        
        # Step 2: Identify failing jobs
        failing_jobs = self.get_failing_jobs(pr['number'])
        if not failing_jobs:
            logger.info("✅ No failing jobs found. CI is already passing!")
            return True
        
        # Step 3: Download failure logs
        log_files = []
        for job in failing_jobs:
            log_file = self.download_job_logs(job)
            if log_file:
                log_files.append(log_file)
        
        if not log_files:
            logger.error("Could not download any job logs")
            return False
        
        # Step 4: Analyze failure patterns
        patterns = self.analyze_failure_patterns(log_files)
        
        logger.info("\n📊 Failure Analysis:")
        for pattern_type, errors in patterns.items():
            if errors:
                logger.info(f"  {pattern_type}: {len(errors)} issues")
        
        # Step 5: Create backup branch
        backup_branch = self.create_backup_branch()
        if not backup_branch:
            logger.error("Failed to create backup branch, aborting")
            return False
        
        # Step 6: Apply fixes
        fixes_applied = []
        
        # Fix linting errors
        if patterns['linting_errors']:
            if self.fix_linting_errors(patterns['linting_errors']):
                fixes_applied.append("Fixed linting errors with auto-formatters")
        
        # Fix dependency issues
        if patterns['dependency_issues'] or patterns['import_errors']:
            if self.fix_dependency_issues(patterns['dependency_issues'] + patterns['import_errors']):
                fixes_applied.append("Fixed dependency issues")
        
        # Fix type errors (manual intervention required)
        if patterns['type_errors']:
            fixes_applied.append("Type errors identified (manual fixing required)")
        
        # Fix test failures (manual intervention required)
        if patterns['test_failures']:
            fixes_applied.append("Test failures identified (manual fixing required)")
        
        if not fixes_applied:
            logger.info("No automatic fixes applicable")
            return True
        
        # Step 7: Commit changes
        commit_message = f"fix(ci): automated fixes for PR #{pr['number']}\\n\\n"
        commit_message += "\\n".join(f"- {fix}" for fix in fixes_applied)
        
        if not self.commit_changes(commit_message):
            logger.error("Failed to commit changes")
            return False
        
        # Step 8: Verify fixes
        logger.info("\n🧪 Running verification tests...")
        verification_passed = self.run_verification_tests()
        
        # Step 9: Rollback if verification failed
        if not self.rollback_if_needed(verification_passed):
            logger.error("Verification failed and rollback failed")
            return False
        
        if verification_passed:
            logger.info("\n✅ All fixes applied successfully!")
            logger.info(f"📝 Committed changes: {commit_message}")
            logger.info("💡 You can now push the changes to trigger CI again")
        else:
            logger.info("\n⚠️  Automatic verification failed. Manual review required.")
            logger.info("📝 Changes were rolled back to maintain branch stability")
        
        return verification_passed


def main():
    """Main entry point for the CI fix command."""
    parser = argparse.ArgumentParser(
        description='Fix failing CI checks for the current PR',
        prog='fix-failing-ci-checks'
    )
    
    parser.add_argument(
        '--repo-path',
        default='.',
        help='Path to the repository (default: current directory)'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create CI fixer and run the process
    fixer = CIFixer(args.repo_path)
    success = fixer.fix_failing_ci()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
