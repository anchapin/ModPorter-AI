"""
Self-Learning System for Minecraft Mod Conversion

This module provides:
- User correction tracking and feedback loop
- Pattern learning from user corrections
- Automatic improvement detection
- Pattern database enhancement with confidence scoring

The system learns from user corrections to improve future translations.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import re
import json
import hashlib


class CorrectionType(Enum):
    """Types of corrections made by users."""
    SYNTAX = "syntax"           # Syntax-level fixes
    SEMANTIC = "semantic"        # Meaning preservation issues
    PATTERN = "pattern"          # Pattern-related improvements
    API = "api"                  # API mapping corrections
    FORMATTING = "formatting"    # Code style/formatting
    LOGIC = "logic"              # Business logic corrections


class CorrectionImpact(Enum):
    """Impact level of corrections."""
    MINOR = "minor"              # Small tweaks
    MODERATE = "moderate"         # Noticeable changes
    MAJOR = "major"              # Significant rewrites


class PatternSource(Enum):
    """Origin of patterns in the database."""
    BUILTIN = "builtin"          # Pre-defined patterns
    LEARNED = "learned"          # Learned from user corrections
    DERIVED = "derived"          # Automatically derived
    USER_SUBMITTED = "user"      # User-submitted patterns


@dataclass
class Correction:
    """Represents a user correction."""
    id: str
    original_code: str
    corrected_code: str
    correction_type: CorrectionType
    impact: CorrectionImpact
    context: Dict[str, Any]
    timestamp: datetime
    source_file: str
    user_id: Optional[str] = None
    quality_score: float = 0.0
    applied: bool = False
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
            
    def _generate_id(self) -> str:
        """Generate unique ID for correction."""
        content = f"{self.original_code}{self.corrected_code}{self.timestamp.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()[:12]


@dataclass
class LearnedPattern:
    """A pattern learned from user corrections."""
    pattern_id: str
    source: PatternSource
    java_pattern: str
    bedrock_pattern: str
    confidence: float
    usage_count: int = 0
    success_count: int = 0
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    last_used: Optional[datetime] = None
    parent_pattern_id: Optional[str] = None
    description: str = ""
    examples: List[str] = field(default_factory=list)
    
    def update_confidence(self, successful: bool) -> None:
        """Update confidence based on usage outcome."""
        self.usage_count += 1
        if successful:
            self.success_count += 1
        # Confidence = success rate with smoothing
        if self.usage_count > 0:
            raw_confidence = self.success_count / self.usage_count
            # Bayesian smoothing
            self.confidence = (raw_confidence * self.usage_count + 0.7 * 5) / (self.usage_count + 5)
        self.last_used = datetime.now()


@dataclass
class LearningMetrics:
    """Metrics for the learning system."""
    total_corrections: int = 0
    patterns_learned: int = 0
    patterns_applied: int = 0
    successful_applications: int = 0
    average_quality_score: float = 0.0
    last_pattern_added: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_corrections": self.total_corrections,
            "patterns_learned": self.patterns_learned,
            "patterns_applied": self.patterns_applied,
            "successful_applications": self.successful_applications,
            "average_quality_score": self.average_quality_score,
            "last_pattern_added": self.last_pattern_added.isoformat() if self.last_pattern_added else None
        }


class SelfLearningSystem:
    """
    Self-Learning System that improves translation accuracy by learning from user corrections.
    
    Features:
    - Tracks user corrections during review
    - Classifies corrections by type and impact
    - Extracts reusable patterns from corrections
    - Updates pattern confidence based on usage
    - Provides improvement suggestions
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize the self-learning system.
        
        Args:
            storage_path: Optional path for persisting learned patterns
        """
        self.logger = None
        self.storage_path = storage_path
        self.corrections: Dict[str, Correction] = {}
        self.learned_patterns: Dict[str, LearnedPattern] = {}
        self.metrics = LearningMetrics()
        
        # Thresholds
        self.min_confidence_threshold = 0.6
        self.min_quality_threshold = 0.5
        self.pattern_similarity_threshold = 0.8
        
        # Load existing data if available
        if storage_path:
            self._load_data()
            
    def set_logger(self, logger):
        """Set the logger for this system."""
        self.logger = logger
        
    def _load_data(self) -> None:
        """Load learned patterns and corrections from storage."""
        if not self.storage_path:
            return
            
        try:
            patterns_file = f"{self.storage_path}/learned_patterns.json"
            corrections_file = f"{self.storage_path}/corrections.json"
            metrics_file = f"{self.storage_path}/metrics.json"
            
            # Load patterns
            try:
                with open(patterns_file, 'r') as f:
                    data = json.load(f)
                    for p_data in data.get('patterns', []):
                        pattern = LearnedPattern(
                            pattern_id=p_data['pattern_id'],
                            source=PatternSource(p_data['source']),
                            java_pattern=p_data['java_pattern'],
                            bedrock_pattern=p_data['bedrock_pattern'],
                            confidence=p_data['confidence'],
                            usage_count=p_data.get('usage_count', 0),
                            success_count=p_data.get('success_count', 0),
                            version=p_data.get('version', 1),
                            created_at=datetime.fromisoformat(p_data.get('created_at', datetime.now().isoformat())),
                            last_used=datetime.fromisoformat(p_data['last_used']) if p_data.get('last_used') else None,
                            parent_pattern_id=p_data.get('parent_pattern_id'),
                            description=p_data.get('description', ''),
                            examples=p_data.get('examples', [])
                        )
                        self.learned_patterns[pattern.pattern_id] = pattern
            except FileNotFoundError:
                pass
                
            # Load corrections
            try:
                with open(corrections_file, 'r') as f:
                    data = json.load(f)
                    for c_data in data.get('corrections', []):
                        correction = Correction(
                            id=c_data['id'],
                            original_code=c_data['original_code'],
                            corrected_code=c_data['corrected_code'],
                            correction_type=CorrectionType(c_data['correction_type']),
                            impact=CorrectionImpact(c_data['impact']),
                            context=c_data.get('context', {}),
                            timestamp=datetime.fromisoformat(c_data['timestamp']),
                            source_file=c_data.get('source_file', ''),
                            user_id=c_data.get('user_id'),
                            quality_score=c_data.get('quality_score', 0.0),
                            applied=c_data.get('applied', False)
                        )
                        self.corrections[correction.id] = correction
            except FileNotFoundError:
                pass
                
            # Load metrics
            try:
                with open(metrics_file, 'r') as f:
                    data = json.load(f)
                    self.metrics = LearningMetrics(
                        total_corrections=data.get('total_corrections', 0),
                        patterns_learned=data.get('patterns_learned', 0),
                        patterns_applied=data.get('patterns_applied', 0),
                        successful_applications=data.get('successful_applications', 0),
                        average_quality_score=data.get('average_quality_score', 0.0),
                        last_pattern_added=datetime.fromisoformat(data['last_pattern_added']) if data.get('last_pattern_added') else None
                    )
            except FileNotFoundError:
                pass
                
            if self.logger:
                self.logger.info(f"Loaded {len(self.learned_patterns)} learned patterns and {len(self.corrections)} corrections")
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to load learning data: {e}")
                
    def _save_data(self) -> None:
        """Save learned patterns and corrections to storage."""
        if not self.storage_path:
            return
            
        try:
            patterns_file = f"{self.storage_path}/learned_patterns.json"
            corrections_file = f"{self.storage_path}/corrections.json"
            metrics_file = f"{self.storage_path}/metrics.json"
            
            # Save patterns
            patterns_data = {
                'patterns': [
                    {
                        'pattern_id': p.pattern_id,
                        'source': p.source.value,
                        'java_pattern': p.java_pattern,
                        'bedrock_pattern': p.bedrock_pattern,
                        'confidence': p.confidence,
                        'usage_count': p.usage_count,
                        'success_count': p.success_count,
                        'version': p.version,
                        'created_at': p.created_at.isoformat(),
                        'last_used': p.last_used.isoformat() if p.last_used else None,
                        'parent_pattern_id': p.parent_pattern_id,
                        'description': p.description,
                        'examples': p.examples
                    }
                    for p in self.learned_patterns.values()
                ]
            }
            with open(patterns_file, 'w') as f:
                json.dump(patterns_data, f, indent=2)
                
            # Save corrections
            corrections_data = {
                'corrections': [
                    {
                        'id': c.id,
                        'original_code': c.original_code,
                        'corrected_code': c.corrected_code,
                        'correction_type': c.correction_type.value,
                        'impact': c.impact.value,
                        'context': c.context,
                        'timestamp': c.timestamp.isoformat(),
                        'source_file': c.source_file,
                        'user_id': c.user_id,
                        'quality_score': c.quality_score,
                        'applied': c.applied
                    }
                    for c in self.corrections.values()
                ]
            }
            with open(corrections_file, 'w') as f:
                json.dump(corrections_data, f, indent=2)
                
            # Save metrics
            with open(metrics_file, 'w') as f:
                json.dump(self.metrics.to_dict(), f, indent=2)
                
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to save learning data: {e}")
    
    def track_correction(
        self,
        original_code: str,
        corrected_code: str,
        context: Dict[str, Any],
        source_file: str,
        user_id: Optional[str] = None
    ) -> Correction:
        """
        Track a user correction.
        
        Args:
            original_code: The original (incorrect) code
            corrected_code: The corrected code
            context: Context about the conversion
            source_file: Source file path
            user_id: Optional user identifier
            
        Returns:
            The created Correction object
        """
        # Classify the correction
        correction_type = self._classify_correction(original_code, corrected_code)
        impact = self._calculate_impact(original_code, corrected_code)
        
        # Create correction
        correction = Correction(
            id="",  # Will be generated
            original_code=original_code,
            corrected_code=corrected_code,
            correction_type=correction_type,
            impact=impact,
            context=context,
            timestamp=datetime.now(),
            source_file=source_file,
            user_id=user_id,
            quality_score=0.0,  # Will be calculated
            applied=False
        )
        
        # Calculate quality score
        correction.quality_score = self._calculate_quality_score(correction)
        
        # Store correction
        self.corrections[correction.id] = correction
        self.metrics.total_corrections += 1
        
        # Try to extract pattern if quality is sufficient
        if correction.quality_score >= self.min_quality_threshold:
            self._extract_pattern_from_correction(correction)
        
        # Update metrics
        self._update_metrics()
        
        # Save data
        self._save_data()
        
        if self.logger:
            self.logger.info(f"Tracked correction {correction.id}: {correction_type.value} ({impact.value})")
            
        return correction
    
    def _classify_correction(self, original: str, corrected: str) -> CorrectionType:
        """Classify the type of correction."""
        # Check for API changes
        if self._is_api_change(original, corrected):
            return CorrectionType.API
            
        # Check for semantic changes (variable names, logic)
        if self._is_semantic_change(original, corrected):
            return CorrectionType.SEMANTIC
            
        # Check for pattern changes
        if self._is_pattern_change(original, corrected):
            return CorrectionType.PATTERN
            
        # Check for syntax changes
        if self._is_syntax_change(original, corrected):
            return CorrectionType.SYNTAX
            
        # Check for formatting
        if self._is_formatting_change(original, corrected):
            return CorrectionType.FORMATTING
            
        # Default to logic
        return CorrectionType.LOGIC
    
    def _is_api_change(self, original: str, corrected: str) -> bool:
        """Check if correction is an API mapping change."""
        api_patterns = [
            r'\b(Block|Item|Entity|World)\.',
            r'extends\s+\w+',
            r'implements\s+\w+',
            r'RegistryObject',
            r'ForgeRegistry',
        ]
        
        original_apis = set()
        corrected_apis = set()
        
        for pattern in api_patterns:
            original_apis.update(re.findall(pattern, original))
            corrected_apis.update(re.findall(pattern, corrected))
            
        return original_apis != corrected_apis
    
    def _is_semantic_change(self, original: str, corrected: str) -> bool:
        """Check if correction is semantic (meaning preservation)."""
        # Check for variable name changes
        original_vars = set(re.findall(r'\b[a-z][a-zA-Z0-9]*\b', original))
        corrected_vars = set(re.findall(r'\b[a-z][a-zA-Z0-9]*\b', corrected))
        
        # If many variables changed, it's semantic
        changed_vars = original_vars.symmetric_difference(corrected_vars)
        if len(changed_vars) > 3:
            return True
            
        # Check for logic changes (operators, conditions)
        original_logic = set(re.findall(r'[!=<>]=?|&&|\|\||\?', original))
        corrected_logic = set(re.findall(r'[!=<>]=?|&&|\|\||\?', corrected))
        
        return original_logic != corrected_logic
    
    def _is_pattern_change(self, original: str, corrected: str) -> bool:
        """Check if correction relates to pattern matching."""
        pattern_keywords = [
            'Block', 'Item', 'Entity', 'Recipe', 'Event',
            'Registry', 'Registration', 'Property', 'State'
        ]
        
        for keyword in pattern_keywords:
            if keyword in original or keyword in corrected:
                # Check if the structure changed but keyword remains
                if original.count(keyword) == corrected.count(keyword):
                    return True
                    
        return False
    
    def _is_syntax_change(self, original: str, corrected: str) -> bool:
        """Check if correction is syntax-level."""
        # Count braces, parentheses, semicolons
        original_syntax = (
            original.count('{') + original.count('}') +
            original.count('(') + original.count(')') +
            original.count(';')
        )
        corrected_syntax = (
            corrected.count('{') + corrected.count('}') +
            corrected.count('(') + corrected.count(')') +
            corrected.count(';')
        )
        
        return abs(original_syntax - corrected_syntax) > 2
    
    def _is_formatting_change(self, original: str, corrected: str) -> bool:
        """Check if correction is purely formatting."""
        # Remove whitespace and compare
        original_clean = re.sub(r'\s+', '', original)
        corrected_clean = re.sub(r'\s+', '', corrected)
        
        # If the content is the same, it's formatting
        return original_clean == corrected_clean
    
    def _calculate_impact(self, original: str, corrected: str) -> CorrectionImpact:
        """Calculate the impact level of a correction."""
        # Calculate difference ratio
        original_len = max(len(original), 1)
        corrected_len = max(len(corrected), 1)
        
        # Simple diff approximation
        original_lines = len(original.split('\n'))
        corrected_lines = len(corrected.split('\n'))
        
        line_diff = abs(original_lines - corrected_lines)
        
        if line_diff <= 2 and len(corrected) <= len(original) * 1.2:
            return CorrectionImpact.MINOR
        elif line_diff <= 10:
            return CorrectionImpact.MODERATE
        else:
            return CorrectionImpact.MAJOR
    
    def _calculate_quality_score(self, correction: Correction) -> float:
        """
        Calculate quality score for a correction.
        
        Higher scores indicate more suitable corrections for pattern learning.
        """
        score = 0.5  # Base score
        
        # Boost for PATTERN and SEMANTIC corrections (more valuable for learning)
        if correction.correction_type in [CorrectionType.PATTERN, CorrectionType.SEMANTIC]:
            score += 0.2
            
        # Boost for MODERATE and MAJOR impact (minor changes less valuable)
        if correction.impact in [CorrectionImpact.MODERATE, CorrectionImpact.MAJOR]:
            score += 0.15
            
        # Check if correction has sufficient context
        if correction.context:
            score += 0.1
            
        # Boost if correction is from a complete method/class
        if '{' in correction.original_code and '}' in correction.original_code:
            score += 0.1
            
        return min(1.0, score)
    
    def _extract_pattern_from_correction(self, correction: Correction) -> Optional[LearnedPattern]:
        """
        Extract a reusable pattern from a correction.
        
        Args:
            correction: The correction to extract from
            
        Returns:
            The extracted pattern, or None if not suitable
        """
        # Only extract from PATTERN and SEMANTIC corrections
        if correction.correction_type not in [CorrectionType.PATTERN, CorrectionType.SEMANTIC]:
            return None
            
        # Generate pattern from original -> corrected mapping
        java_pattern = self._generalize_code(correction.original_code)
        bedrock_pattern = self._generalize_code(correction.corrected_code)
        
        if not java_pattern or not bedrock_pattern:
            return None
            
        # Check for similar existing patterns
        similar = self._find_similar_patterns(java_pattern)
        if similar:
            # Update existing pattern instead of creating new
            existing_pattern = similar[0][0]
            existing_pattern.examples.append(correction.original_code)
            if self.logger:
                self.logger.info(f"Updated existing pattern {existing_pattern.pattern_id}")
            return existing_pattern
            
        # Create new learned pattern
        pattern_id = f"learned_{hashlib.md5(java_pattern.encode()).hexdigest()[:8]}"
        
        pattern = LearnedPattern(
            pattern_id=pattern_id,
            source=PatternSource.LEARNED,
            java_pattern=java_pattern,
            bedrock_pattern=bedrock_pattern,
            confidence=correction.quality_score,
            examples=[correction.original_code],
            description=f"Learned from {correction.correction_type.value} correction"
        )
        
        self.learned_patterns[pattern.pattern_id] = pattern
        self.metrics.patterns_learned += 1
        self.metrics.last_pattern_added = datetime.now()
        
        if self.logger:
            self.logger.info(f"Extracted new pattern: {pattern_id}")
            
        return pattern
    
    def _generalize_code(self, code: str) -> str:
        """
        Generalize code to create a reusable pattern.
        
        Replaces specific names with placeholders.
        """
        # Replace specific class names
        generalized = re.sub(r'\b[A-Z][a-zA-Z0-9]*Block\b', '${BLOCK}', code)
        generalized = re.sub(r'\b[A-Z][a-zA-Z0-9]*Item\b', '${ITEM}', generalized)
        generalized = re.sub(r'\b[A-Z][a-zA-Z0-9]*Entity\b', '${ENTITY}', generalized)
        generalized = re.sub(r'\b[A-Z][a-zA-Z0-9]+\b', '${NAME}', generalized)
        
        return generalized
    
    def _find_similar_patterns(self, java_pattern: str) -> List[Tuple[LearnedPattern, float]]:
        """
        Find patterns similar to the given pattern.
        
        Returns:
            List of (pattern, similarity) tuples
        """
        similar = []
        
        for pattern in self.learned_patterns.values():
            similarity = self._calculate_pattern_similarity(java_pattern, pattern.java_pattern)
            if similarity >= self.pattern_similarity_threshold:
                similar.append((pattern, similarity))
                
        return sorted(similar, key=lambda x: x[1], reverse=True)
    
    def _calculate_pattern_similarity(self, pattern1: str, pattern2: str) -> float:
        """Calculate similarity between two patterns."""
        # Simple token-based similarity
        tokens1 = set(re.findall(r'\$\{[\w]+\}|[a-z]+', pattern1))
        tokens2 = set(re.findall(r'\$\{[\w]+\}|[a-z]+', pattern2))
        
        if not tokens1 or not tokens2:
            return 0.0
            
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union)
    
    def _update_metrics(self) -> None:
        """Update learning metrics."""
        if self.corrections:
            total_quality = sum(c.quality_score for c in self.corrections.values())
            self.metrics.average_quality_score = total_quality / len(self.corrections)
    
    def get_applicable_patterns(self, java_code: str) -> List[Tuple[LearnedPattern, float]]:
        """
        Get patterns that can be applied to the given Java code.
        
        Args:
            java_code: Java source code to match
            
        Returns:
            List of (pattern, confidence) tuples sorted by confidence
        """
        applicable = []
        
        for pattern in self.learned_patterns.values():
            # Skip low-confidence patterns
            if pattern.confidence < self.min_confidence_threshold:
                continue
                
            # Check if pattern matches
            try:
                regex = re.compile(pattern.java_pattern)
                if regex.search(java_code):
                    applicable.append((pattern, pattern.confidence))
            except re.error:
                continue
                
        return sorted(applicable, key=lambda x: x[1], reverse=True)
    
    def apply_learned_pattern(
        self,
        java_code: str,
        pattern_id: str
    ) -> Tuple[str, bool]:
        """
        Apply a learned pattern to Java code.
        
        Args:
            java_code: Source Java code
            pattern_id: ID of the pattern to apply
            
        Returns:
            Tuple of (modified code, success)
        """
        pattern = self.learned_patterns.get(pattern_id)
        if not pattern:
            return java_code, False
            
        try:
            regex = re.compile(pattern.java_pattern)
            
            def replace_func(match):
                # Extract captured groups
                groups = match.groups()
                result = pattern.bedrock_pattern
                
                for i, group in enumerate(groups, 1):
                    result = result.replace(f'${{{i}}}', group or '')
                    
                return result
            
            modified_code = regex.sub(replace_func, java_code)
            
            # Update pattern metrics
            pattern.update_confidence(successful=True)
            self.metrics.patterns_applied += 1
            
            # Save data
            self._save_data()
            
            return modified_code, True
            
        except re.error as e:
            if self.logger:
                self.logger.warning(f"Failed to apply pattern {pattern_id}: {e}")
            pattern.update_confidence(successful=False)
            return java_code, False
    
    def compare_conversions(
        self,
        original_java: str,
        converted_code: str,
        user_corrected: str
    ) -> Dict[str, Any]:
        """
        Compare conversions to find improvement opportunities.
        
        Args:
            original_java: Original Java code
            converted_code: Initial conversion result
            user_corrected: User-corrected version
            
        Returns:
            Dictionary with comparison results
        """
        results = {
            "has_improvements": False,
            "improvement_types": [],
            "suggested_patterns": [],
            "confidence_change": 0.0
        }
        
        # Track the correction
        correction = self.track_correction(
            original_code=converted_code,
            corrected_code=user_corrected,
            context={
                "original_java": original_java,
                "conversion_source": "auto"
            },
            source_file="comparison"
        )
        
        if correction.quality_score >= 0.5:
            results["has_improvements"] = True
            results["improvement_types"] = [correction.correction_type.value]
            
            # Suggest patterns based on correction
            applicable = self.get_applicable_patterns(user_corrected)
            results["suggested_patterns"] = [
                {"id": p.pattern_id, "confidence": c}
                for p, c in applicable[:3]
            ]
            
        return results
    
    def get_learning_report(self) -> Dict[str, Any]:
        """
        Get a comprehensive learning system report.
        
        Returns:
            Dictionary with learning metrics and insights
        """
        # Calculate pattern statistics
        pattern_stats = {
            "total_patterns": len(self.learned_patterns),
            "high_confidence": sum(1 for p in self.learned_patterns.values() if p.confidence >= 0.8),
            "medium_confidence": sum(1 for p in self.learned_patterns.values() if 0.5 <= p.confidence < 0.8),
            "low_confidence": sum(1 for p in self.learned_patterns.values() if p.confidence < 0.5),
            "by_source": {}
        }
        
        # Count by source
        for pattern in self.learned_patterns.values():
            source = pattern.source.value
            pattern_stats["by_source"][source] = pattern_stats["by_source"].get(source, 0) + 1
            
        # Correction statistics
        correction_stats = {
            "total": len(self.corrections),
            "by_type": {},
            "by_impact": {}
        }
        
        for correction in self.corrections.values():
            ctype = correction.correction_type.value
            impact = correction.impact.value
            correction_stats["by_type"][ctype] = correction_stats["by_type"].get(ctype, 0) + 1
            correction_stats["by_impact"][impact] = correction_stats["by_impact"].get(impact, 0) + 1
            
        return {
            "metrics": self.metrics.to_dict(),
            "pattern_stats": pattern_stats,
            "correction_stats": correction_stats,
            "success_rate": (
                self.metrics.successful_applications / self.metrics.patterns_applied
                if self.metrics.patterns_applied > 0 else 0.0
            )
        }
    
    def rollback_pattern(self, pattern_id: str) -> bool:
        """
        Rollback a learned pattern to a previous version.
        
        Args:
            pattern_id: ID of the pattern to rollback
            
        Returns:
            True if successful
        """
        pattern = self.learned_patterns.get(pattern_id)
        if not pattern or pattern.source != PatternSource.LEARNED:
            return False
            
        # Simple rollback: reduce confidence and reset usage
        pattern.confidence = max(0.3, pattern.confidence - 0.2)
        pattern.version += 1
        
        if self.logger:
            self.logger.info(f"Rolled back pattern {pattern_id} to version {pattern.version}")
            
        self._save_data()
        return True
    
    def export_patterns(self) -> List[Dict[str, Any]]:
        """
        Export all learned patterns.
        
        Returns:
            List of pattern dictionaries
        """
        return [
            {
                "pattern_id": p.pattern_id,
                "source": p.source.value,
                "java_pattern": p.java_pattern,
                "bedrock_pattern": p.bedrock_pattern,
                "confidence": p.confidence,
                "usage_count": p.usage_count,
                "version": p.version,
                "description": p.description,
                "examples": p.examples
            }
            for p in self.learned_patterns.values()
        ]


def create_self_learning_system(storage_path: Optional[str] = None) -> SelfLearningSystem:
    """
    Factory function to create a self-learning system.
    
    Args:
        storage_path: Optional path for persisting learned patterns
        
    Returns:
        SelfLearningSystem instance
    """
    return SelfLearningSystem(storage_path=storage_path)
