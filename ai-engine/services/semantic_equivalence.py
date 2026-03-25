"""
Semantic Equivalence Checker for Java and Bedrock code comparison

Implements:
- Data Flow Graph (DFG) construction
- Control Flow Graph (CFG) construction
- Graph-based semantic comparison
- Equivalence scoring
"""

import logging
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
<<<<<<< HEAD
=======
import hashlib

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Types of nodes in data/control flow graphs."""
<<<<<<< HEAD

=======
    ENTRY = "entry"
    EXIT = "exit"
    ASSIGNMENT = "assignment"
    CONDITION = "condition"
    LOOP = "loop"
    METHOD_CALL = "method_call"
    FIELD_ACCESS = "field_access"
    RETURN = "return"
    BRANCH = "branch"
    MERGE = "merge"


@dataclass
class DFGNode:
    """Node in a Data Flow Graph."""
<<<<<<< HEAD

=======
    id: str
    node_type: NodeType
    variable: Optional[str] = None
    value: Optional[str] = None
    operation: Optional[str] = None
    line_number: int = 0
    dependencies: List[str] = field(default_factory=list)
<<<<<<< HEAD

=======
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.node_type.value,
            "variable": self.variable,
            "value": self.value,
            "operation": self.operation,
            "line": self.line_number,
            "dependencies": self.dependencies,
        }


@dataclass
class CFGNode:
    """Node in a Control Flow Graph."""
<<<<<<< HEAD

=======
    id: str
    node_type: NodeType
    statement: Optional[str] = None
    successors: List[str] = field(default_factory=list)
    predecessors: List[str] = field(default_factory=list)
    line_number: int = 0
<<<<<<< HEAD

=======
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.node_type.value,
            "statement": self.statement,
            "successors": self.successors,
            "predecessors": self.predecessors,
            "line": self.line_number,
        }


@dataclass
class DataFlowGraph:
    """Complete data flow graph for a code snippet."""
<<<<<<< HEAD

=======
    nodes: Dict[str, DFGNode] = field(default_factory=dict)
    entry_node: Optional[str] = None
    exit_node: Optional[str] = None
    variables: Set[str] = field(default_factory=set)
<<<<<<< HEAD

=======
    
    def add_node(self, node: DFGNode):
        """Add node to the graph."""
        self.nodes[node.id] = node
        if node.variable:
            self.variables.add(node.variable)
<<<<<<< HEAD

    def get_node(self, node_id: str) -> Optional[DFGNode]:
        """Get node by ID."""
        return self.nodes.get(node_id)

    def get_variable_definitions(self, variable: str) -> List[DFGNode]:
        """Get all nodes that define a variable."""
        return [
            node
            for node in self.nodes.values()
            if node.variable == variable and node.operation == "define"
        ]

    def get_variable_uses(self, variable: str) -> List[DFGNode]:
        """Get all nodes that use a variable."""
        return [
            node
            for node in self.nodes.values()
=======
    
    def get_node(self, node_id: str) -> Optional[DFGNode]:
        """Get node by ID."""
        return self.nodes.get(node_id)
    
    def get_variable_definitions(self, variable: str) -> List[DFGNode]:
        """Get all nodes that define a variable."""
        return [
            node for node in self.nodes.values()
            if node.variable == variable and node.operation == "define"
        ]
    
    def get_variable_uses(self, variable: str) -> List[DFGNode]:
        """Get all nodes that use a variable."""
        return [
            node for node in self.nodes.values()
            if node.variable == variable and node.operation == "use"
        ]


@dataclass
class ControlFlowGraph:
    """Complete control flow graph for a code snippet."""
<<<<<<< HEAD

=======
    nodes: Dict[str, CFGNode] = field(default_factory=dict)
    entry_node: Optional[str] = None
    exit_node: Optional[str] = None
    loops: List[List[str]] = field(default_factory=list)
<<<<<<< HEAD
    branches: List[Tuple[str, str, str]] = field(
        default_factory=list
    )  # (condition, true_branch, false_branch)

    def add_node(self, node: CFGNode):
        """Add node to the graph."""
        self.nodes[node.id] = node

=======
    branches: List[Tuple[str, str, str]] = field(default_factory=list)  # (condition, true_branch, false_branch)
    
    def add_node(self, node: CFGNode):
        """Add node to the graph."""
        self.nodes[node.id] = node
    
    def add_edge(self, from_id: str, to_id: str):
        """Add edge between nodes."""
        if from_id in self.nodes and to_id in self.nodes:
            self.nodes[from_id].successors.append(to_id)
            self.nodes[to_id].predecessors.append(from_id)
<<<<<<< HEAD

=======
    
    def get_paths(self) -> List[List[str]]:
        """Get all paths from entry to exit."""
        if not self.entry_node or not self.exit_node:
            return []
<<<<<<< HEAD

        paths = []
        self._find_paths(self.entry_node, self.exit_node, [], paths)
        return paths

    def _find_paths(self, current: str, target: str, path: List[str], all_paths: List[List[str]]):
        """Recursively find all paths."""
        path = path + [current]

        if current == target:
            all_paths.append(path)
            return

=======
        
        paths = []
        self._find_paths(self.entry_node, self.exit_node, [], paths)
        return paths
    
    def _find_paths(self, current: str, target: str, path: List[str], all_paths: List[List[str]]):
        """Recursively find all paths."""
        path = path + [current]
        
        if current == target:
            all_paths.append(path)
            return
        
        node = self.nodes.get(current)
        if node:
            for successor in node.successors:
                if successor not in path:  # Avoid cycles
                    self._find_paths(successor, target, path, all_paths)


@dataclass
class EquivalenceResult:
    """Result of semantic equivalence checking."""
<<<<<<< HEAD

=======
    equivalent: bool
    confidence: float  # 0.0 to 1.0
    dfg_similarity: float
    cfg_similarity: float
    differences: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
<<<<<<< HEAD

=======
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "equivalent": self.equivalent,
            "confidence": self.confidence,
            "dfg_similarity": self.dfg_similarity,
            "cfg_similarity": self.cfg_similarity,
            "differences": self.differences,
            "warnings": self.warnings,
        }


class DataFlowAnalyzer:
    """
    Analyzes code to build Data Flow Graphs.
