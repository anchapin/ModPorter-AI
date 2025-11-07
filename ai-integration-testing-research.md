# AI Integration Testing Research & Implementation Guide

## Issue Analysis: GitHub #289

**Research Question**: Best practices for integration tests with AI - running LLMs in GitHub CI without paid APIs.

### Current State Analysis

Based on analysis of the ModPorter-AI codebase, the project already has:

#### ✅ Existing LLM Integration
- **Ollama Support**: Already implemented with `USE_OLLAMA` environment variable
- **Local Model Support**: Uses `llama3.2` as default model
- **CI Infrastructure**: Self-hosted runner setup documented and partially implemented
- **Testing Framework**: Comprehensive pytest setup with integration test suites

#### ✅ Current CI Configuration
- **Self-Hosted Runners**: Already configured for `[self-hosted, Linux, X64, ollama]`
- **Docker Compose**: Test environment with PostgreSQL, Redis, and service orchestration
- **Matrix Strategy**: Multiple test suites (integration, backend, ai-engine)
- **Optimization**: Multi-level caching and base image strategies

#### ✅ AI Engine Architecture
- **Rate Limiting**: Built-in rate limiter with Ollama fallback
- **Flexible LLM Backend**: Supports OpenAI, LiteLLM, and direct Ollama integration
- **CrewAI Integration**: Multi-agent system with LLM coordination
- **Environment Detection**: Automatic detection of Docker vs local environments

## Research Findings (Updated with 2025 Research)

### 1. Running Local LLMs on GitHub Hosted Runners

**❌ Standard GitHub Hosted Runners Limitation:**
- **No GPU Access**: Standard GitHub runners don't provide GPU access
- **CPU-Only Models**: Only smaller CPU models could run (very slow, limited quality)
- **Resource Constraints**: 2-core, 7GB RAM runners insufficient for meaningful LLM testing
- **Time Limits**: 6-hour job timeout may be exceeded by model loading/inference

**✅ NEW: GitHub GPU Hosted Runners (Available July 2024):**
- **T4 GPU Access**: Now available for Teams/Enterprise plans ($$$)
- **Fully Managed**: No setup required, integrated with GitHub Actions
- **Windows/Linux Support**: Cross-platform GPU runners available
- **Cost**: Significantly more expensive than self-hosted solutions
- **Limitation**: Only NVIDIA GPUs, no AMD GPU support

### 2. AMD GPU (6600 XT) LLM Solutions

**🎯 Specific to Your Hardware:**
Your AMD Radeon RX 6600 XT (RDNA2) has several viable LLM inference options:

#### Option A: Ollama with ROCm (Traditional Approach)
- **Status**: Limited official support for 6600 XT
- **Issues**: ROCm primarily supports Radeon Pro cards, consumer cards require unofficial patches
- **Performance**: Good if you can get it working, but setup complexity is high

#### Option B: llama.cpp with Vulkan (Recommended for Your Hardware) ✅
- **Support**: Excellent RDNA2 support via Vulkan backend
- **Performance**: ~25x speedup over CPU (based on community reports)
- **Setup**: Simpler than ROCm, works on Windows 11
- **Docker Compatible**: Can run in Docker containers
- **Installation**: `llama-cpp-python` with Vulkan backend

#### Option C: Docker Model Runner (New Alternative - 2025)
- **Native Windows Support**: Added in April 2025
- **Docker Integration**: Seamless Docker Desktop integration
- **Emerging Technology**: Less mature than Ollama but promising
- **AMD GPU Status**: Vulkan-based, should work with 6600 XT

### 3. Self-Hosted GitHub Runner Solutions

#### Option A: Windows 11 Native Runner (Recommended for Your Setup) ✅
- **Your Hardware**: 6600 XT + 16GB+ RAM perfect for LLM testing
- **Docker Desktop**: Use Docker Desktop's WSL2 integration
- **GPU Access**: Native AMD GPU access for llama.cpp + Vulkan
- **Performance**: Excellent for local development and CI

#### Option B: Cloud-based Self-Hosted Runners
- **RunsOn**: 10x cheaper than GitHub GPU runners, supports AMD GPUs
- **HyperEnv**: Up to 75% cost savings vs GitHub GPU runners
- **AWS EC2**: Full control but requires setup and maintenance

#### Option C: Hybrid GPU + Cloud Strategy
- **Local Development**: Windows 11 runner with 6600 XT
- **Cloud CI**: GitHub GPU runners for critical path testing
- **Cost Optimization**: Balance local convenience with cloud reliability

### 4. Cost Analysis (2025 Updated)

#### GitHub Hosted Options:
- **Standard Runners**: Free (but no LLM capability)
- **GPU Runners**: ~$1-2/hour for T4 GPU access
- **Monthly Estimate**: $200-500 for moderate LLM testing

