# Phase 15-05: User Correction Learning - Research

**Researched:** 2026-03-27
**Domain:** RAG feedback learning systems, user correction storage, adaptive knowledge bases
**Confidence:** HIGH

## Summary

Phase 15-05 implements User Correction Learning to enable the RAG system to learn from user feedback on conversion outputs. This builds on existing infrastructure (ConversionFeedback, PatternSubmission) to create a correction pipeline that stores user corrections, validates them through an approval workflow, and applies approved corrections to improve future conversions through re-ranking.

The phase requires creating a new CorrectionSubmission database model, feedback API endpoints, correction storage module, validation workflow, and feedback-driven re-ranking integration with the existing hybrid search engine.

**Primary recommendation:** Implement CorrectionSubmission model following PatternSubmission schema patterns, create async CRUD operations in correction_store.py, integrate FeedbackReranker into HybridSearchEngine with optional parameter, and reuse existing approval workflow patterns.

## User Constraints (from CONTEXT.md)

### Locked Decisions
- PostgreSQL + pgvector for vector storage (production)
- sentence-transformers/all-MiniLM-L6-v2 for embeddings (default)
- Async SQLAlchemy for database operations
- FastAPI for backend API
- Must maintain backward compatibility with existing search API
- Reuse existing ConversionFeedback model for correction storage
- Reuse PatternSubmission approval workflow pattern

### Discretion Areas
- Feedback collection interface design
- Correction validation algorithm
- Knowledge base update frequency and batching strategy
- Re-ranking algorithm based on correction patterns
- Performance optimization vs. accuracy tradeoffs

### Deferred Ideas (OUT OF SCOPE)
- Real-time correction application (use batch processing)
- Multi-user correction aggregation (defer to future phase)
- LLM-based correction validation (manual review required)

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RAG-5.1 | User feedback collection system for conversion corrections | Feedback API endpoints + CorrectionStore |
| RAG-5.2 | Correction validation, approval workflow, and knowledge base update pipeline | ValidationWorkflow + FeedbackReranker |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | Latest | REST API endpoints | Existing project standard |
| SQLAlchemy (async) | 2.x | Database ORM | Existing project standard |
| PostgreSQL + pgvector | Latest | Relational + vector storage | Locked in CONTEXT.md |
| Pydantic | 2.x | Request/Response validation | Existing project standard |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 7.x+ | Unit testing | All new Python code |
| pytest-asyncio | Latest | Async test support | Testing async functions |
| aiosqlite | Latest | Async SQLite for tests | Unit test database |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom correction storage | Reuse ConversionFeedback | CorrectionSubmission provides richer schema (original_output, corrected_output, rationale, status workflow) |

## Architecture Patterns

### Recommended Project Structure
```
backend/src/
├── api/
│   ├── feedback.py           # NEW: Feedback API endpoints
│   └── embeddings.py         # MODIFIED: Add optional feedback param
├── db/
│   ├── models.py             # MODIFIED: Add CorrectionSubmission
│   └── crud.py              # MODIFIED: Add correction CRUD

ai-engine/
├── learning/
│   ├── __init__.py          # NEW: Export correction modules
│   ├── correction_store.py  # NEW: Correction storage logic
│   └── validation_workflow.py # NEW: Validation & approval
└── search/
    └── feedback_reranker.py  # NEW: Feedback-driven re-ranking

backend/tests/unit/
├── test_feedback_api.py      # NEW: Feedback API tests

ai-engine/tests/unit/
└── test_correction_learning.py # NEW: Learning module tests
```

### Pattern 1: Async CRUD with SQLAlchemy
**What:** Standard async database operations following existing project patterns
**When to use:** All database operations in correction_store.py
**Example:**
```python
# Source: Existing patterns in backend/src/db/crud.py
async def add_correction(self, correction: CorrectionSubmission) -> CorrectionSubmission:
    db.add(correction)
    await db.commit()
    await db.refresh(correction)
    return correction
```