<<<<<<< HEAD

=======
    
    Tracks:
    - Variable definitions (defs)
    - Variable uses (uses)
    - Data dependencies
    """
<<<<<<< HEAD

    def __init__(self):
        self.dfg = DataFlowGraph()
        self._node_counter = 0

=======
    
    def __init__(self):
        self.dfg = DataFlowGraph()
        self._node_counter = 0
    
    def _new_id(self) -> str:
        """Generate unique node ID."""
        self._node_counter += 1
        return f"n{self._node_counter}"
<<<<<<< HEAD

    def analyze_java(self, source_code: str, ast: Optional[Any] = None) -> DataFlowGraph:
        """
        Build data flow graph from Java source code.

        Args:
            source_code: Java source code
            ast: Optional pre-parsed AST

=======
    
    def analyze_java(self, source_code: str, ast: Optional[Any] = None) -> DataFlowGraph:
        """
        Build data flow graph from Java source code.
        
        Args:
            source_code: Java source code
            ast: Optional pre-parsed AST
            
        Returns:
            DataFlowGraph for the code
        """
        self.dfg = DataFlowGraph()
        self._node_counter = 0
<<<<<<< HEAD

=======
        
        # Create entry node
        entry = DFGNode(id=self._new_id(), node_type=NodeType.ENTRY, line_number=0)
        self.dfg.add_node(entry)
        self.dfg.entry_node = entry.id
<<<<<<< HEAD

        # Parse and analyze (simplified - would use tree-sitter AST in production)
        lines = source_code.split("\n")
        for line_num, line in enumerate(lines, 1):
            self._analyze_java_line(line.strip(), line_num)

=======
        
        # Parse and analyze (simplified - would use tree-sitter AST in production)
        lines = source_code.split('\n')
        for line_num, line in enumerate(lines, 1):
            self._analyze_java_line(line.strip(), line_num)
        
        # Create exit node
        exit_node = DFGNode(id=self._new_id(), node_type=NodeType.EXIT, line_number=len(lines))
        self.dfg.add_node(exit_node)
        self.dfg.exit_node = exit_node.id
