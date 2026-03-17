"""
Tree-sitter Java Parser Service

Provides fast, robust Java source code parsing using tree-sitter.
Falls back to javalang if tree-sitter is unavailable.
"""

import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# Try to import tree-sitter, fall back to javalang
try:
    import tree_sitter_java as ts_java
    from tree_sitter import Language, Parser

    TREE_SITTER_AVAILABLE = True
    logger.info("Tree-sitter Java parser available")
except ImportError as e:
    logger.warning(f"Tree-sitter not available, falling back to javalang: {e}")
    TREE_SITTER_AVAILABLE = False
    ts_java = None
    Parser = None
    Language = None

# Always have javalang as fallback
import javalang


class TreeSitterJavaParser:
    """
    Java parser using tree-sitter for fast AST extraction.
    """

    def __init__(self):
        self.parser = None
        if TREE_SITTER_AVAILABLE:
            try:
                # New tree-sitter API (0.25+)
                # Language wrapper needed for PyCapsule from tree_sitter_java
                from tree_sitter import Language

                lang = Language(ts_java.language())
                self.parser = Parser(lang)
                logger.debug("Tree-sitter parser initialized (new API)")
            except Exception as e:
                logger.error(f"Failed to initialize tree-sitter parser: {e}")
                self.parser = None

    def parse(self, source_code: str) -> Optional[Dict[str, Any]]:
        """
        Parse Java source code and return AST.

        Args:
            source_code: Java source code string

        Returns:
            Parsed AST as dictionary, or None if parsing fails
        """
        if self.parser is None:
            logger.debug("Tree-sitter not available, using javalang fallback")
            return self._parse_with_javalang(source_code)

        try:
            tree = self.parser.parse(bytes(source_code, "utf8"))

            # Check for error nodes (tree-sitter's error recovery)
            error_count = self._count_error_nodes(tree.root_node)
            if error_count > 0:
                logger.warning(
                    f"Parse completed with {error_count} error nodes (malformed code)"
                )

            return self._tree_to_dict(tree.root_node, error_count)
        except Exception as e:
            logger.warning(f"Tree-sitter parsing failed, falling back to javalang: {e}")
            return self._parse_with_javalang(source_code)

    def _count_error_nodes(self, node) -> int:
        """Count error nodes in the AST (indicates malformed code)."""
        count = 0
        if node.type == "ERROR":
            count += 1
        for child in node.children:
            count += self._count_error_nodes(child)
        return count

    def has_syntax_errors(self, source_code: str) -> bool:
        """
        Check if source code has syntax errors without full parsing.

        Args:
            source_code: Java source code

        Returns:
            True if syntax errors detected, False otherwise
        """
        if self.parser is None:
            return False

        try:
            tree = self.parser.parse(bytes(source_code, "utf8"))
            return self._count_error_nodes(tree.root_node) > 0
        except Exception:
            return True

    def _tree_to_dict(self, node, error_count: int = 0) -> Dict[str, Any]:
        """Convert tree-sitter node to dictionary for easier traversal."""
        result = {
            "type": node.type,
            "start_point": node.start_point,
            "end_point": node.end_point,
            "start_byte": node.start_byte,
            "end_byte": node.end_byte,
            "has_errors": error_count > 0 or node.type == "ERROR",
        }

        # Add text content for leaf nodes
        if node.child_count == 0:
            result["text"] = node.text.decode("utf8") if node.text else ""

        # Recursively convert children
        if node.child_count > 0:
            result["children"] = [
                self._tree_to_dict(child, error_count) for child in node.children
            ]

        return result

    def _parse_with_javalang(self, source_code: str) -> Optional[Dict[str, Any]]:
        """Fallback parsing using javalang."""
        try:
            tree = javalang.parse.parse(source_code)
            return self._javalang_to_dict(tree)
        except Exception as e:
            logger.error(f"Javalang parsing failed: {e}")
            return None

    def _javalang_to_dict(self, tree) -> Dict[str, Any]:
        """Convert javalang AST to dictionary."""
        if tree is None:
            return None

        result = {
            "type": type(tree).__name__,
        }

        # Add attributes
        for attr_name in dir(tree):
            if attr_name.startswith("_"):
                continue
            try:
                attr = getattr(tree, attr_name)
                if isinstance(attr, (str, int, float, bool, type(None))):
                    result[attr_name] = attr
                elif isinstance(attr, javalang.tree.Node):
                    result[attr_name] = self._javalang_to_dict(attr)
                elif isinstance(attr, list):
                    result[attr_name] = [
                        (
                            self._javalang_to_dict(item)
                            if isinstance(item, javalang.tree.Node)
                            else item
                        )
                        for item in attr
                    ]
            except Exception:
                pass

        return result


