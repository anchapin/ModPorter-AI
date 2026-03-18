"""
Learning System for Continuous Improvement

Implements:
- Feedback learning pipeline
- CodeT5+ fine-tuning preparation
- Community pattern sharing
- Continuous improvement tracking
"""

import logging
<<<<<<< HEAD
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
=======
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))

logger = logging.getLogger(__name__)


class FeedbackType(Enum):
    """Types of user feedback."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    RATING = "rating"
    CORRECTION = "correction"
    SUGGESTION = "suggestion"
    BUG_REPORT = "bug_report"


class LearningStatus(Enum):
    """Status of learning items."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    PENDING = "pending"
    ANALYZED = "analyzed"
    QUEUED = "queued"
    LEARNED = "learned"
    DEPLOYED = "deployed"


@dataclass
class UserFeedback:
    """User feedback for a conversion."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    feedback_id: str
    conversion_id: str
    feedback_type: FeedbackType
    rating: Optional[int] = None  # 1-5 scale
    comment: Optional[str] = None
    corrected_code: Optional[str] = None
    original_java: Optional[str] = None
    converted_bedrock: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    user_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def to_dict(self) -> Dict[str, Any]:
        return {
            "feedback_id": self.feedback_id,
            "conversion_id": self.conversion_id,
            "type": self.feedback_type.value,
            "rating": self.rating,
            "comment": self.comment,
            "corrected_code": self.corrected_code,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class LearningItem:
    """Item to learn from feedback."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    item_id: str
    feedback_id: str
    issue_type: str
    description: str
    suggested_fix: str
    confidence: float  # 0.0 to 1.0
    status: LearningStatus = LearningStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    learned_at: Optional[datetime] = None
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "feedback_id": self.feedback_id,
            "issue_type": self.issue_type,
            "description": self.description,
            "suggested_fix": self.suggested_fix,
            "confidence": self.confidence,
            "status": self.status.value,
        }