### Pattern 2: Approval Workflow (Reuse PatternSubmission)
**What:** Status-based workflow: pending → approved/rejected → applied
**When to use:** Correction validation following existing PatternSubmission pattern
**Example:**
```python
# Source: Adapted from PatternSubmission in backend/src/db/models.py
class CorrectionSubmission(Base):
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"))  # pending, approved, rejected, applied
    reviewed_by: Mapped[Optional[str]]
    review_notes: Mapped[Optional[str]]
    reviewed_at: Mapped[Optional[datetime]]
    applied_at: Mapped[Optional[datetime]]
    embedding_updated: Mapped[bool] = mapped_column(Boolean, server_default=text("'false'"))
```

### Pattern 3: Optional Re-ranking Integration
**What:** Extend existing search with optional feedback boost parameter
**When to use:** Integrating FeedbackReranker into HybridSearchEngine
**Example:**
```python
# Source: Based on existing HybridSearchEngine interface
async def search(
    self,
    query: str,
    top_k: int = 10,
    use_feedback_boost: bool = True,  # NEW: Optional parameter
    user_id: Optional[str] = None     # NEW: User context
) -> List[SearchResult]:
    results = await self._base_search(query, top_k)
    if use_feedback_boost:
        reranker = FeedbackReranker()
        results = await reranker.rerank_with_feedback(query, results, user_id)
    return results
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Status workflow | Custom approval logic | Reuse PatternSubmission pattern | Already proven, consistent with existing code |
| Database schema | New table design from scratch | Extend existing models.py | Consistent with project patterns |
| API patterns | Custom endpoint structure | Follow embeddings.py patterns | Maintains consistency |
| Async patterns | Synchronous database calls | Async SQLAlchemy | Matches existing async architecture |

**Key insight:** The project already has ConversionFeedback and PatternSubmission models that handle similar feedback/correction workflows. Building a custom solution would introduce inconsistency and duplicate code.

## Common Pitfalls

### Pitfall 1: Synchronous Database Calls in Async Context
**What goes wrong:** Deadlocks, blocking event loop, poor performance
**Why it happens:** Forgetting to use `await` with async SQLAlchemy operations
**How to avoid:** Always use `async with` for sessions, `await` for all queries
**Warning signs:** Tests pass locally but hang in production, performance degrades under load

### Pitfall 2: Breaking Existing Search API
**What goes wrong:** Existing integrations fail, backward compatibility broken
**Why it happens:** Changing method signatures without optional parameters
**How to avoid:** Add new parameters with default values, maintain backward compatibility
**Warning signs:** Type errors when existing code calls search without new parameters

### Pitfall 3: Validation Too Strict or Too Lenient
**What goes wrong:** Valid corrections rejected OR invalid corrections approved
**Why it happens:** Over-engineering validation or no validation at all
**How to avoid:** Balance: check for obvious issues (empty, identical), rely on human review for quality
**Warning signs:** High rejection rate, user complaints about rejected valid corrections

### Pitfall 4: Missing Indexes on Status Columns
**What goes wrong:** Slow queries when listing pending corrections
**Why it happens:** Forgetting to add `index=True` on status columns
**How to avoid:** Add indexes on frequently filtered columns (status, job_id, user_id)
**Warning signs:** Slow queries with WHERE status='pending', check EXPLAIN ANALYZE

## Code Examples

### CorrectionSubmission Model
```python
# Source: Adapted from existing PatternSubmission and ConversionFeedback models
# backend/src/db/models.py

class CorrectionSubmission(Base):
    __tablename__ = "correction_submissions"
    __table_args__ = {"extend_existing": True}
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversion_jobs.id"), nullable=False, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True, index=True)
    
    # Original conversion output
    original_output: Mapped[str] = mapped_column(Text, nullable=False)
    original_chunk_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    
    # User's correction
    corrected_output: Mapped[str] = mapped_column(Text, nullable=False)
    correction_rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Status workflow
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'pending'"), index=True)  # pending, approved, rejected, applied
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    reviewed_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    review_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    # Apply tracking
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    embedding_updated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("'false'"))
    
    # Relationships
    job = relationship("ConversionJob", backref="correction_submissions")
