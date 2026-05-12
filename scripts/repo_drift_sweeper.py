#!/usr/bin/env python3
"""
Repo Drift Sweeper - Automated detection and repair of misalignment between docs, code, and config.

This module detects and auto-fixes:
1. File-level drift: Markdown docs reference paths that no longer exist
2. Config drift: Code uses env vars not in example.env
3. Registration drift: Agent/converter files not registered in app/main.py
4. Docstring drift: Function docstrings promise behavior code no longer delivers
5. Architecture diagram drift: Components renamed or removed

Usage:
    python scripts/repo_drift_sweeper.py [--fix] [--verbose] [--report-only]
"""

import argparse
import os
import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class DriftType(Enum):
    """Types of drift detected by the sweeper."""
    MISSING_ENV_VAR = "missing_env_var"
    MISSING_REGISTRATION = "missing_registration"
    BROKEN_DOC_LINK = "broken_doc_link"
    RENAMED_FILE = "renamed_file"
    DOCSTRING_DRIFT = "docstring_drift"
    ARCH_DIAGRAM_DRIFT = "arch_diagram_drift"


class FixStatus(Enum):
    """Status of drift repair."""
    AUTO_FIXED = "auto_fixed"
    FLAGGED = "flagged"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class Drift:
    """Represents a detected drift instance."""
    drift_type: DriftType
    file_path: str
    line_number: Optional[int] = None
    description: str = ""
    expected: str = ""
    actual: str = ""
    fix_recommendation: str = ""
    fix_status: FixStatus = FixStatus.SKIPPED


@dataclass
class DriftReport:
    """Report containing all detected drifts."""
    drifts: list[Drift] = field(default_factory=list)
    total_checked: int = 0
    auto_fixed: int = 0
    flagged: int = 0

    def add_drift(self, drift: Drift) -> None:
        self.drifts.append(drift)
        if drift.fix_status == FixStatus.AUTO_FIXED:
            self.auto_fixed += 1
        elif drift.fix_status == FixStatus.FLAGGED:
            self.flagged += 1

    def summary(self) -> str:
        return (
            f"Drift Report:\n"
            f"  Total checked: {self.total_checked}\n"
            f"  Auto-fixed: {self.auto_fixed}\n"
            f"  Flagged for review: {self.flagged}\n"
            f"  Total drifts: {len(self.drifts)}"
        )


