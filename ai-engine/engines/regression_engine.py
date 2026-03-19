"""
Regression Detection Engine

This module provides baseline storage, comparison, and regression detection
for the QA Suite (Phase 09).

Features:
- Baseline storage for known-good conversions
- Baseline comparison engine
- Diff generation
- Regression scoring
- Historical tracking
"""

import json
import hashlib
import os
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Baseline:
    """Represents a baseline conversion for comparison."""
    baseline_id: str
    conversion_id: str
    mod_type: str
    created_at: str
    java_code_hash: str
    bedrock_code_hash: str
    validation_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DiffResult:
    """Represents a diff between two conversions."""
    diff_id: str
    baseline_id: str
    new_conversion_id: str
    created_at: str
    structural_changes: Dict[str, Any]
    code_changes: Dict[str, Any]
    asset_changes: Dict[str, Any]
    added_lines: int = 0
    removed_lines: int = 0
    modified_lines: int = 0


@dataclass
class RegressionResult:
    """Result of regression detection."""
    regression_detected: bool
    regression_score: float  # 0.0 = no regression, 1.0 = full regression
    severity: str  # "none", "minor", "moderate", "major", "critical"
    baseline_id: str
    new_conversion_id: str
    changes: List[str]
    score_breakdown: Dict[str, float]


