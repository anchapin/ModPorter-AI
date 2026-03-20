"""
Type Parameter Extractor for Java Generics
Extracts generic type information from Java AST
"""

import javalang
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass, field


@dataclass
class TypeParameter:
    """Represents a Java type parameter"""
    name: str
    bounds: List[str] = field(default_factory=list)
    is_extends: bool = True  # True for extends, False for super
    is_wildcard: bool = False
    wildcard_bound: Optional[str] = None
    
    def __repr__(self):
        if self.is_wildcard:
            if self.wildcard_bound:
                return f"? {self.is_extends and 'extends' or 'super'} {self.wildcard_bound}"
            return "?"
        if self.bounds:
            return f"{self.name} extends {' & '.join(self.bounds)}"
        return self.name


@dataclass
class GenericDeclaration:
    """Represents a generic class or method declaration"""
    name: str
    type_parameters: List[TypeParameter] = field(default_factory=list)
    is_method: bool = False
    return_type: Optional[str] = None
    parameters: List[Dict[str, Any]] = field(default_factory=list)


class TypeParameterExtractor:
    """Extracts type parameters from Java AST"""
    
    def __init__(self):
        self.logger = None
        
    def set_logger(self, logger):
        """Set logger instance"""
        self.logger = logger
        
    def extract_from_class(self, class_node: javalang.tree.ClassDeclaration) -> GenericDeclaration:
        """Extract generic type parameters from a class declaration"""
        type_params = []
        
        if class_node.type_parameters:
            for tp in class_node.type_parameters:
                type_param = self._parse_type_parameter(tp)
                type_params.append(type_param)
        
        return GenericDeclaration(
            name=class_node.name,
            type_parameters=type_params,
            is_method=False
        )
    
    def extract_from_method(self, method_node: javalang.tree.MethodDeclaration) -> GenericDeclaration:
        """Extract generic type parameters from a method declaration"""
        type_params = []
        
        if method_node.type_parameters:
            for tp in method_node.type_parameters:
                type_param = self._parse_type_parameter(tp)
                type_params.append(type_param)
        
        # Get return type
        return_type = None
        if method_node.return_type:
            return_type = self._get_type_name(method_node.return_type)
        
        # Get parameters
        parameters = []
        if method_node.parameters:
            for param in method_node.parameters:
                param_info = {
                    'name': param.name,
                    'type': self._get_type_name(param.type) if param.type else 'unknown'
                }
                # Check if parameter has generic type
                if hasattr(param, 'type') and param.type and hasattr(param.type, 'type_arguments'):
                    if param.type.type_arguments:
                        param_info['generic_args'] = [
                            self._get_type_name(ta) for ta in param.type.type_arguments
                        ]
                parameters.append(param_info)
        
        return GenericDeclaration(
            name=method_node.name,
            type_parameters=type_params,
            is_method=True,
            return_type=return_type,
            parameters=parameters
        )
    
    def _parse_type_parameter(self, tp_node) -> TypeParameter:
        """Parse a type parameter node"""
        name = tp_node.name
        
        bounds = []
        is_extends = True
        
        if tp_node.extends:
            extends = tp_node.extends
            if isinstance(extends, list):
                bounds = [self._get_type_name(e) for e in extends]
            else:
                bounds = [self._get_type_name(extends)]
        
        return TypeParameter(
            name=name,
            bounds=bounds,
            is_extends=is_extends
        )
    
    def _get_type_name(self, type_node) -> str:
        """Get string representation of a type node"""
        if type_node is None:
            return "void"
        
        # Handle basic types
        if isinstance(type_node, str):
            return type_node
        
        # Handle javalang type nodes
        if hasattr(type_node, 'name'):
            name = type_node.name
            # Handle dimensional types (arrays)
            if hasattr(type_node, 'dimensions') and type_node.dimensions:
                name += ''.join(['[]'] * len(type_node.dimensions))
            # Handle generic types
            if hasattr(type_node, 'type_arguments') and type_node.type_arguments:
                args = [self._get_type_name(ta) for ta in type_node.type_arguments]
                name += f"<{', '.join(args)}>"
            return name
        
        return str(type_node)
    
    def extract_from_source(self, source_code: str) -> List[GenericDeclaration]:
        """Extract all generic declarations from source code"""
        declarations = []
        
        try:
            tree = javalang.parse.parse(source_code)
            
            for path, node in tree:
                if isinstance(node, javalang.tree.ClassDeclaration):
                    if node.type_parameters:
                        decl = self.extract_from_class(node)
                        declarations.append(decl)
                
                elif isinstance(node, javalang.tree.MethodDeclaration):
                    if node.type_parameters:
                        decl = self.extract_from_method(node)
                        declarations.append(decl)
        
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Failed to parse source for generics: {e}")
        
        return declarations
    
    def extract_type_arguments(self, type_node) -> List[str]:
        """Extract type arguments from a generic type node"""
        if not type_node or not hasattr(type_node, 'type_arguments'):
            return []
        
        if not type_node.type_arguments:
            return []
        
        return [self._get_type_name(ta) for ta in type_node.type_arguments]


def extract_generics(source_code: str, logger=None) -> List[GenericDeclaration]:
    """Convenience function to extract generics from source code"""
    extractor = TypeParameterExtractor()
    if logger:
        extractor.set_logger(logger)
    return extractor.extract_from_source(source_code)


# Test functions
if __name__ == "__main__":
    test_code = """
    public class GenericClass<T, U extends Entity> {
        public <V extends Comparable> void method(V value) {
            List<Map<String, Integer>> map = new ArrayList<>();
        }
    }
    """
    
    extractor = TypeParameterExtractor()
    declarations = extractor.extract_from_source(test_code)
    
    for decl in declarations:
        print(f"Declaration: {decl.name}")
        for tp in decl.type_parameters:
            print(f"  Type Param: {tp}")
