"""
Pattern Matching Enhancement module for Minecraft mod structures.

This module provides:
- Extended pattern library for Minecraft mod structures
- Pattern matching for items/blocks/entities
- Inheritance hierarchy pattern recognition
- Pattern confidence scoring
- Pattern recommendation system
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import re


class PatternType(Enum):
    """Types of patterns for Minecraft mod structures."""
    BLOCK = "block"
    ITEM = "item"
    ENTITY = "entity"
    RECIPE = "recipe"
    DIMENSION = "dimension"
    GUI = "gui"
    EVENT = "event"
    CUSTOM = "custom"


@dataclass
class PatternMatch:
    """Represents a matched pattern."""
    pattern_id: str
    pattern_type: PatternType
    confidence: float
    matched_text: str
    translation: str
    context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MinecraftPattern:
    """Represents a Minecraft mod pattern."""
    pattern_id: str
    pattern_type: PatternType
    java_pattern: str
    bedrock_pattern: str
    description: str
    examples: List[str] = field(default_factory=list)
    confidence: float = 1.0
    priority: int = 0
    requires_context: List[str] = field(default_factory=list)


class PatternMatcher:
    """
    Pattern matching system for Minecraft mod structures.
    
    Provides:
    - Extended pattern library for common mod patterns
    - Confidence scoring for matches
    - Context-aware pattern recommendations
    """
    
    def __init__(self):
        self.logger = None
        self.patterns: Dict[str, MinecraftPattern] = {}
        self.pattern_hierarchy: Dict[str, List[str]] = {}  # parent -> children
        self._initialize_patterns()
        
    def set_logger(self, logger):
        """Set the logger for this matcher."""
        self.logger = logger
        
    def _initialize_patterns(self):
        """Initialize the pattern library with common Minecraft mod patterns."""
        
        # Block patterns
        block_patterns = [
            MinecraftPattern(
                pattern_id="block_basic",
                pattern_type=PatternType.BLOCK,
                java_pattern=r"public\s+static\s+final\s+(?:Block|registry\.RegistryObject<Block>)\s+(\w+)",
                bedrock_pattern="BP/blocks/${1}.json",
                description="Basic block registration",
                examples=["public static final Block DIRT_BLOCK"],
                priority=10
            ),
            MinecraftPattern(
                pattern_id="block_state",
                pattern_type=PatternType.BLOCK,
                java_pattern=r"@Override\s+public\s+BlockState(?:<.*>)?\s+getStateForPlacement",
                bedrock_pattern="BP/blocks/${1}/description.json",
                description="Block state provider",
                priority=8
            ),
            MinecraftPattern(
                pattern_id="block_tile_entity",
                pattern_type=PatternType.BLOCK,
                java_pattern=r"class\s+(\w+)\s+extends\s+(?:Block|TileEntity)",
                bedrock_pattern="BP/blocks/${1}/block.json + BE entity",
                description="Block with tile entity",
                priority=7
            ),
            MinecraftPattern(
                pattern_id="block_properties",
                pattern_type=PatternType.BLOCK,
                java_pattern=r"\.(?:setDefaultTab|properties|strength|hardness)\([^)]+\)",
                bedrock_pattern="BP/blocks/${1}/block.json: destructible -> true",
                description="Block properties",
                priority=5
            ),
        ]
        
        # Item patterns
        item_patterns = [
            MinecraftPattern(
                pattern_id="item_basic",
                pattern_type=PatternType.ITEM,
                java_pattern=r"public\s+static\s+final\s+(?:Item|registry\.RegistryObject<Item>)\s+(\w+)",
                bedrock_pattern="BP/items/${1}.json",
                description="Basic item registration",
                examples=["public static final Item DIAMOND_SWORD"],
                priority=10
            ),
            MinecraftPattern(
                pattern_id="item_block",
                pattern_type=PatternType.ITEM,
                java_pattern=r"class\s+(\w+)\s+extends\s+BlockItem",
                bedrock_pattern="BP/items/${1}.json + BP/blocks/${1}.json",
                description="Item that is also a block",
                priority=9
            ),
            MinecraftPattern(
                pattern_id="item_tool",
                pattern_type=PatternType.ITEM,
                java_pattern=r"class\s+(\w+)\s+extends\s+(?:Pickaxe|Sword|Axe|Hoe|Shovel)",
                bedrock_pattern="BP/items/${1}.json with tier",
                description="Tool item",
                priority=8
            ),
            MinecraftPattern(
                pattern_id="item_armor",
                pattern_type=PatternType.ITEM,
                java_pattern=r"class\s+(\w+)\s+extends\s+(?:ArmorItem|Item)",
                bedrock_pattern="BP/items/${1}.json with armor",
                description="Armor item",
                priority=8
            ),
        ]
        
        # Entity patterns
        entity_patterns = [
            MinecraftPattern(
                pattern_id="entity_mob",
                pattern_type=PatternType.ENTITY,
                java_pattern=r"class\s+(\w+)\s+extends\s+(?:Entity|Mob|Creature)",
                bedrock_pattern="BP/entities/${1}.json",
                description="Basic entity/mob",
                examples=["class Zombie extends Mob"],
                priority=10
            ),
            MinecraftPattern(
                pattern_id="entity_rideable",
                pattern_type=PatternType.ENTITY,
                java_pattern=r"class\s+(\w+)\s+extends\s+(?:Entity|Mob).*implements\s+Rideable",
                bedrock_pattern="BP/entities/${1}.json with rideable component",
                description="Rideable entity",
                priority=8
            ),
            MinecraftPattern(
                pattern_id="entity_tamed",
                pattern_type=PatternType.ENTITY,
                java_pattern=r"class\s+(\w+)\s+extends\s+(?:Entity|TameableAnimal)",
                bedrock_pattern="BP/entities/${1}.json with tameable",
                description="Tameable entity",
                priority=8
            ),
        ]
        
        # Recipe patterns
        recipe_patterns = [
            MinecraftPattern(
                pattern_id="recipe_shaped",
                pattern_type=PatternType.RECIPE,
                java_pattern=r"ShapedRecipe\s*\.\s*shaped\s*\(",
                bedrock_pattern="BP/recipes/${1}.json (shaped)",
                description="Shaped crafting recipe",
                priority=9
            ),
            MinecraftPattern(
                pattern_id="recipe_shapeless",
                pattern_type=PatternType.RECIPE,
                java_pattern=r"ShapelessRecipe\s*\.\s*shapeless\s*\(",
                bedrock_pattern="BP/recipes/${1}.json (shapeless)",
                description="Shapeless crafting recipe",
                priority=9
            ),
            MinecraftPattern(
                pattern_id="recipe_smoking",
                pattern_type=PatternType.RECIPE,
                java_pattern=r"CookingRecipe\s*\.\s*smoking\s*\(",
                bedrock_pattern="BP/recipes/${1}.json (smoking)",
                description="Smoking recipe",
                priority=7
            ),
        ]
        
        # Dimension patterns
        dimension_patterns = [
            MinecraftPattern(
                pattern_id="dimension",
                pattern_type=PatternType.DIMENSION,
                java_pattern=r"class\s+(\w+)\s+extends\s+Dimension",
                bedrock_pattern="BP/dimensions/${1}.json",
                description="Custom dimension",
                priority=8
            ),
        ]
        
        # Event patterns
        event_patterns = [
            MinecraftPattern(
                pattern_id="event_handler",
                pattern_type=PatternType.EVENT,
                java_pattern=r"@(?:SubscribeEvent|ModEventHandler)\s+public\s+void\s+(\w+)",
                bedrock_pattern="JS: register('event', (event) => {})",
                description="Event handler method",
                examples=["@SubscribeEvent public void onInit"],
                priority=10
            ),
            MinecraftPattern(
                pattern_id="event_bus",
                pattern_type=PatternType.EVENT,
                java_pattern=r"MinecraftForge\.EVENT_BUS\.register",
                bedrock_pattern="JS: register for event type",
                description="Event bus registration",
                priority=8
            ),
        ]
        
        # Custom patterns (from inheritance)
        custom_patterns = [
            MinecraftPattern(
                pattern_id="extends_mod",
                pattern_type=PatternType.CUSTOM,
                java_pattern=r"class\s+(\w+)\s+extends\s+(\w+)",
                bedrock_pattern="// Inherits behavior from ${2}",
                description="Class extending another class",
                priority=5
            ),
            MinecraftPattern(
                pattern_id="implements_interface",
                pattern_type=PatternType.CUSTOM,
                java_pattern=r"class\s+(\w+)\s+implements\s+([\w,\s]+)",
                bedrock_pattern="// Implements: ${2}",
                description="Class implementing interface",
                priority=4
            ),
        ]
        
        # Add all patterns
        all_patterns = (block_patterns + item_patterns + entity_patterns + 
                       recipe_patterns + dimension_patterns + event_patterns + 
                       custom_patterns)
        
        for pattern in all_patterns:
            self.patterns[pattern.pattern_id] = pattern
            
    def find_matches(self, java_code: str, context: Dict[str, Any] = None) -> List[PatternMatch]:
        """
        Find all pattern matches in Java code.
        
        Args:
            java_code: Java source code to match against
            context: Additional context for scoring
            
        Returns:
            List of PatternMatch objects
        """
        matches = []
        context = context or {}
        
        for pattern_id, pattern in self.patterns.items():
            try:
                regex = re.compile(pattern.java_pattern, re.MULTILINE)
                for match in regex.finditer(java_code):
                    confidence = self._calculate_confidence(pattern, match, context)
                    
                    if confidence > 0.5:
                        pattern_match = PatternMatch(
                            pattern_id=pattern_id,
                            pattern_type=pattern.pattern_type,
                            confidence=confidence,
                            matched_text=match.group(0),
                            translation=self._translate_match(pattern, match),
                            context=context
                        )
                        matches.append(pattern_match)
                        
            except re.error as e:
                if self.logger:
                    self.logger.warning(f"Regex error in pattern {pattern_id}: {e}")
                    
        # Sort by confidence
        matches.sort(key=lambda x: x.confidence, reverse=True)
        return matches
        
    def _calculate_confidence(self, pattern: MinecraftPattern, match: re.Match, 
                             context: Dict[str, Any]) -> float:
        """Calculate confidence score for a pattern match."""
        base_confidence = pattern.confidence
        
        # Boost confidence for exact examples
        if pattern.examples and match.group(0) in pattern.examples:
            return min(1.0, base_confidence * 1.2)
            
        # Check context requirements
        for req in pattern.requires_context:
            if req not in context:
                base_confidence *= 0.8
                
        # Boost priority patterns
        if pattern.priority >= 8:
            base_confidence *= 1.1
            
        return min(1.0, base_confidence)
        
    def _translate_match(self, pattern: MinecraftPattern, match: re.Match) -> str:
        """Translate a matched pattern to Bedrock format."""
        result = pattern.bedrock_pattern
        
        # Replace capture groups
        for i, group in enumerate(match.groups(), 1):
            if group:
                result = result.replace(f"${{{i}}}", group)
                
        return result
        
    def recommend_patterns(self, java_code: str, context: Dict[str, Any] = None) -> List[Tuple[MinecraftPattern, float]]:
        """
        Recommend patterns based on code analysis.
        
        Args:
            java_code: Java source code
            context: Context for recommendations
            
        Returns:
            List of (pattern, score) tuples sorted by relevance
        """
        recommendations = []
        context = context or {}
        
        # Analyze code structure
        code_analysis = self._analyze_code_structure(java_code)
        
        for pattern_id, pattern in self.patterns.items():
            score = self._calculate_recommendation_score(pattern, code_analysis, context)
            if score > 0.3:
                recommendations.append((pattern, score))
                
        # Sort by score
        recommendations.sort(key=lambda x: x[1], reverse=True)
        return recommendations
        
    def _analyze_code_structure(self, java_code: str) -> Dict[str, Any]:
        """Analyze code structure for pattern recommendation."""
        analysis = {
            'has_blocks': bool(re.search(r'extends\s+(?:Block|TileEntity)', java_code)),
            'has_items': bool(re.search(r'extends\s+Item', java_code)),
            'has_entities': bool(re.search(r'extends\s+(?:Entity|Mob|Creature)', java_code)),
            'has_recipes': bool(re.search(r'(?:ShapedRecipe|ShapelessRecipe|CookingRecipe)', java_code)),
            'has_events': bool(re.search(r'@(?:SubscribeEvent|ModEventHandler)', java_code)),
            'class_count': len(re.findall(r'class\s+\w+', java_code)),
            'method_count': len(re.findall(r'(?:public|private|protected)\s+(?:static\s+)?(?:\w+)\s+\w+\s*\(', java_code)),
        }
        
        return analysis
        
    def _calculate_recommendation_score(self, pattern: MinecraftPattern, 
                                        code_analysis: Dict[str, Any],
                                        context: Dict[str, Any]) -> float:
        """Calculate recommendation score for a pattern."""
        score = 0.3  # Base score
        
        # Match pattern type to code analysis
        if pattern.pattern_type == PatternType.BLOCK and code_analysis.get('has_blocks'):
            score += 0.4
        elif pattern.pattern_type == PatternType.ITEM and code_analysis.get('has_items'):
            score += 0.4
        elif pattern.pattern_type == PatternType.ENTITY and code_analysis.get('has_entities'):
            score += 0.4
        elif pattern.pattern_type == PatternType.RECIPE and code_analysis.get('has_recipes'):
            score += 0.4
        elif pattern.pattern_type == PatternType.EVENT and code_analysis.get('has_events'):
            score += 0.4
            
        # Boost by priority
        score += pattern.priority * 0.05
        
        return min(1.0, score)
        
    def recognize_inheritance(self, java_code: str) -> Dict[str, List[str]]:
        """
        Recognize inheritance hierarchies in code.
        
        Returns:
            Dictionary mapping class names to their parent classes
        """
        hierarchy = {}
        
        # Find class declarations with extends
        extends_pattern = re.compile(r'class\s+(\w+)\s+extends\s+(\w+)')
        for match in extends_pattern.finditer(java_code):
            child_class = match.group(1)
            parent_class = match.group(2)
            hierarchy[child_class] = [parent_class]
            
        # Find class declarations with implements
        implements_pattern = re.compile(r'class\s+(\w+)\s+implements\s+([\w,\s]+)')
        for match in implements_pattern.finditer(java_code):
            child_class = match.group(1)
            interfaces = [i.strip() for i in match.group(2).split(',')]
            if child_class in hierarchy:
                hierarchy[child_class].extend(interfaces)
            else:
                hierarchy[child_class] = interfaces
                
        return hierarchy


def create_pattern_matcher() -> PatternMatcher:
    """Factory function to create a pattern matcher."""
    return PatternMatcher()
