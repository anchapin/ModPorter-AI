import unittest
from unittest.mock import patch, MagicMock

# Make sure Config can be imported if it's in a different path
# For this exercise, assume direct import works or PYTHONPATH is set.
from ai_engine.src.utils.config import Config
from ai_engine.src.tools.search_tool import SearchTool
# Assuming WebSearchTool is correctly placed for import
from ai_engine.src.tools.web_search_tool import WebSearchTool

class TestSearchToolFallback(unittest.TestCase):

    def setUp(self):
        """Setup common test resources."""
        self.search_tool = SearchTool()
        self.query = "test query"

    @patch.object(SearchTool, '_perform_primary_search')
    def test_search_with_primary_results(self, mock_primary_search):
        """Test SearchTool returns primary results when available."""
        expected_results_list = [{"id": 1, "score": 0.9, "text": "Primary result 1"}] # Added score for formatting
        mock_primary_search.return_value = expected_results_list

        # Fallback should not be enabled or needed
        with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', False):
            result_str = self.search_tool._run(self.query)

        mock_primary_search.assert_called_once_with(self.query)
        self.assertIn("Found 1 results", result_str)
        self.assertIn("Primary result 1", result_str)
        # Ensure fallback tool (WebSearchTool) was not called (implicitly)
        # No direct mock here, but if primary search returns results, fallback path is skipped.

    @patch('ai_engine.src.tools.search_tool.importlib.import_module')
    @patch.object(SearchTool, '_perform_primary_search')
    def test_search_fallback_when_primary_fails_and_fallback_enabled(self, mock_primary_search, mock_import_module):
        """Test fallback is used when primary search fails and fallback is enabled."""
        mock_primary_search.return_value = []  # Simulate primary search failure

        # Mock the dynamic import and the fallback tool
        mock_fallback_tool_instance = MagicMock(spec=WebSearchTool)
        mock_fallback_tool_instance._run.return_value = "Fallback search result"

        # This simulates the class being found in the imported module
        MockFallbackToolClass = MagicMock(return_value=mock_fallback_tool_instance)
        mock_module = MagicMock()
        # The class name is derived dynamically in search_tool.py from FALLBACK_SEARCH_TOOL
        # If FALLBACK_SEARCH_TOOL is "web_search_tool", class name is "WebSearchTool"
        setattr(mock_module, "WebSearchTool", MockFallbackToolClass)
        mock_import_module.return_value = mock_module

        with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', True), \
             patch.object(Config, 'FALLBACK_SEARCH_TOOL', "web_search_tool"):

            result_str = self.search_tool._run(self.query)

        mock_primary_search.assert_called_once_with(self.query)
        mock_import_module.assert_called_once_with("ai_engine.src.tools.web_search_tool")
        # Ensure the dynamically generated class name "WebSearchTool" was accessed on the module
        self.assertTrue(hasattr(mock_module, "WebSearchTool"))
        MockFallbackToolClass.assert_called_once() # Ensure class was instantiated
        mock_fallback_tool_instance._run.assert_called_once_with(query=self.query)
        self.assertEqual(result_str, "Fallback search result")

    @patch.object(SearchTool, '_perform_primary_search')
    @patch('ai_engine.src.tools.search_tool.importlib.import_module') # To ensure it's not called
    def test_search_no_fallback_when_primary_fails_and_fallback_disabled(self, mock_import_module, mock_primary_search):
        """Test fallback is not used when primary fails and fallback is disabled."""
        mock_primary_search.return_value = []  # Simulate primary search failure

        with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', False):
            result_str = self.search_tool._run(self.query)
        
        mock_primary_search.assert_called_once_with(self.query)
        mock_import_module.assert_not_called() # Fallback tool import should not be attempted
        self.assertIn(f"No results found for query '{self.query}'", result_str)

    @patch.object(SearchTool, '_perform_primary_search')
    @patch('ai_engine.src.tools.search_tool.importlib.import_module')
    def test_search_fallback_handles_invalid_tool_name(self, mock_import_module, mock_primary_search):
        """Test fallback with an invalid tool name handles the error gracefully."""
        mock_primary_search.return_value = []  # Simulate primary search failure
        mock_import_module.side_effect = ImportError("No module named non_existent_tool")

        with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', True), \
             patch.object(Config, 'FALLBACK_SEARCH_TOOL', "non_existent_tool"):

            result_str = self.search_tool._run(self.query)

        mock_primary_search.assert_called_once_with(self.query)
        mock_import_module.assert_called_once_with("ai_engine.src.tools.non_existent_tool")
        self.assertIn("Fallback tool 'non_existent_tool' module not found", result_str)
        self.assertIn("Returning original (empty) results", result_str)

    @patch.object(SearchTool, '_perform_primary_search')
    @patch('ai_engine.src.tools.search_tool.importlib.import_module')
    def test_search_fallback_handles_tool_without_class(self, mock_import_module, mock_primary_search):
        """Test fallback with a valid module but missing class."""
        mock_primary_search.return_value = []

        # Simulate the module being imported correctly
        mock_module = MagicMock()
        # Simulate that the expected class (e.g., ValidModuleInvalidClassTool) is NOT in the module
        # The getattr in search_tool.py will raise AttributeError
        # To ensure this, we make sure the dynamically constructed class name is not an attribute
        tool_name_config = "valid_module_invalid_class_tool"
        class_name_expected = "".join([part.capitalize() for part in tool_name_config.split('_')])

        # Explicitly make getattr on the mock_module raise AttributeError for the specific class name
        def mock_getattr(item, name):
            if name == class_name_expected:
                raise AttributeError(f"Mock module has no attribute {name}")
            return MagicMock() # Default for other attributes
        mock_module.getattr = mock_getattr # This is not the right way to mock getattr for a module.
                                           # Instead, we ensure the attribute *doesn't* exist.

        # A simpler way for the test: ensure the mock_module does NOT have the attribute.
        # If the attribute `class_name_expected` exists on `mock_module`, del it.
        # Or, more directly, make `getattr(mock_module, class_name_expected)` raise AttributeError.
        # We can achieve this by setting a side_effect for `getattr` if we were mocking `getattr` itself,
        # but here we mock the module. So, we ensure the attribute is missing.

        # Let's try this: if the class_name_expected is requested from mock_module, it raises AttributeError
        # This requires mock_module to be configured appropriately.
        # A simple way is to make mock_module a MagicMock and then del the attribute if it exists by chance,
        # or ensure it's not set.
        # The `spec` argument to MagicMock can also be useful.
        # For now, let's assume `getattr(mock_module, class_name_expected)` will raise AttributeError
        # if `class_name_expected` was not explicitly defined on `mock_module`.
        # We can make this more robust by configuring `mock_module.__getattr__` or `mock_module.side_effect`.
        
        # Let's make the mock_module raise AttributeError when the specific class name is accessed
        mock_module_with_missing_class = MagicMock()
        def side_effect_for_getattr(attr_name):
            if attr_name == class_name_expected:
                raise AttributeError(f"Simulated AttributeError for {attr_name}")
            return MagicMock() # Default behavior for other attributes
        mock_module_with_missing_class.__getattr__ = MagicMock(side_effect=side_effect_for_getattr)
        mock_import_module.return_value = mock_module_with_missing_class
        
        with patch.object(Config, 'SEARCH_FALLBACK_ENABLED', True), \
             patch.object(Config, 'FALLBACK_SEARCH_TOOL', tool_name_config):

            result_str = self.search_tool._run(self.query)

        mock_primary_search.assert_called_once_with(self.query)
        mock_import_module.assert_called_once_with(f"ai_engine.src.tools.{tool_name_config}")
        self.assertIn(f"Fallback tool class '{class_name_expected}' not found in module", result_str)
        self.assertIn("Returning original (empty) results", result_str)

if __name__ == '__main__':
    unittest.main()
