# AI Engine

The AI Engine is the core component of ModPorter AI responsible for intelligent mod conversion using a multi-agent system powered by CrewAI and enhanced with RAG (Retrieval Augmented Generation) capabilities.

## Architecture

The AI Engine consists of several specialized agents working together:

### Core Agents

1. **JavaAnalyzerAgent** - Analyzes Java mod code and structure
2. **BedrockArchitectAgent** - Designs Bedrock add-on architecture
3. **LogicTranslatorAgent** - Translates Java logic to Bedrock equivalents
4. **AssetConverterAgent** - Converts assets between formats
5. **PackagingAgent** - Packages the final Bedrock add-on
6. **QAValidatorAgent** - Validates the conversion quality

### RAG System

The RAG system enhances agent capabilities with:

- **Knowledge Retrieval**: Access to specialized Minecraft modding knowledge
- **Semantic Search**: Find relevant information from documentation
- **Embedding Generation**: Vector representation of mod content
- **Context-Aware Responses**: Grounded answers based on retrieved knowledge

## Quick Start

### Running Tests

```bash
# Run all tests
pytest

# Run RAG-specific tests
pytest tests/test_rag_crew.py tests/unit/test_embedding_generator.py tests/integration/test_rag_workflow.py

# Run with coverage
pytest --cov=src --cov-report=html
```

### RAG Evaluation

```bash
# Run RAG evaluation suite
python src/testing/rag_evaluator.py
```

### Code Quality Check

```bash
# Check code quality
python check_code_quality.py
```

## Configuration

### Environment Variables

```bash
# AI Configuration
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# LLM Provider Configuration
# For local testing with Ollama
USE_OLLAMA=true
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434  # Auto-detected if not set

# For Docker environments
DOCKER_ENVIRONMENT=true  # Changes default Ollama URL to http://ollama:11434

# RAG Configuration
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_SIMILARITY_THRESHOLD=0.7
RAG_MAX_RESULTS=10
```

### LLM Provider Setup

#### Option 1: Local Development with Ollama (Recommended)

1. **Install Ollama**: Download from [https://ollama.ai](https://ollama.ai)
2. **Pull the model**: `ollama pull llama3.2`
3. **Set environment variables**:
   ```bash
   export USE_OLLAMA=true
   export OLLAMA_MODEL=llama3.2
   # OLLAMA_BASE_URL will auto-detect to http://localhost:11434
   ```
4. **Run tests**: `python test_crew_ollama_fix.py`

#### Option 2: Docker Development

1. **Use docker-compose**: `docker-compose -f docker-compose.dev.yml up`
2. **Set environment variables**:
   ```bash
   export USE_OLLAMA=true
   export DOCKER_ENVIRONMENT=true
   export OLLAMA_MODEL=llama3.2
   # OLLAMA_BASE_URL will auto-detect to http://ollama:11434
   ```

#### Option 3: Production with OpenAI

1. **Set API key**: `export OPENAI_API_KEY=your_api_key`
2. **Don't set USE_OLLAMA** (defaults to OpenAI)
3. **Optional**: Set model with `export OPENAI_MODEL=gpt-4`

### Configuration Details

- **Base URL Auto-Detection**: The system automatically detects the correct Ollama base URL based on the environment
- **Model Compatibility**: Supports `llama3.2`, `codellama`, `mistral`, and other Ollama models
- **Fallback Handling**: If Ollama fails, the system provides clear error messages with setup instructions
- **Memory Management**: Ollama mode automatically disables CrewAI memory to avoid validation issues

### Agent Configuration

Agents are configured via `src/config/rag_agents.yaml`. See the full configuration example in the RAG documentation.

## Development

### Adding New Agents

1. Create agent class in `src/agents/`
2. Implement required methods (`get_tools`, `execute`, etc.)
3. Add configuration to `rag_agents.yaml`
4. Create unit tests in `tests/unit/`
5. Update integration tests if needed

### Adding New Tools

1. Create tool class in `src/tools/`
2. Follow the existing tool patterns
3. Add comprehensive tests
4. Update agent configurations to use the new tool

### Testing Guidelines

- All new code must have unit tests
- Integration tests for multi-agent workflows
- Performance tests for RAG operations
- Error handling and edge case testing

## Troubleshooting

### Common Issues

#### "Tool object is not callable" Error
- **Cause**: Calling tools directly instead of using `.run()` method
- **Solution**: Use `tool.run(parameters)` instead of `tool(parameters)`

#### "Ollama LLM initialization failed"
- **Cause**: Ollama not running or wrong base URL
- **Solution**: 
  1. Check if Ollama is running: `curl http://localhost:11434/api/tags`
  2. Verify model is available: `ollama list`
  3. Pull model if needed: `ollama pull llama3.2`

#### "LLM Failed" during Crew execution
- **Cause**: Timeout or connection issues with Ollama
- **Solution**: 
  1. Check Ollama logs: `ollama logs`
  2. Increase timeout: Set `request_timeout=300` in configuration
  3. Try smaller model: `export OLLAMA_MODEL=llama3.2:1b`

#### CrewAI Memory Validation Issues
- **Cause**: Memory validation conflicts with Ollama
- **Solution**: Automatic - memory is disabled when `USE_OLLAMA=true`

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
from src.crew.conversion_crew import ModPorterConversionCrew
crew = ModPorterConversionCrew()
"
```

### Testing Ollama Connection

```bash
# Test direct connection
python -c "
from langchain_ollama import ChatOllama
llm = ChatOllama(model='llama3.2', base_url='http://localhost:11434')
response = llm.invoke('Hello')
print(f'✅ Success: {response.content}')
"
```

## Documentation

- [RAG Testing Documentation](../docs/RAG_TESTING.md) - Comprehensive RAG testing guide
- [RAG System Overview](../RAG.md) - Detailed RAG implementation documentation
- [Project Documentation](../docs/project-docs.md) - General project information

## Support

For issues or questions about the AI Engine:

1. Check the test suite for examples
2. Review the RAG documentation
3. Check the main project documentation
4. Open an issue on the GitHub repository
