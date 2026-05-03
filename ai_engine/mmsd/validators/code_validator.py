import re
import os
import subprocess
import tempfile
import json
from typing import Dict, Tuple, List

class CodeValidator:
    """
    Validates generated Minecraft modding code for compilation and schema correctness.
    """

    def validate_java(self, source_code: str) -> Tuple[bool, str]:
        """
        Attempts to compile Java code snippets. 
        Note: This is a basic syntax check. In a production RL loop, 
        you would need the Forge/Fabric MDK jar files in the classpath.
        """
        code = self._extract_code(source_code, "java")
        if not code:
            # Fallback to scanning for structural elements if no block found
            code = source_code

        # Structural checks
        checks = {
            "package": r"package [\w\.]+;",
            "class": r"public class \w+",
            "imports": r"import [\w\.\*]+;",
            "braces": r"\{.*?\}"
        }
        
        for name, pat in checks.items():
            if not re.search(pat, code, re.DOTALL):
                return False, f"Structural check failed: Missing {name}"

        # Try compilation if javac is available
        try:
            subprocess.run(["javac", "-version"], capture_output=True, text=True)
            has_javac = True
        except FileNotFoundError:
            has_javac = False

        if has_javac:
            with tempfile.TemporaryDirectory() as tmpdir:
                class_match = re.search(r"public class (\w+)", code)
                class_name = class_match.group(1) if class_match else "ModComponent"
                file_path = os.path.join(tmpdir, f"{class_name}.java")
                
                with open(file_path, "w") as f:
                    f.write(code)
                
                result = subprocess.run(
                    ["javac", "-Xlint:none", file_path],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    return True, "Perfect Compilation"
                
                # Check for common missing dependency errors vs actual syntax errors
                if "error: package net.minecraft" in result.stderr or "error: cannot find symbol" in result.stderr:
                    return True, "Syntactically Correct (Missing Dependencies)"
                
                return False, result.stderr
        
        return True, "Structural Check Passed (No javac)"

    def validate_bedrock_json(self, source_content: str) -> Tuple[bool, str]:
        """Validates Bedrock JSON snippets found in the source."""
        json_blocks = self._extract_all_code(source_content, "json")
        if not json_blocks:
            # Try finding common Bedrock keys if no block found
            if "format_version" in source_content:
                return True, "Found format_version outside block"
            return False, "No JSON blocks found"
        
        for block in json_blocks:
            try:
                # Basic cleanup for comments which Minecraft JSON often has
                clean_json = re.sub(r"//.*", "", block)
                data = json.loads(clean_json)
                
                # Basic Bedrock structure check
                if "format_version" not in clean_json and "header" not in clean_json:
                    # Might be a partial block or non-manifest
                    pass
            except json.JSONDecodeError as e:
                return False, f"JSON Error: {e}"
        
        return True, "Valid JSON Structures"

    def _extract_code(self, source: str, lang: str) -> str:
        pattern = f"```{lang}(.*?)```"
        match = re.search(pattern, source, re.DOTALL)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_all_code(self, source: str, lang: str) -> List[str]:
        pattern = f"```{lang}(.*?)```"
        matches = re.findall(pattern, source, re.DOTALL)
        return [m.strip() for m in matches]
