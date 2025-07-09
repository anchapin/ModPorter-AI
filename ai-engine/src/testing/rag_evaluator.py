import json
import os
from typing import List, Dict, Any

# Adjust the import path based on the project structure and how it's run.
# This assumes rag_evaluator.py might be run as a script from the project root,
# or that PYTHONPATH is set up appropriately.
try:
    from src.agents.knowledge_base_agent import KnowledgeBaseAgent
    from src.tools.search_tool import SearchTool
except ImportError:
    # Fallback for direct script execution from within `ai-engine/src/testing`
    import sys
    # Add 'ai-engine' to sys.path, assuming 'ai-engine' is the project root.
    # This is a common way to handle relative imports when running scripts directly.
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from src.agents.knowledge_base_agent import KnowledgeBaseAgent
    from src.tools.search_tool import SearchTool


class RagEvaluator:
    def __init__(self, eval_set_path: str):
        self.eval_set_path = eval_set_path
        self.evaluation_data = self._load_evaluation_set()
        self.knowledge_agent = KnowledgeBaseAgent()
        # Assuming KnowledgeBaseAgent provides SearchTool as its first tool.
        # This could be made more robust if KBA offered a named way to get tools.
        tools = self.knowledge_agent.get_tools()
        if not tools or not isinstance(tools[0], SearchTool):
            raise ValueError("KnowledgeBaseAgent did not provide a valid SearchTool.")
        self.search_tool = tools[0]
        self.retrieval_metrics = {"total_queries": 0, "hits": 0}

    def _load_evaluation_set(self) -> List[Dict[str, Any]]:
        try:
            with open(self.eval_set_path, 'r') as f:
                data = json.load(f)
            return data.get("evaluation_queries", [])
        except FileNotFoundError:
            print(f"Error: Evaluation set file not found at {self.eval_set_path}")
            return []
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {self.eval_set_path}")
            return []

    def evaluate_retrieval(self):
        """
        Evaluates the retrieval part of the RAG system.
        Uses SearchTool to retrieve documents and checks for expected snippets.
        """
        if not self.evaluation_data:
            print("No evaluation data loaded. Skipping evaluation.")
            return

        self.retrieval_metrics["total_queries"] = len(self.evaluation_data)

        for item in self.evaluation_data:
            query_id = item.get("id", "N/A")
            query = item.get("query")
            expected_snippet = item.get("expected_document_snippet")

            if not query or not expected_snippet:
                print(f"Warning: Skipping query ID {query_id} due to missing 'query' or 'expected_document_snippet'.")
                continue

            print(f"\nProcessing Query ID: {query_id} - '{query}'")

            # Use SearchTool to get results.
            # Currently, SearchTool returns hardcoded results.
            # In a real scenario, this would involve actual search logic.
            retrieved_docs_text = self.search_tool._run(query=query)

            print(f"  Retrieved: \"{retrieved_docs_text[:100]}...\"") # Print a snippet of retrieved text

            if expected_snippet in retrieved_docs_text:
                self.retrieval_metrics["hits"] += 1
                print(f"  SUCCESS: Expected snippet found for Query ID {query_id}.")
            else:
                print(f"  FAILURE: Expected snippet NOT found for Query ID {query_id}.")
                print(f"           Expected: '{expected_snippet}'")

    def report_metrics(self):
        """
        Prints a summary of the calculated metrics.
        """
        print("\n--- RAG Evaluation Summary ---")
        total_queries = self.retrieval_metrics["total_queries"]
        hits = self.retrieval_metrics["hits"]

        if total_queries > 0:
            hit_rate = (hits / total_queries) * 100
            print(f"Retrieval Hit Rate: {hit_rate:.2f}% ({hits}/{total_queries} queries hit)")
        else:
            print("Retrieval Hit Rate: N/A (No queries processed)")

        print("-----------------------------")
        # Placeholder for future response-based metrics
        # print("Response Keyword Match Score: ...")


def main():
    # Determine the path to the evaluation set relative to this script file.
    # __file__ is the path to the current script (rag_evaluator.py)
    # e.g., /path/to/ai-engine/src/testing/rag_evaluator.py
    # We want /path/to/ai-engine/src/testing/scenarios/rag_evaluation_set.json
    base_dir = os.path.dirname(__file__) # ai-engine/src/testing
    eval_set_file = os.path.join(base_dir, "scenarios", "rag_evaluation_set.json")

    print(f"Attempting to load evaluation set from: {eval_set_file}")

    evaluator = RagEvaluator(eval_set_path=eval_set_file)
    evaluator.evaluate_retrieval()
    evaluator.report_metrics()

if __name__ == "__main__":
    main()
