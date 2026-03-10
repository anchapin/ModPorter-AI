"""
Dependency detection utilities for identifying unused imports and packages.

This module provides functionality to detect:
1. Unused imports in Python source files
2. Unused packages in requirements.txt or pyproject.toml
"""

import ast
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class UnusedImport:
    """Represents an unused import found in a file."""

    file_path: str
    line_number: int
    import_statement: str
    imported_names: list[str]


@dataclass
class UnusedPackage:
    """Represents an unused package found in requirements."""

    package_name: str
    source_file: str
    reason: str = ""


@dataclass
class DependencyReport:
    """Complete dependency analysis report."""

    unused_imports: list[UnusedImport] = field(default_factory=list)
    unused_packages: list[UnusedPackage] = field(default_factory=list)
    files_scanned: int = 0
    packages_scanned: int = 0


class ImportVisitor(ast.NodeVisitor):
    """AST visitor to extract imports and their usage from a Python file."""

    def __init__(self, source_code: str):
        self.source_lines = source_code.split("\n")
        self.imports: dict[str, list[tuple[int, str]]] = {}
        self.defined_names: set[str] = set()
        self.used_names: set[str] = set()
        self.current_function = None
        self.current_class = None

    def visit_Import(self, node: ast.Import):
        """Visit import statements."""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            full_name = alias.name.split(".")[0]
            if full_name not in self.imports:
                self.imports[full_name] = []
            self.imports[full_name].append((node.lineno, name))

    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from...import statements."""
        module = node.module or ""
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            if name == "*":
                continue  # Skip wildcard imports
            full_name = module.split(".")[0] if module else name
            if full_name not in self.imports:
                self.imports[full_name] = []
            self.imports[full_name].append((node.lineno, name))

    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track function definitions."""
        old_func = self.current_function
        self.current_function = node.name
        self.defined_names.add(node.name)
        self.generic_visit(node)
        self.current_function = old_func

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Track async function definitions."""
        old_func = self.current_function
        self.current_function = node.name
        self.defined_names.add(node.name)
        self.generic_visit(node)
        self.current_function = old_func

    def visit_ClassDef(self, node: ast.ClassDef):
        """Track class definitions."""
        old_class = self.current_class
        self.current_class = node.name
        self.defined_names.add(node.name)
        self.generic_visit(node)
        self.current_class = old_class

    def visit_Name(self, node: ast.Name):
        """Track name usage."""
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        """Track attribute access."""
        self.used_names.add(node.attr)
        self.generic_visit(node)

    def get_unused_imports(self) -> list[UnusedImport]:
        """Get list of unused imports."""
        unused = []
        for module, imports in self.imports.items():
            for line_no, imported_name in imports:
                # Check if the imported name is used
                if imported_name not in self.used_names:
                    # Also check if it's defined in this file
                    if imported_name not in self.defined_names:
                        # Get the original import statement
                        if line_no <= len(self.source_lines):
                            stmt = self.source_lines[line_no - 1].strip()
                        else:
                            stmt = f"import {imported_name}"
                        unused.append(
                            UnusedImport(
                                file_path="",
                                line_number=line_no,
                                import_statement=stmt,
                                imported_names=[imported_name],
                            )
                        )
        return unused


def parse_requirements_file(file_path: str) -> dict[str, str]:
    """Parse a requirements.txt file and return package names with versions."""
    packages = {}
    if not os.path.exists(file_path):
        return packages

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith("#"):
                continue
            # Skip -r, -e, and other flags
            if line.startswith("-"):
                continue

            # Parse package name and version
            # Handle various formats: package, package==version, package>=version, etc.
            match = re.match(r"^([a-zA-Z0-9_-]+)([<>=!~]+.+)?", line)
            if match:
                pkg_name = match.group(1).lower().replace("-", "_")
                version = match.group(2) or ""
                packages[pkg_name] = version

    return packages


def parse_pyproject_dependencies(file_path: str) -> dict[str, str]:
    """Parse dependencies from pyproject.toml."""
    packages = {}
    if not os.path.exists(file_path):
        return packages

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Simple regex-based parsing for dependencies
    # Look for dependencies = [ ... ] or project.dependencies = [ ... ]
    import re

    # Match various dependency formats in toml
    patterns = [
        r"dependencies\s*=\s*\[([^\]]+)\]",
        r"project\s*=\s*\{[^}]*dependencies\s*=\s*\[([^\]]+)\]",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content, re.DOTALL)
        for match in matches:
            # Parse each dependency
            deps = re.findall(r'["\']([^"\']+)["\']', match)
            for dep in deps:
                # Handle various formats
                dep_clean = dep.strip()
                match_pkg = re.match(r"^([a-zA-Z0-9_-]+)([<>=!~]+.+)?", dep_clean)
                if match_pkg:
                    pkg_name = match_pkg.group(1).lower().replace("-", "_")
                    version = match_pkg.group(2) or ""
                    packages[pkg_name] = version

    return packages


def scan_python_file(file_path: str) -> list[UnusedImport]:
    """Scan a single Python file for unused imports."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (UnicodeDecodeError, OSError):
        return []

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return []

    visitor = ImportVisitor(source)
    visitor.visit(tree)

    unused = visitor.get_unused_imports()
    for u in unused:
        u.file_path = file_path

    return unused


