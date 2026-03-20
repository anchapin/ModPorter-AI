"""Sealed Class Mapper for Java 17+ to TypeScript conversion.

This module provides functionality to map Java sealed classes to TypeScript
discriminated unions and type narrowing.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from .sealed_class_detector import SealedClass, PermittedSubclass, SealedClassDetector


@dataclass
class TypeScriptSealedOutput:
    """Output TypeScript representation of a Java sealed class."""
    union_name: str
    union_members: List[str]
    type_guard: Optional[str] = None
    jsdoc_comment: Optional[str] = None
    
    def __repr__(self) -> str:
        return f"TypeScriptSealedOutput({self.union_name}, {len(self.union_members)} members)"


class SealedClassMapper:
    """Maps Java sealed classes to TypeScript."""
    
    def __init__(self):
        self.detector = SealedClassDetector()
        self.mappings: Dict[str, TypeScriptSealedOutput] = {}
    
    def map(self, source: str) -> Dict[str, TypeScriptSealedOutput]:
        """Map all sealed classes in source to TypeScript."""
        sealed_classes = self.detector.detect(source)
        
        self.mappings = {}
        for sealed in sealed_classes:
            subclasses = self.detector.get_subclasses_for(sealed.name)
            self.mappings[sealed.name] = self.map_sealed_class(sealed, subclasses)
        
        return self.mappings
    
    def map_sealed_class(self, sealed: SealedClass, subclasses: List[PermittedSubclass]) -> TypeScriptSealedOutput:
        """Map a single sealed class to TypeScript."""
        # Generate union type from permitted subclasses
        union_members = []
        
        if sealed.permits:
            for permitted in sealed.permits:
                union_members.append(permitted)
        else:
            # If no permits clause, infer from subclasses
            for subclass in subclasses:
                union_members.append(subclass.name)
        
        # Generate type guard function
        type_guard = self._generate_type_guard(sealed.name, union_members)
        
        # Generate JSDoc
        jsdoc = self._generate_jsdoc(sealed, subclasses)
        
        return TypeScriptSealedOutput(
            union_name=sealed.name,
            union_members=union_members,
            type_guard=type_guard,
            jsdoc_comment=jsdoc
        )
    
    def _generate_type_guard(self, sealed_name: str, members: List[str]) -> str:
        """Generate TypeScript type guard function."""
        if not members:
            return ""
        
        lines = [
            f"export function is{sealed_name}(value: unknown): value is {sealed_name} {{",
        ]
        
        # Generate type checks
        checks = []
        for member in members:
            checks.append(f"value instanceof {member}")
        
        lines.append(f"    return {' || '.join(checks)};")
        lines.append("}")
        
        return "\n".join(lines)
    
    def _generate_jsdoc(self, sealed: SealedClass, subclasses: List[PermittedSubclass]) -> str:
        """Generate JSDoc comment for the sealed class."""
        lines = ["/**"]
        lines.append(f" * Java Sealed Class: {sealed.name}")
        
        if sealed.is_interface:
            lines.append(" * (sealed interface)")
        
        if sealed.permits:
            lines.append(" *")
            lines.append(" * Permitted types:")
            for p in sealed.permits:
                lines.append(f" *   - {p}")
        
        lines.append(" */")
        
        return "\n".join(lines)
    
    def generate_discriminated_union(self, sealed: SealedClass, subclasses: List[Dict]) -> str:
        """Generate discriminated union type."""
        if not subclasses:
            return f"type {sealed.name} = never;"
        
        lines = [f"export type {sealed.name} = "]
        
        members = []
        for subclass in subclasses:
            subtype = subclass.get('name', 'Unknown')
            # Add discriminant property
            discriminant = subclass.get('discriminant', subtype.lower())
            members.append(f"    {{ __typename: '{discriminant}', {subtype}Specific: any }}")
        
        lines.append(" |\n".join(members) + ";")
        
        return "\n".join(lines)


class TypeHierarchyAnalyzer:
    """Analyzes sealed class type hierarchy."""
    
    def __init__(self):
        self.detector = SealedClassDetector()
    
    def build_hierarchy_tree(self, source: str) -> Dict[str, Any]:
        """Build a tree representing the sealed class hierarchy."""
        sealed_classes = self.detector.detect(source)
        permitted = self.detector.permitted_subclasses
        
        tree = {}
        for sealed in sealed_classes:
            subclasses = self.detector.get_subclasses_for(sealed.name)
            tree[sealed.name] = {
                'type': 'sealed',
                'is_interface': sealed.is_interface,
                'permits': sealed.permits,
                'subclasses': [
                    {
                        'name': s.name,
                        'is_final': s.is_final,
                        'is_non_sealed': s.is_non_sealed,
                        'extends': s.extends
                    }
                    for s in subclasses
                ]
            }
        
        return tree
    
    def generate_exhaustive_switch(self, sealed_name: str, cases: List[str]) -> str:
        """Generate exhaustive switch statement for type narrowing."""
        lines = [
            f"function handle{sealed_name}(value: {sealed_name}): void {{",
            "    switch (value.__typename) {"
        ]
        
        for case in cases:
            lines.append(f"        case '{case}':")
            lines.append(f"            // Handle {case}")
            lines.append("            break;")
        
        # Default case for exhaustiveness
        lines.append("        default:")
        lines.append("            // Exhaustiveness check")
        lines.append("            const _exhaustive: never = value;")
        lines.append("            throw new Error(`Unhandled case: ${{_exhaustive}}`);")
        
        lines.append("    }")
        lines.append("}")
        
        return "\n".join(lines)
    
    def validate_exhaustiveness(self, sealed: SealedClass, handled_types: List[str]) -> bool:
        """Check if all permitted types are handled in switch."""
        all_permits = set(sealed.permits) if sealed.permits else set()
        handled = set(handled_types)
        
        # Check if all permitted types are handled
        return all_permits.issubset(handled)


# Convenience functions
def map_sealed_class(sealed: SealedClass, subclasses: List[PermittedSubclass]) -> TypeScriptSealedOutput:
    """Map a single sealed class to TypeScript."""
    mapper = SealedClassMapper()
    return mapper.map_sealed_class(sealed, subclasses)


def sealed_classes_to_typescript(source: str) -> Dict[str, TypeScriptSealedOutput]:
    """Convert all sealed classes in source to TypeScript."""
    mapper = SealedClassMapper()
    return mapper.map(source)
