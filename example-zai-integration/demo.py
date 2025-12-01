#!/usr/bin/env python3
"""
Demo script showing langchain-code + Z.AI integration usage
"""
import os
from pathlib import Path
from langchain_zai_integration import LangChainZAIIntegration

def demo_feature_implementation():
    """Demo: Implement a new feature"""
    print("🔧 Demo: Feature Implementation")
    print("=" * 50)

    integration = LangChainZAIIntegration(
        model="GLM-4.6",
        project_instructions=".langcode/langcode.md"
    )

    feature_request = """
    Create a Python class for managing a todo list with the following features:
    - Add tasks with priorities (high, medium, low)
    - Mark tasks as completed
    - List tasks by priority or completion status
    - Persistent storage using JSON
    - Thread-safe operations
    """

    result = integration.implement_feature(
        feature_request,
        context="Building a command-line todo application"
    )

    print("Generated Implementation:")
    print(result)

def demo_bug_fixing():
    """Demo: Fix a bug"""
    print("\n🐛 Demo: Bug Fixing")
    print("=" * 50)

    integration = LangChainZAIIntegration(model="GLM-4.5")

    bug_report = """
    Python application crashes with IndexError when processing empty lists.
    The error occurs in the data_processing module when trying to access
    list[0] without checking if the list is empty.
    """

    buggy_code = """
    def process_data(data_list):
        # This line causes the crash when data_list is empty
        first_item = data_list[0]

        processed_items = []
        for item in data_list:
            processed_items.append(item.upper())

        return processed_items
    """

    fix = integration.fix_bug(bug_report, buggy_code)
    print("Bug Analysis and Fix:")
    print(fix)

def demo_code_analysis():
    """Demo: Code analysis"""
    print("\n📊 Demo: Code Analysis")
    print("=" * 50)

    integration = LangChainZAIIntegration(model="GLM-4.6")

    code_to_analyze = '''
    class DatabaseManager:
        def __init__(self):
            self.connections = {}
            self.is_connected = False

        def connect(self, host, port, username, password):
            import sqlite3
            self.connections["default"] = sqlite3.connect(":memory:")
            self.is_connected = True

        def execute_query(self, query):
            if not self.is_connected:
                raise Exception("Not connected to database")

            cursor = self.connections["default"].cursor()
            cursor.execute(query)
            return cursor.fetchall()
    '''

    analysis = integration.analyze_code(
        code_to_analyze,
        analysis_type="security, performance, and best practices"
    )
    print("Code Analysis Results:")
    print(analysis)

def demo_interactive_session():
    """Demo: Interactive coding session"""
    print("\n💬 Demo: Interactive Session (Limited)")
    print("=" * 50)
    print("This demo shows the structure. Run the actual interactive session with:")
    print("integration.interactive_chat()")

def main():
    """Run all demos"""
    print("🚀 LangChain + Z.AI Integration Demo")
    print("=" * 60)

    # Check for API key
    if not os.getenv("ZAI_API_KEY"):
        print("⚠️  Warning: ZAI_API_KEY environment variable not set")
        print("Set it in your .env file to run actual demos")
        return

    try:
        demo_feature_implementation()
        demo_bug_fixing()
        demo_code_analysis()
        demo_interactive_session()

        print("\n✅ Demo completed successfully!")
        print("\nTo try it yourself:")
        print("1. Set your ZAI_API_KEY in .env")
        print("2. Run: python demo.py")
        print("3. Or start an interactive session with:")
        print("   integration.interactive_chat()")

    except Exception as e:
        print(f"❌ Demo failed: {str(e)}")
        print("Make sure your Z.AI API key is valid and you have internet access")

if __name__ == "__main__":
    main()