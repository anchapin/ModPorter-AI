import unittest
import json
from src.agents.logic_translator import LogicTranslatorAgent

class TestLogicTranslatorAgent(unittest.TestCase):
    def test_translate_java_block_tool(self):
        # 1. Define a sample input JSON string
        java_block_json = json.dumps({
            "features": {
                "block_properties": {
                    "name": "magic_crystal",
                    "destroy_time": 5.0,
                    "explosion_resistance": 15.0,
                    "light_emission": 10
                }
            }
        })

        # 2. Call the translate_java_block_tool with the sample input
        result_json = LogicTranslatorAgent.translate_java_block_tool(java_block_json)

        # 3. Assert that the output is a valid JSON string
        try:
            result = json.loads(result_json)
        except json.JSONDecodeError:
            self.fail("The output of translate_java_block_tool is not a valid JSON string.")

        # 4. Parse the output JSON and assert that the generated Bedrock block JSON has the correct structure and values
        self.assertTrue(result["success"])
        bedrock_block = result["bedrock_block_json"]

        self.assertEqual(bedrock_block["format_version"], "1.19.0")
        self.assertEqual(bedrock_block["minecraft:block"]["description"]["identifier"], "custom:magic_crystal")

        components = bedrock_block["minecraft:block"]["components"]
        self.assertEqual(components["minecraft:destroy_time"], 5.0)
        self.assertEqual(components["minecraft:explosion_resistance"], 15.0)
        self.assertEqual(components["minecraft:light_emission"], 10)

if __name__ == "__main__":
    unittest.main()
