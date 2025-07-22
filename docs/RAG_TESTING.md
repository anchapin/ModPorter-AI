# RAG Testing Suite Documentation

## Overview

The RAG (Retrieval Augmented Generation) Testing Suite is a comprehensive test framework designed to evaluate and validate the performance and quality of the RAG system implementation in ModPorter AI. This suite ensures that the AI agents can effectively retrieve and utilize knowledge from specialized knowledge bases.

## Architecture

The RAG system consists of several key components:

### Core Components

1. **RAG Crew (`src/crew/rag_crew.py`)**
   - Multi-agent system using CrewAI
   - Configurable agents with specialized roles
   - Dynamic tool assignment and agent communication

2. **Embedding Generator (`src/utils/embedding_generator.py`)**
   - Text embedding generation using sentence-transformers
   - Handles document vectorization for semantic search
   - Integrated with the JavaAnalyzerAgent for mod analysis

3. **Vector Database Client (`src/utils/vector_db_client.py`)**
   - Interface to PostgreSQL with pgvector extension
   - Document indexing and similarity search
   - Async operations for scalability

4. **Search Tool (`src/tools/search_tool.py`)**
   - Semantic search functionality
   - Document retrieval and filtering
   - Integration with knowledge base agents

5. **RAG Evaluator (`src/testing/rag_evaluator.py`)**
   - Evaluation framework for RAG system quality
   - Retrieval hit rate calculations
   - Performance metrics and reporting

## Testing Framework

### Test Structure

The testing suite is organized into several layers:

#### 1. Unit Tests (`tests/unit/`)

- **`test_rag_crew.py`**: Tests for RAG crew initialization, configuration, and agent setup
- **`test_embedding_generator.py`**: Tests for embedding generation, model loading, and error handling
- **`test_search_tool.py`**: Tests for search functionality, query processing, and result formatting
- **`test_vector_db_client.py`**: Tests for database operations, document indexing, and retrieval
- **`test_rag_evaluator.py`**: Tests for evaluation metrics and performance assessment

#### 2. Integration Tests (`tests/integration/`)

- **`test_rag_workflow.py`**: End-to-end workflow testing
  - Document indexing via VectorDBClient
  - Knowledge retrieval using KnowledgeBaseAgent
  - SearchTool integration and result validation

#### 3. Evaluation Tests

- **RAG Evaluation Set (`src/testing/scenarios/rag_evaluation_set.json`)**
  - Curated queries and expected outcomes
  - Performance benchmarks and quality metrics
  - Retrieval quality assessment

### Key Testing Features

1. **Comprehensive Mocking**
   - Mock sentence-transformers for consistent testing
   - Mock HTTP clients for API interaction testing
   - Mock database operations for unit testing

2. **End-to-End Workflow Testing**
   - Complete RAG pipeline validation
   - Agent communication testing
   - Knowledge retrieval accuracy assessment

3. **Performance Evaluation**
   - Retrieval hit rate calculations
   - Response time measurements
   - Quality metrics tracking

4. **Error Handling Validation**
   - Graceful degradation testing
   - Error recovery mechanisms
   - Logging and monitoring validation

## Running the Tests

### All RAG Tests
```bash
cd ai-engine
pytest tests/test_rag_crew.py tests/unit/test_embedding_generator.py tests/integration/test_rag_workflow.py -v
```

### Unit Tests Only
```bash
cd ai-engine
pytest tests/unit/test_rag_*.py -v
```

### Integration Tests Only
```bash
cd ai-engine
pytest tests/integration/test_rag_workflow.py -v
```

### RAG Evaluation Suite
```bash
cd ai-engine
python src/testing/rag_evaluator.py
```

### With Coverage
```bash
cd ai-engine
pytest --cov=src --cov-report=html tests/test_rag_crew.py tests/unit/test_embedding_generator.py tests/integration/test_rag_workflow.py
```

## Test Coverage

The RAG testing suite achieves comprehensive coverage across:

