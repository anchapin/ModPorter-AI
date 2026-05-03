"""
Prompt-Based Reinforcement Learning System

Implements the feedback loop that the original RL module was missing:
1. After each conversion, store high-quality examples in vector DB
2. On similar mod types, retrieve best prior examples via RAG
3. Track which prompt strategies produce higher quality scores
4. Adapt prompt templates based on learned patterns

This approach is practical at current scale and creates a self-improving system.
"""

import json
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from utils.vector_db_client import VectorDBClient

logger = logging.getLogger(__name__)


class ExampleQuality(Enum):
    """Quality tiers for stored examples."""

    EXCELLENT = "excellent"  # >= 0.9 overall score
    GOOD = "good"  # >= 0.75
    ACCEPTABLE = "acceptable"  # >= 0.6
    POOR = "poor"  # < 0.6


@dataclass
class PromptExample:
    """
    A successful conversion example stored for few-shot learning.

    Contains the input mod characteristics, conversion strategy used,
    and the successful output for reuse in similar conversions.
    """

    example_id: str
    job_id: str

    # Mod characteristics (for retrieval matching)
    mod_name: str
    mod_type: str  # e.g., "texture_pack", "block_mod", "entity_mod"
    mod_framework: str  # e.g., "forge", "fabric"
    minecraft_version: str
    complexity_score: float  # 0-1 scale

    # What conversion strategy was used
    agent_type: str
    conversion_strategy: str  # e.g., "ast_first", "bytecode_fallback"
    prompt_template_used: str

    # The successful conversion details
    input_summary: str  # Brief description of input
    output_summary: str  # Brief description of output
    quality_score: float
    quality_breakdown: Dict[str, float]  # completeness, correctness, etc.

    # Source content for few-shot learning
    input_modality: str  # "jar_analysis_result", "texture_path", etc.
    successful_output: str  # Actual output that worked

    # Retrieval metadata
    content_hash: str
    retrieval_count: int = 0
    last_retrieved: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


