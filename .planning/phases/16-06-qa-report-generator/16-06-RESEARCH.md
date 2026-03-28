# Phase 16-06: QA Report Generator - Research

**Researched:** 2026-03-28
**Domain:** QA report generation, weighted quality scoring, multi-format export
**Confidence:** HIGH

## Summary

This phase implements the QA Report Generator that aggregates results from the multi-agent QA pipeline (Translator, Reviewer, Tester, Semantic Checker agents) into comprehensive, exportable reports. The core requirement is creating a data aggregation layer with weighted quality scoring and multiple export formats (JSON, HTML, Markdown).

**Primary recommendation:** Use dataclasses/Pydantic for type-safe aggregation, Jinja2 for template-based export, and implement a pluggable export architecture for extensibility.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Aggregate results from Translator, Reviewer, Tester, and Semantic Checker agents
- Generate weighted quality score (0-100)
- Support JSON, HTML, and Markdown export formats
- Color-coded severity levels: green (pass), yellow (warning), red (critical)
- Downloadable reports attached to conversion results
- QAReport dataclass with aggregated results from all agents
- QualityScore with weighted average calculation
- IssueSeverity enum: INFO, WARNING, ERROR, CRITICAL
- Issue location tracking (file, line, column)
- ExportFormat enum: JSON, HTML, MARKDOWN

### Claude's Discretion
- Specific weight distribution for quality score calculation
- HTML/Markdown template styling
- Report file naming conventions
- Default export format selection

### Deferred Ideas (OUT OF SCOPE)
None — QA Report Generator is self-contained feature

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| **Pydantic** | 2.x | Data validation, serialization | Type-safe dataclasses, automatic JSON serialization |
| **Jinja2** | 3.x | Template engine | Standard Python templating, HTML/Markdown generation |
| **dataclasses** | stdlib | Lightweight data structures | Simple DTOs for agent outputs |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **markdown** | 3.x | Markdown rendering | Convert Markdown to HTML if needed |
| **bleach** | 6.x | HTML sanitization | Sanitize HTML output for security |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Pydantic | attrs, dataclasses | attrs lacks validation, dataclasses less feature-rich |
| Jinja2 | mako, chevron | Jinja2 is more widely used, better Python integration |
| Custom export | ReportLab, weasyprint | Those are for PDFs, we export to JSON/HTML/MD |

**Installation:**
```bash
pip install pydantic jinja2 markdown bleach
```

## Architecture Patterns

### Recommended Project Structure
```
src/qa/
├── __init__.py
├── models.py              # QAReport, QualityScore, IssueSeverity, etc.
├── aggregator.py          # Result aggregation logic
├── scorer.py              # Weighted quality score calculation
├── exporters/
│   ├── __init__.py
│   ├── base.py            # BaseExporter abstract class
│   ├── json_exporter.py   # JSON export implementation
│   ├── html_exporter.py   # HTML export implementation
│   └── markdown_exporter.py  # Markdown export implementation
├── templates/
│   ├── report.html.j2     # HTML report template
│   └── report.md.j2       # Markdown report template
├── report_generator.py    # Main QAReportGenerator class
└── api.py                 # FastAPI routes for report download
```

### Pattern 1: Pluggable Exporter Architecture
**What:** Abstract base class for exporters with registry pattern
**When to use:** Multiple output formats, extensible export system
**Example:**
```python
from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseExporter(ABC):
    """Abstract base for all report exporters."""
    
    @property
    @abstractmethod
    def format(self) -> str:
        """Export format identifier."""
        pass
    
    @abstractmethod
    def export(self, report: 'QAReport', **options) -> str:
        """Export report to string in target format."""
        pass

class ExporterRegistry:
    """Registry for pluggable exporters."""
    
    def __init__(self):
        self._exporters: Dict[str, BaseExporter] = {}
    
    def register(self, exporter: BaseExporter):
        self._exporters[exporter.format] = exporter
    
    def get(self, format: str) -> BaseExporter:
        return self._exporters[format]
```

### Pattern 2: Weighted Score Calculation
**What:** Quality score aggregation with configurable weights
**When to use:** Combining multiple agent scores into single metric
**Example:**
```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class QualityScore:
    """Weighted quality score from agent results."""
    translator_score: float      # 0-100
    reviewer_score: float        # 0-100
    tester_score: float          # 0-100
    semantic_score: float        # 0-100
    
    # Default equal weights (25% each)
    weights: Dict[str, float] = None
    
    def __post_init__(self):
        if self.weights is None:
            self.weights = {
                'translator': 0.25,
                'reviewer': 0.25,
                'tester': 0.25,
                'semantic': 0.25
            }
    
    @property
    def overall(self) -> float:
        """Calculate weighted average."""
        return (
            self.translator_score * self.weights['translator'] +
            self.reviewer_score * self.weights['reviewer'] +
            self.tester_score * self.weights['tester'] +
            self.semantic_score * self.weights['semantic']
        )
```

