import pytest
import re

def test_regex():
    pattern = r'^[\w\-. ]+$'
    assert bool(re.match(pattern, "valid.jar")) == True
    assert bool(re.match(pattern, "valid_file-1.2.3.jar")) == True
    assert bool(re.match(pattern, "../invalid.jar")) == False
    assert bool(re.match(pattern, "/tmp/invalid.jar")) == False
    assert bool(re.match(pattern, "invalid/file.jar")) == False

test_regex()
print("Regex is working correctly")
