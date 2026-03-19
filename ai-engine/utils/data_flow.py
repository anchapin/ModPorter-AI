"""
Data Flow Analysis module for tracking variable mutations and control flow.

This module provides:
- Data flow graph construction
- Variable mutation tracking across statements
- Complex control flow handling (loops, conditionals)
- Mapping to Bedrock equivalent operations
"""

from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import javalang


class NodeType(Enum):
    """Types of nodes in the data flow graph."""
    VARIABLE_DECL = "variable_declaration"
    ASSIGNMENT = "assignment"
    METHOD_CALL = "method_call"
    FIELD_ACCESS = "field_access"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    RETURN = "return"
    PARAMETER = "parameter"


@dataclass
class DataFlowNode:
    """Represents a node in the data flow graph."""
    node_type: NodeType
    line: int
    value: str
    variables_read: List[str] = field(default_factory=list)
    variables_written: List[str] = field(default_factory=list)
    expression: str = ""
    

@dataclass
class VariableMutation:
    """Represents a mutation to a variable."""
    variable_name: str
    line: int
    mutation_type: str  # assignment, increment, decrement, compound
    value: str
    is_field: bool = False
    

@dataclass
class DataFlowGraph:
    """Represents the data flow graph for a method."""
    nodes: List[DataFlowNode] = field(default_factory=list)
    edges: List[Tuple[int, int]] = field(default_factory=list)
    variable_mutations: List[VariableMutation] = field(default_factory=list)
    entry_point: Optional[int] = None
    exit_points: List[int] = field(default_factory=list)


