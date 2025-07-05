"""
Smart Assumption Engine implementing PRD Table of Smart Assumptions
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AssumptionImpact(Enum):
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"


@dataclass
class SmartAssumption:
    """Represents a single smart assumption mapping per PRD"""
    java_feature: str
    inconvertible_aspect: str
    bedrock_workaround: str
    impact: AssumptionImpact
    description: str
    implementation_notes: str


class SmartAssumptionEngine:
    """
    Implements PRD Section 1.0.2: Smart Assumptions for bridging Java/Bedrock gaps
    """
    
    def __init__(self):
        self.assumption_table = self._build_prd_assumption_table()
    
    def _build_prd_assumption_table(self) -> List[SmartAssumption]:
        """Build the assumption table from PRD specifications"""
        return [
            SmartAssumption(
                java_feature="Custom Dimensions",
                inconvertible_aspect="No Bedrock API for creating new worlds",
                bedrock_workaround="Convert to large, self-contained structure in existing dimension",
                impact=AssumptionImpact.HIGH,
                description="Recreate as 'skybox' or far-off landmass in Overworld or The End",
                implementation_notes="Preserve assets and generation rules as static structures"
            ),
            
            SmartAssumption(
                java_feature="Complex Machinery",
                inconvertible_aspect="Custom Java logic for power, processing, multi-block interactions",
                bedrock_workaround="Replace complex logic with closest Bedrock component",
                impact=AssumptionImpact.HIGH,
                description="Convert model/texture but simplify to decorative block or container",
                implementation_notes="Core functionality lost, aesthetic preserved"
            ),
            
            SmartAssumption(
                java_feature="Custom GUI/HUD",
                inconvertible_aspect="No Bedrock API for creating new UI screens",
                bedrock_workaround="Recreate interface using in-game items",
                impact=AssumptionImpact.HIGH,
                description="Use books or signs for information display",
                implementation_notes="Significant UX change but information access preserved"
            ),
            
            SmartAssumption(
                java_feature="Client-Side Rendering",
                inconvertible_aspect="No access to Bedrock's Render Dragon engine",
                bedrock_workaround="Exclude from conversion with notification",
                impact=AssumptionImpact.HIGH,
                description="Identify and exclude shaders, performance enhancers",
                implementation_notes="Explicitly notify user of unsupported features"
            ),
            
            SmartAssumption(
                java_feature="Mod Dependencies",
                inconvertible_aspect="Bedrock add-ons designed to be self-contained",
                bedrock_workaround="Bundle simple libraries, flag complex dependencies",
                impact=AssumptionImpact.MEDIUM,
                description="Attempt bundling for simple libs, halt for complex deps",
                implementation_notes="Explain dependency issues to user with clear reasoning"
            ),
            
            # Additional common assumptions
            SmartAssumption(
                java_feature="Advanced Redstone Logic",
                inconvertible_aspect="Limited redstone API in Bedrock",
                bedrock_workaround="Simplify to basic redstone components",
                impact=AssumptionImpact.MEDIUM,
                description="Convert complex circuits to simple on/off mechanisms",
                implementation_notes="Document original logic for manual implementation"
            ),
            
            SmartAssumption(
                java_feature="Custom Entity AI",
                inconvertible_aspect="Limited entity behavior customization in Bedrock",
                bedrock_workaround="Use closest vanilla entity behavior",
                impact=AssumptionImpact.MEDIUM,
                description="Map to existing Bedrock entity with similar characteristics",
                implementation_notes="Preserve appearance, adapt behavior to Bedrock limitations"
            )
        ]
    
    def get_assumption_table(self) -> List[SmartAssumption]:
        """Get the complete assumption table"""
        return self.assumption_table
    
    def find_assumption(self, feature_type: str) -> Optional[SmartAssumption]:
        """Find appropriate assumption for a given feature type"""
        feature_lower = feature_type.lower()
        
        for assumption in self.assumption_table:
            if any(keyword in feature_lower for keyword in 
                   assumption.java_feature.lower().split()):
                return assumption
        
        return None
    
    def apply_assumption(self, feature_type: str, feature_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Apply smart assumption to convert incompatible feature
        
        Args:
            feature_type: Type of Java feature (e.g., 'custom_dimension')
            feature_data: Feature metadata and configuration
            
        Returns:
            Conversion result with applied assumption or None if no assumption applies
        """
        assumption = self.find_assumption(feature_type)
        
        if not assumption:
            logger.warning(f"No smart assumption found for feature type: {feature_type}")
            return None
        
        logger.info(f"Applying smart assumption for {feature_type}: {assumption.description}")
        
        # Apply specific conversion logic based on assumption type
        if "dimension" in feature_type.lower():
            return self._convert_custom_dimension(feature_data, assumption)
        elif "machinery" in feature_type.lower():
            return self._convert_complex_machinery(feature_data, assumption)
        elif "gui" in feature_type.lower() or "hud" in feature_type.lower():
            return self._convert_custom_gui(feature_data, assumption)
        elif "rendering" in feature_type.lower():
            return self._exclude_client_rendering(feature_data, assumption)
        elif "dependency" in feature_type.lower():
            return self._handle_mod_dependency(feature_data, assumption)
        else:
            # Generic assumption application
            return {
                'original_feature': feature_type,
                'assumption_applied': assumption.description,
                'impact': assumption.impact.value,
                'converted_data': feature_data,
                'notes': assumption.implementation_notes
            }
    
    def _convert_custom_dimension(self, feature_data: Dict[str, Any], assumption: SmartAssumption) -> Dict[str, Any]:
        """Convert custom dimension to structure per PRD assumption"""
        return {
            'conversion_type': 'dimension_to_structure',
            'target_dimension': 'overworld',  # or 'the_end' based on theme
            'structure_name': f"{feature_data.get('name', 'custom')}_dimension_structure",
            'original_biomes': feature_data.get('biomes', []),
            'generation_rules': 'converted_to_static_structure',
            'assumption_applied': assumption.description,
            'impact': assumption.impact.value,
            'user_note': 'Original dimension converted to explorable structure in Overworld'
        }
    
    def _convert_complex_machinery(self, feature_data: Dict[str, Any], assumption: SmartAssumption) -> Dict[str, Any]:
        """Convert complex machinery to simple components per PRD assumption"""
        return {
            'conversion_type': 'machinery_simplification',
            'preserved_elements': ['model', 'texture', 'name'],
            'removed_elements': ['power_system', 'processing_logic', 'multiblock_structure'],
            'replacement_type': 'decorative_block' if feature_data.get('decorative') else 'container',
            'assumption_applied': assumption.description,
            'impact': assumption.impact.value,
            'user_note': 'Machinery appearance preserved, functionality simplified to container/decoration'
        }
    
    def _convert_custom_gui(self, feature_data: Dict[str, Any], assumption: SmartAssumption) -> Dict[str, Any]:
        """Convert custom GUI to book/sign interface per PRD assumption"""
        return {
            'conversion_type': 'gui_to_book_interface',
            'interface_elements': feature_data.get('elements', []),
            'book_pages': self._convert_gui_elements_to_pages(feature_data.get('elements', [])),
            'assumption_applied': assumption.description,
            'impact': assumption.impact.value,
            'user_note': 'Custom interface converted to in-game book for information access'
        }
    
    def _exclude_client_rendering(self, feature_data: Dict[str, Any], assumption: SmartAssumption) -> Dict[str, Any]:
        """Exclude client-side rendering mods per PRD assumption"""
        return {
            'conversion_type': 'exclusion',
            'reason': 'client_side_rendering_unsupported',
            'excluded_features': feature_data.get('rendering_features', []),
            'assumption_applied': assumption.description,
            'impact': assumption.impact.value,
            'user_note': 'Client-side rendering mods cannot be converted to Bedrock'
        }
    
    def _handle_mod_dependency(self, feature_data: Dict[str, Any], assumption: SmartAssumption) -> Dict[str, Any]:
        """Handle mod dependencies per PRD assumption"""
        dependency_complexity = self._assess_dependency_complexity(feature_data)
        
        if dependency_complexity == 'simple':
            return {
                'conversion_type': 'dependency_bundling',
                'bundled_functions': feature_data.get('required_functions', []),
                'assumption_applied': assumption.description,
                'impact': assumption.impact.value,
                'user_note': 'Simple dependency functions bundled into add-on'
            }
        else:
            return {
                'conversion_type': 'dependency_failure',
                'failed_dependency': feature_data.get('dependency_name'),
                'reason': 'complex_dependency_unsupported',
                'assumption_applied': assumption.description,
                'impact': assumption.impact.value,
                'user_note': 'Complex dependency prevents conversion - manual porting required'
            }
    
    def _convert_gui_elements_to_pages(self, elements: List[Dict]) -> List[str]:
        """Convert GUI elements to book pages"""
        pages = []
        for element in elements:
            if element.get('type') == 'button':
                pages.append(f"Button: {element.get('label', 'Unknown')}\nAction: {element.get('action', 'See manual')}")
            elif element.get('type') == 'display':
                pages.append(f"Info: {element.get('content', 'See original mod')}")
        return pages
    
    def _assess_dependency_complexity(self, feature_data: Dict[str, Any]) -> str:
        """Assess if dependency is simple enough to bundle"""
        # Simple heuristics - would be more sophisticated in real implementation
        dep_size = feature_data.get('dependency_size', 0)
        dep_type = feature_data.get('dependency_type', 'unknown')
        
        if dep_size < 100000 and dep_type in ['library', 'utility']:  # < 100KB
            return 'simple'
        else:
            return 'complex'