def find_python_files(root_dir: str, exclude_dirs: Optional[list[str]] = None) -> list[str]:
    """Find all Python files in a directory tree."""
    if exclude_dirs is None:
        exclude_dirs = [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
            ".ruff_cache",
            "mutants",
        ]

    python_files = []
    root = Path(root_dir)

    for path in root.rglob("*.py"):
        # Check if path should be excluded
        if any(excluded in path.parts for excluded in exclude_dirs):
            continue
        python_files.append(str(path))

    return python_files


def scan_directory_for_unused_imports(
    directory: str, exclude_dirs: Optional[list[str]] = None
) -> list[UnusedImport]:
    """Scan a directory for unused imports in all Python files."""
    python_files = find_python_files(directory, exclude_dirs)
    all_unused = []

    for py_file in python_files:
        unused = scan_python_file(py_file)
        all_unused.extend(unused)

    return all_unused


def get_all_imported_modules(directory: str, exclude_dirs: Optional[list[str]] = None) -> set[str]:
    """Get all modules imported in a directory."""
    python_files = find_python_files(directory, exclude_dirs)
    imported_modules = set()

    for py_file in python_files:
        try:
            with open(py_file, "r", encoding="utf-8") as f:
                source = f.read()
        except (UnicodeDecodeError, OSError):
            continue

        try:
            tree = ast.parse(source, filename=py_file)
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    module = alias.name.split(".")[0]
                    imported_modules.add(module.lower())

            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module:
                    main_module = module.split(".")[0]
                    imported_modules.add(main_module.lower())

    return imported_modules


def find_unused_packages(
    requirements_files: list[str],
    pyproject_files: list[str],
    source_directories: list[str],
    exclude_packages: Optional[set[str]] = None,
) -> list[UnusedPackage]:
    """Find packages that are listed but not imported anywhere."""
    if exclude_packages is None:
        exclude_packages = set()

    all_packages = {}

    # Parse all requirements files
    for req_file in requirements_files:
        packages = parse_requirements_file(req_file)
        all_packages.update(packages)

    # Parse all pyproject.toml files
    for pyproject_file in pyproject_files:
        packages = parse_pyproject_dependencies(pyproject_file)
        all_packages.update(packages)

    # Get all imported modules from source directories
    all_imports = set()
    for source_dir in source_directories:
        imports = get_all_imported_modules(source_dir)
        all_imports.update(imports)

    # Find unused packages
    unused = []
    for pkg_name in all_packages:
        # Skip excluded packages
        if pkg_name in exclude_packages:
            continue

        # Check if the package is imported
        # Handle both underscore and hyphen variations
        pkg_variants = {pkg_name, pkg_name.replace("_", "-")}

        is_used = any(
            imp in pkg_variants
            or pkg_variants.intersection({imp.replace("_", "-"), imp.replace("-", "_")})
            for imp in all_imports
        )

        if not is_used:
            # Try to find which file defines this package
            source_file = None
            for req_file in requirements_files:
                if pkg_name in parse_requirements_file(req_file):
                    source_file = req_file
                    break

            if source_file is None:
                for py_file in pyproject_files:
                    if pkg_name in parse_pyproject_dependencies(py_file):
                        source_file = py_file
                        break

            unused.append(
                UnusedPackage(
                    package_name=pkg_name,
                    source_file=source_file or "unknown",
                    reason="No import found in source code",
                )
            )

    return unused


