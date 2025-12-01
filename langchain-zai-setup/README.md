# Use langchain-code CLI with Z.AI Coding Plan API

This guide shows how to configure the **langchain-code** CLI tool to use **Z.AI's** GLM models through their OpenAI-compatible API.

## 🎯 What You Get

- ✅ Full langchain-code CLI functionality powered by Z.AI GLM models
- ✅ Feature implementation, bug fixing, code analysis, and interactive chat
- ✅ Multiple GLM models: GLM-4.6, GLM-4.5, GLM-4.5-air
- ✅ ReAct and Deep reasoning modes
- ✅ Project-specific instructions support

## 🚀 Quick Setup

### 1. Install langchain-code
```bash
pip install langchain-code
```

### 2. Get Z.AI API Key
Visit [Z.AI Developer Documentation](https://docs.z.ai/devpack/tool/others) to get your API key.

### 3. Configure Environment

#### Option A: Automatic Setup (Recommended)
```bash
# Windows
setup_zai_for_langchain_code.bat

# Linux/Mac
bash setup_zai_for_langchain_code.sh
```

#### Option B: Manual Setup
1. Copy `.env.example` to `.env`
2. Edit `.env` and replace `your_zai_api_key_here` with your actual Z.AI API key:

```env
# OpenAI Configuration (redirected to Z.AI)
OPENAI_API_KEY=your_actual_zai_api_key_here
OPENAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
OPENAI_MODEL=GLM-4.6
OPENAI_TEMPERATURE=0.1
```

## 🎮 Usage

### Interactive Chat
```bash
langcode chat --llm openai --mode react
```

### Autopilot Mode (Hands-off)
```bash
langcode chat --llm openai --mode deep --auto
```

### Feature Implementation
```bash
langcode feature "Implement user authentication with JWT" --llm openai
```

### Bug Fixing
```bash
langcode fix --llm openai
```

### Code Analysis
```bash
langcode analyze --llm openai
```

### Quick Commands
```bash
langcode "tell me about this codebase"      # Quick analysis
langcode fix this                           # Quick fix (reads TTY logs)
```

## 🎛️ Model Selection

Choose the right GLM model for your needs:

| Model | Best For | Performance |
|-------|----------|-------------|
| **GLM-4.6** | Complex tasks, large-scale features | Highest quality |
| **GLM-4.5** | General coding tasks | Balanced |
| **GLM-4.5-air** | Quick fixes, prototyping | Fastest |

Set the model in your `.env` file:
```env
OPENAI_MODEL=GLM-4.6      # For complex tasks
OPENAI_MODEL=GLM-4.5-air  # For speed
```

## 🔧 Advanced Configuration

### Reasoning Modes

#### ReAct Mode (Default)
- Classic reasoning + acting
- Tool-based approach
- Good for most tasks

#### Deep Mode
- Multi-step planning
- LangGraph-style reasoning
- Better for complex projects

```bash
# ReAct Mode
langcode chat --llm openai --mode react

# Deep Mode with Autopilot
langcode chat --llm openai --mode deep --auto
```

### Project Instructions
Create `.langcode/langcode.md` for project-specific context:

```markdown
# My Project
This is a React app with TypeScript and Tailwind CSS.
Follow our coding standards and use functional components.
```

### Router Mode (Multiple Providers)
If you have multiple API keys configured, you can use the router for optimal performance:

```bash
langcode chat --router --priority quality     # Best quality
langcode chat --router --priority speed       # Fastest response
langcode chat --router --priority cost        # Most cost-effective
```

## 📝 Configuration Examples

### Development Setup
```env
# .env for development
OPENAI_API_KEY=your_zai_api_key
OPENAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
OPENAI_MODEL=GLM-4.5-air  # Fast for prototyping
OPENAI_TEMPERATURE=0.2    # More creative
```

### Production Setup
```env
# .env for production code
OPENAI_API_KEY=your_zai_api_key
OPENAI_BASE_URL=https://api.z.ai/api/coding/paas/v4
OPENAI_MODEL=GLM-4.6      # Highest quality
OPENAI_TEMPERATURE=0.1    # More deterministic
```

## 🛠️ Troubleshooting

### Check Configuration
```bash
langcode doctor
```

### Common Issues

1. **API Key Not Working**
   - Verify your Z.AI API key from the dashboard
   - Check that `OPENAI_API_KEY` is set correctly

2. **Model Not Available**
   - Ensure you're using supported models: GLM-4.6, GLM-4.5, GLM-4.5-air
   - Check model names are in UPPERCASE

3. **Connection Issues**
   - Verify `OPENAI_BASE_URL=https://api.z.ai/api/coding/paas/v4`
   - Check internet connection

### Environment Variables
```bash
# Verify current settings
echo $OPENAI_API_KEY
echo $OPENAI_BASE_URL
echo $OPENAI_MODEL
```

## 🎯 Best Practices

1. **Choose the Right Model**
   - `GLM-4.6` for complex features and architecture
   - `GLM-4.5-air` for quick fixes and simple tasks
   - `GLM-4.5` for balanced performance

2. **Use Project Instructions**
   - Create `.langcode/langcode.md` with project context
   - Include coding standards and architecture decisions

3. **Mode Selection**
   - Use `react` mode for most tasks
   - Use `deep --auto` for complex feature implementation
   - Use `fix` for bug diagnosis and resolution

4. **Temperature Settings**
   - `0.1` for production code (more deterministic)
   - `0.2-0.3` for creative exploration

## 🆚 Comparison: Z.AI vs Other Providers

| Feature | Z.AI | OpenAI | Anthropic | Gemini |
|---------|------|--------|-----------|--------|
| Models | GLM-4.6, 4.5, 4.5-air | GPT-4, GPT-3.5 | Claude 3.5 | Gemini Pro |
| Cost | 💰 Lower | 💰💰 Higher | 💰💰 Higher | 💰 Lower |
| Speed | ⚡ Fast | 🐢 Slower | ⚡ Fast | ⚡⚡ Fastest |
| Coding | 🎯 Specialized | 🎯 General | 🎯 Good | 🎯 Good |
| OpenAI Compatible | ✅ Yes | ✅ Native | ❌ No | ❌ No |

## 📚 Resources

- [langchain-code GitHub](https://github.com/zamalali/langchain-code)
- [Z.AI Developer Documentation](https://docs.z.ai/devpack/tool/others)
- [GLM Model Documentation](https://docs.z.ai/models)

## 🤝 Support

1. Check `langcode doctor` for environment issues
2. Review Z.AI documentation for API problems
3. Use GitHub issues for langchain-code problems

---

**Happy coding with Z.AI + langchain-code! 🚀**