
import os

def find_missing_tests():
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.join(current_dir, "backend/src/api")
    tests_dir = os.path.join(current_dir, "backend/tests")

    api_files = [f for f in os.listdir(api_dir) if f.endswith(".py") and f != "__init__.py"]
    test_files = os.listdir(tests_dir)

    missing_tests = []

    for api_file in api_files:
        expected_test_file = f"test_{api_file}"
        if expected_test_file not in test_files:
            missing_tests.append(api_file)

    if missing_tests:
        print("API files with missing tests:")
        for file in missing_tests:
            print(file)
    else:
        print("All API files have corresponding test files.")

if __name__ == "__main__":
    find_missing_tests()