class SemanticAnalyzer:
    """
    Semantic analysis for Java code using tree-sitter AST.
    Provides type inference, symbol resolution, and data flow analysis.
    """

    def __init__(self, ast_tree: Dict):
        """
        Initialize semantic analyzer with AST.

        Args:
            ast_tree: Parsed AST dictionary from JavaASTAnalyzer
        """
        self.ast = ast_tree
        self.symbols = {}  # name -> {type, scope, modifiers, position}
        self.types = {}  # type_name -> {kind, superclass, interfaces, members}
        self.method_calls = []  # List of method invocations
        self.field_accesses = []  # List of field accesses

    def analyze(self) -> Dict[str, Any]:
        """
        Perform full semantic analysis.

        Returns:
            Dictionary with semantic analysis results
        """
        self._build_symbol_table()
        self._resolve_types()
        self._extract_method_calls()
        self._extract_field_accesses()
        self._build_inheritance_graph()

        return {
            "symbols": self.symbols,
            "types": self.types,
            "method_calls": self.method_calls,
            "field_accesses": self.field_accesses,
            "inheritance": self._get_inheritance_info(),
        }

    def _build_symbol_table(self):
        """Build symbol table from AST."""
        if not isinstance(self.ast, dict):
            return

        classes = self.ast.get("classes", [])
        for cls in classes:
            class_name = cls.get("name", "")
            if class_name:
                self.symbols[class_name] = {
                    "type": "class",
                    "scope": "global",
                    "modifiers": cls.get("modifiers", []),
                    "superclass": cls.get("superclass"),
                    "interfaces": cls.get("interfaces", []),
                }

        # TODO: Extract methods and fields from class body
        # This requires traversing the full AST tree structure

    def _resolve_types(self):
        """Resolve type references and build type hierarchy."""
        for name, symbol in self.symbols.items():
            if symbol["type"] == "class":
                self.types[name] = {
                    "kind": "class",
                    "superclass": symbol.get("superclass"),
                    "interfaces": symbol.get("interfaces", []),
                    "members": [],
                }

    def _extract_method_calls(self):
        """Extract method invocations from AST."""
        # TODO: Traverse AST to find method_invocation nodes
        pass

    def _extract_field_accesses(self):
        """Extract field accesses from AST."""
        # TODO: Traverse AST to find field_access nodes
        pass

    def _build_inheritance_graph(self):
        """Build inheritance graph from type information."""
        # TODO: Build graph structure for inheritance hierarchy
        pass

    def _get_inheritance_info(self) -> Dict[str, Any]:
        """Get inheritance information for all types."""
        return {
            name: {
                "superclass": info.get("superclass"),
                "interfaces": info.get("interfaces", []),
            }
            for name, info in self.types.items()
        }

    def get_type_info(self, type_name: str) -> Optional[Dict]:
        """
        Get type information for a given type name.

        Args:
            type_name: Name of the type to look up

        Returns:
            Type information dictionary or None if not found
        """
        return self.types.get(type_name)

    def get_symbol_info(self, symbol_name: str) -> Optional[Dict]:
        """
        Get symbol information for a given symbol name.

        Args:
            symbol_name: Name of the symbol to look up

        Returns:
            Symbol information dictionary or None if not found
        """
        return self.symbols.get(symbol_name)


