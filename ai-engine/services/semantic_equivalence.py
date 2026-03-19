"""
Semantic Equivalence Checker for Java and Bedrock code comparison

Implements:
- Data Flow Graph (DFG) construction
- Control Flow Graph (CFG) construction
- Graph-based semantic comparison
- Embedding-based semantic similarity scoring
- Equivalence scoring with threshold categorization
"""

import logging
import os
import re
from typing import Dict, List, Set, Tuple, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)

# Try to import sentence-transformers, fallback to OpenAI embeddings
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "auto")
_embedding_model = None
_openai_client = None


def _get_embedding_model():
    """Get the embedding model (lazy loading)."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model
    
    if EMBEDDING_PROVIDER in ("auto", "local"):
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Using local sentence-transformers for embeddings")
            return _embedding_model
        except ImportError:
            logger.warning("sentence-transformers not available")
    
    if EMBEDDING_PROVIDER in ("auto", "openai"):
        try:
            from openai import AsyncOpenAI
            global _openai_client
            _openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            logger.info("Using OpenAI for embeddings")
            return "openai"
        except ImportError:
            logger.warning("OpenAI client not available")
    
    logger.warning("No embedding provider available, using mock embeddings")
    return None


async def _compute_embeddings_local(texts: List[str], model) -> List[List[float]]:
    """Compute embeddings using local sentence-transformers model."""
    embeddings = model.encode(texts, convert_to_numpy=True)
    return [emb.tolist() for emb in embeddings]


async def _compute_embeddings_openai(texts: List[str], client) -> List[List[float]]:
    """Compute embeddings using OpenAI API."""
    response = await client.embeddings.create(
        model="text-embedding-ada-002",
        input=texts
    )
    return [item.embedding for item in response.data]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)


@lru_cache(maxsize=128)
def _get_mock_embedding(text_hash: str) -> List[float]:
    """Generate a deterministic mock embedding for testing."""
    # Create a reproducible embedding based on text hash
    import struct
    seed = int(text_hash[:8], 16)
    state = [((seed >> (i * 4)) & 0xFFFF) / 32767.0 for i in range(8)]
    # Extend to 384 dimensions (MiniLM-L6 output)
    embedding = []
    for i in range(384):
        val = (state[i % 8] + (i * 0.1) % 1.0) % 1.0
        embedding.append(val * 2.0 - 1.0)
    return embedding


def _normalize_code_for_embedding(code: str) -> str:
    """Normalize code for embedding computation by removing comments and whitespace."""
    # Remove single-line comments
    code = re.sub(r'//.*?$', '', code, flags=re.MULTILINE)
    # Remove multi-line comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # Remove strings (approximate)
    code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', code)
    code = re.sub(r"'(?:[^'\\]|\\.)*'", "''", code)
    # Normalize whitespace
    code = re.sub(r'\s+', ' ', code)
    return code.strip()


class NodeType(Enum):
    """Types of nodes in data/control flow graphs."""
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
    id: str
    node_type: NodeType
    variable: Optional[str] = None
    value: Optional[str] = None
    operation: Optional[str] = None
    line_number: int = 0
    dependencies: List[str] = field(default_factory=list)
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
    id: str
    node_type: NodeType
    statement: Optional[str] = None
    successors: List[str] = field(default_factory=list)
    predecessors: List[str] = field(default_factory=list)
    line_number: int = 0
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
    nodes: Dict[str, DFGNode] = field(default_factory=dict)
    entry_node: Optional[str] = None
    exit_node: Optional[str] = None
    variables: Set[str] = field(default_factory=set)
    def add_node(self, node: DFGNode):
        """Add node to the graph."""
        self.nodes[node.id] = node
        if node.variable:
            self.variables.add(node.variable)
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
    nodes: Dict[str, CFGNode] = field(default_factory=dict)
    entry_node: Optional[str] = None
    exit_node: Optional[str] = None
    loops: List[List[str]] = field(default_factory=list)
    branches: List[Tuple[str, str, str]] = field(default_factory=list)  # (condition, true_branch, false_branch)
    
    def add_node(self, node: CFGNode):
        """Add node to the graph."""
        self.nodes[node.id] = node
    
    def add_edge(self, from_id: str, to_id: str):
        """Add edge between nodes."""
        if from_id in self.nodes and to_id in self.nodes:
            self.nodes[from_id].successors.append(to_id)
            self.nodes[to_id].predecessors.append(from_id)
    def get_paths(self) -> List[List[str]]:
        """Get all paths from entry to exit."""
        if not self.entry_node or not self.exit_node:
            return []
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


class ScoreCategory(Enum):
    """Semantic equivalence score categories."""
    EXCELLENT = "excellent"  # 90%+
    GOOD = "good"            # 70-89%
    NEEDS_WORK = "needs_work"  # <70%


@dataclass
class EquivalenceResult:
    """Result of semantic equivalence checking."""
    equivalent: bool
    confidence: float  # 0.0 to 1.0
    dfg_similarity: float
    cfg_similarity: float
    embedding_similarity: float = 0.0  # Embedding-based similarity (0.0-1.0)
    semantic_drift: List[str] = field(default_factory=list)  # Semantic differences identified
    score_category: ScoreCategory = ScoreCategory.NEEDS_WORK
    differences: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Apply threshold categorization after initialization."""
        if self.embedding_similarity > 0:
            self.score_category = self.apply_thresholds(self.embedding_similarity)
    
    @staticmethod
    def apply_thresholds(score: float) -> ScoreCategory:
        """Apply threshold categorization to a score."""
        if score >= 0.9:
            return ScoreCategory.EXCELLENT
        elif score >= 0.7:
            return ScoreCategory.GOOD
        else:
            return ScoreCategory.NEEDS_WORK
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "equivalent": self.equivalent,
            "confidence": self.confidence,
            "dfg_similarity": self.dfg_similarity,
            "cfg_similarity": self.cfg_similarity,
            "embedding_similarity": self.embedding_similarity,
            "semantic_drift": self.semantic_drift,
            "score_category": self.score_category.value,
            "differences": self.differences,
            "warnings": self.warnings,
        }


