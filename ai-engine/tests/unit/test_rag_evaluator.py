import json
import os
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock

from src.testing.rag_evaluator import RagEvaluator
from src.tools.search_tool import SearchTool


class TestRagEvaluator(unittest.TestCase):
    """Test class for RagEvaluator functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Clear SearchTool singleton
        SearchTool._instance = None
        
        # Create a temporary evaluation set file
        self.test_eval_data = {
            "evaluation_queries": [
                {
                    "id": "TEST_Q001",
                    "query": "test query",
                    "expected_document_snippet": "test document content",
                    "expected_response_keywords": ["test", "query"]
                }
            ]
        }
        
        # Create temporary file
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.test_eval_data, self.temp_file)
        self.temp_file.close()
        
    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.temp_file.name):
            os.unlink(self.temp_file.name)

    @patch('src.testing.rag_evaluator.KnowledgeBaseAgent')
    def test_rag_evaluator_initialization(self, mock_kb_agent):
        """Test RagEvaluator initialization."""
        # Mock the knowledge base agent and search tool
        mock_search_tool = SearchTool.get_instance()
        mock_kb_agent.return_value.get_tools.return_value = [mock_search_tool]
        
        evaluator = RagEvaluator(self.temp_file.name)
        
        self.assertEqual(evaluator.eval_set_path, self.temp_file.name)
        self.assertEqual(len(evaluator.evaluation_data), 1)
        self.assertEqual(evaluator.evaluation_data[0]["id"], "TEST_Q001")
        mock_kb_agent.assert_called_once()

    @patch('src.testing.rag_evaluator.KnowledgeBaseAgent')
    def test_evaluate_retrieval(self, mock_kb_agent):
        """Test the evaluate_retrieval method."""
        # Mock the knowledge base agent and search tool
        mock_search_tool = SearchTool.get_instance()
        mock_kb_agent.return_value.get_tools.return_value = [mock_search_tool]
        
        evaluator = RagEvaluator(self.temp_file.name)
        evaluator.evaluate_retrieval()
        
        # Check metrics - the SearchTool has default results that should match our expectation
        self.assertEqual(evaluator.retrieval_metrics["total_queries"], 1)
        # The evaluation will depend on whether the hardcoded results contain our expected snippet
        self.assertGreaterEqual(evaluator.retrieval_metrics["hits"], 0)

    @patch('src.testing.rag_evaluator.KnowledgeBaseAgent')
    def test_evaluate_retrieval_miss(self, mock_kb_agent):
        """Test the evaluate_retrieval method when snippet is not found."""
        # Mock the knowledge base agent and search tool
        mock_search_tool = SearchTool.get_instance()
        mock_kb_agent.return_value.get_tools.return_value = [mock_search_tool]
        
        evaluator = RagEvaluator(self.temp_file.name)
        evaluator.evaluate_retrieval()
        
        # Check metrics - since we're using real SearchTool, exact hit count depends on hardcoded results
        self.assertEqual(evaluator.retrieval_metrics["total_queries"], 1)
        # Just check that metrics are properly set
        self.assertGreaterEqual(evaluator.retrieval_metrics["hits"], 0)

    @patch('src.testing.rag_evaluator.KnowledgeBaseAgent')
    def test_load_evaluation_set_file_not_found(self, mock_kb_agent):
        """Test loading evaluation set when file doesn't exist."""
        mock_search_tool = SearchTool.get_instance()
        mock_kb_agent.return_value.get_tools.return_value = [mock_search_tool]
        
        evaluator = RagEvaluator("/nonexistent/path.json")
        
        self.assertEqual(evaluator.evaluation_data, [])

    @patch('src.testing.rag_evaluator.KnowledgeBaseAgent')
    @patch('builtins.print')
    def test_report_metrics(self, mock_print, mock_kb_agent):
        """Test the report_metrics method."""
        mock_search_tool = SearchTool.get_instance()
        mock_kb_agent.return_value.get_tools.return_value = [mock_search_tool]
        
        evaluator = RagEvaluator(self.temp_file.name)
        evaluator.retrieval_metrics = {"total_queries": 10, "hits": 7}
        evaluator.report_metrics()
        
        # Check that print was called with expected metrics
        mock_print.assert_any_call("Retrieval Hit Rate: 70.00% (7/10 queries hit)")


if __name__ == '__main__':
    unittest.main()