#### Self-Hosted Options:
- **Your Windows Machine**: $0 hardware cost (already owned)
- **Electricity**: ~$20-50/month additional usage
- **Internet**: Minimal impact
- **Total Monthly**: ~$20-50 vs $200-500 for GPU runners

#### API-Based Option (Using Existing Z.AI Pro Plan):
- **Z.AI GLM Pro**: Already paid for coding plan
- **API Access**: LLM inference through Z.AI endpoints
- **Cost**: $0 additional (already subscribed)
- **Benefits**: High-quality models, no setup required, reliable
- **Integration**: Can be configured as fallback or primary LLM backend

#### Third-Party Services:
- **RunsOn**: ~10x cheaper than GitHub GPU runners
- **HyperEnv**: Up to 75% savings vs GitHub GPU runners
- **Setup Complexity**: Medium to high

## Enhanced Implementation Plan

### Phase 1: Optimize Current Self-Hosted Setup

#### 1.1 Windows 11 + AMD GPU Self-Hosted Runner Configuration
```yaml
# Target configuration in .github/workflows/ci.yml
integration-tests:
  runs-on: [self-hosted, Windows, X64, amd-gpu]
  timeout-minutes: 30
  env:
    PYTHONPATH: ${{ github.workspace }}
    USE_VULKAN_LLM: true
    GGML_VK_VISIBLE_DEVICES: 0
  services:
    redis:
      image: redis:7-alpine
      ports:
        - 6379:6379
    postgres:
      image: pgvector/pgvector:pg15
      env:
        POSTGRES_DB: modporter
        POSTGRES_USER: postgres
        POSTGRES_PASSWORD: password
      ports:
        - 5432:5432
```

#### 1.2 AMD GPU LLM Backend Setup (llama.cpp + Vulkan)
```python
# Enhanced LLM backend for AMD 6600 XT
class AMDVulkanLLM:
    def __init__(self, model_path="models/llama3.2-3b.Q4_K_M.gguf"):
        self.model_path = model_path
        self.device = "vulkan"
        self.n_gpu_layers = -1  # Use all available GPU layers
        
    def create_llm(self):
        from llama_cpp import Llama
        return Llama(
            model_path=self.model_path,
            n_gpu_layers=self.n_gpu_layers,
            n_ctx=2048,
            verbose=False,
            main_gpu=0,
            seed=-1,
            use_mmap=True,
            use_mlock=False,
            embedding=False,
            n_threads=8,
            n_threads_batch=4
        )
```

#### 1.3 Docker Desktop Integration for AMD GPU
```dockerfile
# Dockerfile for AMD GPU support
FROM python:3.11-slim

# Install Vulkan drivers and tools
RUN apt-get update && apt-get install -y \
    vulkan-tools \
    vulkan-validationlayers \
    mesa-vulkan-drivers \
    && rm -rf /var/lib/apt/lists/*

# Install llama.cpp with Vulkan support
RUN pip install llama-cpp-python --prefer-binary \
    --extra-index-url=https://download.pytorch.org/whl/cpu

WORKDIR /app
COPY . .

# Set Vulkan environment
ENV GGML_VK_VISIBLE_DEVICES=0
ENV VK_ICD_FILENAMES=/usr/share/vulkan/icd.d/radeon_icd.x86_64.json

CMD ["python", "-m", "pytest", "tests/integration/"]
```

#### 1.4 Intelligent Test Orchestration
```python
# Enhanced test selection based on changes
def should_run_llm_tests(changed_files):
    llm_related_paths = [
        'ai-engine/agents/',
        'ai-engine/crew/',
        'ai-engine/utils/rate_limiter.py',
        'ai-engine/testing/'
    ]
    return any(path in changed_file for path in llm_related_paths for changed_file in changed_files)

def get_llm_backend():
    """Auto-detect best LLM backend based on available hardware and API access"""
    if os.getenv("USE_Z_AI", "false").lower() == "true":
        return ZAILLM()  # Use existing Z.AI Pro plan
    elif os.getenv("USE_VULKAN_LLM", "false").lower() == "true":
        return AMDVulkanLLM()
    elif os.getenv("USE_OLLAMA", "false").lower() == "true":
        return OllamaLLM()
    else:
        return OpenAILLM()  # Fallback to API
```

### Phase 2: Advanced LLM Testing Strategies

#### 2.1 Model Caching Strategy
- **Pre-built Docker Images**: Include models in base images
- **Layer Caching**: Store model weights in Docker layers
- **Incremental Updates**: Only download changed model components

#### 2.2 Test Optimization
```python
# Smart test execution with LLM availability detection
@pytest.mark.skipif(
    not os.getenv("USE_OLLAMA") or not check_ollama_health(),
    reason="Ollama not available or unhealthy"
)
def test_llm_integration():
    # Integration test implementation
    pass
```

