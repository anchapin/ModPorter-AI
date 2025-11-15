"""
Expert Knowledge Capture AI Agent

This agent specializes in capturing, validating, and encoding expert knowledge
about Java and Bedrock modding concepts for the knowledge graph system.
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from crewai.tools import BaseTool
from pydantic import BaseModel, Field

from tools.search_tool import SearchTool
from utils.llm_utils import LLMUtils
from .knowledge_base_agent import KnowledgeBaseAgent


class ExpertKnowledgeValidator(BaseModel):
    """Validator for expert knowledge."""
    
    technical_accuracy: float = Field(description="Technical accuracy score (0-1)")
    completeness: float = Field(description="Completeness of knowledge (0-1)")
    minecraft_compatibility: float = Field(description="Minecraft version compatibility (0-1)")
    innovation_value: float = Field(description="Innovation and uniqueness value (0-1)")
    documentation_quality: float = Field(description="Quality of documentation (0-1)")
    overall_score: float = Field(description="Overall quality score (0-1)")
    validation_comments: str = Field(description="Comments on validation")


class KnowledgeExtractorTool(BaseTool):
    """Tool for extracting structured knowledge from unstructured content."""
    
    name: str = "knowledge_extractor"
    description: str = "Extracts structured knowledge from text, code, or documentation about Minecraft modding"
    
    def _run(self, content: str, content_type: str) -> Dict[str, Any]:
        """
        Extract structured knowledge from content.
        
        Args:
            content: The raw content to process
            content_type: Type of content ('text', 'code', 'documentation', 'forum_post')
        
        Returns:
            Structured knowledge representation
        """
        try:
            llm = LLMUtils.get_llm()
            
            prompt = f"""
            You are an expert in Minecraft Java and Bedrock modding. 
            Extract structured knowledge from the following {content_type} content:
            
            CONTENT:
            {content}
            
            Extract and return a JSON object with:
            - concepts: List of Minecraft modding concepts mentioned
            - relationships: How concepts relate to each other
            - java_patterns: Specific Java modding patterns identified
            - bedrock_patterns: Corresponding Bedrock patterns
            - version_compatibility: Minecraft version constraints
            - expert_notes: Additional expert insights
            - confidence_levels: Confidence in each extracted piece of knowledge
            - code_examples: Relevant code examples (if present)
            - validation_rules: Rules to validate this knowledge
            
            Focus on conversion-relevant knowledge that helps map Java concepts to Bedrock equivalents.
            """
            
            response = llm.invoke(prompt)
            
            # Parse JSON response
            try:
                knowledge_data = json.loads(response.content)
                return {
                    "success": True,
                    "knowledge": knowledge_data,
                    "extraction_timestamp": datetime.utcnow().isoformat(),
                    "content_type": content_type,
                    "content_length": len(content)
                }
            except json.JSONDecodeError:
                # Fallback extraction
                return {
                    "success": False,
                    "error": "Failed to parse structured knowledge",
                    "raw_response": response.content
                }
                
        except Exception as e:
            logging.error(f"Error extracting knowledge: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class KnowledgeValidationTool(BaseTool):
    """Tool for validating expert knowledge."""
    
    name: str = "knowledge_validator"
    description: str = "Validates expert knowledge against known patterns and best practices"
    
    def _run(self, knowledge: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate extracted knowledge.
        
        Args:
            knowledge: Structured knowledge to validate
        
        Returns:
            Validation results with quality scores
        """
        try:
            llm = LLMUtils.get_llm()
            
            prompt = f"""
            You are a senior expert in Minecraft modding, specializing in Java to Bedrock conversions.
            Validate the following expert knowledge:
            
            KNOWLEDGE TO VALIDATE:
            {json.dumps(knowledge, indent=2)}
            
            Evaluate and return a JSON object with:
            - technical_accuracy: How technically accurate is this (0-1)
            - completeness: How complete and thorough is this knowledge (0-1)
            - minecraft_compatibility: How well does this work with Minecraft versions (0-1)
            - innovation_value: How innovative or unique is this knowledge (0-1)
            - documentation_quality: How well is this documented (0-1)
            - overall_score: Overall weighted quality score (0-1)
            - validation_comments: Detailed comments on validation
            - missing_information: What additional information would improve this
            - potential_issues: Any potential problems or edge cases
            - expert_recommended_actions: Actions to improve this knowledge
            
            Be thorough and critical in your evaluation.
            """
            
            response = llm.invoke(prompt)
            
            try:
                validation_data = json.loads(response.content)
                return {
                    "success": True,
                    "validation": validation_data,
                    "validation_timestamp": datetime.utcnow().isoformat(),
                    "knowledge_id": knowledge.get("id", "unknown")
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Failed to parse validation response",
                    "raw_response": response.content
                }
                
        except Exception as e:
            logging.error(f"Error validating knowledge: {e}")
            return {
                "success": False,
                "error": str(e)
            }


