# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- LangGraph state-graph conversion pipeline as the only conversion path (issue #1201)
- `services/rag_service.py` LCEL chain replacing the legacy `RAGCrew` (issue #1201)
- `services/report_formatter.py` framework-agnostic conversion-report builder
- `orchestration/progress.py` framework-agnostic progress tracker
- `tests/test_no_crewai_references.py` regression guard for the migration

### Changed
- `utils/rate_limiter` LLM factories now return stock LangChain `BaseChatModel`
  instances (`ChatOpenAI` / `ChatOllama`) with built-in `InMemoryRateLimiter`,
  enabling LangGraph tool-calling, `bind_tools()` and `with_structured_output()`
- All tool layers migrated from `crewai.tools` to `langchain_core.tools`
- `chromadb` pin relaxed to `>=1.5.8,<2.0` (closes #1439, unblocked by #1201)
- `requires-python` floor bumped to `>=3.11` for langchain/langgraph compatibility

### Deprecated
- `crew/__init__.py` is now a no-op stub raising `ImportError` for any
  attribute access; remove the package entirely after one release window

### Removed
- **BREAKING**: removed the legacy multi-agent orchestration framework; the AI
  Engine now runs entirely on LangChain/LangGraph (issue #1201)
- `crew/conversion_crew.py`, `crew/rag_crew.py`, `orchestration/crew_integration.py`,
  `orchestration/run_agent_integration.py` deleted
- `OrchestrationStrategy.SEQUENTIAL` rebranded as a single-threaded baseline
  (the comment about mimicking the legacy framework is gone)
- `RateLimitedChatOpenAI`, `RateLimitedZAI`, `OpenAICompatibleLLM`,
  `enable_crew_mode` / `disable_crew_mode` removed from `utils.rate_limiter`
- `USE_LANGGRAPH_PIPELINE` environment variable retired (LangGraph is the only path)
- `config/rag_agents.yaml` deleted along with the legacy researcher/writer agent schema

### Fixed
- `process_conversion` no longer silently no-ops past `progress=10` when
  `USE_LANGGRAPH_PIPELINE` is unset — the LangGraph path always runs

### Security

---

## [0.1.0] - 2024-03-27

### Added
- Initial project setup with microservices architecture
- Backend FastAPI service with PostgreSQL (pgvector for RAG)
- AI Engine with CrewAI for mod conversion
- Frontend React application
- Redis for caching and rate limiting
- Docker Compose for local development
- Pre-commit hooks with security scanning (Bandit, Gitleaks)
- GitHub Actions CI/CD pipelines
- Security scanning workflow (Trivy, CodeQL, Dependency Review)
- Healthcheck endpoints for all services
- Database backup documentation
- Architecture Decision Records (ADRs)
- Load testing infrastructure with k6
- OpenAPI contract testing workflow

### Security
- Bandit SAST scanning in pre-commit
- Gitleaks secret detection
- Trivy vulnerability scanning in CI
- Dependency Review GitHub Action
- Rate limit headers middleware

---

## Versioning

This project uses [Semantic Versioning](https://semver.org/). Given a version number `MAJOR.MINOR.PATCH`:

- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality in a backwards compatible manner
- **PATCH** version for backwards compatible bug fixes

### Release Branches

- `main` - Current stable release
- `develop` - Next release development
- `release/x.y.z` - Release preparation branches

## How to Add Entries

When making changes, add entries under the `[Unreleased]` section with the appropriate subheading:

```markdown
## [Unreleased]

### Added
- New feature description

### Fixed
- Bug fix description
```

Categories:
- **Added** - New features
- **Changed** - Changes in existing functionality
- **Deprecated** - Soon-to-be removed features
- **Removed** - Removed features
- **Fixed** - Bug fixes
- **Security** - Vulnerability fixes

## Automation

This changelog is manually maintained. Before releasing a new version:

1. Review all changes since last release
2. Move `[Unreleased]` entries to the new version section
3. Add release date
4. Create git tag: `git tag -a v0.1.0 -m "Release v0.1.0"`
5. Push tag: `git push origin v0.1.0`

## Related Documents

- [CONTRIBUTING.md](./CONTRIBUTING.md) - Contribution guidelines
- [SECURITY.md](./SECURITY.md) - Security policies
- [docs/adr/README.md](./docs/adr/README.md) - Architecture Decision Records