def analyze_dependencies(
    source_directories: list[str],
    requirements_files: Optional[list[str]] = None,
    pyproject_files: Optional[list[str]] = None,
    exclude_dirs: Optional[list[str]] = None,
    exclude_packages: Optional[set[str]] = None,
) -> DependencyReport:
    """
    Perform complete dependency analysis.

    Args:
        source_directories: List of directories to scan for Python source files
        requirements_files: List of requirements.txt files to check
        pyproject_files: List of pyproject.toml files to check
        exclude_dirs: Directories to exclude from scanning
        exclude_packages: Package names to exclude from unused check

    Returns:
        DependencyReport with all findings
    """
    if requirements_files is None:
        requirements_files = []

    if pyproject_files is None:
        pyproject_files = []

    if exclude_dirs is None:
        exclude_dirs = [
            "__pycache__",
            ".git",
            ".venv",
            "venv",
            "node_modules",
            ".pytest_cache",
            ".ruff_cache",
            "mutants",
            "tests",
        ]

    if exclude_packages is None:
        exclude_packages = {
            "pytest",
            "pytest-asyncio",
            "ruff",
            "black",
            "mypy",
            "types-python-dateutil",
            "types-pytz",
        }

    # Scan for unused imports
    all_unused_imports = []
    for directory in source_directories:
        unused = scan_directory_for_unused_imports(directory, exclude_dirs)
        all_unused_imports.extend(unused)

    # Find unused packages
    unused_packages = find_unused_packages(
        requirements_files, pyproject_files, source_directories, exclude_packages
    )

    # Count files scanned
    files_scanned = 0
    for directory in source_directories:
        files_scanned += len(find_python_files(directory, exclude_dirs))

    return DependencyReport(
        unused_imports=all_unused_imports,
        unused_packages=unused_packages,
        files_scanned=files_scanned,
        packages_scanned=len(
            set().union(*[parse_requirements_file(f) for f in requirements_files])
        ),
    )


def print_report(report: DependencyReport, verbose: bool = False) -> None:
    """Print a dependency analysis report."""
    print("\n" + "=" * 60)
    print("DEPENDENCY ANALYSIS REPORT")
    print("=" * 60)

    print(f"\nFiles scanned: {report.files_scanned}")
    print(f"Packages scanned: {report.packages_scanned}")

    if report.unused_imports:
        print(f"\n--- Unused Imports ({len(report.unused_imports)}) ---")
        # Group by file
        by_file: dict[str, list[UnusedImport]] = {}
        for imp in report.unused_imports:
            if imp.file_path not in by_file:
                by_file[imp.file_path] = []
            by_file[imp.file_path].append(imp)

        for file_path, imports in sorted(by_file.items()):
            print(f"\n{file_path}:")
            for imp in imports:
                print(f"  Line {imp.line_number}: {imp.import_statement}")
    else:
        print("\n--- Unused Imports: None found ---")

    if report.unused_packages:
        print(f"\n--- Unused Packages ({len(report.unused_packages)}) ---")
        for pkg in report.unused_packages:
            print(f"  {pkg.package_name} (from {pkg.source_file})")
    else:
        print("\n--- Unused Packages: None found ---")

    print("\n" + "=" * 60)


def main():
    """Main entry point for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Detect unused dependencies in Python projects")
    parser.add_argument(
        "--dir",
        "-d",
        action="append",
        help="Source directories to scan (can be specified multiple times)",
    )
    parser.add_argument(
        "--requirements", "-r", action="append", help="requirements.txt files to check"
    )
    parser.add_argument("--pyproject", "-p", action="append", help="pyproject.toml files to check")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose output")
    parser.add_argument("--output", "-o", help="Output file for report (JSON format)")

    args = parser.parse_args()

    # Default to current directory if no directories specified
    source_dirs = args.dir or ["."]

    # Auto-discover requirements files if not specified
    req_files = args.requirements or []
    pyproject_files = args.pyproject or []

    if not req_files:
        # Look for requirements.txt in source directories
        for source_dir in source_dirs:
            for root, _, files in os.walk(source_dir):
                for f in files:
                    if f == "requirements.txt":
                        req_files.append(os.path.join(root, f))

    if not pyproject_files:
        # Look for pyproject.toml
        for source_dir in source_dirs:
            for root, _, files in os.walk(source_dir):
                for f in files:
                    if f == "pyproject.toml":
                        pyproject_files.append(os.path.join(root, f))

    report = analyze_dependencies(
        source_directories=source_dirs,
        requirements_files=req_files,
        pyproject_files=pyproject_files,
    )

    print_report(report, args.verbose)

    # Output JSON if requested
    if args.output:
        import json

        report_dict = {
            "files_scanned": report.files_scanned,
            "packages_scanned": report.packages_scanned,
            "unused_imports": [
                {
                    "file": imp.file_path,
                    "line": imp.line_number,
                    "statement": imp.import_statement,
                    "names": imp.imported_names,
                }
                for imp in report.unused_imports
            ],
            "unused_packages": [
                {"package": pkg.package_name, "source": pkg.source_file, "reason": pkg.reason}
                for pkg in report.unused_packages
            ],
        }
        with open(args.output, "w") as f:
            json.dump(report_dict, f, indent=2)
        print(f"\nJSON report written to: {args.output}")

    # Exit with error code if there are findings
    if report.unused_imports or report.unused_packages:
        sys.exit(1)
    else:
        print("\n✓ No unused dependencies found!")
        sys.exit(0)


if __name__ == "__main__":
    main()
