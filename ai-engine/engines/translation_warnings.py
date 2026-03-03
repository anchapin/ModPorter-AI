"""
Translation Warning and Functionality Loss Detector

This module detects and reports potential functionality loss when translating
Java code to Bedrock JavaScript, providing user-facing warnings
and explanations for smart assumptions applied.

Issue #570: AI Engine Logic Translation - Java OOP to Bedrock Event-Driven JavaScript
"""

from __future__ import annotations

import re
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
from enum import Enum


class ImpactLevel(Enum):
    """Impact level of functionality loss"""
    CRITICAL = "critical"  # Feature completely unavailable
    HIGH = "high"         # Significant functionality loss
    MEDIUM = "medium"     # Partial functionality with workarounds
    LOW = "low"           # Minor changes, mostly equivalent
    NONE = "none"         # Direct equivalent available


@dataclass
class TranslationWarning:
    """
    Represents a translation warning for functionality loss.

    Attributes:
        category: Category of functionality affected
        java_feature: The Java feature being translated
        bedrock_status: Status in Bedrock (supported/partial/unsupported)
        impact: Level of impact on functionality
        user_explanation: User-friendly explanation
        technical_notes: Technical details for developers
        workarounds: Potential workarounds or alternatives
        code_reference: Reference to code location (if available)
    """
    category: str
    java_feature: str
    bedrock_status: str
    impact: ImpactLevel
    user_explanation: str
    technical_notes: str
    workarounds: List[str]
    code_reference: Optional[str] = None


@dataclass
class WarningReport:
    """Complete warning report for a translation"""
    warnings: List[TranslationWarning]
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    overall_assessment: str
    recommendations: List[str]


