# ai-engine/src/agents/validation_agent.py
import uuid
import os
import time
import random

from src.models.validation import (
    ManifestValidationResult,
    SemanticAnalysisResult,
    BehaviorPredictionResult,
    AssetValidationResult,
    ValidationReport as AgentValidationReport
)

class LLMSemanticAnalyzer:
    def __init__(self, api_key: str = "MOCK_API_KEY"):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("API key for LLM Semantic Analyzer is required.")
        print("LLMSemanticAnalyzer initialized (mock). API Key: " + self.api_key[:10] + "...")

    def analyze(self, code_snippet: str) -> dict:
        if not code_snippet:
            print("LLMSemanticAnalyzer: No code snippet provided.")
            return {
                "intent_preserved": False, "confidence": 0.1,
                "findings": ["No code provided for analysis."]
            }
        print("LLMSemanticAnalyzer: Analyzing code snippet (first 50 chars): '" + code_snippet[:50] + "...'")
        # Use asyncio.sleep in async context, time.sleep in sync context
        # Since this is called from a synchronous context, we'll keep time.sleep but with a shorter duration
        time.sleep(random.uniform(0.05, 0.1))  # Reduced sleep time
        intent_preserved = True
        confidence = random.uniform(0.75, 0.95)
        findings = []
        if "TODO" in code_snippet or "FIXME" in code_snippet:
            intent_preserved = False
            confidence *= 0.7
            findings.append("Code contains 'TODO'/'FIXME' markers.")
        if "unsafe" in code_snippet.lower() or "danger" in code_snippet.lower():
            confidence *= 0.8
            findings.append("Code contains 'unsafe'/'danger' keywords.")
        if len(code_snippet) < 50 and "simple" not in code_snippet.lower():
            confidence *= 0.9
            findings.append("Code snippet is very short.")
        if "complex_logic_pattern" in code_snippet:
            confidence *= 0.85
            findings.append("Identified complex logic pattern.")
        if "error" in code_snippet.lower() or "exception" in code_snippet.lower() and "handle" not in code_snippet.lower():
            intent_preserved = False
            confidence *= 0.6
            findings.append("Code mentions unhandled 'error'/'exception'.")
        confidence = min(max(confidence, 0.0), 1.0)
        if not findings and intent_preserved and confidence > 0.8:
            findings.append("Code appears semantically sound (mock).")
        elif not findings:
            findings.append("Mock analysis complete.")
        print("LLMSemanticAnalyzer: Analysis complete. Intent preserved: %s, Confidence: %.2f" % (intent_preserved, confidence))
        return {"intent_preserved": intent_preserved, "confidence": round(confidence, 2), "findings": findings}

class BehaviorAnalysisEngine:
    def __init__(self):
        print("BehaviorAnalysisEngine initialized (mock).")

    def predict_behavior(self, java_code: str, bedrock_code: str) -> dict:
        if not java_code and not bedrock_code:
            print("BehaviorAnalysisEngine: No Java or Bedrock code provided.")
            return {
                "behavior_diff": "No code provided for comparison.",
                "confidence": 0.0,
                "potential_issues": ["Cannot analyze behavior without code inputs."]
            }

        print("BehaviorAnalysisEngine: Predicting behavior differences...")
        print("Java (first 50): '" + java_code[:50] + "...'")
        print("Bedrock (first 50): '" + bedrock_code[:50] + "...'")

        # Reduced sleep time for mock processing
        time.sleep(random.uniform(0.05, 0.1))

        behavior_diff = "No significant differences predicted (mock)."
        confidence = random.uniform(0.70, 0.90)
        potential_issues = []

        if "thread" in java_code.lower() and "thread" not in bedrock_code.lower() and "async" not in bedrock_code.lower():
            behavior_diff = "Potential difference in concurrency model (Java uses threads, Bedrock may need async/event-driven)."
            confidence *= 0.7
            potential_issues.append("Java code mentions 'thread'; ensure Bedrock equivalent handles concurrency correctly.")

        if "file IO" in java_code.lower() or "java.io" in java_code:
            if "http" not in bedrock_code.lower() and "script.storage" not in bedrock_code.lower():
                behavior_diff = "Difference in data persistence/IO. Java file IO may not map directly."
                confidence *= 0.6
                potential_issues.append("Java code uses file IO. Bedrock has limited local storage or requires HTTP for external data.")

        if "reflection" in java_code.lower():
            behavior_diff = "Java reflection usage has no direct equivalent in Bedrock scripting."
            confidence *= 0.5
            potential_issues.append("Java's reflection capabilities are not available in Bedrock's JavaScript environment.")

        if "complex_event_handling" in java_code.lower() and "simple_event" in bedrock_code.lower():
            behavior_diff = "Potential simplification or loss of nuance in event handling."
            confidence *= 0.75
            potential_issues.append("Java code indicates complex event handling; ensure Bedrock script captures all necessary event triggers.")

        if not bedrock_code and java_code:
            behavior_diff = "Bedrock code is empty or missing; Java functionality will be lost."
            confidence = 0.1
            potential_issues.append("No Bedrock code provided to match Java functionality.")

        confidence = min(max(confidence, 0.0), 1.0)

        if not potential_issues and confidence > 0.8:
            potential_issues.append("Behavior prediction suggests good correspondence (mock analysis).")
        elif not potential_issues:
            potential_issues.append("Mock behavior prediction complete; review confidence.")

        print("BehaviorAnalysisEngine: Prediction complete. Confidence: %.2f" % confidence)

        return {
            "behavior_diff": behavior_diff,
            "confidence": round(confidence, 2),
            "potential_issues": potential_issues
        }

