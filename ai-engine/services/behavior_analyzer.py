"""
Behavior Analyzer Service
Analyzes behavioral differences between Java mods and Bedrock addons
"""

import ast
import json
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BehaviorGapSeverity(Enum):
    """Severity levels for behavioral gaps."""
    CRITICAL = "critical"  # Feature completely missing or broken
    MAJOR = "major"        # Significant behavior difference
    MINOR = "minor"        # Cosmetic difference


class BehaviorGapCategory(Enum):
    """Categories of behavioral gaps."""
    EVENT_HANDLER = "event_handler"
    STATE_MANAGEMENT = "state_management"
    FUNCTION_LOGIC = "function_logic"
    API_MISSING = "api_missing"
    API_DIFFERENT = "api_different"


@dataclass
class BehaviorGap:
    """Represents a behavioral difference between Java and Bedrock."""
    category: BehaviorGapCategory
    severity: BehaviorGapSeverity
    title: str
    description: str
    java_element: str
    bedrock_element: Optional[str]
    fix_suggestion: str
    affected_files: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "java_element": self.java_element,
            "bedrock_element": self.bedrock_element,
            "fix_suggestion": self.fix_suggestion,
            "affected_files": self.affected_files,
        }


@dataclass
class BehaviorAnalysisResult:
    """Results of behavior analysis."""
    java_source_path: str
    bedrock_output_path: str
    analyzed_functions: int
    analyzed_events: int
    analyzed_state_vars: int
    gaps: List[BehaviorGap]
    function_mappings: Dict[str, str] = field(default_factory=dict)
    event_mappings: Dict[str, str] = field(default_factory=dict)
    
    @property
    def critical_gaps(self) -> List[BehaviorGap]:
        return [g for g in self.gaps if g.severity == BehaviorGapSeverity.CRITICAL]
    
    @property
    def major_gaps(self) -> List[BehaviorGap]:
        return [g for g in self.gaps if g.severity == BehaviorGapSeverity.MAJOR]
    
    @property
    def minor_gaps(self) -> List[BehaviorGap]:
        return [g for g in self.gaps if g.severity == BehaviorGapSeverity.MINOR]
    
    @property
    def total_gaps(self) -> int:
        return len(self.gaps)
    
    @property
    def preservation_score(self) -> float:
        """Calculate behavior preservation score (0-100)."""
        # If nothing was analyzed, assume full preservation (empty conversion)
        if self.analyzed_functions + self.analyzed_events + self.analyzed_state_vars == 0:
            # If no elements were analyzed but there are gaps, score is 0
            # If no elements were analyzed and no gaps, score is 100 (perfect empty conversion)
            if self.total_gaps > 0:
                return 0.0
            return 100.0
        
        # Deduct points for gaps
        deduction = 0
        for gap in self.gaps:
            if gap.severity == BehaviorGapSeverity.CRITICAL:
                deduction += 15
            elif gap.severity == BehaviorGapSeverity.MAJOR:
                deduction += 8
            else:  # MINOR
                deduction += 2
        
        return max(0.0, 100.0 - deduction)