class TranslationWarningDetector:
    """
    Detects and reports translation warnings based on code analysis.

    Analyzes:
    - Java constructs with no Bedrock equivalent
    - API calls that cannot be translated
    - Paradigm shifts that impact functionality
    - Performance implications of translation
    - Security considerations
    """

    def __init__(self):
        """Initialize detector with warning patterns"""
        self.patterns = self._load_warning_patterns()
        self.api_limitations = self._load_api_limitations()
        self.paradigm_issues = self._load_paradigm_issues()

    def analyze_java_code(
        self,
        java_code: str,
        feature_type: Optional[str] = None
    ) -> WarningReport:
        """
        Analyze Java code for potential translation issues.

        Args:
            java_code: The Java source code to analyze
            feature_type: Optional type of feature (block, item, entity, etc.)

        Returns:
            WarningReport with all detected warnings
        """
        warnings = []

        # 1. Check for unsupported Java constructs
        construct_warnings = self._check_java_constructs(java_code)
        warnings.extend(construct_warnings)

        # 2. Check for API limitations
        api_warnings = self._check_api_usage(java_code)
        warnings.extend(api_warnings)

        # 3. Check for paradigm shift issues
        paradigm_warnings = self._check_paradigm_issues(java_code)
        warnings.extend(paradigm_warnings)

        # 4. Check feature-specific issues
        if feature_type:
            feature_warnings = self._check_feature_specific(java_code, feature_type)
            warnings.extend(feature_warnings)

        # 5. Check for state management issues
        state_warnings = self._check_state_management(java_code)
        warnings.extend(state_warnings)

        # 6. Check for inheritance and polymorphism issues
        oop_warnings = self._check_oop_patterns(java_code)
        warnings.extend(oop_warnings)

        # Deduplicate warnings
        warnings = self._deduplicate_warnings(warnings)

        # Generate report
        return self._generate_report(warnings)

    def analyze_translated_javascript(
        self,
        javascript_code: str,
        original_java_code: Optional[str] = None
    ) -> WarningReport:
        """
        Analyze translated JavaScript for potential issues.

        Args:
            javascript_code: The translated JavaScript code
            original_java_code: Original Java code for comparison

        Returns:
            WarningReport with detected issues
        """
        warnings = []

        # Check for common Bedrock limitations
        bedrock_warnings = self._check_bedrock_limitations(javascript_code)
        warnings.extend(bedrock_warnings)

        # Compare with original if available
        if original_java_code:
            comparison_warnings = self._compare_translations(
                javascript_code,
                original_java_code
            )
            warnings.extend(comparison_warnings)

        # Check for workarounds used
        workaround_warnings = self._detect_workarounds(javascript_code)
        warnings.extend(workaround_warnings)

        return self._generate_report(warnings)

    def _check_java_constructs(self, java_code: str) -> List[TranslationWarning]:
        """Check for Java constructs with no Bedrock equivalent"""
        warnings = []

        lines = java_code.split('\n')

        # Check for custom dimensions
        if re.search(r'\b(Dimension|WorldProvider|DimensionType)\b', java_code):
            warnings.append(TranslationWarning(
                category="Architecture",
                java_feature="Custom Dimensions",
                bedrock_status="unsupported",
                impact=ImpactLevel.CRITICAL,
                user_explanation="Custom dimensions cannot be created in Bedrock. The dimension will be converted to a large structure in the Overworld or existing dimension.",
                technical_notes="Bedrock has no API for dimension creation. Smart assumption: create as large structure.",
                workarounds=[
                    "Use large pre-built structures",
                    "Create structure blocks for placement",
                    "Use different biomes for variety"
                ]
            ))

        # Check for custom GUI/screens
        if re.search(r'\b(Screen|ContainerScreen|GuiContainer|AbstractGui)\b', java_code):
            warnings.append(TranslationWarning(
                category="UI",
                java_feature="Custom GUI Screens",
                bedrock_status="unsupported",
                impact=ImpactLevel.HIGH,
                user_explanation="Custom GUI screens cannot be created in Bedrock. Interface elements will be converted to book/sign-based displays.",
                technical_notes="Bedrock has no custom UI API. Smart assumption: use books, signs, or text displays.",
                workarounds=[
                    "Use writable books for information display",
                    "Use signs for simple labels",
                    "Use text displays for server-side text",
                    "Reorganize UI for book presentation"
                ]
            ))

        # Check for complex machinery
        if re.search(r'\b(BlockEntity|TileEntity)\b', java_code):
            warnings.append(TranslationWarning(
                category="Gameplay",
                java_feature="Block Entities / Complex Machinery",
                bedrock_status="partial",
                impact=ImpactLevel.HIGH,
                user_explanation="Complex block entity logic cannot be fully replicated in Bedrock. Machinery will be simplified to decorative blocks.",
                technical_notes="Bedrock has limited block entity capabilities. Smart assumption: decorative conversion.",
                workarounds=[
                    "Preserve visual aesthetics",
                    "Consider alternative interaction methods",
                    "Use command blocks for complex logic (if enabled)"
                ]
            ))

        # Check for client-side rendering
        if re.search(r'\b(Shader|RenderGameOverlayEvent|RenderPlayerEvent|RenderBlock)\b', java_code):
            warnings.append(TranslationWarning(
                category="Graphics",
                java_feature="Client-Side Rendering / Shaders",
                bedrock_status="unsupported",
                impact=ImpactLevel.CRITICAL,
                user_explanation="Client-side rendering and custom shaders cannot be implemented in Bedrock.",
                technical_notes="Bedrock uses Render Dragon with no public API. Smart assumption: exclude feature.",
                workarounds=[
                    "Use built-in particles and effects",
                    "Use resource packs for visual changes",
                    "Feature is excluded from conversion"
                ]
            ))

        # Check for packet handling
        if re.search(r'\b(Packet|NetworkManager|SimpleChannel)\b', java_code):
            warnings.append(TranslationWarning(
                category="Networking",
                java_feature="Custom Network Packets",
                bedrock_status="unsupported",
                impact=ImpactLevel.HIGH,
                user_explanation="Custom network packets cannot be sent/processed in Bedrock. Communication between players/server is limited.",
                technical_notes="Bedrock has no packet API. Smart assumption: use event-driven communication.",
                workarounds=[
                    "Use shared dynamic properties",
                    "Use commands for communication",
                    "Use scoreboards for state sharing"
                ]
            ))

        # Check for NBT manipulation
        if re.search(r'\b(NBTTagCompound|NBTTag|getNBT)\b', java_code):
            warnings.append(TranslationWarning(
                category="Data",
                java_feature="NBT Data Manipulation",
                bedrock_status="unsupported",
                impact=ImpactLevel.MEDIUM,
                user_explanation="NBT data cannot be directly manipulated in Bedrock. Use component properties instead.",
                technical_notes="Bedrock uses component system, not NBT. Smart assumption: map to components.",
                workarounds=[
                    "Use Bedrock component system",
                    "Use dynamic properties for custom data",
                    "Use item tags instead of NBT tags"
                ]
            ))

        # Check for reflection
        if re.search(r'\b(Method|Field)\.setAccessible\(|getDeclaredFields\(|getDeclaredMethods\(', java_code):
            warnings.append(TranslationWarning(
                category="Security",
                java_feature="Java Reflection",
                bedrock_status="unsupported",
                impact=ImpactLevel.CRITICAL,
                user_explanation="Java reflection cannot be used in Bedrock JavaScript. Private members cannot be accessed.",
                technical_notes="JavaScript in Bedrock has no reflection API. Smart assumption: use public APIs only.",
                workarounds=[
                    "Restrict to public APIs only",
                    "Document API requirements",
                    "Use alternative approaches for needed functionality"
                ]
            ))

        # Check for threading
        if re.search(r'\b(Thread|Runnable|ExecutorService|CompletableFuture)\b', java_code):
            warnings.append(TranslationWarning(
                category="Architecture",
                java_feature="Threading / Async Operations",
                bedrock_status="unsupported",
                impact=ImpactLevel.HIGH,
                user_explanation="Threading and async operations cannot be directly translated. Code will run synchronously on main thread.",
                technical_notes="Bedrock scripts run synchronously. Smart assumption: use event-driven async.",
                workarounds=[
                    "Use event handlers for async behavior",
                    "Use tick events with delays",
                    "Avoid blocking operations in event handlers"
                ]
            ))

        return warnings

    def _check_api_usage(self, java_code: str) -> List[TranslationWarning]:
        """Check for Java API usage with Bedrock limitations"""
        warnings = []

        # Check for common problematic APIs
        api_issues = {
            'world.getBiome(': TranslationWarning(
                category="World",
                java_feature="Biome Setting",
                bedrock_status="partial",
                impact=ImpactLevel.MEDIUM,
                user_explanation="Biomes can be read but not dynamically changed in Bedrock.",
                technical_notes="Bedrock has limited biome manipulation API.",
                workarounds=["Use static structure placement", "Use existing biomes"]
            ),
            'player.getFoodLevel(': TranslationWarning(
                category="Player",
                java_feature="Hunger System",
                bedrock_status="supported",
                impact=ImpactLevel.LOW,
                user_explanation="Hunger is supported through food component.",
                technical_notes="Accessible via player.getComponent('minecraft:food').",
                workarounds=["Standard Bedrock API usage"]
            ),
        }

        for api_pattern, warning in api_issues.items():
            if api_pattern in java_code:
                warnings.append(warning)

        return warnings

    def _check_paradigm_issues(self, java_code: str) -> List[TranslationWarning]:
        """Check for paradigm shift issues"""
        warnings = []

        # Check for class inheritance
        if re.search(r'\bclass\s+\w+\s+extends\s+\w+', java_code):
            warnings.append(TranslationWarning(
                category="OOP",
                java_feature="Class Inheritance",
                bedrock_status="unsupported",
                impact=ImpactLevel.HIGH,
                user_explanation="Bedrock JavaScript does not support class inheritance. Classes will be flattened.",
                technical_notes="JavaScript has no class inheritance in Bedrock context. Smart assumption: use composition.",
                workarounds=[
                    "Flatten inheritance hierarchy",
                    "Use component composition",
                    "Create helper functions for shared logic"
                ]
            ))

        # Check for interface implementation
        if re.search(r'\bimplements\s+\w+', java_code):
            warnings.append(TranslationWarning(
                category="OOP",
                java_feature="Interface Implementation",
                bedrock_status="unsupported",
                impact=ImpactLevel.MEDIUM,
                user_explanation="Bedrock JavaScript does not support interfaces. Duck typing will be used instead.",
                technical_notes="JavaScript uses duck typing (structure over interface).",
                workarounds=["Use duck typing patterns", "Document expected structure"]
            ))

        # Check for polymorphism
        if re.search(r'@\s*Override\b', java_code):
            warnings.append(TranslationWarning(
                category="OOP",
                java_feature="Method Overriding / Polymorphism",
                bedrock_status="partial",
                impact=ImpactLevel.MEDIUM,
                user_explanation="Method overriding is not directly supported. Behavior must be implemented explicitly.",
                technical_notes="JavaScript supports function properties but not polymorphism.",
                workarounds=["Use explicit function assignment", "Use event handlers"]
            ))

        return warnings

    def _check_state_management(self, java_code: str) -> List[TranslationWarning]:
        """Check for state management issues"""
        warnings = []

        # Check for instance variables (fields)
        if re.search(r'\b(private|protected|public)\s+\w+\s+\w+\s*;', java_code):
            warnings.append(TranslationWarning(
                category="State",
                java_feature="Instance Variables / Object State",
                bedrock_status="partial",
                impact=ImpactLevel.MEDIUM,
                user_explanation="Object state management requires different approach in event-driven JavaScript.",
                technical_notes="Bedrock scripts are more stateless. Use dynamic properties or global state.",
                workarounds=[
                    "Use world.setDynamicProperty() for persistent state",
                    "Use module-level variables for shared state",
                    "Consider stateless design patterns"
                ]
            ))

        return warnings

    def _check_oop_patterns(self, java_code: str) -> List[TranslationWarning]:
        """Check for OOP patterns that don't translate well"""
        warnings = []

        # Check for abstract classes
        if re.search(r'\babstract\s+class\b', java_code):
            warnings.append(TranslationWarning(
                category="OOP",
                java_feature="Abstract Classes",
                bedrock_status="unsupported",
                impact=ImpactLevel.MEDIUM,
                user_explanation="Abstract classes are not supported. Concrete implementations will be generated.",
                technical_notes="JavaScript doesn't have abstract classes. Use factory patterns or concrete classes.",
                workarounds=["Create concrete implementations", "Use factory functions"]
            ))

        # Check for generic types
        if re.search(r'<\w+>', java_code):
            warnings.append(TranslationWarning(
                category="OOP",
                java_feature="Generic Types",
                bedrock_status="partial",
                impact=ImpactLevel.LOW,
                user_explanation="Generic types are not explicitly supported. Specific types will be used.",
                technical_notes="JavaScript is dynamically typed. Generics are ignored at runtime.",
                workarounds=["Use specific types in comments", "Document expected types"]
            ))

        return warnings

    def _check_feature_specific(self, java_code: str, feature_type: str) -> List[TranslationWarning]:
        """Check for feature-specific issues"""
        warnings = []

        if feature_type == "entity":
            # Entity-specific checks
            if re.search(r'\bGoalAI\b|\bPathNavigator\b', java_code):
                warnings.append(TranslationWarning(
                    category="Entity",
                    java_feature="Custom Entity AI / Goals",
                    bedrock_status="unsupported",
                    impact=ImpactLevel.HIGH,
                    user_explanation="Custom entity AI cannot be directly implemented in Bedrock.",
                    technical_notes="Bedrock has limited AI modification capabilities.",
                    workarounds=["Use built-in AI behaviors", "Accept limitations"]
                ))

        elif feature_type == "block":
            # Block-specific checks
            if re.search(r'\bRedstoneWire\b|\bRedstoneTorch\b', java_code):
                warnings.append(TranslationWarning(
                    category="Block",
                    java_feature="Complex Redstone Logic",
                    bedrock_status="unsupported",
                    impact=ImpactLevel.MEDIUM,
                    user_explanation="Complex redstone logic in blocks cannot be replicated.",
                    technical_notes="Bedrock has no block update events for redstone.",
                    workarounds=["Use external redstone", "Use command blocks"]
                ))

        return warnings

    def _check_bedrock_limitations(self, javascript_code: str) -> List[TranslationWarning]:
        """Check for Bedrock-specific limitations in translated code"""
        warnings = []

        lines = javascript_code.split('\n')

        # Check for setTimeout/setInterval (limited availability)
        if re.search(r'\b(setTimeout|setInterval)\s*\(', javascript_code):
            warnings.append(TranslationWarning(
                category="Bedrock",
                java_feature="Timers (setTimeout/setInterval)",
                bedrock_status="limited",
                impact=ImpactLevel.MEDIUM,
                user_explanation="Timers may not work reliably in all Bedrock contexts.",
                technical_notes="Bedrock script environment has limited timer support.",
                workarounds=["Use tick events with counters", "Use built-in timing systems"]
            ))

        # Check for excessive world access in tick events
        in_tick_handler = False
        world_access_count = 0
        for line in lines:
            if 'beforeEvents.tick' in line or 'afterEvents.tick' in line:
                in_tick_handler = True
            elif line.strip() == '});':
                in_tick_handler = False

            if in_tick_handler and re.search(r'\bworld\.', line):
                world_access_count += 1

        if world_access_count > 3:
            warnings.append(TranslationWarning(
                category="Performance",
                java_feature="Excessive World Access in Tick Handler",
                bedrock_status="supported",
                impact=ImpactLevel.MEDIUM,
                user_explanation=f"World is accessed {world_access_count} times in tick handler, which may cause lag.",
                technical_notes="Tick events run 20 times per second. Frequent world access is expensive.",
                workarounds=["Cache results", "Use event-driven approach", "Reduce access frequency"]
            ))

        return warnings

    def _compare_translations(
        self,
        javascript_code: str,
        original_java_code: str
    ) -> List[TranslationWarning]:
        """Compare original Java with translated JavaScript"""
        warnings = []

        # Count key constructs
        java_methods = len(re.findall(r'\b(public|private|protected)\s+\w+\s+\w+\s*\(', original_java_code))
        js_functions = len(re.findall(r'function\s+\w+\s*\(', javascript_code))

        if java_methods > js_functions + 2:  # Allow for event handlers
            warnings.append(TranslationWarning(
                category="Translation",
                java_feature="Method Count Mismatch",
                bedrock_status="info",
                impact=ImpactLevel.LOW,
                user_explanation=f"Some Java methods may not have been translated ({java_methods} vs {js_functions}).",
                technical_notes="Some methods may have been removed during paradigm shift.",
                workarounds=["Review original code", "Add missing functionality manually"]
            ))

        return warnings

    def _detect_workarounds(self, javascript_code: str) -> List[TranslationWarning]:
        """Detect workarounds used in translated code"""
        warnings = []

        # Check for TODO comments (indicates incomplete translation)
        if 'TODO' in javascript_code or 'FIXME' in javascript_code:
            warnings.append(TranslationWarning(
                category="Translation",
                java_feature="Incomplete Translation (TODO/FIXME)",
                bedrock_status="incomplete",
                impact=ImpactLevel.MEDIUM,
                user_explanation="Code contains TODO or FIXME markers indicating incomplete translation.",
                technical_notes="Manual review required for commented sections.",
                workarounds=["Complete marked sections", "Review implementation details"]
            ))

        # Check for commented-out code
        commented_code = len([l for l in javascript_code.split('\n') if l.strip().startswith('//')])
        if commented_code > len(javascript_code.split('\n')) * 0.3:
            warnings.append(TranslationWarning(
                category="Translation",
                java_feature="Excessive Commented Code",
                bedrock_status="partial",
                impact=ImpactLevel.LOW,
                user_explanation="Large amount of commented-out code detected.",
                technical_notes="May indicate untranslatable sections.",
                workarounds=["Review comments", "Determine if functionality can be restored"]
            ))

        return warnings

    def _deduplicate_warnings(self, warnings: List[TranslationWarning]) -> List[TranslationWarning]:
        """Remove duplicate warnings"""
        seen = set()
        unique = []

        for warning in warnings:
            key = (warning.category, warning.java_feature)
            if key not in seen:
                seen.add(key)
                unique.append(warning)

        return unique

    def _generate_report(self, warnings: List[TranslationWarning]) -> WarningReport:
        """Generate complete warning report"""
        # Count by impact level
        critical = sum(1 for w in warnings if w.impact == ImpactLevel.CRITICAL)
        high = sum(1 for w in warnings if w.impact == ImpactLevel.HIGH)
        medium = sum(1 for w in warnings if w.impact == ImpactLevel.MEDIUM)
        low = sum(1 for w in warnings if w.impact == ImpactLevel.LOW)

        # Generate overall assessment
        if critical > 0:
            assessment = "Critical functionality loss detected. Major manual intervention required."
        elif high > 2:
            assessment = "Significant functionality loss. Manual review and adjustment strongly recommended."
        elif high > 0 or medium > 3:
            assessment = "Some functionality lost or degraded. Manual review recommended."
        elif medium > 0:
            assessment = "Minor functionality changes with workarounds available."
        elif low > 0:
            assessment = "Translation mostly successful with minor adjustments."
        else:
            assessment = "Translation appears complete with direct equivalents available."

        # Generate recommendations
        recommendations = []
        if critical > 0:
            recommendations.append("Review critical warnings for feature exclusions")
        if high > 0:
            recommendations.append("Test converted add-on thoroughly in Bedrock")
        if medium > 0:
            recommendations.append("Consider alternative implementations for partial support")
        if low > 0:
            recommendations.append("Verify minor functionality changes match expectations")

        return WarningReport(
            warnings=warnings,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
            overall_assessment=assessment,
            recommendations=recommendations
        )

    def _load_warning_patterns(self) -> Dict[str, Any]:
        """Load warning patterns"""
        return {}

    def _load_api_limitations(self) -> Dict[str, Any]:
        """Load API limitation patterns"""
        return {}

    def _load_paradigm_issues(self) -> Dict[str, Any]:
        """Load paradigm issue patterns"""
        return {}

    def format_warning_for_user(self, warning: TranslationWarning) -> str:
        """Format warning for user-facing display"""
        impact_icons = {
            ImpactLevel.CRITICAL: "⛔",
            ImpactLevel.HIGH: "⚠️",
            ImpactLevel.MEDIUM: "⚡",
            ImpactLevel.LOW: "ℹ️",
            ImpactLevel.NONE: "✅"
        }

        icon = impact_icons.get(warning.impact, "")
        formatted = f"""
{icon} {warning.java_feature} - {warning.bedrock_status.upper()}

Impact: {warning.impact.value.upper()}

What this means:
{warning.user_explanation}

Technical Details:
{warning.technical_notes}

Possible Workarounds:
"""
        for i, workaround in enumerate(warning.workarounds, 1):
            formatted += f"  {i}. {workaround}\n"

        return formatted

    def format_report_for_user(self, report: WarningReport) -> str:
        """Format complete report for user-facing display"""
        formatted = f"""
=== Translation Analysis Report ====

Overall Assessment:
{report.overall_assessment}

Warning Summary:
  ⛔ Critical: {report.critical_count}
  ⚠️ High:     {report.high_count}
  ⚡ Medium:   {report.medium_count}
  ℹ️ Low:      {report.low_count}

Recommendations:
"""
        for i, rec in enumerate(report.recommendations, 1):
            formatted += f"  {i}. {rec}\n"

        formatted += "\nDetailed Warnings:\n"
        formatted += "=" * 50 + "\n"

        for i, warning in enumerate(report.warnings, 1):
            formatted += f"\n[Warning {i}]\n"
            formatted += self.format_warning_for_user(warning)

        return formatted