class DataFlowAnalyzer:
    """
    Analyzer for data flow in Java code.
    
    Constructs data flow graphs to track:
    - Variable definitions and uses
    - Method call side effects
    - Control flow dependencies
    - Data dependencies between statements
    """
    
    def __init__(self):
        self.logger = None
        self.current_graph: Optional[DataFlowGraph] = None
        self.current_method: str = ""
        
    def set_logger(self, logger):
        """Set the logger for this analyzer."""
        self.logger = logger
        
    def analyze_method(self, java_source: str, method_name: str = "") -> DataFlowGraph:
        """
        Analyze a method and construct its data flow graph.
        
        Args:
            java_source: Java source code
            method_name: Name of method to analyze (analyzes all if not specified)
            
        Returns:
            DataFlowGraph representing the method's data flow
        """
        graph = DataFlowGraph()
        
        try:
            tree = javalang.parse.parse(java_source)
            
            for path, node in tree:
                if isinstance(node, javalang.tree.MethodDeclaration):
                    if method_name and node.name != method_name:
                        continue
                        
                    self.current_method = node.name
                    
                    # Create entry point
                    entry_node = DataFlowNode(
                        node_type=NodeType.PARAMETER,
                        line=node.position,
                        value=f"entry:{node.name}"
                    )
                    graph.nodes.append(entry_node)
                    graph.entry_point = len(graph.nodes) - 1
                    
                    # Process method body
                    if node.body:
                        self._process_block(node.body, graph, 0)
                        
                    # Add exit points
                    graph.exit_points.append(len(graph.nodes) - 1)
                    
        except javalang.parser.JavaSyntaxError as e:
            if self.logger:
                self.logger.warning(f"Parse error in data flow analysis: {e}")
                
        self.current_graph = graph
        return graph
        
    def _process_block(self, block, graph: DataFlowGraph, parent_idx: int):
        """Process a block of statements."""
        prev_idx = parent_idx
        
        for statement in block:
            node_idx = self._process_statement(statement, graph)
            
            # Add edge from previous statement
            if node_idx is not None and prev_idx != node_idx:
                graph.edges.append((prev_idx, node_idx))
                prev_idx = node_idx
                
    def _process_statement(self, statement, graph: DataFlowGraph) -> Optional[int]:
        """Process a single statement and add to graph."""
        
        # Variable declaration
        if isinstance(statement, javalang.tree.VariableDeclaration):
            for declarator in statement.declarators:
                value = str(declarator.initializer) if declarator.initializer else ""
                
                node = DataFlowNode(
                    node_type=NodeType.VARIABLE_DECL,
                    line=statement.position,
                    value=declarator.name,
                    variables_written=[declarator.name],
                    variables_read=[value] if value else [],
                    expression=str(statement)
                )
                graph.nodes.append(node)
                
                # Track mutation
                mutation = VariableMutation(
                    variable_name=declarator.name,
                    line=statement.position,
                    mutation_type="declaration",
                    value=value
                )
                graph.variable_mutations.append(mutation)
                
                return len(graph.nodes) - 1
                
        # Assignment
        elif isinstance(statement, javalang.tree.Assignment):
            node = DataFlowNode(
                node_type=NodeType.ASSIGNMENT,
                line=statement.position,
                value=str(statement),
                variables_read=[str(statement.expressionl), str(statement.value)],
                variables_written=[str(statement.expressionl)],
                expression=str(statement)
            )
            graph.nodes.append(node)
            
            # Track mutation
            mutation = VariableMutation(
                variable_name=str(statement.expressionl),
                line=statement.position,
                mutation_type="assignment",
                value=str(statement.value)
            )
            graph.variable_mutations.append(mutation)
            
            return len(graph.nodes) - 1
            
        # Method invocation
        elif isinstance(statement, javalang.tree.MethodInvocation):
            args = [str(a) for a in statement.arguments] if statement.arguments else []
            
            node = DataFlowNode(
                node_type=NodeType.METHOD_CALL,
                line=statement.position,
                value=statement.member,
                variables_read=args,
                expression=str(statement)
            )
            graph.nodes.append(node)
            return len(graph.nodes) - 1
            
        # If statement
        elif isinstance(statement, javalang.tree.IfStatement):
            condition = str(statement.condition) if statement.condition else ""
            
            node = DataFlowNode(
                node_type=NodeType.CONDITIONAL,
                line=statement.position,
                value=f"if ({condition})",
                variables_read=[condition],
                expression=str(statement)
            )
            graph.nodes.append(node)
            idx = len(graph.nodes) - 1
            
            # Process then block
            if statement.then_statement:
                self._process_block([statement.then_statement], graph, idx)
                
            # Process else block
            if statement.else_statement:
                self._process_block([statement.else_statement], graph, idx)
                
            return idx
            
        # For loop
        elif isinstance(statement, javalang.tree.ForStatement):
            node = DataFlowNode(
                node_type=NodeType.LOOP,
                line=statement.position,
                value=f"for loop",
                expression=str(statement)
            )
            graph.nodes.append(node)
            idx = len(graph.nodes) - 1
            
            if statement.body:
                self._process_block([statement.body], graph, idx)
                
            return idx
            
        # While loop
        elif isinstance(statement, javalang.tree.WhileStatement):
            condition = str(statement.condition) if statement.condition else ""
            
            node = DataFlowNode(
                node_type=NodeType.LOOP,
                line=statement.position,
                value=f"while ({condition})",
                variables_read=[condition],
                expression=str(statement)
            )
            graph.nodes.append(node)
            idx = len(graph.nodes) - 1
            
            if statement.body:
                self._process_block([statement.body], graph, idx)
                
            return idx
            
        # Return statement
        elif isinstance(statement, javalang.tree.ReturnStatement):
            value = str(statement.expression) if statement.expression else ""
            
            node = DataFlowNode(
                node_type=NodeType.RETURN,
                line=statement.position,
                value=f"return {value}",
                variables_read=[value] if value else [],
                expression=str(statement)
            )
            graph.nodes.append(node)
            return len(graph.nodes) - 1
            
        return None
        
    def get_variable_dependencies(self, var_name: str) -> List[str]:
        """Get all variables that the given variable depends on."""
        if not self.current_graph:
            return []
            
        dependencies = set()
        
        for node in self.current_graph.nodes:
            if var_name in node.variables_written:
                dependencies.update(node.variables_read)
                
        return list(dependencies)
        
    def get_all_mutations(self, var_name: str) -> List[VariableMutation]:
        """Get all mutations for a specific variable."""
        if not self.current_graph:
            return []
            
        return [m for m in self.current_graph.variable_mutations 
                if m.variable_name == var_name]
        
    def map_to_bedrock_operations(self) -> List[str]:
        """
        Map data flow to Bedrock equivalent operations.
        
        Returns:
            List of Bedrock operation descriptions
        """
        if not self.current_graph:
            return []
            
        bedrock_ops = []
        
        for mutation in self.current_graph.variable_mutations:
            # Map Java types to Bedrock equivalents
            bedrock_op = self._map_mutation_to_bedrock(mutation)
            bedrock_ops.append(bedrock_op)
            
        return bedrock_ops
        
    def _map_mutation_to_bedrock(self, mutation: VariableMutation) -> str:
        """Map a Java variable mutation to Bedrock equivalent."""
        
        # Simple type mapping
        if mutation.mutation_type == "declaration":
            # Use let for JavaScript/Bedrock
            return f"let {mutation.variable_name} = {mutation.value};"
        elif mutation.mutation_type == "assignment":
            return f"{mutation.variable_name} = {mutation.value};"
        else:
            return f"// Complex mutation: {mutation.mutation_type}"


def create_data_flow_analyzer() -> DataFlowAnalyzer:
    """Factory function to create a data flow analyzer."""
    return DataFlowAnalyzer()
