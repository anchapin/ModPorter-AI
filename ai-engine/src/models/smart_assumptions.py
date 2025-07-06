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

# New Data Classes Start Here

@dataclass
class FeatureContext:
    """Provides context about the Java feature being analyzed."""
    feature_id: str  # A unique identifier for the feature instance
    feature_type: str  # e.g., 'custom_dimension', 'complex_machinery_block', 'custom_gui_screen'
    original_data: Dict[str, Any]  # Raw data extracted for this feature by JavaAnalyzerAgent
    name: Optional[str] = None # User-friendly name if available

    # Example: original_data for a dimension might include {'biome_data': ..., 'generation_rules': ...}
    # Example: original_data for a machine might include {'power_input_type': ..., 'processes_items': ...}

@dataclass
class AssumptionResult:
    """Result of analyzing a feature against the smart assumption table."""
    feature_context: FeatureContext
    applied_assumption: Optional[SmartAssumption] = None # The assumption that applies
    conflicting_assumptions: List[SmartAssumption] = None # Other assumptions that also matched
    conflict_resolution_reason: Optional[str] = None # Why this assumption was selected over others
    # If no assumption applies, this can remain None, or a specific 'no_assumption_needed' or 'cannot_convert' status could be added.
    # For now, None indicates either it's directly convertible or no specific smart assumption handles it.

    def __post_init__(self):
        if self.conflicting_assumptions is None:
            self.conflicting_assumptions = []

@dataclass
class ConversionPlanComponent:
    """Details a specific part of the conversion for a feature based on an assumption."""
    original_feature_id: str
    original_feature_type: str
    assumption_type: Optional[str] # e.g., "dimension_to_structure", "machinery_simplification"
    bedrock_equivalent: str
    impact_level: str # "low", "medium", "high"
    user_explanation: str
    technical_notes: Optional[str] = None
    # This structure is based on the example output's "assumptions_applied" list items
    # It will be populated by methods like _convert_custom_dimension

@dataclass
class ConversionPlan:
    """Represents the overall plan for converting features, including those with assumptions."""
    components: List[ConversionPlanComponent]
    # This might evolve to include more details, like features that are directly convertible without assumptions.
    # For now, it focuses on parts that involved an assumption.

@dataclass
class AppliedAssumptionReportItem:
    """Mirrors the structure of items in the 'assumptions_applied' list from the example output."""
    original_feature: str # Name or description of the original Java feature
    assumption_type: str # e.g., "dimension_to_structure"
    bedrock_equivalent: str
    impact_level: str # "low", "medium", "high"
    user_explanation: str

@dataclass
class AssumptionReport:
    """The final report detailing all smart assumptions applied during a conversion process."""
    assumptions_applied: List[AppliedAssumptionReportItem]

