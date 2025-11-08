"""
Tool utility functions and registry system for dynamic tool discovery and management.
Provides a centralized system for managing AI agent tools with validation and discovery.
"""

import importlib
import importlib.util
import inspect
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Dynamic tool registry system for AI agents.
    Provides tool discovery, validation, and management capabilities.
    """
    
    def __init__(self, tools_directory: Optional[str] = None):
        """
        Initialize the tool registry.
        
        Args:
            tools_directory: Optional custom tools directory path
        """
        if tools_directory:
            self.tools_directory = Path(tools_directory)
        else:
            # Default to the same directory as this file
            self.tools_directory = Path(__file__).parent
        
        self._registered_tools: Dict[str, Dict[str, Any]] = {}
        self._tool_instances: Dict[str, Any] = {}
        
        logger.info(f"ToolRegistry initialized with directory: {self.tools_directory}")
    
    def discover_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Discover all available tools in the tools directory.
        
        Returns:
            Dictionary mapping tool names to their metadata
        """
        discovered_tools = {}
        
        try:
            # Get all Python files in the tools directory
            python_files = list(self.tools_directory.glob("*.py"))
            
            for file_path in python_files:
                # Skip __init__.py and this file
                if file_path.name in ["__init__.py", "tool_utils.py"]:
                    continue
                
                try:
                    tool_info = self._analyze_tool_file(file_path)
                    if tool_info:
                        discovered_tools[tool_info["name"]] = tool_info
                        logger.debug(f"Discovered tool: {tool_info['name']}")
                except Exception as e:
                    logger.warning(f"Failed to analyze tool file {file_path}: {str(e)}")
            
            logger.info(f"Discovered {len(discovered_tools)} tools")
            return discovered_tools
            
        except Exception as e:
            logger.error(f"Tool discovery failed: {str(e)}")
            return {}
    
    def _analyze_tool_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Analyze a tool file to extract metadata.
        
        Args:
            file_path: Path to the tool file
            
        Returns:
            Tool metadata dictionary or None if not a valid tool
        """
        try:
            # Import the module
            module_name = file_path.stem
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return None
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Look for tool classes and functions
            tool_classes = []
            tool_functions = []
            
            for name, obj in inspect.getmembers(module):
                # Check for CrewAI tool classes
                if (inspect.isclass(obj) and 
                    issubclass(obj, BaseTool) and 
                    obj != BaseTool):
                    tool_classes.append({
                        "name": name,
                        "class": obj,
                        "type": "class"
                    })
                
                # Check for decorated tool functions
                elif (inspect.isfunction(obj) and 
                      hasattr(obj, '__name__') and 
                      hasattr(obj, '_is_crewai_tool')):
                    tool_functions.append({
                        "name": name,
                        "function": obj,
                        "type": "function"
                    })
            
            # Extract tool metadata
            if tool_classes or tool_functions:
                return {
                    "name": module_name,
                    "file_path": str(file_path),
                    "module": module,
                    "classes": tool_classes,
                    "functions": tool_functions,
                    "description": getattr(module, "__doc__", "").strip() if hasattr(module, "__doc__") else "",
                    "version": getattr(module, "__version__", "1.0.0") if hasattr(module, "__version__") else "1.0.0"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to analyze tool file {file_path}: {str(e)}")
            return None
    
    def register_tools(self) -> None:
        """Register all discovered tools."""
        discovered = self.discover_tools()
        self._registered_tools.update(discovered)
        logger.info(f"Registered {len(self._registered_tools)} tools")
    
    def get_tool_by_name(self, tool_name: str) -> Optional[Any]:
        """
        Get a tool instance by name.
        
        Args:
            tool_name: Name of the tool to retrieve
            
        Returns:
            Tool instance or None if not found
        """
        if tool_name not in self._registered_tools:
            logger.warning(f"Tool '{tool_name}' not found in registry")
            return None
        
        # Check if we already have an instance
        if tool_name in self._tool_instances:
            return self._tool_instances[tool_name]
        
        try:
            tool_info = self._registered_tools[tool_name]
            
            # If tool has classes, instantiate the first one
            if tool_info["classes"]:
                tool_class = tool_info["classes"][0]["class"]
                instance = tool_class()
                self._tool_instances[tool_name] = instance
                return instance
            
            # If tool has functions, return the module for access to functions
            elif tool_info["functions"]:
                self._tool_instances[tool_name] = tool_info["module"]
                return tool_info["module"]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to instantiate tool '{tool_name}': {str(e)}")
            return None
    
    def get_all_tools(self) -> List[Any]:
        """
        Get all registered tool instances.
        
        Returns:
            List of all tool instances
        """
        tools = []
        for tool_name in self._registered_tools.keys():
            tool = self.get_tool_by_name(tool_name)
            if tool:
                tools.append(tool)
        return tools
    
    def get_tools_by_category(self, category: str) -> List[Any]:
        """
        Get tools filtered by category.
        
        Args:
            category: Tool category to filter by
            
        Returns:
            List of matching tool instances
        """
        matching_tools = []
        
        for tool_name, tool_info in self._registered_tools.items():
            # Check if tool matches category (based on name or description)
            if (category.lower() in tool_name.lower() or 
                category.lower() in tool_info.get("description", "").lower()):
                tool = self.get_tool_by_name(tool_name)
                if tool:
                    matching_tools.append(tool)
        
        return matching_tools
    
    def validate_tool_configuration(self, tool_name: str) -> Dict[str, Any]:
        """
        Validate a tool's configuration and requirements.
        
        Args:
            tool_name: Name of the tool to validate
            
        Returns:
            Validation results dictionary
        """
        if tool_name not in self._registered_tools:
            return {
                "valid": False,
                "errors": [f"Tool '{tool_name}' not found in registry"],
                "warnings": []
            }
        
        validation_result = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "metadata": {}
        }
        
        try:
            tool_info = self._registered_tools[tool_name]
            tool_instance = self.get_tool_by_name(tool_name)
            
            # Basic validation checks
            if not tool_instance:
                validation_result["errors"].append(f"Failed to instantiate tool '{tool_name}'")
                validation_result["valid"] = False
            
            # Check for required methods/attributes
            if tool_info["classes"]:
                for class_info in tool_info["classes"]:
                    tool_class = class_info["class"]
                    
                    # Check if it's a proper BaseTool subclass
                    if not issubclass(tool_class, BaseTool):
                        validation_result["errors"].append(f"Class {class_info['name']} is not a BaseTool subclass")
                        validation_result["valid"] = False
                    
                    # Check for required attributes
                    required_attrs = ["name", "description"]
                    for attr in required_attrs:
                        if not hasattr(tool_class, attr):
                            validation_result["warnings"].append(f"Class {class_info['name']} missing '{attr}' attribute")
            
            # Add metadata
            validation_result["metadata"] = {
                "file_path": tool_info["file_path"],
                "classes_count": len(tool_info["classes"]),
                "functions_count": len(tool_info["functions"]),
                "description": tool_info["description"],
                "version": tool_info["version"]
            }
            
        except Exception as e:
            validation_result["valid"] = False
            validation_result["errors"].append(f"Validation failed: {str(e)}")
        
        return validation_result
    
    def list_available_tools(self) -> List[Dict[str, Any]]:
        """
        List all available tools with their metadata.
        
        Returns:
            List of tool information dictionaries
        """
        if not self._registered_tools:
            self.register_tools()
        
        tools_list = []
        for tool_name, tool_info in self._registered_tools.items():
            validation = self.validate_tool_configuration(tool_name)
            
            tools_list.append({
                "name": tool_name,
                "description": tool_info["description"],
                "version": tool_info["version"],
                "file_path": tool_info["file_path"],
                "classes": [c["name"] for c in tool_info["classes"]],
                "functions": [f["name"] for f in tool_info["functions"]],
                "valid": validation["valid"],
                "errors": validation["errors"],
                "warnings": validation["warnings"]
            })
        
        return tools_list
    
    def export_registry(self, output_file: Optional[str] = None) -> Dict[str, Any]:
        """
        Export the tool registry to a JSON file or return as dictionary.
        
        Args:
            output_file: Optional file path to export to
            
        Returns:
            Registry data as dictionary
        """
        from datetime import datetime
        
        registry_data = {
            "tools_directory": str(self.tools_directory),
            "total_tools": len(self._registered_tools),
            "tools": self.list_available_tools(),
            "export_timestamp": datetime.now().isoformat()
        }
        
        if output_file:
            try:
                with open(output_file, 'w') as f:
                    json.dump(registry_data, f, indent=2, default=str)
                logger.info(f"Registry exported to {output_file}")
            except Exception as e:
                logger.error(f"Failed to export registry: {str(e)}")
        
        return registry_data


# Global registry instance
_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """
    Get the global tool registry instance.
    
    Returns:
        Global ToolRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
        _global_registry.register_tools()
    return _global_registry


def list_all_tools() -> List[Dict[str, Any]]:
    """
    List all tools in the tools directory.
    
    Returns:
        List of tool information dictionaries
    """
    registry = get_tool_registry()
    return registry.list_available_tools()


def load_tool_by_name(tool_name: str) -> Optional[Any]:
    """
    Load a tool by name from the registry.
    
    Args:
        tool_name: Name of the tool to load
        
    Returns:
        Tool instance or None if not found
    """
    registry = get_tool_registry()
    return registry.get_tool_by_name(tool_name)


def validate_tool_configuration(tool_name: str) -> Dict[str, Any]:
    """
    Validate a tool's configuration.
    
    Args:
        tool_name: Name of the tool to validate
        
    Returns:
        Validation results dictionary
    """
    registry = get_tool_registry()
    return registry.validate_tool_configuration(tool_name)