<<<<<<< HEAD

        return self.dfg

    def _analyze_java_line(self, line: str, line_num: int):
        """Analyze a single Java line for data flow."""
        if not line or line.startswith("//"):
            return

        # Variable assignment: type name = value;
        if "=" in line and not line.startswith("if") and not line.startswith("while"):
            parts = line.split("=")
            if len(parts) >= 2:
                # Extract variable name (simplified)
                var_part = parts[0].strip()
                var_name = var_part.split()[-1] if " " in var_part else var_part
                var_name = var_name.replace(";", "").strip()

=======
        
        return self.dfg
    
    def _analyze_java_line(self, line: str, line_num: int):
        """Analyze a single Java line for data flow."""
        if not line or line.startswith('//'):
            return
        
        # Variable assignment: type name = value;
        if '=' in line and not line.startswith('if') and not line.startswith('while'):
            parts = line.split('=')
            if len(parts) >= 2:
                # Extract variable name (simplified)
                var_part = parts[0].strip()
                var_name = var_part.split()[-1] if ' ' in var_part else var_part
                var_name = var_name.replace(';', '').strip()
                
                # Definition node
                def_node = DFGNode(
                    id=self._new_id(),
                    node_type=NodeType.ASSIGNMENT,
                    variable=var_name,
                    operation="define",
<<<<<<< HEAD
                    value=parts[1].strip().rstrip(";"),
                    line_number=line_num,
                )
                self.dfg.add_node(def_node)

                # Check for uses in the value
                self._extract_uses(parts[1], line_num)

        # Method call: obj.method() or method()
        if "(" in line and ")" in line:
            self._extract_method_call(line, line_num)

        # Field access: obj.field
        if "." in line:
            self._extract_field_access(line, line_num)

    def _extract_uses(self, expression: str, line_num: int):
        """Extract variable uses from an expression."""
        # Simple tokenization (would be more sophisticated with AST)
        tokens = expression.replace("(", " ").replace(")", " ").replace(".", " ").split()
        for token in tokens:
            token = token.strip(";,").strip()
=======
                    value=parts[1].strip().rstrip(';'),
                    line_number=line_num,
                )
                self.dfg.add_node(def_node)
                
                # Check for uses in the value
                self._extract_uses(parts[1], line_num)
        
        # Method call: obj.method() or method()
        if '(' in line and ')' in line:
            self._extract_method_call(line, line_num)
        
        # Field access: obj.field
        if '.' in line:
            self._extract_field_access(line, line_num)
    
    def _extract_uses(self, expression: str, line_num: int):
        """Extract variable uses from an expression."""
        # Simple tokenization (would be more sophisticated with AST)
        tokens = expression.replace('(', ' ').replace(')', ' ').replace('.', ' ').split()
        for token in tokens:
            token = token.strip(';,').strip()
            if token and token[0].islower() and not self._is_keyword(token):
                use_node = DFGNode(
                    id=self._new_id(),
                    node_type=NodeType.ASSIGNMENT,
                    variable=token,
                    operation="use",
                    line_number=line_num,
                )
                self.dfg.add_node(use_node)
<<<<<<< HEAD

    def _extract_method_call(self, line: str, line_num: int):
        """Extract method call information."""
        # Find method name
        paren_idx = line.find("(")
=======
    
    def _extract_method_call(self, line: str, line_num: int):
        """Extract method call information."""
        # Find method name
        paren_idx = line.find('(')
        if paren_idx > 0:
            method_name = line[:paren_idx].strip().split()[-1]
            call_node = DFGNode(
                id=self._new_id(),
                node_type=NodeType.METHOD_CALL,
                operation=f"call:{method_name}",
                line_number=line_num,
            )
            self.dfg.add_node(call_node)
<<<<<<< HEAD

    def _extract_field_access(self, line: str, line_num: int):
        """Extract field access information."""
        parts = line.split(".")
        if len(parts) >= 2:
            field_name = parts[-1].split()[0].strip(";,")
=======
    
    def _extract_field_access(self, line: str, line_num: int):
        """Extract field access information."""
        parts = line.split('.')
        if len(parts) >= 2:
            field_name = parts[-1].split()[0].strip(';,')
            access_node = DFGNode(
                id=self._new_id(),
                node_type=NodeType.FIELD_ACCESS,
                variable=field_name,
                operation="access",
                line_number=line_num,
            )
            self.dfg.add_node(access_node)
