"""
Semantic chunking strategy for large Java mods exceeding LLM context window limits.

Implements Phase 0.4 chunking: breaks mod files into semantically coherent units
using tree-sitter AST class/method boundaries before conversion.
"""

from __future__ import annotations

import re
import zipfile
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

try:
    import tree_sitter_java as ts_java
    from tree_sitter import Language, Parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    ts_java = None
    Parser = None

CHARS_PER_TOKEN = 4
MAX_CHUNK_TOKENS = 3_500
COMPONENT_TYPES = ("items", "blocks", "entities", "recipes", "events", "dimensions", "gui", "other")

_COMPONENT_PATTERNS: Dict[str, List[str]] = {
    "items": ["Item", "ItemStack", "ItemGroup", "CreativeModeTab"],
    "blocks": ["Block", "BlockState", "BlockEntity", "TileEntity"],
    "entities": ["Entity", "LivingEntity", "Mob", "EntityType"],
    "recipes": ["Recipe", "RecipeSerializer", "CraftingRecipe", "ShapedRecipe"],
    "events": ["Event", "EventHandler", "Subscribe", "SubscribeEvent"],
    "dimensions": ["Dimension", "Level", "WorldGeneration", "Biome", "ChunkGenerator"],
    "gui": ["Screen", "Container", "Gui", "Menu", "AbstractContainerMenu"],
}


@dataclass
class ChunkInfo:
    source_file: str
    class_name: str
    chunk_index: int
    chunk_type: str
    component_type: str
    content: str
    start_line: int
    end_line: int
    token_estimate: int
    dependencies: List[str] = field(default_factory=list)
    context_header: str = ""
    superclass: str = ""
    interfaces: List[str] = field(default_factory=list)


@dataclass
class ChunkManifest:
    mod_id: str
    mod_name: str
    loader: str
    loader_version: str
    total_chunks: int
    chunks: List[ChunkInfo] = field(default_factory=list)


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


def _detect_component_type(
    class_name: str, superclass: str, interfaces: List[str], annotations: List[str]
) -> str:
    candidates = [class_name, superclass] + interfaces + annotations
    combined = " ".join(candidates)
    for comp_type, patterns in _COMPONENT_PATTERNS.items():
        if any(p in combined for p in patterns):
            return comp_type
    return "other"


class _TreeSitterHelper:
    """Thin wrapper around tree-sitter to extract class/method boundaries."""

    def __init__(self) -> None:
        self._parser: Optional[object] = None

    def _get_parser(self):
        if not TREE_SITTER_AVAILABLE:
            return None
        if self._parser is None:
            try:
                lang = Language(ts_java.language())
                self._parser = Parser(lang)
            except Exception:
                self._parser = None
        return self._parser

    def parse(self, source_code: str):
        parser = self._get_parser()
        if parser is None:
            return None
        try:
            return parser.parse(bytes(source_code, "utf8"))
        except Exception:
            return None

    def find_class_nodes(self, tree) -> List[object]:
        if tree is None:
            return []
        results: List[object] = []
        self._walk(tree.root_node, "class_declaration", results)
        return results

    def find_method_nodes(self, class_node) -> List[object]:
        results: List[object] = []
        for child in class_node.children:
            if child.type == "class_body":
                for member in child.children:
                    if member.type == "method_declaration":
                        results.append(member)
        return results

    def _walk(self, node, target_type: str, results: List) -> None:
        if node.type == target_type:
            results.append(node)
        for child in node.children:
            self._walk(child, target_type, results)

    def get_class_name(self, class_node) -> str:
        for child in class_node.children:
            if child.type == "identifier":
                return child.text.decode("utf8") if child.text else ""
        return ""

    def get_superclass(self, class_node) -> str:
        for child in class_node.children:
            if child.type == "superclass":
                for sub in child.children:
                    if sub.type == "type_identifier":
                        return sub.text.decode("utf8") if sub.text else ""
        return ""

    def get_interfaces(self, class_node) -> List[str]:
        for child in class_node.children:
            if child.type == "super_interfaces":
                return [
                    sub.text.decode("utf8")
                    for sub in child.children
                    if sub.type == "type_identifier" and sub.text
                ]
        return []

    def get_annotations(self, class_node) -> List[str]:
        results: List[str] = []
        for child in class_node.children:
            if child.type == "marker_annotation" or child.type == "annotation":
                for sub in child.children:
                    if sub.type == "identifier" and sub.text:
                        results.append(sub.text.decode("utf8"))
        return results

    def get_imports(self, tree) -> List[str]:
        if tree is None:
            return []
        imports: List[str] = []
        for child in tree.root_node.children:
            if child.type == "import_declaration":
                text = child.text.decode("utf8") if child.text else ""
                m = re.search(r"import\s+(?:static\s+)?([^;]+);", text)
                if m:
                    imports.append(m.group(1).strip())
        return imports


