import re
from typing import Tuple


class MojmapMappingValidator:
    """
    Validates that Java source code uses Mojmap naming conventions.
    SRG/MCP mappings use patterns like func_NNNNN, field_NNNNN, net_minecraft_.
    Mojmap uses readable names like registerBlock, getDefaultState.
    """

    SRG_PATTERNS = [
        r"\bfunc_\d+",          # func_123456
        r"\bfield_\d+",         # field_123456
        r"\bclass_\d+",         # class_123456 (inner classes)
        r"net_minecraft_\w",  # net_minecraft_X (at least one char after underscore)
    ]

    def __init__(self):
        self._compiled_patterns = [re.compile(p) for p in self.SRG_PATTERNS]

    def validate(self, java_source: str) -> Tuple[bool, str]:
        """
        Check if java_source uses Mojmap naming (good) or SRG/MCP naming (bad).

        Returns (is_valid, message):
            - (True, "Mojmap") if no SRG patterns found
            - (False, "SRG pattern: func_N") if SRG pattern detected
        """
        if not java_source or not java_source.strip():
            return True, "Empty source (skip)"

        for pattern in self._compiled_patterns:
            match = pattern.search(java_source)
            if match:
                return False, f"SRG pattern detected: {match.group()}"

        return True, "Mojmap"

    def filter_pairs(self, pairs: list[dict]) -> Tuple[list[dict], list[dict]]:
        """
        Filter a list of pairs into valid (Mojmap) and invalid (SRG) groups.

        Returns (valid_pairs, invalid_pairs)
        """
        valid = []
        invalid = []

        for pair in pairs:
            java_source = pair.get("java_source", "")
            is_valid, _ = self.validate(java_source)
            if is_valid:
                valid.append(pair)
            else:
                invalid.append(pair)

        return valid, invalid