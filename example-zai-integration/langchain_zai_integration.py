"""
Integration wrapper for langchain-code with Z.AI Coding Plan API
"""
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from langchain.chains import ConversationChain
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from zai_llm_config import create_zai_llm

class LangChainZAIIntegration:
    """Main integration class for langchain-code + Z.AI"""

    def __init__(self,
                 model: str = "GLM-4.6",
                 api_key: Optional[str] = None,
                 project_instructions: Optional[str] = None):
        self.llm = create_zai_llm(model=model, api_key=api_key)
        self.project_instructions = project_instructions
        self.memory = ConversationBufferMemory()

        # Load project instructions if provided
        if project_instructions and os.path.exists(project_instructions):
            with open(project_instructions, 'r', encoding='utf-8') as f:
                self.project_instructions = f.read()

    def create_coding_chain(self, task_type: str = "general") -> ConversationChain:
        """Create a specialized chain for different coding tasks"""

        base_prompt = """You are an expert software engineer helping with coding tasks.
You have deep knowledge of software architecture, best practices, and multiple programming languages.

Project Context:
{project_instructions}

Current Task: {task_type}

Please provide clear, well-structured code solutions with explanations when necessary."""

        if self.project_instructions:
            base_prompt = base_prompt.format(
                project_instructions=self.project_instructions,
                task_type=task_type
            )
        else:
            base_prompt = base_prompt.format(
                project_instructions="No specific project instructions provided.",
                task_type=task_type
            )

        prompt = PromptTemplate(
            input_variables=["history", "input"],
            template=base_prompt + "\n\nHuman: {input}\nAI: "
        )

        return ConversationChain(
            llm=self.llm,
            prompt=prompt,
            memory=self.memory,
            verbose=True
        )

    def implement_feature(self, feature_description: str, context: Optional[str] = None) -> str:
        """Implement a new feature using Z.AI's coding capabilities"""

        prompt = f"""Implement the following feature:
{feature_description}

Context:
{context if context else "No additional context provided."}

Please provide:
1. Analysis of the requirements
2. Implementation approach
3. Complete code solution
4. Any necessary explanations or comments"""

        chain = self.create_coding_chain("feature implementation")
        return chain.predict(input=prompt)

    def fix_bug(self, bug_description: str, code_snippet: Optional[str] = None, logs: Optional[str] = None) -> str:
        """Diagnose and fix a bug"""

        prompt = f"""Bug Description:
{bug_description}

{f'Code Snippet:\n{code_snippet}' if code_snippet else ''}

{f'Relevant Logs:\n{logs}' if logs else ''}

Please provide:
1. Bug analysis and root cause
2. Fix implementation
3. Explanation of the solution"""

        chain = self.create_coding_chain("bug fixing")
        return chain.predict(input=prompt)

    def analyze_code(self, code_path: str, analysis_type: str = "general") -> str:
        """Analyze code for various purposes"""

        if os.path.exists(code_path):
            with open(code_path, 'r', encoding='utf-8') as f:
                code_content = f.read()
        else:
            code_content = code_path  # Assume it's the code itself

        prompt = f"""Analyze the following code:
{code_content}

Analysis Type: {analysis_type}

Please provide comprehensive analysis based on the type requested."""

        chain = self.create_coding_chain(f"code analysis - {analysis_type}")
        return chain.predict(input=prompt)

    def interactive_chat(self) -> None:
        """Start an interactive coding session"""
        print("🚀 LangChain + Z.AI Coding Session Started")
        print("Type 'quit' or 'exit' to end the session")
        print("-" * 50)

        chain = self.create_coding_chain("interactive coding session")

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if user_input.lower() in ['quit', 'exit', 'q']:
                    print("👋 Ending session...")
                    break

                if not user_input:
                    continue

                response = chain.predict(input=user_input)
                print(f"\nZ.AI: {response}")

            except KeyboardInterrupt:
                print("\n👋 Session interrupted. Ending...")
                break
            except Exception as e:
                print(f"❌ Error: {str(e)}")

def main():
    """Example usage"""
    # Initialize the integration
    integration = LangChainZAIIntegration(
        model="GLM-4.6",
        project_instructions=".langcode/langcode.md"  # Optional project instructions
    )

    # Example 1: Implement a feature
    feature_result = integration.implement_feature(
        "Add a REST API endpoint for user authentication with JWT tokens",
        context="Current project uses FastAPI with SQLAlchemy"
    )
    print("Feature Implementation:")
    print(feature_result)

    # Example 2: Fix a bug
    bug_fix = integration.fix_bug(
        "Memory leak detected in the background task processor",
        code_snippet="# Background task code here...",
        logs="Memory usage keeps increasing over time"
    )
    print("\nBug Fix:")
    print(bug_fix)

    # Example 3: Analyze code
    analysis = integration.analyze_code(
        "path/to/your/code.py",
        analysis_type="performance and security"
    )
    print("\nCode Analysis:")
    print(analysis)

if __name__ == "__main__":
    main()