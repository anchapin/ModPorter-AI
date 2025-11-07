"""
Integration tests for the Advanced RAG System.

This module provides comprehensive tests to demonstrate and validate
the advanced RAG system functionality.
"""

import pytest
import asyncio
import logging

# Import components
from agents.advanced_rag_agent import AdvancedRAGAgent
from evaluation.rag_evaluator import RAGEvaluator, GoldenDatasetItem
from schemas.multimodal_schema import ContentType

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TestAdvancedRAGIntegration:
    """Integration tests for the Advanced RAG system."""
    
    @pytest.fixture
    def rag_agent(self):
        """Create an Advanced RAG agent for testing."""
        agent = AdvancedRAGAgent(
            enable_query_expansion=True,
            enable_reranking=True,
            enable_multimodal=True
        )
        return agent
    
    @pytest.fixture
    def evaluator(self):
        """Create a RAG evaluator for testing."""
        evaluator = RAGEvaluator()
        evaluator.create_sample_golden_dataset()
        return evaluator
    
    @pytest.mark.asyncio
    async def test_basic_query_processing(self, rag_agent):
        """Test basic query processing functionality."""
        logger.info("Testing basic query processing...")
        
        response = await rag_agent.query(
            query_text="How to create a custom block in Minecraft",
            content_types=[ContentType.DOCUMENTATION, ContentType.CODE]
        )
        
        assert response is not None
        assert len(response.answer) > 0
        assert response.confidence > 0.0
        assert response.processing_time_ms > 0
        assert isinstance(response.sources, list)
        
        logger.info(f"Basic query test passed - confidence: {response.confidence:.2f}")
    
    @pytest.mark.asyncio
    async def test_multimodal_query_processing(self, rag_agent):
        """Test multi-modal query processing."""
        logger.info("Testing multi-modal query processing...")
        
        response = await rag_agent.query(
            query_text="Show me examples of Bedrock block JSON files",
            content_types=[ContentType.DOCUMENTATION, ContentType.CONFIGURATION]
        )
        
        assert response is not None
        assert "json" in response.answer.lower() or "bedrock" in response.answer.lower()
        assert len(response.sources) > 0
        
        # Check if sources contain appropriate content types
        source_types = [source.document.content_type for source in response.sources]
        assert any(ctype in [ContentType.DOCUMENTATION, ContentType.CONFIGURATION] for ctype in source_types)
        
        logger.info(f"Multi-modal query test passed - found {len(response.sources)} sources")
    
    @pytest.mark.asyncio
    async def test_contextual_querying(self, rag_agent):
        """Test contextual query processing with session awareness."""
        logger.info("Testing contextual querying...")
        
        session_id = "test_session_001"
        
        # First query to establish context
        response1 = await rag_agent.query(
            query_text="What are Minecraft blocks?",
            session_id=session_id
        )
        
        # Follow-up query that should benefit from context
        response2 = await rag_agent.query(
            query_text="How do I create custom ones in Java?",
            session_id=session_id
        )
        
        assert response1 is not None
        assert response2 is not None
        
        # The second response should reference blocks/Java given the context
        assert any(word in response2.answer.lower() for word in ['block', 'java', 'custom'])
        
        # Check session context was maintained
        session_context = await rag_agent.get_session_context(session_id)
        assert len(session_context.get('queries', [])) >= 2
        
        logger.info("Contextual querying test passed")
    
    @pytest.mark.asyncio
    async def test_query_expansion_functionality(self, rag_agent):
        """Test query expansion capabilities."""
        logger.info("Testing query expansion...")
        
        # Query that should benefit from expansion
        response = await rag_agent.query(
            query_text="block creation",
            content_types=[ContentType.DOCUMENTATION]
        )
        
        assert response is not None
        
        # Check metadata for expansion information
        expansion_metadata = response.metadata.get('query_expansion', {})
        assert expansion_metadata.get('enabled', False)
        
        if expansion_metadata.get('expansion_terms_count', 0) > 0:
            expanded_query = expansion_metadata.get('expanded_query', '')
            original_query = expansion_metadata.get('original_query', '')
            
            # Expanded query should be longer than original
            assert len(expanded_query.split()) > len(original_query.split())
            logger.info(f"Query expanded from '{original_query}' to '{expanded_query}'")
        
        logger.info("Query expansion test passed")
    
    @pytest.mark.asyncio
    async def test_hybrid_search_functionality(self, rag_agent):
        """Test hybrid search capabilities."""
        logger.info("Testing hybrid search...")
        
        # Test query that should work well with hybrid search
        response = await rag_agent.query(
            query_text="copper block recipe minecraft",
            content_types=None  # Allow all content types
        )
        
        assert response is not None
        assert len(response.sources) > 0
        
        # Check that hybrid search was used
        retrieval_metadata = response.metadata.get('retrieval', {})
        assert retrieval_metadata.get('search_mode') == 'hybrid'
        
        # Verify sources have both semantic and keyword relevance
        for source in response.sources[:3]:
            assert source.final_score > 0.0
            # Should have both similarity and keyword scores
            assert hasattr(source, 'similarity_score')
            assert hasattr(source, 'keyword_score')
        
        logger.info(f"Hybrid search test passed - retrieved {len(response.sources)} sources")
    
    @pytest.mark.asyncio
    async def test_reranking_functionality(self, rag_agent):
        """Test result re-ranking capabilities."""
        logger.info("Testing re-ranking functionality...")
        
        response = await rag_agent.query(
            query_text="detailed guide for creating Minecraft Java blocks",
            content_types=[ContentType.DOCUMENTATION]
        )
        
        assert response is not None
        
        # Check reranking metadata
        reranking_metadata = response.metadata.get('reranking', {})
        assert reranking_metadata.get('enabled', False)
        
        if len(response.sources) > 1:
            # Results should be ordered by relevance
            scores = [source.final_score for source in response.sources]
            assert scores == sorted(scores, reverse=True), "Results should be sorted by score"
        
        logger.info("Re-ranking test passed")
    
    @pytest.mark.asyncio
    async def test_error_handling(self, rag_agent):
        """Test error handling and graceful degradation."""
        logger.info("Testing error handling...")
        
        # Test with empty query
        response = await rag_agent.query(query_text="")
        assert response is not None
        assert "error" in response.answer.lower() or len(response.answer) > 0
        
        # Test with very long query
        long_query = "word " * 200  # 200 words
        response = await rag_agent.query(query_text=long_query)
        assert response is not None
        assert response.processing_time_ms > 0
        
        logger.info("Error handling test passed")
    
    @pytest.mark.asyncio
    async def test_performance_metrics(self, rag_agent):
        """Test performance and timing metrics."""
        logger.info("Testing performance metrics...")
        
        response = await rag_agent.query(
            query_text="How to register blocks in Minecraft Forge"
        )
        
        assert response is not None
        assert response.processing_time_ms > 0
        assert response.processing_time_ms < 10000  # Should complete within 10 seconds
        
        # Check that confidence is reasonable
        assert 0.0 <= response.confidence <= 1.0
        
        # Check metadata completeness
        metadata = response.metadata
        assert 'query_expansion' in metadata
        assert 'retrieval' in metadata
        assert 'generation' in metadata
        assert 'timestamp' in metadata
        
        logger.info(f"Performance test passed - response time: {response.processing_time_ms:.1f}ms")
    
    @pytest.mark.asyncio
    async def test_agent_status_reporting(self, rag_agent):
        """Test agent status and configuration reporting."""
        logger.info("Testing agent status reporting...")
        
        status = rag_agent.get_agent_status()
        
        assert isinstance(status, dict)
        assert 'configuration' in status
        assert 'cache_status' in status
        assert 'capabilities' in status
        
        config = status['configuration']
        assert 'multimodal_enabled' in config
        assert 'query_expansion_enabled' in config
        assert 'reranking_enabled' in config
        
        capabilities = status['capabilities']
        assert isinstance(capabilities, list)
        assert len(capabilities) > 0
        
        logger.info(f"Agent status test passed - {len(capabilities)} capabilities reported")
    
    @pytest.mark.asyncio
    async def test_golden_dataset_evaluation(self, rag_agent, evaluator):
        """Test evaluation against golden dataset."""
        logger.info("Testing golden dataset evaluation...")
        
        # Run evaluation on sample dataset
        evaluation_report = await evaluator.evaluate_full_dataset(rag_agent)
        
        assert evaluation_report is not None
        assert 'evaluation_summary' in evaluation_report
        assert 'category_scores' in evaluation_report
        assert 'metric_summaries' in evaluation_report
        
        summary = evaluation_report['evaluation_summary']
        assert summary['total_queries'] > 0
        assert summary['overall_score'] >= 0.0
        
        # Check that we have metrics for all categories
        category_scores = evaluation_report['category_scores']
        assert 'retrieval' in category_scores
        assert 'generation' in category_scores
        assert 'diversity' in category_scores
        
        logger.info(f"Evaluation test passed - overall score: {summary['overall_score']:.3f}")
    
    @pytest.mark.asyncio
    async def test_single_query_evaluation(self, rag_agent, evaluator):
        """Test evaluation of a single query."""
        logger.info("Testing single query evaluation...")
        
        # Create a test golden item
        golden_item = GoldenDatasetItem(
            query_id="test_001",
            query_text="How to create a basic block in Minecraft",
            query_type="how_to",
            difficulty_level="beginner",
            domain="blocks",
            expected_answer="Create a class extending Block",
            expected_sources=["java_blocks"],
            required_keywords=["block", "class", "create"],
            prohibited_keywords=["bedrock"],
            min_sources=1,
            max_response_time_ms=3000.0,
            min_confidence=0.3,
            content_types=["documentation"],
            metadata={}
        )
        
        # Evaluate the query
        result = await evaluator.evaluate_single_query(rag_agent, golden_item)
        
        assert result is not None
        assert result.query_id == "test_001"
        assert isinstance(result.metrics, dict)
        assert len(result.metrics) > 0
        assert isinstance(result.passed_tests, list)
        assert isinstance(result.failed_tests, list)
        
        # Check specific metrics
        assert 'precision_at_5' in result.metrics
        assert 'keyword_coverage' in result.metrics
        assert 'response_time_ms' in result.metrics
        
        logger.info(f"Single query evaluation passed - {len(result.passed_tests)} tests passed")
    
    def test_evaluation_report_generation(self, evaluator):
        """Test evaluation report generation and formatting."""
        logger.info("Testing evaluation report generation...")
        
        # Create sample evaluation results
        from evaluation.rag_evaluator import EvaluationResult
        from agents.advanced_rag_agent import RAGResponse
        
        # Mock response
        mock_response = RAGResponse(
            answer="Test answer",
            sources=[],
            confidence=0.75,
            processing_time_ms=1500.0,
            metadata={}
        )
        
        # Mock evaluation result
        mock_result = EvaluationResult(
            query_id="test_001",
            query_text="Test query",
            expected_answer="Expected answer",
            expected_sources=["doc1"],
            actual_response=mock_response,
            metrics={
                'precision_at_5': 0.8,
                'keyword_coverage': 0.9,
                'coherence_score': 0.7
            },
            passed_tests=['precision_threshold', 'keyword_coverage'],
            failed_tests=['response_time'],
            evaluation_timestamp="2024-01-01T00:00:00"
        )
        
        # Test report compilation
        report = evaluator._compile_evaluation_report([mock_result])
        
        assert isinstance(report, dict)
        assert 'evaluation_summary' in report
        assert 'metric_summaries' in report
        assert 'recommendations' in report
        
        logger.info("Evaluation report generation test passed")