#### 2.3 Performance Benchmarking
- **Model Loading Times**: Track initialization overhead
- **Inference Speed**: Monitor response times
- **Memory Usage**: Track resource consumption
- **Cost Analysis**: Compare vs API-based testing

### Phase 3: Production-Grade Setup

#### 3.1 Multi-Runner Strategy
```yaml
# Multiple self-hosted runners for different purposes
strategy:
  matrix:
    runner-type: [cpu-only, gpu-accelerated, model-cached]
    include:
      - runner-type: cpu-only
        runs-on: [self-hosted, Linux, X64, ollama-cpu]
        test-scope: [unit, basic-integration]
      - runner-type: gpu-accelerated
        runs-on: [self-hosted, Linux, X64, ollama-gpu]
        test-scope: [full-integration, performance]
      - runner-type: model-cached
        runs-on: [self-hosted, Linux, X64, ollama-cached]
        test-scope: [e2e, benchmarking]
```

#### 3.2 Advanced Caching
```yaml
# Multi-level caching for models and dependencies
cache-models:
  uses: actions/cache@v4
  with:
    path: |
      /root/.ollama/models/
      /tmp/llm-cache/
    key: llm-models-${{ hashFiles('ai-engine/models/**') }}
    restore-keys: |
      llm-models-
      models-
```

## Security Considerations

### 1. Self-Hosted Runner Security
- **Network Isolation**: Run runners in separate network segments
- **Resource Limits**: CPU, memory, and disk usage constraints
- **Access Control**: Limited permissions and scoped access tokens
- **Audit Logging**: Comprehensive logging of all activities

### 2. Model Security
- **Model Verification**: Checksums and authenticity verification
- **Data Privacy**: Ensure no training data leakage
- **Update Security**: Secure model update mechanisms

## Cost Analysis

### Current Setup (API-based)
- **OpenAI API**: $0.002-0.03 per 1K tokens (varies by model)
- **Monthly Estimate**: $200-500 for comprehensive testing
- **Pros**: No infrastructure maintenance
- **Cons**: Recurring costs, rate limits, dependency

### Self-Hosted Setup
- **Hardware**: $1000-3000 one-time (GPU-enabled machine)
- **Hosting**: $50-200/month (cloud or co-location)
- **Maintenance**: Minimal (Docker and runner management)
- **Pros**: Fixed costs, full control, no API limits
- **Cons**: Initial investment, maintenance overhead

### Hybrid Approach (Recommended)
- **Unit Tests**: GitHub hosted (free)
- **Basic Integration**: Self-hosted CPU runner (~$50/month)
- **Full Integration**: Self-hosted GPU runner (~$200/month)
- **Total Monthly Cost**: ~$250 vs $500+ API approach

## Enhanced Implementation Prompt

### Feature Branch Prompt: `implement-enhanced-ai-testing`

```
# Enhanced AI Integration Testing Implementation

## Objective
Implement comprehensive LLM testing strategy for ModPorter-AI that balances cost, reliability, and testing effectiveness.

## Current State
- ✅ Ollama integration already implemented with USE_OLLAMA environment variable
- ✅ Self-hosted runner documentation exists but needs optimization
- ✅ CI workflows partially configured for matrix testing
- ❌ Missing: Comprehensive LLM availability detection, smart caching, optimized test orchestration

## Implementation Tasks

### Phase 1: Infrastructure Optimization (Priority: HIGH)
1. **Enhance Self-Hosted Runner Configuration**
   - Implement health checks for Ollama service in CI
   - Add model pre-caching in Docker base images
   - Create fallback mechanisms for runner unavailability

2. **Smart Test Orchestration**
   - Implement change-based test selection for LLM tests
   - Add conditional test execution based on code changes
   - Create test categories: unit, basic-integration, full-integration

3. **Enhanced Caching Strategy**
   - Multi-level caching for models, dependencies, and test artifacts
   - Intelligent cache invalidation based on model/config changes
   - Docker layer optimization for faster startup

### Phase 2: Advanced Testing Framework (Priority: MEDIUM)
1. **LLM Availability Detection**
   - Health check utilities for multiple LLM backends
   - Graceful degradation when models unavailable
   - Performance benchmarking infrastructure

2. **Test Environment Optimization**
   - Docker Compose configurations for different testing scenarios
   - Memory and resource optimization for CI environments
   - Parallel test execution with resource isolation

3. **Monitoring and Reporting**
   - Test execution metrics and performance tracking
   - Model behavior consistency validation
   - Cost analysis and optimization recommendations

### Phase 3: Production Readiness (Priority: LOW)
1. **Multi-Runner Strategy**
   - CPU-only runners for basic tests
   - GPU-accelerated runners for performance tests
   - Model-cached runners for fast E2E testing

2. **Security and Compliance**
   - Runner security hardening
   - Model integrity verification
   - Audit logging and compliance reporting

## Technical Requirements

### Environment Variables
```bash
# LLM Configuration
USE_Z_AI=true  # Use existing Z.AI Pro plan (recommended)
USE_OLLAMA=true  # Fallback to local Ollama
USE_VULKAN_LLM=true  # Use llama.cpp with Vulkan for AMD GPU
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
DOCKER_ENVIRONMENT=true  # Auto-detect container URLs

