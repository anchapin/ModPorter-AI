
import json

def analyze_coverage(coverage_file="coverage.json"):
    """
    Analyzes a JSON coverage report and prints a sorted list of files by coverage.

    Args:
        coverage_file (str): The path to the coverage JSON file.
    """
    try:
        with open(coverage_file, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Coverage file not found at {coverage_file}")
        return
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {coverage_file}")
        return

    file_coverage = []
    for filename, file_data in data.get("files", {}).items():
        summary = file_data.get("summary", {})
        percent_covered = summary.get("percent_covered", 0)
        file_coverage.append((filename, percent_covered))

    # Sort by percentage, ascending
    file_coverage.sort(key=lambda x: x[1])

    print("File Coverage Report (Lowest First):")
    for filename, percent in file_coverage:
        print(f"{filename}: {percent:.2f}%")

if __name__ == "__main__":
    analyze_coverage()