class AssetIntegrityChecker:
    def __init__(self):
        self.supported_image_extensions = {".png", ".jpg", ".jpeg", ".tga"}
        self.supported_sound_extensions = {".ogg", ".wav", ".mp3"}
        self.supported_model_extensions = {".json"}
        print("AssetIntegrityChecker initialized.")
    def validate_assets(self, asset_files: list, base_path: str = "") -> dict:
        print("Validating %d asset files. Base path: '%s'" % (len(asset_files), base_path))
        corrupted_files, asset_specific_issues = [], {}
        if not asset_files:
            return {"all_assets_valid": True, "corrupted_files": [], "asset_specific_issues": {"general": ["No asset files provided."] }}
        for asset_path in asset_files:
            full_path = os.path.join(base_path, asset_path) if base_path and base_path != "." else asset_path
            if "missing" in asset_path.lower():
                corrupted_files.append(asset_path)
                asset_specific_issues.setdefault(asset_path, []).append("File missing: '%s'." % full_path)
                continue
            _, ext = os.path.splitext(asset_path)
            ext = ext.lower()
            issues = []
            if ext in self.supported_image_extensions:
                if "corrupt_texture" in asset_path:
                    issues.append("Mock: Texture corrupt.")
                if "oversized_texture" in asset_path:
                    issues.append("Mock: Texture oversized.")
            elif ext in self.supported_sound_extensions:
                if ext != ".ogg" and "allow_non_ogg" not in asset_path:
                    issues.append("Mock: Non-preferred sound format '%s'." % ext)
                if "corrupt_sound" in asset_path:
                    issues.append("Mock: Sound corrupt.")
            elif ext in self.supported_model_extensions:
                if "invalid_geo" in asset_path:
                    issues.append("Mock: Model geo invalid.")
            elif not ext:
                issues.append("Warning: File '%s' no extension." % asset_path)
            else:
                issues.append("Warning: Unrecognized extension '%s' for '%s'." % (ext, asset_path))
            if issues:
                corrupted_files.append(asset_path)
                asset_specific_issues.setdefault(asset_path, []).extend(issues)
        return {"all_assets_valid": not corrupted_files, "corrupted_files": list(set(corrupted_files)), "asset_specific_issues": asset_specific_issues}

