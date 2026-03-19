# Phase 10-01: Timeout & Deadline Management - Requirements

## Requirements Coverage

| Requirement ID | Description | Status |
|----------------|-------------|--------|
| REQ-1.15 | Implement job timeout (30 minutes max) | 🔄 Implementing |

## Additional Requirements (Implicit)

| Requirement | Description |
|-------------|-------------|
| REQ-T1.1 | All LLM API calls must have explicit timeouts |
| REQ-T1.2 | Agent tasks must support deadline management |
| REQ-T1.3 | Pipeline stages must timeout independently |
| REQ-T1.4 | Timeout events must be logged with full context |
| REQ-T1.5 | Timeout configuration must be externalized (YAML) |
| REQ-T1.6 | System must handle timeout gracefully without hanging |
| REQ-T1.7 | Timeout status must be exposed in API responses |

## Acceptance Criteria

1. **LLM Timeout**: Every LLM API call (translate, analyze, validate) has explicit timeout
2. **Agent Deadline**: Each agent task can be terminated gracefully at deadline
3. **Stage Timeout**: Pipeline stages (analysis, conversion, validation, packaging) timeout independently
4. **Job Deadline**: Overall job timeout at 30 minutes (configurable)
5. **Logging**: All timeout events logged with context (what timed out, how long, why)
6. **Configurability**: Timeouts adjustable via YAML configuration file
7. **Graceful Handling**: Timeout results in graceful degradation, not crash

## Configuration Schema

```yaml
llm_timeout:
  openai:
    translate: 120  # seconds
    analyze: 60
    validate: 30
  anthropic:
    translate: 120
    analyze: 60
    validate: 30
  ollama:
    translate: 180
    analyze: 90
    validate: 45

agent_timeout:
  java_analyzer: 120
  bedrock_architect: 60
  logic_translator: 180
  asset_converter: 120
  packaging_agent: 60
  qa_validator: 90
  warning_threshold: 0.8  # Warn at 80% of timeout

pipeline_timeout:
  analysis: 180
  conversion: 300
  validation: 120
  packaging: 60
  total_job: 1800  # 30 minutes

timeouts:
  enabled: true
  default: 300
  max: 3600
```