# Z.AI Configuration (if using Z.AI)
Z_AI_API_KEY=your_z_ai_api_key_here
Z_AI_MODEL=glm-4-plus  # Latest GLM model
Z_AI_BASE_URL=https://api.z.ai/v1

# Test Orchestration
LLM_TEST_LEVEL=basic  # basic|standard|comprehensive
SKIP_LLM_TESTS=false
CACHE_LLM_MODELS=true

# Performance Monitoring
ENABLE_LLM_BENCHMARKING=false
TRACK_MODEL_PERFORMANCE=false
```

### File Structure
```
.github/
├── workflows/
│   ├── ci.yml (enhance existing)
│   └── llm-testing.yml (new)
├── runners/
│   ├── ollama-setup.sh (new)
│   └── health-checks.sh (new)
└── scripts/
    ├── test-selector.py (new)
    └── llm-health-check.py (new)

ai-engine/
├── testing/
│   ├── llm_test_utils.py (new)
│   ├── model_benchmarks.py (new)
│   └── test_orchestrator.py (new)
└── utils/
    └── llm_health.py (enhance existing)
```

### Testing Categories
1. **Unit Tests** (GitHub hosted)
   - Logic validation without LLM calls
   - Mock-based LLM response testing
   - Fast feedback for code changes

2. **Basic Integration** (Self-hosted, CPU)
   - LLM connectivity tests
   - Basic crew functionality
   - Model loading and basic inference

3. **Full Integration** (Self-hosted, GPU)
   - End-to-end workflow testing
   - Performance benchmarking
   - Multi-agent coordination

## Success Criteria

### Performance Targets
- CI execution time: <25 minutes (current: 45-60 minutes)
- LLM test reliability: >95% success rate
- Cost reduction: 50% vs API-based approach
- Cache hit rate: >90% for models and dependencies

### Quality Metrics
- LLM behavior consistency across environments
- Test coverage for all LLM integration points
- Model performance baseline establishment
- Automated cost and performance reporting

### Operational Excellence
- Zero manual intervention for routine testing
- Clear failure diagnostics and recovery procedures
- Scalable testing infrastructure for future growth
- Comprehensive monitoring and alerting

## Implementation Notes

1. **Iterative Approach**: Start with Phase 1, validate success, then proceed
2. **Backwards Compatibility**: Ensure all changes work with existing workflows
3. **Documentation**: Update all relevant documentation and README files
4. **Testing**: Thoroughly test all changes before merging to main
5. **Monitoring**: Implement monitoring from day one to track improvements

## Risks and Mitigations

### Technical Risks
- **Runner Reliability**: Implement multiple runner pools and health checks
- **Model Availability**: Pre-cache models and implement fallback strategies
- **Performance Degradation**: Continuous monitoring and optimization

### Operational Risks
- **Security Concerns**: Follow security best practices for self-hosted runners
- **Maintenance Overhead**: Automate as much as possible
- **Cost Overrun**: Monitor usage and implement cost controls

This implementation will transform ModPorter-AI's LLM testing from a potentially expensive, API-dependent approach to a cost-effective, reliable, and comprehensive testing strategy that scales with the project's growth.
```

## Next Steps

1. **Create Feature Branch**: `git checkout -b feature/enhanced-ai-testing`
2. **Phase 1 Implementation**: Focus on infrastructure optimization
3. **Testing and Validation**: Ensure all changes work as expected
4. **Documentation Updates**: Update README and developer guides
5. **Monitoring Setup**: Implement performance and cost tracking
6. **Iterative Improvement**: Continuously optimize based on metrics

## References and Resources

### Existing Documentation
- `.github/self-hosted-runner-setup.md` - Current runner setup guide
- `ai-engine/utils/rate_limiter.py` - LLM integration utilities
- `.github/workflows/ci.yml` - Current CI configuration
- `README.md` - Project setup and LLM configuration

### External Resources
- GitHub Actions Self-Hosted Runner Documentation
- Ollama Documentation and Best Practices
- Docker Compose for Testing Environments
- CI/CD Best Practices for AI/ML Projects

---

This research confirms that the self-hosted runner approach is the most viable solution for comprehensive LLM testing in CI/CD, and ModPorter-AI already has much of the foundation in place. The implementation plan focuses on optimizing existing infrastructure rather than building from scratch.
