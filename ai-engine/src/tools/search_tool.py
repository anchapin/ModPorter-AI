from crewai.tools import BaseTool
import json # Import json for structured output

class SearchTool(BaseTool):
    name: str = "Vector DB Search Tool"
    description: str = (
        "A tool to perform similarity searches in a vector database. "
        "Input should be a user query string. "
        "Output is a JSON string containing a list of search results."
    )

    def _run(self, query: str) -> str:
        """
        Performs a similarity search in the vector database based on the query.
        Currently returns mock data.
        """
        # TODO(autogpt): Connect to the vector database as described in RAG.md.
        # This would involve:
        # 1. Getting an API client or connection to the backend service.
        # 2. Sending the query to the backend's search endpoint.
        # 3. Receiving results from the backend.

        print(f"SearchTool received query: {query}") # For debugging

        # Placeholder for mock search results
        # In a real scenario, these would come from the vector DB via a backend API
        if "AI advancements" in query:
            search_results = [
                {"id": "doc1", "score": 0.92, "text": "Recent breakthroughs in large language models have enabled more natural and context-aware conversations.", "source": "ai_research_journal_vol2.pdf"},
                {"id": "doc2", "score": 0.88, "text": "Generative Adversarial Networks (GANs) are being used to create hyper-realistic images and videos.", "source": "tech_conference_proceedings_2023.docx"},
                {"id": "doc3", "score": 0.85, "text": "Ethical considerations in AI development, including bias and fairness, are becoming increasingly important.", "source": "ethics_in_ai_whitepaper.pdf"}
            ]
        elif "Minecraft modding" in query:
            search_results = [
                {"id": "mc_doc1", "score": 0.95, "text": "Minecraft Forge is a popular modding API for the Java Edition, allowing extensive modifications.", "source": "forge_wiki.html"},
                {"id": "mc_doc2", "score": 0.90, "text": "Bedrock Edition uses Add-Ons, which are behavior packs and resource packs, often written in JSON and JavaScript.", "source": "bedrock.dev/docs"},
                {"id": "mc_doc3", "score": 0.87, "text": "The RAG.md document in this repository outlines a plan for using AI to assist with porting Minecraft mods.", "source": "RAG.md"}
            ]
        else:
            search_results = [
                {"id": "gen_doc1", "score": 0.80, "text": "No specific documents found for this query. This is a generic mock response.", "source": "mock_source.txt"}
            ]

        # Format the results as a JSON string, as this is often easier for LLMs to parse
        return json.dumps(search_results)

if __name__ == "__main__":
    search_tool = SearchTool()

    sample_query_ai = "What are the latest advancements in AI?"
    output_ai = search_tool._run(sample_query_ai)
    print(f"Query: {sample_query_ai}")
    print(f"Output:\n{output_ai}\n")

    sample_query_mc = "Tell me about Minecraft modding."
    output_mc = search_tool._run(sample_query_mc)
    print(f"Query: {sample_query_mc}")
    print(f"Output:\n{output_mc}\n")

    sample_query_other = "Some other topic."
    output_other = search_tool._run(sample_query_other)
    print(f"Query: {sample_query_other}")
    print(f"Output:\n{output_other}\n")
