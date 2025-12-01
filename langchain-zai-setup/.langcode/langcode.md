# Project Instructions for Z.AI + langchain-code Integration

## Project Overview
This project demonstrates the integration between langchain-code CLI tool and Z.AI's coding plan API.

## Configuration
We're using Z.AI's OpenAI-compatible endpoint to power langchain-code with GLM models:
- **GLM-4.6**: Best for complex reasoning and large-scale code generation
- **GLM-4.5**: Balanced performance for most coding tasks
- **GLM-4.5-air**: Fastest response for quick prototyping

## Setup Instructions
1. Copy `.env.example` to `.env`
2. Replace `your_zai_api_key_here` with your actual Z.AI API key
3. Run `langcode chat --llm openai --mode react`

## Available Commands
```bash
# Interactive chat with Z.AI models
langcode chat --llm openai --mode react

# Autopilot mode (hands-off planning and execution)
langcode chat --llm openai --mode deep --auto

# Feature implementation
langcode feature "Implement user authentication" --llm openai

# Bug fixing
langcode fix --llm openai

# Code analysis
langcode analyze --llm openai
```

## Best Practices
- Use `GLM-4.6` for complex features and architectural decisions
- Use `GLM-4.5-air` for quick fixes and simple tasks
- Set `OPENAI_TEMPERATURE=0.1` for more deterministic outputs
- Use project-specific instructions in this file for better context

## Model Selection Guide
- **Complex tasks**: `OPENAI_MODEL=GLM-4.6`
- **Speed prioritized**: `OPENAI_MODEL=GLM-4.5-air`
- **Balanced approach**: `OPENAI_MODEL=GLM-4.5`