"""Record Mapper for Java 14+ to TypeScript conversion.

This module provides functionality to map Java records to TypeScript interfaces/classes.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from .record_detector import JavaRecord, RecordComponent, RecordMethod, RecordDetector


@dataclass
class TypeScriptRecordOutput:
    """Output TypeScript representation of a Java record."""
    interface_name: str
    interface_body: str
    class_name: Optional[str] = None
    class_body: Optional[str] = None
    jsdoc_comment: Optional[str] = None
    
    def __repr__(self) -> str:
        return f"TypeScriptRecordOutput({self.interface_name})"


class RecordMapper:
    """Maps Java records to TypeScript."""
    
    def __init__(self):
        self.detector = RecordDetector()
        self.mappings: Dict[str, TypeScriptRecordOutput] = {}
    
    def map(self, source: str) -> Dict[str, TypeScriptRecordOutput]:
        """Map all records in source to TypeScript."""
        records = self.detector.detect(source)
        
        self.mappings = {}
        for record in records:
            self.mappings[record.name] = self.map_record(record)
        
        return self.mappings
    
    def map_record(self, record: JavaRecord) -> TypeScriptRecordOutput:
        """Map a single Java record to TypeScript."""
        # Create interface from components
        interface_name = self._to_interface_name(record.name)
        interface_body = self._generate_interface_body(record)
        
        # Generate JSDoc
        jsdoc = self._generate_jsdoc(record)
        
        output = TypeScriptRecordOutput(
            interface_name=interface_name,
            interface_body=interface_body,
            jsdoc_comment=jsdoc
        )
        
        # Add class if record has methods
        if record.methods:
            output.class_name = record.name
            output.class_body = self._generate_class_body(record)
        
        return output
    
    def _to_interface_name(self, record_name: str) -> str:
        """Convert record name to interface name."""
        # Records are typically PascalCase
        return f"I{record_name}" if not record_name.startswith('I') else record_name
    
    def _generate_interface_body(self, record: JavaRecord) -> str:
        """Generate TypeScript interface body from record components."""
        lines = []
        
        for component in record.components:
            field_type = self._convert_type(component.type)
            lines.append(f"    {component.name}: {field_type};")
        
        return "\n".join(lines) if lines else "    // No components"
    
    def _generate_class_body(self, record: JavaRecord) -> str:
        """Generate TypeScript class body if record has methods."""
        lines = [f"export class {record.name} {{"]
        
        # Add constructor from components
        if record.components:
            params = ", ".join(
                f"public {c.name}: {self._convert_type(c.type)}"
                for c in record.components
            )
            lines.append(f"    constructor({params}) {{")
            lines.append("        // Initialize")
            lines.append("    }")
            lines.append("")
        
        # Add methods
        for method in record.methods:
            return_type = self._convert_type(method.return_type)
            lines.append(f"    {method.name}(): {return_type} {{")
            lines.append("        // TODO: implement")
            lines.append("    }")
            lines.append("")
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def _convert_type(self, java_type: str) -> str:
        """Convert Java type to TypeScript."""
        # Handle primitives
        type_map = {
            'int': 'number',
            'long': 'number',
            'float': 'number',
            'double': 'number',
            'boolean': 'boolean',
            'byte': 'number',
            'short': 'number',
            'char': 'string',
            'String': 'string',
            'void': 'void',
        }
        
        return type_map.get(java_type, java_type)
    
    def _generate_jsdoc(self, record: JavaRecord) -> str:
        """Generate JSDoc comment for the record."""
        lines = ["/**"]
        lines.append(f" * Java Record: {record.name}")
        
        if record.components:
            lines.append(" *")
            lines.append(" * Components:")
            for comp in record.components:
                lines.append(f" *   - {comp.name}: {comp.type}")
        
        if record.implements:
            lines.append(" *")
            lines.append(f" * Implements: {', '.join(record.implements)}")
        
        lines.append(" */")
        
        return "\n".join(lines)
    
    def map_to_interface_only(self, record: JavaRecord) -> TypeScriptRecordOutput:
        """Map record to interface only (no class)."""
        interface_name = self._to_interface_name(record.name)
        
        return TypeScriptRecordOutput(
            interface_name=interface_name,
            interface_body=self._generate_interface_body(record),
            jsdoc_comment=self._generate_jsdoc(record)
        )


class RecordEqualityHandler:
    """Handles record equality methods (equals, hashCode, toString)."""
    
    def generate_equals(self, record: JavaRecord) -> str:
        """Generate TypeScript equals method."""
        lines = [
            "equals(other: unknown): boolean {",
            "    if (!(other instanceof " + record.name + ")) return false;"
        ]
        
        for comp in record.components:
            lines.append(f"    if (this.{comp.name} !== other.{comp.name}) return false;")
        
        lines.append("    return true;")
        lines.append("}")
        
        return "\n".join(lines)
    
    def generate_hashcode(self, record: JavaRecord) -> str:
        """Generate TypeScript hashCode method."""
        lines = [
            "hashCode(): number {",
            "    let hash = 0;"
        ]
        
        for i, comp in enumerate(record.components):
            lines.append(f"    hash = hash * 31 + ({self._hash_value(comp.name)});")
        
        lines.append("    return hash;")
        lines.append("}")
        
        return "\n".join(lines)
    
    def generate_tostring(self, record: JavaRecord) -> str:
        """Generate TypeScript toString method."""
        fields = ", ".join(
            f"{c.name}=' + this.{c.name} + '"
            for c in record.components
        )
        
        return f"toString(): string {{ return '{record.name}({fields})'; }}"
    
    def _hash_value(self, name: str) -> str:
        """Generate hash value expression for a field."""
        return f"this.{name}.hashCode()"


# Convenience functions
def map_record(record: JavaRecord) -> TypeScriptRecordOutput:
    """Map a single Java record to TypeScript."""
    mapper = RecordMapper()
    return mapper.map_record(record)


def records_to_typescript(source: str) -> Dict[str, TypeScriptRecordOutput]:
    """Convert all records in source to TypeScript."""
    mapper = RecordMapper()
    return mapper.map(source)