class PromptExampleStore:
    """
    Stores and retrieves high-quality conversion examples in vector DB.

    Examples are indexed by both:
    - Semantic embedding (via vector DB) for similarity search
    - Structured metadata (mod type, framework, etc.) for filtering

    Only examples with quality_score >= 0.6 are stored.
    """

    QUALITY_THRESHOLD = 0.6
    MAX_EXAMPLES_PER_TYPE = 100

    def __init__(self, vector_db_client: Optional[VectorDBClient] = None):
        self.vector_db = vector_db_client or VectorDBClient()

        # SQLite index for structured queries
        self.db_path = "training_data/prompt_examples.db"
        self._init_db()

        # In-memory cache for frequent access
        self._example_cache: Dict[str, PromptExample] = {}

    def _init_db(self):
        """Initialize SQLite index for structured example queries."""
        import os

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prompt_examples (
                    example_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL,
                    mod_name TEXT,
                    mod_type TEXT,
                    mod_framework TEXT,
                    minecraft_version TEXT,
                    complexity_score REAL,
                    agent_type TEXT,
                    conversion_strategy TEXT,
                    prompt_template_used TEXT,
                    input_summary TEXT,
                    output_summary TEXT,
                    quality_score REAL,
                    quality_breakdown TEXT,
                    input_modality TEXT,
                    successful_output TEXT,
                    content_hash TEXT UNIQUE,
                    retrieval_count INTEGER DEFAULT 0,
                    last_retrieved TEXT,
                    created_at TEXT
                )
            """)

            # Indexes for common query patterns
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mod_type ON prompt_examples(mod_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_agent_type ON prompt_examples(agent_type)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_quality ON prompt_examples(quality_score)")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_framework ON prompt_examples(mod_framework)"
            )

    async def store_example(
        self,
        job_id: str,
        mod_info: Dict[str, Any],
        conversion_result: Dict[str, Any],
        quality_metrics: Dict[str, Any],
        prompt_used: str,
    ) -> Optional[str]:
        """
        Store a successful conversion example for future few-shot learning.

        Args:
            job_id: Unique conversion job ID
            mod_info: Dict with mod_name, mod_type, framework, version, complexity
            conversion_result: Dict with input_summary, output_summary, successful_output
            quality_metrics: Quality scores from ConversionQualityScorer
            prompt_used: The prompt template that produced this result

        Returns:
            example_id if stored successfully, None if quality too low
        """
        quality_score = quality_metrics.get("overall_score", 0.0)

        # Only store if quality meets threshold
        if quality_score < self.QUALITY_THRESHOLD:
            logger.debug(f"Example {job_id} quality {quality_score:.2f} below threshold")
            return None

        # Determine quality tier
        if quality_score >= 0.9:
            quality_tier = ExampleQuality.EXCELLENT
        elif quality_score >= 0.75:
            quality_tier = ExampleQuality.GOOD
        elif quality_score >= 0.6:
            quality_tier = ExampleQuality.ACCEPTABLE
        else:
            quality_tier = ExampleQuality.POOR

        # Build example
        example_id = f"pex_{job_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        import hashlib

        content_hash = hashlib.md5(
            f"{job_id}:{mod_info.get('mod_name', '')}:{quality_score}".encode()
        ).hexdigest()[:16]

        example = PromptExample(
            example_id=example_id,
            job_id=job_id,
            mod_name=mod_info.get("mod_name", "unknown"),
            mod_type=mod_info.get("mod_type", "unknown"),
            mod_framework=mod_info.get("framework", "unknown"),
            minecraft_version=mod_info.get("version", "unknown"),
            complexity_score=mod_info.get("complexity", 0.5),
            agent_type=conversion_result.get("agent_type", "unknown"),
            conversion_strategy=conversion_result.get("strategy", "default"),
            prompt_template_used=prompt_used,
            input_summary=conversion_result.get("input_summary", ""),
            output_summary=conversion_result.get("output_summary", ""),
            quality_score=quality_score,
            quality_breakdown={
                "completeness": quality_metrics.get("completeness_score", 0.0),
                "correctness": quality_metrics.get("correctness_score", 0.0),
                "performance": quality_metrics.get("performance_score", 0.0),
                "compatibility": quality_metrics.get("compatibility_score", 0.0),
                "user_experience": quality_metrics.get("user_experience_score", 0.0),
            },
            input_modality=conversion_result.get("input_modality", "jar"),
            successful_output=conversion_result.get("successful_output", ""),
            content_hash=content_hash,
        )

        # Store in SQLite
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO prompt_examples (
                        example_id, job_id, mod_name, mod_type, mod_framework,
                        minecraft_version, complexity_score, agent_type, conversion_strategy,
                        prompt_template_used, input_summary, output_summary, quality_score,
                        quality_breakdown, input_modality, successful_output, content_hash,
                        retrieval_count, last_retrieved, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        example.example_id,
                        example.job_id,
                        example.mod_name,
                        example.mod_type,
                        example.mod_framework,
                        example.minecraft_version,
                        example.complexity_score,
                        example.agent_type,
                        example.conversion_strategy,
                        example.prompt_template_used,
                        example.input_summary,
                        example.output_summary,
                        example.quality_score,
                        json.dumps(example.quality_breakdown),
                        example.input_modality,
                        example.successful_output,
                        example.content_hash,
                        example.retrieval_count,
                        example.last_retrieved,
                        example.created_at,
                    ),
                )

            # Store embedding in vector DB for semantic search
            embedding_text = self._build_embedding_text(example)
            await self.vector_db.index_document(
                document_content=embedding_text, document_source=f"prompt_example:{example_id}"
            )

            # Cache locally
            self._example_cache[example_id] = example

            logger.info(
                f"Stored prompt example {example_id} (quality={quality_score:.2f}, tier={quality_tier.value})"
            )
            return example_id

        except Exception as e:
            logger.error(f"Failed to store prompt example: {e}")
            return None

    def _build_embedding_text(self, example: PromptExample) -> str:
        """Build text for embedding generation."""
        return f"""
