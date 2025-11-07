"""
Quality Scoring System for Conversion Assessment
Provides automated quality scoring metrics for mod conversion outcomes.
"""

import json
import logging
import os
import zipfile
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class QualityMetrics:
    """Container for all quality assessment metrics"""
    overall_score: float
    completeness_score: float
    correctness_score: float
    performance_score: float
    compatibility_score: float
    user_experience_score: float
    
    # Detailed breakdowns
    file_structure_score: float
    manifest_validity_score: float
    asset_conversion_score: float
    behavior_correctness_score: float
    recipe_correctness_score: float
    
    # Raw counts and data
    total_blocks: int
    converted_blocks: int
    total_items: int
    converted_items: int
    total_recipes: int
    converted_recipes: int
    total_assets: int
    converted_assets: int
    
    # Error tracking
    critical_errors: List[str]
    warnings: List[str]
    missing_features: List[str]
    
    timestamp: str
    conversion_time_seconds: float

class ConversionQualityScorer:
    """
    Automated quality assessment system for mod conversions.
    Evaluates conversion outcomes across multiple dimensions.
    """
    
    def __init__(self):
        self.weights = {
            'completeness': 0.25,
            'correctness': 0.30,
            'performance': 0.15,
            'compatibility': 0.15,
            'user_experience': 0.15
        }
        
        # Minimum thresholds for quality gates
        self.quality_thresholds = {
            'excellent': 0.9,
            'good': 0.75,
            'acceptable': 0.6,
            'poor': 0.4,
            'failed': 0.0
        }

    def assess_conversion_quality(
        self, 
        original_mod_path: str,
        converted_addon_path: str,
        conversion_metadata: Dict[str, Any],
        user_feedback: Optional[Dict[str, Any]] = None
    ) -> QualityMetrics:
        """
        Comprehensive quality assessment of a mod conversion.
        
        Args:
            original_mod_path: Path to original Java mod
            converted_addon_path: Path to converted Bedrock addon
            conversion_metadata: Metadata from conversion process
            user_feedback: Optional user feedback data
            
        Returns:
            QualityMetrics object containing all assessment results
        """
        logger.info(f"Starting quality assessment for conversion: {original_mod_path} -> {converted_addon_path}")
        
        start_time = datetime.now()
        
        # Initialize metrics container
        metrics = QualityMetrics(
            overall_score=0.0,
            completeness_score=0.0,
            correctness_score=0.0,
            performance_score=0.0,
            compatibility_score=0.0,
            user_experience_score=0.0,
            file_structure_score=0.0,
            manifest_validity_score=0.0,
            asset_conversion_score=0.0,
            behavior_correctness_score=0.0,
            recipe_correctness_score=0.0,
            total_blocks=0,
            converted_blocks=0,
            total_items=0,
            converted_items=0,
            total_recipes=0,
            converted_recipes=0,
            total_assets=0,
            converted_assets=0,
            critical_errors=[],
            warnings=[],
            missing_features=[],
            timestamp=datetime.now().isoformat(),
            conversion_time_seconds=0.0
        )
        
        try:
            # 1. Analyze original mod to establish baseline
            original_analysis = self._analyze_original_mod(original_mod_path)
            
            # 2. Analyze converted addon
            converted_analysis = self._analyze_converted_addon(converted_addon_path)
            
            # 3. Calculate individual dimension scores
            metrics.completeness_score = self._calculate_completeness_score(
                original_analysis, converted_analysis, metrics
            )
            
            metrics.correctness_score = self._calculate_correctness_score(
                converted_analysis, metrics
            )
            
            metrics.performance_score = self._calculate_performance_score(
                converted_analysis, conversion_metadata, metrics
            )
            
            metrics.compatibility_score = self._calculate_compatibility_score(
                converted_analysis, metrics
            )
            
            metrics.user_experience_score = self._calculate_user_experience_score(
                converted_analysis, user_feedback, metrics
            )
            
            # 4. Calculate weighted overall score
            metrics.overall_score = (
                metrics.completeness_score * self.weights['completeness'] +
                metrics.correctness_score * self.weights['correctness'] +
                metrics.performance_score * self.weights['performance'] +
                metrics.compatibility_score * self.weights['compatibility'] +
                metrics.user_experience_score * self.weights['user_experience']
            )
            
            # 5. Record timing
            end_time = datetime.now()
            metrics.conversion_time_seconds = (end_time - start_time).total_seconds()
            
            logger.info(f"Quality assessment completed. Overall score: {metrics.overall_score:.3f}")
            
        except Exception as e:
            logger.error(f"Error during quality assessment: {e}", exc_info=True)
            metrics.critical_errors.append(f"Assessment failed: {str(e)}")
            metrics.overall_score = 0.0
            
        return metrics

    def _analyze_original_mod(self, mod_path: str) -> Dict[str, Any]:
        """Analyze the original Java mod to establish conversion baseline."""
        analysis = {
            'blocks': [],
            'items': [],
            'recipes': [],
            'assets': [],
            'complexity_score': 0.0,
            'mod_type': 'unknown',
            'total_files': 0
        }
        
        try:
            if not os.path.exists(mod_path):
                logger.warning(f"Original mod path not found: {mod_path}")
                return analysis
                
            if mod_path.endswith('.jar'):
                # Analyze JAR file
                with zipfile.ZipFile(mod_path, 'r') as jar:
                    file_list = jar.namelist()
                    analysis['total_files'] = len(file_list)
                    
                    # Look for common mod structure patterns
                    for file_path in file_list:
                        if 'blocks' in file_path.lower() or 'block' in file_path.lower():
                            analysis['blocks'].append(file_path)
                        elif 'items' in file_path.lower() or 'item' in file_path.lower():
                            analysis['items'].append(file_path)
                        elif 'recipe' in file_path.lower():
                            analysis['recipes'].append(file_path)
                        elif any(ext in file_path.lower() for ext in ['.png', '.jpg', '.json', '.mcmeta']):
                            analysis['assets'].append(file_path)
                    
                    # Estimate complexity based on file count and structure
                    analysis['complexity_score'] = min(1.0, len(file_list) / 100.0)
                    
            elif os.path.isdir(mod_path):
                # Analyze directory structure
                for root, dirs, files in os.walk(mod_path):
                    analysis['total_files'] += len(files)
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, mod_path)
                        
                        if 'block' in rel_path.lower():
                            analysis['blocks'].append(rel_path)
                        elif 'item' in rel_path.lower():
                            analysis['items'].append(rel_path)
                        elif 'recipe' in rel_path.lower():
                            analysis['recipes'].append(rel_path)
                        elif any(ext in file.lower() for ext in ['.png', '.jpg', '.json']):
                            analysis['assets'].append(rel_path)
                            
        except Exception as e:
            logger.error(f"Error analyzing original mod: {e}")
            
        return analysis

    def _analyze_converted_addon(self, addon_path: str) -> Dict[str, Any]:
        """Analyze the converted Bedrock addon."""
        analysis = {
            'has_behavior_pack': False,
            'has_resource_pack': False,
            'behavior_pack_structure': {},
            'resource_pack_structure': {},
            'blocks': [],
            'items': [],
            'recipes': [],
            'assets': [],
            'manifests': [],
            'errors': [],
            'total_files': 0
        }
        
        try:
            if not os.path.exists(addon_path):
                logger.warning(f"Converted addon path not found: {addon_path}")
                analysis['errors'].append("Addon path not found")
                return analysis
                
            if addon_path.endswith('.mcaddon') or addon_path.endswith('.zip'):
                # Analyze zip/mcaddon file
                with zipfile.ZipFile(addon_path, 'r') as addon_zip:
                    file_list = addon_zip.namelist()
                    analysis['total_files'] = len(file_list)
                    
                    self._analyze_addon_structure(file_list, analysis)
                    
            elif os.path.isdir(addon_path):
                # Analyze directory structure
                for root, dirs, files in os.walk(addon_path):
                    analysis['total_files'] += len(files)
                    
                    # Check for pack directories
                    if any('behavior' in d.lower() or 'bp' in d.lower() for d in dirs):
                        analysis['has_behavior_pack'] = True
                    if any('resource' in d.lower() or 'rp' in d.lower() for d in dirs):
                        analysis['has_resource_pack'] = True
                        
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, addon_path)
                        self._categorize_addon_file(rel_path, analysis)
                        
        except Exception as e:
            logger.error(f"Error analyzing converted addon: {e}")
            analysis['errors'].append(f"Analysis error: {str(e)}")
            
        return analysis

    def _analyze_addon_structure(self, file_list: List[str], analysis: Dict[str, Any]):
        """Analyze the structure of files in an addon archive."""
        for file_path in file_list:
            # Check for pack types
            if any(term in file_path.lower() for term in ['behavior', 'bp']):
                analysis['has_behavior_pack'] = True
            if any(term in file_path.lower() for term in ['resource', 'rp']):
                analysis['has_resource_pack'] = True
                
            self._categorize_addon_file(file_path, analysis)

    def _categorize_addon_file(self, file_path: str, analysis: Dict[str, Any]):
        """Categorize a file within the addon structure."""
        lower_path = file_path.lower()
        
        if 'manifest.json' in lower_path:
            analysis['manifests'].append(file_path)
        elif 'blocks' in lower_path and file_path.endswith('.json'):
            analysis['blocks'].append(file_path)
        elif 'items' in lower_path and file_path.endswith('.json'):
            analysis['items'].append(file_path)
        elif 'recipes' in lower_path and file_path.endswith('.json'):
            analysis['recipes'].append(file_path)
        elif any(ext in lower_path for ext in ['.png', '.jpg', '.tga']):
            analysis['assets'].append(file_path)

    def _calculate_completeness_score(
        self, 
        original: Dict[str, Any], 
        converted: Dict[str, Any], 
        metrics: QualityMetrics
    ) -> float:
        """Calculate how complete the conversion is relative to the original."""
        
        # Update metrics with counts
        metrics.total_blocks = len(original.get('blocks', []))
        metrics.converted_blocks = len(converted.get('blocks', []))
        metrics.total_items = len(original.get('items', []))
        metrics.converted_items = len(converted.get('items', []))
        metrics.total_recipes = len(original.get('recipes', []))
        metrics.converted_recipes = len(converted.get('recipes', []))
        metrics.total_assets = len(original.get('assets', []))
        metrics.converted_assets = len(converted.get('assets', []))
        
        # Calculate completion ratios
        ratios = []
        
        if metrics.total_blocks > 0:
            block_ratio = min(1.0, metrics.converted_blocks / metrics.total_blocks)
            ratios.append(block_ratio)
        else:
            ratios.append(1.0)  # No blocks to convert
            
        if metrics.total_items > 0:
            item_ratio = min(1.0, metrics.converted_items / metrics.total_items)
            ratios.append(item_ratio)
        else:
            ratios.append(1.0)
            
        if metrics.total_recipes > 0:
            recipe_ratio = min(1.0, metrics.converted_recipes / metrics.total_recipes)
            ratios.append(recipe_ratio)
        else:
            ratios.append(1.0)
            
        if metrics.total_assets > 0:
            asset_ratio = min(1.0, metrics.converted_assets / metrics.total_assets)
            ratios.append(asset_ratio)
        else:
            ratios.append(1.0)
        
        # Weighted average of completion ratios
        completeness = sum(ratios) / len(ratios) if ratios else 0.0
        
        # Check for critical missing components
        if not converted.get('has_behavior_pack', False):
            metrics.missing_features.append("Behavior pack missing")
            completeness *= 0.5
            
        if not converted.get('has_resource_pack', False):
            metrics.missing_features.append("Resource pack missing")
            completeness *= 0.8
            
        return min(1.0, completeness)

    def _calculate_correctness_score(
        self, 
        converted: Dict[str, Any], 
        metrics: QualityMetrics
    ) -> float:
        """Calculate the correctness of the converted addon structure."""
        
        correctness_factors = []
        
        # 1. Manifest validation
        manifest_score = self._validate_manifests(converted, metrics)
        metrics.manifest_validity_score = manifest_score
        correctness_factors.append(manifest_score)
        
        # 2. File structure validation
        structure_score = self._validate_file_structure(converted, metrics)
        metrics.file_structure_score = structure_score
        correctness_factors.append(structure_score)
        
        # 3. Behavior correctness (basic validation)
        behavior_score = self._validate_behaviors(converted, metrics)
        metrics.behavior_correctness_score = behavior_score
        correctness_factors.append(behavior_score)
        
        # 4. Recipe correctness
        recipe_score = self._validate_recipes(converted, metrics)
        metrics.recipe_correctness_score = recipe_score
        correctness_factors.append(recipe_score)
        
        # 5. Asset conversion quality
        asset_score = self._validate_assets(converted, metrics)
        metrics.asset_conversion_score = asset_score
        correctness_factors.append(asset_score)
        
        return sum(correctness_factors) / len(correctness_factors) if correctness_factors else 0.0

    def _validate_manifests(self, converted: Dict[str, Any], metrics: QualityMetrics) -> float:
        """Validate manifest files for correctness."""
        manifests = converted.get('manifests', [])
        
        if not manifests:
            metrics.critical_errors.append("No manifest files found")
            return 0.0
            
        # For now, just check presence - could be enhanced to validate JSON structure
        if len(manifests) >= 2:  # Expecting BP and RP manifests
            return 1.0
        elif len(manifests) == 1:
            metrics.warnings.append("Only one manifest found (expecting behavior and resource)")
            return 0.7
        else:
            return 0.0

    def _validate_file_structure(self, converted: Dict[str, Any], metrics: QualityMetrics) -> float:
        """Validate overall file structure correctness."""
        score = 0.0
        
        # Check for basic addon structure
        if converted.get('has_behavior_pack', False):
            score += 0.5
        else:
            metrics.warnings.append("Behavior pack structure not detected")
            
        if converted.get('has_resource_pack', False):
            score += 0.5
        else:
            metrics.warnings.append("Resource pack structure not detected")
            
        return score

    def _validate_behaviors(self, converted: Dict[str, Any], metrics: QualityMetrics) -> float:
        """Validate behavior definitions."""
        blocks = converted.get('blocks', [])
        items = converted.get('items', [])
        
        if not blocks and not items:
            metrics.warnings.append("No block or item behaviors found")
            return 0.5  # Not necessarily an error
            
        # Basic validation - presence of behavior files
        return 1.0 if (blocks or items) else 0.0

    def _validate_recipes(self, converted: Dict[str, Any], metrics: QualityMetrics) -> float:
        """Validate recipe definitions."""
        recipes = converted.get('recipes', [])
        
        # Recipes are optional, so lack of recipes isn't necessarily bad
        return 1.0 if recipes or True else 0.0  # Always pass for now

    def _validate_assets(self, converted: Dict[str, Any], metrics: QualityMetrics) -> float:
        """Validate asset conversion quality."""
        assets = converted.get('assets', [])
        
        if not assets:
            metrics.warnings.append("No texture assets found")
            return 0.7  # Not critical but impacts user experience
            
        return 1.0

    def _calculate_performance_score(
        self, 
        converted: Dict[str, Any], 
        metadata: Dict[str, Any], 
        metrics: QualityMetrics
    ) -> float:
        """Calculate performance-related quality metrics."""
        
        performance_factors = []
        
        # 1. File size efficiency
        total_files = converted.get('total_files', 0)
        if total_files > 0:
            # Prefer fewer, more organized files
            size_efficiency = max(0.0, 1.0 - (total_files / 1000.0))  # Penalty for too many files
            performance_factors.append(size_efficiency)
        else:
            performance_factors.append(0.0)
            
        # 2. Conversion time efficiency
        conversion_time = metadata.get('processing_time_seconds', 0)
        if conversion_time > 0:
            # Prefer faster conversions (under 30 seconds is excellent)
            time_efficiency = max(0.0, 1.0 - (conversion_time / 30.0))
            performance_factors.append(time_efficiency)
        else:
            performance_factors.append(0.5)  # Unknown timing
            
        return sum(performance_factors) / len(performance_factors) if performance_factors else 0.5

    def _calculate_compatibility_score(
        self, 
        converted: Dict[str, Any], 
        metrics: QualityMetrics
    ) -> float:
        """Calculate Bedrock compatibility score."""
        
        compatibility_factors = []
        
        # 1. Proper addon structure
        if converted.get('has_behavior_pack', False) and converted.get('has_resource_pack', False):
            compatibility_factors.append(1.0)
        else:
            compatibility_factors.append(0.5)
            
        # 2. Manifest presence
        manifests = converted.get('manifests', [])
        if len(manifests) >= 2:
            compatibility_factors.append(1.0)
        elif len(manifests) == 1:
            compatibility_factors.append(0.7)
        else:
            compatibility_factors.append(0.0)
            
        # 3. No critical errors
        if not converted.get('errors', []):
            compatibility_factors.append(1.0)
        else:
            compatibility_factors.append(0.3)
            
        return sum(compatibility_factors) / len(compatibility_factors) if compatibility_factors else 0.0

    def _calculate_user_experience_score(
        self, 
        converted: Dict[str, Any], 
        user_feedback: Optional[Dict[str, Any]], 
        metrics: QualityMetrics
    ) -> float:
        """Calculate user experience quality score."""
        
        ux_factors = []
        
        # 1. Asset presence (affects visual quality)
        assets = converted.get('assets', [])
        if assets:
            ux_factors.append(1.0)
        else:
            ux_factors.append(0.5)
            
        # 2. Complete pack structure
        if converted.get('has_behavior_pack', False) and converted.get('has_resource_pack', False):
            ux_factors.append(1.0)
        else:
            ux_factors.append(0.3)
            
        # 3. User feedback integration
        if user_feedback:
            feedback_type = user_feedback.get('feedback_type', '')
            if feedback_type == 'thumbs_up':
                ux_factors.append(1.0)
            elif feedback_type == 'thumbs_down':
                ux_factors.append(0.2)
            else:
                ux_factors.append(0.5)
        else:
            ux_factors.append(0.5)  # Neutral when no feedback
            
        return sum(ux_factors) / len(ux_factors) if ux_factors else 0.5

    def get_quality_category(self, overall_score: float) -> str:
        """Get quality category based on overall score."""
        for category, threshold in sorted(self.quality_thresholds.items(), 
                                        key=lambda x: x[1], reverse=True):
            if overall_score >= threshold:
                return category
        return "failed"

    def export_metrics(self, metrics: QualityMetrics, output_path: str) -> None:
        """Export quality metrics to JSON file."""
        try:
            with open(output_path, 'w') as f:
                json.dump(asdict(metrics), f, indent=2)
            logger.info(f"Quality metrics exported to: {output_path}")
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")

def create_quality_scorer() -> ConversionQualityScorer:
    """Factory function to create a quality scorer instance."""
    return ConversionQualityScorer()