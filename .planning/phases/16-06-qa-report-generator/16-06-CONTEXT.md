# Phase 16-06: QA Report Generator - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning
**Source:** Roadmap requirements extraction

<domain>
## Phase Boundary

**Phase Goal:** Aggregates all agent outputs into comprehensive QA report

**What this phase delivers:**
- Aggregates results from all 4 QA agents (Translator, Reviewer, Tester, Semantic Checker)
- Generates quality score (weighted average)
- Lists all issues with severity and location
- Includes test execution results
- Shows semantic equivalence analysis
- Exports report in JSON/HTML/Markdown formats
- Color-coded severity (green/yellow/red)
- Downloadable with conversion results

</domain>

<decisions>
## Implementation Decisions

### Core Functionality (Locked)
- Aggregate results from Translator, Reviewer, Tester, and Semantic Checker agents
- Generate weighted quality score (0-100)
- Support JSON, HTML, and Markdown export formats
- Color-coded severity levels: green (pass), yellow (warning), red (critical)
- Downloadable reports attached to conversion results

### Data Structures (Locked)
- QAReport dataclass with aggregated results from all agents
- QualityScore with weighted average calculation
- IssueSeverity enum: INFO, WARNING, ERROR, CRITICAL
- Issue location tracking (file, line, column)
- ExportFormat enum: JSON, HTML, MARKDOWN

### the agent's Discretion
- Specific weight distribution for quality score calculation
- HTML/Markdown template styling
- Report file naming conventions
- Default export format selection

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### QA System Architecture
- `.planning/phases/16-01-qa-context-orchestration/16-01-01-PLAN.md` — QAContext schema
- `.planning/phases/16-01-qa-context-orchestration/16-01-02-PLAN.md` — QAOrchestrator
- `.planning/phases/16-02-translator-agent/16-02-01-PLAN.md` — TranslatorAgent output format
- `.planning/phases/16-03-reviewer-agent/16-03-01-PLAN.md` — ReviewerAgent output format
- `.planning/phases/16-04-fixer-agent/16-04-01-PLAN.md` — TesterAgent output format
- `.planning/phases/16-05-semantic-checker-agent/16-05-01-PLAN.md` — SemanticCheckerAgent output format

### Project Structure
- `src/agents/` — Agent implementations
- `src/qa/` — QA system core (if exists)

</canonical_refs>

<specifics>
## Specific Ideas

- Quality score should be weighted: Translator (25%), Reviewer (25%), Tester (25%), Semantic Checker (25%)
- Issues should be sortable by severity and file location
- HTML reports should include inline styles for color-coding
- JSON export should include metadata (timestamp, job ID, agent versions)
- Report should be downloadable via API endpoint

</specifics>

<deferred>
## Deferred Ideas

None — QA Report Generator is self-contained feature

</deferred>

---

*Phase: 16-06-qa-report-generator*
*Context gathered: 2026-03-28 via roadmap requirements*