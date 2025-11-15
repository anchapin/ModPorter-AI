#!/usr/bin/env python3
"""
Quick coverage check script for easy execution
"""

import os
import sys
import subprocess

def main():
    """Run coverage check with default settings."""
    project_root = os.path.dirname(os.path.abspath(__file__))

    print("🚀 Running ModPorter-AI Test Coverage Check")
    print("=" * 50)

    try:
        # Run the coverage monitor
        result = subprocess.run([
            sys.executable, "coverage_monitor.py",
            "--project-root", project_root,
            "--generate-dashboard",
            "--target-coverage", "80"
        ], cwd=project_root)

        if result.returncode == 0:
            print("\n✅ Coverage check completed successfully!")
            print("📊 Check the coverage_reports directory for detailed reports.")
        else:
            print("\n⚠️ Coverage check completed with issues to address.")

    except Exception as e:
        print(f"❌ Error running coverage check: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()