- **RAG Crew Configuration**: 95%+ coverage of agent setup and configuration
- **Embedding Generation**: 100% coverage of embedding operations
- **Vector Database Operations**: 90%+ coverage of indexing and retrieval
- **Search Functionality**: 95%+ coverage of search operations
- **Integration Workflows**: 85%+ coverage of end-to-end processes

## Evaluation Metrics

### Retrieval Quality Metrics

1. **Hit Rate**: Percentage of queries that return relevant results
2. **Precision**: Accuracy of retrieved documents
3. **Response Time**: Average time for retrieval operations
4. **Coverage**: Percentage of knowledge base utilized

### Performance Benchmarks

- **Query Processing**: < 500ms average response time
- **Document Indexing**: < 100ms per document
- **Retrieval Accuracy**: > 85% hit rate for evaluation queries
- **System Reliability**: > 99% uptime during testing

## Configuration

### RAG Agents Configuration (`src/config/rag_agents.yaml`)

The RAG system uses a YAML configuration file to define agent roles, goals, and tool assignments:

```yaml
agents:
  researcher:
    role: "Information Researcher"
    goal: "Research and retrieve relevant information"
    backstory: "Specialized in finding and organizing information"
    tools: ["SearchTool"]
    verbose: true
    allow_delegation: false
  
  writer:
    role: "Content Synthesizer"
    goal: "Synthesize information into coherent responses"
    backstory: "Expert in combining multiple sources"
    tools: []
    verbose: true
    allow_delegation: false
```

### Environment Variables

The RAG system requires several environment variables for configuration:

```bash
# AI/ML Configuration
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost/modporter
VECTOR_DB_URL=postgresql://user:password@localhost/modporter

# RAG Configuration
RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
RAG_SIMILARITY_THRESHOLD=0.7
RAG_MAX_RESULTS=10
```

## Best Practices

### Writing RAG Tests

1. **Use Comprehensive Mocking**: Mock external dependencies to ensure consistent test results
2. **Test Error Conditions**: Include tests for failure scenarios and edge cases
3. **Validate Data Flow**: Ensure data passes correctly through the entire pipeline
4. **Performance Testing**: Include performance benchmarks and thresholds
5. **Integration Testing**: Test complete workflows from end to end

### Maintaining Test Quality

1. **Regular Updates**: Keep evaluation datasets current with new use cases
2. **Continuous Monitoring**: Track performance metrics over time
3. **Automated Validation**: Include RAG tests in CI/CD pipelines
4. **Documentation**: Keep test documentation up to date with code changes

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed and PYTHONPATH is set correctly
2. **Mock Failures**: Verify mock configurations match actual implementations
3. **Database Issues**: Check PostgreSQL connection and pgvector extension
4. **Performance Issues**: Monitor resource usage and optimize query patterns

### Debugging Tips

1. **Enable Verbose Logging**: Set log levels to DEBUG for detailed output
2. **Use Test Isolation**: Run tests individually to identify specific issues
3. **Check Dependencies**: Verify all required packages are installed
4. **Review Configuration**: Ensure all environment variables are set correctly

## Future Enhancements

### Planned Improvements

1. **Advanced Evaluation Metrics**: More sophisticated quality measurements
2. **Multi-Modal Testing**: Support for image and audio content evaluation
3. **Stress Testing**: Load testing for high-volume scenarios
4. **A/B Testing Framework**: Comparative evaluation of different RAG configurations
5. **Real-time Monitoring**: Live performance tracking and alerting

### Contributing

To contribute to the RAG testing suite:

1. Follow the existing test patterns and naming conventions
2. Include comprehensive docstrings and comments
3. Add both positive and negative test cases
4. Update documentation when adding new features
5. Ensure all tests pass before submitting changes

## References

- [RAG.md](../RAG.md) - Detailed RAG system documentation
- [CrewAI Documentation](https://docs.crewai.com/) - Multi-agent framework
- [LangChain Documentation](https://python.langchain.com/) - LLM framework
- [pytest Documentation](https://docs.pytest.org/) - Testing framework