### Pattern 3: Issue Tracking with Location
**What:** Structured issue representation with source location
**When to use:** Tracking errors, warnings from multiple agents
**Example:**
```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class IssueSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class IssueLocation:
    """Location of an issue in source code."""
    file: str
    line: int
    column: Optional[int] = None

@dataclass
class Issue:
    """A single issue found during QA."""
    severity: IssueSeverity
    message: str
    location: Optional[IssueLocation] = None
    agent: Optional[str] = None        # Which agent found it
    code: Optional[str] = None         # Error code for filtering
```

### Anti-Patterns to Avoid
- **Hardcoding export formats:** Use pluggable architecture for extensibility
- **Mixing aggregation with export:** Separate concerns into different modules
- **Ignoring encoding issues:** Always specify UTF-8 for file exports

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Data validation | Custom validation | Pydantic | Built-in validation, serialization, error messages |
| HTML generation | String concatenation | Jinja2 | Safe templating, auto-escaping, inheritance |
| JSON serialization | Manual dict building | Pydantic model.model_dump() | Type-safe, handles dates/UUIDs |
| Color-coded output | ANSI codes | CSS classes + inline styles | HTML/MD need different handling |

**Key insight:** Report generation is a well-solved problem. Custom solutions add maintenance burden without benefits.

## Common Pitfalls

### Pitfall 1: Inconsistent Score Normalization
**What goes wrong:** Different agents return scores in different ranges (0-1 vs 0-100)
**Why it happens:** No unified scoring contract defined upfront
**How to avoid:** Define score contract in QAContext, normalize in aggregator
**Warning signs:** Quality score wildly off from expected range

### Pitfall 2: Template Injection in User Content
**What goes wrong:** Code comments from converted mods execute in Jinja2 templates
**Why it happens:** User content passed directly to template engine
**How to avoid:** Use autoescape in Jinja2, sanitize with bleach for HTML
**Warning signs:** Unexpected characters in rendered reports

### Pitfall 3: Large Report Memory Usage
**What goes wrong:** Reports with many issues consume excessive memory
**Why it happens:** Storing full file contents alongside issue locations
**How to avoid:** Store only file path and line number, not content
**Warning signs:** Memory spikes on large conversions

### Pitfall 4: Missing Agent Result Handling
**What goes wrong:** Report fails entirely if one agent fails
**Why it happens:** No partial result handling
**How to avoid:** Implement graceful degradation, show "N/A" for missing agents
**Warning signs:** Pipeline failures cascade to report generation

## Code Examples

Verified patterns:

### Aggregating Agent Results
```python
# Source: Standard Python patterns
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid

@dataclass
class AgentResult:
    """Result from a single QA agent."""
    agent_name: str
    score: float
    issues: List[Issue] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class QAReport:
    """Aggregated QA report from all agents."""
    job_id: str
    timestamp: datetime
    agent_results: List[AgentResult]
    quality_score: float
    
    # Computed properties
    @property
    def total_issues(self) -> int:
        return sum(len(r.issues) for r in self.agent_results)
    
    @property
    def issues_by_severity(self) -> Dict[IssueSeverity, List[Issue]]:
        result: Dict[IssueSeverity, List[Issue]] = {s: [] for s in IssueSeverity}
        for agent_result in self.agent_results:
            for issue in agent_result.issues:
                result[issue.severity].append(issue)
        return result
```

### JSON Export
```python
# Source: Standard Pydantic patterns
from pydantic import BaseModel

class QAReportDTO(BaseModel):
    """Data transfer object for QA reports."""
    job_id: str
    timestamp: str  # ISO format
    quality_score: float
    agent_results: List[dict]
    total_issues: int
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

def export_json(report: QAReport) -> str:
    """Export report as JSON."""
    dto = QAReportDTO(
        job_id=report.job_id,
        timestamp=report.timestamp.isoformat(),
        quality_score=report.quality_score,
        agent_results=[
            {
                'agent_name': r.agent_name,
                'score': r.score,
                'issues': [
                    {
                        'severity': i.severity.value,
                        'message': i.message,
                        'location': {
                            'file': i.location.file,
                            'line': i.location.line,
                            'column': i.location.column
                        } if i.location else None
                    }
                    for i in r.issues
                ]
            }
            for r in report.agent_results
        ],
        total_issues=report.total_issues
    )
    return dto.model_dump_json(indent=2)
```

### HTML Export with Jinja2
```python
# Source: Jinja2 documentation
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pathlib import Path

def export_html(report: QAReport, template_dir: str = "src/qa/templates") -> str:
    """Export report as HTML."""
    env = Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('report.html.j2')
    
    return template.render(
        report=report,
        severity_colors={
            'info': '#3b82f6',      # blue
            'warning': '#f59e0b',   # yellow
            'error': '#ef4444',     # red
            'critical': '#7f1d1d'   # dark red
        }
    )
```