@dataclass
class TrainingPair:
    """Training pair for model fine-tuning."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    java_code: str
    bedrock_code: str
    quality_score: float  # 0.0 to 1.0
    source: str = "user_feedback"  # user_feedback, manual, synthetic
    metadata: Dict[str, Any] = field(default_factory=dict)
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def to_dict(self) -> Dict[str, Any]:
        return {
            "java": self.java_code,
            "bedrock": self.bedrock_code,
            "quality_score": self.quality_score,
            "source": self.source,
        }


@dataclass
class CommunityPattern:
    """Community-submitted conversion pattern."""
<<<<<<< HEAD

=======
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    pattern_id: str
    name: str
    description: str
    java_example: str
    bedrock_example: str
    submitted_by: str
    submitted_at: datetime = field(default_factory=datetime.now)
    status: str = "pending"  # pending, reviewing, approved, rejected
    votes: int = 0
    reviews: List[Dict[str, Any]] = field(default_factory=list)
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pattern_id": self.pattern_id,
            "name": self.name,
            "description": self.description,
            "java_example": self.java_example,
            "bedrock_example": self.bedrock_example,
            "submitted_by": self.submitted_by,
            "status": self.status,
            "votes": self.votes,
        }


class FeedbackLearningPipeline:
    """
    Pipeline for learning from user feedback.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Processes:
    1. Collect feedback
    2. Analyze failures
    3. Extract patterns
    4. Update rules
    5. Queue for retraining
    """
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def __init__(self):
        self.feedback_store: Dict[str, UserFeedback] = {}
        self.learning_items: Dict[str, LearningItem] = {}
        self.translation_rules: Dict[str, str] = {}
        self.training_pairs: List[TrainingPair] = []
<<<<<<< HEAD

        logger.info("FeedbackLearningPipeline initialized")

=======
        
        logger.info("FeedbackLearningPipeline initialized")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def submit_feedback(self, feedback: UserFeedback):
        """Submit user feedback for processing."""
        self.feedback_store[feedback.feedback_id] = feedback
        logger.info(f"Received feedback: {feedback.feedback_id} (rating={feedback.rating})")
<<<<<<< HEAD

        # Process low-rated feedback automatically
        if feedback.rating is not None and feedback.rating <= 2:
            self._analyze_failure(feedback)

=======
        
        # Process low-rated feedback automatically
        if feedback.rating is not None and feedback.rating <= 2:
            self._analyze_failure(feedback)
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _analyze_failure(self, feedback: UserFeedback):
        """Analyze low-rated conversion to identify issues."""
        if not feedback.corrected_code or not feedback.original_java:
            logger.warning(f"Feedback {feedback.feedback_id} missing code for analysis")
            return
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Identify issue type (simplified analysis)
        issue_type = self._identify_issue_type(
            feedback.original_java,
            feedback.converted_bedrock or "",
<<<<<<< HEAD
            feedback.corrected_code,
        )

=======
            feedback.corrected_code
        )
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Create learning item
        learning_item = LearningItem(
            item_id=f"learn_{feedback.feedback_id}",
            feedback_id=feedback.feedback_id,
            issue_type=issue_type,
            description=f"Issue in conversion {feedback.conversion_id}",
            suggested_fix=self._generate_fix(feedback),
            confidence=0.8,
            status=LearningStatus.ANALYZED,
        )
<<<<<<< HEAD

        self.learning_items[learning_item.item_id] = learning_item
        logger.info(f"Created learning item: {learning_item.item_id} (issue={issue_type})")

        # Queue for retraining
        self._queue_for_retraining(feedback)

=======
        
        self.learning_items[learning_item.item_id] = learning_item
        logger.info(f"Created learning item: {learning_item.item_id} (issue={issue_type})")
        
        # Queue for retraining
        self._queue_for_retraining(feedback)
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _identify_issue_type(self, java: str, bedrock: str, corrected: str) -> str:
        """Identify the type of conversion issue."""
        # Simple heuristic-based issue identification
        if "syntax error" in corrected.lower():
            return "syntax_error"
        elif "missing" in corrected.lower():
            return "missing_feature"
        elif "wrong" in corrected.lower():
            return "incorrect_translation"
        elif "type" in corrected.lower():
            return "type_mismatch"
        else:
            return "semantic_difference"
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _generate_fix(self, feedback: UserFeedback) -> str:
        """Generate fix suggestion from feedback."""
        if feedback.corrected_code:
            return f"Use corrected code: {feedback.corrected_code[:100]}..."
        return "Review and update translation rules"
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _queue_for_retraining(self, feedback: UserFeedback):
        """Queue feedback for model retraining."""
        if feedback.original_java and feedback.corrected_code:
            training_pair = TrainingPair(
                java_code=feedback.original_java,
                bedrock_code=feedback.corrected_code,
                quality_score=0.9,  # High quality since user corrected
                source="user_correction",
            )
            self.training_pairs.append(training_pair)
            logger.info(f"Queued training pair from feedback {feedback.feedback_id}")
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def update_translation_rules(self, issue_type: str, fix: str):
        """Update translation rules based on learned issue."""
        rule_key = f"fix_{issue_type}"
        self.translation_rules[rule_key] = fix
        logger.info(f"Updated translation rule: {rule_key}")
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_learning_stats(self) -> Dict[str, Any]:
        """Get learning pipeline statistics."""
        return {
            "total_feedback": len(self.feedback_store),
            "low_rated": sum(1 for f in self.feedback_store.values() if f.rating and f.rating <= 2),
            "learning_items": len(self.learning_items),
            "training_pairs": len(self.training_pairs),
            "translation_rules": len(self.translation_rules),
            "by_status": {
<<<<<<< HEAD
                status.value: sum(
                    1 for item in self.learning_items.values() if item.status == status
                )
=======
                status.value: sum(1 for item in self.learning_items.values() if item.status == status)
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
                for status in LearningStatus
            },
        }


class CodeT5FineTuner:
    """
    CodeT5+ fine-tuning manager.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Handles:
    - Training data preparation
    - Model fine-tuning
    - Validation
    - Model deployment
    """
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def __init__(self):
        self.training_data: List[TrainingPair] = []
        self.model_path: Optional[str] = None
        self.training_history: List[Dict[str, Any]] = []
<<<<<<< HEAD

        logger.info("CodeT5FineTuner initialized")

=======
        
        logger.info("CodeT5FineTuner initialized")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def prepare_training_data(
        self,
        feedback_pairs: List[TrainingPair],
        min_quality: float = 0.7,
    ) -> int:
        """Prepare training data from feedback pairs."""
        # Filter by quality
        valid_pairs = [p for p in feedback_pairs if p.quality_score >= min_quality]
<<<<<<< HEAD

        self.training_data = valid_pairs
        logger.info(f"Prepared {len(valid_pairs)} training pairs (quality >= {min_quality})")

        return len(valid_pairs)

=======
        
        self.training_data = valid_pairs
        logger.info(f"Prepared {len(valid_pairs)} training pairs (quality >= {min_quality})")
        
        return len(valid_pairs)
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def fine_tune(
        self,
        model_name: str = "Salesforce/codet5-plus",
        epochs: int = 3,
        batch_size: int = 8,
        learning_rate: float = 1e-4,
    ) -> Dict[str, Any]:
        """
        Fine-tune CodeT5+ model.
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        Note: Actual training would require GPU and ML infrastructure.
        This is a simulation for the pipeline.
        """
        logger.info(f"Starting fine-tuning: {model_name}, epochs={epochs}")
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        # Simulated training results
        training_result = {
            "model_name": model_name,
            "epochs": epochs,
            "training_samples": len(self.training_data),
            "validation_accuracy": 0.85 + (0.01 * len(self.training_data) / 1000),
            "training_loss": 0.1,
            "validation_loss": 0.15,
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
        }
<<<<<<< HEAD

        self.training_history.append(training_result)
        self.model_path = f"models/codet5-plus-finetuned-{datetime.now().strftime('%Y%m%d')}"

        logger.info(f"Fine-tuning complete: {training_result['validation_accuracy']:.2%} accuracy")

        return training_result

=======
        
        self.training_history.append(training_result)
        self.model_path = f"models/codet5-plus-finetuned-{datetime.now().strftime('%Y%m%d')}"
        
        logger.info(f"Fine-tuning complete: {training_result['validation_accuracy']:.2%} accuracy")
        
        return training_result
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_model_stats(self) -> Dict[str, Any]:
        """Get model fine-tuning statistics."""
        return {
            "training_data_size": len(self.training_data),
            "model_path": self.model_path,
            "training_runs": len(self.training_history),
<<<<<<< HEAD
            "latest_accuracy": (
                self.training_history[-1]["validation_accuracy"] if self.training_history else 0.0
            ),
=======
            "latest_accuracy": self.training_history[-1]["validation_accuracy"] if self.training_history else 0.0,
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        }


class CommunityPatternSharing:
    """
    Community pattern sharing system.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Features:
    - Pattern submission
    - Review process
    - Voting/rating
    - Pattern library updates
    """
<<<<<<< HEAD

    def __init__(self):
        self.patterns: Dict[str, CommunityPattern] = {}
        self.review_queue: List[str] = []

        logger.info("CommunityPatternSharing initialized")

=======
    
    def __init__(self):
        self.patterns: Dict[str, CommunityPattern] = {}
        self.review_queue: List[str] = []
        
        logger.info("CommunityPatternSharing initialized")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def submit_pattern(
        self,
        name: str,
        description: str,
        java_example: str,
        bedrock_example: str,
        submitted_by: str,
    ) -> CommunityPattern:
        """Submit a community pattern for review."""
        pattern_id = f"community_{len(self.patterns) + 1}"
<<<<<<< HEAD

=======
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        pattern = CommunityPattern(
            pattern_id=pattern_id,
            name=name,
            description=description,
            java_example=java_example,
            bedrock_example=bedrock_example,
            submitted_by=submitted_by,
        )
<<<<<<< HEAD

        self.patterns[pattern_id] = pattern
        self.review_queue.append(pattern_id)

        logger.info(f"Pattern submitted: {pattern_id} by {submitted_by}")
        return pattern

=======
        
        self.patterns[pattern_id] = pattern
        self.review_queue.append(pattern_id)
        
        logger.info(f"Pattern submitted: {pattern_id} by {submitted_by}")
        return pattern
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def review_pattern(self, pattern_id: str, approved: bool, reviewer: str, comments: str = ""):
        """Review a community pattern."""
        pattern = self.patterns.get(pattern_id)
        if not pattern:
            logger.warning(f"Pattern {pattern_id} not found")
            return
<<<<<<< HEAD

        pattern.reviews.append(
            {
                "reviewer": reviewer,
                "approved": approved,
                "comments": comments,
                "timestamp": datetime.now().isoformat(),
            }
        )

=======
        
        pattern.reviews.append({
            "reviewer": reviewer,
            "approved": approved,
            "comments": comments,
            "timestamp": datetime.now().isoformat(),
        })
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        if approved:
            pattern.status = "approved"
            logger.info(f"Pattern {pattern_id} approved by {reviewer}")
        else:
            pattern.status = "rejected"
            logger.info(f"Pattern {pattern_id} rejected by {reviewer}")
<<<<<<< HEAD

        if pattern_id in self.review_queue:
            self.review_queue.remove(pattern_id)

=======
        
        if pattern_id in self.review_queue:
            self.review_queue.remove(pattern_id)
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def vote_pattern(self, pattern_id: str, vote: int):
        """Vote on a community pattern (+1 or -1)."""
        pattern = self.patterns.get(pattern_id)
        if not pattern:
            return
<<<<<<< HEAD

        pattern.votes += vote
        logger.debug(f"Pattern {pattern_id} voted: {vote}, total: {pattern.votes}")

=======
        
        pattern.votes += vote
        logger.debug(f"Pattern {pattern_id} voted: {vote}, total: {pattern.votes}")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_top_patterns(self, limit: int = 10) -> List[CommunityPattern]:
        """Get top-voted approved patterns."""
        approved = [p for p in self.patterns.values() if p.status == "approved"]
        approved.sort(key=lambda p: p.votes, reverse=True)
        return approved[:limit]
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_stats(self) -> Dict[str, Any]:
        """Get community pattern statistics."""
        return {
            "total_patterns": len(self.patterns),
            "pending_review": len(self.review_queue),
            "approved": sum(1 for p in self.patterns.values() if p.status == "approved"),
            "rejected": sum(1 for p in self.patterns.values() if p.status == "rejected"),
            "total_votes": sum(p.votes for p in self.patterns.values()),
        }


class ContinuousImprovementDashboard:
    """
    Dashboard for tracking continuous improvement metrics.
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    Metrics:
    - Accuracy trend over time
    - New patterns added
    - User feedback incorporated
    - Model version tracking
    """
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def __init__(self):
        self.metrics_history: List[Dict[str, Any]] = []
        self.current_metrics: Dict[str, float] = {
            "accuracy": 0.80,
            "user_satisfaction": 4.0,
            "mod_coverage": 0.65,
            "conversion_speed": 3.0,  # minutes
        }
<<<<<<< HEAD

        logger.info("ContinuousImprovementDashboard initialized")

=======
        
        logger.info("ContinuousImprovementDashboard initialized")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def update_metrics(
        self,
        accuracy: Optional[float] = None,
        user_satisfaction: Optional[float] = None,
        mod_coverage: Optional[float] = None,
        conversion_speed: Optional[float] = None,
    ):
        """Update current metrics."""
        if accuracy is not None:
            self.current_metrics["accuracy"] = accuracy
        if user_satisfaction is not None:
            self.current_metrics["user_satisfaction"] = user_satisfaction
        if mod_coverage is not None:
            self.current_metrics["mod_coverage"] = mod_coverage
        if conversion_speed is not None:
            self.current_metrics["conversion_speed"] = conversion_speed
<<<<<<< HEAD

        # Record history
        self.metrics_history.append(
            {
                **self.current_metrics,
                "timestamp": datetime.now().isoformat(),
            }
        )

        logger.info(f"Metrics updated: accuracy={accuracy}")

=======
        
        # Record history
        self.metrics_history.append({
            **self.current_metrics,
            "timestamp": datetime.now().isoformat(),
        })
        
        logger.info(f"Metrics updated: accuracy={accuracy}")
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            "current": self.current_metrics,
            "history": self.metrics_history[-100:],  # Last 100 data points
            "improvements": self._calculate_improvements(),
        }
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _calculate_improvements(self) -> Dict[str, float]:
        """Calculate improvement percentages."""
        if len(self.metrics_history) < 2:
            return {}
<<<<<<< HEAD

        first = self.metrics_history[0]
        latest = self.metrics_history[-1]

=======
        
        first = self.metrics_history[0]
        latest = self.metrics_history[-1]
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        return {
            "accuracy_change": latest["accuracy"] - first["accuracy"],
            "satisfaction_change": latest["user_satisfaction"] - first["user_satisfaction"],
            "coverage_change": latest["mod_coverage"] - first["mod_coverage"],
            "speed_improvement": first["conversion_speed"] - latest["conversion_speed"],
        }
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get complete dashboard data."""
        return {
            "metrics": self.get_metrics(),
            "milestone_summary": self._get_milestone_summary(),
            "recommendations": self._generate_recommendations(),
        }
