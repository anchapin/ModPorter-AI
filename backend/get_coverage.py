#!/usr/bin/env python3
"""Quick script to read coverage data"""
import json
from pathlib import Path

def main():
    coverage_file = Path("coverage.json")
    if not coverage_file.exists():
        print("coverage.json not found")
        return
    
    with open(coverage_file) as f:
        data = json.load(f)
    
    totals = data.get("totals", {})
    percent = totals.get("percent_covered", 0)
    covered = totals.get("covered_lines", 0)
    total = totals.get("num_statements", 0)
    
    print(f"Current Coverage: {percent:.1f}% ({covered}/{total} statements)")
    
    # Find service layer files
    files = data.get("files", {})
    service_files = {}
    
    for filename, file_data in files.items():
        if "services" in filename and "src/services" in filename:
            name = filename.split("src/services/")[-1]
            service_files[name] = {
                "percent": file_data["summary"]["percent_covered"],
                "covered": file_data["summary"]["covered_lines"],
                "total": file_data["summary"]["num_statements"]
            }
    
    print("\n=== Service Layer Coverage ===")
    for name, stats in sorted(service_files.items(), key=lambda x: x[1]["total"], reverse=True):
        print(f"{name}: {stats['percent']:.1f}% ({stats['covered']}/{stats['total']} statements)")

if __name__ == "__main__":
    main()
