# LangChain + Z.AI Coding Plan API Integration

This project demonstrates how to integrate [langchain-code](https://github.com/zamalali/langchain-code) with the [Z.AI Coding Plan API](https://docs.z.ai/devpack/tool/others).

## Features

- ✅ Custom LLM wrapper for Z.AI's GLM models (GLM-4.6, GLM-4.5, GLM-4.5-air)
- ✅ Feature implementation with contextual analysis
- ✅ Bug diagnosis and fixing with log analysis support
- ✅ Comprehensive code analysis (security, performance, best practices)
- ✅ Interactive coding sessions with memory
- ✅ Project-specific instruction support
- ✅ OpenAI-compatible API integration

## Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your Z.AI API key
   ```

3. **Get your Z.AI API key** from [Z.AI Console](https://docs.z.ai/devpack/tool/others)

## Usage

### Basic Usage

```python
from langchain_zai_integration import LangChainZAIIntegration

# Initialize with GLM-4.6 for complex tasks
integration = LangChainZAIIntegration(model="GLM-4.6")

# Implement a feature
result = integration.implement_feature(
    "Add user authentication with JWT",
    context="FastAPI application with SQLAlchemy"
)

# Fix a bug
fix = integration.fix_bug(
    "Memory leak in background processor",
    logs="Memory usage keeps increasing"
)

# Analyze code
analysis = integration.analyze_code(
    "path/to/code.py",
    analysis_type="security and performance"
)
```

### Interactive Session

```python
# Start an interactive coding session
integration.interactive_chat()
```

### With Project Instructions

Create `.langcode/langcode.md` with project-specific context:

```python
integration = LangChainZAIIntegration(
    model="GLM-4.6",
    project_instructions=".langcode/langcode.md"
)
```

## Available Models

- **GLM-4.6**: Best for complex reasoning and large-scale code generation
- **GLM-4.5**: Balanced performance for most coding tasks
- **GLM-4.5-air**: Fastest response for quick prototyping

## API Features

### Feature Implementation
- Requirement analysis
- Architecture suggestions
- Complete code solutions
- Documentation and comments

### Bug Fixing
- Root cause analysis
- Log interpretation
- Step-by-step fixes
- Prevention strategies

### Code Analysis
- Security vulnerabilities
- Performance bottlenecks
- Code quality metrics
- Best practices compliance

## Examples

Run the demo script to see all features in action:

```bash
python demo.py
```

## Configuration

### Environment Variables
```bash
ZAI_API_KEY=your_api_key_here
ZAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
LANGCHAIN_TRACING_V2=true  # Optional
```

### Project Instructions
Create `.langcode/langcode.md` for project-specific context that helps the AI provide more relevant responses.

## Architecture

```
LangChain + Z.AI Integration
├── ZAICodingLLM           # Custom LLM wrapper
├── LangChainZAIIntegration # Main integration class
├── ConversationChain       # For interactive sessions
└── Memory                 # Conversation context
```

## Error Handling

The integration includes comprehensive error handling:
- API rate limiting
- Network timeouts
- Invalid API responses
- Authentication failures

## Best Practices

1. **Choose the right model**: Use GLM-4.6 for complex tasks, GLM-4.5-air for quick responses
2. **Provide context**: More context leads to better results
3. **Use project instructions**: Helps maintain consistency across sessions
4. **Handle edge cases**: Always validate generated code before use
5. **Memory management**: Clear conversation memory for unrelated tasks

## Comparison with langchain-code

| Feature | langchain-code | This Integration |
|---------|----------------|------------------|
| LLM Support | Multiple | Z.AI GLM models |
| API Protocol | Various | OpenAI-compatible |
| Customization | Limited | Full control |
| Project Context | File-based | Configurable |
| Memory | Built-in | LangChain memory |
| Specialized Chains | Basic | Advanced |

## Contributing

Feel free to submit issues and enhancement requests!

## License

This integration is provided as example code. See individual package licenses for more details.