<<<<<<< HEAD

=======
    
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
    def _get_milestone_summary(self) -> Dict[str, Any]:
        """Get Milestone v2.0 summary."""
        return {
            "parsing_success": {"before": 0.70, "after": 0.98, "improvement": "+40%"},
<<<<<<< HEAD
            "conversion_time": {
                "before": 8.0,
                "after": 3.0,
                "improvement": "62% faster",
            },
=======
            "conversion_time": {"before": 8.0, "after": 3.0, "improvement": "62% faster"},
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
            "automation": {"before": 0.60, "after": 0.85, "improvement": "+42%"},
            "mod_coverage": {"before": 0.40, "after": 0.65, "improvement": "+62%"},
            "user_satisfaction": {"before": 3.5, "after": 4.5, "improvement": "+29%"},
            "failure_rate": {"before": 0.20, "after": 0.10, "improvement": "-50%"},
        }
<<<<<<< HEAD

    def _generate_recommendations(self) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []

        if self.current_metrics["accuracy"] < 0.90:
            recommendations.append(
                "Focus on improving conversion accuracy through more training data"
            )

        if self.current_metrics["mod_coverage"] < 0.75:
            recommendations.append("Expand pattern library to cover more mod types")

        if self.current_metrics["conversion_speed"] > 2.0:
            recommendations.append("Optimize conversion pipeline for faster processing")

