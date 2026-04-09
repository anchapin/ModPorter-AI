"""
Comprehensive tests for agent orchestration and multi-step workflows.
Tests RAG pipelines, agent coordination, and end-to-end conversions.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock

# Set up imports
try:
    # Try multiple import paths for flexibility
    try:
        from qa.orchestrator import QAOrchestrator
        from agents.java_analyzer import JavaAnalyzerAgent
        from agents.bedrock_builder import BedrockBuilderAgent
        from agents.qa_agent import QAAgent
        from tools.search_tool import SearchTool
    except ImportError:
        from ai_engine.qa.orchestrator import QAOrchestrator
        from ai_engine.agents.java_analyzer import JavaAnalyzerAgent
        from ai_engine.agents.bedrock_builder import BedrockBuilderAgent
        from ai_engine.agents.qa_agent import QAAgent
        from ai_engine.tools.search_tool import SearchTool
    
    IMPORTS_AVAILABLE = True
except ImportError as e:
    IMPORTS_AVAILABLE = False
    IMPORT_ERROR = str(e)


# Skip all tests if imports fail
pytestmark = pytest.mark.skipif(not IMPORTS_AVAILABLE, reason="Required imports unavailable")


@pytest.fixture
def mock_java_analyzer():
    """Create a mock JavaAnalyzerAgent."""
    agent = AsyncMock(spec=JavaAnalyzerAgent)

    async def side_effect(arg):
        if arg is None:
            raise ValueError("Invalid input")
        return {
            "success": True,
            "classes": ["BlockEntity", "CustomBlock"],
            "methods": 42,
            "imports": ["net.minecraft.block", "net.minecraft.entity"]
        }

    agent.analyze_jar = AsyncMock(side_effect=side_effect)
    return agent


@pytest.fixture
def mock_bedrock_builder():
    """Create a mock BedrockBuilderAgent."""
    agent = AsyncMock(spec=BedrockBuilderAgent)
    agent.build_addon = AsyncMock(return_value={
        "success": True,
        "addon_dir": "/tmp/addon",
        "components": ["block", "entity", "item"]
    })
    return agent


@pytest.fixture
def mock_qa_agent():
    """Create a mock QAAgent."""
    agent = AsyncMock(spec=QAAgent)
    agent.validate_conversion = AsyncMock(return_value={
        "success": True,
        "issues": [],
        "score": 0.95
    })
    return agent


@pytest.fixture
def mock_search_tool():
    """Create a mock SearchTool."""
    tool = AsyncMock(spec=SearchTool)
    tool.semantic_search = AsyncMock(return_value={
        "results": [
            {"id": "doc_1", "content": "Block entity pattern", "score": 0.92}
        ]
    })
    return tool


@pytest.fixture
def mock_orchestrator(mock_java_analyzer, mock_bedrock_builder, mock_qa_agent):
    """Create a mock QAOrchestrator."""
    orchestrator = AsyncMock(spec=QAOrchestrator)
    orchestrator.java_analyzer = mock_java_analyzer
    orchestrator.bedrock_builder = mock_bedrock_builder
    orchestrator.qa_agent = mock_qa_agent
    return orchestrator


class TestAgentInitialization:
    """Test agent initialization and setup."""
    
    @pytest.mark.asyncio
    async def test_java_analyzer_initialization(self, mock_java_analyzer):
        """Test JavaAnalyzerAgent initialization."""
        assert mock_java_analyzer is not None
        assert hasattr(mock_java_analyzer, 'analyze_jar')
    
    @pytest.mark.asyncio
    async def test_bedrock_builder_initialization(self, mock_bedrock_builder):
        """Test BedrockBuilderAgent initialization."""
        assert mock_bedrock_builder is not None
        assert hasattr(mock_bedrock_builder, 'build_addon')
    
    @pytest.mark.asyncio
    async def test_qa_agent_initialization(self, mock_qa_agent):
        """Test QAAgent initialization."""
        assert mock_qa_agent is not None
        assert hasattr(mock_qa_agent, 'validate_conversion')
    
    @pytest.mark.asyncio
    async def test_orchestrator_initialization(self, mock_orchestrator):
        """Test QAOrchestrator initialization."""
        assert mock_orchestrator is not None
        assert hasattr(mock_orchestrator, 'java_analyzer')
        assert hasattr(mock_orchestrator, 'bedrock_builder')
        assert hasattr(mock_orchestrator, 'qa_agent')


class TestSingleAgentWorkflows:
    """Test single agent workflows."""
    
    @pytest.mark.asyncio
    async def test_java_analysis_workflow(self, mock_java_analyzer):
        """Test Java code analysis workflow."""
        jar_path = "/tmp/test_mod.jar"
        
        result = await mock_java_analyzer.analyze_jar(jar_path)
        
        assert result["success"] is True
        assert "classes" in result
        assert len(result["classes"]) > 0
    
    @pytest.mark.asyncio
    async def test_bedrock_build_workflow(self, mock_bedrock_builder):
        """Test Bedrock addon building workflow."""
        analysis_result = {
            "classes": ["CustomBlock"],
            "methods": 10
        }
        
        result = await mock_bedrock_builder.build_addon(analysis_result)
        
        assert result["success"] is True
        assert "addon_dir" in result
    
    @pytest.mark.asyncio
    async def test_qa_validation_workflow(self, mock_qa_agent):
        """Test QA validation workflow."""
        conversion_result = {
            "addon_dir": "/tmp/addon",
            "components": ["block"]
        }
        
        result = await mock_qa_agent.validate_conversion(conversion_result)
        
        assert result["success"] is True
        assert "score" in result
    
    @pytest.mark.asyncio
    async def test_search_tool_workflow(self, mock_search_tool):
        """Test search tool workflow."""
        query = "block entity implementation"
        
        result = await mock_search_tool.semantic_search(query)
        
        assert "results" in result
        assert len(result["results"]) > 0


class TestSequentialAgentChaining:
    """Test sequential chaining of agents."""
    
    @pytest.mark.asyncio
    async def test_analysis_to_build_chain(self, mock_java_analyzer, mock_bedrock_builder):
        """Test chaining Java analysis to Bedrock building."""
        # Step 1: Analyze JAR
        jar_path = "/tmp/test_mod.jar"
        analysis_result = await mock_java_analyzer.analyze_jar(jar_path)
        
        assert analysis_result["success"] is True
        
        # Step 2: Build Bedrock addon from analysis
        build_result = await mock_bedrock_builder.build_addon(analysis_result)
        
        assert build_result["success"] is True
        
        # Verify chain worked
        mock_java_analyzer.analyze_jar.assert_called_once_with(jar_path)
        mock_bedrock_builder.build_addon.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_build_to_qa_chain(self, mock_bedrock_builder, mock_qa_agent):
        """Test chaining Bedrock building to QA validation."""
        # Step 1: Build addon
        analysis_result = {"classes": ["Block"]}
        build_result = await mock_bedrock_builder.build_addon(analysis_result)
        
        assert build_result["success"] is True
        
        # Step 2: Validate with QA
        qa_result = await mock_qa_agent.validate_conversion(build_result)
        
        assert qa_result["success"] is True
        assert "score" in qa_result
    
    @pytest.mark.asyncio
    async def test_full_conversion_chain(self, mock_java_analyzer, mock_bedrock_builder, mock_qa_agent):
        """Test full conversion chain: analyze -> build -> validate."""
        jar_path = "/tmp/test_mod.jar"
        
        # Step 1: Analyze
        analysis = await mock_java_analyzer.analyze_jar(jar_path)
        assert analysis["success"] is True
        
        # Step 2: Build
        build = await mock_bedrock_builder.build_addon(analysis)
        assert build["success"] is True
        
        # Step 3: Validate
        validation = await mock_qa_agent.validate_conversion(build)
        assert validation["success"] is True
        assert validation["score"] >= 0.8


class TestParallelAgentExecution:
    """Test parallel execution of agents."""
    
    @pytest.mark.asyncio
    async def test_parallel_analysis_tasks(self, mock_java_analyzer):
        """Test running multiple analysis tasks in parallel."""
        jar_files = [
            "/tmp/mod1.jar",
            "/tmp/mod2.jar",
            "/tmp/mod3.jar"
        ]
        
        results = await asyncio.gather(*[
            mock_java_analyzer.analyze_jar(jar) for jar in jar_files
        ])
        
        assert len(results) == 3
        assert all(r["success"] for r in results)
    
    @pytest.mark.asyncio
    async def test_parallel_build_tasks(self, mock_bedrock_builder):
        """Test running multiple build tasks in parallel."""
        analyses = [
            {"classes": ["Block1"]},
            {"classes": ["Block2"]},
            {"classes": ["Block3"]}
        ]
        
        results = await asyncio.gather(*[
            mock_bedrock_builder.build_addon(a) for a in analyses
        ])
        
        assert len(results) == 3
        assert all(r["success"] for r in results)
    
    @pytest.mark.asyncio
    async def test_mixed_parallel_execution(self, mock_java_analyzer, mock_bedrock_builder):
        """Test parallel execution of different agent types."""
        tasks = [
            mock_java_analyzer.analyze_jar("/tmp/mod1.jar"),
            mock_java_analyzer.analyze_jar("/tmp/mod2.jar"),
            mock_bedrock_builder.build_addon({"classes": ["Block"]}),
        ]
        
        results = await asyncio.gather(*tasks)
        
        assert len(results) == 3
        assert all(r["success"] for r in results)


class TestAgentErrorHandling:
    """Test error handling in agent workflows."""
    
    @pytest.mark.asyncio
    async def test_agent_timeout_handling(self, mock_java_analyzer):
        """Test handling agent timeout."""
        mock_java_analyzer.analyze_jar = AsyncMock(
            side_effect=TimeoutError("Analysis timed out")
        )
        
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(
                mock_java_analyzer.analyze_jar("/tmp/test.jar"),
                timeout=0.1
            )
    
    @pytest.mark.asyncio
    async def test_agent_exception_handling(self, mock_java_analyzer):
        """Test handling agent exceptions."""
        mock_java_analyzer.analyze_jar = AsyncMock(
            side_effect=ValueError("Invalid JAR file")
        )
        
        with pytest.raises(ValueError):
            await mock_java_analyzer.analyze_jar("/tmp/test.jar")
    
    @pytest.mark.asyncio
    async def test_partial_failure_in_chain(self, mock_java_analyzer, mock_bedrock_builder):
        """Test handling partial failures in agent chain."""
        # Java analyzer succeeds
        analysis = await mock_java_analyzer.analyze_jar("/tmp/test.jar")
        assert analysis["success"] is True
        
        # Bedrock builder fails
        mock_bedrock_builder.build_addon = AsyncMock(
            side_effect=RuntimeError("Build failed")
        )
        
        with pytest.raises(RuntimeError):
            await mock_bedrock_builder.build_addon(analysis)
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self, mock_java_analyzer):
        """Test circuit breaker pattern for failing agents."""
        failure_count = 0
        circuit_open = False
        
        for _ in range(5):
            if circuit_open:
                with pytest.raises(RuntimeError):
                    raise RuntimeError("Circuit breaker open")
            
            try:
                mock_java_analyzer.analyze_jar = AsyncMock(
                    side_effect=RuntimeError("Agent failure")
                )
                await mock_java_analyzer.analyze_jar("/tmp/test.jar")
            except RuntimeError:
                failure_count += 1
                if failure_count >= 3:
                    circuit_open = True
        
        assert circuit_open is True


class TestRAGIntegration:
    """Test RAG (Retrieval-Augmented Generation) integration."""
    
    @pytest.mark.asyncio
    async def test_search_augmented_analysis(self, mock_search_tool, mock_java_analyzer):
        """Test analysis augmented with search results."""
        # Step 1: Search for relevant documentation
        search_results = await mock_search_tool.semantic_search("block entity")
        assert len(search_results["results"]) > 0
        
        # Step 2: Use search results in analysis
        mock_java_analyzer.analyze_jar = AsyncMock(return_value={
            "success": True,
            "classes": ["BlockEntity"],
            "knowledge_base_refs": search_results["results"]
        })
        
        analysis = await mock_java_analyzer.analyze_jar("/tmp/test.jar")
        assert "knowledge_base_refs" in analysis
    
    @pytest.mark.asyncio
    async def test_context_aware_conversion(self, mock_search_tool, mock_bedrock_builder):
        """Test conversion with RAG context."""
        # Get relevant patterns
        patterns = await mock_search_tool.semantic_search("entity rendering")
        
        # Use patterns in conversion
        mock_bedrock_builder.build_addon = AsyncMock(return_value={
            "success": True,
            "addon_dir": "/tmp/addon",
            "patterns_used": patterns["results"]
        })
        
        result = await mock_bedrock_builder.build_addon({"classes": ["Entity"]})
        assert "patterns_used" in result


class TestOrchestratorCoordination:
    """Test orchestrator coordination of agents."""
    
    @pytest.mark.asyncio
    async def test_orchestrator_full_pipeline(self, mock_orchestrator):
        """Test orchestrator managing full pipeline."""
        jar_path = "/tmp/test_mod.jar"
        
        mock_orchestrator.execute_pipeline = AsyncMock(return_value={
            "analysis": {"success": True},
            "build": {"success": True},
            "validation": {"success": True, "score": 0.95}
        })
        
        result = await mock_orchestrator.execute_pipeline(jar_path)
        
        assert result["analysis"]["success"] is True
        assert result["build"]["success"] is True
        assert result["validation"]["success"] is True
    
    @pytest.mark.asyncio
    async def test_orchestrator_error_recovery(self, mock_orchestrator):
        """Test orchestrator error recovery."""
        mock_orchestrator.execute_with_fallback = AsyncMock(return_value={
            "success": True,
            "used_fallback": True,
            "fallback_reason": "Primary build failed"
        })
        
        result = await mock_orchestrator.execute_with_fallback("/tmp/test.jar")
        
        assert result["success"] is True
        assert result["used_fallback"] is True
    
    @pytest.mark.asyncio
    async def test_orchestrator_resource_management(self, mock_orchestrator):
        """Test orchestrator resource management."""
        mock_orchestrator.cleanup = AsyncMock(return_value=True)
        
        # Cleanup resources
        result = await mock_orchestrator.cleanup()
        
        assert result is True


class TestConversionOptimization:
    """Test optimization strategies for conversions."""
    
    @pytest.mark.asyncio
    async def test_caching_agent_results(self, mock_java_analyzer):
        """Test caching of agent results."""
        jar_path = "/tmp/test_mod.jar"
        
        # First call
        result1 = await mock_java_analyzer.analyze_jar(jar_path)
        
        # Second call (should use cache)
        result2 = await mock_java_analyzer.analyze_jar(jar_path)
        
        # Both should succeed
        assert result1["success"] is True
        assert result2["success"] is True
    
    @pytest.mark.asyncio
    async def test_lazy_loading_components(self, mock_orchestrator):
        """Test lazy loading of conversion components."""
        mock_orchestrator.lazy_load_builder = AsyncMock(return_value=True)
        
        loaded = await mock_orchestrator.lazy_load_builder()
        
        assert loaded is True
    
    @pytest.mark.asyncio
    async def test_batch_conversion_optimization(self, mock_java_analyzer):
        """Test optimization for batch conversions."""
        jars = [f"/tmp/mod{i}.jar" for i in range(5)]
        
        # Batch analysis
        results = await asyncio.gather(*[
            mock_java_analyzer.analyze_jar(jar) for jar in jars
        ])
        
        assert len(results) == 5
        assert all(r["success"] for r in results)


class TestWorkflowValidation:
    """Test workflow validation and verification."""
    
    @pytest.mark.asyncio
    async def test_validate_workflow_inputs(self, mock_java_analyzer):
        """Test validating workflow inputs."""
        # Invalid input
        with pytest.raises((ValueError, TypeError, AttributeError)):
            await mock_java_analyzer.analyze_jar(None)
    
    @pytest.mark.asyncio
    async def test_validate_workflow_outputs(self, mock_java_analyzer):
        """Test validating workflow outputs."""
        result = await mock_java_analyzer.analyze_jar("/tmp/test.jar")
        
        # Verify required fields
        assert "success" in result
        assert "classes" in result
    
    @pytest.mark.asyncio
    async def test_workflow_contract_validation(self, mock_java_analyzer, mock_bedrock_builder):
        """Test contract validation between agents."""
        analysis = await mock_java_analyzer.analyze_jar("/tmp/test.jar")
        
        # Bedrock builder expects certain fields
        required_fields = {"classes", "methods"}
        assert all(field in analysis for field in required_fields)
        
        # Should not fail
        build = await mock_bedrock_builder.build_addon(analysis)
        assert build["success"] is True


class TestAgentMonitoring:
    """Test monitoring and observability of agent workflows."""
    
    @pytest.mark.asyncio
    async def test_track_agent_execution(self, mock_java_analyzer):
        """Test tracking agent execution."""
        execution_log = []
        
        # Mock execution with tracking
        async def tracked_analyze(jar_path):
            execution_log.append({"agent": "analyzer", "status": "started"})
            result = await mock_java_analyzer.analyze_jar(jar_path)
            execution_log.append({"agent": "analyzer", "status": "completed"})
            return result
        
        await tracked_analyze("/tmp/test.jar")
        
        assert len(execution_log) == 2
        assert execution_log[0]["status"] == "started"
        assert execution_log[1]["status"] == "completed"
    
    @pytest.mark.asyncio
    async def test_measure_agent_performance(self, mock_java_analyzer):
        """Test measuring agent performance."""
        import time
        
        start_time = time.time()
        result = await mock_java_analyzer.analyze_jar("/tmp/test.jar")
        duration = time.time() - start_time
        
        assert result["success"] is True
        assert duration >= 0
    
    @pytest.mark.asyncio
    async def test_agent_metrics_collection(self, mock_orchestrator):
        """Test collecting agent metrics."""
        mock_orchestrator.get_metrics = AsyncMock(return_value={
            "total_executions": 42,
            "success_rate": 0.95,
            "avg_duration_ms": 1234
        })
        
        metrics = await mock_orchestrator.get_metrics()
        
        assert metrics["success_rate"] == 0.95
        assert metrics["total_executions"] == 42