### HTML Template Example
```html
<!-- Source: Standard HTML5 + Jinja2 -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>QA Report - {{ report.job_id }}</title>
    <style>
        body { font-family: system-ui, sans-serif; margin: 40px; }
        .score { font-size: 48px; font-weight: bold; }
        .score-high { color: #22c55e; }
        .score-medium { color: #f59e0b; }
        .score-low { color: #ef4444; }
        .issue { padding: 8px; margin: 4px 0; border-left: 4px solid; }
        .issue-info { border-color: #3b82f6; background: #eff6ff; }
        .issue-warning { border-color: #f59e0b; background: #fffbeb; }
        .issue-error { border-color: #ef4444; background: #fef2f2; }
        .issue-critical { border-color: #7f1d1d; background: #fef2f2; }
    </style>
</head>
<body>
    <h1>QA Report</h1>
    <p>Job: {{ report.job_id }}</p>
    <p>Generated: {{ report.timestamp.strftime('%Y-%m-%d %H:%M') }}</p>
    
    <div class="score score-{{ 'high' if report.quality_score >= 80 else 'medium' if report.quality_score >= 60 else 'low' }}">
        {{ "%.1f"|format(report.quality_score) }}%
    </div>
    
    <h2>Issues ({{ report.total_issues }})</h2>
    {% for severity, issues in report.issues_by_severity.items() %}
        {% if issues %}
        <h3>{{ severity.value|capitalize }} ({{ issues|length }})</h3>
        {% for issue in issues %}
        <div class="issue issue-{{ severity.value }}">
            <strong>{{ issue.location.file }}:{{ issue.location.line }}</strong>
            {{ issue.message }}
        </div>
        {% endfor %}
        {% endif %}
    {% endfor %}
</body>
</html>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Custom HTML generation | Jinja2 templates | Long-standing | Standard, maintainable |
| XML reports | JSON + HTML + Markdown | Modern preference | Better tooling, wider compatibility |
| Single score average | Weighted quality scores | Industry best practice | More accurate quality representation |

**Deprecated/outdated:**
- XML report formats: Replaced by JSON
- PDF generation: Not in scope (user can convert from HTML)

## Open Questions

1. **Score weight distribution**
   - What we know: 25% each is the CONTEXT.md default
   - What's unclear: Whether this is optimal for all mod types
   - Recommendation: Start with 25% each, make configurable

2. **Report retention policy**
   - What we know: Reports should be downloadable
   - What's unclear: How long to store reports server-side
   - Recommendation: Default 30 days, configurable

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | `pytest.ini` or `pyproject.toml` |
| Quick run command | `pytest tests/test_qa_report.py -x` |
| Full suite command | `pytest tests/qa/` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QA-06.1 | Aggregate results from all 4 agents | unit | `pytest tests/test_aggregator.py -x` | ✅ |
| QA-06.2 | Generate weighted quality score | unit | `pytest tests/test_scorer.py -x` | ✅ |
| QA-06.3 | Export to JSON format | integration | `pytest tests/test_json_exporter.py -x` | ✅ |
| QA-06.4 | Export to HTML format | integration | `pytest tests/test_html_exporter.py -x` | ✅ |
| QA-06.5 | Export to Markdown format | integration | `pytest tests/test_markdown_exporter.py -x` | ✅ |
| QA-06.6 | Color-coded severity display | unit | `pytest tests/test_templates.py -x` | ✅ |

### Sampling Rate
- **Per task commit:** `pytest tests/test_qa_report.py -x`
- **Per wave merge:** `pytest tests/qa/`
- **Phase gate:** Full suite green before execution verification

### Wave 0 Gaps
- [ ] `tests/test_aggregator.py` — covers QA-06.1
- [ ] `tests/test_scorer.py` — covers QA-06.2
- [ ] `tests/test_json_exporter.py` — covers QA-06.3
- [ ] `tests/test_html_exporter.py` — covers QA-06.4
- [ ] `tests/test_markdown_exporter.py` — covers QA-06.5
- [ ] `tests/test_templates.py` — covers QA-06.6

## Sources

### Primary (HIGH confidence)
- Pydantic documentation - Data validation and serialization
- Jinja2 documentation - Template engine
- Python dataclasses - Standard library patterns

### Secondary (MEDIUM confidence)
- QA system patterns from existing codebase
- Report generation best practices

### Tertiary (LOW confidence)
- N/A - This is a straightforward aggregation/reporting pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Well-established Python libraries
- Architecture: HIGH - Standard pluggable exporter pattern
- Pitfalls: HIGH - Common issues with known solutions

**Research date:** 2026-03-28
**Valid until:** 2026-04-28 (30 days for stable domain)