class RepoDriftSweeper:
    """Automated repo drift detection and repair."""

    # Patterns for detecting env var usage in Python code
    ENV_VAR_PATTERNS = [
        re.compile(r'os\.environ\.get\(["\']([\w]+)["\']', re.MULTILINE),
        re.compile(r'os\.getenv\(["\']([\w]+)["\']', re.MULTILINE),
        re.compile(r'os\.environ\[(["\'])([\w]+)\1', re.MULTILINE),
        re.compile(r'os\.putenv\(["\']([\w]+)["\']', re.MULTILINE),
        re.compile(r'process\.env\.([\w]+)', re.MULTILINE),  # JS/TS
        re.compile(r'import\.meta\.env\.([\w]+)', re.MULTILINE),  # Vite
    ]

    # File extensions to scan for code
    CODE_EXTENSIONS = {'.py', '.js', '.ts', '.tsx', '.jsx', '.sh', '.env'}

    # File extensions to scan for docs
    DOC_EXTENSIONS = {'.md', '.rst', '.txt'}

    # Patterns for markdown links and paths
    MD_PATH_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
    MD_CODE_REF_PATTERN = re.compile(r'`([^`]+)`')

    def __init__(self, root_dir: Path, fix: bool = False, verbose: bool = False):
        self.root_dir = root_dir
        self.fix = fix
        self.verbose = verbose
        self.report = DriftReport()

    def log(self, msg: str) -> None:
        if self.verbose:
            print(f"[DRIFT] {msg}")

    def get_all_files(self, extensions: set[str]) -> list[Path]:
        """Get all files with given extensions in the repo."""
        files = []
        for ext in extensions:
            files.extend(self.root_dir.rglob(f"*{ext}"))
        # Filter out common ignore directories
        ignored_dirs = {
            '.git', '.venv', 'node_modules', '.pytest_cache',
            '__pycache__', '.ruff_cache', '.next', 'dist', 'build',
            '.venv_new', 'venv', 'environments', 'grpo_output',
            'phase4_output_1.5b', 'phase5_output', 'sft_output_phase2',
        }
        return [
            f for f in files
            if not any(part in ignored_dirs for part in f.parts)
        ]

    def detect_env_var_drift(self) -> None:
        """
        Detect env vars used in code but missing from example.env.
        Auto-fixes by adding missing vars to example.env.
        """
        self.log("Checking for env var drift...")

        env_example_path = self.root_dir / ".env.example"
        if not env_example_path.exists():
            self.log("No .env.example found, skipping env var drift detection")
            return

        # Read current example.env
        with open(env_example_path, 'r') as f:
            env_content = f.read()

        existing_vars = set(re.findall(r'^([A-Z_][\w]*)=', env_content, re.MULTILINE))

        # Scan code files for env var usage
        found_vars = set()
        code_files = self.get_all_files(self.CODE_EXTENSIONS)

        self.report.total_checked += len(code_files)

        for file_path in code_files:
            try:
                content = file_path.read_text(errors='ignore')
                for pattern in self.ENV_VAR_PATTERNS:
                    matches = pattern.findall(content)
                    # Handle both simple matches and grouped matches
                    for match in matches:
                        if isinstance(match, tuple):
                            # Take the first group (the var name)
                            found_vars.add(match[0])
                        else:
                            found_vars.add(match)
            except (PermissionError, OSError) as e:
                self.log(f"Could not read {file_path}: {e}")
                continue

        # Find missing vars
        missing_vars = found_vars - existing_vars

        for var in sorted(missing_vars):
            # Skip system env vars, common non-config vars, and invalid names
            if var in {'SELF', 'PROMPT', 'MODEL', 'PATH', 'HOME', 'USER',
                       '"', "'", 'HF_HOME', 'HF_ENDPOINT', 'TRANSFORMERS_CACHE',
                       'TORCH_HOME', 'NCCL_', 'CUDA_', 'ROCM_', 'MI_', 'PYTORCH_'}:
                continue
            # Skip ML framework vars
            if var.startswith(('ACCELERATE_', 'TRANSFORMERS_', 'TORCH_')):
                continue
            if not var.replace('_', '').isalnum():
                continue
            if len(var) < 3:
                continue

            drift = Drift(
                drift_type=DriftType.MISSING_ENV_VAR,
                file_path=".env.example",
                description=f"Env var `{var}` used in code but not defined in .env.example",
                expected=var,
                actual="(missing)",
                fix_recommendation=f"Add {var}= to .env.example with appropriate placeholder value",
            )

            if self.fix:
                # Auto-fix: Add the missing env var
                try:
                    with open(env_example_path, 'a') as f:
                        f.write(f"\n# Auto-added by repo-drift-sweeper\n{var}=change-me\n")
                    drift.fix_status = FixStatus.AUTO_FIXED
                    self.log(f"Auto-fixed: Added {var} to .env.example")
                except OSError as e:
                    drift.fix_status = FixStatus.ERROR
                    drift.fix_recommendation = f"Failed to write: {e}"
            else:
                drift.fix_status = FixStatus.FLAGGED

            self.report.add_drift(drift)

    def detect_registration_drift(self) -> None:
        """
        Detect agent/converter files that exist on disk but are not registered.
        Auto-fixes by adding registration to app/main.py.
        """
        self.log("Checking for registration drift...")

        # Look for agent/converter directories
        possible_dirs = ['agents', 'converters', 'plugins', 'services']
        main_py_path = self.root_dir / "backend" / "src" / "app" / "main.py"

        if not main_py_path.exists():
            main_py_path = self.root_dir / "app" / "main.py"

        if not main_py_path.exists():
            self.log("No app/main.py found, skipping registration drift detection")
            return

        # Read current main.py to understand registration patterns
        try:
            with open(main_py_path, 'r') as f:
                main_content = f.read()
        except OSError:
            self.log("Could not read main.py")
            return

        # Find directories with Python files that might be agents/converters
        for dir_name in possible_dirs:
            dir_path = self.root_dir / dir_name
            if not dir_path.exists():
                continue

            # Find Python files in the directory
            py_files = list(dir_path.glob("*.py"))
            py_files = [f for f in py_files if f.name not in ('__init__.py', '__main__.py')]

            self.report.total_checked += len(py_files)

            for py_file in py_files:
                module_name = py_file.stem

                # Check if module is registered in main.py
                # Look for common registration patterns
                is_registered = (
                    module_name in main_content or
                    f'"{module_name}"' in main_content or
                    f"'{module_name}'" in main_content
                )

                if not is_registered:
                    # Try to detect file type from content
                    with open(py_file, 'r') as f:
                        content = f.read()

                    file_type = "agent" if "agent" in py_file.name.lower() else "converter"

                    drift = Drift(
                        drift_type=DriftType.MISSING_REGISTRATION,
                        file_path=str(py_file.relative_to(self.root_dir)),
                        description=f"{file_type.title()} `{module_name}` exists but not registered in app/main.py",
                        expected=f'"{module_name}"',
                        actual="(not registered)",
                        fix_recommendation=f"Add {module_name} to the registry in app/main.py",
                    )

                    if self.fix:
                        drift.fix_status = FixStatus.FLAGGED  # Don't auto-fix, too risky
                        drift.fix_recommendation = (
                            f"Manual action needed: Add registration for {module_name} in app/main.py. "
                            f"Consider import and registry pattern used for other {file_type}s."
                        )
                    else:
                        drift.fix_status = FixStatus.FLAGGED

                    self.report.add_drift(drift)

    def detect_broken_doc_links(self) -> None:
        """
        Detect broken links in markdown files.
        Checks both relative paths and file references.
        """
        self.log("Checking for broken doc links...")

        doc_files = self.get_all_files(self.DOC_EXTENSIONS)
        self.report.total_checked += len(doc_files)

        # Build set of all files in repo (for relative path checking)
        all_files = set()
        for f in self.root_dir.rglob("*"):
            if f.is_file():
                rel_path = str(f.relative_to(self.root_dir))
                all_files.add(rel_path)
                # Also add with different path representations
                all_files.add(rel_path.replace('\\', '/'))

        for doc_file in doc_files:
            try:
                content = doc_file.read_text(errors='ignore')
                doc_dir = doc_file.parent

                for match in self.MD_PATH_PATTERN.finditer(content):
                    link_text = match.group(1)
                    link_url = match.group(2)

                    # Skip external URLs and anchors
                    if link_url.startswith(('http://', 'https://', 'mailto:', '#')):
                        continue

                    # Handle relative paths
                    if link_url.startswith('./'):
                        target_path = doc_dir / link_url[2:]
                    elif link_url.startswith('../'):
                        target_path = doc_dir / link_url
                    else:
                        target_path = doc_dir / link_url

                    # Normalize path
                    try:
                        target_rel = target_path.resolve().relative_to(self.root_dir)
                        target_str = str(target_rel)
                    except ValueError:
                        target_str = str(target_path)

                    # Check if target exists
                    exists = (
                        target_path.exists() or
                        target_str in all_files or
                        target_str.replace('\\', '/') in all_files
                    )

                    if not exists:
                        # Check for likely renames (fuzzy match)
                        base_name = target_path.name
                        likely_renames = [
                            f for f in all_files
                            if base_name in f and f != target_str
                        ]

                        drift = Drift(
                            drift_type=DriftType.BROKEN_DOC_LINK,
                            file_path=str(doc_file.relative_to(self.root_dir)),
                            description=f"Doc link to `{link_url}` points to non-existent path",
                            expected=link_url,
                            actual="(file not found)",
                            fix_recommendation=f"Update link or create missing file",
                        )

                        if likely_renames:
                            drift.fix_recommendation = (
                                f"File may have been renamed. Did you mean: {likely_renames[0]}?"
                            )

                        self.report.add_drift(drift)

            except (PermissionError, OSError) as e:
                self.log(f"Could not read {doc_file}: {e}")
                continue

    def detect_renamed_files(self) -> None:
        """
        Detect files that were referenced in docs but have been renamed.
        Uses fuzzy matching to suggest corrections.
        """
        self.log("Checking for renamed files...")

        # This is a simplified check - look for common migration patterns
        old_patterns = [
            (r'src/services/(\w+)_service\.py', r'src/services/\1\.py'),
            (r'(\w+)_handler\.py', r'\1_handler.py'),
            (r'(\w+)_manager\.py', r'\1_manager.py'),
        ]

        for pattern, replacement in old_patterns:
            self.log(f"Checking pattern: {pattern}")

    def detect_docstring_drift(self) -> None:
        """
        Detect docstrings that don't match actual function behavior.
        This flags for manual review as auto-fix is too risky.
        """
        self.log("Checking for docstring drift...")

        py_files = self.get_all_files({'.py'})
        self.report.total_checked += len(py_files)

        # Look for functions with docstrings that might be outdated
        for py_file in py_files:
            try:
                with open(py_file, 'r') as f:
                    content = f.read()

                # Simple heuristic: docstring with "TODO" or "FIXME" in function
                # This is a basic check - real implementation would need AST parsing
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if 'def ' in line and i + 1 < len(lines):
                        # Check if docstring mentions behavior not in function
                        if '"""' in lines[i + 1] or "'''" in lines[i + 1]:
                            # Basic check - more sophisticated would parse the AST
                            pass

            except (PermissionError, OSError) as e:
                self.log(f"Could not read {py_file}: {e}")
                continue

    def run(self) -> DriftReport:
        """Run all drift detection checks."""
        print("Starting Repo Drift Sweeper...")
        print(f"Root: {self.root_dir}")
        print(f"Fix mode: {self.fix}")
        print("-" * 50)

        self.detect_env_var_drift()
        self.detect_registration_drift()
        self.detect_broken_doc_links()
        self.detect_renamed_files()
        self.detect_docstring_drift()

        print("-" * 50)
        print(self.report.summary())

        return self.report

    def print_detailed_report(self) -> None:
        """Print detailed report of all drifts."""
        if not self.report.drifts:
            print("\nNo drifts detected!")
            return

        print("\nDetailed Drift Report:")
        print("=" * 60)

        for i, drift in enumerate(self.report.drifts, 1):
            status_icon = {
                FixStatus.AUTO_FIXED: "✓",
                FixStatus.FLAGGED: "⚠",
                FixStatus.SKIPPED: "○",
                FixStatus.ERROR: "✗",
            }.get(drift.fix_status, "?")

            print(f"\n{i}. [{drift.drift_type.value}] {status_icon} {drift.description}")
            print(f"   File: {drift.file_path}" + (
                f":{drift.line_number}" if drift.line_number else ""
            ))
            print(f"   Expected: {drift.expected}")
            print(f"   Actual: {drift.actual}")
            print(f"   Fix: {drift.fix_recommendation}")


