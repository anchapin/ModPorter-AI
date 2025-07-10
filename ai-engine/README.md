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

# RAG Configuration
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_SIMILARITY_THRESHOLD=0.7
RAG_MAX_RESULTS=10
```

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
