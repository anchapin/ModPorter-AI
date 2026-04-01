"""
Comprehensive pytest tests for utils/dependency_detector.py - Dependency Detector Module.
Coverage target: 80%+
"""

import pytest
import ast
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from utils.dependency_detector import (
    ImportVisitor,
    parse_requirements_file,
    parse_pyproject_dependencies,
    scan_python_file,
    find_python_files,
    scan_directory_for_unused_imports,
    get_all_imported_modules,
    find_unused_packages,
    analyze_dependencies,
    print_report,
    UnusedImport,
    UnusedPackage,
    DependencyReport,
)


class TestImportVisitor:
    """Test ImportVisitor AST visitor."""

    def test_visit_import(self):
        """Test visiting import statements."""
        source = """
import os
import sys
import json as json_module
"""
        visitor = ImportVisitor(source)
        tree = ast.parse(source)
        visitor.visit(tree)

        assert "os" in visitor.imports
        assert "sys" in visitor.imports
        assert "json_module" in visitor.imports

    def test_visit_import_from(self):
        """Test visiting from...import statements."""
        source = """
from os import path
from collections import OrderedDict, defaultdict
from typing import List, Dict
"""
        visitor = ImportVisitor(source)
        tree = ast.parse(source)
        visitor.visit(tree)

        assert "os" in visitor.imports
        assert "collections" in visitor.imports
        assert "typing" in visitor.imports

    def test_visit_wildcard_import_skipped(self):
        """Test that wildcard imports are skipped."""
        source = """
from os import *
"""
        visitor = ImportVisitor(source)
        tree = ast.parse(source)
        visitor.visit(tree)

        # Wildcard imports should not be tracked
        assert len(visitor.imports.get("os", [])) == 0

    def test_track_function_definitions(self):
        """Test tracking function definitions."""
        source = """
def my_function():
    pass

def another_function():
    pass
"""
        visitor = ImportVisitor(source)
        tree = ast.parse(source)
        visitor.visit(tree)

        assert "my_function" in visitor.defined_names
        assert "another_function" in visitor.defined_names

    def test_track_async_function_definitions(self):
        """Test tracking async function definitions."""
        source = """
async def async_function():
    pass
"""
        visitor = ImportVisitor(source)
        tree = ast.parse(source)
        visitor.visit(tree)

        assert "async_function" in visitor.defined_names

    def test_track_class_definitions(self):
        """Test tracking class definitions."""
        source = """
class MyClass:
    pass

class AnotherClass:
    pass
"""
        visitor = ImportVisitor(source)
        tree = ast.parse(source)
        visitor.visit(tree)

        assert "MyClass" in visitor.defined_names
        assert "AnotherClass" in visitor.defined_names

    def test_track_name_usage(self):
        """Test tracking name usage."""
        source = """
x = 5
y = x + 1
print(y)
"""
        visitor = ImportVisitor(source)
        tree = ast.parse(source)
        visitor.visit(tree)

        assert "x" in visitor.used_names
        assert "y" in visitor.used_names

    def test_track_attribute_access(self):
        """Test tracking attribute access."""
        source = """
import os
os.path.join()
os.path.exists()
"""
        visitor = ImportVisitor(source)
        tree = ast.parse(source)
        visitor.visit(tree)

        assert "path" in visitor.used_names
        assert "join" in visitor.used_names
        assert "exists" in visitor.used_names

    def test_get_unused_imports(self):
        """Test identifying unused imports."""
        source = """
import os
import sys
x = 5
"""
        visitor = ImportVisitor(source)
        tree = ast.parse(source)
        visitor.visit(tree)

        unused = visitor.get_unused_imports()
        assert len(unused) >= 1  # sys should be unused

    def test_get_unused_imports_all_used(self):
        """Test when all imports are used."""
        source = """
import os
os.path.join()
"""
        visitor = ImportVisitor(source)
        tree = ast.parse(source)
        visitor.visit(tree)

        unused = visitor.get_unused_imports()
        # os should be used because path is used
        assert all(u.imported_names[0] != "os" for u in unused)


class TestParseRequirementsFile:
    """Test requirements.txt parsing."""

    def test_parse_simple_requirements(self, tmp_path):
        """Test parsing simple requirements file."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("requests==2.28.0\nflask>=2.0\nnumpy\n")

        result = parse_requirements_file(str(req_file))

        assert "requests" in result
        assert "flask" in result
        assert "numpy" in result
        assert result["requests"] == "==2.28.0"

    def test_parse_requirements_with_comments(self, tmp_path):
        """Test parsing requirements with comments."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            "# This is a comment\nrequests==2.28.0\n# Another comment\nflask>=2.0\n"
        )

        result = parse_requirements_file(str(req_file))

        assert "requests" in result
        assert "flask" in result

    def test_parse_requirements_with_flags(self, tmp_path):
        """Test parsing requirements with pip flags."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text(
            "-e git+https://github.com/user/repo.git\n-r other.txt\nrequests==2.28.0\n"
        )

        result = parse_requirements_file(str(req_file))

        assert "requests" in result
        assert "-e" not in result
        assert "-r" not in result

    def test_parse_non_existent_file(self):
        """Test parsing non-existent file."""
        result = parse_requirements_file("/non/existent/path/requirements.txt")
        assert result == {}

    def test_parse_requirements_hyphen_underscore(self, tmp_path):
        """Test parsing package names with hyphens."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("django-rest-framework==1.0.0\n")

        result = parse_requirements_file(str(req_file))

        assert "django_rest_framework" in result