<<<<<<< HEAD

    def _is_keyword(self, token: str) -> bool:
        """Check if token is a Java keyword."""
        keywords = {
            "if",
            "else",
            "while",
            "for",
            "return",
            "class",
            "public",
            "private",
            "protected",
            "static",
            "void",
            "int",
            "String",
            "boolean",
            "new",
            "this",
            "super",
            "extends",
            "implements",
            "try",
            "catch",
            "finally",
            "throw",
        }
        return token in keywords

    def analyze_javascript(self, source_code: str) -> DataFlowGraph:
        """
        Build data flow graph from JavaScript source code.

=======
    
    def _is_keyword(self, token: str) -> bool:
        """Check if token is a Java keyword."""
        keywords = {
            'if', 'else', 'while', 'for', 'return', 'class', 'public', 'private',
            'protected', 'static', 'void', 'int', 'String', 'boolean', 'new', 'this',
            'super', 'extends', 'implements', 'try', 'catch', 'finally', 'throw',
        }
        return token in keywords
    
    def analyze_javascript(self, source_code: str) -> DataFlowGraph:
        """
        Build data flow graph from JavaScript source code.
        
        Similar to Java analysis but adapted for JavaScript syntax.
        """
        self.dfg = DataFlowGraph()
        self._node_counter = 0
<<<<<<< HEAD

=======
        
        # Create entry node
        entry = DFGNode(id=self._new_id(), node_type=NodeType.ENTRY, line_number=0)
        self.dfg.add_node(entry)
        self.dfg.entry_node = entry.id
<<<<<<< HEAD

        # Parse and analyze
        lines = source_code.split("\n")
        for line_num, line in enumerate(lines, 1):
            self._analyze_javascript_line(line.strip(), line_num)

=======
        
        # Parse and analyze
        lines = source_code.split('\n')
        for line_num, line in enumerate(lines, 1):
            self._analyze_javascript_line(line.strip(), line_num)
        
        # Create exit node
        exit_node = DFGNode(id=self._new_id(), node_type=NodeType.EXIT, line_number=len(lines))
        self.dfg.add_node(exit_node)
        self.dfg.exit_node = exit_node.id
<<<<<<< HEAD

        return self.dfg

    def _analyze_javascript_line(self, line: str, line_num: int):
        """Analyze a single JavaScript line for data flow."""
        if not line or line.startswith("//"):
            return

        # Variable declaration: let/const/var name = value
        if any(line.startswith(kw) for kw in ["let ", "const ", "var "]) or "=" in line:
            # Extract variable name
            line_clean = line.lstrip("let ").lstrip("const ").lstrip("var ")
            if "=" in line_clean:
                var_name = line_clean.split("=")[0].strip()

=======
        
        return self.dfg
    
    def _analyze_javascript_line(self, line: str, line_num: int):
        """Analyze a single JavaScript line for data flow."""
        if not line or line.startswith('//'):
            return
        
        # Variable declaration: let/const/var name = value
        if any(line.startswith(kw) for kw in ['let ', 'const ', 'var ']) or '=' in line:
            # Extract variable name
            line_clean = line.lstrip('let ').lstrip('const ').lstrip('var ')
            if '=' in line_clean:
                var_name = line_clean.split('=')[0].strip()
                
                def_node = DFGNode(
                    id=self._new_id(),
                    node_type=NodeType.ASSIGNMENT,
                    variable=var_name,
                    operation="define",
<<<<<<< HEAD
                    value=line_clean.split("=", 1)[1].strip().rstrip(";"),
                    line_number=line_num,
                )
                self.dfg.add_node(def_node)
                self._extract_uses(line_clean.split("=", 1)[1], line_num)

        # Function call
        if "(" in line and ")" in line:
=======
                    value=line_clean.split('=', 1)[1].strip().rstrip(';'),
                    line_number=line_num,
                )
                self.dfg.add_node(def_node)
                self._extract_uses(line_clean.split('=', 1)[1], line_num)
        
        # Function call
        if '(' in line and ')' in line:
            self._extract_method_call(line, line_num)


class ControlFlowAnalyzer:
    """
    Analyzes code to build Control Flow Graphs.
<<<<<<< HEAD