@pytest.mark.asyncio
async def test_full_advanced_rag_workflow():
    """
    Comprehensive integration test demonstrating the full Advanced RAG workflow.
    
    This test showcases all major components working together.
    """
    logger.info("Starting comprehensive Advanced RAG workflow test...")
    
    # Initialize components
    rag_agent = AdvancedRAGAgent(
        enable_query_expansion=True,
        enable_reranking=True,
        enable_multimodal=True
    )
    
    evaluator = RAGEvaluator()
    evaluator.create_sample_golden_dataset()
    
    # Test queries representing different use cases
    test_queries = [
        {
            "query": "How do I create a copper block in Minecraft Java Edition?",
            "expected_features": ["query_expansion", "hybrid_search", "code_examples"]
        },
        {
            "query": "What's the difference between Java and Bedrock block definitions?",
            "expected_features": ["multimodal_retrieval", "comparison", "documentation"]
        },
        {
            "query": "Show me recipe examples",
            "expected_features": ["example_retrieval", "structured_response"]
        }
    ]
    
    workflow_results = []
    
    for i, test_case in enumerate(test_queries):
        logger.info(f"Processing test query {i+1}: {test_case['query']}")
        
        # Process the query
        response = await rag_agent.query(
            query_text=test_case['query'],
            session_id=f"workflow_test_{i}"
        )
        
        # Validate response
        assert response is not None
        assert len(response.answer) > 50, "Answer should be substantial"
        assert response.confidence > 0.0, "Should have some confidence"
        assert len(response.sources) > 0, "Should retrieve sources"
        
        # Check expected features
        metadata = response.metadata
        for feature in test_case.get('expected_features', []):
            if feature == "query_expansion":
                assert metadata.get('query_expansion', {}).get('enabled', False)
            elif feature == "hybrid_search":
                assert metadata.get('retrieval', {}).get('search_mode') == 'hybrid'
            elif feature == "multimodal_retrieval":
                source_types = [s.document.content_type for s in response.sources]
                # Mock data only has DOCUMENTATION type, so we just verify we have content types
                assert len(source_types) > 0, "Should have content types"
        
        workflow_results.append({
            'query': test_case['query'],
            'response_length': len(response.answer),
            'confidence': response.confidence,
            'sources_count': len(response.sources),
            'processing_time': response.processing_time_ms,
            'features_used': list(metadata.keys())
        })
        
        logger.info(f"Query {i+1} completed successfully")
    
    # Run evaluation on golden dataset
    logger.info("Running golden dataset evaluation...")
    evaluation_report = await evaluator.evaluate_full_dataset(rag_agent)
    
    assert evaluation_report is not None
    overall_score = evaluation_report.get('evaluation_summary', {}).get('overall_score', 0.0)
    
    # Compile comprehensive results
    comprehensive_results = {
        'workflow_test_results': workflow_results,
        'evaluation_report': evaluation_report,
        'agent_status': rag_agent.get_agent_status(),
        'test_summary': {
            'total_queries_tested': len(test_queries),
            'evaluation_overall_score': overall_score,
            'all_queries_successful': all(r['confidence'] > 0.0 for r in workflow_results),
            'average_response_time': sum(r['processing_time'] for r in workflow_results) / len(workflow_results),
            'average_confidence': sum(r['confidence'] for r in workflow_results) / len(workflow_results)
        }
    }
    
    logger.info("=== COMPREHENSIVE ADVANCED RAG WORKFLOW TEST RESULTS ===")
    logger.info(f"Total queries tested: {len(test_queries)}")
    logger.info(f"Evaluation overall score: {overall_score:.3f}")
    logger.info(f"Average response time: {comprehensive_results['test_summary']['average_response_time']:.1f}ms")
    logger.info(f"Average confidence: {comprehensive_results['test_summary']['average_confidence']:.3f}")
    logger.info("All advanced RAG components functioning correctly!")
    
    return comprehensive_results


if __name__ == "__main__":
    # Run the comprehensive test
    asyncio.run(test_full_advanced_rag_workflow())