Mod: {example.mod_name}
Type: {example.mod_type}
Framework: {example.mod_framework}
Agent: {example.agent_type}
Strategy: {example.conversion_strategy}
Input: {example.input_summary}
Output: {example.output_summary}
Quality: {example.quality_score}
""".strip()

    async def retrieve_similar_examples(
        self,
        mod_info: Dict[str, Any],
        agent_type: str,
        top_k: int = 3,
    ) -> List[PromptExample]:
        """
        Retrieve similar successful examples for few-shot learning.

        Uses hybrid search: vector similarity + structured filtering.

        Args:
            mod_info: Dict with mod characteristics to match
            agent_type: Type of agent (for filtering)
            top_k: Number of examples to retrieve

        Returns:
            List of most relevant PromptExamples
        """
        # Build search query
        query_text = f"""
        {mod_info.get("mod_type", "")} conversion
        {mod_info.get("mod_name", "")}
        framework: {mod_info.get("framework", "")}
        agent: {agent_type}
        """.strip()

        try:
            # Semantic search via vector DB
            results = await self.vector_db.search_documents(
                query_text=query_text,
                top_k=top_k * 2,  # Over-retrieve to allow filtering
                document_source_filter="prompt_example:",
            )

            # Get example IDs from results
            example_ids = []
            for r in results:
                source = r.get("document_source", "")
                if source.startswith("prompt_example:"):
                    example_ids.append(source.replace("prompt_example:", ""))

            # Fetch from SQLite with structured filtering
            examples = self._fetch_examples_from_db(
                example_ids=example_ids,
                agent_type=agent_type,
                mod_type=mod_info.get("mod_type"),
                framework=mod_info.get("framework"),
                limit=top_k,
            )

            # Update retrieval stats
            for ex in examples:
                self._update_retrieval_stats(ex.example_id)

            return examples

        except Exception as e:
            logger.error(f"Failed to retrieve similar examples: {e}")
            return []

    def _fetch_examples_from_db(
        self,
        example_ids: List[str],
        agent_type: str,
        mod_type: Optional[str],
        framework: Optional[str],
        limit: int,
    ) -> List[PromptExample]:
        """Fetch examples from SQLite with filtering."""
        if not example_ids:
            return []

        placeholders = ",".join("?" * len(example_ids))

        query = f"""
            SELECT * FROM prompt_examples
            WHERE example_id IN ({placeholders})
        """
        params = list(example_ids)

        # Add filters
        if agent_type:
            query += " AND agent_type = ?"
            params.append(agent_type)
        if mod_type:
            query += " AND mod_type = ?"
            params.append(mod_type)
        if framework:
            query += " AND mod_framework = ?"
            params.append(framework)

        query += " ORDER BY quality_score DESC LIMIT ?"
        params.append(limit)

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                examples = []
                for row in rows:
                    example = PromptExample(
                        example_id=row["example_id"],
                        job_id=row["job_id"],
                        mod_name=row["mod_name"] or "",
                        mod_type=row["mod_type"] or "",
                        mod_framework=row["mod_framework"] or "",
                        minecraft_version=row["minecraft_version"] or "",
                        complexity_score=row["complexity_score"] or 0.0,
                        agent_type=row["agent_type"] or "",
                        conversion_strategy=row["conversion_strategy"] or "",
                        prompt_template_used=row["prompt_template_used"] or "",
                        input_summary=row["input_summary"] or "",
                        output_summary=row["output_summary"] or "",
                        quality_score=row["quality_score"] or 0.0,
                        quality_breakdown=json.loads(row["quality_breakdown"] or "{}"),
                        input_modality=row["input_modality"] or "",
                        successful_output=row["successful_output"] or "",
                        content_hash=row["content_hash"] or "",
                        retrieval_count=row["retrieval_count"] or 0,
                        last_retrieved=row["last_retrieved"],
                        created_at=row["created_at"] or "",
                    )
                    examples.append(example)
                    self._example_cache[example.example_id] = example

                return examples

        except Exception as e:
            logger.error(f"Failed to fetch examples from DB: {e}")
            return []

    def _update_retrieval_stats(self, example_id: str):
        """Update retrieval count and timestamp."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE prompt_examples
                    SET retrieval_count = retrieval_count + 1,
                        last_retrieved = ?
                    WHERE example_id = ?
                """,
                    (datetime.now().isoformat(), example_id),
                )
        except Exception as e:
            logger.error(f"Failed to update retrieval stats: {e}")


class PromptStrategyTracker:
    """
    Tracks which prompt strategies lead to better quality scores.

    Analyzes correlations between:
    - Prompt templates used
    - Conversion strategies
    - Mod types/frameworks
    - Quality outcomes

    Generates recommendations for which strategies to use in which contexts.
    """

    def __init__(self, db_path: str = "training_data/strategy_tracker.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Initialize strategy tracking database."""
        import os

        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_outcomes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    mod_type TEXT,
                    mod_framework TEXT,
                    agent_type TEXT,
                    strategy_used TEXT,
                    prompt_template TEXT,
                    quality_score REAL,
                    quality_breakdown TEXT,
                    conversion_success INTEGER,
                    created_at TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS strategy_stats (
                    strategy_key TEXT PRIMARY KEY,
                    strategy_type TEXT,
                    usage_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    total_quality REAL DEFAULT 0.0,
                    avg_quality REAL DEFAULT 0.0,
                    last_updated TEXT
                )
            """)

            # Indexes
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_strategy_key ON strategy_stats(strategy_key)"
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_mod_type ON strategy_outcomes(mod_type)")

    def record_outcome(
        self,
        job_id: str,
        mod_type: str,
        mod_framework: str,
        agent_type: str,
        strategy_used: str,
        prompt_template: str,
        quality_score: float,
        quality_breakdown: Dict[str, float],
        conversion_success: bool,
    ):
        """Record a strategy outcome for analysis."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()

                # Record individual outcome
                conn.execute(
                    """
                    INSERT INTO strategy_outcomes (
                        job_id, mod_type, mod_framework, agent_type, strategy_used,
                        prompt_template, quality_score, quality_breakdown,
                        conversion_success, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        job_id,
                        mod_type,
                        mod_framework,
                        agent_type,
                        strategy_used,
                        prompt_template,
                        quality_score,
                        json.dumps(quality_breakdown),
                        1 if conversion_success else 0,
                        now,
                    ),
                )

                # Update aggregated stats
                strategy_key = self._make_strategy_key(
                    mod_type, mod_framework, agent_type, strategy_used
                )

                conn.execute(
                    """
                    INSERT INTO strategy_stats (
                        strategy_key, strategy_type, usage_count, success_count,
                        total_quality, avg_quality, last_updated
                    ) VALUES (?, ?, 1, ?, ?, ?, ?)
                    ON CONFLICT(strategy_key) DO UPDATE SET
                        usage_count = usage_count + 1,
                        success_count = success_count + ?,
                        total_quality = total_quality + ?,
                        avg_quality = (total_quality + ?) / (usage_count + 1),
                        last_updated = ?
                """,
                    (
                        strategy_key,
                        strategy_used,
                        1 if conversion_success else 0,
                        quality_score,
                        quality_score,
                        now,
                        1 if conversion_success else 0,
                        quality_score,
                        quality_score,
                        now,
                    ),
                )

        except Exception as e:
            logger.error(f"Failed to record strategy outcome: {e}")

    def _make_strategy_key(
        self, mod_type: str, mod_framework: str, agent_type: str, strategy: str
    ) -> str:
        """Create unique key for strategy combination."""
        return f"{mod_type}:{mod_framework}:{agent_type}:{strategy}"

    def get_best_strategy(
        self,
        mod_type: str,
        mod_framework: str,
        agent_type: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Get the best performing strategy for a given context.

        Returns strategy details and quality expectations.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                # Find strategies for this context
                cursor = conn.execute(
                    """
                    SELECT * FROM strategy_stats
                    WHERE strategy_key LIKE ?
                    ORDER BY avg_quality DESC, usage_count DESC
                    LIMIT 1
                """,
                    (f"{mod_type}:{mod_framework}:{agent_type}:%",),
                )

                row = cursor.fetchone()
                if row:
                    return {
                        "strategy": row["strategy_type"],
                        "avg_quality": row["avg_quality"],
                        "usage_count": row["usage_count"],
                        "success_rate": row["success_count"] / row["usage_count"]
                        if row["usage_count"] > 0
                        else 0.0,
                    }

                # Fallback: try with just mod_type and agent_type
                cursor = conn.execute(
                    """
                    SELECT * FROM strategy_stats
                    WHERE strategy_key LIKE ?
                    ORDER BY avg_quality DESC, usage_count DESC
                    LIMIT 1
                """,
                    (f"{mod_type}:%:{agent_type}:%",),
                )

                row = cursor.fetchone()
                if row:
                    return {
                        "strategy": row["strategy_type"],
                        "avg_quality": row["avg_quality"],
                        "usage_count": row["usage_count"],
                        "success_rate": row["success_count"] / row["usage_count"]
                        if row["usage_count"] > 0
                        else 0.0,
                        "note": "Fallback - framework mismatch",
                    }

                return None

        except Exception as e:
            logger.error(f"Failed to get best strategy: {e}")
            return None

    def get_strategy_recommendations(
        self,
        mod_type: str,
        mod_framework: str,
    ) -> List[Dict[str, Any]]:
        """Get ranked strategy recommendations for a mod type."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row

                cursor = conn.execute(
                    """
                    SELECT * FROM strategy_stats
                    WHERE strategy_key LIKE ?
                    ORDER BY avg_quality DESC
                    LIMIT 5
                """,
                    (f"{mod_type}:{mod_framework}:%",),
                )

                rows = cursor.fetchall()
                return [
                    {
                        "strategy": row["strategy_type"],
                        "avg_quality": row["avg_quality"],
                        "usage_count": row["usage_count"],
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Failed to get recommendations: {e}")
            return []


class FewShotPromptBuilder:
    """
    Builds prompts with few-shot examples for agent execution.

    Integrates with the retrieval system to inject relevant
    successful examples into agent prompts.
    """

    def __init__(
        self,
        example_store: PromptExampleStore,
        strategy_tracker: PromptStrategyTracker,
    ):
        self.example_store = example_store
        self.strategy_tracker = strategy_tracker

    async def build_prompt(
        self,
        base_prompt: str,
        mod_info: Dict[str, Any],
        agent_type: str,
        max_examples: int = 3,
    ) -> Tuple[str, List[PromptExample]]:
        """
        Build an enhanced prompt with few-shot examples.

        Args:
            base_prompt: The base prompt template
            mod_info: Mod characteristics for example matching
            agent_type: Type of agent (for filtering examples)
            max_examples: Maximum number of examples to include

        Returns:
            Tuple of (enhanced_prompt, retrieved_examples)
        """
        # Retrieve similar successful examples
        examples = await self.example_store.retrieve_similar_examples(
            mod_info=mod_info,
            agent_type=agent_type,
            top_k=max_examples,
        )

        if not examples:
            return base_prompt, []

        # Build few-shot section
        few_shot_section = self._build_few_shot_section(examples)

        # Check for best known strategy
        best_strategy = self.strategy_tracker.get_best_strategy(
            mod_type=mod_info.get("mod_type", "unknown"),
            mod_framework=mod_info.get("framework", "unknown"),
            agent_type=agent_type,
        )

        # Append strategy hint if we have strong evidence
        strategy_hint = ""
        if best_strategy and best_strategy["usage_count"] >= 3:
            strategy_hint = f"\n\n[Strategy hint: For {mod_info.get('mod_type')} with {mod_info.get('framework')}, '{best_strategy['strategy']}' has achieved avg quality {best_strategy['avg_quality']:.2f}]\n"

        # Combine
        enhanced_prompt = f"""{base_prompt}

{few_shot_section}{strategy_hint}"""

        return enhanced_prompt, examples

    def _build_few_shot_section(self, examples: List[PromptExample]) -> str:
        """Build the few-shot examples section."""
        if not examples:
            return ""

        section = "\n\n## Successful Examples\n\n"

        for i, ex in enumerate(examples, 1):
            section += f"""### Example {i} ({ex.mod_name}, Quality: {ex.quality_score:.2f})

**Input:** {ex.input_summary}

**Strategy Used:** {ex.conversion_strategy}

**Output:** {ex.output_summary}

**Quality Breakdown:** completenes={ex.quality_breakdown.get("completeness", 0):.2f}, correctness={ex.quality_breakdown.get("correctness", 0):.2f}

---
"""

        return section


class RLFeedbackLoop:
    """
    Main integration point: connects RL components to the conversion pipeline.

    This is what was missing in the original RL module - the actual
    feedback mechanism that updates agent behavior.

    Usage:
        1. After a conversion, call record_conversion() with results
        2. Before a conversion, call get_enhanced_prompt() for the agent
    """

    def __init__(self):
        self.example_store = PromptExampleStore()
        self.strategy_tracker = PromptStrategyTracker()
        self.prompt_builder = FewShotPromptBuilder(
            self.example_store,
            self.strategy_tracker,
        )

        # Quality score needed to update best strategy
        self.strategy_update_threshold = 0.7

    async def record_conversion(
        self,
        job_id: str,
        mod_info: Dict[str, Any],
        conversion_result: Dict[str, Any],
        quality_metrics: Dict[str, Any],
        prompt_used: str,
        conversion_success: bool,
    ):
        """
        Record a conversion outcome for the RL feedback loop.

        This should be called after every conversion attempt.
        """
        quality_score = quality_metrics.get("overall_score", 0.0)

        # Store successful example if quality is good enough
        if quality_score >= self.example_store.QUALITY_THRESHOLD:
            await self.example_store.store_example(
                job_id=job_id,
                mod_info=mod_info,
                conversion_result={
                    "agent_type": conversion_result.get("agent_type", "unknown"),
                    "strategy": conversion_result.get("strategy", "default"),
                    "input_summary": conversion_result.get("input_summary", ""),
                    "output_summary": conversion_result.get("output_summary", ""),
                    "successful_output": conversion_result.get("successful_output", ""),
                    "input_modality": conversion_result.get("input_modality", "jar"),
                },
                quality_metrics=quality_metrics,
                prompt_used=prompt_used,
            )

        # Record strategy outcome
        self.strategy_tracker.record_outcome(
            job_id=job_id,
            mod_type=mod_info.get("mod_type", "unknown"),
            mod_framework=mod_info.get("framework", "unknown"),
            agent_type=conversion_result.get("agent_type", "unknown"),
            strategy_used=conversion_result.get("strategy", "default"),
            prompt_template=prompt_used,
            quality_score=quality_score,
            quality_breakdown={
                "completeness": quality_metrics.get("completeness_score", 0.0),
                "correctness": quality_metrics.get("correctness_score", 0.0),
                "performance": quality_metrics.get("performance_score", 0.0),
                "compatibility": quality_metrics.get("compatibility_score", 0.0),
                "user_experience": quality_metrics.get("user_experience_score", 0.0),
            },
            conversion_success=conversion_success,
        )

        logger.info(
            f"Recorded conversion {job_id}: "
            f"quality={quality_score:.2f}, success={conversion_success}"
        )

    async def get_enhanced_prompt(
        self,
        base_prompt: str,
        mod_info: Dict[str, Any],
        agent_type: str,
    ) -> str:
        """
        Get an enhanced prompt with few-shot examples and strategy hints.

        Call this before agent execution to get an optimized prompt.
        """
        enhanced_prompt, _ = await self.prompt_builder.build_prompt(
            base_prompt=base_prompt,
            mod_info=mod_info,
            agent_type=agent_type,
        )
        return enhanced_prompt

    def get_prompt_strategy_summary(self) -> Dict[str, Any]:
        """Get a summary of tracked strategies and their performance."""
        return {
            "example_store": {
                "db_path": self.example_store.db_path,
            },
            "strategy_tracker": {
                "db_path": self.strategy_tracker.db_path,
            },
        }


# Singleton instance
_rl_feedback_loop: Optional[RLFeedbackLoop] = None


def get_rl_feedback_loop() -> RLFeedbackLoop:
    """Get the singleton RL feedback loop instance."""
    global _rl_feedback_loop
    if _rl_feedback_loop is None:
        _rl_feedback_loop = RLFeedbackLoop()
    return _rl_feedback_loop


async def integrate_conversion_result(
    job_id: str,
    mod_path: str,
    output_path: str,
    conversion_result: Dict[str, Any],
    quality_metrics: Dict[str, Any],
    agent_type: str = "conversion_planner",
) -> None:
    """
    Convenience function to integrate a conversion result into the RL feedback loop.

    This is the main integration point for the conversion pipeline.

    Args:
        job_id: Unique job identifier
        mod_path: Path to original mod file
        output_path: Path to converted output
        conversion_result: Dict with conversion details
        quality_metrics: Quality assessment from ConversionQualityScorer
        agent_type: Type of agent used for conversion
    """
    rl = get_rl_feedback_loop()

    mod_info = {
        "mod_name": conversion_result.get("mod_name", mod_path.split("/")[-1]),
        "mod_type": conversion_result.get("mod_type", "unknown"),
        "framework": conversion_result.get("framework", "unknown"),
        "version": conversion_result.get("version", "unknown"),
        "complexity": conversion_result.get("complexity", 0.5),
    }

    await rl.record_conversion(
        job_id=job_id,
        mod_info=mod_info,
        conversion_result={
            "agent_type": agent_type,
            "strategy": conversion_result.get("strategy", "default"),
            "input_summary": conversion_result.get("input_summary", f"Conversion of {mod_path}"),
            "output_summary": conversion_result.get("output_summary", f"Output to {output_path}"),
            "successful_output": str(conversion_result.get("output", ""))[:1000],
            "input_modality": "jar" if mod_path.endswith(".jar") else "directory",
        },
        quality_metrics=quality_metrics,
        prompt_used=conversion_result.get("prompt_used", "default"),
        conversion_success=conversion_result.get(
            "success", quality_metrics.get("overall_score", 0) > 0.5
        ),
    )