class BaselineStorage:
    """Manages storage and retrieval of baseline conversions."""
    
    def __init__(self, storage_path: str = "data/baselines"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.baselines: Dict[str, Baseline] = {}
        self._load_baselines()
    
    def _load_baselines(self):
        """Load baselines from storage."""
        index_file = self.storage_path / "index.json"
        if index_file.exists():
            with open(index_file, 'r') as f:
                data = json.load(f)
                for bid, bdata in data.items():
                    self.baselines[bid] = Baseline(**bdata)
    
    def _save_index(self):
        """Save baselines index to storage."""
        index_file = self.storage_path / "index.json"
        data = {bid: {
            'baseline_id': b.baseline_id,
            'conversion_id': b.conversion_id,
            'mod_type': b.mod_type,
            'created_at': b.created_at,
            'java_code_hash': b.java_code_hash,
            'bedrock_code_hash': b.bedrock_code_hash,
            'validation_score': b.validation_score,
            'metadata': b.metadata
        } for bid, b in self.baselines.items()}
        with open(index_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _compute_hash(self, content: str) -> str:
        """Compute SHA256 hash of content."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    def store_baseline(
        self,
        conversion_id: str,
        mod_type: str,
        java_code: str,
        bedrock_code: str,
        validation_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Baseline:
        """Store a new baseline."""
        baseline_id = f"baseline_{self._compute_hash(conversion_id + datetime.now().isoformat())}"
        
        baseline = Baseline(
            baseline_id=baseline_id,
            conversion_id=conversion_id,
            mod_type=mod_type,
            created_at=datetime.now().isoformat(),
            java_code_hash=self._compute_hash(java_code),
            bedrock_code_hash=self._compute_hash(bedrock_code),
            validation_score=validation_score,
            metadata=metadata or {}
        )
        
        # Store baseline data
        baseline_file = self.storage_path / f"{baseline_id}.json"
        with open(baseline_file, 'w') as f:
            json.dump({
                'baseline_id': baseline_id,
                'conversion_id': conversion_id,
                'mod_type': mod_type,
                'java_code': java_code,
                'bedrock_code': bedrock_code,
                'created_at': baseline.created_at,
                'validation_score': validation_score,
                'metadata': baseline.metadata
            }, f, indent=2)
        
        # Update index
        self.baselines[baseline_id] = baseline
        self._save_index()
        
        return baseline
    
    def get_baseline(self, baseline_id: str) -> Optional[Baseline]:
        """Retrieve a baseline by ID."""
        return self.baselines.get(baseline_id)
    
    def get_baseline_by_conversion(self, conversion_id: str) -> Optional[Baseline]:
        """Retrieve the latest baseline for a conversion."""
        matching = [b for b in self.baselines.values() if b.conversion_id == conversion_id]
        if matching:
            return max(matching, key=lambda b: b.created_at)
        return None
    
    def get_baselines_by_type(self, mod_type: str) -> List[Baseline]:
        """Get all baselines for a specific mod type."""
        return [b for b in self.baselines.values() if b.mod_type == mod_type]
    
    def list_baselines(self) -> List[Baseline]:
        """List all baselines."""
        return list(self.baselines.values())


class DiffGenerator:
    """Generates diffs between baseline and new conversions."""
    
    def generate_diff(
        self,
        baseline_id: str,
        baseline_code: str,
        new_code: str,
        new_conversion_id: str
    ) -> DiffResult:
        """Generate a diff between baseline and new code."""
        diff_id = f"diff_{hashlib.sha256((baseline_id + new_conversion_id).encode()).hexdigest()[:16]}"
        
        # Calculate line-by-line diff
        baseline_lines = baseline_code.split('\n')
        new_lines = new_code.split('\n')
        
        added_lines = 0
        removed_lines = 0
        
        # Simple diff calculation
        baseline_set = set(baseline_lines)
        new_set = set(new_lines)
        
        added_lines = len(new_set - baseline_set)
        removed_lines = len(baseline_set - new_set)
        
        # Calculate structural changes
        structural_changes = self._analyze_structural_changes(baseline_code, new_code)
        
        # Calculate code changes
        code_changes = self._analyze_code_changes(baseline_code, new_code)
        
        # Calculate asset changes
        asset_changes = self._analyze_asset_changes(baseline_code, new_code)
        
        return DiffResult(
            diff_id=diff_id,
            baseline_id=baseline_id,
            new_conversion_id=new_conversion_id,
            created_at=datetime.now().isoformat(),
            structural_changes=structural_changes,
            code_changes=code_changes,
            asset_changes=asset_changes,
            added_lines=added_lines,
            removed_lines=removed_lines,
            modified_lines=min(added_lines, removed_lines)
        )
    
    def _analyze_structural_changes(self, old_code: str, new_code: str) -> Dict[str, Any]:
        """Analyze structural changes between code."""
        changes = {}
        
        # Check for function changes
        old_funcs = set()
        new_funcs = set()
        
        import re
        old_funcs = set(re.findall(r'function\s+(\w+)', old_code))
        new_funcs = set(re.findall(r'function\s+(\w+)', new_code))
        
        changes['functions_added'] = list(new_funcs - old_funcs)
        changes['functions_removed'] = list(old_funcs - new_funcs)
        
        # Check for class changes
        old_classes = set(re.findall(r'class\s+(\w+)', old_code))
        new_classes = set(re.findall(r'class\s+(\w+)', new_code))
        
        changes['classes_added'] = list(new_classes - old_classes)
        changes['classes_removed'] = list(old_classes - new_classes)
        
        return changes
    
    def _analyze_code_changes(self, old_code: str, new_code: str) -> Dict[str, Any]:
        """Analyze code-level changes."""
        changes = {}
        
        old_lines = old_code.split('\n')
        new_lines = new_code.split('\n')
        
        changes['old_line_count'] = len(old_lines)
        changes['new_line_count'] = len(new_lines)
        changes['line_delta'] = len(new_lines) - len(old_lines)
        
        # Check complexity changes
        import re
        old_complexity = len(re.findall(r'\b(if|else|for|while|switch|case|try|catch)\b', old_code))
        new_complexity = len(re.findall(r'\b(if|else|for|while|switch|case|try|catch)\b', new_code))
        
        changes['old_complexity'] = old_complexity
        changes['new_complexity'] = new_complexity
        changes['complexity_delta'] = new_complexity - old_complexity
        
        return changes
    
    def _analyze_asset_changes(self, old_code: str, new_code: str) -> Dict[str, Any]:
        """Analyze asset reference changes."""
        import re
        
        # Extract asset references
        old_assets = set(re.findall(r'(minecraft:\w+)["\']?\s*:', old_code))
        new_assets = set(re.findall(r'(minecraft:\w+)["\']?\s*:', new_code))
        
        return {
            'assets_added': list(new_assets - old_assets),
            'assets_removed': list(old_assets - new_assets),
            'total_assets_old': len(old_assets),
            'total_assets_new': len(new_assets)
        }


class RegressionDetector:
    """Detects regressions between baseline and new conversions."""
    
    def __init__(self):
        self.baseline_storage = BaselineStorage()
        self.diff_generator = DiffGenerator()
        
        # Thresholds for regression detection
        self.thresholds = {
            'critical': 0.7,  # >70% score change = critical
            'major': 0.5,     # >50% = major
            'moderate': 0.3,  # >30% = moderate
            'minor': 0.1      # >10% = minor
        }
    
    def detect_regression(
        self,
        baseline_id: str,
        new_conversion_id: str,
        new_java_code: str,
        new_bedrock_code: str,
        new_validation_score: float
    ) -> RegressionResult:
        """Detect regression between baseline and new conversion."""
        
        baseline = self.baseline_storage.get_baseline(baseline_id)
        if not baseline:
            return RegressionResult(
                regression_detected=False,
                regression_score=0.0,
                severity="none",
                baseline_id=baseline_id,
                new_conversion_id=new_conversion_id,
                changes=["Baseline not found"],
                score_breakdown={}
            )
        
        # Load baseline code
        baseline_file = self.baseline_storage.storage_path / f"{baseline_id}.json"
        with open(baseline_file, 'r') as f:
            baseline_data = json.load(f)
        
        baseline_java = baseline_data.get('java_code', '')
        baseline_bedrock = baseline_data.get('bedrock_code', '')
        
        # Generate diffs
        java_diff = self.diff_generator.generate_diff(
            baseline_id, baseline_java, new_java_code, new_conversion_id
        )
        bedrock_diff = self.diff_generator.generate_diff(
            baseline_id, baseline_bedrock, new_bedrock_code, new_conversion_id
        )
        
        # Calculate regression score
        score_breakdown = self._calculate_score_breakdown(
            baseline.validation_score,
            new_validation_score,
            java_diff,
            bedrock_diff,
            baseline
        )
        
        regression_score = (
            score_breakdown['validation_drop'] * 0.5 +
            score_breakdown['structural_change'] * 0.2 +
            score_breakdown['code_change'] * 0.2 +
            score_breakdown['asset_change'] * 0.1
        )
        
        regression_score = min(regression_score, 1.0)
        
        # Determine severity
        severity = "none"
        for sev, threshold in self.thresholds.items():
            if regression_score >= threshold:
                severity = sev
        
        regression_detected = regression_score >= self.thresholds['minor']
        
        # Collect changes
        changes = []
        if score_breakdown['validation_drop'] > 0:
            changes.append(f"Validation score dropped by {score_breakdown['validation_drop']*100:.1f}%")
        if java_diff.added_lines > 0:
            changes.append(f"Java: +{java_diff.added_lines} lines")
        if java_diff.removed_lines > 0:
            changes.append(f"Java: -{java_diff.removed_lines} lines")
        if bedrock_diff.added_lines > 0:
            changes.append(f"Bedrock: +{bedrock_diff.added_lines} lines")
        if bedrock_diff.removed_lines > 0:
            changes.append(f"Bedrock: -{bedrock_diff.removed_lines} lines")
        if java_diff.structural_changes.get('functions_removed'):
            changes.append(f"Functions removed: {java_diff.structural_changes['functions_removed']}")
        
        return RegressionResult(
            regression_detected=regression_detected,
            regression_score=regression_score,
            severity=severity,
            baseline_id=baseline_id,
            new_conversion_id=new_conversion_id,
            changes=changes,
            score_breakdown=score_breakdown
        )
    
    def _calculate_score_breakdown(
        self,
        baseline_score: float,
        new_score: float,
        java_diff: DiffResult,
        bedrock_diff: DiffResult,
        baseline: Baseline
    ) -> Dict[str, float]:
        """Calculate detailed score breakdown."""
        
        # Validation score drop (0.0 - 1.0)
        validation_drop = max(0.0, baseline_score - new_score)
        
        # Structural change (0.0 - 1.0)
        total_funcs = max(1, len(java_diff.structural_changes.get('functions_added', [])) + 
                         len(java_diff.structural_changes.get('functions_removed', [])))
        structural_change = min(total_funcs / 10.0, 1.0)
        
        # Code change (0.0 - 1.0)
        code_change = 0.0
        if java_diff.removed_lines > 0 or java_diff.added_lines > 0:
            baseline_lines = java_diff.removed_lines + java_diff.added_lines
            code_change = min(baseline_lines / 100.0, 1.0)
        
        # Asset change (0.0 - 1.0)
        asset_change = 0.0
        total_asset_changes = (len(java_diff.asset_changes.get('assets_added', [])) +
                              len(java_diff.asset_changes.get('assets_removed', [])))
        asset_change = min(total_asset_changes / 5.0, 1.0)
        
        return {
            'validation_drop': validation_drop,
            'structural_change': structural_change,
            'code_change': code_change,
            'asset_change': asset_change
        }
    
    def store_and_compare(
        self,
        conversion_id: str,
        mod_type: str,
        java_code: str,
        bedrock_code: str,
        validation_score: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Tuple[Baseline, Optional[RegressionResult]]:
        """Store new conversion and compare with baseline."""
        
        # Check if baseline exists for this conversion
        existing_baseline = self.baseline_storage.get_baseline_by_conversion(conversion_id)
        
        # Store new baseline
        baseline = self.baseline_storage.store_baseline(
            conversion_id=conversion_id,
            mod_type=mod_type,
            java_code=java_code,
            bedrock_code=bedrock_code,
            validation_score=validation_score,
            metadata=metadata
        )
        
        # Compare with previous baseline if exists
        regression_result = None
        if existing_baseline:
            regression_result = self.detect_regression(
                baseline_id=existing_baseline.baseline_id,
                new_conversion_id=conversion_id,
                new_java_code=java_code,
                new_bedrock_code=bedrock_code,
                new_validation_score=validation_score
            )
        
        return baseline, regression_result


# Singleton for easy access
_regression_detector: Optional[RegressionDetector] = None

def get_regression_detector() -> RegressionDetector:
    """Get or create the regression detector singleton."""
    global _regression_detector
    if _regression_detector is None:
        _regression_detector = RegressionDetector()
    return _regression_detector