=======
    
    Tracks:
    - Basic blocks
    - Branches (if/else)
    - Loops (for/while)
    - Entry/exit points
    """
<<<<<<< HEAD

    def __init__(self):
        self.cfg = ControlFlowGraph()
        self._node_counter = 0

=======
    
    def __init__(self):
        self.cfg = ControlFlowGraph()
        self._node_counter = 0
    
    def _new_id(self) -> str:
        """Generate unique node ID."""
        self._node_counter += 1
        return f"b{self._node_counter}"
<<<<<<< HEAD

=======
    
    def analyze_java(self, source_code: str) -> ControlFlowGraph:
        """Build control flow graph from Java source code."""
        self.cfg = ControlFlowGraph()
        self._node_counter = 0
<<<<<<< HEAD

=======
        
        # Create entry node
        entry = CFGNode(id=self._new_id(), node_type=NodeType.ENTRY, line_number=0)
        self.cfg.add_node(entry)
        self.cfg.entry_node = entry.id
<<<<<<< HEAD

        # Analyze lines
        lines = source_code.split("\n")
        prev_node_id = entry.id

=======
        
        # Analyze lines
        lines = source_code.split('\n')
        prev_node_id = entry.id
        
        for line_num, line in enumerate(lines, 1):
            node = self._analyze_java_line(line.strip(), line_num)
            if node:
                self.cfg.add_node(node)
                self.cfg.add_edge(prev_node_id, node.id)
                prev_node_id = node.id
<<<<<<< HEAD

=======
        
        # Create exit node
        exit_node = CFGNode(id=self._new_id(), node_type=NodeType.EXIT, line_number=len(lines))
        self.cfg.add_node(exit_node)
        if prev_node_id:
            self.cfg.add_edge(prev_node_id, exit_node.id)
        self.cfg.exit_node = exit_node.id
<<<<<<< HEAD

        return self.cfg

    def _analyze_java_line(self, line: str, line_num: int) -> Optional[CFGNode]:
        """Analyze a single Java line for control flow."""
        if not line or line.startswith("//"):
            return None

        # If statement
        if line.startswith("if (") or line.startswith("if("):
=======
        
        return self.cfg
    
    def _analyze_java_line(self, line: str, line_num: int) -> Optional[CFGNode]:
        """Analyze a single Java line for control flow."""
        if not line or line.startswith('//'):
            return None
        
        # If statement
        if line.startswith('if (') or line.startswith('if('):
            branch_node = CFGNode(
                id=self._new_id(),
                node_type=NodeType.BRANCH,
                statement=line,
                line_number=line_num,
            )
            self.cfg.branches.append((line, "true_branch", "false_branch"))
            return branch_node
<<<<<<< HEAD

        # Loop
        if line.startswith("while (") or line.startswith("for ("):
=======
        
        # Loop
        if line.startswith('while (') or line.startswith('for ('):
            loop_node = CFGNode(
                id=self._new_id(),
                node_type=NodeType.LOOP,
                statement=line,
                line_number=line_num,
            )
            return loop_node
<<<<<<< HEAD

        # Return
        if line.startswith("return"):
=======
        
        # Return
        if line.startswith('return'):
            return CFGNode(
                id=self._new_id(),
                node_type=NodeType.RETURN,
                statement=line,
                line_number=line_num,
            )
<<<<<<< HEAD

=======
        
        # Regular statement
        return CFGNode(
            id=self._new_id(),
            node_type=NodeType.ASSIGNMENT,
            statement=line,
            line_number=line_num,
        )
<<<<<<< HEAD

=======
    
    def analyze_javascript(self, source_code: str) -> ControlFlowGraph:
        """Build control flow graph from JavaScript source code."""
        self.cfg = ControlFlowGraph()
        self._node_counter = 0
<<<<<<< HEAD

=======
        
        # Create entry node
        entry = CFGNode(id=self._new_id(), node_type=NodeType.ENTRY, line_number=0)
        self.cfg.add_node(entry)
        self.cfg.entry_node = entry.id
<<<<<<< HEAD

        # Analyze lines
        lines = source_code.split("\n")
        prev_node_id = entry.id

=======
        
        # Analyze lines
        lines = source_code.split('\n')
        prev_node_id = entry.id
        
        for line_num, line in enumerate(lines, 1):
            node = self._analyze_javascript_line(line.strip(), line_num)
            if node:
                self.cfg.add_node(node)
                self.cfg.add_edge(prev_node_id, node.id)
                prev_node_id = node.id
<<<<<<< HEAD

=======
        
        # Create exit node
        exit_node = CFGNode(id=self._new_id(), node_type=NodeType.EXIT, line_number=len(lines))
        self.cfg.add_node(exit_node)
        if prev_node_id:
            self.cfg.add_edge(prev_node_id, exit_node.id)
        self.cfg.exit_node = exit_node.id
<<<<<<< HEAD

        return self.cfg

    def _analyze_javascript_line(self, line: str, line_num: int) -> Optional[CFGNode]:
        """Analyze a single JavaScript line for control flow."""
        if not line or line.startswith("//"):
            return None

        # If statement
        if line.startswith("if (") or line.startswith("if("):
=======
        
        return self.cfg
    
    def _analyze_javascript_line(self, line: str, line_num: int) -> Optional[CFGNode]:
        """Analyze a single JavaScript line for control flow."""
        if not line or line.startswith('//'):
            return None
        
        # If statement
        if line.startswith('if (') or line.startswith('if('):
            branch_node = CFGNode(
                id=self._new_id(),
                node_type=NodeType.BRANCH,
                statement=line,
                line_number=line_num,
            )
            self.cfg.branches.append((line, "true_branch", "false_branch"))
            return branch_node
<<<<<<< HEAD

        # Loop
        if line.startswith("while (") or line.startswith("for ("):
=======
        
        # Loop
        if line.startswith('while (') or line.startswith('for ('):
            loop_node = CFGNode(
                id=self._new_id(),
                node_type=NodeType.LOOP,
                statement=line,
                line_number=line_num,
            )
            return loop_node
<<<<<<< HEAD

        # Return
        if line.startswith("return"):
=======
        
        # Return
        if line.startswith('return'):
            return CFGNode(
                id=self._new_id(),
                node_type=NodeType.RETURN,
                statement=line,
                line_number=line_num,
            )
<<<<<<< HEAD

=======
        
        # Regular statement
        return CFGNode(
            id=self._new_id(),
            node_type=NodeType.ASSIGNMENT,
            statement=line,
            line_number=line_num,
        )


class SemanticEquivalenceChecker:
    """
    Checks semantic equivalence between Java and Bedrock (JavaScript) code.