class TestParsePyprojectDependencies:
    """Test pyproject.toml parsing."""

    def test_parse_simple_dependencies(self, tmp_path):
        """Test parsing simple dependencies."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project]
dependencies = [
    "requests>=2.28.0",
    "flask>=2.0",
]
""")

        result = parse_pyproject_dependencies(str(pyproject))

        assert "requests" in result
        assert "flask" in result

    def test_parse_dependencies_with_quotes(self, tmp_path):
        """Test parsing dependencies with various quote styles."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
dependencies = [
    "requests>=2.28.0",
    'flask>=2.0',
]
""")

        result = parse_pyproject_dependencies(str(pyproject))

        assert "requests" in result
        assert "flask" in result

    def test_parse_non_existent_file(self):
        """Test parsing non-existent file."""
        result = parse_pyproject_dependencies("/non/existent/pyproject.toml")
        assert result == {}


class TestScanPythonFile:
    """Test Python file scanning."""

    def test_scan_valid_file(self, tmp_path):
        """Test scanning a valid Python file."""
        py_file = tmp_path / "test.py"
        py_file.write_text("""
import os
import sys

def main():
    os.path.join("a", "b")
""")

        unused = scan_python_file(str(py_file))
        assert len(unused) >= 1  # sys should be unused

    def test_scan_file_with_syntax_error(self, tmp_path):
        """Test scanning file with syntax error."""
        py_file = tmp_path / "test.py"
        py_file.write_text("""
def main(
    pass
""")

        unused = scan_python_file(str(py_file))
        assert unused == []

    def test_scan_nonexistent_file(self):
        """Test scanning non-existent file."""
        unused = scan_python_file("/non/existent/file.py")
        assert unused == []

    def test_scan_binary_file(self, tmp_path):
        """Test scanning binary file."""
        py_file = tmp_path / "test.py"
        py_file.write_bytes(b"\x00\x01\x02\x03")

        unused = scan_python_file(str(py_file))
        assert unused == []


class TestFindPythonFiles:
    """Test Python file discovery."""

    def test_find_python_files(self, tmp_path):
        """Test finding Python files."""
        # Create test structure
        (tmp_path / "file1.py").write_text("# test")
        (tmp_path / "file2.py").write_text("# test")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "file3.py").write_text("# test")

        files = find_python_files(str(tmp_path))

        assert len(files) >= 3

    def test_exclude_pycache(self, tmp_path):
        """Test excluding __pycache__ directories."""
        (tmp_path / "main.py").write_text("# test")
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "__pycache__" / "cached.pyc").write_bytes(b"cached")

        files = find_python_files(str(tmp_path))

        assert not any("__pycache__" in f for f in files)

    def test_exclude_git(self, tmp_path):
        """Test excluding .git directories."""
        (tmp_path / "main.py").write_text("# test")
        (tmp_path / ".git").mkdir()
        (tmp_path / ".git" / "config").write_text("git config")

        files = find_python_files(str(tmp_path))

        assert not any(".git" in f for f in files)

    def test_custom_exclude_dirs(self, tmp_path):
        """Test custom exclude directories."""
        (tmp_path / "main.py").write_text("# test")
        (tmp_path / "exclude_me").mkdir()
        (tmp_path / "exclude_me" / "file.py").write_text("# test")

        files = find_python_files(str(tmp_path), exclude_dirs=["exclude_me"])

        assert not any("exclude_me" in f for f in files)


class TestScanDirectoryForUnusedImports:
    """Test directory scanning for unused imports."""

    def test_scan_directory(self, tmp_path):
        """Test scanning a directory."""
        (tmp_path / "file1.py").write_text("""
import os
import sys

def main():
    os.path.join("a", "b")
""")

        unused = scan_directory_for_unused_imports(str(tmp_path))
        assert len(unused) >= 1

    def test_scan_directory_with_subdirs(self, tmp_path):
        """Test scanning with subdirectories."""
        (tmp_path / "main.py").write_text("import os")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "module.py").write_text("import sys")

        unused = scan_directory_for_unused_imports(str(tmp_path))
        assert isinstance(unused, list)