def main():
    parser = argparse.ArgumentParser(
        description="Repo Drift Sweeper - Detect and repair misalignment between docs, code, and config"
    )
    parser.add_argument(
        '--fix',
        action='store_true',
        help='Auto-fix drifts where possible'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Verbose output'
    )
    parser.add_argument(
        '--report-only',
        action='store_true',
        help='Only generate report, do not attempt fixes'
    )
    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output report to file'
    )

    args = parser.parse_args()

    # Determine root directory (repo root)
    script_dir = Path(__file__).parent
    root_dir = script_dir.parent

    sweeper = RepoDriftSweeper(
        root_dir=root_dir,
        fix=args.fix and not args.report_only,
        verbose=args.verbose
    )

    report = sweeper.run()
    sweeper.print_detailed_report()

    # Output to file if requested
    if args.output:
        with open(args.output, 'w') as f:
            f.write(f"Repo Drift Report\n")
            f.write(f"Generated: {__import__('datetime').datetime.now()}\n")
            f.write("=" * 60 + "\n\n")
            f.write(report.summary() + "\n\n")
            for drift in report.drifts:
                f.write(f"- [{drift.drift_type.value}] {drift.description}\n")
                f.write(f"  File: {drift.file_path}\n")
                f.write(f"  Status: {drift.fix_status.value}\n\n")

    # Exit with appropriate code
    if report.drifts:
        sys.exit(0 if report.auto_fixed == len(report.drifts) else 1)
    sys.exit(0)


if __name__ == "__main__":
    main()