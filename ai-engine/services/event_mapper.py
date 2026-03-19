"""
Event Mapper Service
Maps Java (Forge/Fabric) events to Bedrock events
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


# Comprehensive Java to Bedrock event mapping
JAVA_TO_BEDROCK_EVENT_MAP: Dict[str, Dict[str, str]] = {
    # Block events
    "block_placed": {
        "java": ["onBlockPlace", "onBlockPlaced", "onPlace", "OnBlockPlaceEvent"],
        "bedrock": "minecraft:block_placed",
        "description": "Called when a block is placed",
    },
    "block_broken": {
        "java": ["onBlockBreak", "onBlockBroken", "onBreak", "OnBlockBreakEvent"],
        "bedrock": "minecraft:block_broken",
        "description": "Called when a block is broken",
    },
    "block_interacted": {
        "java": ["onBlockRightClick", "onBlockInteract", "OnBlockInteractEvent"],
        "bedrock": "minecraft:block_interacted_with",
        "description": "Called when a block is interacted with",
    },
    "block_updated": {
        "java": ["onBlockUpdate", "OnBlockUpdateEvent", "onBlockChanged"],
        "bedrock": "minecraft:block_changed",
        "description": "Called when a block is updated",
    },
    
    # Item events
    "item_used": {
        "java": ["onItemUse", "onItemUseFirst", "OnItemUseEvent"],
        "bedrock": "minecraft:item_used",
        "description": "Called when an item is used",
    },
    "item_consumed": {
        "java": ["onItemConsume", "onItemEat", "OnItemConsumeEvent"],
        "bedrock": "minecraft:item_consumed",
        "description": "Called when an item is consumed",
    },
    "item_crafted": {
        "java": ["onItemCrafted", "OnItemCraftedEvent"],
        "bedrock": "minecraft:item_crafted",
        "description": "Called when an item is crafted",
    },
    "item_damaged": {
        "java": ["onItemDamage", "OnItemDamageEvent"],
        "bedrock": "minecraft:item_damaged",
        "description": "Called when an item is damaged",
    },
    
    # Entity events
    "entity_spawned": {
        "java": ["onEntitySpawn", "OnEntitySpawnEvent", "onLivingSpawn"],
        "bedrock": "minecraft:entity_spawned",
        "description": "Called when an entity spawns",
    },
    "entity_death": {
        "java": ["onEntityDeath", "OnEntityDeathEvent", "onDeath", "OnDeathEvent"],
        "bedrock": "minecraft:entity_death",
        "description": "Called when an entity dies",
    },
    "entity_attacked": {
        "java": ["onEntityAttack", "OnEntityAttackEvent", "onAttack"],
        "bedrock": "minecraft:entity_attacked",
        "description": "Called when an entity is attacked",
    },
    "entity_interact": {
        "java": ["onEntityInteract", "OnEntityInteractEvent"],
        "bedrock": "minecraft:entity_interact",
        "description": "Called when interacting with an entity",
    },
    
    # Player events
    "player_joined": {
        "java": ["onPlayerJoin", "onPlayerLoggedIn", "OnPlayerJoinEvent"],
        "bedrock": "minecraft:player_joined",
        "description": "Called when a player joins",
    },
    "player_left": {
        "java": ["onPlayerLeave", "onPlayerLoggedOut", "OnPlayerLeaveEvent"],
        "bedrock": "minecraft:player_left",
        "description": "Called when a player leaves",
    },
    "player_respawn": {
        "java": ["onPlayerRespawn", "OnPlayerRespawnEvent"],
        "bedrock": "minecraft:player_respawn",
        "description": "Called when a player respawns",
    },
    "player_death": {
        "java": ["onPlayerDeath", "OnPlayerDeathEvent"],
        "bedrock": "minecraft:player_died",
        "description": "Called when a player dies",
    },
    "player_level_up": {
        "java": ["onPlayerLevelUp", "OnPlayerLevelChangeEvent"],
        "bedrock": "minecraft:player_leveled_up",
        "description": "Called when a player levels up",
    },
    "player_moved": {
        "java": ["onPlayerMove", "OnPlayerMoveEvent", "onPlayerTeleport"],
        "bedrock": "minecraft:player_moved",
        "description": "Called when a player moves",
    },
    
    # Tick events
    "tick": {
        "java": ["onTick", "onServerTick", "OnTickEvent", "update"],
        "bedrock": "minecraft:tick",
        "description": "Called every tick",
    },
    
    # World events
    "world_load": {
        "java": ["onWorldLoad", "OnWorldLoadEvent", "onLoad"],
        "bedrock": "minecraft:world_loaded",
        "description": "Called when world loads",
    },
    "world_unload": {
        "java": ["onWorldUnload", "OnWorldUnloadEvent"],
        "bedrock": "minecraft:world_unloaded",
        "description": "Called when world unloads",
    },
    
    # Custom event patterns
    "custom": {
        "java": [],
        "bedrock": None,
        "description": "Custom event - requires manual mapping",
    },
}


# Reverse map for Bedrock to Java
BEDROCK_TO_JAVA_EVENT_MAP: Dict[str, List[str]] = {}
for category, mapping in JAVA_TO_BEDROCK_EVENT_MAP.items():
    bedrock_event = mapping.get("bedrock")
    if bedrock_event:
        BEDROCK_TO_JAVA_EVENT_MAP[bedrock_event] = mapping.get("java", [])


@dataclass
class EventMapping:
    """Represents an event mapping between Java and Bedrock."""
    java_event: str
    bedrock_event: str
    category: str
    confidence: float  # 0-1
    requires_custom_implementation: bool = False
    notes: str = ""


class EventMapper:
    """
    Maps Java mod events to Bedrock add-on events.
    """
    
    def __init__(self):
        self.java_to_bedrock = JAVA_TO_BEDROCK_EVENT_MAP.copy()
        self.bedrock_to_java = BEDROCK_TO_JAVA_EVENT_MAP.copy()
        self.custom_mappings: Dict[str, str] = {}
        
    def map_java_event(
        self, 
        event_type: str, 
        method_name: str = ""
    ) -> Optional[str]:
        """
        Map a Java event type to Bedrock event.
        
        Args:
            event_type: The detected event type (e.g., "block_placed")
            method_name: Optional method name for additional context
            
        Returns:
            Bedrock event name or None if no mapping exists
        """
        # Check custom mappings first
        if event_type in self.custom_mappings:
            return self.custom_mappings[event_type]
        
        # Look up in standard mapping
        if event_type in self.java_to_bedrock:
            mapping = self.java_to_bedrock[event_type]
            bedrock_event = mapping.get("bedrock")
            if bedrock_event:
                return bedrock_event
        
        # Try to infer from method name
        if method_name:
            inferred = self._infer_from_method_name(method_name)
            if inferred:
                return inferred
        
        return None
    
    def map_bedrock_event(self, bedrock_event: str) -> List[str]:
        """
        Map a Bedrock event to possible Java events.
        
        Args:
            bedrock_event: The Bedrock event name
            
        Returns:
            List of possible Java event names
        """
        if bedrock_event in self.bedrock_to_java:
            return self.bedrock_to_java[bedrock_event]
        return []
    
    def get_mapping_info(self, event_type: str) -> Optional[Dict]:
        """
        Get detailed mapping information for an event type.
        
        Args:
            event_type: The event type to look up
            
        Returns:
            Mapping info dict or None
        """
        return self.java_to_bedrock.get(event_type)
    
    def get_all_mappings(self) -> List[EventMapping]:
        """
        Get all available event mappings.
        
        Returns:
            List of EventMapping objects
        """
        mappings = []
        for category, mapping in self.java_to_bedrock.items():
            bedrock_event = mapping.get("bedrock")
            if bedrock_event:
                mappings.append(EventMapping(
                    java_event=category,
                    bedrock_event=bedrock_event,
                    category=category,
                    confidence=1.0 if mapping.get("java") else 0.5,
                    requires_custom_implementation=bedrock_event is None,
                    notes=mapping.get("description", ""),
                ))
        return mappings
    
    def add_custom_mapping(
        self, 
        java_event: str, 
        bedrock_event: str,
        category: str = "custom"
    ) -> None:
        """
        Add a custom event mapping.
        
        Args:
            java_event: The Java event name
            bedrock_event: The Bedrock event name
            category: The category of the event
        """
        self.custom_mappings[java_event] = bedrock_event
        self.custom_mappings[category] = bedrock_event
        logger.info(f"Added custom mapping: {java_event} -> {bedrock_event}")
    
    def _infer_from_method_name(self, method_name: str) -> Optional[str]:
        """
        Infer the Bedrock event from a Java method name.
        
        Args:
            method_name: The Java method name
            
        Returns:
            Inferred Bedrock event or None
        """
        name_lower = method_name.lower()
        
        # Common patterns
        patterns = [
            ("place", "minecraft:block_placed"),
            ("break", "minecraft:block_broken"),
            ("use", "minecraft:item_used"),
            ("interact", "minecraft:block_interacted_with"),
            ("join", "minecraft:player_joined"),
            ("leave", "minecraft:player_left"),
            ("death", "minecraft:entity_death"),
            ("die", "minecraft:entity_death"),
            ("attack", "minecraft:entity_attacked"),
            ("tick", "minecraft:tick"),
            ("spawn", "minecraft:entity_spawned"),
            ("init", "minecraft:world_loaded"),
            ("load", "minecraft:world_loaded"),
            ("consume", "minecraft:item_consumed"),
            ("craft", "minecraft:item_crafted"),
            ("respawn", "minecraft:player_respawn"),
            ("level", "minecraft:player_leveled_up"),
            ("move", "minecraft:player_moved"),
        ]
        
        for pattern, bedrock_event in patterns:
            if pattern in name_lower:
                return bedrock_event
        
        return None
    
    def get_unsupported_events(self, java_events: List[str]) -> List[str]:
        """
        Get list of Java events that have no Bedrock equivalent.
        
        Args:
            java_events: List of Java event names
            
        Returns:
            List of unsupported event names
        """
        unsupported = []
        
        for java_event in java_events:
            event_type = self._detect_event_type(java_event)
            mapping = self.java_to_bedrock.get(event_type, {})
            if not mapping.get("bedrock"):
                unsupported.append(java_event)
        
        return unsupported
    
    def _detect_event_type(self, event_name: str) -> str:
        """Detect event type from event name."""
        name_lower = event_name.lower()
        
        if "place" in name_lower:
            return "block_placed"
        elif "break" in name_lower:
            return "block_broken"
        elif "use" in name_lower:
            return "item_used"
        elif "interact" in name_lower:
            return "block_interacted"
        elif "join" in name_lower:
            return "player_joined"
        elif "leave" in name_lower or "quit" in name_lower:
            return "player_left"
        elif "death" in name_lower:
            return "entity_death"
        elif "attack" in name_lower:
            return "entity_attacked"
        elif "tick" in name_lower:
            return "tick"
        elif "spawn" in name_lower:
            return "entity_spawned"
        elif "consume" in name_lower or "eat" in name_lower:
            return "item_consumed"
        elif "craft" in name_lower:
            return "item_crafted"
        elif "respawn" in name_lower:
            return "player_respawn"
        elif "level" in name_lower:
            return "player_level_up"
        elif "move" in name_lower or "teleport" in name_lower:
            return "player_moved"
        elif "load" in name_lower:
            return "world_load"
        elif "unload" in name_lower:
            return "world_unload"
        else:
            return "custom"


def get_event_mapping(event_type: str, method_name: str = "") -> Optional[str]:
    """
    Convenience function to map a Java event to Bedrock.
    
    Args:
        event_type: The detected event type
        method_name: Optional method name for additional context
        
    Returns:
        Bedrock event name or None
    """
    mapper = EventMapper()
    return mapper.map_java_event(event_type, method_name)
