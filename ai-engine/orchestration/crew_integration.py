"""
Integration layer for connecting the parallel orchestrator with existing CrewAI agents.
Part of Phase 3: Agent and Crew Integration
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
import time
import tempfile
import os
import shutil

from .orchestrator import ParallelOrchestrator
from .strategy_selector import StrategySelector, OrchestrationStrategy
from .task_graph import TaskGraph, TaskNode

# Import existing agents (this will need to be adapted based on actual imports)
from agents.java_analyzer import JavaAnalyzerAgent
from agents.bedrock_architect import BedrockArchitectAgent  
from agents.logic_translator import LogicTranslatorAgent
from agents.asset_converter import AssetConverterAgent
from agents.packaging_agent import PackagingAgent
from agents.qa_validator import QAValidatorAgent

logger = logging.getLogger(__name__)


class EnhancedConversionCrew:
    """
    Enhanced conversion crew that can use either the original sequential approach
    or the new parallel orchestration system based on A/B testing configuration.
    """
    
    def __init__(
        self,
        model_name: str = "gpt-4",
        variant_id: Optional[str] = None,
        force_strategy: Optional[OrchestrationStrategy] = None
    ):
        """
        Initialize the enhanced conversion crew
        
        Args:
            model_name: LLM model to use
            variant_id: A/B testing variant identifier
            force_strategy: Force a specific orchestration strategy (for testing)
        """
        self.model_name = model_name
        self.variant_id = variant_id
        self.force_strategy = force_strategy
        
        # Initialize strategy selector
        self.strategy_selector = StrategySelector()
        
        # Initialize parallel orchestrator
        self.orchestrator = ParallelOrchestrator(
            strategy_selector=self.strategy_selector,
            enable_monitoring=True
        )
        
        # Initialize agents
        self._initialize_agents()
        
        # Register agents with orchestrator
        self._register_agents()
        
        # Keep reference to original crew for fallback
        self.original_crew = None
        
    def _initialize_agents(self):
        """Initialize all agent instances"""
        self.java_analyzer_agent = JavaAnalyzerAgent()
        self.bedrock_architect_agent = BedrockArchitectAgent()  
        self.logic_translator_agent = LogicTranslatorAgent()
        self.asset_converter_agent = AssetConverterAgent()
        self.packaging_agent_instance = PackagingAgent()
        self.qa_validator_agent = QAValidatorAgent()
        
        logger.info("Initialized all agent instances")
    
    def _register_agents(self):
        """Register agents with the parallel orchestrator"""
        
        # Create agent executors that work with our task format
        self.orchestrator.register_agent(
            "java_analyzer",
            self._create_java_analyzer_executor(),
        )
        
        self.orchestrator.register_agent(
            "bedrock_architect", 
            self._create_bedrock_architect_executor(),
        )
        
        self.orchestrator.register_agent(
            "logic_translator",
            self._create_logic_translator_executor(),
        )
        
        self.orchestrator.register_agent(
            "asset_converter",
            self._create_asset_converter_executor(),
        )
        
        self.orchestrator.register_agent(
            "packaging_agent",
            self._create_packaging_agent_executor(),
        )
        
        self.orchestrator.register_agent(
            "qa_validator",
            self._create_qa_validator_executor(),
        )
        
        # Register any additional specialized agents
        if hasattr(self, 'entity_converter_agent'):
            self.orchestrator.register_agent(
                "entity_converter",
                self._create_entity_converter_executor(),
            )
        
        logger.info("Registered all agents with orchestrator")
    
    def _create_java_analyzer_executor(self):
        """Create executor for Java analyzer agent"""
        def executor(task_data: Dict[str, Any]) -> Dict[str, Any]:
            """Execute Java analysis task"""
            try:
                # Extract necessary data from task
                mod_path = task_data.get('mod_path')
                if not mod_path:
                    raise ValueError("mod_path is required for Java analysis")
                
                # Use the agent's tools to perform analysis
                tools = self.java_analyzer_agent.get_tools()
                
                # Execute analysis using the agent's tools
                # This mimics what would happen in CrewAI but in a stateless way
                analysis_result = {
                    'assets': [],
                    'features': {},
                    'dependencies': [],
                    'framework': 'unknown'
                }
                
                # Use tools to gather information
                for tool in tools:
                    try:
                        if hasattr(tool, 'name'):
                            if 'extract_assets' in tool.name:
                                assets = tool.run(mod_path=mod_path)
                                if assets:
                                    analysis_result['assets'] = assets
                            elif 'identify_features' in tool.name:
                                features = tool.run(mod_path=mod_path)
                                if features:
                                    analysis_result['features'] = features
                            elif 'analyze_mod_structure' in tool.name:
                                structure = tool.run(mod_path=mod_path)
                                if structure:
                                    analysis_result['dependencies'] = structure.get('dependencies', [])
                                    analysis_result['framework'] = structure.get('framework', 'unknown')
                    except Exception as tool_error:
                        logger.warning(f"Tool execution failed: {tool_error}")
                        continue
                
                logger.info(f"Java analysis completed for {mod_path}")
                return analysis_result
                
            except Exception as e:
                logger.error(f"Java analyzer execution failed: {e}")
                raise
        
        return executor
    
    def _create_bedrock_architect_executor(self):
        """Create executor for Bedrock architect agent"""
        def executor(task_data: Dict[str, Any]) -> Dict[str, Any]:
            """Execute Bedrock architecture planning task"""
            try:
                # This agent depends on analysis results
                # In the orchestrated version, we get these from the task context
                analysis_context = task_data.get('analysis_result', {})
                
                # Use the agent's tools for planning
                tools = self.bedrock_architect_agent.get_tools()
                
                planning_result = {
                    'conversion_plan': {},
                    'smart_assumptions': [],
                    'compatibility_analysis': {}
                }
                
                # Execute planning tools
                for tool in tools:
                    try:
                        if hasattr(tool, 'name'):
                            if 'create_conversion_plan' in tool.name:
                                plan = tool.run(analysis_data=analysis_context)
                                if plan:
                                    planning_result['conversion_plan'] = plan
                            elif 'apply_smart_assumption' in tool.name:
                                assumptions = tool.run(features=analysis_context.get('features', {}))
                                if assumptions:
                                    planning_result['smart_assumptions'] = assumptions
                    except Exception as tool_error:
                        logger.warning(f"Planning tool execution failed: {tool_error}")
                        continue
                
                logger.info("Bedrock architecture planning completed")
                return planning_result
                
            except Exception as e:
                logger.error(f"Bedrock architect execution failed: {e}")
                raise
        
        return executor
    
    def _create_logic_translator_executor(self):
        """Create executor for logic translator agent"""
        def executor(task_data: Dict[str, Any]) -> Dict[str, Any]:
            """Execute logic translation task"""
            try:
                # Get context from previous tasks
                analysis_context = task_data.get('analysis_result', {})
                planning_context = task_data.get('planning_result', {})
                
                # Use translator tools
                tools = self.logic_translator_agent.get_tools()
                
                translation_result = {
                    'converted_scripts': [],
                    'translation_report': {},
                    'untranslatable_code': []
                }
                
                # Execute translation tools
                for tool in tools:
                    try:
                        if hasattr(tool, 'name'):
                            if 'translate_java_to_javascript' in tool.name:
                                scripts = tool.run(
                                    features=analysis_context.get('features', {}),
                                    conversion_plan=planning_context.get('conversion_plan', {})
                                )
                                if scripts:
                                    translation_result['converted_scripts'] = scripts
                    except Exception as tool_error:
                        logger.warning(f"Translation tool execution failed: {tool_error}")
                        continue
                
                logger.info("Logic translation completed")
                return translation_result
                
            except Exception as e:
                logger.error(f"Logic translator execution failed: {e}")
                raise
        
        return executor
    
    def _create_asset_converter_executor(self):
        """Create executor for asset converter agent"""
        def executor(task_data: Dict[str, Any]) -> Dict[str, Any]:
            """Execute asset conversion task"""
            try:
                # Get asset information from analysis
                analysis_context = task_data.get('analysis_result', {})
                assets = analysis_context.get('assets', [])
                
                # Use asset converter tools
                tools = self.asset_converter_agent.get_tools()
                
                conversion_result = {
                    'converted_assets': [],
                    'asset_structure': {},
                    'conversion_report': {}
                }
                
                # Execute asset conversion tools
                for tool in tools:
                    try:
                        if hasattr(tool, 'name'):
                            if 'convert_texture_assets' in tool.name:
                                textures = tool.run(assets=assets)
                                if textures:
                                    conversion_result['converted_assets'].extend(textures)
                            elif 'convert_model_assets' in tool.name:
                                models = tool.run(assets=assets)
                                if models:
                                    conversion_result['converted_assets'].extend(models)
                    except Exception as tool_error:
                        logger.warning(f"Asset conversion tool execution failed: {tool_error}")
                        continue
                
                logger.info("Asset conversion completed")
                return conversion_result
                
            except Exception as e:
                logger.error(f"Asset converter execution failed: {e}")
                raise
        
        return executor
    
    def _create_packaging_agent_executor(self):
        """Create executor for packaging agent"""
        def executor(task_data: Dict[str, Any]) -> Dict[str, Any]:
            """Execute packaging task"""
            try:
                # Get all previous results
                analysis_context = task_data.get('analysis_result', {})
                planning_context = task_data.get('planning_result', {})
                translation_context = task_data.get('translation_result', {})
                asset_context = task_data.get('asset_result', {})
                
                output_path = task_data.get('output_path')
                
                # Use packaging tools
                tools = self.packaging_agent_instance.get_tools()
                
                packaging_result = {
                    'package_path': None,
                    'manifest_data': {},
                    'validation_score': 0.0,
                    'packaging_report': {}
                }
                
                # Execute packaging tools
                for tool in tools:
                    try:
                        if hasattr(tool, 'name'):
                            if 'package_enhanced_addon' in tool.name:
                                package_info = tool.run(
                                    converted_scripts=translation_context.get('converted_scripts', []),
                                    converted_assets=asset_context.get('converted_assets', []),
                                    output_path=output_path
                                )
                                if package_info:
                                    packaging_result.update(package_info)
                    except Exception as tool_error:
                        logger.warning(f"Packaging tool execution failed: {tool_error}")
                        continue
                
                logger.info("Packaging completed")
                return packaging_result
                
            except Exception as e:
                logger.error(f"Packaging agent execution failed: {e}")
                raise
        
        return executor
    
    def _create_qa_validator_executor(self):
        """Create executor for QA validator agent"""
        def executor(task_data: Dict[str, Any]) -> Dict[str, Any]:
            """Execute QA validation task"""
            try:
                # Get package information
                packaging_context = task_data.get('packaging_result', {})
                package_path = packaging_context.get('package_path')
                
                # Use QA tools
                tools = self.qa_validator_agent.get_tools()
                
                validation_result = {
                    'validation_score': 0.0,
                    'functionality_tests': [],
                    'compatibility_issues': [],
                    'quality_report': {}
                }
                
                # Execute validation tools
                for tool in tools:
                    try:
                        if hasattr(tool, 'name'):
                            if 'validate_conversion_quality' in tool.name:
                                quality = tool.run(package_path=package_path)
                                if quality:
                                    validation_result['validation_score'] = quality.get('score', 0.0)
                            elif 'run_functionality_tests' in tool.name:
                                tests = tool.run(package_path=package_path)
                                if tests:
                                    validation_result['functionality_tests'] = tests
                    except Exception as tool_error:
                        logger.warning(f"QA tool execution failed: {tool_error}")
                        continue
                
                logger.info("QA validation completed")
                return validation_result
                
            except Exception as e:
                logger.error(f"QA validator execution failed: {e}")
                raise
        
        return executor
    
    def _create_entity_converter_executor(self):
        """Create executor for specialized entity converter (dynamically spawned)"""
        def executor(task_data: Dict[str, Any]) -> Dict[str, Any]:
            """Execute specialized entity conversion task"""
            try:
                entity_data = task_data.get('entity_data', {})
                entity_index = task_data.get('entity_index', 0)
                
                # Simulate specialized entity conversion
                # In practice, this would use specialized tools or agents
                conversion_result = {
                    'entity_id': entity_data.get('id', f'entity_{entity_index}'),
                    'converted_entity': {
                        'behavior_pack': {},
                        'resource_pack': {},
                        'conversion_notes': []
                    }
                }
                
                logger.info(f"Specialized entity conversion completed for entity {entity_index}")
                return conversion_result
                
            except Exception as e:
                logger.error(f"Entity converter execution failed: {e}")
                raise
        
        return executor
    
    def convert_mod(
        self,
        mod_path: Path,
        output_path: Path,
        smart_assumptions: bool = True,
        include_dependencies: bool = True
    ) -> Dict[str, Any]:
        """
        Execute mod conversion using the appropriate orchestration strategy
        
        Args:
            mod_path: Path to Java mod file
            output_path: Path for converted output  
            smart_assumptions: Enable smart assumption processing
            include_dependencies: Include dependency analysis
            
        Returns:
            Conversion result following PRD Feature 3 format
        """
        
        try:
            # Create temporary directory
            output_base_dir = os.getenv("CONVERSION_OUTPUT_DIR", "/tmp")
            temp_dir = Path(tempfile.mkdtemp(dir=output_base_dir))
            
            logger.info(f"Starting enhanced conversion for {mod_path}")
            
            # Measure wall-clock execution time
            start_time = time.time()
            
            # Create workflow task graph
            task_graph = self.orchestrator.create_conversion_workflow(
                mod_path=str(mod_path),
                output_path=str(output_path),
                temp_dir=str(temp_dir),
                variant_id=self.variant_id,
                smart_assumptions_enabled=smart_assumptions,
                include_dependencies=include_dependencies
            )
            
            # Execute workflow
            execution_results = self.orchestrator.execute_workflow(task_graph)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Format results according to PRD format
            formatted_results = self._format_results(
                task_graph,
                execution_results,
                mod_path,
                output_path,
                execution_time
            )
            
            logger.info("Enhanced conversion completed successfully")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Enhanced conversion failed: {e}")
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
        finally:
            # Clean up temp directory
            if 'temp_dir' in locals() and temp_dir.exists():
                shutil.rmtree(temp_dir)
    
    def _format_results(
        self,
        task_graph: TaskGraph,
        execution_results: Dict[str, Any],
        mod_path: Path,
        output_path: Path,
        execution_time: float
    ) -> Dict[str, Any]:
        """Format orchestrator results to match PRD format"""
        
        stats = task_graph.get_completion_stats()
        success_rate = stats['completion_rate']
        
        # Extract smart assumptions from planning results
        smart_assumptions = []
        if 'plan' in execution_results:
            planning_result = execution_results['plan']
            if isinstance(planning_result, dict):
                assumptions = planning_result.get('smart_assumptions', [])
                for assumption in assumptions:
                    if isinstance(assumption, dict):
                        smart_assumptions.append({
                            'original_feature': assumption.get('java_feature', 'unknown'),
                            'assumption_type': assumption.get('type', 'compatibility'),
                            'bedrock_equivalent': assumption.get('bedrock_workaround', 'undefined'),
                            'impact_level': assumption.get('impact', 'medium'),
                            'user_explanation': assumption.get('description', 'No explanation available')
                        })
        
        # Create detailed report
        detailed_report = {
            'stage': 'completed' if success_rate > 0.8 else 'partial',
            'progress': int(success_rate * 100),
            'logs': [],
            'orchestration_strategy': self.orchestrator.current_strategy.value if self.orchestrator.current_strategy else 'unknown',
            'parallel_execution_stats': {
                'total_tasks': stats['total_tasks'],
                'completed_tasks': stats['completed_tasks'],
                'failed_tasks': stats['failed_tasks'],
                'average_task_duration': stats['average_task_duration'],
                'total_duration': stats['total_duration']
            }
        }
        
        # Add execution logs
        for task_id, task in task_graph.nodes.items():
            log_entry = {
                'task': task_id,
                'agent': task.agent_name,
                'status': task.status.value,
                'duration': task.duration,
                'output': str(execution_results.get(task_id, ''))[:500] + '...' if len(str(execution_results.get(task_id, ''))) > 500 else str(execution_results.get(task_id, ''))
            }
            if task.error:
                log_entry['error'] = task.error
            detailed_report['logs'].append(log_entry)
        
        # Determine overall status
        if stats['failed_tasks'] == 0 and stats['completed_tasks'] > 0:
            status = 'completed'
        elif stats['completed_tasks'] > 0:
            status = 'partial'
        else:
            status = 'failed'
        
        return {
            'status': status,
            'overall_success_rate': success_rate,
            'converted_mods': [{'name': str(mod_path), 'success_rate': success_rate}] if success_rate > 0 else [],
            'failed_mods': [{'name': str(mod_path), 'reason': 'Conversion failed', 'suggestions': []}] if success_rate == 0 else [],
            'smart_assumptions_applied': smart_assumptions,
            'download_url': str(output_path) if success_rate > 0.8 else None,
            'detailed_report': detailed_report,
            'orchestration_metadata': {
                'strategy_used': self.orchestrator.current_strategy.value if self.orchestrator.current_strategy else 'unknown',
                'execution_time': execution_time,
                'parallel_efficiency': self._calculate_parallel_efficiency(task_graph, execution_time),
                'dynamic_tasks_spawned': len([t for t in task_graph.nodes.values() if 'spawned' in t.task_id])
            }
        }
    
    def _calculate_parallel_efficiency(self, task_graph: TaskGraph, execution_time: float) -> float:
        """Calculate parallel execution efficiency"""
        stats = task_graph.get_completion_stats()
        
        # Calculate efficiency as speedup ratio
        # T_serial is the sum of all task durations
        # T_parallel is the wall-clock execution time
        if execution_time > 0 and stats['total_duration'] > 0:
            sequential_time = stats['total_duration']
            parallel_time = execution_time
            # Speedup = T_serial / T_parallel
            return sequential_time / parallel_time
        
        return 0.0
    
    def get_orchestration_status(self) -> Dict[str, Any]:
        """Get current orchestration status"""
        return self.orchestrator.get_execution_status()
    
    def get_strategy_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for all strategies"""
        return self.strategy_selector.get_performance_summary()