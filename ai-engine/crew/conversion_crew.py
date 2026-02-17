"""
ModPorter AI Conversion Crew
Implements PRD Feature 2: AI Conversion Engine using CrewAI multi-agent system
"""

from crewai import Agent, Task, Crew, Process
from typing import Dict, List, Any, Optional
import json
import os
from pathlib import Path
import tempfile
import shutil

from agents.java_analyzer import JavaAnalyzerAgent
from agents.bedrock_architect import BedrockArchitectAgent
from agents.logic_translator import LogicTranslatorAgent
from agents.asset_converter import AssetConverterAgent
from agents.packaging_agent import PackagingAgent
from agents.qa_validator import QAValidatorAgent
from agents.variant_loader import variant_loader

# Import enhanced orchestration system
from orchestration.crew_integration import EnhancedConversionCrew

# Variant constants for enhanced orchestration selection
ENHANCED_VARIANTS = {
    'parallel_basic',
    'parallel_adaptive', 
    'hybrid',
    'enhanced_logic',
    'variant_enhanced_logic'
}

CONTROL_VARIANTS = {'control', 'sequential', 'baseline'}
# --- INTEGRATION PLAN FOR QAAgent ---
# The following comments outline where and how the new QAAgent
# (for comprehensive QA testing) would be integrated into this crew.
# Actual implementation would occur in a subsequent step.
#
# 1. Import QAAgent:
#    from src.agents.qa_agent import QAAgent # Add this near other agent imports
# --- END INTEGRATION PLAN ---
from models.smart_assumptions import ConversionPlanComponent, AssumptionReport
from utils.rate_limiter import create_rate_limited_llm, create_ollama_llm
from utils.logging_config import get_crew_logger, log_performance

# Import progress callback for real-time updates
try:
    from utils.progress_callback import ProgressCallback
    PROGRESS_CALLBACK_AVAILABLE = True
except ImportError:
    PROGRESS_CALLBACK_AVAILABLE = False
    ProgressCallback = None

# Use enhanced crew logger
logger = get_crew_logger()


