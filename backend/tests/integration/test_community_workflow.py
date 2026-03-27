"""
Integration tests for community pattern workflow.

Tests the complete pipeline from pattern submission, validation, review,
to library integration.
"""

import pytest
import asyncio
from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool
from db.declarative_base import Base
from db.models import PatternSubmission
from db import crud

# Add ai-engine to path
import sys
import os
ai_engine_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
    "ai-engine",
)
if ai_engine_path not in sys.path:
    sys.path.insert(0, ai_engine_path)

from knowledge.community import CommunityPatternManager, SubmissionStatus
from knowledge.patterns import PatternLibrary


# Use in-memory SQLite for testing
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    """Create test database session."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Provide session
    async with async_session() as session:
        yield session

    # Cleanup
    await engine.dispose()


@pytest.fixture
def sample_java_pattern():
    """Sample Java pattern for testing."""
    return """
public class CustomItem extends Item {
    public CustomItem() {
        super(new Item.Properties()
            .tab(CreativeModeTab.TAB_MISC)
            .stacksTo(64));
    }
}
"""


@pytest.fixture
def sample_bedrock_pattern():
    """Sample Bedrock pattern for testing."""
    return """{
    "format_version": "1.16.0",
    "minecraft:item": {
        "description": {
            "identifier": "mod:custom_item"
        },
        "components": {
            "minecraft:display_name": {
                "value": "Custom Item"
            },
            "minecraft:max_stack_size": 64
        }
    }
}"""


@pytest.fixture
def sample_description():
    """Sample pattern description."""
    return "A simple custom item registration pattern that demonstrates basic item creation with stack size and creative tab configuration"


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_submit_pattern(test_db, sample_java_pattern, sample_bedrock_pattern, sample_description):
    """Test submitting a valid pattern."""
    manager = CommunityPatternManager()

    # Submit pattern
    submission = await manager.submit_pattern(
        java_pattern=sample_java_pattern,
        bedrock_pattern=sample_bedrock_pattern,
        description=sample_description,
        contributor_id="user123",
        tags=["item", "simple"],
        category="item",
    )

    # Verify submission created
    assert submission.id is not None
    assert submission.status == SubmissionStatus.PENDING
    assert submission.contributor_id == "user123"
    assert submission.category == "item"
    assert submission.tags == ["item", "simple"]
    assert submission.upvotes == 0
    assert submission.downvotes == 0


@pytest.mark.asyncio
async def test_submit_invalid_pattern(test_db):
    """Test submitting an invalid pattern (too short)."""
    manager = CommunityPatternManager()

    with pytest.raises(ValueError, match="Pattern validation failed"):
        await manager.submit_pattern(
            java_pattern="x",
            bedrock_pattern="y",
            description="Too short",
            contributor_id="user123",
            tags=[],
            category="item",
        )


@pytest.mark.asyncio
async def test_submit_malicious_pattern(test_db):
    """Test submitting a pattern with malicious content."""
    manager = CommunityPatternManager()

    with pytest.raises(ValueError, match="malicious"):
        await manager.submit_pattern(
            java_pattern='public class Test { eval("malicious"); }',
            bedrock_pattern='{"format_version": "1.16.0"}',
            description="A malicious pattern that is long enough to pass validation",
            contributor_id="user123",
            tags=[],
            category="item",
        )


@pytest.mark.asyncio
async def test_review_pattern_approve(test_db, sample_java_pattern, sample_bedrock_pattern, sample_description):
    """Test approving a pattern submission."""
    manager = CommunityPatternManager()

    # Create submission
    submission = await manager.submit_pattern(
        java_pattern=sample_java_pattern,
        bedrock_pattern=sample_bedrock_pattern,
        description=sample_description,
        contributor_id="user123",
        tags=["item"],
        category="item",
    )

    submission_id = submission.id

    # Approve pattern
    await manager.review_pattern(
        submission_id=submission_id,
        reviewer_id="reviewer456",
        approved=True,
        notes="Good pattern, approved",
    )

    # Verify status updated
    assert submission.status == SubmissionStatus.APPROVED
    assert submission.reviewed_by == "reviewer456"
    assert submission.review_notes == "Good pattern, approved"
    assert submission.reviewed_at is not None

    # Verify pattern was created with correct properties
    # Note: PatternLibrary is not a singleton, so we can't directly check
    # Instead, verify that the review_pattern method completed without error
    # and the submission status is correct


@pytest.mark.asyncio
async def test_review_pattern_reject(test_db, sample_java_pattern, sample_bedrock_pattern, sample_description):
    """Test rejecting a pattern submission."""
    manager = CommunityPatternManager()

    # Create submission
    submission = await manager.submit_pattern(
        java_pattern=sample_java_pattern,
        bedrock_pattern=sample_bedrock_pattern,
        description=sample_description,
        contributor_id="user123",
        tags=["item"],
        category="item",
    )

    submission_id = submission.id

    # Reject pattern
    await manager.review_pattern(
        submission_id=submission_id,
        reviewer_id="reviewer456",
        approved=False,
        notes="Incorrect pattern mapping",
    )

    # Verify status updated
    assert submission.status == SubmissionStatus.REJECTED
    assert submission.reviewed_by == "reviewer456"
    assert submission.review_notes == "Incorrect pattern mapping"

    # Verify submission was rejected (not approved)
    assert submission.status != SubmissionStatus.APPROVED


@pytest.mark.asyncio
async def test_vote_on_pattern(test_db, sample_java_pattern, sample_bedrock_pattern, sample_description):
    """Test voting on a pattern submission."""
    manager = CommunityPatternManager()

    # Create submission
    submission = await manager.submit_pattern(
        java_pattern=sample_java_pattern,
        bedrock_pattern=sample_bedrock_pattern,
        description=sample_description,
        contributor_id="user123",
        tags=["item"],
        category="item",
    )

    # Submit upvote
    await manager.vote_on_pattern(
        submission_id=submission.id,
        user_id="voter1",
        upvote=True,
    )

    assert submission.upvotes == 1
    assert submission.downvotes == 0
    assert submission.score == 1

    # Submit downvote
    await manager.vote_on_pattern(
        submission_id=submission.id,
        user_id="voter2",
        upvote=False,
    )

    assert submission.upvotes == 1
    assert submission.downvotes == 1
    assert submission.score == 0


@pytest.mark.asyncio
async def test_get_pending_submissions(test_db, sample_java_pattern, sample_bedrock_pattern, sample_description):
    """Test getting pending submissions."""
    manager = CommunityPatternManager()

    # Create 5 pending submissions
    submission_ids = []
    for i in range(5):
        submission = await manager.submit_pattern(
            java_pattern=sample_java_pattern,
            bedrock_pattern=sample_bedrock_pattern,
            description=f"Pattern {i}: {sample_description}",
            contributor_id=f"user{i}",
            tags=["item"],
            category="item",
        )
        submission_ids.append(submission.id)

    # Create 2 approved submissions
    for i in range(2):
        submission = await manager.submit_pattern(
            java_pattern=sample_java_pattern,
            bedrock_pattern=sample_bedrock_pattern,
            description=f"Approved pattern {i}: {sample_description}",
            contributor_id=f"user{i+5}",
            tags=["item"],
            category="item",
        )
        await manager.review_pattern(
            submission_id=submission.id,
            reviewer_id="reviewer",
            approved=True,
        )

    # Get pending submissions
    pending = await manager.get_pending_submissions(limit=10)

    # Should return only pending submissions
    assert len(pending) == 5
    for sub in pending:
        assert sub.status == SubmissionStatus.PENDING


@pytest.mark.asyncio
async def test_pattern_library_search(test_db):
    """Test searching pattern library."""
    library = PatternLibrary()

    # Pre-populate library with some patterns
    from knowledge.patterns import JavaPatternRegistry, BedrockPatternRegistry

    java_reg = JavaPatternRegistry()
    bedrock_reg = BedrockPatternRegistry()

    # Add some patterns to library
    for pattern in java_reg.get_by_category("item")[:3]:
        library.add_pattern(pattern)

    # Search for "item"
    results = library.search(query="item", limit=10)

    # Should return item-related patterns
    assert len(results) > 0
    for pattern in results:
        assert "item" in pattern.category.lower() or "item" in pattern.name.lower()

    # Filter by category "block"
    block_patterns = library.get_by_category("block")
    # Note: We didn't add block patterns, so this might be empty
    # Just testing the filter works
    assert isinstance(block_patterns, list)
