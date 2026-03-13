import re

filepath = 'backend/tests/conftest.py'
with open(filepath, 'r') as f:
    content = f.read()

content = content.replace('@pytest.fixture(scope="function")\nasync def db_session', '@pytest.fixture()\nasync def db_session')
content = content.replace('@pytest.fixture(scope="function")\nasync def async_test_db', '@pytest.fixture()\nasync def async_test_db')
content = content.replace('@pytest.fixture(scope="function")\nasync def async_client', '@pytest.fixture()\nasync def async_client')

with open(filepath, 'w') as f:
    f.write(content)

print("Fixed backend/tests/conftest.py.")
