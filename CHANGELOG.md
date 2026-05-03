# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
### Changed
### Deprecated
### Removed
### Fixed
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