def _extract_imports_regex(source_code: str) -> List[str]:
    return re.findall(r"^import\s+(?:static\s+)?([^;]+);", source_code, re.MULTILINE)


def _extract_class_info_regex(source_code: str) -> List[Tuple[str, str, List[str]]]:
    """Fallback: extract (class_name, superclass, interfaces) via regex."""
    pattern = (
        r"(?:public\s+|private\s+|protected\s+)?(?:abstract\s+)?(?:final\s+)?class\s+(\w+)"
        r"(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?"
    )
    results: List[Tuple[str, str, List[str]]] = []
    for m in re.finditer(pattern, source_code):
        name = m.group(1) or ""
        superclass = m.group(2) or ""
        ifaces_raw = m.group(3) or ""
        ifaces = [i.strip() for i in ifaces_raw.split(",") if i.strip()]
        results.append((name, superclass, ifaces))
    return results


class JavaSemanticChunker:
    """
    Produces a ChunkManifest from a set of Java source files using tree-sitter
    AST class/method boundaries.

    Chunking strategy (priority order):
    1. Top-level class  — each Java class is a chunk
    2. Mod component type — label by detected component category
    3. Method cluster   — split oversized classes by method with a shared header

    Chunks are ordered via topological sort over inter-class import references.
    """

    def __init__(self) -> None:
        self._ts = _TreeSitterHelper()

    def build_manifest(
        self,
        sources: List[Tuple[str, str]],
        mod_id: str = "",
        mod_name: str = "",
        loader: str = "",
        loader_version: str = "",
    ) -> ChunkManifest:
        """
        Args:
            sources: list of (relative_path, source_code) pairs
            mod_id, mod_name, loader, loader_version: mod metadata for context headers

        Returns:
            ChunkManifest with chunks in topological order
        """
        raw_chunks: List[ChunkInfo] = []
        class_to_chunk_index: Dict[str, int] = {}

        for source_path, source_code in sources:
            file_chunks = self._chunk_file(
                source_path, source_code, mod_id, mod_name, loader, loader_version
            )
            for chunk in file_chunks:
                class_to_chunk_index[chunk.class_name] = len(raw_chunks)
                raw_chunks.append(chunk)

        ordered = self._topological_sort(raw_chunks, class_to_chunk_index)

        for i, chunk in enumerate(ordered):
            chunk.chunk_index = i
            if not chunk.context_header:
                chunk.context_header = self._build_context_header(
                    chunk, mod_id, mod_name, loader, loader_version
                )

        manifest = ChunkManifest(
            mod_id=mod_id,
            mod_name=mod_name,
            loader=loader,
            loader_version=loader_version,
            total_chunks=len(ordered),
            chunks=ordered,
        )
        return manifest

    def build_manifest_from_jar(
        self,
        jar_path: str,
        mod_id: str = "",
        mod_name: str = "",
        loader: str = "",
        loader_version: str = "",
    ) -> ChunkManifest:
        sources: List[Tuple[str, str]] = []
        try:
            with zipfile.ZipFile(jar_path, "r") as jar:
                for name in jar.namelist():
                    if name.endswith(".java"):
                        try:
                            code = jar.read(name).decode("utf-8", errors="replace")
                            sources.append((name, code))
                        except Exception:
                            pass
        except Exception:
            pass
        return self.build_manifest(
            sources, mod_id=mod_id, mod_name=mod_name, loader=loader, loader_version=loader_version
        )

    def _chunk_file(
        self,
        source_path: str,
        source_code: str,
        mod_id: str,
        mod_name: str,
        loader: str,
        loader_version: str,
    ) -> List[ChunkInfo]:
        tree = self._ts.parse(source_code)
        lines = source_code.splitlines()

        if tree is not None:
            return self._chunk_with_ast(
                source_path, source_code, lines, tree, mod_id, mod_name, loader, loader_version
            )
        return self._chunk_with_regex(
            source_path, source_code, mod_id, mod_name, loader, loader_version
        )

    def _chunk_with_ast(
        self,
        source_path: str,
        source_code: str,
        lines: List[str],
        tree,
        mod_id: str,
        mod_name: str,
        loader: str,
        loader_version: str,
    ) -> List[ChunkInfo]:
        imports = self._ts.get_imports(tree)
        class_nodes = self._ts.find_class_nodes(tree)
        chunks: List[ChunkInfo] = []

        if not class_nodes:
            token_est = _estimate_tokens(source_code)
            chunk = ChunkInfo(
                source_file=source_path,
                class_name=source_path.split("/")[-1].replace(".java", ""),
                chunk_index=0,
                chunk_type="file",
                component_type="other",
                content=source_code,
                start_line=0,
                end_line=len(lines) - 1,
                token_estimate=token_est,
                dependencies=imports,
            )
            chunk.context_header = self._build_context_header(
                chunk, mod_id, mod_name, loader, loader_version
            )
            chunks.append(chunk)
            return chunks

        for class_node in class_nodes:
            class_name = self._ts.get_class_name(class_node)
            superclass = self._ts.get_superclass(class_node)
            interfaces = self._ts.get_interfaces(class_node)
            annotations = self._ts.get_annotations(class_node)
            comp_type = _detect_component_type(class_name, superclass, interfaces, annotations)

            start_row = class_node.start_point[0]
            end_row = class_node.end_point[0]
            class_content = "\n".join(lines[start_row : end_row + 1])
            token_est = _estimate_tokens(class_content)

            if token_est <= MAX_CHUNK_TOKENS:
                chunk = ChunkInfo(
                    source_file=source_path,
                    class_name=class_name,
                    chunk_index=0,
                    chunk_type="class",
                    component_type=comp_type,
                    content=class_content,
                    start_line=start_row,
                    end_line=end_row,
                    token_estimate=token_est,
                    dependencies=imports,
                    superclass=superclass,
                    interfaces=interfaces,
                )
                chunk.context_header = self._build_context_header(
                    chunk, mod_id, mod_name, loader, loader_version
                )
                chunks.append(chunk)
            else:
                method_chunks = self._split_class_by_methods(
                    source_path,
                    class_node,
                    class_name,
                    comp_type,
                    superclass,
                    interfaces,
                    imports,
                    lines,
                    mod_id,
                    mod_name,
                    loader,
                    loader_version,
                )
                chunks.extend(method_chunks)

        return chunks

    def _split_class_by_methods(
        self,
        source_path: str,
        class_node,
        class_name: str,
        comp_type: str,
        superclass: str,
        interfaces: List[str],
        imports: List[str],
        lines: List[str],
        mod_id: str,
        mod_name: str,
        loader: str,
        loader_version: str,
    ) -> List[ChunkInfo]:
        method_nodes = self._ts.find_method_nodes(class_node)
        chunks: List[ChunkInfo] = []

        if not method_nodes:
            start_row = class_node.start_point[0]
            end_row = class_node.end_point[0]
            content = "\n".join(lines[start_row : end_row + 1])
            chunk = ChunkInfo(
                source_file=source_path,
                class_name=class_name,
                chunk_index=0,
                chunk_type="class",
                component_type=comp_type,
                content=content,
                start_line=start_row,
                end_line=end_row,
                token_estimate=_estimate_tokens(content),
                dependencies=imports,
                superclass=superclass,
                interfaces=interfaces,
            )
            chunk.context_header = self._build_context_header(
                chunk, mod_id, mod_name, loader, loader_version
            )
            return [chunk]

        current_methods: List[object] = []
        current_tokens = 0

        def flush(method_list: List[object]) -> None:
            if not method_list:
                return
            start_row = method_list[0].start_point[0]
            end_row = method_list[-1].end_point[0]
            content = "\n".join(lines[start_row : end_row + 1])
            chunk = ChunkInfo(
                source_file=source_path,
                class_name=class_name,
                chunk_index=len(chunks),
                chunk_type="method_cluster",
                component_type=comp_type,
                content=content,
                start_line=start_row,
                end_line=end_row,
                token_estimate=_estimate_tokens(content),
                dependencies=imports,
                superclass=superclass,
                interfaces=interfaces,
            )
            chunk.context_header = self._build_context_header(
                chunk, mod_id, mod_name, loader, loader_version
            )
            chunks.append(chunk)

        for method_node in method_nodes:
            method_start = method_node.start_point[0]
            method_end = method_node.end_point[0]
            method_content = "\n".join(lines[method_start : method_end + 1])
            method_tokens = _estimate_tokens(method_content)

            if current_tokens + method_tokens > MAX_CHUNK_TOKENS and current_methods:
                flush(current_methods)
                current_methods = []
                current_tokens = 0

            current_methods.append(method_node)
            current_tokens += method_tokens

        flush(current_methods)
        return chunks

    def _chunk_with_regex(
        self,
        source_path: str,
        source_code: str,
        mod_id: str,
        mod_name: str,
        loader: str,
        loader_version: str,
    ) -> List[ChunkInfo]:
        imports = _extract_imports_regex(source_code)
        class_infos = _extract_class_info_regex(source_code)
        chunks: List[ChunkInfo] = []

        if not class_infos:
            token_est = _estimate_tokens(source_code)
            chunk = ChunkInfo(
                source_file=source_path,
                class_name=source_path.split("/")[-1].replace(".java", ""),
                chunk_index=0,
                chunk_type="file",
                component_type="other",
                content=source_code,
                start_line=0,
                end_line=source_code.count("\n"),
                token_estimate=token_est,
                dependencies=imports,
            )
            chunk.context_header = self._build_context_header(
                chunk, mod_id, mod_name, loader, loader_version
            )
            return [chunk]

        for class_name, superclass, interfaces in class_infos:
            comp_type = _detect_component_type(class_name, superclass, interfaces, [])
            token_est = _estimate_tokens(source_code)
            chunk = ChunkInfo(
                source_file=source_path,
                class_name=class_name,
                chunk_index=len(chunks),
                chunk_type="class",
                component_type=comp_type,
                content=source_code,
                start_line=0,
                end_line=source_code.count("\n"),
                token_estimate=token_est,
                dependencies=imports,
                superclass=superclass,
                interfaces=interfaces,
            )
            chunk.context_header = self._build_context_header(
                chunk, mod_id, mod_name, loader, loader_version
            )
            chunks.append(chunk)

        return chunks

    def _build_context_header(
        self,
        chunk: ChunkInfo,
        mod_id: str,
        mod_name: str,
        loader: str,
        loader_version: str,
    ) -> str:
        mod_label = mod_name or mod_id or "UnknownMod"
        version_label = loader_version or "?"
        loader_label = loader or "unknown"

        parent = ""
        if chunk.superclass:
            parent = f" (extends {chunk.superclass})"
        ifaces = ""
        if chunk.interfaces:
            ifaces = f" implements {', '.join(chunk.interfaces)}"

        deps_label = ""
        short_deps = [d.split(".")[-1] for d in chunk.dependencies[:6]]
        if short_deps:
            deps_label = f"\n// Dependencies: [{', '.join(short_deps)}]"

        return (
            f"// Mod: {mod_label} | Loader: {loader_label} {version_label}\n"
            f"// Component: {chunk.component_type} | Class: {chunk.class_name}{parent}{ifaces}\n"
            f"// Chunk type: {chunk.chunk_type} | Lines: {chunk.start_line}-{chunk.end_line}"
            f"{deps_label}\n"
            f"// Conversion target: Bedrock Add-On"
        )

    def _topological_sort(
        self,
        chunks: List[ChunkInfo],
        class_to_chunk_index: Dict[str, int],
    ) -> List[ChunkInfo]:
        """Sort chunks so dependencies are processed before dependents."""
        n = len(chunks)
        adj: Dict[int, Set[int]] = defaultdict(set)
        in_degree: Dict[int, int] = defaultdict(int)

        for i, chunk in enumerate(chunks):
            in_degree[i] = in_degree.get(i, 0)
            for dep in chunk.dependencies:
                short = dep.split(".")[-1]
                if short in class_to_chunk_index and class_to_chunk_index[short] != i:
                    dep_idx = class_to_chunk_index[short]
                    if dep_idx not in adj[i]:
                        adj[dep_idx].add(i)
                        in_degree[i] = in_degree.get(i, 0) + 1

        queue: deque[int] = deque(i for i in range(n) if in_degree.get(i, 0) == 0)
        ordered: List[ChunkInfo] = []
        visited: Set[int] = set()

        while queue:
            idx = queue.popleft()
            if idx in visited:
                continue
            visited.add(idx)
            ordered.append(chunks[idx])
            for neighbor in sorted(adj[idx]):
                in_degree[neighbor] = in_degree.get(neighbor, 1) - 1
                if in_degree[neighbor] <= 0 and neighbor not in visited:
                    queue.append(neighbor)

        for i, chunk in enumerate(chunks):
            if i not in visited:
                ordered.append(chunk)

        return ordered