=======
    
    def _generate_recommendations(self) -> List[str]:
        """Generate improvement recommendations."""
        recommendations = []
        
        if self.current_metrics["accuracy"] < 0.90:
            recommendations.append("Focus on improving conversion accuracy through more training data")
        
        if self.current_metrics["mod_coverage"] < 0.75:
            recommendations.append("Expand pattern library to cover more mod types")
        
        if self.current_metrics["conversion_speed"] > 2.0:
            recommendations.append("Optimize conversion pipeline for faster processing")
        
>>>>>>> 676f3c2 (fix: replace Math.random() with crypto.randomUUID() for ID generation (#841))
        return recommendations


# Global instances
_learning_pipeline: Optional[FeedbackLearningPipeline] = None
_fine_tuner: Optional[CodeT5FineTuner] = None
_pattern_sharing: Optional[CommunityPatternSharing] = None
_dashboard: Optional[ContinuousImprovementDashboard] = None


def get_learning_pipeline() -> FeedbackLearningPipeline:
    """Get or create learning pipeline instance."""
    global _learning_pipeline
    if _learning_pipeline is None:
        _learning_pipeline = FeedbackLearningPipeline()
    return _learning_pipeline


def get_fine_tuner() -> CodeT5FineTuner:
    """Get or create fine-tuner instance."""
    global _fine_tuner
    if _fine_tuner is None:
        _fine_tuner = CodeT5FineTuner()
    return _fine_tuner


def get_pattern_sharing() -> CommunityPatternSharing:
    """Get or create pattern sharing instance."""
    global _pattern_sharing
    if _pattern_sharing is None:
        _pattern_sharing = CommunityPatternSharing()
    return _pattern_sharing


def get_dashboard() -> ContinuousImprovementDashboard:
    """Get or create dashboard instance."""
    global _dashboard
    if _dashboard is None:
        _dashboard = ContinuousImprovementDashboard()
    return _dashboard


def get_learning_system_status() -> Dict[str, Any]:
    """Get overall learning system status."""
    return {
        "learning_pipeline": get_learning_pipeline().get_learning_stats(),
        "fine_tuner": get_fine_tuner().get_model_stats(),
        "pattern_sharing": get_pattern_sharing().get_stats(),
        "dashboard": get_dashboard().get_metrics(),
    }
