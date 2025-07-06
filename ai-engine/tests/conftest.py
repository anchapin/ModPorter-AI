import pytest
import os
from unittest.mock import MagicMock
from httpx import AsyncClient















# Set test environment variables
os.environ["OPENAI_API_KEY"] = "test-key"
os.environ["ANTHROPIC_API_KEY"] = "test-key"
os.environ["MOCK_AI_RESPONSES"] = "true"

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client for testing."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Mocked AI response"
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client

@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for testing."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock()]
    mock_response.content[0].text = "Mocked Anthropic response"
    mock_client.messages.create.return_value = mock_response
    return mock_client

@pytest.fixture
async def async_http_client():
    """Create an async HTTP client for testing."""
    async with AsyncClient() as client:
        yield client

@pytest.fixture
def sample_java_mod():
    """Sample Java mod structure for testing."""
    return {
        "mod_info": {
            "name": "TestMod",
            "version": "1.0.0",
            "minecraft_version": "1.19.2",
            "mod_loader": "forge"
        },
        "files": {
            "main.java": """
                public class TestMod {
                    public static final String MOD_ID = "testmod";
                    
                    public void init() {
                        System.out.println("TestMod initialized");
                    }
                }
            """,
            "items.json": """
                {
                    "test_item": {
                        "type": "item",
                        "name": "Test Item",
                        "texture": "test_item.png"
                    }
                }
            """
        }
    }

@pytest.fixture
def expected_bedrock_output():
    """Expected Bedrock addon structure."""
    return {
        "manifest.json": {
            "format_version": 2,
            "header": {
                "name": "TestMod",
                "description": "Converted from Java mod",
                "uuid": "test-uuid",
                "version": [1, 0, 0],
                "min_engine_version": [1, 20, 0]
            },
            "modules": [
                {
                    "type": "data",
                    "uuid": "test-module-uuid",
                    "version": [1, 0, 0]
                }
            ]
        },
        "items": {
            "test_item.json": {
                "format_version": "1.20.0",
                "minecraft:item": {
                    "description": {
                        "identifier": "testmod:test_item",
                        "category": "items"
                    },
                    "components": {
                        "minecraft:icon": "test_item"
                    }
                }
            }
        }
    }

@pytest.fixture
def mock_crew_ai():
    """Mock CrewAI for testing."""
    mock_crew = MagicMock()
    mock_crew.kickoff.return_value = {
        "status": "completed",
        "result": "Conversion completed successfully",
        "output_files": ["converted_addon.mcaddon"]
    }
    return mock_crew

@pytest.fixture
def conversion_job_data():
    """Sample conversion job data."""
    return {
        "job_id": "test_job_123",
        "input_file": "test_mod.jar",
        "status": "processing",
        "progress": 0,
        "created_at": "2024-01-01T00:00:00Z",
        "options": {
            "target_version": "1.20.0",
            "enable_smart_assumptions": True,
            "preserve_functionality": True
        }
    }