```

### Feedback API Endpoints Pattern
```python
# Source: Based on existing patterns in backend/src/api/embeddings.py
# backend/src/api/feedback.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from db.base import get_db

router = APIRouter(prefix="/api/feedback", tags=["feedback"])

class CorrectionSubmitRequest(BaseModel):
    job_id: str
    original_output: str
    corrected_output: str
    correction_rationale: Optional[str] = None
    original_chunk_id: Optional[str] = None

class CorrectionReviewRequest(BaseModel):
    status: str  # "approved" or "rejected"
    review_notes: Optional[str] = None

@router.post("/corrections")
async def submit_correction(
    request: CorrectionSubmitRequest,
    db: AsyncSession = Depends(get_db)
):
    """Submit a correction for a conversion output."""
    # Implementation
    pass

@router.get("/corrections")
async def list_corrections(
    job_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db)
):
    """List corrections with optional filters."""
    # Implementation
    pass

@router.put("/corrections/{correction_id}/review")
async def review_correction(
    correction_id: str,
    request: CorrectionReviewRequest,
    db: AsyncSession = Depends(get_db)
):
    """Review a correction (approve or reject)."""
    # Implementation
    pass
```

### FeedbackReranker Class
```python
# Source: Based on research on RAG feedback loops
# ai-engine/search/feedback_reranker.py

from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
import uuid

@dataclass
class FeedbackBoost:
    chunk_id: uuid.UUID
    boost_score: float
    correction_count: int
    last_correction_date: Optional[datetime]