class JavaASTAnalyzer:
    """
    Analyze Java AST to extract mod components and structure.
    """

    def __init__(self):
        self.parser = TreeSitterJavaParser()

    def analyze_file(self, source_code: str, filename: str = "") -> Dict[str, Any]:
        """
        Analyze a Java file and extract mod-related information.

        Args:
            source_code: Java source code
            filename: Optional filename for context

        Returns:
            Dictionary with extracted information
        """
        ast = self.parser.parse(source_code)

        if ast is None:
            return {
                "success": False,
                "error": "Failed to parse Java file",
                "filename": filename,
            }

        result = {
            "success": True,
            "filename": filename,
            "classes": self._extract_classes(ast),
            "imports": self._extract_imports(ast),
            "annotations": self._extract_annotations(ast),
            "components": self._identify_components(ast),
        }

        return result

    def _extract_classes(self, ast: Dict) -> List[Dict]:
        """Extract class declarations from AST."""
        classes = []
        seen_classes = set()  # Track unique classes by name and position

        def traverse(node):
            if not isinstance(node, dict):
                return

            node_type = node.get("type", "")

            # Tree-sitter node type
            if node_type == "class_declaration":
                class_info = self._extract_class_info(node)
                # Create unique key to avoid duplicates
                class_key = f"{class_info['name']}_{node.get('start_point', '')}"
                if class_key not in seen_classes:
                    seen_classes.add(class_key)
                    classes.append(class_info)
            # Javalang node type
            elif node_type == "ClassDeclaration":
                class_info = self._extract_class_info_javalang(node)
                classes.append(class_info)

            # Traverse children
            for child in node.get("children", []):
                traverse(child)

            # Also check javalang-style attributes
            for key, value in node.items():
                if key in ["children", "members", "body"]:
                    if isinstance(value, list):
                        for item in value:
                            traverse(item)

        traverse(ast)
        return classes

    def _extract_class_info(self, node: Dict) -> Dict:
        """Extract class information from tree-sitter node."""
        class_info = {
            "name": "",
            "modifiers": [],
            "superclass": None,
            "interfaces": [],
        }

        # Extract class name from identifier
        for child in node.get("children", []):
            if child.get("type") == "identifier":
                class_info["name"] = child.get("text", "")
            elif child.get("type") == "modifiers":
                class_info["modifiers"] = [
                    c.get("text", "")
                    for c in child.get("children", [])
                    if c.get("type")
                    in ["public", "private", "protected", "static", "final", "abstract"]
                ]
            elif child.get("type") == "superclass":
                # Superclass node contains: extends, type_identifier
                superclass_children = child.get("children", [])
                for sc in superclass_children:
                    if sc.get("type") == "type_identifier":
                        class_info["superclass"] = sc.get("text", "")
            elif child.get("type") == "super_interfaces":
                # Interfaces the class implements
                class_info["interfaces"] = [
                    c.get("text", "")
                    for c in child.get("children", [])
                    if c.get("type") == "type_identifier"
                ]

        return class_info

    def _extract_class_info_javalang(self, node: Dict) -> Dict:
        """Extract class information from javalang node."""
        return {
            "name": node.get("name", ""),
            "modifiers": node.get("modifiers", []),
            "superclass": node.get("extends"),
            "interfaces": node.get("implements", []),
        }

    def _extract_imports(self, ast: Dict) -> List[str]:
        """Extract import statements from AST."""
        imports = []

        def traverse(node):
            if not isinstance(node, dict):
                return

            node_type = node.get("type", "")

            # Tree-sitter
            if node_type == "import_declaration":
                for child in node.get("children", []):
                    if child.get("type") == "scoped_identifier":
                        imports.append(self._get_scoped_identifier_text(child))

            # Javalang
            elif node_type == "Import":
                import_path = node.get("path", "")
                if import_path:
                    imports.append(import_path)

            for child in node.get("children", []):
                traverse(child)

        traverse(ast)
        return imports

    def _get_scoped_identifier_text(self, node: Dict) -> str:
        """Get full text of a scoped identifier (e.g., net.minecraft.block.Block)."""
        parts = []

        def collect_parts(n):
            if n.get("type") == "identifier":
                parts.append(n.get("text", ""))
            elif n.get("type") == "scoped_identifier":
                for child in n.get("children", []):
                    collect_parts(child)

        collect_parts(node)
        return ".".join(parts)

    def _extract_annotations(self, ast: Dict) -> List[Dict]:
        """Extract annotations from AST."""
        annotations = []

        def traverse(node):
            if not isinstance(node, dict):
                return

            node_type = node.get("type", "")

            if node_type == "marker_annotation" or node_type == "annotation":
                annotation_info = {"name": "", "attributes": {}}
                for child in node.get("children", []):
                    if child.get("type") == "identifier":
                        annotation_info["name"] = child.get("text", "")
                if annotation_info["name"]:
                    annotations.append(annotation_info)

            for child in node.get("children", []):
                traverse(child)

        traverse(ast)
        return annotations

    def _identify_components(self, ast: Dict) -> Dict[str, List[Dict]]:
        """Identify Minecraft mod components (blocks, items, entities)."""
        components = {
            "blocks": [],
            "items": [],
            "entities": [],
            "other": [],
        }

        classes = self._extract_classes(ast)

        for cls in classes:
            superclass = cls.get("superclass", "") or ""
            class_name = cls.get("name", "")
            cls.get("modifiers", [])

            # Check if it's a nested class (static class inside another class)
            # Tree-sitter represents extends as "superclass" child node
            # Need to check the full type hierarchy

            # Identify blocks - check for Block in superclass
            if self._is_subclass_of(superclass, ["Block", "net.minecraft.block.Block"]):
                components["blocks"].append(
                    {
                        "class": class_name,
                        "extends": superclass,
                    }
                )
            # Identify items
            elif self._is_subclass_of(superclass, ["Item", "net.minecraft.item.Item"]):
                components["items"].append(
                    {
                        "class": class_name,
                        "extends": superclass,
                    }
                )
            # Identify entities
            elif self._is_subclass_of(
                superclass,
                [
                    "Entity",
                    "LivingEntity",
                    "MobEntity",
                    "net.minecraft.entity.Entity",
                    "net.minecraft.entity.LivingEntity",
                ],
            ):
                components["entities"].append(
                    {
                        "class": class_name,
                        "extends": superclass,
                    }
                )
            else:
                components["other"].append(
                    {
                        "class": class_name,
                        "extends": superclass,
                    }
                )

        return components

    def _is_subclass_of(self, superclass: str, targets: List[str]) -> bool:
        """Check if superclass matches any of the target types."""
        if not superclass:
            return False

        # Direct match
        if superclass in targets:
            return True

        # Check if superclass ends with target (handles simple names like "Block")
        return any(
            superclass.endswith(target) or target.endswith(superclass)
            for target in targets
        )


def analyze_java_file(source_code: str, filename: str = "") -> Dict[str, Any]:
    """
    Convenience function to analyze a Java file.

    Args:
        source_code: Java source code
        filename: Optional filename

    Returns:
        Analysis results dictionary
    """
    analyzer = JavaASTAnalyzer()
    return analyzer.analyze_file(source_code, filename)


def perform_semantic_analysis(source_code: str) -> Dict[str, Any]:
    """
    Perform semantic analysis on Java source code.

    Args:
        source_code: Java source code

    Returns:
        Semantic analysis results
    """
    # First parse the code
    analyzer = JavaASTAnalyzer()
    ast_result = analyzer.analyze_file(source_code)

    if not ast_result["success"]:
        return {"success": False, "error": "Parsing failed"}

    # Then perform semantic analysis
    semantic_analyzer = SemanticAnalyzer(ast_result)
    semantic_result = semantic_analyzer.analyze()

    return {"success": True, "semantic": semantic_result, "ast": ast_result}