class TestGetAllImportedModules:
    """Test getting all imported modules."""

    def test_get_imported_modules(self, tmp_path):
        """Test getting imported modules."""
        (tmp_path / "file.py").write_text("""
import os
import sys
from collections import defaultdict
from typing import List
""")

        modules = get_all_imported_modules(str(tmp_path))

        assert "os" in modules
        assert "sys" in modules
        assert "collections" in modules
        assert "typing" in modules

    def test_get_imported_modules_empty_dir(self, tmp_path):
        """Test with empty directory."""
        modules = get_all_imported_modules(str(tmp_path))
        assert modules == set()


class TestFindUnusedPackages:
    """Test finding unused packages."""

    def test_find_unused_packages(self, tmp_path):
        """Test finding unused packages."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("unused_pkg==1.0.0\n")

        result = find_unused_packages(
            requirements_files=[str(req_file)],
            pyproject_files=[],
            source_directories=[str(tmp_path)],
        )

        assert len(result) >= 1
        assert any(p.package_name == "unused_pkg" for p in result)

    def test_find_used_packages(self, tmp_path):
        """Test finding used packages."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("os==1.0.0\n")  # os is used in Python

        (tmp_path / "file.py").write_text("import os\nos.path.join()")

        result = find_unused_packages(
            requirements_files=[str(req_file)],
            pyproject_files=[],
            source_directories=[str(tmp_path)],
        )

        # os should not be in unused
        assert not any(p.package_name == "os" for p in result)

    def test_exclude_packages(self, tmp_path):
        """Test excluding packages from check."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("pytest==7.0.0\n")

        result = find_unused_packages(
            requirements_files=[str(req_file)],
            pyproject_files=[],
            source_directories=[str(tmp_path)],
            exclude_packages={"pytest"},
        )

        assert not any(p.package_name == "pytest" for p in result)


class TestAnalyzeDependencies:
    """Test full dependency analysis."""

    def test_analyze_dependencies(self, tmp_path):
        """Test full dependency analysis."""
        # Create test files
        (tmp_path / "main.py").write_text("""
import os
import unused_module

def main():
    os.path.join("a", "b")
""")

        req_file = tmp_path / "requirements.txt"
        req_file.write_text("unused_module==1.0.0\n")

        report = analyze_dependencies(
            source_directories=[str(tmp_path)],
            requirements_files=[str(req_file)],
        )

        assert isinstance(report, DependencyReport)
        assert report.files_scanned >= 1

    def test_analyze_dependencies_empty_dirs(self):
        """Test analysis with empty directories."""
        report = analyze_dependencies(
            source_directories=["/non/existent/dir"],
        )

        assert report.files_scanned == 0
        assert report.packages_scanned == 0


class TestPrintReport:
    """Test report printing."""

    def test_print_report_empty(self):
        """Test printing empty report."""
        report = DependencyReport()
        # Should not raise
        print_report(report)

    def test_print_report_with_findings(self):
        """Test printing report with findings."""
        report = DependencyReport(
            unused_imports=[
                UnusedImport(
                    file_path="test.py",
                    line_number=1,
                    import_statement="import sys",
                    imported_names=["sys"],
                ),
            ],
            unused_packages=[
                UnusedPackage(
                    package_name="unused",
                    source_file="requirements.txt",
                ),
            ],
        )
        # Should not raise
        print_report(report, verbose=True)


class TestEdgeCases:
    """Test edge cases."""

    def test_parse_requirements_special_chars(self, tmp_path):
        """Test parsing requirements with special characters."""
        req_file = tmp_path / "requirements.txt"
        req_file.write_text("package==1.0.0; python_version<'3.8'\n")

        result = parse_requirements_file(str(req_file))
        assert "package" in result

    def test_parse_pyproject_complex_deps(self, tmp_path):
        """Test parsing complex dependencies."""
        pyproject = tmp_path / "pyproject.toml"
        pyproject.write_text("""
[project.optional-dependencies]
dev = [
    "pytest>=7.0",
    "black>=22.0",
]
""")

        result = parse_pyproject_dependencies(str(pyproject))
        # Should handle optional dependencies
        assert isinstance(result, dict)

    def test_scan_file_with_encoding(self, tmp_path):
        """Test scanning file with different encoding."""
        py_file = tmp_path / "test.py"
        py_file.write_text("# -*- coding: utf-8 -*-\nimport os\n", encoding="utf-8")

        unused = scan_python_file(str(py_file))
        assert isinstance(unused, list)

    def test_get_imports_with_relative_imports(self, tmp_path):
        """Test handling relative imports."""
        (tmp_path / "file.py").write_text("from . import module\nfrom .module import func\n")

        modules = get_all_imported_modules(str(tmp_path))
        # Relative imports should be handled
        assert isinstance(modules, set)
