"""
Mod Dependency Analyzer for modpack conversion support.

Analyzes mod dependencies from CurseForge/Modrinth manifests, builds dependency graphs,
detects circular dependencies, resolves version conflicts, and calculates optimal
download order for modpacks.

Issue: #498 - Implement Mod Dependency Analysis & Resolution (Phase 5c)
"""

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict

logger = logging.getLogger(__name__)


class DependencyType(Enum):
    """Types of dependencies between mods."""
    REQUIRED = "required"
    OPTIONAL = "optional"
    EMBEDDED = "embedded"
    INCOMPATIBLE = "incompatible"


class ConflictResolution(Enum):
    """Resolution strategies for version conflicts."""
    USE_NEWEST = "use_newest"
    USE_OLDEST = "use_oldest"
    USE_SPECIFIED = "use_specified"
    EXCLUDE_CONFLICTING = "exclude_conflicting"


@dataclass
class ModDependency:
    """Represents a dependency relationship between mods."""
    mod_id: str
    mod_name: str
    version_range: Optional[str] = None
    dependency_type: DependencyType = DependencyType.REQUIRED
    source: str = "unknown"  # curseforge, modrinth


@dataclass
class ModInfo:
    """Information about a single mod."""
    mod_id: str
    name: str
    version: Optional[str] = None
    source: str = "unknown"
    file_id: Optional[int] = None
    url: Optional[str] = None
    dependencies: List[ModDependency] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DependencyGraph:
    """Represents the dependency graph for a modpack."""
    mods: Dict[str, ModInfo] = field(default_factory=dict)
    edges: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    reverse_edges: Dict[str, List[str]] = field(default_factory=lambda: defaultdict(list))
    
    def add_mod(self, mod: ModInfo) -> None:
        """Add a mod to the graph."""
        self.mods[mod.mod_id] = mod
    
    def add_dependency(self, from_mod_id: str, to_mod_id: str) -> None:
        """Add a dependency edge from one mod to another."""
        if from_mod_id not in self.edges:
            self.edges[from_mod_id] = []
        self.edges[from_mod_id].append(to_mod_id)
        
        if to_mod_id not in self.reverse_edges:
            self.reverse_edges[to_mod_id] = []
        self.reverse_edges[to_mod_id].append(from_mod_id)


@dataclass
class CircularDependency:
    """Represents a circular dependency detected in the graph."""
    mods: List[str]
    description: str


@dataclass 
class VersionConflict:
    """Represents a version conflict between mods."""
    mod_id: str
    mod_name: str
    versions: List[str]
    suggested_resolution: ConflictResolution
    resolved_version: Optional[str] = None


@dataclass
class DependencyAnalysisResult:
    """Result of dependency analysis."""
    graph: DependencyGraph
    circular_dependencies: List[CircularDependency] = field(default_factory=list)
    version_conflicts: List[VersionConflict] = field(default_factory=list)
    recommended_load_order: List[str] = field(default_factory=list)
    missing_dependencies: List[ModDependency] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    success: bool = True
    error_message: Optional[str] = None