class ModPorterConversionCrew:
    """
    Multi-agent crew for converting Java mods to Bedrock add-ons
    Following PRD Section 3.0.3: CrewAI framework implementation
    """
    
    def __init__(self, model_name: str = "gpt-4", variant_id: str = None, progress_callback: Optional["ProgressCallback"] = None):
        # Store variant ID
        self.variant_id = variant_id
        
        # Store progress callback for real-time updates
        self.progress_callback = progress_callback
        
        # Initialize enhanced orchestration crew
        self.enhanced_crew = None
        self.use_enhanced_orchestration = self._should_use_enhanced_orchestration(variant_id)
        
        # Check for Ollama configuration first (for local testing)
        if os.getenv("USE_OLLAMA", "false").lower() == "true":
            try:
                ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2")
                logger.info(f"Using Ollama with model: {ollama_model}")
                # Auto-detect Ollama base URL based on environment
                default_base_url = "http://ollama:11434" if os.getenv("DOCKER_ENVIRONMENT") else "http://localhost:11434"
                base_url = os.getenv("OLLAMA_BASE_URL", default_base_url)
                
                # Create Ollama LLM with rate limiting
                self.llm = create_ollama_llm(model=ollama_model, base_url=base_url)
            except Exception as e:
                logger.error(f"Failed to initialize Ollama LLM: {e}")
                raise
        else:
            # Use OpenAI-compatible API with rate limiting
            self.llm = create_rate_limited_llm(model=model_name)
        
        # Load variant configuration if provided
        self.variant_config = None
        if self.variant_id:
            self.variant_config = variant_loader.load_variant_config(self.variant_id)
            if self.variant_config:
                logger.info(f"Using variant configuration: {self.variant_config.get('name', self.variant_id)}")
            else:
                logger.warning(f"Variant {self.variant_id} configuration not found, using default")
        
        # Initialize agents with variant-specific configurations
        self._initialize_agents()
        
        # Initialize enhanced orchestration if enabled
        if self.use_enhanced_orchestration:
            self._initialize_enhanced_orchestration(model_name, variant_id)
    
    def _initialize_agents(self):
        """Initialize specialized agents as per PRD Feature 2 requirements"""
        
        # Initialize agent instances
        self.java_analyzer_agent = JavaAnalyzerAgent()
        self.bedrock_architect_agent = BedrockArchitectAgent()
        self.logic_translator_agent = LogicTranslatorAgent()
        self.asset_converter_agent = AssetConverterAgent()
        self.packaging_agent_instance = PackagingAgent()
        self.qa_validator_agent = QAValidatorAgent()
        # --- INTEGRATION PLAN FOR QAAgent ---
        # 2. Initialize QAAgent instance:
        #    self.actual_qa_agent = QAAgent() # Initialize the actual QAAgent
        # --- END INTEGRATION PLAN ---
        
        # Get agent configurations from variant if available
        java_analyzer_config = {}
        bedrock_architect_config = {}
        logic_translator_config = {}
        
        if self.variant_config:
            agents_config = self.variant_config.get("agents", {})
            java_analyzer_config = agents_config.get("java_analyzer", {})
            bedrock_architect_config = agents_config.get("bedrock_architect", {})
            logic_translator_config = agents_config.get("logic_translator", {})
            agents_config.get("asset_converter", {})
        
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
        
        # Apply variant configuration if available
        if java_analyzer_config:
            if "model" in java_analyzer_config:
                llm_params = {
                    'model': java_analyzer_config["model"],
                    'temperature': java_analyzer_config.get("temperature"),
                    'max_tokens': java_analyzer_config.get("max_tokens")
                }
                # Filter out None values so defaults are used
                llm_params = {k: v for k, v in llm_params.items() if v is not None}
                agent_kwargs["llm"] = create_rate_limited_llm(**llm_params)
        
        # Disable memory when using Ollama to avoid validation issues
        if os.getenv("USE_OLLAMA", "false").lower() == "true":
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
        
        # Apply variant configuration if available
        if bedrock_architect_config:
            if "model" in bedrock_architect_config:
                llm_params = {
                    'model': bedrock_architect_config["model"],
                    'temperature': bedrock_architect_config.get("temperature"),
                    'max_tokens': bedrock_architect_config.get("max_tokens")
                }
                # Filter out None values so defaults are used
                llm_params = {k: v for k, v in llm_params.items() if v is not None}
                architect_kwargs["llm"] = create_rate_limited_llm(**llm_params)
        
        if os.getenv("USE_OLLAMA", "false").lower() == "true":
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
        
        # Apply variant configuration if available
        if logic_translator_config:
            if "model" in logic_translator_config:
                llm_params = {
                    'model': logic_translator_config["model"],
                    'temperature': logic_translator_config.get("temperature"),
                    'max_tokens': logic_translator_config.get("max_tokens")
                }
                # Filter out None values so defaults are used
                llm_params = {k: v for k, v in llm_params.items() if v is not None}
                translator_kwargs["llm"] = create_rate_limited_llm(**llm_params)
        
        if os.getenv("USE_OLLAMA", "false").lower() == "true":
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
        
        if os.getenv("USE_OLLAMA", "false").lower() == "true":
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
        
        if os.getenv("USE_OLLAMA", "false").lower() == "true":
            packaging_kwargs["memory"] = False
            
        self.packaging_agent = Agent(**packaging_kwargs)
        
        # PRD Feature 2: QA Agent (This is the existing QAValidatorAgent)
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
        
        if os.getenv("USE_OLLAMA", "false").lower() == "true":
            qa_kwargs["memory"] = False
            
        self.qa_validator = Agent(**qa_kwargs)

        # --- INTEGRATION PLAN FOR QAAgent ---
        # 2. Initialize crewai.Agent wrapper for QAAgent:
        #    comprehensive_qa_kwargs = {
        #        "role": "Comprehensive QA Tester",
        #        "goal": "Perform in-depth QA testing using a predefined framework and scenarios",
        #        "backstory": """You are an advanced QA agent that uses a structured testing
        #        framework (TestFramework) and a scenario generator (TestScenarioGenerator)
        #        to execute a variety of tests (functional, performance, compatibility)
        #        on the converted add-on package.""",
        #        "verbose": True,
        #        "allow_delegation": False, # Or True if it needs to delegate sub-tasks
        #        "llm": self.llm,
        #        # "tools": [tool_to_run_qa_pipeline] # A tool would be needed to trigger QAAgent.run_qa_pipeline()
        #                                          # This tool would take scenario_file_path as input.
        #    }
        #    if os.getenv("MOCK_AI_RESPONSES", "false").lower() == "true":
        #        comprehensive_qa_kwargs["memory"] = False
        #    self.comprehensive_qa_tester_agent = Agent(**comprehensive_qa_kwargs)
        # --- END INTEGRATION PLAN ---
    
    def _should_use_enhanced_orchestration(self, variant_id: Optional[str]) -> bool:
        """
        Determine whether to use the enhanced orchestration system
        
        Args:
            variant_id: A/B testing variant identifier
            
        Returns:
            True if enhanced orchestration should be used
        """
        
        # Check environment variable override
        env_override = os.getenv("USE_ENHANCED_ORCHESTRATION", "").lower()
        if env_override in ["true", "1", "yes"]:
            logger.info("Enhanced orchestration enabled via environment variable")
            return True
        elif env_override in ["false", "0", "no"]:
            logger.info("Enhanced orchestration disabled via environment variable")
            return False
        
        # Check variant configuration
        if variant_id:
            # Check if variant matches enhanced patterns
            variant_lower = variant_id.lower()
            for enhanced_variant in ENHANCED_VARIANTS:
                if enhanced_variant in variant_lower:
                    logger.info(f"Enhanced orchestration enabled for variant: {variant_id}")
                    return True
            
            # Control/sequential variants use original system
            for control_variant in CONTROL_VARIANTS:
                if control_variant in variant_lower:
                    logger.info(f"Using original orchestration for control variant: {variant_id}")
                    return False
        
        # Default: use enhanced orchestration for new features
        # This can be changed to False for conservative rollout
        default_enhanced = os.getenv("DEFAULT_ENHANCED_ORCHESTRATION", "true").lower() == "true"
        logger.info(f"Using default enhanced orchestration setting: {default_enhanced}")
        return default_enhanced
    
    def _initialize_enhanced_orchestration(self, model_name: str, variant_id: Optional[str]):
        """Initialize the enhanced orchestration system"""
        try:
            self.enhanced_crew = EnhancedConversionCrew(
                model_name=model_name,
                variant_id=variant_id
            )
            logger.info("Enhanced orchestration crew initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize enhanced orchestration: {e}")
            logger.warning("Falling back to original CrewAI system")
            self.use_enhanced_orchestration = False
            self.enhanced_crew = None
    
    def _setup_crew(self):
        """Setup the crew workflow following PRD conversion process"""
        
        # Define tasks in sequence
        self.analyze_task = Task(
            description="""Analyze the provided Java mod file to identify:
            1. All assets (textures, models, sounds) - use extract_assets_tool with mod_path input
            2. Code logic and custom mechanics - use identify_features_tool with mod_path input  
            3. Dependencies and mod framework used - use analyze_mod_structure_tool with mod_path input
            4. Feature types (blocks, items, entities, dimensions, GUI, etc.)
            5. Incompatible features that require smart assumptions
            
            Use the mod_path from the task inputs: {mod_path}
            
            Pass the mod_path directly to each tool as a string parameter.
            After each tool execution, provide a BRIEF summary (max 50 words) of what was found.
            If a tool fails or times out, return a simple JSON response with the error.
            Keep all responses very concise - aim for under 500 characters total to prevent timeouts.
            
            Final output should be a simple JSON with: assets, features, dependencies, framework.""",
            agent=self.java_analyzer,
            expected_output="Simple JSON with assets, features, dependencies, framework (under 500 characters)"
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
            description="""Assemble all converted components into a valid .mcaddon using the enhanced Bedrock generation system:
            
            ENHANCED BEDROCK GENERATION WORKFLOW:
            1. Extract mod metadata (name, description, version) from the analysis report.
            2. Use 'generate_enhanced_manifests_tool' to create standards-compliant behavior and resource pack manifests with proper UUIDs, dependencies, and capabilities.
            3. Use 'generate_blocks_and_items_tool' to convert Java blocks, items, and recipes to Bedrock format with proper components and creative menu integration.
            4. Use 'generate_entities_tool' to convert Java entities to Bedrock format with behaviors, animations, and proper AI goals.
            5. Create package structure and organize all components into proper Bedrock directory hierarchy.
            6. Use 'package_enhanced_addon_tool' to create the final .mcaddon file with correct structure (behavior_packs/ and resource_packs/ directories).
            7. Use 'validate_enhanced_addon_tool' to perform comprehensive validation including manifest schema validation, file structure checks, and compatibility analysis.
            8. Generate detailed installation and usage instructions.
            
            The enhanced system provides:
            - Standards-compliant manifest generation with proper UUIDs and dependencies
            - Automatic block/item/entity conversion with Bedrock components
            - Comprehensive validation with detailed scoring and feedback
            - Proper .mcaddon file structure for Bedrock compatibility
            
            Return comprehensive results including validation scores, compatibility analysis, and any issues found.""",
            agent=self.packaging_agent,
            expected_output="Complete .mcaddon package with validation score, compatibility analysis, and detailed generation report",
            context=[self.analyze_task, self.plan_task, self.translate_task, self.convert_assets_task]
        )
        
        self.validate_task = Task( # This is the existing QAValidatorAgent's task
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

        # --- INTEGRATION PLAN FOR QAAgent ---
        # 3. Define the new crewai.Task for comprehensive QA:
        #    self.comprehensive_testing_task = Task(
        #        description="""Execute a comprehensive QA test suite on the packaged .mcaddon file.
        #        This involves:
        #        1. Loading test scenarios from a predefined path (e.g., 'ai-engine/src/testing/scenarios/example_scenarios.json').
        #        2. Running functional tests based on these scenarios.
        #        3. Running performance tests based on these scenarios.
        #        4. Running compatibility tests based on these scenarios.
        #        5. Collecting all results and generating a structured QA pipeline output.
        #
        #        The task should use a tool that invokes the QAAgent's `run_qa_pipeline` method,
        #        passing the path to the scenario file. The output of this pipeline
        #        (a dictionary of results) will be the output of this task.""",
        #        agent=self.comprehensive_qa_tester_agent, # The new crewAI agent wrapper for QAAgent
        #        expected_output="A JSON string or dictionary containing the full results from the QAAgent's pipeline, including functional, performance, and compatibility test outcomes.",
        #        context=[self.validate_task] # This task runs AFTER the initial validation.
        #    )
        #
        # 5. Invoking QAAgent.run_qa_pipeline():
        #    The `comprehensive_qa_tester_agent` would need a tool. Let's call it `RunQAPipelineTool`.
        #    This tool's `run` method would essentially do:
        #    `return self.actual_qa_agent.run_qa_pipeline(scenario_file_path="ai-engine/src/testing/scenarios/example_scenarios.json")`
        #    The task's description would instruct the agent to use this tool.
        #    The output of this tool (the dictionary from `run_qa_pipeline`) would become the task's output.
        # --- END INTEGRATION PLAN ---
        
        # Create the crew
        self.crew = Crew(
            agents=[
                self.java_analyzer,
                self.bedrock_architect,
                self.logic_translator,
                self.asset_converter,
                self.packaging_agent,
                self.qa_validator
                # --- INTEGRATION PLAN FOR QAAgent ---
                # 4. Add the new agent to the Crew's agent list:
                #    self.comprehensive_qa_tester_agent,
                # --- END INTEGRATION PLAN ---
            ],
            tasks=[
                self.analyze_task,
                self.plan_task,
                self.translate_task,
                self.convert_assets_task,
                self.package_task,
                self.validate_task
                # --- INTEGRATION PLAN FOR QAAgent ---
                # 4. Add the new task to the Crew's task list:
                #    self.comprehensive_testing_task,
                # --- END INTEGRATION PLAN ---
            ],
            process=Process.sequential,
            verbose=True
        )
    
    async def _report_progress(self, agent: str, status: str, progress: int, message: str):
        """Send progress update via callback if available"""
        if self.progress_callback:
            try:
                await self.progress_callback.send_progress(
                    agent=agent,
                    status=status,
                    progress=progress,
                    message=message
                )
            except Exception as e:
                logger.warning(f"Failed to send progress update: {e}")

    @log_performance("mod_conversion")
    def convert_mod(
        self, 
        mod_path: Path, 
        output_path: Path,
        smart_assumptions: bool = True,
        include_dependencies: bool = True,
        job_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute the full conversion process
        
        Args:
            mod_path: Path to Java mod file or directory
            output_path: Path for converted output
            smart_assumptions: Enable smart assumption processing
            include_dependencies: Include dependency analysis
            job_id: Optional job ID for progress tracking
            
        Returns:
            Conversion result following PRD Feature 3 format
        """
        
        # Log conversion start with context
        logger.log_operation_start("mod_conversion", 
                                 mod_path=str(mod_path),
                                 output_path=str(output_path),
                                 smart_assumptions=smart_assumptions,
                                 include_dependencies=include_dependencies)
        
        # Send initial progress if callback available
        if self.progress_callback:
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._report_progress("ConversionWorkflow", "in_progress", 0, "Starting conversion process"))
                else:
                    loop.run_until_complete(self._report_progress("ConversionWorkflow", "in_progress", 0, "Starting conversion process"))
            except Exception as e:
                logger.warning(f"Failed to send initial progress: {e}")
        
        # Check if we should use enhanced orchestration
        if self.use_enhanced_orchestration and self.enhanced_crew:
            logger.info("Using enhanced orchestration system for conversion")
            return self._convert_with_enhanced_orchestration(
                mod_path, output_path, smart_assumptions, include_dependencies
            )
        else:
            logger.info("Using original CrewAI system for conversion")
            return self._convert_with_original_crew(
                mod_path, output_path, smart_assumptions, include_dependencies
            )
    
    def _convert_with_enhanced_orchestration(
        self, 
        mod_path: Path, 
        output_path: Path,
        smart_assumptions: bool,
        include_dependencies: bool
    ) -> Dict[str, Any]:
        """Execute conversion using the enhanced orchestration system"""
        try:
            # Use the enhanced crew for conversion
            result = self.enhanced_crew.convert_mod(
                mod_path=mod_path,
                output_path=output_path,
                smart_assumptions=smart_assumptions,
                include_dependencies=include_dependencies
            )
            
            logger.info("Enhanced orchestration conversion completed")
            return result
            
        except Exception as e:
            logger.error(f"Enhanced orchestration conversion failed: {e}")
            logger.warning("Attempting fallback to original CrewAI system")
            
            # Fallback to original system
            try:
                return self._convert_with_original_crew(
                    mod_path, output_path, smart_assumptions, include_dependencies
                )
            except Exception as fallback_error:
                logger.error(f"Fallback conversion also failed: {fallback_error}")
                return self._create_failure_response(
                    f"Both enhanced and original conversion failed. Enhanced: {e}, Original: {fallback_error}",
                    mod_path
                )
    
    def _convert_with_original_crew(
        self, 
        mod_path: Path, 
        output_path: Path,
        smart_assumptions: bool,
        include_dependencies: bool
    ) -> Dict[str, Any]:
        """Execute conversion using the original CrewAI system"""
        
        temp_dir = None  # Initialize temp_dir to None
        
        try:
            # Resolve the mod path relative to /app if it's a relative path
            if not mod_path.is_absolute():
                original_path = str(mod_path)
                mod_path = Path("/app") / mod_path
                logger.debug(f"Resolved relative path from {original_path} to {mod_path}")
            
            # Check if mod file exists
            if not mod_path.exists():
                error_msg = f"Mod file not found: {mod_path}"
                logger.error(error_msg)
                return {
                    'status': 'failed',
                    'error': error_msg,
                    'overall_success_rate': 0.0,
                    'converted_mods': [],
                    'failed_mods': [{'name': str(mod_path), 'reason': 'File not found', 'suggestions': ['Check file path']}],
                    'smart_assumptions_applied': [],
                    'download_url': None,
                    'detailed_report': {'stage': 'error', 'progress': 0, 'logs': [f'Mod file not found: {mod_path}']}
                }
            
            # Resolve the output path relative to /app if it's a relative path
            if not output_path.is_absolute():
                output_path = Path("/app") / output_path
                logger.debug(f"Resolved output path to: {output_path}")
            
            # Set up the original crew if not already done
            if not hasattr(self, 'crew') or self.crew is None:
                self._setup_crew()
            
            # Create a temporary directory for intermediate files 
            # Use /tmp for local testing, /app/conversion_outputs for Docker
            output_base_dir = os.getenv("CONVERSION_OUTPUT_DIR", "/tmp")
            temp_dir = Path(tempfile.mkdtemp(dir=output_base_dir))
            logger.info(f"Created temporary directory for conversion: {temp_dir}")
            
            # Prepare inputs for the crew
            inputs = {
                'mod_path': str(mod_path),
                'output_path': str(output_path),
                'temp_dir': str(temp_dir),  # Pass the temporary directory to the crew
                'smart_assumptions_enabled': smart_assumptions,
                'include_dependencies': include_dependencies
            }
            logger.debug(f"Crew inputs: {inputs}")
            
            # Execute the crew workflow
            try:
                logger.info("Starting original crew execution...")
                result = self.crew.kickoff(inputs=inputs)
                logger.info(f"Crew execution completed with result: {type(result)}")
                
                # Check if crew execution failed or returned invalid result
                if result is None or (hasattr(result, 'raw') and not result.raw):
                    logger.error("Crew execution failed - no valid result returned")
                    raise RuntimeError("Crew execution failed - no valid result returned")
                    
            except Exception as crew_error:
                logger.error(f"Crew execution failed: {crew_error}")
                raise RuntimeError(f"Crew execution failed: {crew_error}")
            
            # Extract conversion plan components for assumption reporting
            plan_components = self._extract_plan_components(result)
            
            # Generate comprehensive assumption report using enhanced engine
            conversion_report = self._format_conversion_report(result, plan_components)
            
            logger.info("Original crew conversion completed successfully")
            return conversion_report

        except Exception as e:
            logger.error(f"Original crew conversion failed: {str(e)}")
            return self._create_failure_response(str(e), mod_path)
        finally:
            # Clean up temporary directory if it was created
            if temp_dir and temp_dir.exists():
                shutil.rmtree(temp_dir)
                logger.info(f"Cleaned up temporary directory: {temp_dir}")
    
    def _create_failure_response(self, error_message: str, mod_path: Path) -> Dict[str, Any]:
        """Create standardized failure response dictionary"""
        return {
            'status': 'failed',
            'error': error_message,
            'overall_success_rate': 0.0,
            'converted_mods': [],
            'failed_mods': [{'name': str(mod_path), 'reason': error_message, 'suggestions': []}],
            'smart_assumptions_applied': [],
            'download_url': None,
            'detailed_report': {'stage': 'error', 'progress': 0, 'logs': [error_message]}
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
            # --- INTEGRATION PLAN FOR QAAgent ---
            # 6. Incorporate QAAgent results into the final report:
            #    The output from `self.comprehensive_testing_task` (which is the dictionary from
            #    QAAgent.run_qa_pipeline()) should be added here.
            #    For example:
            #    `detailed_report['comprehensive_qa_results'] = comprehensive_testing_task_output`
            #    The `comprehensive_testing_task_output` would be retrieved from `crew_result.tasks_output`
            #    based on the task's position in the sequence.
            #
            #    The `overall_success_rate` and other summary metrics could also be updated
            #    based on the `comprehensive_qa_results`. For example, if the QA pipeline
            #    reports a low pass rate, the `overall_success_rate` might be adjusted downwards.
            # --- END INTEGRATION PLAN ---
        }
        
        # Extract logs from crew result if available
        try:
            if hasattr(crew_result, 'tasks_output'):
                for i, task_output in enumerate(crew_result.tasks_output):
                    task_names = ['analyze', 'plan', 'translate', 'convert_assets', 'package', 'validate']
                    # --- INTEGRATION PLAN FOR QAAgent ---
                    # Add 'comprehensive_qa' to task_names if the new task is added
                    # task_names.append('comprehensive_qa')
                    # --- END INTEGRATION PLAN ---
                    task_name = task_names[i] if i < len(task_names) else f'task_{i}'
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
                # --- INTEGRATION PLAN FOR QAAgent ---
                # Add comprehensive_qa_tester_agent status:
                # 'comprehensive_qa_tester': hasattr(self, 'comprehensive_qa_tester_agent')
                # --- END INTEGRATION PLAN ---
            },
            'smart_assumption_engine': {
                'initialized': self.smart_assumption_engine is not None,
                'conflict_resolution_enabled': hasattr(self.smart_assumption_engine, 'find_all_matching_assumptions'),
                'assumption_count': len(self.smart_assumption_engine.assumption_table) if self.smart_assumption_engine else 0
            },
            'crew_ready': hasattr(self, 'crew') and self.crew is not None
        }