class ManifestValidator:
    def __init__(self):
        pass
        
    def validate_manifest(self, md: dict) -> ManifestValidationResult:
        err, warn = [], []
        if not isinstance(md, dict):
            return ManifestValidationResult(is_valid=False, errors=["Manifest not dict."], warnings=warn)
        fv = md.get("format_version")
        if fv is None:
            err.append("Missing 'format_version'.")
        elif not isinstance(fv, int):
            if isinstance(fv, str) and fv.isdigit():
                warn.append("format_version (%s) is str, should be int." % str(fv))
                fv = int(fv)
            else:
                err.append("format_version (%s) must be int." % str(fv))
        if isinstance(fv, int) and fv != 2:
            warn.append("format_version (%s) not typical (2)." % str(fv))
        hd = md.get("header")
        if hd is None:
            err.append("Missing 'header'.")
        elif not isinstance(hd, dict):
            err.append("'header' not dict.")
        else:
            for field in ["name","description","uuid","version"]:
                if field not in hd:
                    err.append("Header missing '%s'." % field)
            if hd.get("uuid"):
                try:
                    uuid.UUID(str(hd.get("uuid")))
                except ValueError:
                    err.append("Header uuid (%s) invalid." % str(hd.get("uuid")))
            v = hd.get("version")
            if v and not (isinstance(v,list) and len(v)==3 and all(isinstance(i,int) for i in v)):
                err.append("Header version (%s) invalid." % str(v))
            mev = hd.get("min_engine_version")
            if mev and not (isinstance(mev,list) and len(mev)>=3 and all(isinstance(i,int) for i in mev)):
                warn.append("Header min_engine_version (%s) invalid." % str(mev))
        mods = md.get("modules")
        if mods is None:
            err.append("Missing 'modules'.")
        elif not isinstance(mods, list):
            err.append("'modules' not list.")
        else:
            if not mods:
                warn.append("'modules' empty.")
            for i, m in enumerate(mods):
                if not isinstance(m, dict):
                    err.append("Module %d not dict." % i)
                    continue
                for field in ["type", "uuid", "version"]:
                    if field not in m:
                        err.append("Module %d missing '%s'." % (i, field))
                if m.get("uuid"):
                    try:
                        uuid.UUID(str(m.get("uuid")))
                    except ValueError:
                        err.append("Module %d uuid (%s) invalid." % (i, str(m.get("uuid"))))
                mv = m.get("version")
                if mv and not (isinstance(mv, list) and len(mv) == 3 and all(isinstance(x, int) for x in mv)):
                    err.append("Module %d version (%s) invalid." % (i, str(mv)))
                mt = m.get("type")
                ok = ["data", "resources", "script", "client_data", "world_template", "skin_pack", "javascript"]
                if mt and mt not in ok:
                    warn.append("Module %d type ('%s') non-standard." % (i, mt))
                if mt in ["script", "javascript"] and "entry" not in m:
                    warn.append("Module %d type '%s' missing 'entry'." % (i, mt))
        return ManifestValidationResult(is_valid=not err, errors=err, warnings=warn)

class ValidationAgent:
    def __init__(self):
        self.semantic_analyzer = LLMSemanticAnalyzer()
        self.behavior_predictor = BehaviorAnalysisEngine()
        self.asset_validator = AssetIntegrityChecker()
        self.manifest_validator = ManifestValidator()
        print("ValidationAgent initialized with all components.")

    def validate_conversion(self, conversion_artifacts: dict) -> AgentValidationReport:
        print("Starting validation process...")
        conversion_id = conversion_artifacts.get('conversion_id', "unknown_conversion")
        java_code = conversion_artifacts.get('java_code', "")
        bedrock_code = conversion_artifacts.get('bedrock_code', "")
        asset_files = conversion_artifacts.get('asset_files', [])
        asset_base_path = conversion_artifacts.get('asset_base_path', "")
        manifest_data = conversion_artifacts.get('manifest_data', {})

        semantic_raw = self.semantic_analyzer.analyze(bedrock_code)
        behavior_raw = self.behavior_predictor.predict_behavior(java_code, bedrock_code)
        asset_raw = self.asset_validator.validate_assets(asset_files, base_path=asset_base_path)
        manifest_result_model = self.manifest_validator.validate_manifest(manifest_data)

        semantic_model = SemanticAnalysisResult(**semantic_raw)
        behavior_model = BehaviorPredictionResult(**behavior_raw)
        asset_model = AssetValidationResult(**asset_raw)

        conf_semantic = semantic_model.confidence
        conf_behavior = behavior_model.confidence
        conf_asset = 1.0 if asset_model.all_assets_valid else 0.3
        conf_manifest = 1.0 if manifest_result_model.is_valid else 0.3

        overall_confidence = (conf_semantic * 0.3) + (conf_behavior * 0.4) + (conf_asset * 0.15) + (conf_manifest * 0.15)
        overall_confidence = round(min(max(overall_confidence, 0.0), 1.0), 2)

        recommendations = []
        if not semantic_model.intent_preserved or semantic_model.confidence < 0.7:
            recommendations.append("Semantic analysis suggests potential issues; manual review of code logic advised.")
        for finding in semantic_model.findings:
            if "appears semantically sound" not in finding and "Mock analysis complete" not in finding:
                recommendations.append("Semantic finding: " + finding)

        if behavior_model.confidence < 0.7 or "No significant differences predicted" not in behavior_model.behavior_diff :
            recommendations.append("Behavior prediction indicates potential differences: " + behavior_model.behavior_diff)
        for issue in behavior_model.potential_issues:
            if "good correspondence" not in issue and "Mock behavior prediction complete" not in issue:
                 recommendations.append("Behavioral issue: " + issue)

        if not asset_model.all_assets_valid and asset_model.corrupted_files:
            recommendations.append("Review " + str(len(asset_model.corrupted_files)) + " asset(s) with issues.")
        if asset_model.asset_specific_issues.get("general"):
            recommendations.extend(asset_model.asset_specific_issues["general"])
        if not manifest_result_model.is_valid:
            recommendations.append("Manifest has errors. Please check details.")
        if manifest_result_model.warnings:
            recommendations.append("Manifest has warnings. Review for optimal compatibility.")

        report = AgentValidationReport(
            conversion_id=conversion_id,
            semantic_analysis=semantic_model,
            behavior_prediction=behavior_model,
            asset_integrity=asset_model,
            manifest_validation=manifest_result_model,
            overall_confidence=overall_confidence,
            recommendations=list(set(recommendations))
        )

        print("Validation process completed.")
        return report