class FeedbackReranker:
    """Re-rank search results based on user correction patterns."""
    
    def __init__(self, decay_factor: float = 0.95):
        self.decay_factor = decay_factor
        self.status_weights = {
            "approved": 1.0,
            "pending": 0.3,
            "rejected": -0.5,
            "applied": 1.2
        }
    
    async def rerank_with_feedback(
        self,
        query: str,
        initial_results: List[SearchResult],
        user_id: Optional[str] = None
    ) -> List[SearchResult]:
        """Re-rank results incorporating correction feedback."""
        if not initial_results:
            return initial_results
        
        # 1. Get chunk IDs from results
        chunk_ids = [r.chunk_id for r in initial_results]
        
        # 2. Fetch feedback boost for these chunks
        feedback_boosts = await self.get_feedback_boost(chunk_ids)
        boost_map = {fb.chunk_id: fb for fb in feedback_boosts}
        
        # 3. Apply boost to scores
        for result in initial_results:
            if result.chunk_id in boost_map:
                boost = boost_map[result.chunk_id]
                result.relevance_score += boost.boost_score
        
        # 4. Re-sort by updated scores
        return sorted(initial_results, key=lambda r: r.relevance_score, reverse=True)
    
    async def get_feedback_boost(
        self,
        chunk_ids: List[uuid.UUID]
    ) -> List[FeedbackBoost]:
        """Get feedback boost scores for chunks."""
        # Query correction_submissions for these chunks
        # Calculate boost: sum of (status_weight * recency_factor)
        pass
    
    def _calculate_boost_score(
        self,
        correction_count: int,
        last_correction_date: Optional[datetime],
        status_weights: List[float]
    ) -> float:
        """Calculate boost score with recency decay."""
        if not last_correction_date:
            return 0.0
        
        days_since = (datetime.now() - last_correction_date).days
        recency_factor = self.decay_factor ** days_since
        return sum(status_weights) * correction_count * recency_factor
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x + pytest-asyncio |
| Config file | pyproject.toml (root) or pytest.ini |
| Quick run command | `pytest backend/tests/unit/test_feedback_api.py -x -v` |
| Full suite command | `pytest backend/tests/unit/ ai-engine/tests/unit/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RAG-5.1 | Submit correction via API | unit | `pytest backend/tests/unit/test_feedback_api.py::test_submit_correction -x` | ❌ Wave 0 |
| RAG-5.1 | List corrections with filters | unit | `pytest backend/tests/unit/test_feedback_api.py::test_list_corrections -x` | ❌ Wave 0 |
| RAG-5.1 | Review correction (approve/reject) | unit | `pytest backend/tests/unit/test_feedback_api.py::test_review_correction -x` | ❌ Wave 0 |
| RAG-5.2 | Validate correction (valid) | unit | `pytest ai-engine/tests/unit/test_correction_learning.py::test_validator_valid -x` | ❌ Wave 0 |
| RAG-5.2 | Validate correction (invalid) | unit | `pytest ai-engine/tests/unit/test_correction_learning.py::test_validator_invalid -x` | ❌ Wave 0 |
| RAG-5.2 | Feedback re-ranking | unit | `pytest ai-engine/tests/unit/test_correction_learning.py::test_feedback_reranker -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest {task_test_file} -x -v`
- **Per wave merge:** `pytest backend/tests/unit/ ai-engine/tests/unit/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/unit/test_feedback_api.py` — covers RAG-5.1 (feedback API)
- [ ] `ai-engine/tests/unit/test_correction_learning.py` — covers RAG-5.2 (validation & re-ranking)
- [ ] `backend/tests/conftest.py` — shared fixtures (exists, verify coverage)
- [ ] Framework install: `pip install pytest pytest-asyncio aiosqlite` — if none detected

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Static RAG | Adaptive RAG with feedback | Phase 15-05 | System learns from user corrections |
| Single-pass search | Re-ranked with feedback | Phase 15-05 | Improved relevance from user signals |
| Batch-only corrections | Approval workflow | Phase 15-05 | Quality control before application |

**Deprecated/outdated:**
- Hard-coded knowledge base updates: Replaced with user-driven correction pipeline
- Single-user feedback: Now supports multi-user feedback aggregation through correction patterns

## Open Questions

1. **Should corrections automatically update embeddings or require manual trigger?**
   - What we know: Pattern is pending → approved → applied workflow
   - What's unclear: Whether to auto-apply on approval or require manual trigger
   - Recommendation: Require manual `/apply` endpoint for safety; auto-apply can be added in future phase

2. **How to handle conflicting corrections from different users?**
   - What we know: Multiple corrections can exist for same chunk
   - What's unclear: Which correction takes precedence
   - Recommendation: Use approval timestamp + count as tiebreaker; document in phase plan

3. **Should correction embeddings replace or supplement original embeddings?**
   - What we know: Need to store both original and corrected output
   - What's unclear: Whether to replace original vector or add corrected version
   - Recommendation: Add corrected version as new embedding; keep original for fallback

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL | Data layer | ✓ | Latest | — |
| pgvector | Vector operations | ✓ | Latest | — |
| pytest | Testing | ✓ | 7.x+ | — |
| pytest-asyncio | Async tests | ✓ | Latest | — |

**Missing dependencies with no fallback:**
- None identified

**Missing dependencies with fallback:**
- None identified

## Sources

### Primary (HIGH confidence)
- Context7: FastAPI async patterns, SQLAlchemy async operations
- Existing codebase: backend/src/db/models.py (ConversionFeedback, PatternSubmission)
- Existing codebase: backend/src/api/knowledge_base.py (approval workflow patterns)

### Secondary (MEDIUM confidence)
- WebSearch: "Building Feedback Loops in RAG for Continuous Learning" - patterns for RAG feedback
- WebSearch: "Self-Corrective RAG with LangGraph" - correction validation approaches
- Blog posts: RAG user feedback systems best practices

### Tertiary (LOW confidence)
- WebSearch only: Specific algorithm details for boost calculation (need verification)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Existing project standards confirmed in CONTEXT.md
- Architecture: HIGH - Based on existing patterns from PatternSubmission and ConversionFeedback
- Pitfalls: MEDIUM - Based on general async Python patterns, need to verify against project specifics

**Research date:** 2026-03-27
**Valid until:** 2026-04-26 (30 days for stable patterns)
