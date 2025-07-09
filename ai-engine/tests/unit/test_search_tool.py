import unittest
from unittest.mock import patch, MagicMock

from src.utils.config import Config
from src.tools.search_tool import SearchTool
from src.tools.web_search_tool import WebSearchTool

class TestSearchToolFallback(unittest.TestCase):
    """Test suite for SearchTool fallback functionality."""

    def setUp(self):
        """Setup common test resources."""
        self.search_tool = SearchTool()
        self.query = "test query"

    @patch.object(SearchTool, '_perform_primary_search')
    def test_search_with_primary_results(self, mock_primary_search):
        """Test SearchTool returns primary results when available."""
        expected_results_list = [{"id": 1, "score": 0.9, "text": "Primary result 1"}]
        mock_primary_search.return_value = expected_results_list

        with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', False):
            result_str = self.search_tool._run(self.query)

        mock_primary_search.assert_called_once_with(self.query)
        self.assertIn("Found 1 results", result_str)
        self.assertIn("Primary result 1", result_str)

    @patch('src.tools.search_tool.importlib.import_module')
    @patch.object(SearchTool, '_perform_primary_search')
    def test_search_fallback_when_primary_fails_and_fallback_enabled(self, mock_primary_search, mock_import_module):
        """Test fallback is used when primary search fails and fallback is enabled."""
        mock_primary_search.return_value = []

        # Mock the fallback tool behavior
        mock_fallback_tool_instance = MagicMock(spec=WebSearchTool)
        mock_fallback_tool_instance._run.return_value = "Fallback search result"

        MockFallbackToolClass = MagicMock(return_value=mock_fallback_tool_instance)
        mock_module = MagicMock()
        setattr(mock_module, "WebSearchTool", MockFallbackToolClass)
        mock_import_module.return_value = mock_module

        with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', True), \
             patch.object(Config, 'FALLBACK_SEARCH_TOOL', "web_search_tool"):

            result_str = self.search_tool._run(self.query)

        mock_primary_search.assert_called_once_with(self.query)
        mock_import_module.assert_called_once_with("src.tools.web_search_tool")
        self.assertTrue(hasattr(mock_module, "WebSearchTool"))
        MockFallbackToolClass.assert_called_once()
        mock_fallback_tool_instance._run.assert_called_once_with(query=self.query)
        self.assertEqual(result_str, "Fallback search result")

    @patch.object(SearchTool, '_perform_primary_search')
    @patch('src.tools.search_tool.importlib.import_module')
    def test_search_no_fallback_when_primary_fails_and_fallback_disabled(self, mock_import_module, mock_primary_search):
        """Test fallback is not used when primary fails and fallback is disabled."""
        mock_primary_search.return_value = []

        with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', False):
            result_str = self.search_tool._run(self.query)
        
        mock_primary_search.assert_called_once_with(self.query)
        mock_import_module.assert_not_called()
        self.assertIn(f"No results found for query '{self.query}'", result_str)

    @patch.object(SearchTool, '_perform_primary_search')
    @patch('src.tools.search_tool.importlib.import_module')
    def test_search_fallback_handles_invalid_tool_name(self, mock_import_module, mock_primary_search):
        """Test fallback with an invalid tool name handles the error gracefully."""
        mock_primary_search.return_value = []
        mock_import_module.side_effect = ImportError("No module named non_existent_tool")

        with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', True), \
             patch.object(Config, 'FALLBACK_SEARCH_TOOL', "non_existent_tool"):

            result_str = self.search_tool._run(self.query)

        mock_primary_search.assert_called_once_with(self.query)
        mock_import_module.assert_called_once_with("src.tools.non_existent_tool")
        self.assertIn("Fallback tool 'non_existent_tool' module not found", result_str)
        self.assertIn("Returning original (empty) results", result_str)

    @patch.object(SearchTool, '_perform_primary_search')
    @patch('src.tools.search_tool.importlib.import_module')
    def test_search_fallback_handles_tool_without_class(self, mock_import_module, mock_primary_search):
        """Test fallback with a valid module but missing class."""
        mock_primary_search.return_value = []

        # Configure mock module to raise AttributeError for the specific class name
        tool_name_config = "valid_module_invalid_class_tool"
        class_name_expected = "".join([part.capitalize() for part in tool_name_config.split('_')])
        
        # Create a custom mock that handles getattr specifically
        class MockModule:
            def __getattr__(self, name):
                if name == class_name_expected:
                    raise AttributeError(f"module has no attribute '{name}'")
                return MagicMock()
        
        mock_module = MockModule()
        mock_import_module.return_value = mock_module
        
        with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', True), \
             patch.object(Config, 'FALLBACK_SEARCH_TOOL', tool_name_config):

            result_str = self.search_tool._run(self.query)

        mock_primary_search.assert_called_once_with(self.query)
        mock_import_module.assert_called_once_with(f"src.tools.{tool_name_config}")
        self.assertIn(f"Fallback tool class '{class_name_expected}' not found in module", result_str)
        self.assertIn("Returning original (empty) results", result_str)

if __name__ == '__main__':
    unittest.main()