class KnowledgeGraphTool(BaseTool):
    """Tool for integrating knowledge into the graph database."""
    
    name: str = "knowledge_graph_integrator"
    description: str = "Integrates validated knowledge into the knowledge graph database"
    
    def _run(self, validated_knowledge: Dict[str, Any], contribution_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Integrate validated knowledge into the graph database.
        
        Args:
            validated_knowledge: Knowledge that has passed validation
            contribution_data: Metadata about the contribution
        
        Returns:
            Integration results with node/relationship IDs
        """
        try:
            # This would integrate with the actual knowledge graph database
            # For now, simulate the integration
            
            knowledge = validated_knowledge.get("knowledge", {})
            validation = validated_knowledge.get("validation", {})
            
            # Create knowledge nodes
            nodes_created = []
            relationships_created = []
            patterns_created = []
            
            # Process concepts
            concepts = knowledge.get("concepts", [])
            for concept in concepts:
                node_data = {
                    "node_type": "java_concept" if "java" in concept.lower() else "bedrock_concept",
                    "name": concept,
                    "description": f"Expert-validated concept: {concept}",
                    "properties": {
                        "expert_validated": True,
                        "validation_score": validation.get("overall_score", 0.5),
                        "minecraft_version": knowledge.get("version_compatibility", "latest"),
                        "expert_notes": knowledge.get("expert_notes", ""),
                        "validation_comments": validation.get("validation_comments", ""),
                        "extracted_at": validated_knowledge.get("validation_timestamp"),
                        "confidence_level": knowledge.get("confidence_levels", {}).get(concept, 0.5)
                    },
                    "platform": "both",  # Determine based on content
                    "expert_validated": True,
                    "community_rating": validation.get("overall_score", 0.5) * 10,
                    "created_by": contribution_data.get("contributor_id", "expert_agent"),
                    "neo4j_id": None  # Will be assigned by graph DB
                }
                nodes_created.append(node_data)
            
            # Process relationships
            relationships = knowledge.get("relationships", [])
            for rel in relationships:
                rel_data = {
                    "relationship_type": rel.get("type", "converts_to"),
                    "properties": {
                        "expert_validated": True,
                        "confidence_score": validation.get("overall_score", 0.5),
                        "validation_notes": validation.get("validation_comments", ""),
                        "validation_rules": knowledge.get("validation_rules", [])
                    },
                    "minecraft_version": knowledge.get("version_compatibility", "latest"),
                    "expert_validated": True,
                    "community_votes": 0,
                    "created_by": contribution_data.get("contributor_id", "expert_agent")
                }
                relationships_created.append(rel_data)
            
            # Process conversion patterns
            java_patterns = knowledge.get("java_patterns", [])
            bedrock_patterns = knowledge.get("bedrock_patterns", [])
            
            for i, (java_pattern, bedrock_pattern) in enumerate(zip(java_patterns, bedrock_patterns)):
                pattern_data = {
                    "name": f"Expert Pattern {i+1}: {java_pattern.get('name', 'Unnamed')}",
                    "description": f"Expert-validated conversion pattern from {java_pattern.get('name', 'Unknown')} to Bedrock equivalent",
                    "java_pattern": java_pattern,
                    "bedrock_pattern": bedrock_pattern,
                    "graph_representation": {
                        "source_type": "java_concept",
                        "target_type": "bedrock_concept",
                        "relationship": "converts_to"
                    },
                    "validation_status": "validated",
                    "community_rating": validation.get("overall_score", 0.5) * 10,
                    "expert_reviewed": True,
                    "success_rate": 0.0,  # Will be updated as it's used
                    "usage_count": 0,
                    "minecraft_versions": [knowledge.get("version_compatibility", "latest")],
                    "tags": knowledge.get("concepts", []),
                    "created_by": contribution_data.get("contributor_id", "expert_agent")
                }
                patterns_created.append(pattern_data)
            
            # Store contribution data
            contribution_id = self._store_contribution(validated_knowledge, contribution_data, nodes_created, relationships_created, patterns_created)
            
            return {
                "success": True,
                "contribution_id": contribution_id,
                "nodes_created": len(nodes_created),
                "relationships_created": len(relationships_created),
                "patterns_created": len(patterns_created),
                "integration_timestamp": datetime.utcnow().isoformat(),
                "validation_score": validation.get("overall_score", 0.5)
            }
            
        except Exception as e:
            logging.error(f"Error integrating knowledge into graph: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _store_contribution(self, validated_knowledge: Dict, contribution_data: Dict, 
                           nodes: List, relationships: List, patterns: List) -> str:
        """
        Store contribution and related data.
        In a real implementation, this would interact with the API.
        For now, generate a mock contribution ID.
        """
        import uuid
        contribution_id = str(uuid.uuid4())
        
        # Log what would be stored
        logging.info(f"Storing contribution {contribution_id}:")
        logging.info(f"  - Nodes: {len(nodes)}")
        logging.info(f"  - Relationships: {len(relationships)}")
        logging.info(f"  - Patterns: {len(patterns)}")
        
        return contribution_id


class ExpertKnowledgeAgent:
    """
    An AI agent specialized in capturing, validating, and encoding expert knowledge
    about Minecraft modding for the knowledge graph system.
    """
    
    def __init__(self):
        self.llm = LLMUtils.get_llm()
        self.search_tool = SearchTool()
        self.knowledge_extractor = KnowledgeExtractorTool()
        self.knowledge_validator = KnowledgeValidationTool()
        self.knowledge_graph = KnowledgeGraphTool()
        
    def get_tools(self) -> List[BaseTool]:
        """Returns list of available tools for this agent."""
        return [
            self.search_tool,
            self.knowledge_extractor,
            self.knowledge_validator,
            self.knowledge_graph
        ]
    
    async def capture_expert_knowledge(self, content: str, content_type: str, 
                                     contributor_id: str, title: str, description: str) -> Dict[str, Any]:
        """
        Main workflow to capture expert knowledge from content.
        
        Args:
            content: Raw content to process
            content_type: Type of content
            contributor_id: ID of the contributor
            title: Title for the contribution
            description: Description of the contribution
        
        Returns:
            Results of the knowledge capture process
        """
        try:
            # Step 1: Extract structured knowledge
            logging.info("Extracting structured knowledge from content...")
            extraction_result = self.knowledge_extractor._run(content, content_type)
            
            if not extraction_result.get("success"):
                return {
                    "success": False,
                    "error": "Knowledge extraction failed",
                    "details": extraction_result.get("error")
                }
            
            knowledge = extraction_result.get("knowledge", {})
            
            # Step 2: Validate extracted knowledge
            logging.info("Validating extracted knowledge...")
            validation_result = self.knowledge_validator._run(knowledge)
            
            if not validation_result.get("success"):
                return {
                    "success": False,
                    "error": "Knowledge validation failed",
                    "details": validation_result.get("error")
                }
            
            validation = validation_result.get("validation", {})
            
            # Step 3: Check if validation meets minimum quality threshold
            min_score = 0.6  # Minimum 60% quality score for expert knowledge
            overall_score = validation.get("overall_score", 0.0)
            
            if overall_score < min_score:
                return {
                    "success": False,
                    "error": "Knowledge quality below minimum threshold",
                    "score": overall_score,
                    "min_required": min_score,
                    "validation_comments": validation.get("validation_comments", "")
                }
            
            # Step 4: Prepare contribution data
            contribution_data = {
                "contributor_id": contributor_id,
                "contribution_type": "expert_capture",
                "title": title,
                "description": description,
                "minecraft_version": knowledge.get("version_compatibility", "latest"),
                "tags": knowledge.get("concepts", []),
                "extracted_metadata": extraction_result
            }
            
            # Step 5: Integrate into knowledge graph
            logging.info("Integrating validated knowledge into graph...")
            integration_result = self.knowledge_graph._run(validation_result, contribution_data)
            
            if integration_result.get("success"):
                return {
                    "success": True,
                    "message": "Expert knowledge captured and integrated successfully",
                    "contribution_id": integration_result.get("contribution_id"),
                    "quality_score": overall_score,
                    "nodes_created": integration_result.get("nodes_created"),
                    "relationships_created": integration_result.get("relationships_created"),
                    "patterns_created": integration_result.get("patterns_created"),
                    "validation_comments": validation.get("validation_comments")
                }
            else:
                return {
                    "success": False,
                    "error": "Knowledge graph integration failed",
                    "details": integration_result.get("error")
                }
                
        except Exception as e:
            logging.error(f"Error in expert knowledge capture workflow: {e}")
            return {
                "success": False,
                "error": "Workflow error",
                "details": str(e)
            }
    
    async def batch_capture_from_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Capture knowledge from multiple sources in batch.
        
        Args:
            sources: List of source objects with content, type, metadata
        
        Returns:
            List of capture results
        """
        results = []
        
        for source in sources:
            try:
                result = await self.capture_expert_knowledge(
                    content=source.get("content", ""),
                    content_type=source.get("type", "text"),
                    contributor_id=source.get("contributor_id", "batch_expert"),
                    title=source.get("title", "Batch Captured Knowledge"),
                    description=source.get("description", "Knowledge captured in batch processing")
                )
                results.append(result)
            except Exception as e:
                logging.error(f"Error processing source {source}: {e}")
                results.append({
                    "success": False,
                    "error": "Source processing error",
                    "source": source.get("id", "unknown"),
                    "details": str(e)
                })
        
        return results
    
    def generate_knowledge_summary(self, domain: str, limit: int = 100) -> Dict[str, Any]:
        """
        Generate a summary of expert knowledge in a specific domain.
        
        Args:
            domain: Domain to summarize (e.g., 'entities', 'block_conversions', 'logic')
            limit: Maximum number of knowledge items to summarize
        
        Returns:
            Summary of domain knowledge
        """
        try:
            # Use search tool to find knowledge in domain
            search_results = self.search_tool._run(
                query=f"expert validated {domain} minecraft modding",
                limit=limit
            )
            
            # Generate summary using LLM
            prompt = f"""
            Summarize the expert knowledge in the {domain} domain based on these search results:
            
            {json.dumps(search_results, indent=2)}
            
            Provide a comprehensive summary including:
            - Key concepts and their relationships
            - Common patterns and best practices
            - Version compatibility considerations
            - Expert insights and recommendations
            - Knowledge gaps or areas needing more research
            
            Focus on information most valuable for Java to Bedrock modding conversions.
            """
            
            response = self.llm.invoke(prompt)
            
            return {
                "domain": domain,
                "summary": response.content,
                "knowledge_count": len(search_results.get("results", [])),
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logging.error(f"Error generating knowledge summary: {e}")
            return {
                "success": False,
                "error": str(e),
                "domain": domain
            }


# Example usage for testing
if __name__ == "__main__":
    import asyncio
    
    async def test_agent():
        agent = ExpertKnowledgeAgent()
        
        # Test knowledge capture
        test_content = """
        In Minecraft Java Edition, custom entities can be created using the Entity system.
        For Bedrock Edition, the equivalent is using behavior packs with entity JSON files.
        
        Key differences:
        1. Java uses code-based entity registration
        2. Bedrock uses JSON-defined entity behaviors
        3. Animation systems differ significantly
        
        For converting entity AI behavior:
        - Java's pathfinding becomes Bedrock's minecraft:behavior.pathfind
        - Java's custom goals become Bedrock's minecraft:behavior.go_to_entity
        - Need to translate Java's tick-based updates to Bedrock's event-driven system
        """
        
        result = await agent.capture_expert_knowledge(
            content=test_content,
            content_type="text",
            contributor_id="test_expert",
            title="Entity Conversion Knowledge",
            description="Expert knowledge about converting entities from Java to Bedrock"
        )
        
        print("Knowledge capture result:")
        print(json.dumps(result, indent=2))
    
    asyncio.run(test_agent())
