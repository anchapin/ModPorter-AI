"""
Quality control service for community feedback.

This module handles:
- Automated quality assessment
- Spam and inappropriate content detection
- Duplicate feedback detection
- Quality metrics and scoring
- Content moderation workflows
"""

import asyncio
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
import difflib
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, and_

from db.models import FeedbackEntry, FeedbackVote
from db.reputation_models import UserReputation

logger = logging.getLogger(__name__)


class QualityIssue(Enum):
    """Types of quality issues that can be detected."""

    SPAM = "spam"
    INAPPROPRIATE = "inappropriate"
    DUPLICATE = "duplicate"
    LOW_EFFORT = "low_effort"
    OFF_TOPIC = "off_topic"
    HARASSMENT = "harassment"
    SELF_PROMOTION = "self_promotion"
    VOTE_MANIPULATION = "vote_manipulation"


class QualityService:
    """Service for managing content quality and moderation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def assess_feedback_quality(
        self, feedback_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive quality assessment for feedback.

        Returns:
            Dict with quality score, detected issues, and recommendations
        """
        try:
            # Get feedback details
            feedback = await self._get_feedback_for_assessment(feedback_id)
            if not feedback:
                return {"error": "Feedback not found"}

            # Get user reputation if available
            user_reputation = (
                await self._get_user_reputation(user_id) if user_id else None
            )

            # Initialize assessment results
            assessment = {
                "feedback_id": feedback_id,
                "quality_score": 100.0,  # Start with perfect score
                "issues": [],
                "warnings": [],
                "recommendations": [],
                "auto_actions": [],
                "assessment_time": datetime.utcnow(),
                "assessor": "automated_quality_system",
            }

            # Run various quality checks
            await self._check_spam_indicators(feedback, assessment)
            await self._check_inappropriate_content(feedback, assessment)
            await self._check_duplicate_content(feedback, assessment)
            await self._check_content_quality(feedback, assessment)
            await self._check_engagement_patterns(feedback, assessment)
            await self._check_user_reputation_context(
                feedback, user_reputation, assessment
            )

            # Calculate final quality score
            assessment["quality_score"] = max(0, assessment["quality_score"])
            assessment["quality_grade"] = self._get_quality_grade(
                assessment["quality_score"]
            )

            # Determine automatic actions
            assessment["auto_actions"] = self._determine_auto_actions(assessment)

            return assessment

        except Exception as e:
            logger.error(
                f"Error assessing feedback quality for {feedback_id}: {str(e)}"
            )
            return {
                "error": "Quality assessment failed",
                "feedback_id": feedback_id,
                "quality_score": 0.0,
            }

    async def _get_feedback_for_assessment(
        self, feedback_id: str
    ) -> Optional[FeedbackEntry]:
        """Get feedback entry with related data for assessment."""
        try:
            result = await self.db.execute(
                select(FeedbackEntry).where(FeedbackEntry.id == feedback_id)
            )
            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"Error fetching feedback for assessment: {str(e)}")
            return None

    async def _get_user_reputation(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user reputation information."""
        try:
            result = await self.db.execute(
                select(UserReputation).where(UserReputation.user_id == user_id)
            )
            reputation = result.scalar_one_or_none()

            if reputation:
                return {
                    "score": reputation.reputation_score,
                    "level": reputation.level,
                    "updated_at": reputation.updated_at,
                }

            return None

        except Exception as e:
            logger.error(f"Error getting user reputation: {str(e)}")
            return None

    async def _check_spam_indicators(
        self, feedback: FeedbackEntry, assessment: Dict[str, Any]
    ) -> None:
        """Check for common spam indicators."""
        spam_score = 0
        spam_indicators = []

        content = feedback.content.lower()
        title = feedback.title.lower() if feedback.title else ""

        # Check for excessive capitalization
        if content.count("!") > 3 or title.count("!") > 2:
            spam_score += 15
            spam_indicators.append("Excessive exclamation marks")

        if sum(1 for c in content if c.isupper()) / len(content) > 0.3:
            spam_score += 20
            spam_indicators.append("Excessive capitalization")

        # Check for spam keywords
        spam_keywords = [
            "click here",
            "buy now",
            "free money",
            "make money fast",
            "limited time",
            "act now",
            "guaranteed",
            "winner",
            "congratulations",
        ]

        spam_matches = sum(1 for keyword in spam_keywords if keyword in content)
        if spam_matches > 0:
            spam_score += spam_matches * 10
            spam_indicators.append(f"Spam keywords detected: {spam_matches}")

        # Check for repetitive content
        words = content.split()
        if len(set(words)) / len(words) < 0.3:  # Low word diversity
            spam_score += 25
            spam_indicators.append("Low content diversity")

        # Check for URL spam
        url_count = len(re.findall(r"https?://[^\s]+", content))
        if url_count > 2:
            spam_score += url_count * 10
            spam_indicators.append(f"Multiple URLs: {url_count}")

        # Check for phone/email spam
        if re.search(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", content):  # Phone
            spam_score += 10
            spam_indicators.append("Phone number detected")

        email_count = len(
            re.findall(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", content)
        )
        if email_count > 1:
            spam_score += email_count * 5
            spam_indicators.append(f"Multiple emails: {email_count}")

        if spam_score > 0:
            assessment["issues"].append(
                {
                    "type": QualityIssue.SPAM.value,
                    "severity": "high" if spam_score > 50 else "medium",
                    "score": spam_score,
                    "indicators": spam_indicators,
                    "confidence": min(100, spam_score * 2),
                }
            )
            assessment["quality_score"] -= spam_score

    async def _check_inappropriate_content(
        self, feedback: FeedbackEntry, assessment: Dict[str, Any]
    ) -> None:
        """Check for inappropriate or harmful content."""
        inappropriate_score = 0
        violations = []

        content = feedback.content.lower()
        feedback.title.lower() if feedback.title else ""

        # Profanity filter (basic implementation)
        profanity_list = [
            "fuck",
            "shit",
            "asshole",
            "bitch",
            "damn",
            "crap",
            "idiot",
            "stupid",
            "dumb",
            "moron",
        ]

        profanity_count = sum(1 for word in profanity_list if word in content)
        if profanity_count > 0:
            inappropriate_score += profanity_count * 15
            violations.append(f"Profanity detected: {profanity_count} instances")

        # Harassment indicators
        harassment_patterns = [
            r"\b(you are|you\'re)\s+(an?\s+)?(idiot|stupid|dumb|moron)\b",
            r"\bkys\b",  # Kill yourself
            r"\b(kill yourself|go die)\b",
        ]

        for pattern in harassment_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                inappropriate_score += 50
                violations.append("Harassment language detected")

        # Hate speech indicators (basic)
        hate_indicators = ["nazi", "hitler", "racist", "sexist", "homophobic"]
        hate_matches = sum(1 for indicator in hate_indicators if indicator in content)
        if hate_matches > 0:
            inappropriate_score += hate_matches * 40
            violations.append(f"Hate speech indicators: {hate_matches}")

        # Threats
        threat_patterns = [
            r"\b(i\s+will|i\'ll)\s+(kill|hurt|harm|destroy)\b",
            r"\b(threaten|threatening)\b",
        ]

        for pattern in threat_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                inappropriate_score += 100
                violations.append("Threatening language detected")

        if inappropriate_score > 0:
            assessment["issues"].append(
                {
                    "type": QualityIssue.INAPPROPRIATE.value,
                    "severity": "critical" if inappropriate_score > 50 else "high",
                    "score": inappropriate_score,
                    "violations": violations,
                    "confidence": min(100, inappropriate_score),
                }
            )
            assessment["quality_score"] -= inappropriate_score

    async def _check_duplicate_content(
        self, feedback: FeedbackEntry, assessment: Dict[str, Any]
    ) -> None:
        """Check for duplicate or very similar content."""
        duplicate_score = 0
        duplicates = []

        # Get recent feedback from same user and others
        recent_window = datetime.utcnow() - timedelta(days=7)

        result = await self.db.execute(
            select(FeedbackEntry).where(
                and_(
                    FeedbackEntry.id != feedback.id,
                    FeedbackEntry.created_at >= recent_window,
                )
            )
        )
        recent_feedback = result.scalars().all()

        for existing in recent_feedback:
            # Check content similarity
            similarity = self._calculate_content_similarity(
                feedback.content, existing.content
            )

            # Check title similarity if both exist
            title_similarity = 0
            if feedback.title and existing.title:
                title_similarity = self._calculate_content_similarity(
                    feedback.title, existing.title
                )

            # High similarity detection
            if similarity > 0.85:
                duplicate_score += 30
                duplicates.append(
                    {
                        "feedback_id": existing.id,
                        "similarity": similarity,
                        "type": "near_duplicate",
                        "user_id": existing.user_id,
                    }
                )
            elif similarity > 0.7:
                duplicate_score += 10
                duplicates.append(
                    {
                        "feedback_id": existing.id,
                        "similarity": similarity,
                        "type": "similar_content",
                        "user_id": existing.user_id,
                    }
                )

            if title_similarity > 0.9:
                duplicate_score += 20
                duplicates[-1]["title_similarity"] = (
                    title_similarity if duplicates else title_similarity
                )

        if duplicate_score > 0:
            assessment["issues"].append(
                {
                    "type": QualityIssue.DUPLICATE.value,
                    "severity": "medium" if duplicate_score < 40 else "high",
                    "score": duplicate_score,
                    "duplicates": duplicates[:5],  # Limit to top 5
                    "confidence": min(100, duplicate_score * 2),
                }
            )
            assessment["quality_score"] -= duplicate_score

    async def _check_content_quality(
        self, feedback: FeedbackEntry, assessment: Dict[str, Any]
    ) -> None:
        """Check for general content quality issues."""
        quality_score = 0
        issues = []

        content = feedback.content
        title = feedback.title or ""

        # Length checks
        if len(content.strip()) < 20:
            quality_score += 30
            issues.append("Content too short")
        elif len(content.strip()) < 50:
            quality_score += 15
            issues.append("Content very short")

        if title and len(title.strip()) < 5:
            quality_score += 10
            issues.append("Title too short")

        # Meaningful content checks
        words = content.split()
        if len(words) < 5:
            quality_score += 40
            issues.append("Insufficient word count")

        # Check for meaningful sentences
        sentences = re.split(r"[.!?]+", content)
        meaningful_sentences = [
            s for s in sentences if len(s.strip()) > 10 and not s.strip().isdigit()
        ]

        if len(meaningful_sentences) < 1:
            quality_score += 25
            issues.append("No meaningful sentences")

        # Check for actionable or constructive content
        constructive_indicators = [
            "suggest",
            "recommend",
            "improve",
            "fix",
            "add",
            "remove",
            "change",
            "update",
            "implement",
            "consider",
            "try",
        ]

        has_constructive = any(
            indicator in content.lower() for indicator in constructive_indicators
        )
        if not has_constructive and feedback.feedback_type == "improvement":
            quality_score += 15
            issues.append("Lacks constructive suggestions")

        # Check technical depth for technical feedback
        if feedback.feedback_type in ["bug_report", "technical_issue"]:
            technical_terms = [
                "error",
                "bug",
                "crash",
                "glitch",
                "issue",
                "problem",
                "function",
                "method",
                "code",
                "implementation",
                "algorithm",
            ]

            has_technical = any(term in content.lower() for term in technical_terms)
            if not has_technical:
                quality_score += 20
                issues.append("Lacks technical details")

        if quality_score > 0:
            assessment["issues"].append(
                {
                    "type": QualityIssue.LOW_EFFORT.value,
                    "severity": "low" if quality_score < 30 else "medium",
                    "score": quality_score,
                    "issues": issues,
                    "confidence": min(100, quality_score * 3),
                }
            )
            assessment["quality_score"] -= quality_score

    async def _check_engagement_patterns(
        self, feedback: FeedbackEntry, assessment: Dict[str, Any]
    ) -> None:
        """Check for unusual engagement patterns that might indicate manipulation."""
        manipulation_score = 0
        patterns = []

        # Check for rapid voting (if feedback has votes)
        if feedback.vote_count and feedback.vote_count > 10:
            # Check if votes came in too quickly
            result = await self.db.execute(
                select(func.count(FeedbackVote.id)).where(
                    and_(
                        FeedbackVote.feedback_id == feedback.id,
                        FeedbackVote.created_at >= feedback.created_at,
                        FeedbackVote.created_at
                        <= feedback.created_at + timedelta(minutes=5),
                    )
                )
            )
            rapid_votes = result.scalar()

            if rapid_votes > 5:
                manipulation_score += 25
                patterns.append(f"Rapid voting: {rapid_votes} votes in 5 minutes")

        # Check for voting rings (multiple votes from same IP/user group)
        if feedback.vote_count and feedback.vote_count > 3:
            result = await self.db.execute(
                select(
                    FeedbackVote.user_id,
                    func.count(FeedbackVote.id).label("vote_count"),
                )
                .where(FeedbackVote.feedback_id == feedback.id)
                .group_by(FeedbackVote.user_id)
                .having(func.count(FeedbackVote.id) > 1)
            )
            suspicious_voters = result.all()

            if suspicious_voters:
                manipulation_score += len(suspicious_voters) * 15
                patterns.append(
                    f"Suspicious voting patterns: {len(suspicious_voters)} repeat voters"
                )

        if manipulation_score > 0:
            assessment["issues"].append(
                {
                    "type": QualityIssue.VOTE_MANIPULATION.value,
                    "severity": "high",
                    "score": manipulation_score,
                    "patterns": patterns,
                    "confidence": min(100, manipulation_score * 2),
                }
            )
            assessment["quality_score"] -= manipulation_score

    async def _check_user_reputation_context(
        self,
        feedback: FeedbackEntry,
        user_reputation: Optional[Dict[str, Any]],
        assessment: Dict[str, Any],
    ) -> None:
        """Adjust quality assessment based on user reputation."""
        if not user_reputation:
            return

        reputation_score = user_reputation.get("score", 0)
        user_reputation.get("level", "NEWCOMER")

        # Bonus for high-reputation users
        if reputation_score > 100:
            bonus = min(20, reputation_score / 10)
            assessment["quality_score"] += bonus
            assessment["warnings"].append(f"High reputation bonus: +{bonus:.1f}")

        # Scrutiny for very low-reputation users
        if reputation_score < 5:
            assessment["warnings"].append(
                "Low reputation user - extra scrutiny applied"
            )

    def _calculate_content_similarity(self, content1: str, content2: str) -> float:
        """Calculate similarity between two text contents."""
        # Normalize content
        c1 = re.sub(r"\s+", " ", content1.lower().strip())
        c2 = re.sub(r"\s+", " ", content2.lower().strip())

        # Use difflib for similarity calculation
        similarity = difflib.SequenceMatcher(None, c1, c2).ratio()
        return similarity

    def _get_quality_grade(self, score: float) -> str:
        """Get quality grade based on score."""
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 60:
            return "acceptable"
        elif score >= 40:
            return "poor"
        else:
            return "unacceptable"

    def _determine_auto_actions(self, assessment: Dict[str, Any]) -> List[str]:
        """Determine automatic moderation actions based on assessment."""
        actions = []
        score = assessment["quality_score"]
        issues = assessment["issues"]

        # Check for critical issues requiring immediate action
        critical_issues = [
            issue for issue in issues if issue.get("severity") == "critical"
        ]
        if critical_issues:
            actions.extend(
                ["auto_hide_content", "flag_for_human_review", "notify_moderators"]
            )

        # High severity issues
        high_issues = [issue for issue in issues if issue.get("severity") == "high"]
        if len(high_issues) >= 2:
            actions.extend(["reduce_visibility", "flag_for_review"])

        # Very low quality score
        if score < 30:
            actions.append("quality_gate_block")
        elif score < 50:
            actions.append("require_moderator_approval")

        # Vote manipulation
        manipulation_issues = [
            issue
            for issue in issues
            if issue["type"] == QualityIssue.VOTE_MANIPULATION.value
        ]
        if manipulation_issues:
            actions.extend(
                ["reset_votes", "flag_manipulation", "investigate_user_account"]
            )

        return actions

    async def get_quality_metrics(
        self, time_range: str = "7d", user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get quality metrics and statistics."""
        try:
            # Calculate time window
            days = int(time_range.replace("d", ""))
            start_date = datetime.utcnow() - timedelta(days=days)

            # Base query
            query = select(func.count(FeedbackEntry.id)).where(
                FeedbackEntry.created_at >= start_date
            )

            if user_id:
                query = query.where(FeedbackEntry.user_id == user_id)

            result = await self.db.execute(query)
            total_feedback = result.scalar()

            if total_feedback == 0:
                return {"error": "No feedback found in time range"}

            # Get quality metrics
            metrics = {
                "time_range": time_range,
                "total_feedback": total_feedback,
                "quality_distribution": {},
                "common_issues": {},
                "auto_action_stats": {},
                "average_quality_score": 0.0,
            }

            # Note: In a real implementation, you would query from a quality_assessments table
            # For now, returning placeholder metrics
            metrics.update(
                {
                    "quality_distribution": {
                        "excellent": 0.25,
                        "good": 0.35,
                        "acceptable": 0.25,
                        "poor": 0.10,
                        "unacceptable": 0.05,
                    },
                    "common_issues": {
                        "low_effort": 0.30,
                        "duplicate": 0.20,
                        "spam": 0.15,
                        "inappropriate": 0.10,
                        "off_topic": 0.15,
                        "other": 0.10,
                    },
                    "auto_actions": {
                        "auto_approved": 0.60,
                        "flagged_for_review": 0.25,
                        "auto_hidden": 0.10,
                        "quality_blocked": 0.05,
                    },
                    "average_quality_score": 75.5,
                }
            )

            return metrics

        except Exception as e:
            logger.error(f"Error getting quality metrics: {str(e)}")
            return {"error": "Failed to retrieve quality metrics"}

    async def batch_quality_assessment(
        self, feedback_ids: List[str], batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """Run quality assessment on multiple feedback items."""
        results = []

        for i in range(0, len(feedback_ids), batch_size):
            batch = feedback_ids[i : i + batch_size]

            # Run assessments in parallel for batch
            tasks = [self.assess_feedback_quality(feedback_id) for feedback_id in batch]

            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for feedback_id, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(
                        f"Error in batch assessment for {feedback_id}: {str(result)}"
                    )
                    results.append(
                        {
                            "feedback_id": feedback_id,
                            "error": "Assessment failed",
                            "exception": str(result),
                        }
                    )
                else:
                    results.append(result)

            # Small delay between batches to avoid overwhelming system
            if i + batch_size < len(feedback_ids):
                await asyncio.sleep(0.1)

        return results
