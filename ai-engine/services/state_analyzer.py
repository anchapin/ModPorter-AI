"""
State Analyzer Service
Analyzes state management differences between Java mods and Bedrock addons
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
import json
from pathlib import Path

logger = logging.getLogger(__name__)


class StorageType(Enum):
    """Types of state storage in Minecraft."""
    # Java mod storage
    JAVA_FIELD = "java_field"                    # Instance field
    JAVA_STATIC_FIELD = "java_static_field"      # Static field
    JAVA_PERSISTENT = "java_persistent"          # NBT persistent data
    JAVA_WORLD_DATA = "java_world_data"           # World stored data
    
    # Bedrock storage
    BEDROCK_COMPONENT = "bedrock_component"       # Entity/block component
    BEDROCK_STORAGE = "bedrock_storage"          # Custom storage
    BEDROCK_LOOT_TABLE = "bedrock_loot_table"    # Loot table pools
    BEDROCK_TAG = "bedrock_tag"                   # Data-driven tags
    BEDROCK_SCOREBOARD = "bedrock_scoreboard"     # Scoreboard objectives
    
    # Unsupported
    UNSUPPORTED = "unsupported"


@dataclass
class StateVariable:
    """Represents a state variable in a mod."""
    name: str
    java_type: str
    initial_value: Any
    is_static: bool
    is_persistent: bool
    file_path: str
    line_number: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "java_type": self.java_type,
            "initial_value": str(self.initial_value),
            "is_static": self.is_static,
            "is_persistent": self.is_persistent,
            "file_path": self.file_path,
            "line_number": self.line_number,
        }


@dataclass
class StateMapping:
    """Maps a Java state variable to Bedrock storage."""
    java_var: StateVariable
    bedrock_storage_type: StorageType
    bedrock_location: str  # Path to component/storage
    preservation_status: str  # "preserved", "transformed", "lost", "unsupported"
    notes: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "java_variable": self.java_var.to_dict(),
            "bedrock_storage": {
                "type": self.bedrock_storage_type.value,
                "location": self.bedrock_location,
            },
            "preservation_status": self.preservation_status,
            "notes": self.notes,
        }


# Java type to Bedrock storage type mapping
JAVA_TYPE_MAPPINGS: Dict[str, Dict[str, Any]] = {
    # Primitives
    "int": {
        "bedrock_type": "minecraft:integer",
        "storage_types": [StorageType.BEDROCK_COMPONENT, StorageType.BEDROCK_SCOREBOARD],
        "description": "Integer value",
    },
    "float": {
        "bedrock_type": "minecraft:number",
        "storage_types": [StorageType.BEDROCK_COMPONENT],
        "description": "Float value",
    },
    "boolean": {
        "bedrock_type": "minecraft:boolean",
        "storage_types": [StorageType.BEDROCK_COMPONENT],
        "description": "Boolean value",
    },
    "String": {
        "bedrock_type": "minecraft:text",
        "storage_types": [StorageType.BEDROCK_COMPONENT, StorageType.BEDROCK_STORAGE],
        "description": "Text value",
    },
    
    # Minecraft types
    "ItemStack": {
        "bedrock_type": "minecraft:item",
        "storage_types": [StorageType.BEDROCK_COMPONENT, StorageType.BEDROCK_LOOT_TABLE],
        "description": "Item with count, damage, NBT",
    },
    "BlockPos": {
        "bedrock_type": "minecraft:position",
        "storage_types": [StorageType.BEDROCK_COMPONENT],
        "description": "3D position",
    },
    "Vec3": {
        "bedrock_type": "minecraft:position",
        "storage_types": [StorageType.BEDROCK_COMPONENT],
        "description": "3D vector",
    },
    "UUID": {
        "bedrock_type": "minecraft:Uuid",
        "storage_types": [StorageType.BEDROCK_COMPONENT],
        "description": "Unique identifier",
    },
    "NBTTagCompound": {
        "bedrock_type": "minecraft:custom_data",
        "storage_types": [StorageType.BEDROCK_STORAGE, StorageType.BEDROCK_COMPONENT],
        "description": "Complex NBT data",
    },
    "List": {
        "bedrock_type": "minecraft:custom_data",
        "storage_types": [StorageType.BEDROCK_STORAGE],
        "description": "List/array data",
    },
    "Map": {
        "bedrock_type": "minecraft:custom_data",
        "storage_types": [StorageType.BEDROCK_STORAGE],
        "description": "Key-value pairs",
    },
    
    # Entity types
    "Entity": {
        "bedrock_type": "minecraft:entity",
        "storage_types": [StorageType.BEDROCK_COMPONENT],
        "description": "Entity reference",
    },
    "Player": {
        "bedrock_type": "minecraft:entity",
        "storage_types": [StorageType.BEDROCK_COMPONENT],
        "description": "Player reference",
    },
    
    # Unsupported
    "World": {
        "bedrock_type": None,
        "storage_types": [],
        "description": "World access - not directly supported",
    },
    "Server": {
        "bedrock_type": None,
        "storage_types": [],
        "description": "Server access - not directly supported",
    },
}


class StateAnalyzer:
    """
    Analyzes state management differences between Java and Bedrock.
    """
    
    def __init__(self):
        self.java_mappings = JAVA_TYPE_MAPPINGS.copy()
        
    def detect_storage_type(self, java_type: str, var_name: str = "") -> str:
        """
        Detect the Bedrock storage type for a Java variable type.
        
        Args:
            java_type: The Java type of the variable
            var_name: Optional variable name for additional context
            
        Returns:
            Storage type as string or "unsupported"
        """
        # Check exact type match
        if java_type in self.java_mappings:
            mapping = self.java_mappings[java_type]
            if mapping.get("bedrock_type"):
                return mapping["storage_types"][0].value if mapping["storage_types"] else "unsupported"
        
        # Try to infer from type name
        type_lower = java_type.lower()
        
        # Primitives
        if type_lower in ["int", "integer", "long", "short", "byte"]:
            return StorageType.BEDROCK_COMPONENT.value
        elif type_lower in ["float", "double"]:
            return StorageType.BEDROCK_COMPONENT.value
        elif type_lower == "boolean":
            return StorageType.BEDROCK_COMPONENT.value
        elif type_lower == "string":
            return StorageType.BEDROCK_COMPONENT.value
        
        # Collections
        if "list" in type_lower or "array" in type_lower:
            return StorageType.BEDROCK_STORAGE.value
        elif "map" in type_lower or "dict" in type_lower:
            return StorageType.BEDROCK_STORAGE.value
        elif "set" in type_lower:
            return StorageType.BEDROCK_STORAGE.value
        
        # Check for Minecraft classes
        if "item" in type_lower:
            return StorageType.BEDROCK_COMPONENT.value
        elif "block" in type_lower:
            return StorageType.BEDROCK_COMPONENT.value
        elif "entity" in type_lower:
            return StorageType.BEDROCK_COMPONENT.value
        elif "player" in type_lower:
            return StorageType.BEDROCK_COMPONENT.value
        elif "world" in type_lower:
            return StorageType.UNSUPPORTED.value
        
        # Unknown
        return StorageType.BEDROCK_STORAGE.value
    
    def analyze_java_state(
        self, 
        java_files: List[Path]
    ) -> List[StateVariable]:
        """
        Analyze Java source files for state variables.
        
        Args:
            java_files: List of Java source file paths
            
        Returns:
            List of StateVariable objects
        """
        import ast
        
        state_vars = []
        
        for java_file in java_files:
            try:
                content = java_file.read_text(encoding="utf-8")
                tree = ast.parse(content)
                
                for node in ast.walk(tree):
                    # Class fields
                    if isinstance(node, ast.AnnAssign):
                        if isinstance(node.target, ast.Name):
                            var_name = node.target.id
                            
                            # Skip methods and constructors
                            if var_name in ["__init__", "__str__", "__repr__"]:
                                continue
                            
                            # Determine type
                            java_type = "unknown"
                            if node.annotation:
                                if isinstance(node.annotation, ast.Name):
                                    java_type = node.annotation.id
                                elif isinstance(node.annotation, ast.Subscript):
                                    java_type = ast.unparse(node.annotation)
                            
                            # Check for static
                            is_static = False
                            
                            # Check for initial value
                            initial_value = None
                            if node.value:
                                initial_value = ast.unparse(node.value)
                            
                            state_vars.append(StateVariable(
                                name=var_name,
                                java_type=java_type,
                                initial_value=initial_value,
                                is_static=is_static,
                                is_persistent=False,  # Would need deeper analysis
                                file_path=str(java_file),
                                line_number=node.lineno or 0,
                            ))
                    
                    # Simple assignments (type inference needed)
                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                var_name = target.id
                                
                                # Skip common non-state names
                                if var_name.startswith("_") or var_name in [
                                    "logger", "LOGGER", "instance", "INSTANCE"
                                ]:
                                    continue
                                
                                state_vars.append(StateVariable(
                                    name=var_name,
                                    java_type="unknown",
                                    initial_value=ast.unparse(node.value) if node.value else None,
                                    is_static=False,
                                    is_persistent=False,
                                    file_path=str(java_file),
                                    line_number=node.lineno or 0,
                                ))
                                
            except Exception as e:
                logger.warning(f"Failed to parse {java_file}: {e}")
        
        return state_vars
    
    def analyze_bedrock_state(
        self, 
        bedrock_path: Path
    ) -> Dict[str, Any]:
        """
        Analyze Bedrock behavior pack for state storage.
        
        Args:
            bedrock_path: Path to Bedrock behavior pack
            
        Returns:
            Dict of state storage locations
        """
        state_locations = {
            "components": [],
            "storage": [],
            "loot_tables": [],
            "tags": [],
            "scoreboard": [],
        }
        
        # Find all JSON files
        json_files = list(bedrock_path.rglob("*.json"))
        
        for json_file in json_files:
            try:
                content = json_file.read_text(encoding="utf-8")
                data = json.loads(content)
                
                # Extract components
                if isinstance(data, dict):
                    for key, value in data.items():
                        if key.startswith("minecraft:"):
                            state_locations["components"].append({
                                "name": key,
                                "file": str(json_file.relative_to(bedrock_path)),
                            })
                
                # Check for storage definitions
                if "storage" in data:
                    for storage_name in data["storage"]:
                        state_locations["storage"].append({
                            "name": storage_name,
                            "file": str(json_file.relative_to(bedrock_path)),
                        })
                
                # Check for loot tables
                if "pools" in data:
                    state_locations["loot_tables"].append({
                        "name": str(json_file.relative_to(bedrock_path)),
                        "file": str(json_file.relative_to(bedrock_path)),
                    })
                        
            except Exception as e:
                logger.warning(f"Failed to parse {json_file}: {e}")
        
        return state_locations
    
    def map_state_variables(
        self,
        java_vars: List[StateVariable],
        bedrock_state: Dict[str, Any]
    ) -> List[StateMapping]:
        """
        Map Java state variables to Bedrock storage.
        
        Args:
            java_vars: List of Java state variables
            bedrock_state: Bedrock state locations
            
        Returns:
            List of StateMapping objects
        """
        mappings = []
        
        for java_var in java_vars:
            # Determine storage type
            storage_type = self.detect_storage_type(java_var.java_type, java_var.name)
            
            # Determine preservation status
            preservation = "preserved"
            notes = ""
            
            if storage_type == StorageType.UNSUPPORTED.value:
                preservation = "unsupported"
                notes = f"Java type '{java_var.java_type}' has no Bedrock equivalent"
            elif java_var.java_type == "unknown":
                preservation = "transformed"
                notes = "Type unknown - manual review required"
            else:
                # Check if we have matching storage
                bedrock_storages = bedrock_state.get("components", [])
                if not bedrock_storages:
                    preservation = "lost"
                    notes = "No equivalent Bedrock storage found"
            
            mappings.append(StateMapping(
                java_var=java_var,
                bedrock_storage_type=StorageType(storage_type),
                bedrock_location=self._determine_location(java_var, storage_type),
                preservation_status=preservation,
                notes=notes,
            ))
        
        return mappings
    
    def _determine_location(self, java_var: StateVariable, storage_type: str) -> str:
        """Determine the Bedrock storage location for a variable."""
        var_name = java_var.name.lower()
        
        if storage_type == StorageType.BEDROCK_COMPONENT.value:
            # Map common variable names to components
            if "health" in var_name or "hp" in var_name:
                return "minecraft:health"
            elif "age" in var_name or "tick" in var_name:
                return "minecraft:age"
            elif "owner" in var_name:
                return "minecraft:owner"
            elif "variant" in var_name:
                return "minecraft:variant"
            elif "color" in var_name:
                return "minecraft:color"
            else:
                return f"custom:{java_var.name}"
        
        elif storage_type == StorageType.BEDROCK_STORAGE.value:
            return f"storage:.{java_var.name}"
        
        elif storage_type == StorageType.BEDROCK_LOOT_TABLE.value:
            return f"loot_tables/{java_var.name}.json"
        
        elif storage_type == StorageType.BEDROCK_SCOREBOARD.value:
            return f"scoreboard:objectives/{java_var.name}"
        
        return "unknown"
    
    def get_preservation_summary(
        self, 
        mappings: List[StateMapping]
    ) -> Dict[str, Any]:
        """
        Get a summary of state preservation.
        
        Args:
            mappings: List of state mappings
            
        Returns:
            Summary dict
        """
        total = len(mappings)
        if total == 0:
            return {
                "total": 0,
                "preserved": 0,
                "transformed": 0,
                "lost": 0,
                "unsupported": 0,
                "preservation_rate": 0.0,
            }
        
        preserved = sum(1 for m in mappings if m.preservation_status == "preserved")
        transformed = sum(1 for m in mappings if m.preservation_status == "transformed")
        lost = sum(1 for m in mappings if m.preservation_status == "lost")
        unsupported = sum(1 for m in mappings if m.preservation_status == "unsupported")
        
        return {
            "total": total,
            "preserved": preserved,
            "transformed": transformed,
            "lost": lost,
            "unsupported": unsupported,
            "preservation_rate": (preserved / total) * 100 if total > 0 else 0.0,
        }


def analyze_state(
    java_files: List[Path],
    bedrock_path: Path
) -> Dict[str, Any]:
    """
    Convenience function for state analysis.
    
    Args:
        java_files: List of Java source files
        bedrock_path: Path to Bedrock behavior pack
        
    Returns:
        Analysis results
    """
    analyzer = StateAnalyzer()
    
    java_vars = analyzer.analyze_java_state(java_files)
    bedrock_state = analyzer.analyze_bedrock_state(bedrock_path)
    mappings = analyzer.map_state_variables(java_vars, bedrock_state)
    
    return {
        "java_variables": [v.to_dict() for v in java_vars],
        "bedrock_state": bedrock_state,
        "mappings": [m.to_dict() for m in mappings],
        "summary": analyzer.get_preservation_summary(mappings),
    }