class DataFlowAnalyzer:
    """
    Analyzes code to build Data Flow Graphs.
    Tracks:
    - Variable definitions (defs)
    - Variable uses (uses)
    - Data dependencies
    """
    def __init__(self):
        self.dfg = DataFlowGraph()
        self._node_counter = 0
    
    def _new_id(self) -> str:
        """Generate unique node ID."""
        self._node_counter += 1
        return f"n{self._node_counter}"
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
        # Create entry node
        entry = DFGNode(id=self._new_id(), node_type=NodeType.ENTRY, line_number=0)
        self.dfg.add_node(entry)
        self.dfg.entry_node = entry.id
        # Parse and analyze (simplified - would use tree-sitter AST in production)
        lines = source_code.split('\n')
        for line_num, line in enumerate(lines, 1):
            self._analyze_java_line(line.strip(), line_num)
        
        # Create exit node
        exit_node = DFGNode(id=self._new_id(), node_type=NodeType.EXIT, line_number=len(lines))
        self.dfg.add_node(exit_node)
        self.dfg.exit_node = exit_node.id
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
        # Create entry node
        entry = DFGNode(id=self._new_id(), node_type=NodeType.ENTRY, line_number=0)
        self.dfg.add_node(entry)
        self.dfg.entry_node = entry.id
        # Parse and analyze
        lines = source_code.split('\n')
        for line_num, line in enumerate(lines, 1):
            self._analyze_javascript_line(line.strip(), line_num)
        
        # Create exit node
        exit_node = DFGNode(id=self._new_id(), node_type=NodeType.EXIT, line_number=len(lines))
        self.dfg.add_node(exit_node)
        self.dfg.exit_node = exit_node.id
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
    Tracks:
    - Basic blocks
    - Branches (if/else)
    - Loops (for/while)
    - Entry/exit points
    """
    def __init__(self):
        self.cfg = ControlFlowGraph()
        self._node_counter = 0
    
    def _new_id(self) -> str:
        """Generate unique node ID."""
        self._node_counter += 1
        return f"b{self._node_counter}"
    def analyze_java(self, source_code: str) -> ControlFlowGraph:
        """Build control flow graph from Java source code."""
        self.cfg = ControlFlowGraph()
        self._node_counter = 0
        # Create entry node
        entry = CFGNode(id=self._new_id(), node_type=NodeType.ENTRY, line_number=0)
        self.cfg.add_node(entry)
        self.cfg.entry_node = entry.id
        # Analyze lines
        lines = source_code.split('\n')
        prev_node_id = entry.id
        
        for line_num, line in enumerate(lines, 1):
            node = self._analyze_java_line(line.strip(), line_num)
            if node:
                self.cfg.add_node(node)
                self.cfg.add_edge(prev_node_id, node.id)
                prev_node_id = node.id
        # Create exit node
        exit_node = CFGNode(id=self._new_id(), node_type=NodeType.EXIT, line_number=len(lines))
        self.cfg.add_node(exit_node)
        if prev_node_id:
            self.cfg.add_edge(prev_node_id, exit_node.id)
        self.cfg.exit_node = exit_node.id
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
        # Loop
        if line.startswith('while (') or line.startswith('for ('):
            loop_node = CFGNode(
                id=self._new_id(),
                node_type=NodeType.LOOP,
                statement=line,
                line_number=line_num,
            )
            return loop_node
        # Return
        if line.startswith('return'):
            return CFGNode(
                id=self._new_id(),
                node_type=NodeType.RETURN,
                statement=line,
                line_number=line_num,
            )
        # Regular statement
        return CFGNode(
            id=self._new_id(),
            node_type=NodeType.ASSIGNMENT,
            statement=line,
            line_number=line_num,
        )
    def analyze_javascript(self, source_code: str) -> ControlFlowGraph:
        """Build control flow graph from JavaScript source code."""
        self.cfg = ControlFlowGraph()
        self._node_counter = 0
        # Create entry node
        entry = CFGNode(id=self._new_id(), node_type=NodeType.ENTRY, line_number=0)
        self.cfg.add_node(entry)
        self.cfg.entry_node = entry.id
        # Analyze lines
        lines = source_code.split('\n')
        prev_node_id = entry.id
        
        for line_num, line in enumerate(lines, 1):
            node = self._analyze_javascript_line(line.strip(), line_num)
            if node:
                self.cfg.add_node(node)
                self.cfg.add_edge(prev_node_id, node.id)
                prev_node_id = node.id
        # Create exit node
        exit_node = CFGNode(id=self._new_id(), node_type=NodeType.EXIT, line_number=len(lines))
        self.cfg.add_node(exit_node)
        if prev_node_id:
            self.cfg.add_edge(prev_node_id, exit_node.id)
        self.cfg.exit_node = exit_node.id
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
        # Loop
        if line.startswith('while (') or line.startswith('for ('):
            loop_node = CFGNode(
                id=self._new_id(),
                node_type=NodeType.LOOP,
                statement=line,
                line_number=line_num,
            )
            return loop_node
        # Return
        if line.startswith('return'):
            return CFGNode(
                id=self._new_id(),
                node_type=NodeType.RETURN,
                statement=line,
                line_number=line_num,
            )
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
    Compares:
    - Data flow graphs (variable definitions and uses)
    - Control flow graphs (branches, loops, paths)
    - Embedding-based semantic similarity
    - Overall behavioral equivalence
    """
    def __init__(self):
        self.dfg_analyzer = DataFlowAnalyzer()
        self.cfg_analyzer = ControlFlowAnalyzer()
        self._embedding_cache: Dict[str, List[float]] = {}
    
    async def check_equivalence(
        self,
        java_code: str,
        bedrock_code: str,
        compute_embedding: bool = True,
    ) -> EquivalenceResult:
        """
        Check semantic equivalence between Java and Bedrock code.
        Args:
            java_code: Original Java source code
            bedrock_code: Converted Bedrock JavaScript code
            compute_embedding: Whether to compute embedding-based similarity
            
        Returns:
            EquivalenceResult with confidence score and differences
        """
        logger.info("Checking semantic equivalence...")
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
        
        # Compute embedding-based similarity if requested
        embedding_similarity = 0.0
        semantic_drift = []
        if compute_embedding:
            embedding_similarity = await self._compute_embedding_similarity(java_code, bedrock_code)
            semantic_drift = self._identify_semantic_drift(java_code, bedrock_code)
        
        # Determine equivalence (consider both graph-based and embedding-based)
        if embedding_similarity > 0:
            # Weighted combination of graph and embedding similarity
            confidence = (confidence * 0.5) + (embedding_similarity * 0.5)
            equivalent = embedding_similarity >= 0.7  # Lower threshold when embedding available
        else:
            equivalent = confidence >= 0.8
        
        differences = self._find_differences(java_dfg, bedrock_dfg, java_cfg, bedrock_cfg)
        warnings = self._generate_warnings(java_dfg, bedrock_dfg)
        
        # Apply threshold categorization
        score_category = EquivalenceResult.apply_thresholds(
            embedding_similarity if embedding_similarity > 0 else confidence
        )
        
        result = EquivalenceResult(
            equivalent=equivalent,
            confidence=confidence,
            dfg_similarity=dfg_similarity,
            cfg_similarity=cfg_similarity,
            embedding_similarity=embedding_similarity,
            semantic_drift=semantic_drift,
            score_category=score_category,
            differences=differences,
            warnings=warnings,
        )
        logger.info(f"Equivalence check complete: equivalent={equivalent}, confidence={confidence:.2f}, embedding={embedding_similarity:.2f}")
        return result
    
    async def _compute_embedding_similarity(
        self,
        java_code: str,
        bedrock_code: str,
    ) -> float:
        """
        Compute embedding-based similarity between Java and Bedrock code.
        
        Uses sentence-transformers or OpenAI embeddings to measure semantic
        similarity at the code behavior level.
        """
        try:
            model = _get_embedding_model()
            if model is None:
                # Use mock embeddings
                return self._compute_mock_embedding_similarity(java_code, bedrock_code)
            
            # Normalize code for embedding
            java_normalized = _normalize_code_for_embedding(java_code)
            bedrock_normalized = _normalize_code_for_embedding(bedrock_code)
            
            if model == "openai":
                # Use OpenAI embeddings
                embeddings = await _compute_embeddings_openai(
                    [java_normalized, bedrock_normalized], _openai_client
                )
            else:
                # Use local sentence-transformers
                embeddings = await _compute_embeddings_local(
                    [java_normalized, bedrock_normalized], model
                )
            
            # Compute cosine similarity
            similarity = _cosine_similarity(embeddings[0], embeddings[1])
            return float(similarity)
            
        except Exception as e:
            logger.warning(f"Embedding computation failed: {e}, using mock similarity")
            return self._compute_mock_embedding_similarity(java_code, bedrock_code)
    
    def _compute_mock_embedding_similarity(
        self,
        java_code: str,
        bedrock_code: str,
    ) -> float:
        """Compute mock embedding similarity for testing when no embedding provider is available."""
        # Create deterministic hashes
        java_hash = hashlib.md5(java_code.encode()).hexdigest()
        bedrock_hash = hashlib.md5(bedrock_code.encode()).hexdigest()
        
        # Get mock embeddings
        java_emb = _get_mock_embedding(java_hash)
        bedrock_emb = _get_mock_embedding(bedrock_hash)
        
        # Compute similarity
        return _cosine_similarity(java_emb, bedrock_emb)
    
    def _identify_semantic_drift(
        self,
        java_code: str,
        bedrock_code: str,
    ) -> List[str]:
        """
        Identify semantic drift between Java and Bedrock code.
        
        Detects differences in:
        - Method/function signatures
        - Control flow patterns
        - Variable usage patterns
        - API calls
        """
        drift = []
        
        # Extract method/function names
        java_methods = set(re.findall(r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(', java_code))
        js_functions = set(re.findall(r'function\s+(\w+)\s*\(', bedrock_code))
        js_arrows = set(re.findall(r'(?:const|let|var)\s+(\w+)\s*=\s*\(', bedrock_code))
        
        js_methods = js_functions | js_arrows
        
        # Check for method mapping issues
        missing_in_js = java_methods - js_methods
        extra_in_js = js_methods - java_methods
        
        if missing_in_js:
            drift.append(f"Methods not found in Bedrock: {', '.join(missing_in_js)}")
        if extra_in_js:
            drift.append(f"Additional methods in Bedrock: {', '.join(extra_in_js)}")
        
        # Check for control flow differences
        java_loops = len(re.findall(r'\b(while|for)\s*\(', java_code))
        js_loops = len(re.findall(r'\b(while|for)\s*\(', bedrock_code))
        
        if java_loops != js_loops:
            drift.append(f"Loop count mismatch: Java={java_loops}, Bedrock={js_loops}")
        
        # Check for async/await usage
        java_async = 'async' in java_code or 'CompletableFuture' in java_code
        js_async = 'async' in bedrock_code or 'await' in bedrock_code
        
        if java_async and not js_async:
            drift.append("Java uses async but Bedrock does not")
        elif js_async and not java_async:
            drift.append("Bedrock uses async but Java does not")
        
        return drift
    
    def _compare_dfgs(self, java_dfg: DataFlowGraph, bedrock_dfg: DataFlowGraph) -> float:
        """Compare data flow graphs and return similarity score."""
        if not java_dfg.variables and not bedrock_dfg.variables:
            return 1.0
        # Compare variable sets
        java_vars = java_dfg.variables
        bedrock_vars = bedrock_dfg.variables
        
        # Jaccard similarity for variables
        intersection = len(java_vars & bedrock_vars)
        union = len(java_vars | bedrock_vars)
        var_similarity = intersection / union if union > 0 else 1.0
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
        # Missing variables
        missing_vars = java_dfg.variables - bedrock_dfg.variables
        for var in missing_vars:
            differences.append(f"Missing variable in Bedrock: {var}")
        extra_vars = bedrock_dfg.variables - java_dfg.variables
        for var in extra_vars:
            differences.append(f"Extra variable in Bedrock: {var}")
        
        # Different branch counts
        if len(java_cfg.branches) != len(bedrock_cfg.branches):
            differences.append(
                f"Branch count mismatch: Java={len(java_cfg.branches)}, Bedrock={len(bedrock_cfg.branches)}"
            )
        # Different loop counts
        java_loops = sum(1 for n in java_cfg.nodes.values() if n.node_type == NodeType.LOOP)
        bedrock_loops = sum(1 for n in bedrock_cfg.nodes.values() if n.node_type == NodeType.LOOP)
        if java_loops != bedrock_loops:
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
        # Check for unused variables in Bedrock
        for var in bedrock_dfg.variables:
            defs = bedrock_dfg.get_variable_definitions(var)
            uses = bedrock_dfg.get_variable_uses(var)
            if defs and not uses:
                warnings.append(f"Potentially unused variable: {var}")
        return warnings


async def check_semantic_equivalence(
    java_code: str,
    bedrock_code: str,
    compute_embedding: bool = True,
) -> EquivalenceResult:
    """
    Convenience async function to check semantic equivalence.
    Args:
        java_code: Original Java source code
        bedrock_code: Converted Bedrock JavaScript code
        compute_embedding: Whether to compute embedding-based similarity
        
    Returns:
        EquivalenceResult with analysis
    """
    checker = SemanticEquivalenceChecker()
    return await checker.check_equivalence(java_code, bedrock_code, compute_embedding)
