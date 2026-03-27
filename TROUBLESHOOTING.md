# ModPorter AI Troubleshooting Guide

This guide covers common issues, error messages, and solutions for ModPorter AI.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Configuration Issues](#configuration-issues)
3. [Agent Errors](#agent-errors)
4. [Conversion Failures](#conversion-failures)
5. [Performance Issues](#performance-issues)
6. [Docker Issues](#docker-issues)
7. [API/LLM Issues](#apillm-issues)
8. [Testing Issues](#testing-issues)

---

## Installation Issues

### Python Version Mismatch

**Error:**
```
ERROR: Package 'modporter-ai' requires Python >=3.10 but you have Python 3.9.x
```

**Solution:**
```bash
# Check Python version
python --version

# Install Python 3.10+ using pyenv (recommended)
pyenv install 3.10.13
pyenv local 3.10.13

# Or use conda
conda create -n modporter python=3.10
conda activate modporter
```

### Missing Dependencies

**Error:**
```
ModuleNotFoundError: No module named 'crewai'
```

**Solution:**
```bash
# Install all dependencies
pip install -r requirements.txt

# Or install the package in development mode
pip install -e .
```

### Java Parser Issues

**Error:**
```
ModuleNotFoundError: No module named 'javalang'
```

**Solution:**
```bash
pip install javalang
```

---

## Configuration Issues

### Missing Environment Variables

**Error:**
```
ERROR: OPENAI_API_KEY not found in environment
```

**Solution:**
```bash
# Create .env file
cp .env.example .env

# Edit .env and add your API key
echo "OPENAI_API_KEY=your-key-here" >> .env

# Or export directly
export OPENAI_API_KEY="your-key-here"
```

### Invalid Ollama Configuration

**Error:**
```
ConnectionError: Cannot connect to Ollama at http://localhost:11434
```

**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start Ollama if not running
ollama serve

# For Docker environments, check the Ollama container
docker ps | grep ollama
docker start ollama  # if stopped
```

### Variant Configuration Not Found

**Error:**
```
WARNING: Variant 'custom_variant' configuration not found, using default
```

**Solution:**
1. Check that the variant file exists in `ai-engine/config/variants/`
2. Ensure the variant ID matches the filename (without `.yaml`)
3. Validate the YAML syntax

```bash
# List available variants
ls ai-engine/config/variants/

# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('ai-engine/config/variants/your_variant.yaml'))"
```

---

## Agent Errors

### JavaAnalyzerAgent Errors

#### Empty JAR File

**Error:**
```
Empty JAR file: /path/to/mod.jar
```

**Solution:**
- Verify the JAR file is not corrupted
- Check the file size is greater than 0
- Try re-downloading the mod file

```bash
# Check JAR file
unzip -l /path/to/mod.jar

# If empty, re-download the mod
```

#### Framework Detection Failed

**Error:**
```
Framework: unknown
```

**Solution:**
- The mod may use an unsupported framework
- Check for metadata files manually:

```bash
# Check for Forge
unzip -p mod.jar mcmod.info

# Check for Fabric
unzip -p mod.jar fabric.mod.json

# Check for Quilt
unzip -p mod.jar quilt.mod.json
```

### LogicTranslatorAgent Errors

#### Block Generation Failed

**Error:**
```
Block generation failed: Missing required property 'material'
```

**Solution:**
- Ensure the Java block analysis includes required properties
- Check that the block class was properly parsed

```python
# Verify block analysis data
block_analysis = {
    "name": "CopperBlock",
    "registry_name": "copper_block",
    "properties": {
        "material": "metal",  # Required
        "hardness": 5.0,
        "explosion_resistance": 6.0
    }
}
```

#### Invalid Block JSON

**Error:**
```
Block validation failed: Missing 'identifier' in description
```

**Solution:**
- Check the generated block JSON structure
- Ensure namespace is included in identifier

```json
{
  "format_version": "1.20.10",
  "minecraft:block": {
    "description": {
      "identifier": "namespace:block_name"  // Must include namespace
    }
  }
}
```

### CrewAI Agent Errors

#### Memory Validation Error

**Error:**
```
ValidationError: memory field cannot be set when using Ollama
```

**Solution:**
- Memory is automatically disabled when using Ollama
- Ensure the environment variable is set:

```bash
export USE_OLLAMA=true
```

#### Tool Execution Timeout

**Error:**
```
TimeoutError: Tool execution timed out after 300 seconds
```

**Solution:**
- Increase timeout in configuration
- Simplify the mod being analyzed
- Check for infinite loops in custom tools

```python
# Increase timeout in rate_limiter.py
request_timeout=600  # 10 minutes
```

---

## Conversion Failures

### Mod File Not Found

**Error:**
```
Mod file not found: /path/to/mod.jar
```

**Solution:**
```bash
# Check if path is correct
ls -la /path/to/mod.jar

# If using relative path, check working directory
pwd

# Use absolute path
python -m crew.main /absolute/path/to/mod.jar
```

### Output Directory Not Writable

**Error:**
```
PermissionError: [Errno 13] Permission denied: '/app/output'
```

**Solution:**
```bash
# Create output directory with proper permissions
mkdir -p /app/output
chmod 755 /app/output

# Or use a different output directory
python -m crew.main input.jar --output ~/output
```

### Conversion Pipeline Stuck

**Symptoms:**
- Conversion hangs at a specific stage
- No progress updates for extended period

**Solution:**
1. Check logs for the stuck stage
2. Enable verbose logging:

```bash
export LOG_LEVEL=DEBUG
python -m crew.main input.jar
```

3. Check for resource constraints:

```bash
# Check memory usage
free -h

# Check disk space
df -h

# Check CPU usage
top
```

---

## Performance Issues

### Slow Analysis

**Symptoms:**
- JAR analysis takes > 5 minutes
- High CPU/memory usage

**Solutions:**

1. **Reduce analysis depth:**
```python
# In conversion_crew.py
analysis_depth = "basic"  # Instead of "comprehensive"
```

2. **Limit file processing:**
```python
# In java_analyzer.py
FEATURE_ANALYSIS_FILE_LIMIT = 5  # Reduce from 10
```

3. **Use caching:**
```bash
# Enable caching for repeated analyses
export ENABLE_CACHE=true
```

### Memory Issues

**Error:**
```
MemoryError: Unable to allocate array
```

**Solution:**
```bash
# Increase Python memory limit
export PYTHONHASHSEED=0
export PYTHONMALLOC=malloc

# Or use a machine with more RAM
# For Docker, increase container memory:
docker run --memory=4g modporter-ai
```

---

## Docker Issues

### Container Won't Start

**Error:**
```
Error: container exited immediately
```

**Solution:**
```bash
# Check container logs
docker logs modporter-ai

# Check for missing environment variables
docker inspect modporter-ai | grep -A 10 "Env"

# Rebuild container
docker-compose build --no-cache
docker-compose up
```

### Ollama Container Not Reachable

**Error:**
```
ConnectionError: Cannot connect to http://ollama:11434
```

**Solution:**
```bash
# Check Docker network
docker network ls
docker network inspect modporter_default

# Ensure both containers are on same network
docker-compose up -d

# Use correct hostname in Docker
export OLLAMA_BASE_URL=http://ollama:11434
export DOCKER_ENVIRONMENT=true
```

### Volume Mount Issues

**Error:**
```
PermissionError: Cannot write to mounted volume
```

**Solution:**
```bash
# Fix volume permissions
sudo chown -R $USER:$USER ./output

# Or use Docker user mapping
docker run --user $(id -u):$(id -g) modporter-ai
```

---

## API/LLM Issues

### OpenAI Rate Limiting

**Error:**
```
RateLimitError: Rate limit exceeded for GPT-4
```

**Solution:**
```bash
# Wait and retry (automatic in rate_limiter.py)
# Or use a different model
export MODEL_NAME=gpt-3.5-turbo

# Or use Ollama for local inference
export USE_OLLAMA=true
```

### Ollama Model Not Found

**Error:**
```
Error: model 'llama3.2' not found
```

**Solution:**
```bash
# Pull the model
ollama pull llama3.2

# List available models
ollama list

# Use a different model
export OLLAMA_MODEL=llama2
```

### Invalid API Response

**Error:**
```
JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Solution:**
- Check API key is valid
- Verify API endpoint is correct
- Enable response logging:

```bash
export LOG_LEVEL=DEBUG
export LOG_API_RESPONSES=true
```

---

## Testing Issues

### Tests Fail with Import Errors

**Error:**
```
ImportError: cannot import name 'JavaAnalyzerAgent' from 'agents'
```

**Solution:**
```bash
# Ensure package is installed in development mode
pip install -e .

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/ai-engine"
```

### Fixture Not Found

**Error:**
```
FixtureNotFound: 'mock_jar_path' is not a valid fixture
```

**Solution:**
```bash
# Ensure conftest.py is in the tests directory
ls ai-engine/tests/conftest.py

# Or import fixtures explicitly
pytest --fixtures tests/test_agents_unit.py
```

### Coverage Not Generated

**Error:**
```
Coverage.py warning: No data was collected
```

**Solution:**
```bash
# Install pytest-cov
pip install pytest-cov

# Run with coverage
pytest --cov=agents --cov-report=html tests/
```

---

## Debug Mode

Enable comprehensive debugging:

```bash
# Set all debug flags
export LOG_LEVEL=DEBUG
export CREWAI_DEBUG=true
export PYTHONFAULTHANDLER=1

# Run with debug output
python -m crew.main input.jar 2>&1 | tee debug.log
```

## Getting Help

If you continue to experience issues:

1. **Check the logs:**
   ```bash
   # View recent logs
   tail -100 logs/modporter.log
   ```

2. **Search existing issues:**
   - [GitHub Issues](https://github.com/anchapin/ModPorter-AI/issues)

3. **Create a new issue:**
   - Include error messages
   - Include environment details (`python --version`, OS, etc.)
   - Include steps to reproduce
   - Attach debug logs if possible

4. **Community support:**
   - Check documentation in `/docs`
   - Review test cases in `/tests` for usage examples

---

## Quick Reference

| Issue | Solution |
|-------|----------|
| Python version | Use Python 3.10+ |
| Missing API key | Set `OPENAI_API_KEY` in `.env` |
| Ollama connection | Start Ollama: `ollama serve` |
| Empty JAR | Re-download mod file |
| Permission denied | `chmod 755` or use correct user |
| Rate limit | Wait or use different model |
| Memory error | Increase RAM or reduce file limit |
| Import error | `pip install -e .` |

---

*Last updated: 2026-02-19*