class ModDependencyAnalyzer:
    """
    Analyzes mod dependencies for modpack conversion.
    
    Supports CurseForge and Modrinth modpack formats.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def analyze_from_manifest(
        self,
        manifest_data: Dict[str, Any],
        source: str = "curseforge"
    ) -> DependencyAnalysisResult:
        """
        Analyze dependencies from a modpack manifest.
        
        Args:
            manifest_data: Parsed modpack manifest
            source: Source platform (curseforge or modrinth)
            
        Returns:
            DependencyAnalysisResult with full analysis
        """
        try:
            # Build the dependency graph
            graph = self._build_dependency_graph(manifest_data, source)
            
            # Detect circular dependencies
            circular_deps = self._detect_circular_dependencies(graph)
            
            # Detect version conflicts
            version_conflicts = self._detect_version_conflicts(graph)
            
            # Find missing dependencies
            missing_deps = self._find_missing_dependencies(graph)
            
            # Calculate optimal load order
            load_order = self._calculate_load_order(graph)
            
            # Generate warnings
            warnings = self._generate_warnings(graph, circular_deps, version_conflicts, missing_deps)
            
            return DependencyAnalysisResult(
                graph=graph,
                circular_dependencies=circular_deps,
                version_conflicts=version_conflicts,
                recommended_load_order=load_order,
                missing_dependencies=missing_deps,
                warnings=warnings,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing dependencies: {e}")
            return DependencyAnalysisResult(
                graph=DependencyGraph(),
                success=False,
                error_message=str(e)
            )
    
    def analyze_from_modlist(
        self,
        mods: List[Dict[str, Any]]
    ) -> DependencyAnalysisResult:
        """
        Analyze dependencies from a list of mods.
        
        Args:
            mods: List of mod dictionaries with dependency information
            
        Returns:
            DependencyAnalysisResult with full analysis
        """
        try:
            # Build graph from mod list
            graph = self._build_graph_from_modlist(mods)
            
            # Detect circular dependencies
            circular_deps = self._detect_circular_dependencies(graph)
            
            # Detect version conflicts
            version_conflicts = self._detect_version_conflicts(graph)
            
            # Find missing dependencies
            missing_deps = self._find_missing_dependencies(graph)
            
            # Calculate optimal load order
            load_order = self._calculate_load_order(graph)
            
            # Generate warnings
            warnings = self._generate_warnings(graph, circular_deps, version_conflicts, missing_deps)
            
            return DependencyAnalysisResult(
                graph=graph,
                circular_dependencies=circular_deps,
                version_conflicts=version_conflicts,
                recommended_load_order=load_order,
                missing_dependencies=missing_deps,
                warnings=warnings,
                success=True
            )
            
        except Exception as e:
            self.logger.error(f"Error analyzing mod list: {e}")
            return DependencyAnalysisResult(
                graph=DependencyGraph(),
                success=False,
                error_message=str(e)
            )
    
    def _build_dependency_graph(
        self,
        manifest_data: Dict[str, Any],
        source: str
    ) -> DependencyGraph:
        """Build dependency graph from manifest data."""
        graph = DependencyGraph()
        
        # Extract files/mods from manifest
        files = manifest_data.get("files", [])
        
        for file_entry in files:
            mod_id = str(file_entry.get("projectID", file_entry.get("modId", "")))
            file_id = file_entry.get("fileID")
            
            # Get mod name from metadata if available
            name = file_entry.get("name", f"mod_{mod_id}")
            
            mod = ModInfo(
                mod_id=mod_id,
                name=name,
                source=source,
                file_id=file_id,
                version=file_entry.get("version")
            )
            
            # Parse dependencies
            dependencies = file_entry.get("dependencies", [])
            for dep in dependencies:
                dep_id = str(dep.get("projectID", dep.get("modId", "")))
                dep_name = dep.get("name", f"mod_{dep_id}")
                dep_type_str = dep.get("type", "required")
                
                dep_type = DependencyType.REQUIRED
                if dep_type_str == "optional":
                    dep_type = DependencyType.OPTIONAL
                elif dep_type_str == "embedded":
                    dep_type = DependencyType.EMBEDDED
                elif dep_type_str == "incompatible":
                    dep_type = DependencyType.INCOMPATIBLE
                
                dependency = ModDependency(
                    mod_id=dep_id,
                    mod_name=dep_name,
                    version_range=dep.get("version"),
                    dependency_type=dep_type,
                    source=source
                )
                mod.dependencies.append(dependency)
                
                # Add edge to graph
                graph.add_dependency(mod_id, dep_id)
            
            graph.add_mod(mod)
        
        return graph
    
    def _build_graph_from_modlist(self, mods: List[Dict[str, Any]]) -> DependencyGraph:
        """Build dependency graph from a list of mods."""
        graph = DependencyGraph()
        
        for mod_data in mods:
            mod_id = str(mod_data.get("id", mod_data.get("modId", "")))
            name = mod_data.get("name", f"mod_{mod_id}")
            
            mod = ModInfo(
                mod_id=mod_id,
                name=name,
                version=mod_data.get("version"),
                source=mod_data.get("source", "unknown"),
                file_id=mod_data.get("file_id"),
                url=mod_data.get("url"),
                metadata=mod_data
            )
            
            # Parse dependencies
            dependencies = mod_data.get("dependencies", [])
            for dep in dependencies:
                if isinstance(dep, dict):
                    dep_id = str(dep.get("id", dep.get("modId", "")))
                    dep_name = dep.get("name", f"mod_{dep_id}")
                    
                    dependency = ModDependency(
                        mod_id=dep_id,
                        mod_name=dep_name,
                        version_range=dep.get("version"),
                        dependency_type=DependencyType.REQUIRED,
                        source=mod_data.get("source", "unknown")
                    )
                else:
                    # Dependency is just an ID
                    dep_id = str(dep)
                    dependency = ModDependency(
                        mod_id=dep_id,
                        mod_name=f"mod_{dep_id}",
                        dependency_type=DependencyType.REQUIRED,
                        source=mod_data.get("source", "unknown")
                    )
                
                mod.dependencies.append(dependency)
                graph.add_dependency(mod_id, dep_id)
            
            graph.add_mod(mod)
        
        return graph
    
    def _detect_circular_dependencies(
        self,
        graph: DependencyGraph
    ) -> List[CircularDependency]:
        """Detect circular dependencies using DFS."""
        circular_deps = []
        visited = set()
        rec_stack = set()
        path = []
        
        def dfs(node: str) -> bool:
            """DFS to detect cycles. Returns True if cycle found."""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            # Visit all neighbors
            for neighbor in graph.edges.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle_nodes = path[cycle_start:] + [neighbor]
                    circular_deps.append(CircularDependency(
                        mods=cycle_nodes,
                        description=f"Circular dependency: {' -> '.join(cycle_nodes)}"
                    ))
                    return True
            
            path.pop()
            rec_stack.remove(node)
            return False
        
        # Run DFS from each unvisited node
        for mod_id in graph.mods:
            if mod_id not in visited:
                path = []
                dfs(mod_id)
        
        return circular_deps
    
    def _detect_version_conflicts(
        self,
        graph: DependencyGraph
    ) -> List[VersionConflict]:
        """Detect version conflicts between mods."""
        conflicts = []
        
        # Group mods by name (case-insensitive)
        version_groups: Dict[str, List[Tuple[str, str]]] = defaultdict(list)
        
        for mod_id, mod in graph.mods.items():
            if mod.version:
                key = mod.name.lower()
                version_groups[key].append((mod_id, mod.version))
        
        # Find groups with multiple versions
        for name, versions in version_groups.items():
            if len(versions) > 1:
                unique_versions = list(set(v[1] for v in versions))
                if len(unique_versions) > 1:
                    # Get mod info for conflict
                    mod_ids = [v[0] for v in versions]
                    first_mod = graph.mods.get(mod_ids[0])
                    
                    conflicts.append(VersionConflict(
                        mod_id=name,
                        mod_name=first_mod.name if first_mod else name,
                        versions=unique_versions,
                        suggested_resolution=ConflictResolution.USE_NEWEST,
                        resolved_version=max(unique_versions, key=self._version_sort_key)
                    ))
        
        return conflicts
    
    def _version_sort_key(self, version: str) -> Tuple[int, ...]:
        """Generate sort key for version strings."""
        try:
            # Simple version parsing (e.g., "1.2.3" -> (1, 2, 3))
            parts = version.replace("-", ".").split(".")
            return tuple(int(p) for p in parts if p.isdigit())
        except (ValueError, AttributeError):
            return (0,)
    
    def _find_missing_dependencies(
        self,
        graph: DependencyGraph
    ) -> List[ModDependency]:
        """Find dependencies that are not in the modpack."""
        missing = []
        
        for mod_id, mod in graph.mods.items():
            for dep in mod.dependencies:
                # Check if dependency is in the graph
                if dep.mod_id not in graph.mods and dep.dependency_type == DependencyType.REQUIRED:
                    missing.append(dep)
        
        return missing
    
    def _calculate_load_order(self, graph: DependencyGraph) -> List[str]:
        """
        Calculate optimal load order using topological sort.
        
        Mods with no dependencies come first, followed by their dependents.
        """
        # Calculate in-degree for each mod
        # We want dependencies to be loaded BEFORE dependents.
        # Standard topological sort on A->B (A depends on B) gives B then A if we consider edges as "must load before".
        # But our graph.edges are "A depends on B".
        # So A needs B. B must come first.
        # In-degree based on "Depends On" edges:
        # A->B. In-degree(A)=0, In-degree(B)=1.
        # Queue initial: [A]. Pop A. Decrement B. Queue: [B]. Result: A, B. (Dependent, Dependency) -> WRONG.

        # We want to reverse the logic: A depends on B implies B->A dependency edge for load order.
        # Or simpler: count in-degree using reverse_edges (B->A).
        # B->A. In-degree(B)=0, In-degree(A)=1.
        # Queue initial: [B]. Pop B. Decrement A. Queue: [A]. Result: B, A. (Dependency, Dependent) -> CORRECT.

        in_degree = {mod_id: 0 for mod_id in graph.mods}
        for mod_id in graph.mods:
            # Use reverse_edges to count incoming dependencies (i.e. number of mods that must load before this one)
            # Actually, reverse_edges[B] = [A] means A depends on B.
            # If we iterate graph.edges (A->B), we are saying A needs B.
            # So B is a prerequisite for A.
            # We want to find mods that have NO prerequisites first.
            # A mod has no prerequisites if it has no outgoing "depends on" edges?
            # A->B. A has 1 outgoing. B has 0 outgoing.
            # B is a leaf in "Depends On" graph.
            # Topological sort usually processes nodes with in-degree 0.
            # If we reverse the graph (B->A, B is prerequisite for A), then B has in-degree 0.
            pass

        # Let's count "how many unsatisfied dependencies does this mod have?"
        # If A depends on B (A->B), A has 1 dependency. B has 0.
        # We should load B first.
        # So we want to pick mods with 0 unsatisfied dependencies.
        # That corresponds to out-degree in "Depends On" graph (A->B).
        # A has out-degree 1. B has out-degree 0.
        # So we pick B.
        # When B is picked, we satisfy dependency for A. A's count becomes 0. Pick A.
        # So we need to track out-degree.

        dependency_count = {mod_id: 0 for mod_id in graph.mods}
        dependents_map = defaultdict(list) # Who depends on key?

        for mod_id in graph.mods:
            dependencies = graph.edges.get(mod_id, [])
            dependency_count[mod_id] = len(dependencies)
            for dep_id in dependencies:
                dependents_map[dep_id].append(mod_id)
        
        # Start with mods that have no dependencies (out-degree 0)
        queue = [mod_id for mod_id, count in dependency_count.items() if count == 0]
        load_order = []
        
        while queue:
            # Sort to ensure consistent ordering
            queue.sort(key=lambda x: graph.mods.get(x, ModInfo(mod_id=x, name=x)).name)
            current = queue.pop(0)
            load_order.append(current)
            
            # For every mod that depends on current, decrement their dependency count
            for dependent in dependents_map.get(current, []):
                dependency_count[dependent] -= 1
                if dependency_count[dependent] == 0:
                    queue.append(dependent)
        
        # If we haven't visited all mods, there are cycles
        if len(load_order) != len(graph.mods):
            self.logger.warning(
                "Could not calculate full load order - possible circular dependencies"
            )
            # Add remaining mods (those in cycles)
            for mod_id in graph.mods:
                if mod_id not in load_order:
                    load_order.append(mod_id)
        
        return load_order
    
    def _generate_warnings(
        self,
        graph: DependencyGraph,
        circular_deps: List[CircularDependency],
        version_conflicts: List[VersionConflict],
        missing_deps: List[ModDependency]
    ) -> List[str]:
        """Generate warnings based on analysis."""
        warnings = []
        
        if circular_deps:
            warnings.append(
                f"Found {len(circular_deps)} circular dependency(ies) in modpack"
            )
        
        if version_conflicts:
            warnings.append(
                f"Found {len(version_conflicts)} version conflict(s) between mods"
            )
        
        if missing_deps:
            missing_names = [dep.mod_name for dep in missing_deps[:5]]
            if len(missing_deps) > 5:
                missing_names.append(f"and {len(missing_deps) - 5} more")
            warnings.append(
                f"Missing {len(missing_deps)} required dependency(ies): {', '.join(missing_names)}"
            )
        
        return warnings
    
    def resolve_conflicts(
        self,
        result: DependencyAnalysisResult,
        strategy: ConflictResolution = ConflictResolution.USE_NEWEST
    ) -> List[str]:
        """
        Resolve version conflicts and return list of mods to include/exclude.
        
        Args:
            result: The dependency analysis result
            strategy: Resolution strategy to use
            
        Returns:
            List of mod IDs to exclude (empty if all resolved)
        """
        exclude = []
        
        for conflict in result.version_conflicts:
            if strategy == ConflictResolution.EXCLUDE_CONFLICTING:
                # Exclude all but the newest version
                exclude.append(conflict.mod_id)
            elif strategy == ConflictResolution.USE_NEWEST:
                # Already handled in detection
                pass
            elif strategy == ConflictResolution.USE_OLDEST:
                conflict.resolved_version = min(
                    conflict.versions,
                    key=self._version_sort_key
                )
        
        return exclude
    
    def generate_report(self, result: DependencyAnalysisResult) -> Dict[str, Any]:
        """
        Generate a human-readable report of the dependency analysis.
        
        Args:
            result: The dependency analysis result
            
        Returns:
            Dictionary containing the report
        """
        report = {
            "success": result.success,
            "total_mods": len(result.graph.mods),
            "load_order": []
        }
        
        if not result.success:
            report["error"] = result.error_message
            return report
        
        # Add load order with mod names
        for mod_id in result.recommended_load_order:
            mod = result.graph.mods.get(mod_id)
            if mod:
                report["load_order"].append({
                    "id": mod_id,
                    "name": mod.name,
                    "version": mod.version
                })
        
        # Add warnings
        report["warnings"] = result.warnings
        
        # Add circular dependencies
        if result.circular_dependencies:
            report["circular_dependencies"] = [
                {
                    "mods": dep.mods,
                    "description": dep.description
                }
                for dep in result.circular_dependencies
            ]
        
        # Add version conflicts
        if result.version_conflicts:
            report["version_conflicts"] = [
                {
                    "mod_id": conflict.mod_id,
                    "mod_name": conflict.mod_name,
                    "versions": conflict.versions,
                    "resolved_version": conflict.resolved_version,
                    "suggested_resolution": conflict.suggested_resolution.value
                }
                for conflict in result.version_conflicts
            ]
        
        # Add missing dependencies
        if result.missing_dependencies:
            report["missing_dependencies"] = [
                {
                    "id": dep.mod_id,
                    "name": dep.mod_name,
                    "type": dep.dependency_type.value
                }
                for dep in result.missing_dependencies
            ]
        
        return report


# Singleton instance
mod_dependency_analyzer = ModDependencyAnalyzer()
