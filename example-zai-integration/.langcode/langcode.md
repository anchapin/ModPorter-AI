# Project Instructions for LangChain + Z.AI Integration

## Project Overview
This project demonstrates the integration between langchain-code and Z.AI Coding Plan API.

## Architecture
- **LLM**: Z.AI GLM models (GLM-4.6, GLM-4.5, GLM-4.5-air)
- **Framework**: LangChain for orchestration
- **API**: Z.AI Coding Plan API with OpenAI-compatible protocol

## Integration Features
1. **Custom LLM Wrapper**: Python class to interface with Z.AI API
2. **Task Specialization**: Different chains for feature implementation, bug fixing, and code analysis
3. **Memory Management**: Conversation buffer for context retention
4. **Interactive Mode**: Real-time coding assistance

## Usage Patterns
- Feature implementation with contextual analysis
- Bug diagnosis and fixing with log analysis
- Code review and optimization suggestions
- Interactive coding sessions

## Best Practices
- Use GLM-4.6 for complex tasks requiring deep reasoning
- Use GLM-4.5-air for rapid prototyping and simpler tasks
- Always provide sufficient context for better results
- Leverage the conversation memory for multi-turn interactions