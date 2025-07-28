"""
Test Mod Validation Framework for ModPorter AI
Validates comprehensive test mods for conversion testing.

Implements Issue #213: Test Mod Validation Requirements
"""

import json
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Result of test mod validation."""
    is_valid: bool
    mod_name: str
    mod_type: str
    errors: List[str]
    warnings: List[str]
    features: List[str]
    expected_conversion_challenges: List[str]


class TestModValidator:
    """Validates test mods for comprehensive ModPorter AI testing."""
    
    def __init__(self):
        """Initialize the test mod validator."""
        self.validation_rules = {
            "entity": self._validate_entity_mod,
            "gui": self._validate_gui_mod,
            "logic": self._validate_complex_logic_mod
        }
    
    def validate_mod(self, jar_path: Path) -> ValidationResult:
        """Validate a single test mod JAR file.
        
        Args:
            jar_path: Path to the JAR file to validate
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(
            is_valid=True,
            mod_name=jar_path.stem,
            mod_type=self._determine_mod_type(jar_path.stem),
            errors=[],
            warnings=[],
            features=[],
            expected_conversion_challenges=[]
        )
        
        if not jar_path.exists():
            result.errors.append(f"JAR file does not exist: {jar_path}")
            result.is_valid = False
            return result
        
        try:
            with zipfile.ZipFile(jar_path, 'r') as zf:
                self._validate_basic_structure(zf, result)
                self._validate_fabric_metadata(zf, result)
                
                # Type-specific validation
                if result.mod_type in self.validation_rules:
                    self.validation_rules[result.mod_type](zf, result)
                
                self._analyze_features(zf, result)
                self._predict_conversion_challenges(zf, result)
                
        except zipfile.BadZipFile:
            result.errors.append("Invalid ZIP/JAR file format")
            result.is_valid = False
        except Exception as e:
            result.errors.append(f"Validation error: {str(e)}")
            result.is_valid = False
        
        result.is_valid = len(result.errors) == 0
        return result
    
    def validate_test_suite(self, test_dir: Path) -> Dict[str, List[ValidationResult]]:
        """Validate entire test mod suite.
        
        Args:
            test_dir: Directory containing test mod categories
            
        Returns:
            Dictionary mapping categories to validation results
        """
        results = {}
        
        for category_dir in test_dir.iterdir():
            if category_dir.is_dir():
                category_results = []
                
                for jar_file in category_dir.glob("*.jar"):
                    validation_result = self.validate_mod(jar_file)
                    category_results.append(validation_result)
                
                results[category_dir.name] = category_results
        
        return results
    
    def _determine_mod_type(self, mod_name: str) -> str:
        """Determine mod type from name."""
        if "entity" in mod_name:
            return "entity"
        elif "gui" in mod_name:
            return "gui"
        elif "logic" in mod_name:
            return "logic"
        else:
            return "unknown"
    
    def _validate_basic_structure(self, zf: zipfile.ZipFile, result: ValidationResult):
        """Validate basic JAR structure."""
        files = zf.namelist()
        
        # Check for required files
        required_files = ["fabric.mod.json", "META-INF/MANIFEST.MF"]
        for required_file in required_files:
            if required_file not in files:
                result.errors.append(f"Missing required file: {required_file}")
        
        # Check for Java classes
        java_classes = [f for f in files if f.endswith('.class')]
        if not java_classes:
            result.warnings.append("No compiled Java classes found")
        
        # Check for assets
        asset_files = [f for f in files if f.startswith('assets/')]
        if not asset_files:
            result.warnings.append("No asset files found")
    
    def _validate_fabric_metadata(self, zf: zipfile.ZipFile, result: ValidationResult):
        """Validate Fabric mod metadata."""
        try:
            fabric_data = zf.read("fabric.mod.json").decode('utf-8')
            metadata = json.loads(fabric_data)
            
            # Check required fields
            required_fields = ["schemaVersion", "id", "version", "name"]
            for field in required_fields:
                if field not in metadata:
                    result.errors.append(f"Missing fabric.mod.json field: {field}")
            
            # Validate structure
            if "entrypoints" not in metadata:
                result.warnings.append("No entrypoints defined in fabric.mod.json")
            
            if "depends" not in metadata:
                result.warnings.append("No dependencies defined in fabric.mod.json")
            
            result.features.append(f"Fabric mod ID: {metadata.get('id', 'unknown')}")
            
        except (KeyError, json.JSONDecodeError) as e:
            result.errors.append(f"Invalid fabric.mod.json: {str(e)}")
    
    def _validate_entity_mod(self, zf: zipfile.ZipFile, result: ValidationResult):
        """Validate entity-specific mod features."""
        files = zf.namelist()
        
        # Check for entity classes
        entity_classes = [f for f in files if "Entity.java" in f or "Entity.class" in f]
        if not entity_classes:
            result.errors.append("No entity classes found in entity mod")
        else:
            result.features.append(f"Entity classes: {len(entity_classes)}")
        
        # Check for entity assets
        entity_textures = [f for f in files if "/textures/entity/" in f]
        if not entity_textures:
            result.warnings.append("No entity textures found")
        else:
            result.features.append(f"Entity textures: {len(entity_textures)}")
        
        entity_models = [f for f in files if "/models/entity/" in f]
        if entity_models:
            result.features.append(f"Entity models: {len(entity_models)}")
        
        # Check for loot tables
        loot_tables = [f for f in files if "/loot_tables/entities/" in f]
        if loot_tables:
            result.features.append(f"Entity loot tables: {len(loot_tables)}")
        
        # Entity-specific conversion challenges
        result.expected_conversion_challenges.extend([
            "Entity AI behavior conversion",
            "Entity model format conversion",
            "Spawn rules and biome restrictions",
            "Entity sound and animation mapping"
        ])
    
    def _validate_gui_mod(self, zf: zipfile.ZipFile, result: ValidationResult):
        """Validate GUI-specific mod features."""
        files = zf.namelist()
        
        # Check for GUI classes
        gui_classes = [f for f in files if any(gui_term in f.lower() for gui_term in 
                      ["screen", "gui", "overlay", "hud", "inventory"])]
        if not gui_classes:
            result.errors.append("No GUI classes found in GUI mod")
        else:
            result.features.append(f"GUI classes: {len(gui_classes)}")
        
        # Check for GUI textures
        gui_textures = [f for f in files if "/textures/gui/" in f]
        if not gui_textures:
            result.warnings.append("No GUI textures found")
        else:
            result.features.append(f"GUI textures: {len(gui_textures)}")
        
        # Check for screen handlers
        screen_handlers = [f for f in files if "ScreenHandler" in f or "Container" in f]
        if screen_handlers:
            result.features.append(f"Screen handlers: {len(screen_handlers)}")
        
        # GUI-specific conversion challenges
        result.expected_conversion_challenges.extend([
            "Custom GUI layout conversion",
            "Screen interaction mapping",
            "Inventory slot positioning",
            "Client-side rendering adaptation"
        ])
    
    def _validate_complex_logic_mod(self, zf: zipfile.ZipFile, result: ValidationResult):
        """Validate complex logic mod features."""
        files = zf.namelist()
        
        # Check for complex logic patterns
        logic_patterns = {
            "machinery": ["Machine", "Process", "Tick"],
            "multiblock": ["Multiblock", "Controller", "Structure"],
            "automation": ["Automation", "Node", "Network", "Pipeline"]
        }
        
        found_patterns = []
        for pattern_type, patterns in logic_patterns.items():
            for pattern in patterns:
                matching_files = [f for f in files if pattern in f]
                if matching_files:
                    found_patterns.append(f"{pattern_type}: {pattern}")
        
        if not found_patterns:
            result.warnings.append("No complex logic patterns detected")
        else:
            result.features.extend(found_patterns)
        
        # Check for block entities
        block_entities = [f for f in files if "BlockEntity" in f or "TileEntity" in f]
        if block_entities:
            result.features.append(f"Block entities: {len(block_entities)}")
        
        # Check for data structures
        data_files = [f for f in files if f.startswith('data/')]
        if data_files:
            result.features.append(f"Data files: {len(data_files)}")
        
        # Complex logic conversion challenges
        result.expected_conversion_challenges.extend([
            "Complex state management",
            "Multi-block structure recognition",
            "Advanced redstone interaction",
            "Custom data persistence",
            "Inter-block communication protocols"
        ])
    
    def _analyze_features(self, zf: zipfile.ZipFile, result: ValidationResult):
        """Analyze mod features for conversion complexity."""
        files = zf.namelist()
        
        # Count different file types
        file_counts = {
            "Java sources": len([f for f in files if f.endswith('.java')]),
            "Class files": len([f for f in files if f.endswith('.class')]),
            "Textures": len([f for f in files if f.endswith('.png')]),
            "Models": len([f for f in files if f.endswith('.json') and '/models/' in f]),
            "Recipes": len([f for f in files if '/recipes/' in f]),
            "Loot tables": len([f for f in files if '/loot_tables/' in f])
        }
        
        for file_type, count in file_counts.items():
            if count > 0:
                result.features.append(f"{file_type}: {count}")
        
        # Check for advanced features
        advanced_features = [
            ("Mixins", "mixins.json"),
            ("Access transformers", "accesstransformer.cfg"),
            ("Custom registries", "Registry.register"),
            ("Data generation", "DataGenerator")
        ]
        
        for feature_name, pattern in advanced_features:
            matching_files = [f for f in files if pattern in f]
            if matching_files:
                result.features.append(f"Advanced: {feature_name}")
    
    def _predict_conversion_challenges(self, zf: zipfile.ZipFile, result: ValidationResult):
        """Predict potential conversion challenges."""
        files = zf.namelist()
        
        # Common conversion challenges
        if any("mixin" in f.lower() for f in files):
            result.expected_conversion_challenges.append("Mixin bytecode manipulation")
        
        if any("/client/" in f for f in files):
            result.expected_conversion_challenges.append("Client-side specific code")
        
        if any("network" in f.lower() for f in files):
            result.expected_conversion_challenges.append("Custom networking protocols")
        
        if any("worldgen" in f.lower() or "biome" in f.lower() for f in files):
            result.expected_conversion_challenges.append("World generation features")
        
        # Add general challenges
        result.expected_conversion_challenges.extend([
            "Java to Bedrock API mapping",
            "Resource pack structure conversion",
            "Behavior pack adaptation"
        ])
    
    def generate_validation_report(self, results: Dict[str, List[ValidationResult]]) -> str:
        """Generate a comprehensive validation report.
        
        Args:
            results: Validation results by category
            
        Returns:
            Formatted validation report
        """
        report_lines = [
            "=" * 80,
            "MODPORTER AI TEST MOD VALIDATION REPORT",
            "=" * 80,
            ""
        ]
        
        total_mods = sum(len(category_results) for category_results in results.values())
        valid_mods = sum(len([r for r in category_results if r.is_valid]) 
                        for category_results in results.values())
        
        report_lines.extend([
            f"📊 SUMMARY:",
            f"   Total test mods: {total_mods}",
            f"   Valid mods: {valid_mods}",
            f"   Invalid mods: {total_mods - valid_mods}",
            f"   Success rate: {(valid_mods/total_mods*100):.1f}%",
            ""
        ])
        
        for category, category_results in results.items():
            report_lines.extend([
                f"📁 {category.upper()} CATEGORY ({len(category_results)} mods):",
                "-" * 60
            ])
            
            for result in category_results:
                status = "✅ VALID" if result.is_valid else "❌ INVALID"
                report_lines.append(f"   {status} {result.mod_name}")
                
                if result.features:
                    report_lines.append(f"      Features: {', '.join(result.features[:3])}{'...' if len(result.features) > 3 else ''}")
                
                if result.errors:
                    report_lines.append(f"      🚨 Errors: {len(result.errors)}")
                    for error in result.errors[:2]:
                        report_lines.append(f"         - {error}")
                
                if result.warnings:
                    report_lines.append(f"      ⚠️  Warnings: {len(result.warnings)}")
                
                if result.expected_conversion_challenges:
                    challenges = result.expected_conversion_challenges[:2]
                    report_lines.append(f"      🎯 Conversion challenges: {', '.join(challenges)}{'...' if len(result.expected_conversion_challenges) > 2 else ''}")
                
                report_lines.append("")
            
            report_lines.append("")
        
        report_lines.extend([
            "=" * 80,
            "✅ VALIDATION COMPLETE",
            "   Test suite ready for ModPorter AI conversion testing!",
            "=" * 80
        ])
        
        return "\n".join(report_lines)


def validate_test_suite(test_dir: Optional[Path] = None) -> Dict[str, List[ValidationResult]]:
    """Validate the complete test mod suite.
    
    Args:
        test_dir: Directory containing test mods (defaults to fixtures/test_mods)
        
    Returns:
        Validation results by category
    """
    if test_dir is None:
        test_dir = Path(__file__).parent / "test_mods"
    
    validator = TestModValidator()
    return validator.validate_test_suite(test_dir)


if __name__ == "__main__":
    # Run validation when executed directly
    test_dir = Path(__file__).parent / "test_mods"
    
    validator = TestModValidator()
    results = validator.validate_test_suite(test_dir)
    
    report = validator.generate_validation_report(results)
    print(report)
    
    # Save report to file
    report_file = Path(__file__).parent / "test_validation_report.md"
    with open(report_file, 'w') as f:
        f.write(f"# ModPorter AI Test Mod Validation Report\n\n```\n{report}\n```\n")
    
    print(f"\n📄 Detailed report saved to: {report_file}")