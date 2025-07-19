import pytest

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    return {}

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client."""
    return {}

@pytest.fixture
def mock_crew_ai():
    """Mock Crew AI."""
    return {}

@pytest.fixture
def sample_java_mod():
    """Sample Java mod."""
    return "sample_java_mod"

@pytest.fixture
def expected_bedrock_output():
    """Expected Bedrock output."""
    return "expected_bedrock_output"


