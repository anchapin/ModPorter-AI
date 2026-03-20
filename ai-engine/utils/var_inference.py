"""Var Type Inference for Java 10+ to TypeScript conversion.

This module provides functionality to detect, analyze, and convert
Java 'var' keyword (local variable type inference) to TypeScript types.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Set
import javalang
from javalang.tree import (
    ReferenceType, LocalVariableDeclaration, VariableDeclarator,
    ClassCreator, MethodInvocation, MemberReference, Literal,
    LambdaExpression, MethodReference, This
)


@dataclass
class VarDeclaration:
    """Represents a single var declaration."""
    name: str
    inferred_type: Optional[str] = None
    initializer: Optional[str] = None
    initializer_type: Optional[str] = None  # 'new', 'method', 'lambda', 'this', 'literal'
    line_number: Optional[int] = None
    scope: str = "method"  # method, for-loop, lambda
    
    def __repr__(self) -> str:
        return f"VarDeclaration({self.name}: {self.inferred_type})"


@dataclass
class VarScope:
    """Represents a scope containing var declarations."""
    scope_id: str
    parent_scope: Optional['VarScope'] = None
    declarations: Dict[str, VarDeclaration] = field(default_factory=dict)
    children: List['VarScope'] = field(default_factory=list)
    
    def add(self, decl: VarDeclaration):
        """Add a var declaration to this scope."""
        self.declarations[decl.name] = decl
    
    def get(self, name: str) -> Optional[VarDeclaration]:
        """Get a declaration by name, checking parent scopes."""
        if name in self.declarations:
            return self.declarations[name]
        if self.parent_scope:
            return self.parent_scope.get(name)
        return None


class VarDetector:
    """Detects var declarations in Java source code."""
    
    def __init__(self):
        self.var_declarations: List[VarDeclaration] = []
        self._source_lines: List[str] = []
    
    def reset(self):
        """Reset detector state for new source."""
        self.var_declarations = []
        self._source_lines = []
    
    def detect_from_source(self, source_code: str) -> List[VarDeclaration]:
        """Detect all var declarations in source code.
        
        Args:
            source_code: Java source code string
            
        Returns:
            List of detected VarDeclaration objects
        """
        self.reset()
        self._source_lines = source_code.split('\n')
        
        try:
            tree = javalang.parse.parse(source_code)
            self._walk_tree(tree)
        except (javalang.parser.JavaParserError, javalang.parser.ParserError):
            pass  # Silently handle parse errors for non-var code
        
        return self.var_declarations
    
    def _walk_tree(self, tree):
        """Walk the AST and find var declarations."""
        for path, node in tree:
            # Check for LocalVariableDeclaration with var type
            if isinstance(node, LocalVariableDeclaration):
                self._process_local_var_decl(node)
        
        # Also check ForStatement for EnhancedForControl with var
        for path, node in tree:
            if isinstance(node, javalang.tree.ForStatement):
                if hasattr(node, 'control') and node.control:
                    self._process_for_each_control(node.control)
    
    def _process_local_var_decl(self, node: LocalVariableDeclaration):
        """Process a local variable declaration with var type."""
        # Check if type is 'var'
        if not isinstance(node.type, ReferenceType):
            return
        
        if node.type.name != 'var':
            return
        
        # Get line number
        line_number = node.position.line if node.position else None
        
        # Process each declarator
        for declarator in node.declarators:
            if not isinstance(declarator, VariableDeclarator):
                continue
            
            var_name = declarator.name
            var_decl = VarDeclaration(
                name=var_name,
                line_number=line_number,
                scope="method"
            )
            
            # Analyze initializer
            if declarator.initializer:
                var_decl.initializer = self._get_initializer_text(declarator.initializer)
                self._infer_initializer_type(var_decl, declarator.initializer)
            
            self.var_declarations.append(var_decl)
    
    def _process_for_each_control(self, control):
        """Process EnhancedForControl with var."""
        if not hasattr(control, 'var'):
            return
        
        var_node = control.var
        if not isinstance(var_node, javalang.tree.VariableDeclaration):
            return
        
        # Check if the variable declaration type is 'var'
        if not hasattr(var_node, 'type'):
            return
        
        var_type = var_node.type
        if not isinstance(var_type, ReferenceType):
            return
        
        if var_type.name != 'var':
            return
        
        line_number = var_node.position.line if var_node.position else None
        
        # Get variable name
        if var_node.declarators:
            var_name = var_node.declarators[0].name
        else:
            return
        
        # Get the iterable type from the for-loop
        var_decl = VarDeclaration(
            name=var_name,
            line_number=line_number,
            scope="for-loop"
        )
        
        # Infer from iterable
        if hasattr(control, 'iterable'):
            self._infer_from_iterable(var_decl, control.iterable)
        
        self.var_declarations.append(var_decl)
    
    def _get_initializer_text(self, node) -> str:
        """Get the text representation of an initializer."""
        if isinstance(node, ClassCreator):
            # new ClassName<...>(...)
            parts = []
            if node.qualifier:
                parts.append(node.qualifier + ".")
            parts.append(node.type.name if hasattr(node.type, 'name') else str(node.type))
            
            # Add type arguments if present
            if node.type and hasattr(node.type, 'arguments'):
                type_args = node.type.arguments
                if type_args:
                    args_str = ", ".join(
                        self._get_type_argument_text(ta) for ta in type_args
                    )
                    parts[-1] = f"{parts[-1]}<{args_str}>"
            
            # Add constructor arguments
            if node.arguments:
                args_str = ", ".join(str(a) for a in node.arguments)
                parts.append(f"({args_str})")
            else:
                parts.append("()")
            
            return "".join(parts)
        
        elif isinstance(node, MethodInvocation):
            return node.member
        
        elif isinstance(node, MemberReference):
            return node.member
        
        elif isinstance(node, Literal):
            return str(node.value)
        
        elif isinstance(node, LambdaExpression):
            return "(...) => ..."
        
        elif isinstance(node, MethodReference):
            return f"{node.member}::..."
        
        elif isinstance(node, This):
            return "this"
        
        return str(node)
    
    def _get_type_argument_text(self, ta) -> str:
        """Get text for a type argument."""
        if hasattr(ta, 'type') and ta.type:
            return ta.type.name if hasattr(ta.type, 'name') else str(ta.type)
        return str(ta)
    
    def _infer_initializer_type(self, var_decl: VarDeclaration, initializer):
        """Infer the type from the initializer expression."""
        if isinstance(initializer, ClassCreator):
            var_decl.initializer_type = 'new'
            var_decl.inferred_type = self._infer_from_creator(initializer)
        
        elif isinstance(initializer, MethodInvocation):
            var_decl.initializer_type = 'method'
            # Method invocations return the method's return type
            # For now, we'll need context to know the return type
            var_decl.inferred_type = self._infer_from_method_invocation(initializer)
        
        elif isinstance(initializer, MemberReference):
            var_decl.initializer_type = 'member'
            var_decl.inferred_type = self._infer_from_member_reference(initializer)
        
        elif isinstance(initializer, Literal):
            var_decl.initializer_type = 'literal'
            var_decl.inferred_type = self._infer_from_literal(initializer)
        
        elif isinstance(initializer, LambdaExpression):
            var_decl.initializer_type = 'lambda'
            var_decl.inferred_type = self._infer_from_lambda(initializer)
        
        elif isinstance(initializer, MethodReference):
            var_decl.initializer_type = 'method_ref'
            var_decl.inferred_type = self._infer_from_method_ref(initializer)
    
    def _infer_from_creator(self, creator: ClassCreator) -> str:
        """Infer type from a constructor call."""
        type_name = creator.type.name if hasattr(creator.type, 'name') else 'Object'
        
        # Handle qualifiers (nested classes)
        if creator.qualifier:
            type_name = f"{creator.qualifier}.{type_name}"
        
        # Handle dimensions (arrays)
        if creator.type.dimensions:
            type_name += "[]"
        
        # Handle type arguments - convert Java types to TypeScript
        if creator.type and hasattr(creator.type, 'arguments') and creator.type.arguments:
            type_args = []
            for ta in creator.type.arguments:
                if hasattr(ta, 'type') and ta.type:
                    arg_name = ta.type.name if hasattr(ta.type, 'name') else '?'
                    # Convert Java wrapper types to TypeScript
                    arg_name = self._convert_type_argument(arg_name)
                    type_args.append(arg_name)
                else:
                    type_args.append('?')
            
            # Check for diamond operator (empty type args)
            if not any(type_args):
                # Diamond operator - try to infer from context
                return type_name  # The type without generics
            
            type_name = f"{type_name}<{', '.join(type_args)}>"
        
        return type_name
    
    def _infer_from_method_invocation(self, inv: MethodInvocation) -> str:
        """Infer return type from method invocation."""
        # This requires method resolution which needs more context
        # For now, return unknown - caller should use type inference
        return "/* return type */"
    
    def _infer_from_member_reference(self, ref: MemberReference) -> str:
        """Infer type from member reference."""
        # Without type context, we can't determine the type
        return "/* member type */"
    
    def _infer_from_literal(self, lit: Literal) -> str:
        """Infer type from literal value."""
        value = str(lit.value)
        
        if value.startswith('"') or value.startswith("'"):
            return "string"
        elif value.endswith('f') or value.endswith('F'):
            return "float"
        elif value.endswith('d') or value.endswith('D'):
            return "double"
        elif value.endswith('l') or value.endswith('L'):
            return "long"
        elif value.endswith('b') or value.endswith('B'):
            return "byte"
        elif value.endswith('s'):
            return "short"
        elif value == 'true' or value == 'false':
            return "boolean"
        elif '.' in value:
            return "double"  # Default decimal is double in Java
        else:
            try:
                int(value)
                return "int"
            except ValueError:
                return "unknown"
    
    def _infer_from_lambda(self, lam: LambdaExpression) -> str:
        """Infer type from lambda expression."""
        # Without context, we can't determine the functional interface type
        return "/* lambda */"
    
    def _infer_from_method_ref(self, ref: MethodReference) -> str:
        """Infer type from method reference."""
        return "/* method reference */"
    
    def _infer_from_iterable(self, var_decl: VarDeclaration, iterable):
        """Infer type from for-each iterable."""
        if isinstance(iterable, MethodInvocation):
            # e.g., list.stream() - would need method resolution
            var_decl.inferred_type = "/* iterable element */"
        elif isinstance(iterable, MemberReference):
            # e.g., items - would need variable type lookup
            var_decl.inferred_type = "/* iterable element */"
        elif isinstance(iterable, ClassCreator):
            # e.g., new ArrayList<>()
            type_name = self._infer_from_creator(iterable)
            # Remove the generic part to get element type
            if '<' in type_name:
                var_decl.inferred_type = f"/* element of {type_name} */"
            else:
                var_decl.inferred_type = "/* element */"
    
    def _convert_type_argument(self, java_type: str) -> str:
        """Convert a Java type to TypeScript equivalent for type arguments."""
        java_primitives = {
            'String': 'string',
            'Integer': 'number',
            'Long': 'number',
            'Short': 'number',
            'Byte': 'number',
            'Float': 'number',
            'Double': 'number',
            'Boolean': 'boolean',
            'Character': 'string',
            'Object': 'object',
        }
        return java_primitives.get(java_type, java_type)


class VarTypeInference:
    """Infers TypeScript types from Java var declarations."""
    
    # Mapping from Java types to TypeScript equivalents
    JAVA_TO_TS = {
        'int': 'number',
        'long': 'number',
        'short': 'number',
        'byte': 'number',
        'float': 'number',
        'double': 'number',
        'boolean': 'boolean',
        'char': 'string',
        'String': 'string',
        'Object': 'object',
        'Integer': 'number',
        'Long': 'number',
        'Short': 'number',
        'Byte': 'number',
        'Float': 'number',
        'Double': 'number',
        'Boolean': 'boolean',
        'Character': 'string',
    }
    
    # Java collection class to TypeScript equivalents
    JAVA_COLLECTIONS_TO_TS = {
        'ArrayList': 'Array',
        'LinkedList': 'Array',
        'List': 'Array',
        'Collection': 'Array',
        'HashSet': 'Set',
        'TreeSet': 'Set',
        'Set': 'Set',
        'HashMap': 'Map',
        'TreeMap': 'Map',
        'LinkedHashMap': 'Map',
        'Map': 'Map',
    }
    
    def __init__(self):
        self.type_context: Dict[str, str] = {}  # Variable name -> known type
    
    def infer_typescript_type(self, var_decl: VarDeclaration) -> str:
        """Infer the TypeScript type for a var declaration.
        
        Args:
            var_decl: The var declaration to infer type for
            
        Returns:
            TypeScript type string
        """
        if var_decl.inferred_type:
            return self._convert_to_typescript(var_decl.inferred_type)
        
        # Fallback based on initializer
        if var_decl.initializer_type == 'new':
            return self._infer_from_new_expression(var_decl.initializer)
        elif var_decl.initializer_type == 'literal':
            return self._infer_from_literal_string(var_decl.initializer)
        
        return "any"
    
    def _convert_to_typescript(self, java_type: str) -> str:
        """Convert Java type to TypeScript equivalent."""
        if not java_type or java_type.startswith('/*'):
            return "any"
        
        # Check for array
        is_array = '[]' in java_type
        base_type = java_type.replace('[]', '')
        
        # Handle generic types like List<String>
        if '<' in base_type:
            return self._convert_generic_type(base_type, is_array)
        
        # Check if it's a collection type first
        ts_type = self.JAVA_COLLECTIONS_TO_TS.get(base_type)
        if ts_type is None:
            # Simple type mapping
            ts_type = self.JAVA_TO_TS.get(base_type, base_type)
        
        if is_array:
            ts_type += "[]"
        
        return ts_type
    
    def _convert_generic_type(self, java_type: str, is_array: bool) -> str:
        """Convert Java generic type to TypeScript."""
        # Parse: List<String> -> Array<string>
        #        Map<String, Integer> -> Map<string, number>
        
        # Extract base type and type arguments
        match = r'(\w+)<(.+)>'
        import re
        m = re.match(match, java_type)
        
        if not m:
            return java_type  # Return as-is if can't parse
        
        base_type = m.group(1)
        args = m.group(2)
        
        # Convert base type using collections mapping
        base_type = self.JAVA_COLLECTIONS_TO_TS.get(base_type, base_type)
        
        # Convert type arguments
        converted_args = []
        for arg in args.split(','):
            arg = arg.strip()
            # Remove generic nesting if present
            if '<' in arg:
                arg = arg.split('<')[0]
            # Only lowercase Java wrapper types (String, Integer, etc.)
            # Keep custom types as-is
            java_primitives = ['String', 'Integer', 'Long', 'Short', 'Byte', 
                              'Float', 'Double', 'Boolean', 'Character',
                              'Object', 'Class']
            if arg in java_primitives:
                lower_arg = arg[0].lower() + arg[1:] if len(arg) > 1 else arg
                converted_args.append(self.JAVA_TO_TS.get(lower_arg, arg))
            else:
                converted_args.append(arg)
        
        result = f"{base_type}<{', '.join(converted_args)}>"
        
        if is_array:
            result += "[]"
        
        return result
    
    def _infer_from_new_expression(self, initializer: str) -> str:
        """Infer type from new expression."""
        if not initializer:
            return "any"
        
        import re
        
        # Handle common collection constructors - use collections mapping
        # Note: initializer may include () at the end
        if 'ArrayList' in initializer:
            if '<>' in initializer:  # Diamond operator
                return "Array<any>"
            # Try to extract type argument - include optional ()
            match = re.search(r'ArrayList<(.+?)>\s*\(?', initializer)
            if match:
                elem_type = self._convert_type_argument(match.group(1))
                return f"Array<{elem_type}>"
            return "Array<any>"
        
        elif 'HashMap' in initializer:
            if '<>' in initializer:
                return "Map<any, any>"
            match = re.search(r'HashMap<(.+?),(.+?)>\s*\(?', initializer)
            if match:
                key_type = self._convert_type_argument(match.group(1).strip())
                val_type = self._convert_type_argument(match.group(2).strip())
                return f"Map<{key_type}, {val_type}>"
            return "Map<any, any>"
        
        elif 'TreeMap' in initializer:
            if '<>' in initializer:
                return "Map<any, any>"
            match = re.search(r'TreeMap<(.+?),(.+?)>\s*\(?', initializer)
            if match:
                key_type = self._convert_type_argument(match.group(1).strip())
                val_type = self._convert_type_argument(match.group(2).strip())
                return f"Map<{key_type}, {val_type}>"
            return "Map<any, any>"
        
        elif 'LinkedHashMap' in initializer:
            if '<>' in initializer:
                return "Map<any, any>"
            match = re.search(r'LinkedHashMap<(.+?),(.+?)>\s*\(?', initializer)
            if match:
                key_type = self._convert_type_argument(match.group(1).strip())
                val_type = self._convert_type_argument(match.group(2).strip())
                return f"Map<{key_type}, {val_type}>"
            return "Map<any, any>"
        
        elif 'HashSet' in initializer:
            if '<>' in initializer:
                return "Set<any>"
            match = re.search(r'HashSet<(.+?)>\s*\(?', initializer)
            if match:
                elem_type = self._convert_type_argument(match.group(1))
                return f"Set<{elem_type}>"
            return "Set<any>"
        
        elif 'TreeSet' in initializer:
            if '<>' in initializer:
                return "Set<any>"
            match = re.search(r'TreeSet<(.+?)>\s*\(?', initializer)
            if match:
                elem_type = self._convert_type_argument(match.group(1))
                return f"Set<{elem_type}>"
            return "Set<any>"
        
        elif 'LinkedList' in initializer:
            return "Array<any>"
        
        # Generic class - use convert_generic_type for proper conversion
        if '<' in initializer:
            return self._convert_generic_type(initializer, False)
        
        return "any"
    
    def _convert_type_argument(self, java_type: str) -> str:
        """Convert a single type argument to TypeScript."""
        # Java wrapper types to lowercase
        java_primitives = {
            'String': 'string',
            'Integer': 'number',
            'Long': 'number',
            'Short': 'number',
            'Byte': 'number',
            'Float': 'number',
            'Double': 'number',
            'Boolean': 'boolean',
            'Character': 'string',
            'Object': 'object',
        }
        
        return java_primitives.get(java_type, java_type)
    
    def _infer_from_literal_string(self, initializer: str) -> str:
        """Infer type from literal string."""
        if not initializer:
            return "any"
        
        if initializer.startswith('"'):
            return "string"
        elif initializer.startswith("'"):
            return "string"
        elif initializer in ('true', 'false'):
            return "boolean"
        elif initializer.isdigit():
            return "number"
        else:
            return "any"


class VarScopeHandler:
    """Handles var declarations within scope."""
    
    def __init__(self):
        self.root_scope = VarScope("root")
        self.current_scope: VarScope = self.root_scope
        self._scope_counter = 0
    
    def enter_scope(self, scope_name: str = None):
        """Enter a new scope."""
        if scope_name is None:
            self._scope_counter += 1
            scope_name = f"scope_{self._scope_counter}"
        
        new_scope = VarScope(scope_name, self.current_scope)
        self.current_scope.children.append(new_scope)
        self.current_scope = new_scope
    
    def exit_scope(self):
        """Exit current scope and return to parent."""
        if self.current_scope.parent_scope:
            self.current_scope = self.current_scope.parent_scope
    
    def add_var(self, var_decl: VarDeclaration):
        """Add a var declaration to the current scope."""
        self.current_scope.add(var_decl)
    
    def get_var(self, name: str) -> Optional[VarDeclaration]:
        """Get a var declaration by name, searching parent scopes."""
        return self.current_scope.get(name)
    
    def get_all_vars(self) -> List[VarDeclaration]:
        """Get all var declarations in current scope (not parent)."""
        return list(self.current_scope.declarations.values())
    
    def get_all_scopes(self) -> List[VarScope]:
        """Get all scopes (for debugging)."""
        def collect(scope, result):
            result.append(scope)
            for child in scope.children:
                collect(child, result)
        
        result = []
        collect(self.root_scope, result)
        return result


def detect_and_convert(source_code: str) -> List[VarDeclaration]:
    """Convenience function to detect and infer types for var declarations.
    
    Args:
        source_code: Java source code string
        
    Returns:
        List of VarDeclaration objects with inferred TypeScript types
    """
    detector = VarDetector()
    inferrer = VarTypeInference()
    
    var_declarations = detector.detect_from_source(source_code)
    
    for var_decl in var_declarations:
        var_decl.inferred_type = inferrer.infer_typescript_type(var_decl)
    
    return var_declarations
