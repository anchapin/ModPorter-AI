"""Tests for dependency detection utilities."""

import os
import tempfile
from pathlib import Path

import pytest

from src.utils.dependency_detector import (
    DependencyReport,
    ImportVisitor,
    UnusedImport,
    UnusedPackage,
    analyze_dependencies,
    find_python_files,
    find_unused_packages,
    get_all_imported_modules,
    parse_pyproject_dependencies,
    parse_requirements_file,
    scan_directory_for_unused_imports,
    scan_python_file,
)


class TestParseRequirementsFile:
    """Tests for requirements file parsing."""

    def test_parse_simple_requirements(self):
        """Test parsing a simple requirements.txt file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("requests==2.28.0\n")
            f.write("flask>=2.0.0\n")
            f.write("# This is a comment\n")
            f.write("numpy\n")
            temp_file = f.name

        try:
            packages = parse_requirements_file(temp_file)
            assert "requests" in packages
            assert packages["requests"] == "==2.28.0"
            assert "flask" in packages
            assert "numpy" in packages
        finally:
            os.unlink(temp_file)

    def test_parse_empty_requirements(self):
        """Test parsing an empty requirements file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            temp_file = f.name

        try:
            packages = parse_requirements_file(temp_file)
            assert packages == {}
        finally:
            os.unlink(temp_file)

    def test_parse_nonexistent_file(self):
        """Test parsing a file that doesn't exist."""
        packages = parse_requirements_file("/nonexistent/file.txt")
        assert packages == {}


class TestParsePyprojectDependencies:
    """Tests for pyproject.toml parsing."""

    def test_parse_simple_pyproject(self):
        """Test parsing a simple pyproject.toml."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            f.write("""
[project]
name = "test"
version = "0.1.0"
dependencies = [
    "requests>=2.28.0",
    "flask>=2.0.0",
]
""")
            temp_file = f.name

        try:
            packages = parse_pyproject_dependencies(temp_file)
            assert "requests" in packages
            assert "flask" in packages
        finally:
            os.unlink(temp_file)


class TestFindPythonFiles:
    """Tests for finding Python files."""

    def test_find_python_files_basic(self):
        """Test finding Python files in a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            Path(tmpdir, "test1.py").write_text("print('hello')")
            Path(tmpdir, "test2.py").write_text("print('world')")
            Path(tmpdir, "README.md").write_text("# Readme")

            # Create subdirectory
            subdir = Path(tmpdir, "subdir")
            subdir.mkdir()
            Path(subdir, "test3.py").write_text("print('subdir')")

            files = find_python_files(tmpdir)
            assert len(files) == 3
            assert any("test1.py" in f for f in files)
            assert any("test2.py" in f for f in files)
            assert any("test3.py" in f for f in files)

    def test_exclude_dirs(self):
        """Test excluding directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files in normal directory
            Path(tmpdir, "test.py").write_text("print('hello')")

            # Create __pycache__ directory
            pycache = Path(tmpdir, "__pycache__")
            pycache.mkdir()
            Path(pycache, "test.pyc").write_text("")

            files = find_python_files(tmpdir, exclude_dirs=["__pycache__"])
            assert len(files) == 1


class TestScanPythonFile:
    """Tests for scanning individual Python files."""

    def test_scan_file_with_unused_import(self):
        """Test scanning a file with unused imports."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
import os
import sys

def hello():
    return "hello"
""")
            temp_file = f.name

        try:
            unused = scan_python_file(temp_file)
            # os and sys are unused
            assert len(unused) >= 1
        finally:
            os.unlink(temp_file)

    def test_scan_file_with_used_import(self):
        """Test scanning a file with used imports."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("""
import os

def hello():
    return os.getcwd()
""")
            temp_file = f.name

        try:
            unused = scan_python_file(temp_file)
            # os is used, so should not be in unused
            unused_names = [name for imp in unused for name in imp.imported_names]
            assert "os" not in unused_names
        finally:
            os.unlink(temp_file)


class TestGetAllImportedModules:
    """Tests for getting all imported modules."""

    def test_get_imported_modules(self):
        """Test getting all imported modules from a directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "test1.py").write_text("import os\nimport sys\n")
            Path(tmpdir, "test2.py").write_text(
                "import json\nfrom pathlib import Path\n"
            )

            imports = get_all_imported_modules(tmpdir)
            assert "os" in imports
            assert "sys" in imports
            assert "json" in imports
            assert "pathlib" in imports


class TestFindUnusedPackages:
    """Tests for finding unused packages."""

    def test_find_truly_unused_packages(self):
        """Test finding packages that are truly unused."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create requirements file
            req_file = Path(tmpdir, "requirements.txt")
            req_file.write_text("unused_pkg\n")

            # Create source file that imports something else
            src_dir = Path(tmpdir, "src")
            src_dir.mkdir()
            Path(src_dir, "main.py").write_text("import os\n")

            unused = find_unused_packages(
                requirements_files=[str(req_file)],
                pyproject_files=[],
                source_directories=[str(src_dir)],
                exclude_packages=set(),
            )

            assert len(unused) == 1
            assert unused[0].package_name == "unused_pkg"


class TestAnalyzeDependencies:
    """Tests for the main analyze_dependencies function."""

    def test_analyze_dependencies_basic(self):
        """Test basic dependency analysis."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create requirements file
            req_file = Path(tmpdir, "requirements.txt")
            req_file.write_text("used_package\nunused_package\n")

            # Create source directory
            src_dir = Path(tmpdir, "src")
            src_dir.mkdir()
            Path(src_dir, "main.py").write_text(
                "import os\nfrom used_package import something\n"
            )

            report = analyze_dependencies(
                source_directories=[str(src_dir)],
                requirements_files=[str(req_file)],
                exclude_packages={"pytest", "ruff"},
            )

            assert report.files_scanned >= 1
            assert "unused_package" in [p.package_name for p in report.unused_packages]


class TestDependencyReport:
    """Tests for DependencyReport dataclass."""

    def test_empty_report(self):
        """Test creating an empty report."""
        report = DependencyReport()
        assert report.unused_imports == []
        assert report.unused_packages == []
        assert report.files_scanned == 0

    def test_report_with_data(self):
        """Test creating a report with data."""
        unused_import = UnusedImport(
            file_path="/test.py",
            line_number=5,
            import_statement="import os",
            imported_names=["os"],
        )
        unused_package = UnusedPackage(
            package_name="unused", source_file="/requirements.txt"
        )

        report = DependencyReport(
            unused_imports=[unused_import],
            unused_packages=[unused_package],
            files_scanned=10,
            packages_scanned=5,
        )

        assert len(report.unused_imports) == 1
        assert len(report.unused_packages) == 1
        assert report.files_scanned == 10