class BehaviorAnalyzer:
    """
    Main behavior analyzer for comparing Java mods with Bedrock addons.
    """
    
    def __init__(self):
        self.java_analyzer = None
        self._event_mapper = None
        self._state_analyzer = None
        
    def _get_event_mapper(self):
        """Lazy load event mapper."""
        if self._event_mapper is None:
            from services.event_mapper import EventMapper
            self._event_mapper = EventMapper()
        return self._event_mapper
    
    def _get_state_analyzer(self):
        """Lazy load state analyzer."""
        if self._state_analyzer is None:
            from services.state_analyzer import StateAnalyzer
            self._state_analyzer = StateAnalyzer()
        return self._state_analyzer
    
    def analyze(
        self,
        java_source_path: str | Path,
        bedrock_output_path: str | Path,
    ) -> BehaviorAnalysisResult:
        """
        Analyze behavioral differences between Java source and Bedrock output.
        
        Args:
            java_source_path: Path to Java source files
            bedrock_output_path: Path to Bedrock behavior pack
            
        Returns:
            BehaviorAnalysisResult with gaps and mappings
        """
        java_path = Path(java_source_path)
        bedrock_path = Path(bedrock_output_path)
        
        logger.info(f"Analyzing behavior for {java_path} -> {bedrock_path}")
        
        # Collect analysis results
        gaps: List[BehaviorGap] = []
        function_mappings: Dict[str, str] = {}
        event_mappings: Dict[str, str] = {}
        
        # 1. Analyze Java source
        java_analysis = self._analyze_java_source(java_path)
        
        # 2. Analyze Bedrock output
        bedrock_analysis = self._analyze_bedrock_output(bedrock_path)
        
        # 3. Map and compare events
        event_gaps, event_map = self._compare_events(
            java_analysis.get("events", []),
            bedrock_analysis.get("events", [])
        )
        gaps.extend(event_gaps)
        event_mappings.update(event_map)
        
        # 4. Analyze function logic
        func_gaps, func_map = self._compare_functions(
            java_analysis.get("functions", []),
            bedrock_analysis.get("functions", [])
        )
        gaps.extend(func_gaps)
        function_mappings.update(func_map)
        
        # 5. Analyze state management
        state_gaps = self._compare_state(
            java_analysis.get("state_vars", []),
            bedrock_analysis.get("state_vars", [])
        )
        gaps.extend(state_gaps)
        
        # Sort gaps by severity
        gaps.sort(key=lambda g: (
            [BehaviorGapSeverity.CRITICAL, BehaviorGapSeverity.MAJOR, BehaviorGapSeverity.MINOR].index(g.severity),
            g.category.value
        ))
        
        return BehaviorAnalysisResult(
            java_source_path=str(java_path),
            bedrock_output_path=str(bedrock_path),
            analyzed_functions=len(java_analysis.get("functions", [])),
            analyzed_events=len(java_analysis.get("events", [])),
            analyzed_state_vars=len(java_analysis.get("state_vars", [])),
            gaps=gaps,
            function_mappings=function_mappings,
            event_mappings=event_mappings,
        )
    
    def _analyze_java_source(self, path: Path) -> Dict[str, Any]:
        """Analyze Java source files for events, functions, and state using pattern matching."""
        import re
        
        analysis = {
            "events": [],
            "functions": [],
            "state_vars": [],
        }
        
        # Find all Java files
        java_files = list(path.rglob("*.java"))
        
        for java_file in java_files:
            try:
                content = java_file.read_text(encoding="utf-8")
                
                # Extract function/method definitions using regex
                # Match: accessModifier returnType methodName(params) { ...
                method_pattern = r'(?:public|private|protected)?\s*(?:static)?\s*(\w+)\s+(\w+)\s*\([^)]*\)\s*\{'
                for match in re.finditer(method_pattern, content):
                    return_type = match.group(1)
                    method_name = match.group(2)
                    
                    # Skip constructors (same as class name)
                    class_match = re.search(r'class\s+(\w+)', content)
                    if class_match and method_name == class_match.group(1):
                        continue
                    
                    func_info = {
                        "name": method_name,
                        "file": str(java_file.relative_to(path)),
                        "return_type": return_type,
                    }
                    analysis["functions"].append(func_info)
                    
                    # Check for event handlers via method names
                    if self._is_event_handler_by_name(method_name):
                        analysis["events"].append({
                            **func_info,
                            "event_type": self._detect_event_type(method_name),
                        })
                
                # Extract field declarations (state variables)
                # Match: accessModifier type fieldName = value;
                field_pattern = r'(?:private|public|protected)?\s+(?:static|final)?\s*(\w+)\s+(\w+)\s*=?([^;]+)?;'
                for match in re.finditer(field_pattern, content):
                    field_type = match.group(1)
                    field_name = match.group(2)
                    
                    # Skip common non-state names
                    if field_name.startswith('_') or field_name in ['LOGGER', 'logger', 'instance', 'INSTANCE']:
                        continue
                    # Skip methods
                    if field_name in [f['name'] for f in analysis['functions']]:
                        continue
                    
                    analysis["state_vars"].append({
                        "name": field_name,
                        "type": field_type,
                        "file": str(java_file.relative_to(path)),
                    })
                                
            except Exception as e:
                logger.warning(f"Failed to parse {java_file}: {e}")
        
        logger.info(f"Java analysis: {len(analysis['functions'])} functions, "
                   f"{len(analysis['events'])} events, "
                   f"{len(analysis['state_vars'])} state vars")
        
        return analysis
    
    def _is_event_handler_by_name(self, method_name: str) -> bool:
        """Check if a method name suggests it's an event handler."""
        name = method_name.lower()
        
        # Check naming patterns - handle both lowercase and camelCase
        event_patterns = [
            "oninit", "onload", "onconstruct", "onplace", "onuse", 
            "onbreak", "oninteract", "onattack", "ondeath", "ontick",
            "onblock", "onitem", "onplayer", "onentity",
            "handler", "listener", "callback", "event", "subscribe"
        ]
        return any(p in name for p in event_patterns)
    
    def _analyze_bedrock_output(self, path: Path) -> Dict[str, Any]:
        """Analyze Bedrock behavior pack for events, functions, and state."""
        analysis = {
            "events": [],
            "functions": [],
            "state_vars": [],
        }
        
        # Find all JSON and JS files
        json_files = list(path.rglob("*.json"))
        js_files = list(path.rglob("*.js"))
        
        # Analyze JSON files (definitions, components, triggers)
        for json_file in json_files:
            try:
                content = json_file.read_text(encoding="utf-8")
                data = json.loads(content)
                
                # Extract events from triggers, event responses
                if "events" in data:
                    for event_name, event_data in data["events"].items():
                        analysis["events"].append({
                            "name": event_name,
                            "file": str(json_file.relative_to(path)),
                            "bedrock_type": "event_response",
                            "data": event_data,
                        })
                
                # Extract from entity/item/block definitions
                if "minecraft:entity" in data:
                    entity_data = data["minecraft:entity"]
                    components = entity_data.get("components", {})
                    
                    # Events can be at the components level or inside specific components
                    # Check components level first (e.g., "events": {...})
                    if "events" in components:
                        for event_name, event_data in components["events"].items():
                            analysis["events"].append({
                                "name": event_name,
                                "file": str(json_file.relative_to(path)),
                                "bedrock_type": "component_event",
                                "component": "components",
                            })
                    
                    # Then check inside individual components
                    for comp_name, comp_data in components.items():
                        if isinstance(comp_data, dict) and "events" in comp_data:
                            for event_name in comp_data["events"].keys():
                                analysis["events"].append({
                                    "name": event_name,
                                    "file": str(json_file.relative_to(path)),
                                    "bedrock_type": "component_event",
                                    "component": comp_name,
                                })
                                
                # Extract custom functions from scripts
                if "scripts" in data:
                    scripts = data["scripts"]
                    for script_type in ["on_tick", "on_player_join", "on_player_leave", 
                                       "on_item_use", "on_block_placed"]:
                        if script_type in scripts:
                            script_content = scripts[script_type]
                            if isinstance(script_content, str):
                                analysis["functions"].append({
                                    "name": script_content.split('(')[0].strip() if '(' in script_content else script_content,
                                    "file": str(json_file.relative_to(path)),
                                    "bedrock_type": "script",
                                    "script_type": script_type,
                                })
                                
            except Exception as e:
                logger.warning(f"Failed to parse {json_file}: {e}")
        
        # Analyze JavaScript files
        for js_file in js_files:
            try:
                content = js_file.read_text(encoding="utf-8")
                
                # Simple function detection
                import re
                functions = re.findall(r'function\s+(\w+)\s*\(', content)
                for func_name in functions:
                    analysis["functions"].append({
                        "name": func_name,
                        "file": str(js_file.relative_to(path)),
                        "bedrock_type": "js_function",
                    })
                    
                # Detect event handlers
                event_patterns = [
                    (r'\.on\(["\'](\w+)["\']', 'listener'),
                    (r'register\(["\'](\w+)["\']', 'register'),
                    (r'minecraft:(\w+)', 'minecraft_event'),
                ]
                for pattern, event_type in event_patterns:
                    matches = re.findall(pattern, content)
                    for match in matches:
                        analysis["events"].append({
                            "name": match,
                            "file": str(js_file.relative_to(path)),
                            "bedrock_type": f"js_{event_type}",
                        })
                        
            except Exception as e:
                logger.warning(f"Failed to parse {js_file}: {e}")
        
        # Analyze state from loot tables and storage
        loot_tables = list(path.rglob("loot_tables/**/*.json"))
        for lt in loot_tables:
            try:
                data = json.loads(lt.read_text())
                if "pools" in data:
                    analysis["state_vars"].append({
                        "name": str(lt.relative_to(path)),
                        "type": "loot_table",
                        "file": str(lt.relative_to(path)),
                    })
            except:
                pass
        
        logger.info(f"Bedrock analysis: {len(analysis['functions'])} functions, "
                   f"{len(analysis['events'])} events, "
                   f"{len(analysis['state_vars'])} state vars")
        
        return analysis
    
    def _is_event_handler(self, func_info: Dict) -> bool:
        """Check if a function is likely an event handler."""
        # Handle both dict and string input
        if isinstance(func_info, str):
            name = func_info.lower()
            decorators = []
        else:
            name = func_info.get("name", "").lower()
            decorators = func_info.get("decorators", [])
        
        # Check decorators
        event_decorators = ["subscribe", "receiver", "eventlistener", "mod.event"]
        if any(d.lower() in event_decorators for d in decorators):
            return True
        
        # Check naming patterns
        event_patterns = [
            "oninit", "onload", "onconstruct", "onplace", "onuse", 
            "onbreak", "oninteract", "onattack", "ondeath", "on tick",
            "handler", "listener", "callback", "event"
        ]
        return any(p in name for p in event_patterns)
    
    def _detect_event_type(self, method_name: str) -> str:
        """Detect event type from method name."""
        name = method_name.lower()
        
        if "place" in name:
            return "block_placed"
        elif "break" in name:
            return "block_broken"
        elif "use" in name or "interact" in name:
            return "item_used"
        elif "tick" in name:
            return "tick"
        elif "init" in name or "construct" in name:
            return "init"
        elif "death" in name:
            return "entity_death"
        elif "attack" in name:
            return "entity_attacked"
        elif "join" in name:
            return "player_joined"
        elif "leave" in name:
            return "player_left"
        else:
            return "custom"
    
    def _get_decorator_name(self, decorator) -> str:
        """Get decorator name from AST node."""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
            elif isinstance(decorator.func, ast.Attribute):
                return decorator.func.attr
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr
        return "unknown"
    
    def _compare_events(
        self, 
        java_events: List[Dict], 
        bedrock_events: List[Dict]
    ) -> Tuple[List[BehaviorGap], Dict[str, str]]:
        """Compare events between Java and Bedrock."""
        gaps = []
        mappings = {}
        
        event_mapper = self._get_event_mapper()
        
        # Map Java events to Bedrock
        for java_event in java_events:
            java_event_name = java_event.get("name", "")
            java_event_type = java_event.get("event_type", "custom")
            
            # Try to find matching Bedrock event
            mapped_event = event_mapper.map_java_event(java_event_type, java_event_name)
            
            if mapped_event:
                # Check if mapped event exists in Bedrock
                bedrock_event_names = {e.get("name", "") for e in bedrock_events}
                if mapped_event in bedrock_event_names:
                    mappings[java_event_name] = mapped_event
                else:
                    # Event mapped but not found - potential gap
                    gaps.append(BehaviorGap(
                        category=BehaviorGapCategory.EVENT_HANDLER,
                        severity=BehaviorGapSeverity.MAJOR,
                        title=f"Event handler not found in Bedrock: {mapped_event}",
                        description=f"Java event '{java_event_name}' mapped to Bedrock '{mapped_event}', "
                                   f"but the event handler was not found in the output.",
                        java_element=java_event_name,
                        bedrock_element=mapped_event,
                        fix_suggestion=f"Implement event handler for '{mapped_event}' in the Bedrock behavior pack.",
                        affected_files=[java_event.get("file", "")],
                    ))
            else:
                # No mapping found - unknown if supported
                gaps.append(BehaviorGap(
                    category=BehaviorGapCategory.EVENT_HANDLER,
                    severity=BehaviorGapSeverity.MINOR,
                    title=f"Unknown event mapping: {java_event_name}",
                    description=f"Java event '{java_event_name}' could not be mapped to a Bedrock event.",
                    java_element=java_event_name,
                    bedrock_element=None,
                    fix_suggestion="Review manually to determine if equivalent Bedrock event exists.",
                    affected_files=[java_event.get("file", "")],
                ))
        
        # Check for Bedrock events with no Java source (may be extra functionality)
        java_event_names = {e.get("name", "") for e in java_events}
        for bedrock_event in bedrock_events:
            if bedrock_event.get("name") not in java_event_names:
                # Extra Bedrock event - not necessarily a gap
                pass
        
        return gaps, mappings
    
    def _compare_functions(
        self,
        java_functions: List[Dict],
        bedrock_functions: List[Dict]
    ) -> Tuple[List[BehaviorGap], Dict[str, str]]:
        """Compare functions between Java and Bedrock."""
        gaps = []
        mappings = {}
        
        # Simple name-based matching with similarity
        bedrock_names = {f.get("name", ""): f for f in bedrock_functions}
        
        for java_func in java_functions:
            java_name = java_func.get("name", "")
            
            # Try exact match first
            if java_name in bedrock_names:
                mappings[java_name] = java_name
                continue
            
            # Try case-insensitive match
            java_lower = java_name.lower()
            for bp_name, bp_func in bedrock_names.items():
                if java_lower == bp_name.lower():
                    mappings[java_name] = bp_name
                    break
            else:
                # No match found - could be API difference
                # Check if it's a Minecraft API function
                if java_name.startswith("Minecraft") or java_name.startswith("net.minecraft"):
                    gaps.append(BehaviorGap(
                        category=BehaviorGapCategory.API_MISSING,
                        severity=BehaviorGapSeverity.CRITICAL,
                        title=f"Missing Minecraft API: {java_name}",
                        description=f"Java function '{java_name}' uses Minecraft API that may not be available in Bedrock.",
                        java_element=java_name,
                        bedrock_element=None,
                        fix_suggestion="Research Bedrock equivalent API or implement custom behavior.",
                        affected_files=[java_func.get("file", "")],
                    ))
                elif not self._is_event_handler(java_func):
                    # Non-event function not found
                    gaps.append(BehaviorGap(
                        category=BehaviorGapCategory.FUNCTION_LOGIC,
                        severity=BehaviorGapSeverity.MAJOR,
                        title=f"Function not implemented: {java_name}",
                        description=f"Java method '{java_name}' was not found in Bedrock output.",
                        java_element=java_name,
                        bedrock_element=None,
                        fix_suggestion=f"Implement equivalent logic for '{java_name}' in Bedrock.",
                        affected_files=[java_func.get("file", "")],
                    ))
        
        return gaps, mappings
    
    def _compare_state(
        self,
        java_state_vars: List[Dict],
        bedrock_state_vars: List[Dict]
    ) -> List[BehaviorGap]:
        """Compare state management between Java and Bedrock."""
        gaps = []
        
        state_analyzer = self._get_state_analyzer()
        
        # Check each Java state variable
        for java_var in java_state_vars:
            var_name = java_var.get("name", "")
            var_type = java_var.get("type", "unknown")
            
            # Look for equivalent in Bedrock
            found = False
            for bp_var in bedrock_state_vars:
                if var_name.lower() in bp_var.get("name", "").lower():
                    found = True
                    break
            
            if not found:
                # Check if it's stored in a different way
                storage_type = state_analyzer.detect_storage_type(var_type, var_name)
                
                if storage_type == "unsupported":
                    gaps.append(BehaviorGap(
                        category=BehaviorGapCategory.STATE_MANAGEMENT,
                        severity=BehaviorGapSeverity.MAJOR,
                        title=f"State variable not preserved: {var_name}",
                        description=f"Java state variable '{var_name}' ({var_type}) was not found in Bedrock output.",
                        java_element=f"{var_type} {var_name}",
                        bedrock_element=None,
                        fix_suggestion=f"Implement state storage using Bedrock's storage system or entity components.",
                        affected_files=[java_var.get("file", "")],
                    ))
                # If stored differently (like loot table), it's fine
        
        return gaps


def analyze_behavior(
    java_source_path: str | Path,
    bedrock_output_path: str | Path,
) -> BehaviorAnalysisResult:
    """
    Convenience function for behavior analysis.
    
    Args:
        java_source_path: Path to Java source files
        bedrock_output_path: Path to Bedrock behavior pack
        
    Returns:
        BehaviorAnalysisResult with gaps and mappings
    """
    analyzer = BehaviorAnalyzer()
    return analyzer.analyze(java_source_path, bedrock_output_path)
