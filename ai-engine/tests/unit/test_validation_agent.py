
import uuid
from agents.validation_agent import (
    ValidationAgent, 
    LLMSemanticAnalyzer, 
    BehaviorAnalysisEngine, 
    AssetIntegrityChecker, 
    ManifestValidator
)
from models.validation import (
    ValidationReport
)

class TestValidationAgentComponents:
    def test_llm_semantic_analyzer(self):
        analyzer = LLMSemanticAnalyzer()
        
        # Test empty snippet
        res = analyzer.analyze("")
        assert res["intent_preserved"] is False
        
        # Test good snippet
        res = analyzer.analyze("public class Test {}")
        assert res["intent_preserved"] is True
        
        # Test TODO/FIXME
        res = analyzer.analyze("// TODO: fix this")
        assert res["intent_preserved"] is False
        assert any("TODO" in f for f in res["findings"])
        
        # Test unsafe
        res = analyzer.analyze("unsafe code here")
        assert any("unsafe" in f for f in res["findings"])

    def test_behavior_analysis_engine(self):
        engine = BehaviorAnalysisEngine()
        
        # Test empty
        res = engine.predict_behavior("", "")
        assert res["confidence"] == 0.0
        
        # Test thread diff
        res = engine.predict_behavior("new Thread()", "some regular function()")
        assert "thread" in res["behavior_diff"].lower() or any("thread" in p.lower() for p in res["potential_issues"])
        
        # Test reflection
        res = engine.predict_behavior("Some code using reflection", "")
        assert any("reflection" in p.lower() for p in res["potential_issues"])

    def test_asset_integrity_checker(self):
        checker = AssetIntegrityChecker()
        
        # Test empty
        res = checker.validate_assets([])
        assert res["all_assets_valid"] is True
        
        # Test various assets
        assets = [
            "test.png",
            "corrupt_texture.png",
            "missing.png",
            "test.ogg",
            "test.wav",
            "invalid_geo.json",
            "unknown.xyz",
            "noextension"
        ]
        res = checker.validate_assets(assets)
        assert res["all_assets_valid"] is False
        assert "missing.png" in res["corrupted_files"]
        assert "corrupt_texture.png" in res["corrupted_files"]

    def test_manifest_validator(self):
        validator = ManifestValidator()
        
        # Test invalid input
        assert validator.validate_manifest(None).is_valid is False
        
        # Test valid manifest
        valid_md = {
            "format_version": 2,
            "header": {
                "name": "Test",
                "description": "Desc",
                "uuid": str(uuid.uuid4()),
                "version": [1, 0, 0]
            },
            "modules": [
                {"type": "data", "uuid": str(uuid.uuid4()), "version": [1, 0, 0]}
            ]
        }
        res = validator.validate_manifest(valid_md)
        assert res.is_valid is True
        
        # Test missing fields
        invalid_md = {"format_version": 2}
        res = validator.validate_manifest(invalid_md)
        assert res.is_valid is False
        assert any("header" in e.lower() for e in res.errors)

    def test_validation_agent_integration(self):
        agent = ValidationAgent()
        
        artifacts = {
            "conversion_id": "test_conv",
            "java_code": "public class Test {}",
            "bedrock_code": "console.log('test')",
            "asset_files": ["a.png"],
            "manifest_data": {
                "format_version": 2,
                "header": {
                    "name": "Test",
                    "description": "Desc",
                    "uuid": str(uuid.uuid4()),
                    "version": [1, 0, 0]
                },
                "modules": [{"type": "data", "uuid": str(uuid.uuid4()), "version": [1, 0, 0]}]
            }
        }
        
        report = agent.validate_conversion(artifacts)
        assert isinstance(report, ValidationReport)
        assert report.conversion_id == "test_conv"
        assert report.overall_confidence > 0
