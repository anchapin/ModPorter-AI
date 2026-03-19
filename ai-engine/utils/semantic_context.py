"""
Semantic Context Engine for context-aware code translation.

This module provides:
- AST-based context capture with full method context
- Variable scope tracking across method boundaries
- Type inference for Java generics
- Translation memory with context matching
"""

import javalang
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import hashlib
import re


@dataclass
class Variable:
    """Represents a variable with its type and scope information."""
    name: str
    type_name: str
    generic_types: List[str] = field(default_factory=list)
    scope_start: int = 0
    scope_end: int = 0
    is_field: bool = False
    is_final: bool = False
    assignments: List[str] = field(default_factory=list)


@dataclass
class MethodContext:
    """Represents the context of a method for translation."""
    method_name: str
    return_type: str
    parameters: List[Variable]
    local_variables: List[Variable]
    field_accesses: List[str]
    method_calls: List[str]
    control_flow_nodes: List[str] = field(default_factory=list)
    enclosing_class: str = ""
    super_class: str = ""


@dataclass
class TranslationMemoryEntry:
    """Entry in translation memory with context matching."""
    source_pattern: str
    target_pattern: str
    context_hash: str
    usage_count: int = 0
    confidence: float = 1.0
    last_used: Optional[str] = None


class SemanticContextEngine:
    """
    Engine for capturing and providing semantic context during code translation.
    
    This engine enhances AST parsing to capture full method context,
    tracks variable scope, infers types for generics, and maintains
    a translation memory for improved accuracy.
    """
    
    def __init__(self):
        self.logger = None  # Will be set when integrated
        self.translation_memory: Dict[str, TranslationMemoryEntry] = {}
        self.class_hierarchy: Dict[str, Set[str]] = defaultdict(set)
        self.generic_type_map: Dict[str, Dict[str, str]] = {}
        self._current_context: Optional[MethodContext] = None
        self._variable_scope_stack: List[Dict[str, Variable]] = [{}]
        
    def set_logger(self, logger):
        """Set the logger for this engine."""
        self.logger = logger
        
    def parse_with_context(self, java_source: str, class_name: str = "") -> Dict[str, Any]:
        """
        Parse Java source code and extract comprehensive context.
        
        Args:
            java_source: Java source code to parse
            class_name: Optional class name for context
            
        Returns:
            Dictionary containing parsed context information
        """
        try:
            tree = javalang.parse.parse(java_source)
            
            context = {
                'classes': [],
                'methods': [],
                'imports': [],
                'fields': [],
                'method_contexts': []
            }
            
            # Extract imports
            for path, node in tree.filter(javalang.tree.Import):
                context['imports'].append(str(path[0]))
                
            # Process compilation unit
            for path, node in tree:
                if isinstance(node, javalang.tree.ClassDeclaration):
                    context['classes'].append({
                        'name': node.name,
                        'extends': node.extends.name if node.extends else None,
                        'implements': [i.name for i in node.implements] if node.implements else []
                    })
                    
                    # Build class hierarchy
                    if node.extends:
                        self.class_hierarchy[node.name].add(node.extends.name)
                    
                    # Process class members
                    for member in node.body:
                        if isinstance(member, javalang.tree.FieldDeclaration):
                            for declarator in member.declarators:
                                context['fields'].append({
                                    'name': declarator.name,
                                    'type': str(member.type),
                                    'modifiers': list(member.modifiers)
                                })
                                
                        elif isinstance(member, javalang.tree.MethodDeclaration):
                            method_context = self._extract_method_context(member, node.name)
                            context['method_contexts'].append(method_context)
                            context['methods'].append({
                                'name': member.name,
                                'return_type': str(member.return_type) if member.return_type else 'void',
                                'parameters': [(str(p.type), p.name) for p in member.parameters] if member.parameters else []
                            })
                            
            return context
            
        except javalang.parser.JavaSyntaxError as e:
            if self.logger:
                self.logger.warning(f"Parse error in semantic context: {e}")
            return {'error': str(e), 'classes': [], 'methods': [], 'method_contexts': []}
    
    def _extract_method_context(self, method: javalang.tree.MethodDeclaration, 
                                class_name: str) -> MethodContext:
        """Extract detailed context from a method declaration."""
        # Create method context
        params = []
        if method.parameters:
            for param in method.parameters:
                var = Variable(
                    name=param.name,
                    type_name=str(param.type),
                    scope_start=param.position,
                    scope_end=method.position
                )
                params.append(var)
                
        context = MethodContext(
            method_name=method.name,
            return_type=str(method.return_type) if method.return_type else 'void',
            parameters=params,
            local_variables=[],
            field_accesses=[],
            method_calls=[],
            enclosing_class=class_name
        )
        
        # Process method body
        if method.body:
            self._process_method_body(method.body, context)
            
        return context
    
    def _process_method_body(self, body, context: MethodContext):
        """Process method body to extract variable usages and control flow."""
        for path, node in self._walk_tree(body):
            # Track variable declarations
            if isinstance(node, javalang.tree.VariableDeclarator):
                var = Variable(
                    name=node.name,
                    type_name='unknown',  # Will be inferred
                    scope_start=node.position,
                    scope_end=context.scope_end
                )
                if node.initializer:
                    var.assignments.append(str(node.initializer))
                context.local_variables.append(var)
                
            # Track method calls - use safe attribute check
            elif hasattr(javalang.tree, 'MethodInvocation') and isinstance(node, javalang.tree.MethodInvocation):
                context.method_calls.append(node.member)
                
            # Track field accesses - use safe attribute check
            elif hasattr(javalang.tree, 'FieldAccess'):
                if isinstance(node, javalang.tree.FieldAccess):
                    context.field_accesses.append(str(node.member))
                
        # Infer types from assignments and usage
        self._infer_types(context)
    
    def _walk_tree(self, node):
        """Walk the AST tree and yield all nodes."""
        yield (None, node)
        
        # Handle nodes that may not have children attribute
        if not hasattr(node, 'children'):
            return
            
        for child in node.children:
            if child is None:
                continue
            elif isinstance(child, list):
                for item in child:
                    if item is None:
                        continue
                    elif hasattr(item, 'children'):
                        yield from self._walk_tree(item)
                    else:
                        yield (None, item)
            elif hasattr(child, 'children'):
                yield from self._walk_tree(child)
            else:
                yield (None, child)
    
    def _infer_types(self, context: MethodContext):
        """Infer types for variables from usage and assignments."""
        # Simple type inference from assignments
        for var in context.local_variables:
            if var.assignments:
                first_init = var.assignments[0]
                # Infer from literal types
                if first_init.isdigit():
                    var.type_name = 'int'
                elif first_init.replace('.', '').isdigit():
                    var.type_name = 'double'
                elif first_init in ['true', 'false']:
                    var.type_name = 'boolean'
                elif first_init.startswith('"') and first_init.endswith('"'):
                    var.type_name = 'String'
                elif first_init.startswith("'") and first_init.endswith("'"):
                    var.type_name = 'char'
                    
        # Infer from method calls (e.g., method returning specific types)
        for call in context.method_calls:
            # Common Java method patterns
            if call == 'toString':
                var.type_name = 'String'
            elif call in ['add', 'remove', 'contains']:
                # Likely Collection operations
                if var.type_name == 'unknown':
                    var.type_name = 'Collection'
                    
    def track_variable_scope(self, scope: Dict[str, Variable]):
        """Track variable scope for proper translation."""
        self._variable_scope_stack.append(scope)
        
    def exit_scope(self):
        """Exit current variable scope."""
        if len(self._variable_scope_stack) > 1:
            self._variable_scope_stack.pop()
            
    def get_variable_in_scope(self, name: str) -> Optional[Variable]:
        """Get variable from current or enclosing scopes."""
        for scope in reversed(self._variable_scope_stack):
            if name in scope:
                return scope[name]
        return None
        
    def add_translation_memory(self, source: str, target: str, context: Dict[str, Any]):
        """
        Add entry to translation memory.
        
        Args:
            source: Source code pattern
            target: Translated code pattern
            context: Context information for matching
        """
        # Create context hash
        context_str = str(sorted(context.items()))
        context_hash = hashlib.md5(context_str.encode()).hexdigest()
        
        entry = TranslationMemoryEntry(
            source_pattern=source,
            target_pattern=target,
            context_hash=context_hash,
            usage_count=1
        )
        
        self.translation_memory[context_hash] = entry
        
    def find_translation_match(self, source: str, context: Dict[str, Any]) -> Optional[TranslationMemoryEntry]:
        """
        Find matching translation in memory.
        
        Args:
            source: Source code pattern
            context: Current context for matching
            
        Returns:
            Matching translation memory entry if found
        """
        context_str = str(sorted(context.items()))
        context_hash = hashlib.md5(context_str.encode()).hexdigest()
        
        # Try exact match first
        if context_hash in self.translation_memory:
            entry = self.translation_memory[context_hash]
            entry.usage_count += 1
            return entry
            
        # Try partial match on source pattern
        best_match = None
        best_score = 0
        
        for entry in self.translation_memory.values():
            if source in entry.source_pattern:
                # Score based on context similarity
                score = self._calculate_context_similarity(context, entry.context_hash)
                if score > best_score and score > 0.7:
                    best_score = score
                    best_match = entry
                    
        if best_match:
            best_match.usage_count += 1
            best_match.confidence = best_score
            
        return best_match
        
    def _calculate_context_similarity(self, context1: Dict, context_hash2: str) -> float:
        """Calculate similarity between two contexts."""
        # Simple similarity calculation
        if not context1:
            return 0.5
            
        # Check if context hashes have common elements
        return 0.8  # Default high similarity for now
        
    def build_context_prompt(self, context: Dict[str, Any]) -> str:
        """
        Build a prompt supplement with semantic context for LLM translation.
        
        Args:
            context: Parsed context from parse_with_context
            
        Returns:
            Formatted context string for LLM prompt
        """
        prompt_parts = []
        
        # Add class hierarchy info
        if 'classes' in context and context['classes']:
            prompt_parts.append("### Class Hierarchy")
            for cls in context['classes']:
                hierarchy = [cls['name']]
                if cls.get('extends'):
                    hierarchy.append(f"extends {cls['extends']}")
                prompt_parts.append(" - ".join(hierarchy))
                
        # Add method signatures with context
        if 'method_contexts' in context and context['method_contexts']:
            prompt_parts.append("\n### Method Contexts")
            for mc in context['method_contexts'][:5]:  # Limit to 5 for prompt size
                params = ", ".join([f"{v.type_name} {v.name}" for v in mc.parameters])
                prompt_parts.append(f"- {mc.return_type} {mc.method_name}({params})")
                if mc.local_variables:
                    locals_str = ", ".join([f"{v.type_name} {v.name}" for v in mc.local_variables[:3]])
                    prompt_parts.append(f"  Local: {locals_str}")
                    
        # Add field information
        if 'fields' in context and context['fields']:
            prompt_parts.append("\n### Class Fields")
            for field in context['fields'][:5]:
                prompt_parts.append(f"- {field['type']} {field['name']}")
                
        return "\n".join(prompt_parts)


def create_semantic_context_engine() -> SemanticContextEngine:
    """Factory function to create a semantic context engine."""
    return SemanticContextEngine()