if __name__ == '__main__':
    agent = ValidationAgent()

    valid_manifest_for_tests = {
        "format_version": 2,
        "header": {"name": "Test Pack", "description": "Valid.", "uuid": str(uuid.uuid4()), "version": [1,0,0]},
        "modules": [{"type": "data", "uuid": str(uuid.uuid4()), "version": [1,0,0]}]
    }

    behavior_code_samples = {
        "simple_match": {"java": "System.out.println(\"Hello\");", "bedrock": "console.log(\"Hello\");"},
        "threading_diff": {"java": "new Thread().start();", "bedrock": "// Needs async solution"},
        "file_io_java": {"java": "import java.io.File; new File(\"test.txt\");", "bedrock": "// Script storage or HTTP"},
        "reflection_java": {"java": "obj.getClass().getMethods();", "bedrock": "// No equivalent"},
        "empty_bedrock": {"java": "int main() { return 0; }", "bedrock": ""}
    }

    for test_name, codes in behavior_code_samples.items():
        print("\n--- Test Case (Agent - Behavior - %s) ---" % test_name)
        mock_artifacts_behavior = {
            'conversion_id': 'conv_behavior_' + test_name,
            'java_code': codes["java"],
            'bedrock_code': codes["bedrock"],
            'asset_files': [], 'manifest_data': valid_manifest_for_tests
        }
        report_behavior_test = agent.validate_conversion(mock_artifacts_behavior)
        print(report_behavior_test.model_dump_json(indent=2))

    behavior_analyzer = BehaviorAnalysisEngine()
    print("\n--- Test Case (Direct Behavior Analyzer): Simple Match ---")
    direct_behavior_simple = behavior_analyzer.predict_behavior(
        behavior_code_samples["simple_match"]["java"], behavior_code_samples["simple_match"]["bedrock"]
    )
    print(BehaviorPredictionResult(**direct_behavior_simple).model_dump_json(indent=2))

    print("\n--- Test Case (Direct Behavior Analyzer): Threading Difference ---")
    direct_behavior_thread = behavior_analyzer.predict_behavior(
        behavior_code_samples["threading_diff"]["java"], behavior_code_samples["threading_diff"]["bedrock"]
    )
    print(BehaviorPredictionResult(**direct_behavior_thread).model_dump_json(indent=2))

    print("\n--- Test Case (Direct Behavior Analyzer): No Code ---")
    direct_behavior_none = behavior_analyzer.predict_behavior("","")
    print(BehaviorPredictionResult(**direct_behavior_none).model_dump_json(indent=2))

    good_java_code = behavior_code_samples["simple_match"]["java"]
    good_semantic_code = "// Simple and clear Bedrock script\nlet value = 100;\nfunction activate() { console.log('Activated: ' + value); }"


    mock_artifacts_all_good = {
        'conversion_id': 'conv_all_good_001',
        'java_code': good_java_code,
        'bedrock_code': good_semantic_code,
        'asset_files': ["textures/block.png"], 'asset_base_path': "mock/path",
        'manifest_data': valid_manifest_for_tests
    }
    print("\n--- Test Case (Agent): All Components Good/Simple ---")
    report_all_good = agent.validate_conversion(mock_artifacts_all_good)
    print(report_all_good.model_dump_json(indent=2))
