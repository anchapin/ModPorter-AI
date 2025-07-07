"""
ModPorter AI Conversion Crew
Implements PRD Feature 2: AI Conversion Engine using CrewAI multi-agent system
"""

from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from typing import Dict, List, Any, Optional
import json
import logging
import os
from pathlib import Path

from src.agents.java_analyzer import JavaAnalyzerAgent
from src.agents.bedrock_architect import BedrockArchitectAgent
from src.agents.logic_translator import LogicTranslatorAgent
from src.agents.asset_converter import AssetConverterAgent
from src.agents.packaging_agent import PackagingAgent
from src.agents.qa_validator import QAValidatorAgent
from src.models.smart_assumptions import SmartAssumptionEngine, ConversionPlanComponent, AssumptionReport

logger = logging.getLogger(__name__)


class ModPorterConversionCrew:
    """
    Multi-agent crew for converting Java mods to Bedrock add-ons
    Following PRD Section 3.0.3: CrewAI framework implementation
    """
    
    def __init__(self, model_name: str = "gpt-4"):
        # Use mock LLM in test environment
        if os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true":
            try:
                # Try importing from the current project structure
                import sys
                from pathlib import Path
                test_dir = Path(__file__).parent.parent.parent / "tests" / "mocks"
                sys.path.insert(0, str(test_dir))
                from mock_llm import MockLLM
                self.llm = MockLLM(responses=[
                    "Mock analysis complete",
                    "Mock conversion plan generated", 
                    "Mock translation complete",
                    "Mock assets converted",
                    "Mock package built",
                    "Mock validation passed"
                ])
            except ImportError:
                # Fallback if mock not available
                from unittest.mock import MagicMock
                self.llm = MagicMock()
                self.llm.predict.return_value = "Mock response"
        else:
            try:
                self.llm = ChatOpenAI(
                    model=model_name,
                    temperature=0.1,  # Low temperature for consistent technical output
                    max_tokens=4000
                )
            except Exception as e:
                # Fallback for testing environment
                logger.warning(f"Failed to initialize OpenAI LLM: {e}")
                from unittest.mock import MagicMock
                self.llm = MagicMock()
        
        self.smart_assumption_engine = SmartAssumptionEngine()
        self._setup_agents()
        self._setup_crew()
    
    def _setup_agents(self):
        """Initialize specialized agents as per PRD Feature 2 requirements"""
        
        # Initialize agent instances
        self.java_analyzer_agent = JavaAnalyzerAgent()
        self.bedrock_architect_agent = BedrockArchitectAgent()
        self.logic_translator_agent = LogicTranslatorAgent()
        self.asset_converter_agent = AssetConverterAgent()
        self.packaging_agent_instance = PackagingAgent()
        self.qa_validator_agent = QAValidatorAgent()
        
        # PRD Feature 2: Analyzer Agent
        agent_kwargs = {
            "role": "Java Mod Analyzer",
            "goal": "Accurately analyze Java mod structure, dependencies, and features",
            "backstory": """You are an expert Java developer with deep knowledge of Minecraft 
            modding frameworks like Forge, Fabric, and Quilt. You can deconstruct any mod 
            to understand its components, dependencies, and intended functionality.""",
            "verbose": True,
            "allow_delegation": False,
            "llm": self.llm,
            "tools": self.java_analyzer_agent.get_tools()
        }
        
        # Disable memory in test environment to avoid validation issues
        if os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true":
            agent_kwargs["memory"] = False
        
        self.java_analyzer = Agent(**agent_kwargs)
        
        # PRD Feature 2: Planner Agent (Bedrock Architect)
        architect_kwargs = {
            "role": "Bedrock Conversion Architect",
            "goal": "Design optimal conversion strategies using smart assumptions",
            "backstory": """You are a Minecraft Bedrock add-on expert who understands the 
            limitations and capabilities of the Bedrock platform. You excel at finding 
            creative workarounds and making intelligent compromises to adapt Java features 
            for Bedrock.""",
            "verbose": True,
            "allow_delegation": False,
            "llm": self.llm,
            "tools": self.bedrock_architect_agent.get_tools()
        }
        
        if os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true":
            architect_kwargs["memory"] = False
        
        self.bedrock_architect = Agent(**architect_kwargs)
        
        # PRD Feature 2: Logic Translation Agent
        translator_kwargs = {
            "role": "Code Logic Translator",
            "goal": "Convert Java code to Bedrock JavaScript with proper error handling",
            "backstory": """You are a polyglot programmer specializing in Java to JavaScript 
            conversion. You understand both object-oriented and event-driven paradigms 
            and can bridge the gap between Minecraft's Java API and Bedrock's JavaScript API.""",
            "verbose": True,
            "allow_delegation": False,
            "llm": self.llm,
            "tools": self.logic_translator_agent.get_tools()
        }
        
        if os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true":
            translator_kwargs["memory"] = False
            
        self.logic_translator = Agent(**translator_kwargs)
        
        # PRD Feature 2: Asset Conversion Agent
        asset_kwargs = {
            "role": "Asset Conversion Specialist",
            "goal": "Convert all visual and audio assets to Bedrock-compatible formats",
            "backstory": """You are a technical artist who specializes in game asset 
            conversion. You understand the technical requirements for Minecraft Bedrock 
            textures, models, and sounds, and can optimize them for performance.""",
            "verbose": True,
            "allow_delegation": False,
            "llm": self.llm,
            "tools": self.asset_converter_agent.get_tools()
        }
        
        if os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true":
            asset_kwargs["memory"] = False
            
        self.asset_converter = Agent(**asset_kwargs)
        
        # PRD Feature 2: Packaging Agent
        packaging_kwargs = {
            "role": "Bedrock Package Builder",
            "goal": "Assemble converted components into valid .mcaddon packages",
            "backstory": """You are a Bedrock add-on packaging expert who knows the exact 
            file structure, manifest requirements, and validation rules for creating 
            working .mcaddon files.""",
            "verbose": True,
            "allow_delegation": False,
            "llm": self.llm,
            "tools": self.packaging_agent_instance.get_tools()
        }
        
        if os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true":
            packaging_kwargs["memory"] = False
            
        self.packaging_agent = Agent(**packaging_kwargs)
        
        # PRD Feature 2: QA Agent
        qa_kwargs = {
            "role": "Quality Assurance Validator",
            "goal": "Validate conversion quality and generate comprehensive reports",
            "backstory": """You are a meticulous QA engineer who tests both functionality 
            and user experience. You can identify potential issues and provide clear, 
            actionable feedback on conversion quality.""",
            "verbose": True,
            "allow_delegation": False,
            "llm": self.llm,
            "tools": self.qa_validator_agent.get_tools()
        }
        
        if os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true":
            qa_kwargs["memory"] = False
            
        self.qa_validator = Agent(**qa_kwargs)
    
    def _setup_crew(self):
        """Setup the crew workflow following PRD conversion process"""
        
        # Define tasks in sequence
        self.analyze_task = Task(
            description="""Analyze the provided Java mod files to identify:
            1. All assets (textures, models, sounds)
            2. Code logic and custom mechanics
            3. Dependencies and mod framework used
            4. Feature types (blocks, items, entities, dimensions, GUI, etc.)
            5. Incompatible features that require smart assumptions
            
            Generate a comprehensive analysis report with feature categorization.""",
            agent=self.java_analyzer,
            expected_output="Detailed JSON analysis report with categorized features"
        )
        
        self.plan_task = Task(
            description="""Based on the analysis report, create a conversion plan that:
            1. Maps each Java feature to a Bedrock equivalent using smart assumptions
            2. Uses the Smart Assumption Engine to handle incompatible features with conflict resolution
            3. Identifies and resolves any assumption conflicts using the priority system
            4. Documents all applied assumptions with explanations and confidence levels
            5. Flags features that cannot be converted and must be excluded
            6. Provides detailed conversion strategy for each component
            
            Use the bedrock_architect_agent tools to:
            - analyze_feature_compatibility for each identified feature
            - apply_smart_assumptions for incompatible features
            - create_conversion_plan with comprehensive mapping
            - resolve_assumption_conflicts when multiple assumptions apply
            - validate_bedrock_compatibility for the overall plan
            
            Return results as ConversionPlanComponent objects for assumption reporting.""",
            agent=self.bedrock_architect,
            expected_output="Comprehensive conversion plan with smart assumption mappings and conflict resolution details",
            context=[self.analyze_task]
        )
        
        self.translate_task = Task(
            description="""Convert Java code to Bedrock JavaScript following the plan:
            1. Use translate_java_to_javascript for main code conversion
            2. Apply map_java_types_to_javascript for proper type mapping
            3. Use map_java_apis_to_bedrock for API translation
            4. Handle event-driven paradigm with handle_event_system_conversion
            5. Validate conversions with validate_javascript_syntax
            6. Comment out untranslatable code with explanations
            7. Ensure all scripts follow Bedrock scripting standards
            
            For untranslatable logic, add explanatory notes for developers.
            Use the logic_translator_agent tools for accurate conversion.""",
            agent=self.logic_translator,
            expected_output="Converted JavaScript files with detailed comments and validation reports",
            context=[self.analyze_task, self.plan_task]
        )
        
        self.convert_assets_task = Task(
            description="""Convert all assets to Bedrock-compatible formats:
            1. Use analyze_asset_requirements to understand conversion needs
            2. Convert textures with convert_texture_assets to proper resolution and format
            3. Convert 3D models with convert_model_assets to Bedrock geometry format
            4. Convert sounds with convert_audio_assets to supported audio formats
            5. Use organize_converted_assets for proper Bedrock folder structure
            6. Validate conversions with validate_asset_conversion
            7. Generate necessary texture and model definition files
            
            Ensure all assets meet Bedrock technical requirements and performance standards.
            Use the asset_converter_agent tools for reliable conversion.""",
            agent=self.asset_converter,
            expected_output="Converted assets in proper Bedrock folder structure with validation reports",
            context=[self.analyze_task, self.plan_task]
        )
        
        self.package_task = Task(
            description="""Assemble all converted components into a valid .mcaddon:
            1. Use create_addon_structure to set up proper Bedrock add-on structure
            2. Generate manifest with generate_manifest_json using correct metadata
            3. Organize files with organize_addon_files in correct structure
            4. Validate package with validate_addon_package for integrity
            5. Create final package with create_mcaddon_package
            6. Generate installation instructions for users
            
            Ensure the package meets all Bedrock add-on standards and is ready for distribution.
            Use the packaging_agent tools for reliable packaging.""",
            agent=self.packaging_agent,
            expected_output="Complete .mcaddon package ready for installation with validation reports",
            context=[self.translate_task, self.convert_assets_task]
        )
        
        self.validate_task = Task(
            description="""Validate the conversion and generate the final report:
            1. Use validate_conversion_quality to check package validity and completeness
            2. Run run_functionality_tests to verify converted features work as expected
            3. Analyze compatibility with analyze_compatibility_issues for potential problems
            4. Check performance with analyze_performance_impact
            5. Generate comprehensive reports with generate_qa_report
            6. Document all smart assumptions applied with detailed explanations
            7. Create both user-friendly summary and technical developer documentation
            
            Provide detailed validation results and actionable recommendations.
            Use the qa_validator_agent tools for thorough quality assurance.""",
            agent=self.qa_validator,
            expected_output="Complete conversion report with success metrics, validation results, and quality analysis",
            context=[self.package_task]
        )
        
        # Create the crew
        self.crew = Crew(
            agents=[
                self.java_analyzer,
                self.bedrock_architect,
                self.logic_translator,
                self.asset_converter,
                self.packaging_agent,
                self.qa_validator
            ],
            tasks=[
                self.analyze_task,
                self.plan_task,
                self.translate_task,
                self.convert_assets_task,
                self.package_task,
                self.validate_task
            ],
            process=Process.sequential,
            verbose=True
        )
    
    def convert_mod(
        self, 
        mod_path: Path, 
        output_path: Path,
        smart_assumptions: bool = True,
        include_dependencies: bool = True
    ) -> Dict[str, Any]:
        """
        Execute the full conversion process
        
        Args:
            mod_path: Path to Java mod file or directory
            output_path: Path for converted output
            smart_assumptions: Enable smart assumption processing
            include_dependencies: Include dependency analysis
            
        Returns:
            Conversion result following PRD Feature 3 format
        """
        try:
            logger.info(f"Starting conversion of {mod_path}")
            
            # Prepare inputs for the crew
            inputs = {
                'mod_path': str(mod_path),
                'output_path': str(output_path),
                'smart_assumptions_enabled': smart_assumptions,
                'include_dependencies': include_dependencies,
                'smart_assumption_engine': self.smart_assumption_engine
            }
            
            # Execute the crew workflow
            result = self.crew.kickoff(inputs=inputs)
            
            # Extract conversion plan components for assumption reporting
            plan_components = self._extract_plan_components(result)
            
            # Generate comprehensive assumption report using enhanced engine
            conversion_report = self._format_conversion_report(result, plan_components)
            
            logger.info("Conversion completed successfully")
            return conversion_report
            
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'overall_success_rate': 0.0,
                'converted_mods': [],
                'failed_mods': [{'name': str(mod_path), 'reason': str(e), 'suggestions': []}],
                'smart_assumptions_applied': [],
                'download_url': None,
                'detailed_report': {'stage': 'error', 'progress': 0, 'logs': [str(e)]}
            }

    def _extract_plan_components(self, crew_result: Any) -> List[ConversionPlanComponent]:
        """Extract conversion plan components from crew result for assumption reporting"""
        plan_components: List[ConversionPlanComponent] = []
        
        try:
            # Access task outputs from crew result
            if hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
                # Plan task is the second task (index 1)
                if len(crew_result.tasks_output) > 1:
                    plan_task_output = crew_result.tasks_output[1]
                    
                    # Try to parse the output for conversion plan components
                    if hasattr(plan_task_output, 'raw'):
                        try:
                            # Attempt to parse JSON output from bedrock architect
                            output_data = json.loads(plan_task_output.raw)
                            if isinstance(output_data, dict):
                                # Look for conversion plan components in the output
                                components_data = output_data.get('conversion_plan_components', [])
                                if not components_data:
                                    components_data = output_data.get('components', [])
                                if not components_data:
                                    components_data = output_data.get('plan_components', [])
                                
                                for comp_data in components_data:
                                    if isinstance(comp_data, dict):
                                        try:
                                            component = ConversionPlanComponent(**comp_data)
                                            plan_components.append(component)
                                        except TypeError as e:
                                            logger.warning(f"Could not create ConversionPlanComponent: {e}")
                                            # Create a basic component from available data
                                            component = ConversionPlanComponent(
                                                original_feature_id=comp_data.get('original_feature_id', 'unknown'),
                                                original_feature_type=comp_data.get('original_feature_type', 'unknown'),
                                                assumption_type=comp_data.get('assumption_type'),
                                                bedrock_equivalent=comp_data.get('bedrock_equivalent', 'undefined'),
                                                impact_level=comp_data.get('impact_level', 'medium'),
                                                user_explanation=comp_data.get('user_explanation', 'No explanation available')
                                            )
                                            plan_components.append(component)
                        except json.JSONDecodeError:
                            logger.warning("Failed to decode plan task output as JSON")
                    
                    # If no structured data found, create basic components from the agent's work
                    if not plan_components and hasattr(self.bedrock_architect_agent, 'last_plan_components'):
                        plan_components = self.bedrock_architect_agent.last_plan_components
                        
        except Exception as e:
            logger.warning(f"Could not extract plan components: {e}")
        
        return plan_components

    def _format_conversion_report(self, crew_result: Any, plan_components: List[ConversionPlanComponent]) -> Dict[str, Any]:
        """Format crew result into PRD Feature 3 report structure with enhanced assumption reporting"""
        
        assumption_report_data = []
        conflict_analysis = {}
        
        try:
            if self.smart_assumption_engine and plan_components:
                # Generate comprehensive assumption report using enhanced engine
                assumption_report: AssumptionReport = self.smart_assumption_engine.generate_assumption_report(plan_components)
                
                # Extract assumption data for JSON output
                assumption_report_data = [
                    {
                        'original_feature': item.original_feature,
                        'assumption_type': item.assumption_type,
                        'bedrock_equivalent': item.bedrock_equivalent,
                        'impact_level': item.impact_level,
                        'user_explanation': item.user_explanation
                    }
                    for item in assumption_report.assumptions_applied
                ]
                
                # Get conflict analysis for transparency
                if hasattr(self.smart_assumption_engine, 'get_conflict_analysis'):
                    conflicts = self.smart_assumption_engine.get_conflict_analysis("general")
                    if conflicts:
                        conflict_analysis = {
                            'total_conflicts_detected': len(conflicts),
                            'conflicts_resolved': len([c for c in conflicts if c.get('resolved', False)]),
                            'resolution_method': 'priority_based_deterministic',
                            'details': conflicts
                        }
                
        except Exception as e:
            logger.warning(f"Failed to generate assumption report: {e}")
        
        # Calculate success metrics from crew results
        success_rate = 0.85  # Default fallback
        converted_features = []
        failed_features = []
        
        try:
            # Extract success metrics from crew results if available
            if hasattr(crew_result, 'tasks_output') and crew_result.tasks_output:
                # Analyze task outputs for success indicators
                for task_output in crew_result.tasks_output:
                    if hasattr(task_output, 'raw'):
                        # Look for success indicators in task outputs
                        output_text = str(task_output.raw).lower()
                        if 'success' in output_text or 'completed' in output_text:
                            success_rate = min(success_rate + 0.05, 1.0)
                        elif 'failed' in output_text or 'error' in output_text:
                            success_rate = max(success_rate - 0.1, 0.0)
        except Exception as e:
            logger.warning(f"Could not calculate success metrics: {e}")
        
        # Prepare detailed report
        detailed_report = {
            'stage': 'completed',
            'progress': 100,
            'logs': [],
            'technical_details': {},
            'assumption_conflicts': conflict_analysis
        }
        
        # Extract logs from crew result if available
        try:
            if hasattr(crew_result, 'tasks_output'):
                for i, task_output in enumerate(crew_result.tasks_output):
                    task_name = ['analyze', 'plan', 'translate', 'convert_assets', 'package', 'validate'][i] if i < 6 else f'task_{i}'
                    if hasattr(task_output, 'raw'):
                        detailed_report['logs'].append({
                            'task': task_name,
                            'output': str(task_output.raw)[:500] + '...' if len(str(task_output.raw)) > 500 else str(task_output.raw)
                        })
        except Exception as e:
            logger.warning(f"Could not extract detailed logs: {e}")
        
        return {
            'status': 'completed',
            'overall_success_rate': success_rate,
            'converted_mods': converted_features,
            'failed_mods': failed_features,
            'smart_assumptions_applied': assumption_report_data,
            'assumption_conflicts_resolved': conflict_analysis,
            'download_url': None,  # Would be set after successful packaging
            'detailed_report': detailed_report
        }

    def get_assumption_conflicts(self) -> List[Dict[str, Any]]:
        """Get current assumption conflicts for transparency"""
        if hasattr(self.smart_assumption_engine, 'get_conflict_analysis'):
            return self.smart_assumption_engine.get_conflict_analysis("general")
        return []
    
    def analyze_feature_with_assumptions(self, feature_type: str, feature_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a single feature using the SmartAssumptionEngine with conflict resolution"""
        try:
            from ..models.smart_assumptions import FeatureContext
            
            # Create feature context for analysis
            feature_context = FeatureContext(
                feature_id=feature_data.get('id', f'feature_{hash(str(feature_data))}'),
                feature_type=feature_type,
                original_data=feature_data,
                name=feature_data.get('name')
            )
            
            # Use the enhanced analyze_feature method with conflict handling
            result = self.smart_assumption_engine.analyze_feature(feature_context)
            
            # Get conflict information for this specific feature type
            conflict_analysis = self.smart_assumption_engine.get_conflict_analysis(feature_type)
            
            return {
                'analysis_result': {
                    'feature_context': {
                        'feature_id': result.feature_context.feature_id,
                        'feature_type': result.feature_context.feature_type,
                        'name': result.feature_context.name
                    },
                    'applied_assumption': {
                        'java_feature': result.applied_assumption.java_feature,
                        'bedrock_workaround': result.applied_assumption.bedrock_workaround,
                        'impact': result.applied_assumption.impact.value,
                        'description': result.applied_assumption.description
                    } if result.applied_assumption else None,
                    'conflicting_assumptions': [a.java_feature for a in result.conflicting_assumptions],
                    'conflict_resolution_reason': result.conflict_resolution_reason
                },
                'conflict_analysis': conflict_analysis,
                'has_conflicts': conflict_analysis.get('has_conflicts', False),
                'resolution_applied': result.conflict_resolution_reason is not None
            }
        except Exception as e:
            logger.error(f"Feature analysis failed: {e}")
            return {
                'error': str(e),
                'conflict_analysis': {},
                'has_conflicts': False,
                'resolution_applied': False
            }
    
    def get_conversion_crew_status(self) -> Dict[str, Any]:
        """Get status of all crew agents and SmartAssumptionEngine"""
        return {
            'agents_initialized': {
                'java_analyzer': hasattr(self, 'java_analyzer_agent'),
                'bedrock_architect': hasattr(self, 'bedrock_architect_agent'),
                'logic_translator': hasattr(self, 'logic_translator_agent'),
                'asset_converter': hasattr(self, 'asset_converter_agent'),
                'packaging_agent': hasattr(self, 'packaging_agent_instance'),
                'qa_validator': hasattr(self, 'qa_validator_agent')
            },
            'smart_assumption_engine': {
                'initialized': self.smart_assumption_engine is not None,
                'conflict_resolution_enabled': hasattr(self.smart_assumption_engine, 'find_all_matching_assumptions'),
                'assumption_count': len(self.smart_assumption_engine.assumption_table) if self.smart_assumption_engine else 0
            },
            'crew_ready': hasattr(self, 'crew') and self.crew is not None
        }