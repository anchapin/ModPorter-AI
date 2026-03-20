"""
Generic Type Mapper
Maps Java generic types to Bedrock-compatible JavaScript representations
"""

from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from copy import deepcopy
import re


@dataclass
class TypeMapping:
    """Represents a mapping from Java type to Bedrock type"""
    java_type: str
    bedrock_type: str
    description: str = ""
    requires_cast: bool = False


class GenericTypeMapper:
    """Maps Java generic types to Bedrock-compatible types"""
    
    # Default type mappings for common Java types
    DEFAULT_TYPE_MAPPINGS = {
        # Primitives
        "int": "number",
        "long": "number",
        "float": "number",
        "double": "number",
        "boolean": "boolean",
        "char": "string",
        "byte": "number",
        "short": "number",
        
        # Common Java types
        "String": "string",
        "Integer": "number",
        "Long": "number",
        "Double": "number",
        "Float": "number",
        "Boolean": "boolean",
        "Character": "string",
        "Object": "any",
        "Class": "string",
        
        # Collection types
        "List": "Array",
        "ArrayList": "Array",
        "LinkedList": "Array",
        "Set": "Array",
        "HashSet": "Array",
        "Map": "Object",
        "HashMap": "Object",
        "Collection": "Array",
        "Iterable": "Array",
        
        # Optional
        "Optional": "any",
        "OptionalInt": "number",
        "OptionalDouble": "number",
        "OptionalLong": "number",
        
        # Common Minecraft types
        "ItemStack": "ItemStack",
        "BlockPos": "Vector3",
        "Vec3": "Vector3",
        "Entity": "Entity",
        "Player": "Player",
        "World": "World",
        "Location": "Vector3",
    }
    
    def __init__(self):
        self.type_mappings = deepcopy(self.DEFAULT_TYPE_MAPPINGS)
        self.type_parameters: Dict[str, str] = {}  # Maps type param name to resolved type
        self.logger = None
        
    def set_logger(self, logger):
        """Set logger instance"""
        self.logger = logger
        
    def add_type_mapping(self, java_type: str, bedrock_type: str, description: str = ""):
        """Add a custom type mapping"""
        self.type_mappings[java_type] = TypeMapping(java_type, bedrock_type, description)
        
    def map_type(self, java_type: str, context: Optional[Dict] = None) -> str:
        """
        Map a Java type to a Bedrock-compatible type
        
        Args:
            java_type: The Java type to map
            context: Optional context with type parameter substitutions
            
        Returns:
            Mapped Bedrock type string
        """
        if not java_type:
            return "any"
            
        # Handle array types
        if java_type.endswith("[]"):
            base_type = java_type[:-2]
            mapped = self.map_type(base_type, context)
            return f"Array<{mapped}>"
        
        # Handle primitive types
        if java_type in self.type_mappings:
            return self.type_mappings[java_type]
        
        # Handle type parameters from context
        if context and java_type in context:
            return context[java_type]
        
        # Handle unknown types - return as-is for now
        return java_type
    
    def map_generic_type(self, type_str: str, type_params: Dict[str, str]) -> str:
        """
        Map a generic type string with type parameter substitutions
        
        Args:
            type_str: The generic type string (e.g., "List<T>")
            type_params: Dictionary mapping type parameter names to concrete types
            
        Returns:
            Mapped generic type string
        """
        if not type_str:
            return "any"
            
        # Handle parameterized types like List<T>, Map<K, V>
        match = re.match(r'(\w+)<(.+)>', type_str)
        if match:
            base_type = match.group(1)
            args_str = match.group(2)
            
            # Split arguments (handle nested generics)
            args = self._split_type_args(args_str)
            
            # Map each argument
            mapped_args = []
            for arg in args:
                arg = arg.strip()
                if arg in type_params:
                    mapped_args.append(type_params[arg])
                else:
                    mapped_args.append(self.map_type(arg))
            
            mapped_base = self.map_type(base_type)
            return f"{mapped_base}<{', '.join(mapped_args)}>"
        
        # Not a parameterized type
        return self.map_type(type_str, type_params)
    
    def _split_type_args(self, args_str: str) -> List[str]:
        """Split type arguments, handling nested generics"""
        result = []
        current = ""
        depth = 0
        
        for char in args_str:
            if char == '<':
                depth += 1
                current += char
            elif char == '>':
                depth -= 1
                current += char
            elif char == ',' and depth == 0:
                result.append(current)
                current = ""
            else:
                current += char
        
        if current:
            result.append(current)
            
        return result
    
    def resolve_type_parameter(self, type_param: str, usage_type: Optional[str] = None) -> str:
        """
        Resolve a type parameter to a concrete type
        
        Args:
            type_param: The type parameter name (e.g., 'T')
            usage_type: Optional usage context to infer type
            
        Returns:
            Resolved type string
        """
        if type_param in self.type_parameters:
            return self.type_parameters[type_param]
        
        # Default resolution based on common patterns
        if usage_type:
            return self.map_type(usage_type)
        
        return "any"
    
    def set_type_parameter(self, name: str, concrete_type: str):
        """Set a type parameter mapping"""
        self.type_parameters[name] = concrete_type
        
    def clear_type_parameters(self):
        """Clear all type parameter mappings"""
        self.type_parameters.clear()
        
    def extract_type_params(self, generic_type: str) -> List[str]:
        """Extract type parameter names from a generic type string"""
        match = re.match(r'\w+<(.+)>', generic_type)
        if match:
            args_str = match.group(1)
            return [arg.strip() for arg in self._split_type_args(args_str)]
        return []
    
    def substitute_type_params(self, type_str: str, substitutions: Dict[str, str]) -> str:
        """
        Substitute type parameters in a type string
        
        Args:
            type_str: Type string potentially containing type parameters
            substitutions: Dictionary of substitutions
            
        Returns:
            Type string with substitutions applied
        """
        result = type_str
        
        for param, concrete in substitutions.items():
            # Replace exact parameter
            result = re.sub(rf'\b{param}\b', concrete, result)
        
        return result


# Convenience function
def map_java_to_bedrock(java_type: str, type_params: Optional[Dict[str, str]] = None) -> str:
    """Map a Java type to Bedrock-compatible type"""
    mapper = GenericTypeMapper()
    if type_params:
        for param, concrete in type_params.items():
            mapper.set_type_parameter(param, concrete)
    return mapper.map_type(java_type)


# Test
if __name__ == "__main__":
    mapper = GenericTypeMapper()
    
    # Test basic mapping
    print(f"String -> {mapper.map_type('String')}")
    print(f"List -> {mapper.map_type('List')}")
    print(f"int[] -> {mapper.map_type('int[]')}")
    
    # Test generic mapping
    mapper.set_type_parameter("T", "string")
    mapper.set_type_parameter("U", "number")
    
    print(f"List<T> -> {mapper.map_generic_type('List<T>', mapper.type_parameters)}")
    print(f"Map<String, Integer> -> {mapper.map_generic_type('Map<String, Integer>', {})}")


if __name__ == "__main__":
    # Test more complex cases
    mapper = GenericTypeMapper()
    
    # Test nested generics
    result = mapper.map_generic_type("List<Map<String, Integer>>", {})
    print(f"Nested: {result}")
    
    # Test type parameter substitution
    substitutions = {"T": "Entity", "V": "Player"}
    result = mapper.substitute_type_params("Map<T, List<V>>", substitutions)
    print(f"Substituted: {result}")