<<<<<<< HEAD

=======
    
    Compares:
    - Data flow graphs (variable definitions and uses)
    - Control flow graphs (branches, loops, paths)
    - Overall behavioral equivalence
    """
<<<<<<< HEAD

    def __init__(self):
        self.dfg_analyzer = DataFlowAnalyzer()
        self.cfg_analyzer = ControlFlowAnalyzer()

=======
    
    def __init__(self):
        self.dfg_analyzer = DataFlowAnalyzer()
        self.cfg_analyzer = ControlFlowAnalyzer()
    
    def check_equivalence(
        self,
        java_code: str,
        bedrock_code: str,
    ) -> EquivalenceResult:
        """
        Check semantic equivalence between Java and Bedrock code.
<<<<<<< HEAD

        Args:
            java_code: Original Java source code
            bedrock_code: Converted Bedrock JavaScript code

=======
        
        Args:
            java_code: Original Java source code
            bedrock_code: Converted Bedrock JavaScript code
            
        Returns:
            EquivalenceResult with confidence score and differences
        """
        logger.info("Checking semantic equivalence...")
<<<<<<< HEAD

        # Build data flow graphs
        java_dfg = self.dfg_analyzer.analyze_java(java_code)
        bedrock_dfg = self.dfg_analyzer.analyze_javascript(bedrock_code)

        # Build control flow graphs
        java_cfg = self.cfg_analyzer.analyze_java(java_code)
        bedrock_cfg = self.cfg_analyzer.analyze_javascript(bedrock_code)

        # Compare graphs
        dfg_similarity = self._compare_dfgs(java_dfg, bedrock_dfg)
        cfg_similarity = self._compare_cfgs(java_cfg, bedrock_cfg)

        # Calculate overall confidence
        confidence = (dfg_similarity + cfg_similarity) / 2

=======
        
        # Build data flow graphs
        java_dfg = self.dfg_analyzer.analyze_java(java_code)
        bedrock_dfg = self.dfg_analyzer.analyze_javascript(bedrock_code)
        
        # Build control flow graphs
        java_cfg = self.cfg_analyzer.analyze_java(java_code)
        bedrock_cfg = self.cfg_analyzer.analyze_javascript(bedrock_code)
        
        # Compare graphs
        dfg_similarity = self._compare_dfgs(java_dfg, bedrock_dfg)
        cfg_similarity = self._compare_cfgs(java_cfg, bedrock_cfg)
        
        # Calculate overall confidence
        confidence = (dfg_similarity + cfg_similarity) / 2
        
        # Determine equivalence
        equivalent = confidence >= 0.8
        differences = self._find_differences(java_dfg, bedrock_dfg, java_cfg, bedrock_cfg)
        warnings = self._generate_warnings(java_dfg, bedrock_dfg)
<<<<<<< HEAD

=======
        
        result = EquivalenceResult(
            equivalent=equivalent,
            confidence=confidence,
            dfg_similarity=dfg_similarity,
            cfg_similarity=cfg_similarity,
            differences=differences,
            warnings=warnings,
        )
<<<<<<< HEAD

        logger.info(
            f"Equivalence check complete: equivalent={equivalent}, confidence={confidence:.2f}"
        )
        return result

=======
        
        logger.info(f"Equivalence check complete: equivalent={equivalent}, confidence={confidence:.2f}")
        return result
    
    def _compare_dfgs(self, java_dfg: DataFlowGraph, bedrock_dfg: DataFlowGraph) -> float:
        """Compare data flow graphs and return similarity score."""
        if not java_dfg.variables and not bedrock_dfg.variables:
            return 1.0
<<<<<<< HEAD

        # Compare variable sets
        java_vars = java_dfg.variables
        bedrock_vars = bedrock_dfg.variables

=======
        
        # Compare variable sets
        java_vars = java_dfg.variables
        bedrock_vars = bedrock_dfg.variables
        
        # Jaccard similarity for variables
        intersection = len(java_vars & bedrock_vars)
        union = len(java_vars | bedrock_vars)
        var_similarity = intersection / union if union > 0 else 1.0
<<<<<<< HEAD

        # Compare node counts (normalized)
        java_nodes = len(java_dfg.nodes)
        bedrock_nodes = len(bedrock_dfg.nodes)
        node_similarity = (
            min(java_nodes, bedrock_nodes) / max(java_nodes, bedrock_nodes)
            if max(java_nodes, bedrock_nodes) > 0
            else 1.0
        )

        # Weighted average
        return 0.6 * var_similarity + 0.4 * node_similarity

=======
        
        # Compare node counts (normalized)
        java_nodes = len(java_dfg.nodes)
        bedrock_nodes = len(bedrock_dfg.nodes)
        node_similarity = min(java_nodes, bedrock_nodes) / max(java_nodes, bedrock_nodes) if max(java_nodes, bedrock_nodes) > 0 else 1.0
        
        # Weighted average
        return 0.6 * var_similarity + 0.4 * node_similarity
    
    def _compare_cfgs(self, java_cfg: ControlFlowGraph, bedrock_cfg: ControlFlowGraph) -> float:
        """Compare control flow graphs and return similarity score."""
        # Compare branch counts
        java_branches = len(java_cfg.branches)
        bedrock_branches = len(bedrock_cfg.branches)
<<<<<<< HEAD
        branch_similarity = (
            min(java_branches, bedrock_branches) / max(java_branches, bedrock_branches)
            if max(java_branches, bedrock_branches) > 0
            else 1.0
        )

        # Compare loop counts
        java_loops = sum(1 for n in java_cfg.nodes.values() if n.node_type == NodeType.LOOP)
        bedrock_loops = sum(1 for n in bedrock_cfg.nodes.values() if n.node_type == NodeType.LOOP)
        loop_similarity = (
            min(java_loops, bedrock_loops) / max(java_loops, bedrock_loops)
            if max(java_loops, bedrock_loops) > 0
            else 1.0
        )

        # Compare path counts (simplified)
        java_paths = len(java_cfg.get_paths())
        bedrock_paths = len(bedrock_cfg.get_paths())
        path_similarity = (
            min(java_paths, bedrock_paths) / max(java_paths, bedrock_paths)
            if max(java_paths, bedrock_paths) > 0
            else 1.0
        )

        # Weighted average
        return 0.4 * branch_similarity + 0.3 * loop_similarity + 0.3 * path_similarity

=======
        branch_similarity = min(java_branches, bedrock_branches) / max(java_branches, bedrock_branches) if max(java_branches, bedrock_branches) > 0 else 1.0
        
        # Compare loop counts
        java_loops = sum(1 for n in java_cfg.nodes.values() if n.node_type == NodeType.LOOP)
        bedrock_loops = sum(1 for n in bedrock_cfg.nodes.values() if n.node_type == NodeType.LOOP)
        loop_similarity = min(java_loops, bedrock_loops) / max(java_loops, bedrock_loops) if max(java_loops, bedrock_loops) > 0 else 1.0
        
        # Compare path counts (simplified)
        java_paths = len(java_cfg.get_paths())
        bedrock_paths = len(bedrock_cfg.get_paths())
        path_similarity = min(java_paths, bedrock_paths) / max(java_paths, bedrock_paths) if max(java_paths, bedrock_paths) > 0 else 1.0
        
        # Weighted average
        return 0.4 * branch_similarity + 0.3 * loop_similarity + 0.3 * path_similarity
    
    def _find_differences(
        self,
        java_dfg: DataFlowGraph,
        bedrock_dfg: DataFlowGraph,
        java_cfg: ControlFlowGraph,
        bedrock_cfg: ControlFlowGraph,
    ) -> List[str]:
        """Find specific differences between the graphs."""
        differences = []
<<<<<<< HEAD

=======
        
        # Missing variables
        missing_vars = java_dfg.variables - bedrock_dfg.variables
        for var in missing_vars:
            differences.append(f"Missing variable in Bedrock: {var}")
<<<<<<< HEAD

        extra_vars = bedrock_dfg.variables - java_dfg.variables
        for var in extra_vars:
            differences.append(f"Extra variable in Bedrock: {var}")

=======
        
        extra_vars = bedrock_dfg.variables - java_dfg.variables
        for var in extra_vars:
            differences.append(f"Extra variable in Bedrock: {var}")
        
        # Different branch counts
        if len(java_cfg.branches) != len(bedrock_cfg.branches):
            differences.append(
                f"Branch count mismatch: Java={len(java_cfg.branches)}, Bedrock={len(bedrock_cfg.branches)}"
            )
<<<<<<< HEAD

=======
        
        # Different loop counts
        java_loops = sum(1 for n in java_cfg.nodes.values() if n.node_type == NodeType.LOOP)
        bedrock_loops = sum(1 for n in bedrock_cfg.nodes.values() if n.node_type == NodeType.LOOP)
        if java_loops != bedrock_loops:
<<<<<<< HEAD
            differences.append(f"Loop count mismatch: Java={java_loops}, Bedrock={bedrock_loops}")

        return differences

=======
            differences.append(
                f"Loop count mismatch: Java={java_loops}, Bedrock={bedrock_loops}"
            )
        
        return differences
    
    def _generate_warnings(
        self,
        java_dfg: DataFlowGraph,
        bedrock_dfg: DataFlowGraph,
    ) -> List[str]:
        """Generate warnings about potential issues."""
        warnings = []
<<<<<<< HEAD

=======
        
        # Check for unused variables in Bedrock
        for var in bedrock_dfg.variables:
            defs = bedrock_dfg.get_variable_definitions(var)
            uses = bedrock_dfg.get_variable_uses(var)
            if defs and not uses:
                warnings.append(f"Potentially unused variable: {var}")
<<<<<<< HEAD

=======
        
        return warnings


def check_semantic_equivalence(java_code: str, bedrock_code: str) -> EquivalenceResult:
    """
    Convenience function to check semantic equivalence.
<<<<<<< HEAD

    Args:
        java_code: Original Java source code
        bedrock_code: Converted Bedrock JavaScript code

=======
    
    Args:
        java_code: Original Java source code
        bedrock_code: Converted Bedrock JavaScript code
        
    Returns:
        EquivalenceResult with analysis
    """
    checker = SemanticEquivalenceChecker()
    return checker.check_equivalence(java_code, bedrock_code)
