"""
Parallel Orchestrator for managing multi-agent conversion workflows.
Part of Phase 2: Core Orchestration Engine Implementation
"""

import asyncio
import time
import logging
import multiprocessing
import os
from typing import Dict, List, Any, Optional, Callable, Tuple
from concurrent.futures import Future, as_completed
import json
from pathlib import Path

from .task_graph import TaskGraph, TaskNode, TaskStatus
from .worker_pool import WorkerPool, WorkerType, create_agent_executor
from .strategy_selector import OrchestrationStrategy, StrategySelector, StrategyConfig

logger = logging.getLogger(__name__)


class ParallelOrchestrator:
    """
    Main orchestrator for parallel multi-agent conversion workflows.
    Manages task graphs, worker pools, and execution strategies.
    """
    
    def __init__(
        self,
        strategy_selector: Optional[StrategySelector] = None,
        enable_monitoring: bool = True
    ):
        """
        Initialize the parallel orchestrator
        
        Args:
            strategy_selector: Strategy selector for choosing execution approaches
            enable_monitoring: Enable performance monitoring and logging
        """
        self.strategy_selector = strategy_selector or StrategySelector()
        self.enable_monitoring = enable_monitoring
        
        # Core components
        self.task_graph: Optional[TaskGraph] = None
        self.worker_pool: Optional[WorkerPool] = None
        self.current_strategy: Optional[OrchestrationStrategy] = None
        self.current_config: Optional[StrategyConfig] = None
        
        # Agent executors mapping
        self.agent_executors: Dict[str, Callable] = {}
        
        # Execution state
        self.execution_start_time: Optional[float] = None
        self.execution_end_time: Optional[float] = None
        self.execution_results: Dict[str, Any] = {}
        
        logger.info("ParallelOrchestrator initialized")
    
    def register_agent(self, agent_name: str, agent_instance: Any, tools_mapping: Optional[Dict] = None):
        """
        Register an agent for execution
        
        Args:
            agent_name: Unique identifier for the agent
            agent_instance: The agent instance to execute
            tools_mapping: Optional tools mapping for the agent
        """
        executor = create_agent_executor(agent_instance, tools_mapping)
        self.agent_executors[agent_name] = executor
        logger.debug(f"Registered agent: {agent_name}")
    
    def create_conversion_workflow(
        self,
        mod_path: str,
        output_path: str,
        temp_dir: str,
        variant_id: Optional[str] = None,
        smart_assumptions_enabled: bool = True,
        include_dependencies: bool = True
    ) -> TaskGraph:
        """
        Create the conversion workflow task graph
        
        Args:
            mod_path: Path to the Java mod file
            output_path: Output path for conversion
            temp_dir: Temporary directory for intermediate files
            variant_id: A/B testing variant identifier
            smart_assumptions_enabled: Enable smart assumption processing
            include_dependencies: Include dependency analysis
            
        Returns:
            TaskGraph representing the conversion workflow
        """
        
        # Select execution strategy
        task_complexity = self._analyze_mod_complexity(mod_path)
        system_resources = self._get_system_resources()
        
        strategy, config = self.strategy_selector.select_strategy(
            variant_id=variant_id,
            task_complexity=task_complexity,
            system_resources=system_resources
        )
        
        self.current_strategy = strategy
        self.current_config = config
        
        logger.info(f"Creating workflow with strategy: {strategy.value}")
        
        # Create task graph
        task_graph = TaskGraph()
        
        # Common input data for all tasks
        base_input = {
            'mod_path': mod_path,
            'output_path': output_path,
            'temp_dir': temp_dir,
            'smart_assumptions_enabled': smart_assumptions_enabled,
            'include_dependencies': include_dependencies,
            'strategy': strategy.value,
            'variant_id': variant_id
        }
        
        # Create tasks based on strategy
        if strategy == OrchestrationStrategy.SEQUENTIAL:
            return self._create_sequential_workflow(task_graph, base_input)
        elif strategy == OrchestrationStrategy.PARALLEL_BASIC:
            return self._create_parallel_basic_workflow(task_graph, base_input)
        elif strategy == OrchestrationStrategy.PARALLEL_ADAPTIVE:
            return self._create_adaptive_workflow(task_graph, base_input)
        elif strategy == OrchestrationStrategy.HYBRID:
            return self._create_hybrid_workflow(task_graph, base_input)
        else:
            raise ValueError(f"Unsupported strategy: {strategy}")
    
    def _create_sequential_workflow(self, task_graph: TaskGraph, base_input: Dict[str, Any]) -> TaskGraph:
        """Create sequential workflow (original CrewAI behavior)"""
        
        # Create tasks in sequential order
        analyze_task = TaskNode(
            task_id="analyze",
            agent_name="java_analyzer",
            agent_type="analyzer",
            input_data=base_input.copy(),
            priority=5
        )
        task_graph.add_task(analyze_task)
        
        plan_task = TaskNode(
            task_id="plan",
            agent_name="bedrock_architect",
            agent_type="planner",
            input_data=base_input.copy(),
            priority=4
        )
        task_graph.add_task(plan_task)
        task_graph.add_dependency("plan", "analyze")
        
        translate_task = TaskNode(
            task_id="translate",
            agent_name="logic_translator",
            agent_type="translator",
            input_data=base_input.copy(),
            priority=3
        )
        task_graph.add_task(translate_task)
        task_graph.add_dependency("translate", "plan")
        
        convert_assets_task = TaskNode(
            task_id="convert_assets",
            agent_name="asset_converter",
            agent_type="converter",
            input_data=base_input.copy(),
            priority=3
        )
        task_graph.add_task(convert_assets_task)
        task_graph.add_dependency("convert_assets", "plan")
        
        package_task = TaskNode(
            task_id="package",
            agent_name="packaging_agent",
            agent_type="packager",
            input_data=base_input.copy(),
            priority=2
        )
        task_graph.add_task(package_task)
        task_graph.add_dependency("package", "translate")
        task_graph.add_dependency("package", "convert_assets")
        
        validate_task = TaskNode(
            task_id="validate",
            agent_name="qa_validator",
            agent_type="validator",
            input_data=base_input.copy(),
            priority=1
        )
        task_graph.add_task(validate_task)
        task_graph.add_dependency("validate", "package")
        
        return task_graph
    
    def _create_parallel_basic_workflow(self, task_graph: TaskGraph, base_input: Dict[str, Any]) -> TaskGraph:
        """Create basic parallel workflow"""
        
        # Analysis task first (required by all others)
        analyze_task = TaskNode(
            task_id="analyze",
            agent_name="java_analyzer", 
            agent_type="analyzer",
            input_data=base_input.copy(),
            priority=5
        )
        task_graph.add_task(analyze_task)
        
        # Planning task depends on analysis
        plan_task = TaskNode(
            task_id="plan",
            agent_name="bedrock_architect",
            agent_type="planner",
            input_data=base_input.copy(),
            priority=4
        )
        task_graph.add_task(plan_task)
        task_graph.add_dependency("plan", "analyze")
        
        # Translation and asset conversion can run in parallel after planning
        translate_task = TaskNode(
            task_id="translate",
            agent_name="logic_translator",
            agent_type="translator",
            input_data=base_input.copy(),
            priority=3
        )
        task_graph.add_task(translate_task)
        task_graph.add_dependency("translate", "plan")
        
        convert_assets_task = TaskNode(
            task_id="convert_assets",
            agent_name="asset_converter",
            agent_type="converter",
            input_data=base_input.copy(),
            priority=3
        )
        task_graph.add_task(convert_assets_task)
        task_graph.add_dependency("convert_assets", "plan")
        
        # Packaging waits for both translation and asset conversion
        package_task = TaskNode(
            task_id="package",
            agent_name="packaging_agent",
            agent_type="packager",
            input_data=base_input.copy(),
            priority=2
        )
        task_graph.add_task(package_task)
        task_graph.add_dependency("package", "translate")
        task_graph.add_dependency("package", "convert_assets")
        
        # Validation runs after packaging
        validate_task = TaskNode(
            task_id="validate",
            agent_name="qa_validator",
            agent_type="validator",
            input_data=base_input.copy(),
            priority=1
        )
        task_graph.add_task(validate_task)
        task_graph.add_dependency("validate", "package")
        
        return task_graph
    
    def _create_adaptive_workflow(self, task_graph: TaskGraph, base_input: Dict[str, Any]) -> TaskGraph:
        """Create adaptive workflow with dynamic spawning"""
        
        # Start with basic parallel structure
        task_graph = self._create_parallel_basic_workflow(task_graph, base_input)
        
        # Add dynamic spawning callbacks
        analyze_task = task_graph.nodes["analyze"]
        analyze_task.spawn_callback = self._create_analysis_spawn_callback(base_input)
        
        plan_task = task_graph.nodes["plan"]
        plan_task.spawn_callback = self._create_planning_spawn_callback(base_input)
        
        return task_graph
    
    def _create_hybrid_workflow(self, task_graph: TaskGraph, base_input: Dict[str, Any]) -> TaskGraph:
        """Create hybrid workflow mixing sequential and parallel approaches"""
        
        # Analyze dependencies and complexity to decide on parallelization
        # For now, use parallel basic as the hybrid approach
        # In future iterations, this could be more sophisticated
        return self._create_parallel_basic_workflow(task_graph, base_input)
    
    def _create_analysis_spawn_callback(self, base_input: Dict[str, Any]) -> Callable:
        """Create callback for dynamic task spawning after analysis"""
        
        def spawn_callback(analysis_result: Any) -> List[TaskNode]:
            """Spawn additional tasks based on analysis results"""
            spawned_tasks = []
            
            try:
                # Parse analysis result to determine what to spawn
                if isinstance(analysis_result, str):
                    result_data = json.loads(analysis_result)
                elif isinstance(analysis_result, dict):
                    result_data = analysis_result
                else:
                    logger.warning(f"Unexpected analysis result type: {type(analysis_result)}")
                    return spawned_tasks
                
                # Example: Spawn specialized entity converters for each entity type
                entities = result_data.get('features', {}).get('entities', [])
                for i, entity in enumerate(entities):
                    if isinstance(entity, dict) and entity.get('complex', False):
                        entity_task = TaskNode(
                            task_id=f"convert_entity_{i}",
                            agent_name="entity_converter",
                            agent_type="entity_converter",
                            input_data={
                                **base_input,
                                'entity_data': entity,
                                'entity_index': i
                            },
                            priority=3
                        )
                        spawned_tasks.append(entity_task)
                
                logger.info(f"Spawned {len(spawned_tasks)} entity conversion tasks")
                
            except Exception as e:
                logger.error(f"Error in analysis spawn callback: {e}")
            
            return spawned_tasks
        
        return spawn_callback
    
    def _create_planning_spawn_callback(self, base_input: Dict[str, Any]) -> Callable:
        """Create callback for dynamic task spawning after planning"""
        
        def spawn_callback(planning_result: Any) -> List[TaskNode]:
            """Spawn additional tasks based on planning results"""
            spawned_tasks = []
            
            try:
                # Example: Spawn specialized tasks for complex conversions
                if hasattr(planning_result, 'complex_features'):
                    for feature in planning_result.complex_features:
                        if feature.requires_specialized_processing:
                            specialized_task = TaskNode(
                                task_id=f"specialized_{feature.id}",
                                agent_name="specialized_converter",
                                agent_type="specialized_converter", 
                                input_data={
                                    **base_input,
                                    'feature_data': feature,
                                },
                                priority=3
                            )
                            spawned_tasks.append(specialized_task)
                
                logger.info(f"Spawned {len(spawned_tasks)} specialized conversion tasks")
                
            except Exception as e:
                logger.error(f"Error in planning spawn callback: {e}")
            
            return spawned_tasks
        
        return spawn_callback
    
    def execute_workflow(self, task_graph: TaskGraph) -> Dict[str, Any]:
        """
        Execute the conversion workflow
        
        Args:
            task_graph: TaskGraph to execute
            
        Returns:
            Execution results dictionary
        """
        self.task_graph = task_graph
        self.execution_start_time = time.time()
        
        logger.info(f"Starting workflow execution with {len(task_graph.nodes)} tasks")
        
        # Initialize worker pool based on strategy
        worker_type = WorkerType.PROCESS if self.current_config.use_process_pool else WorkerType.THREAD
        
        with WorkerPool(
            max_workers=self.current_config.max_parallel_tasks,
            worker_type=worker_type,
            task_timeout=self.current_config.task_timeout,
            enable_monitoring=self.enable_monitoring
        ) as worker_pool:
            
            self.worker_pool = worker_pool
            
            try:
                # Execute workflow based on strategy
                if self.current_strategy == OrchestrationStrategy.SEQUENTIAL:
                    results = self._execute_sequential(task_graph, worker_pool)
                else:
                    results = self._execute_parallel(task_graph, worker_pool)
                
                self.execution_end_time = time.time()
                self.execution_results = results
                
                # Record performance metrics
                self._record_performance_metrics(task_graph, results)
                
                return results
                
            except Exception as e:
                logger.error(f"Workflow execution failed: {e}")
                self.execution_end_time = time.time()
                raise
            finally:
                self.worker_pool = None
    
    def _execute_sequential(self, task_graph: TaskGraph, worker_pool: WorkerPool) -> Dict[str, Any]:
        """Execute tasks sequentially (mimics original CrewAI behavior)"""
        
        task_order = ["analyze", "plan", "translate", "convert_assets", "package", "validate"]
        results = {}
        
        for task_id in task_order:
            if task_id not in task_graph.nodes:
                logger.warning(f"Task {task_id} not found in graph")
                continue
            
            task = task_graph.nodes[task_id]
            
            if task.agent_name not in self.agent_executors:
                error_msg = f"No executor found for agent {task.agent_name}"
                logger.error(error_msg)
                task_graph.mark_task_failed(task_id, error_msg)
                continue
            
            try:
                logger.info(f"Executing task {task_id} sequentially")
                
                # Submit task and wait for completion
                future = worker_pool.submit_task(task, self.agent_executors[task.agent_name])
                result = future.result(timeout=self.current_config.task_timeout)
                
                # Mark as completed and handle spawning
                spawned_tasks = task_graph.mark_task_completed(task_id, result)
                
                # In sequential mode, execute spawned tasks immediately
                for spawned_task in spawned_tasks:
                    if spawned_task.agent_name in self.agent_executors:
                        try:
                            spawned_future = worker_pool.submit_task(
                                spawned_task, 
                                self.agent_executors[spawned_task.agent_name]
                            )
                            spawned_result = spawned_future.result(timeout=self.current_config.task_timeout)
                            task_graph.mark_task_completed(spawned_task.task_id, spawned_result)
                        except Exception as e:
                            logger.error(f"Spawned task {spawned_task.task_id} failed: {e}")
                            task_graph.mark_task_failed(spawned_task.task_id, str(e))
                
                results[task_id] = result
                
            except Exception as e:
                logger.error(f"Task {task_id} failed: {e}")
                if self.current_config.retry_failed_tasks and task_graph.retry_task(task_id):
                    logger.info(f"Retrying task {task_id}")
                    # Retry logic would go here
                else:
                    task_graph.mark_task_failed(task_id, str(e))
                    break  # Stop sequential execution on failure
        
        return results
    
    def _execute_parallel(self, task_graph: TaskGraph, worker_pool: WorkerPool) -> Dict[str, Any]:
        """Execute tasks in parallel"""
        
        results = {}
        active_futures: Dict[str, Future] = {}
        
        while not task_graph.is_complete() and not task_graph.has_permanently_failed_tasks():
            
            # Get ready tasks
            ready_tasks = task_graph.get_ready_tasks()
            
            # Submit ready tasks that aren't already running
            for task in ready_tasks:
                if task.task_id not in active_futures and task.agent_name in self.agent_executors:
                    logger.info(f"Submitting task {task.task_id} for parallel execution")
                    future = worker_pool.submit_task(task, self.agent_executors[task.agent_name])
                    active_futures[task.task_id] = future
            
            if not active_futures:
                logger.warning("No active tasks and no ready tasks - workflow may be stuck")
                break
            
            # Wait for at least one task to complete using as_completed with timeout
            completed_futures = []
            try:
                # Use as_completed with timeout to avoid busy waiting
                for future in as_completed(active_futures.values(), timeout=0.1):
                    task_id = None
                    for t_id, fut in active_futures.items():
                        if fut == future:
                            task_id = t_id
                            break
                    
                    if task_id is not None:
                        completed_futures.append((task_id, future))
                        # Break after first completion to allow submitting new ready tasks
                        break
            except TimeoutError:
                # No tasks completed in timeout period, continue to check for new ready tasks
                continue
            
            if not completed_futures:
                continue
                
            # Process completed tasks
            for task_id, future in completed_futures:
                del active_futures[task_id]
                
                try:
                    result = future.result()
                    results[task_id] = result
                    
                    # Mark task completed and handle dynamic spawning
                    spawned_tasks = task_graph.mark_task_completed(task_id, result)
                    
                    # Submit spawned tasks if dynamic spawning is enabled
                    if self.current_config.enable_dynamic_spawning:
                        for spawned_task in spawned_tasks:
                            if spawned_task.agent_name in self.agent_executors:
                                logger.info(f"Submitting dynamically spawned task {spawned_task.task_id}")
                                spawned_future = worker_pool.submit_task(
                                    spawned_task,
                                    self.agent_executors[spawned_task.agent_name]
                                )
                                active_futures[spawned_task.task_id] = spawned_future
                    
                except Exception as e:
                    logger.error(f"Task {task_id} failed: {e}")
                    if self.current_config.retry_failed_tasks and task_graph.retry_task(task_id):
                        logger.info(f"Retrying task {task_id}")
                        # Task will be picked up in next iteration
                    else:
                        task_graph.mark_task_failed(task_id, str(e))
        
        # Wait for any remaining active tasks
        for task_id, future in active_futures.items():
            try:
                result = future.result(timeout=10.0)  # Give remaining tasks time to finish
                results[task_id] = result
                task_graph.mark_task_completed(task_id, result)
            except Exception as e:
                logger.error(f"Final task {task_id} failed: {e}")
                task_graph.mark_task_failed(task_id, str(e))
        
        return results
    
    def _analyze_mod_complexity(self, mod_path: str) -> Dict[str, Any]:
        """Analyze mod complexity for strategy selection"""
        # This is a simplified analysis - in practice, you'd examine the mod file
        
        mod_file = Path(mod_path)
        
        # Basic complexity metrics
        complexity = {
            'file_size_mb': mod_file.stat().st_size / (1024 * 1024) if mod_file.exists() else 0,
            'num_features': 5,  # Default estimate
            'num_dependencies': 2,  # Default estimate
            'has_complex_assets': False,
            'estimated_entities': 3
        }
        
        # Estimate based on file size
        if complexity['file_size_mb'] > 10:
            complexity['num_features'] = 15
            complexity['estimated_entities'] = 8
            complexity['has_complex_assets'] = True
        elif complexity['file_size_mb'] > 5:
            complexity['num_features'] = 10
            complexity['estimated_entities'] = 5
        
        return complexity
    
    def _get_system_resources(self) -> Dict[str, Any]:
        """Get current system resource information"""
        return {
            'cpu_count': multiprocessing.cpu_count(),
            'memory_gb': 8,  # Default estimate - could use psutil if available
            'is_containerized': os.path.exists('/.dockerenv')
        }
    
    def _record_performance_metrics(self, task_graph: TaskGraph, results: Dict[str, Any]):
        """Record performance metrics for strategy optimization"""
        
        if not self.execution_start_time or not self.execution_end_time:
            return
        
        stats = task_graph.get_completion_stats()
        total_duration = self.execution_end_time - self.execution_start_time
        success_rate = stats['completion_rate']
        
        # Record in strategy selector
        self.strategy_selector.record_performance(
            strategy=self.current_strategy,
            success_rate=success_rate,
            total_duration=total_duration,
            task_count=stats['total_tasks'],
            additional_metrics={
                'failed_tasks': stats['failed_tasks'],
                'average_task_duration': stats['average_task_duration'],
                'parallel_efficiency': stats['total_duration'] / total_duration if total_duration > 0 else 0
            }
        )
        
        logger.info(f"Recorded performance: strategy={self.current_strategy.value}, "
                   f"success_rate={success_rate:.2%}, duration={total_duration:.2f}s")
    
    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status"""
        
        status = {
            'strategy': self.current_strategy.value if self.current_strategy else None,
            'is_running': self.execution_start_time is not None and self.execution_end_time is None,
            'start_time': self.execution_start_time,
            'end_time': self.execution_end_time,
            'duration': (
                (self.execution_end_time or time.time()) - self.execution_start_time
                if self.execution_start_time else None
            )
        }
        
        if self.task_graph:
            status.update(self.task_graph.get_completion_stats())
        
        if self.worker_pool:
            status['worker_stats'] = self.worker_pool.get_worker_stats()
        
        return status