# New Data Classes End Here

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
                impact=AssumptionImpact.MEDIUM,
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
        """Find appropriate assumption for a given feature type with conflict detection"""
        matching_assumptions = self.find_all_matching_assumptions(feature_type)
        
        if not matching_assumptions:
            return None
        elif len(matching_assumptions) == 1:
            return matching_assumptions[0]
        else:
            # Handle conflicts by selecting highest priority assumption
            logger.warning(f"Multiple assumptions match feature type '{feature_type}': {[a.java_feature for a in matching_assumptions]}")
            return self._resolve_assumption_conflict(matching_assumptions, feature_type)
    
    def find_all_matching_assumptions(self, feature_type: str) -> List[SmartAssumption]:
        """Find all assumptions that could apply to a given feature type"""
        feature_lower = feature_type.lower()
        matching_assumptions = []
        
        for assumption in self.assumption_table:
            if any(keyword in feature_lower for keyword in 
                   assumption.java_feature.lower().split()):
                matching_assumptions.append(assumption)
        
        return matching_assumptions
    
    def _resolve_assumption_conflict(self, conflicting_assumptions: List[SmartAssumption], feature_type: str) -> SmartAssumption:
        """Resolve conflicts between multiple matching assumptions using priority rules"""
        logger.info(f"Resolving assumption conflict for feature type '{feature_type}' with {len(conflicting_assumptions)} candidates")
        
        # Priority rule 1: Exact feature type match takes precedence
        exact_matches = [a for a in conflicting_assumptions if a.java_feature.lower().replace(" ", "_") == feature_type.lower()]
        if exact_matches:
            selected = exact_matches[0]
            logger.info(f"Selected assumption '{selected.java_feature}' due to exact feature type match")
            return selected
        
        # Priority rule 2: Higher impact assumptions take precedence (HIGH > MEDIUM > LOW)
        impact_priority = {AssumptionImpact.HIGH: 3, AssumptionImpact.MEDIUM: 2, AssumptionImpact.LOW: 1}
        sorted_by_impact = sorted(conflicting_assumptions, key=lambda a: impact_priority[a.impact], reverse=True)
        
        # If top impacts are equal, use specificity (more keywords = more specific)
        top_impact = sorted_by_impact[0].impact
        top_impact_assumptions = [a for a in sorted_by_impact if a.impact == top_impact]
        
        if len(top_impact_assumptions) == 1:
            selected = top_impact_assumptions[0]
            logger.info(f"Selected assumption '{selected.java_feature}' due to highest impact level ({selected.impact.value})")
            return selected
        
        # Priority rule 3: More specific assumptions (more keywords) take precedence
        def calculate_specificity(assumption: SmartAssumption, feature_type: str) -> int:
            """Calculate how specific an assumption is for a given feature type"""
            feature_words = set(feature_type.lower().split('_'))
            assumption_words = set(assumption.java_feature.lower().split())
            return len(feature_words.intersection(assumption_words))
        
        sorted_by_specificity = sorted(top_impact_assumptions, 
                                     key=lambda a: calculate_specificity(a, feature_type), 
                                     reverse=True)
        
        selected = sorted_by_specificity[0]
        specificity_score = calculate_specificity(selected, feature_type)
        logger.info(f"Selected assumption '{selected.java_feature}' due to highest specificity (score: {specificity_score})")
        
        return selected

    def analyze_feature(self, feature_context: FeatureContext) -> AssumptionResult:
        """
        Analyzes a given feature context to determine if a smart assumption applies.

        Args:
            feature_context: Contextual information about the Java feature.

        Returns:
            An AssumptionResult containing the original feature context and any
            SmartAssumption that applies, plus conflict resolution information.
        """
        logger.info(f"Analyzing feature: {feature_context.feature_id} of type {feature_context.feature_type}")
        
        # Find all matching assumptions to detect conflicts
        all_matching = self.find_all_matching_assumptions(feature_context.feature_type)
        applicable_assumption = None
        conflict_resolution_reason = None
        
        if all_matching:
            if len(all_matching) == 1:
                applicable_assumption = all_matching[0]
                logger.info(f"Found single applicable assumption for {feature_context.feature_type}: {applicable_assumption.java_feature} -> {applicable_assumption.bedrock_workaround}")
            else:
                # Multiple matches - resolve conflict
                applicable_assumption = self._resolve_assumption_conflict(all_matching, feature_context.feature_type)
                conflict_resolution_reason = f"Selected from {len(all_matching)} conflicting assumptions using priority rules"
                logger.info(f"Resolved conflict for {feature_context.feature_type}: selected {applicable_assumption.java_feature} from {[a.java_feature for a in all_matching]}")
        else:
            logger.info(f"No specific smart assumption found for feature type: {feature_context.feature_type}")

        return AssumptionResult(
            feature_context=feature_context,
            applied_assumption=applicable_assumption,
            conflicting_assumptions=all_matching if len(all_matching) > 1 else [],
            conflict_resolution_reason=conflict_resolution_reason
        )
    
    def apply_assumption(self, analysis_result: AssumptionResult) -> Optional[ConversionPlanComponent]:
        """
        Applies a smart assumption to an analyzed feature and generates conversion plan details.

        Args:
            analysis_result: The result from the analyze_feature method, containing
                             the feature context and the smart assumption that applies.

        Returns:
            A ConversionPlanComponent detailing the conversion, or None if no
            assumption was applicable in the analysis_result or if the feature type
            is not handled by a specific conversion method.
        """
        if not analysis_result.applied_assumption:
            logger.warning(f"apply_assumption called for feature '{analysis_result.feature_context.feature_id}' but no assumption was found in analysis_result.")
            return None

        feature_context = analysis_result.feature_context
        assumption = analysis_result.applied_assumption
        feature_type_lower = feature_context.feature_type.lower() # Use feature_type from context

        logger.info(f"Applying smart assumption for feature type '{feature_context.feature_type}' (ID: {feature_context.feature_id}): {assumption.description}")

        conversion_details_dict: Optional[Dict[str, Any]] = None

        # PRD Phase 1: Three core assumptions
        if "dimension" in feature_type_lower and "custom dimensions" in assumption.java_feature.lower():
            conversion_details_dict = self._convert_custom_dimension(feature_context, assumption)
        elif "machinery" in feature_type_lower and "complex machinery" in assumption.java_feature.lower():
            conversion_details_dict = self._convert_complex_machinery(feature_context, assumption)
        elif ("gui" in feature_type_lower or "hud" in feature_type_lower) and "custom gui/hud" in assumption.java_feature.lower():
            conversion_details_dict = self._convert_custom_gui(feature_context, assumption)

        # Placeholder for other assumptions from the PRD table (not part of Phase 1 implementation focus)
        elif "rendering" in feature_type_lower and "client-side rendering" in assumption.java_feature.lower():
            # conversion_details_dict = self._exclude_client_rendering(feature_context, assumption) # Assuming it returns a dict
            logger.warning(f"Smart assumption for '{feature_context.feature_type}' (Client-Side Rendering) is defined but not fully implemented in Phase 1.")
            # Fallback to generic or skip
        elif "dependency" in feature_type_lower and "mod dependencies" in assumption.java_feature.lower():
            # conversion_details_dict = self._handle_mod_dependency(feature_context, assumption) # Assuming it returns a dict
            logger.warning(f"Smart assumption for '{feature_context.feature_type}' (Mod Dependencies) is defined but not fully implemented in Phase 1.")
            # Fallback to generic or skip

        # Add other conditions for assumptions like "Advanced Redstone Logic", "Custom Entity AI" if they were to be handled
        # For now, they will fall through if not explicitly matched above.

        if conversion_details_dict:
            # Construct the ConversionPlanComponent object from the dictionary
            return ConversionPlanComponent(
                original_feature_id=conversion_details_dict['original_feature_id'],
                original_feature_type=conversion_details_dict['original_feature_type'],
                assumption_type=conversion_details_dict['assumption_type'],
                bedrock_equivalent=conversion_details_dict['bedrock_equivalent'],
                impact_level=conversion_details_dict['impact_level'],
                user_explanation=conversion_details_dict['user_explanation'],
                technical_notes=conversion_details_dict.get('technical_notes') # .get for optional field
            )
        else:
            # If it's an assumption we know about but don't have specific logic for (e.g. non-Phase 1)
            # or if the logic is somehow bypassed.
            # We could create a generic ConversionPlanComponent here based on the assumption's direct fields
            # if that's desired, or return None. For Phase 1, focusing on the main three.
            logger.warning(f"No specific conversion logic implemented in apply_assumption for feature type '{feature_context.feature_type}' with assumption '{assumption.java_feature}'.")
            # Fallback to a generic component based on the assumption itself.
            return ConversionPlanComponent(
                original_feature_id=feature_context.feature_id,
                original_feature_type=feature_context.feature_type,
                assumption_type=assumption.java_feature.lower().replace(" ", "_"), # A generic type
                bedrock_equivalent=assumption.bedrock_workaround,
                impact_level=assumption.impact.value,
                user_explanation=assumption.description, # Generic description
                technical_notes=f"Generic assumption applied. Specific conversion path not detailed in Phase 1. {assumption.implementation_notes}"
            )

    def _convert_custom_dimension(self, feature_context: FeatureContext, assumption: SmartAssumption) -> Dict[str, Any]:
        """
        Generates conversion details for turning a custom dimension into a large structure.

        Args:
            feature_context: Contextual information about the custom dimension feature.
            assumption: The specific "Custom Dimensions" smart assumption being applied.

        Returns:
            A dictionary formatted to be used in a ConversionPlanComponent.
        """
        feature_data = feature_context.original_data
        feature_name = feature_context.name if feature_context.name else feature_context.feature_id

        # Determine target dimension (e.g., based on theme, or default to Overworld)
        # This could be made more sophisticated later, perhaps by analyzing feature_data['theme'] if available.
        target_dimension_bedrock = 'Overworld'
        if 'nether_like' in feature_data.get('theme', '').lower():
            target_dimension_bedrock = 'The Nether' # Though PRD mentions Overworld/End, Nether is also a possibility.
        elif 'end_like' in feature_data.get('theme', '').lower():
            target_dimension_bedrock = 'The End'

        original_biomes = feature_data.get('biomes', [])
        original_biomes_str = ", ".join(original_biomes) if original_biomes else "unknown"

        structure_name = f"{feature_name.replace(' ', '_')}_structure"

        user_explanation = (
            f"The custom dimension '{feature_name}' will be converted into a large, explorable "
            f"static structure named '{structure_name}' within the {target_dimension_bedrock}. "
            f"Original biome characteristics ({original_biomes_str}) and generation rules will be "
            f"approximated by the structure's design."
        )

        technical_notes = (
            f"Original feature ID: {feature_context.feature_id}. "
            f"Input dimension data: {str(feature_data)}. "
            f"Structure will need to incorporate representative elements of biomes: {original_biomes_str}. "
            f"Generation rules are to be translated into a fixed structural layout. "
            f"Assets (textures, models) associated with the dimension are to be mapped to this structure."
        )

        return {
            'original_feature_id': feature_context.feature_id,
            'original_feature_type': feature_context.feature_type,
            'assumption_type': "dimension_to_structure", # Matches example output
            'bedrock_equivalent': f"Large structure '{structure_name}' in {target_dimension_bedrock}",
            'impact_level': assumption.impact.value,
            'user_explanation': user_explanation,
            'technical_notes': technical_notes
        }
    
    def _convert_complex_machinery(self, feature_context: FeatureContext, assumption: SmartAssumption) -> Dict[str, Any]:
        """
        Generates conversion details for simplifying complex machinery.

        Args:
            feature_context: Contextual information about the complex machinery feature.
            assumption: The specific "Complex Machinery" smart assumption being applied.

        Returns:
            A dictionary formatted to be used in a ConversionPlanComponent.
        """
        feature_data = feature_context.original_data
        feature_name = feature_context.name if feature_context.name else feature_context.feature_id

        # Determine replacement type (decorative or container)
        # This could be based on feature_data analysis, e.g., if it has inventory slots.
        is_decorative_default = True # Default to decorative
        if feature_data.get('has_inventory', False) or 'chest' in feature_name.lower() or 'storage' in feature_name.lower():
            is_decorative_default = False

        replacement_type = 'decorative_block' if is_decorative_default else 'simple_container_block'

        preserved_elements = ['model', 'texture', 'name', 'general_shape']
        removed_elements = ['custom_java_logic', 'power_system', 'processing_logic', 'multi-block_interactions', 'complex_event_handling']

        if feature_data.get('power_related', False):
            preserved_elements.append('power_connection_visuals (if any, non-functional)')
        if feature_data.get('item_io_ports', False):
            preserved_elements.append('item_port_visuals (if any, non-functional)')


        user_explanation = (
            f"The complex machine '{feature_name}' will be simplified. Its visual appearance "
            f"(model, textures) will be preserved as much as possible, but its custom Java-based "
            f"functionality (power, processing, etc.) will be removed. It will become a "
            f"{replacement_type.replace('_', ' ')} in Bedrock."
        )

        technical_notes = (
            f"Original feature ID: {feature_context.feature_id}. "
            f"Input machinery data: {str(feature_data)}. "
            f"Preserve: {', '.join(preserved_elements)}. Remove: {', '.join(removed_elements)}. "
            f"Target Bedrock type: {replacement_type}. "
            f"Asset conversion for models and textures is critical. Any animations tied to logic will likely be lost or simplified."
        )

        return {
            'original_feature_id': feature_context.feature_id,
            'original_feature_type': feature_context.feature_type,
            'assumption_type': "machinery_simplification", # Matches example output style
            'bedrock_equivalent': f"{replacement_type.replace('_', ' ')} preserving original appearance of '{feature_name}'",
            'impact_level': assumption.impact.value,
            'user_explanation': user_explanation,
            'technical_notes': technical_notes
        }
    
    def _convert_gui_elements_to_pages(self, elements: List[Dict[str, Any]], feature_name: str) -> List[str]:
        """
        Converts a list of GUI element data into a list of strings, representing book pages.

        Args:
            elements: A list of dictionaries, where each dict describes a GUI element.
                      Example: {'type': 'label', 'text': 'Welcome!', 'x': 10, 'y': 10}
                               {'type': 'button', 'text': 'Click Me', 'action_id': 'my_action'}
                               {'type': 'slot', 'item_id': 'minecraft:diamond', 'x': 20, 'y': 30}
                               {'type': 'text_area', 'content_variable': 'status_text'}
            feature_name: The name of the GUI feature, for context in messages.

        Returns:
            A list of strings, where each string can be a page in a Bedrock book.
        """
        pages = []
        current_page_content = f"--- {feature_name} Interface ---\n"
        lines_on_current_page = 1

        if not elements:
            pages.append(current_page_content + "\n(No specific UI elements data found for this GUI)")
            return pages

        for i, element in enumerate(elements):
            element_text = ""
            el_type = element.get('type', 'unknown').lower()
            el_text_content = element.get('text', element.get('label', element.get('content', '')))

            if el_type == 'label' or el_type == 'text':
                element_text = f"Info: {el_text_content}"
            elif el_type == 'button':
                element_text = f"Button: '{el_text_content}' (Note: Action '{element.get('action_id', 'unspecified')}' will be non-functional)"
            elif el_type == 'image':
                element_text = f"Image: {element.get('resource_id', 'unspecified_image')} (Note: Display as text only)"
            elif el_type == 'slot' or el_type == 'item_slot':
                element_text = f"Item Slot: Displays {element.get('item_id', 'item')} (Note: Interaction removed)"
            elif el_type == 'text_area':
                element_text = f"Text Area: (Content from '{element.get('content_variable', 'dynamic_text')}' would appear here)"
            elif el_type == 'checkbox' or el_type == 'toggle':
                element_text = f"Option: '{el_text_content}' (Note: Setting will be non-functional)"
            else:
                element_text = f"UI Element: Type '{el_type}', Content: '{el_text_content}' (Note: Functionality removed)"

            if lines_on_current_page > 10 or len(current_page_content) + len(element_text) > 250: # Simple page break logic
                pages.append(current_page_content)
                current_page_content = ""
                lines_on_current_page = 0

            current_page_content += element_text + "\n"
            lines_on_current_page += 1

            if i == len(elements) - 1 and current_page_content.strip(): # Add last page if it has content
                 pages.append(current_page_content)

        if not pages and current_page_content.strip(): # Ensure at least one page if there was initial content
            pages.append(current_page_content)
        elif not pages: # Fallback if elements was empty and initial content was also somehow skipped
            pages.append(f"--- {feature_name} Interface ---\n(No displayable content extracted)")

        # Ensure all pages are strings
        return [str(page_content) for page_content in pages]

    def generate_assumption_report(self, conversion_plan_components: List[ConversionPlanComponent]) -> AssumptionReport:
        """
        Generates a final report object from a list of conversion plan components
        that involved smart assumptions.

        Args:
            conversion_plan_components: A list of ConversionPlanComponent objects,
                                        typically generated by multiple calls to apply_assumption.

        Returns:
            An AssumptionReport object.
        """
        report_items: List[AppliedAssumptionReportItem] = []

        if not conversion_plan_components:
            logger.info("generate_assumption_report called with no conversion plan components. Returning empty report.")
            return AssumptionReport(assumptions_applied=[])

        for component in conversion_plan_components:
            if component is None: # Should ideally not happen if list is filtered beforehand
                logger.warning("Encountered a None component in conversion_plan_components list. Skipping.")
                continue

            # Constructing the 'original_feature' string.
            # This might need refinement based on how FeatureContext.name is populated or if more detail is desired.
            # For now, using original_feature_type and a part of original_feature_id.
            original_feature_description = f"{component.original_feature_type} (ID: ...{component.original_feature_id[-6:]})"
            # If a more user-friendly name was stored in ConversionPlanComponent, that would be better.
            # Let's assume for now that original_feature_type is descriptive enough for the report's 'original_feature' field.
            # Or, if the component's 'user_explanation' already names the feature well, we can rely on that.
            # The example output shows "Twilight Forest Dimension", which is quite specific.
            # The current 'user_explanation' in components like _convert_custom_dimension starts with "The custom dimension '{feature_name}'..."
            # Let's try to extract that feature name.

            # Attempt to extract a more descriptive name from the user_explanation
            explanation_intro_pattern = r"The .+? '([^']+)'" # Matches "The custom dimension 'feature_name'"
            import re
            match = re.search(explanation_intro_pattern, component.user_explanation)
            if match:
                original_feature_description = f"{match.group(1)} ({component.original_feature_type})" # e.g. "Twilight Forest (custom_dimension)"
            else:
                # Fallback if pattern doesn't match (e.g. generic assumption user_explanation)
                original_feature_description = f"{component.original_feature_type} (ID: {component.original_feature_id})"


            report_item = AppliedAssumptionReportItem(
                original_feature=original_feature_description,
                assumption_type=component.assumption_type if component.assumption_type else "unknown_assumption",
                bedrock_equivalent=component.bedrock_equivalent,
                impact_level=component.impact_level,
                user_explanation=component.user_explanation
            )
            report_items.append(report_item)

        logger.info(f"Generated assumption report with {len(report_items)} items.")
        return AssumptionReport(assumptions_applied=report_items)

    def _convert_custom_gui(self, feature_context: FeatureContext, assumption: SmartAssumption) -> Dict[str, Any]:
        """
        Generates conversion details for adapting a custom GUI to a book/sign interface.

        Args:
            feature_context: Contextual information about the custom GUI feature.
            assumption: The specific "Custom GUI/HUD" smart assumption being applied.

        Returns:
            A dictionary formatted to be used in a ConversionPlanComponent.
        """
        feature_data = feature_context.original_data
        feature_name = feature_context.name if feature_context.name else feature_context.feature_id

        # Assume feature_data['elements'] is a list of dicts describing UI elements
        gui_elements = feature_data.get('elements', [])
        if not isinstance(gui_elements, list):
            logger.warning(f"GUI elements for {feature_name} is not a list: {type(gui_elements)}. Treating as empty.")
            gui_elements = []

        book_pages_content = self._convert_gui_elements_to_pages(gui_elements, feature_name)

        num_pages = len(book_pages_content)
        bedrock_equivalent_desc = (
            f"Book-based interface for '{feature_name}' ({num_pages} page(s)). "
            f"Original interactive elements are now descriptive text."
        )

        user_explanation = (
            f"The custom interface '{feature_name}' will be converted into a read-only book in Bedrock. "
            f"Information and button labels from the original UI will be presented as text in the book. "
            f"Interactive functionality will be lost."
        )

        technical_notes = (
            f"Original feature ID: {feature_context.feature_id}. "
            f"Input GUI data: {str(feature_data)}. "
            f"Extracted {len(gui_elements)} UI elements. Converted to {num_pages} book pages. "
            f"All interactive components (buttons, checkboxes, text inputs) are mapped to static text descriptions. "
            f"Layout is simplified to sequential pages."
        )

        return {
            'original_feature_id': feature_context.feature_id,
            'original_feature_type': feature_context.feature_type,
            'assumption_type': "gui_to_book_interface", # Matches example output style
            'bedrock_equivalent': bedrock_equivalent_desc,
            'impact_level': assumption.impact.value,
            'user_explanation': user_explanation,
            'technical_notes': technical_notes,
            'conversion_details': { # Adding extra structured data if useful later
                'book_title': feature_name,
                'pages_content': book_pages_content
            }
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
    
    
    def _assess_dependency_complexity(self, feature_data: Dict[str, Any]) -> str:
        """Assess if dependency is simple enough to bundle"""
        # Simple heuristics - would be more sophisticated in real implementation
        dep_size = feature_data.get('dependency_size', 0)
        dep_type = feature_data.get('dependency_type', 'unknown')
        
        if dep_size < 100000 and dep_type in ['library', 'utility']:  # < 100KB
            return 'simple'
        else:
            return 'complex'
    
    def get_conflict_analysis(self, feature_type: str) -> Dict[str, Any]:
        """Get detailed analysis of assumption conflicts for a feature type"""
        all_matching = self.find_all_matching_assumptions(feature_type)
        
        if len(all_matching) <= 1:
            return {
                "has_conflicts": False,
                "matching_assumptions": [a.java_feature for a in all_matching],
                "selected_assumption": all_matching[0].java_feature if all_matching else None,
                "resolution_method": "no_conflict"
            }
        
        # Simulate conflict resolution to show the logic
        selected = self._resolve_assumption_conflict(all_matching, feature_type)
        
        return {
            "has_conflicts": True,
            "matching_assumptions": [a.java_feature for a in all_matching],
            "selected_assumption": selected.java_feature,
            "resolution_method": "priority_rules",
            "conflict_details": {
                "impact_levels": {a.java_feature: a.impact.value for a in all_matching},
                "selected_impact": selected.impact.value,
                "resolution_reason": f"Selected '{selected.java_feature}' using impact and specificity rules"
            }
        }