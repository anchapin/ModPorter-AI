"""
ModPorter AI Conversion Crew
Implements PRD Feature 2: AI Conversion Engine using CrewAI multi-agent system
"""

from crewai import Agent, Task, Crew, Process
from langchain_openai import ChatOpenAI
from typing import Dict, List, Any, Optional
import json
import logging
from pathlib import Path

from ..agents.java_analyzer import JavaAnalyzerAgent
from ..agents.bedrock_architect import BedrockArchitectAgent
from ..agents.logic_translator import LogicTranslatorAgent
from ..agents.asset_converter import AssetConverterAgent
from ..agents.packaging_agent import PackagingAgent
from ..agents.qa_validator import QAValidatorAgent
from ..models.smart_assumptions import SmartAssumptionEngine
from ..utils.config import settings

logger = logging.getLogger(__name__)


class ModPorterConversionCrew:
    """
    Multi-agent crew for converting Java mods to Bedrock add-ons
    Following PRD Section 3.0.3: CrewAI framework implementation
    """
    
    def __init__(self, model_name: str = "gpt-4"):
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=0.1,  # Low temperature for consistent technical output
            max_tokens=4000
        )
        
        self.smart_assumption_engine = SmartAssumptionEngine()
        self._setup_agents()
        self._setup_crew()
    
    def _setup_agents(self):
        """Initialize specialized agents as per PRD Feature 2 requirements"""
        
        # PRD Feature 2: Analyzer Agent
        self.java_analyzer = Agent(
            role="Java Mod Analyzer",
            goal="Accurately analyze Java mod structure, dependencies, and features",
            backstory="""You are an expert Java developer with deep knowledge of Minecraft 
            modding frameworks like Forge, Fabric, and Quilt. You can deconstruct any mod 
            to understand its components, dependencies, and intended functionality.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[JavaAnalyzerAgent().get_tools()]
        )
        
        # PRD Feature 2: Planner Agent (Bedrock Architect)
        self.bedrock_architect = Agent(
            role="Bedrock Conversion Architect",
            goal="Design optimal conversion strategies using smart assumptions",
            backstory="""You are a Minecraft Bedrock add-on expert who understands the 
            limitations and capabilities of the Bedrock platform. You excel at finding 
            creative workarounds and making intelligent compromises to adapt Java features 
            for Bedrock.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[BedrockArchitectAgent().get_tools()]
        )
        
        # PRD Feature 2: Logic Translation Agent
        self.logic_translator = Agent(
            role="Code Logic Translator",
            goal="Convert Java code to Bedrock JavaScript with proper error handling",
            backstory="""You are a polyglot programmer specializing in Java to JavaScript 
            conversion. You understand both object-oriented and event-driven paradigms 
            and can bridge the gap between Minecraft's Java API and Bedrock's JavaScript API.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[LogicTranslatorAgent().get_tools()]
        )
        
        # PRD Feature 2: Asset Conversion Agent
        self.asset_converter = Agent(
            role="Asset Conversion Specialist",
            goal="Convert all visual and audio assets to Bedrock-compatible formats",
            backstory="""You are a technical artist who specializes in game asset 
            conversion. You understand the technical requirements for Minecraft Bedrock 
            textures, models, and sounds, and can optimize them for performance.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[AssetConverterAgent().get_tools()]
        )
        
        # PRD Feature 2: Packaging Agent
        self.packaging_agent = Agent(
            role="Bedrock Package Builder",
            goal="Assemble converted components into valid .mcaddon packages",
            backstory="""You are a Bedrock add-on packaging expert who knows the exact 
            file structure, manifest requirements, and validation rules for creating 
            working .mcaddon files.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[PackagingAgent().get_tools()]
        )
        
        # PRD Feature 2: QA Agent
        self.qa_validator = Agent(
            role="Quality Assurance Validator",
            goal="Validate conversion quality and generate comprehensive reports",
            backstory="""You are a meticulous QA engineer who tests both functionality 
            and user experience. You can identify potential issues and provide clear, 
            actionable feedback on conversion quality.""",
            verbose=True,
            allow_delegation=False,
            llm=self.llm,
            tools=[QAValidatorAgent().get_tools()]
        )
    
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
            1. Maps each Java feature to a Bedrock equivalent
            2. Identifies features requiring smart assumptions from the PRD table
            3. Flags features that cannot be converted and must be excluded
            4. Provides detailed conversion strategy for each component
            
            Use the Smart Assumption Engine to handle incompatible features.""",
            agent=self.bedrock_architect,
            expected_output="Comprehensive conversion plan with smart assumption mappings",
            context=[self.analyze_task]
        )
        
        self.translate_task = Task(
            description="""Convert Java code to Bedrock JavaScript following the plan:
            1. Translate object-oriented Java to event-driven JavaScript
            2. Map Java APIs to equivalent Bedrock APIs
            3. Comment out untranslatable code with explanations
            4. Handle the paradigm shift properly
            5. Ensure all scripts follow Bedrock scripting standards
            
            For untranslatable logic, add explanatory notes for developers.""",
            agent=self.logic_translator,
            expected_output="Converted JavaScript files with detailed comments",
            context=[self.analyze_task, self.plan_task]
        )
        
        self.convert_assets_task = Task(
            description="""Convert all assets to Bedrock-compatible formats:
            1. Convert textures to proper resolution and format
            2. Convert 3D models to Bedrock geometry format
            3. Convert sounds to supported audio formats
            4. Organize assets in correct Bedrock folder structure
            5. Generate necessary texture and model definition files
            
            Ensure all assets meet Bedrock technical requirements.""",
            agent=self.asset_converter,
            expected_output="Converted assets in proper Bedrock folder structure",
            context=[self.analyze_task, self.plan_task]
        )
        
        self.package_task = Task(
            description="""Assemble all converted components into a valid .mcaddon:
            1. Create proper manifest.json with correct metadata
            2. Organize all files in correct Bedrock add-on structure
            3. Validate package integrity
            4. Generate installation instructions
            5. Create .mcaddon archive
            
            Ensure the package meets all Bedrock add-on standards.""",
            agent=self.packaging_agent,
            expected_output="Complete .mcaddon package ready for installation",
            context=[self.translate_task, self.convert_assets_task]
        )
        
        self.validate_task = Task(
            description="""Validate the conversion and generate the final report:
            1. Check package validity and completeness
            2. Verify all converted features work as expected
            3. Document all smart assumptions applied
            4. Generate user-friendly conversion report
            5. Create technical log for developers
            
            Provide both high-level summary and detailed technical analysis.""",
            agent=self.qa_validator,
            expected_output="Complete conversion report with success metrics",
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
                'smart_assumption_table': self.smart_assumption_engine.get_assumption_table()
            }
            
            # Execute the crew workflow
            result = self.crew.kickoff(inputs=inputs)
            
            # Process and format the result according to PRD Feature 3
            conversion_report = self._format_conversion_report(result)
            
            logger.info("Conversion completed successfully")
            return conversion_report
            
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
            return {
                'status': 'failed',
                'error': str(e),
                'overall_success_rate': 0.0,
                'converted_mods': [],
                'failed_mods': [{'name': 'Unknown', 'reason': str(e), 'suggestions': []}],
                'smart_assumptions_applied': [],
                'detailed_report': {'stage': 'error', 'progress': 0, 'logs': [str(e)]}
            }
    
    def _format_conversion_report(self, crew_result: Any) -> Dict[str, Any]:
        """Format crew result into PRD Feature 3 report structure"""
        # This would process the crew's output and format it according to
        # the ConversionResponse model defined in the PRD
        
        # Placeholder implementation - would parse actual crew results
        return {
            'status': 'completed',
            'overall_success_rate': 0.85,  # Would be calculated from actual results
            'converted_mods': [],  # Would be populated from crew analysis
            'failed_mods': [],
            'smart_assumptions_applied': [],
            'download_url': None,  # Would be set after packaging
            'detailed_report': {
                'stage': 'completed',
                'progress': 100,
                'logs': [],
                'technical_details': crew_result
            }
        }