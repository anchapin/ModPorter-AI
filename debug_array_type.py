#!/usr/bin/env python3

import sys
sys.path.append('/home/anchapin/ModPorter-AI/ai-engine/src')
import javalang

java_code = """
public class TestClass {
    public void processItems(ItemStack[] items) {
        // Process items
    }
}
"""

tree = javalang.parse.parse(java_code)
method_node = tree.types[0].body[0]

print("Method name:", method_node.name)
print("Parameters:", method_node.parameters)

for param in method_node.parameters:
    print(f"Parameter name: {param.name}")
    print(f"Parameter type: {param.type}")
    print(f"Parameter type type: {type(param.type)}")
    print(f"Parameter type attributes: {dir(param.type)}")
    
    if hasattr(param.type, 'name'):
        print(f"Type name: {param.type.name}")
    if hasattr(param.type, 'dimensions'):
        print(f"Dimensions: {param.type.dimensions}")
    if hasattr(param.type, 'type'):
        print(f"Nested type: {param.type.type}")
        if hasattr(param.type.type, 'name'):
            print(f"Nested type name: {param.type.type.name}")
