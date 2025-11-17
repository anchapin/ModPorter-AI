"""
Graph Database Abstraction Layer for Knowledge Graph

This module provides a high-level interface for interacting with Neo4j
for the knowledge graph and community curation system.
"""

import os
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
from neo4j import GraphDatabase, Driver, Session
from neo4j.exceptions import ServiceUnavailable, AuthError
import json

logger = logging.getLogger(__name__)

class GraphDatabaseManager:
    """Neo4j graph database manager for knowledge graph operations."""
    
    def __init__(self):
        """Initialize the Neo4j driver."""
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver: Optional[Driver] = None
        
    def connect(self) -> bool:
        """
        Establish connection to Neo4j database.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info("Successfully connected to Neo4j database")
            return True
        except (ServiceUnavailable, AuthError, Exception) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False
    
    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")
    
    def get_session(self) -> Optional[Session]:
        """
        Get a Neo4j session.
        
        Returns:
            Optional[Session]: Neo4j session or None if not connected
        """
        if not self.driver:
            if not self.connect():
                return None
        return self.driver.session()
    
    def create_node(self, 
                   node_type: str, 
                   name: str, 
                   properties: Dict[str, Any] = None,
                   minecraft_version: str = "latest",
                   platform: str = "both",
                   created_by: Optional[str] = None) -> Optional[str]:
        """
        Create a knowledge node in the graph.
        
        Args:
            node_type: Type of node (java_concept, bedrock_concept, etc.)
            name: Name of the node
            properties: Additional properties for the node
            minecraft_version: Minecraft version
            platform: Platform (java, bedrock, both)
            created_by: Creator identifier
            
        Returns:
            Optional[str]: Node ID if successful, None otherwise
        """
        if properties is None:
            properties = {}
            
        query = """
        CREATE (n:KnowledgeNode {
            node_type: $node_type,
            name: $name,
            properties: $properties,
            minecraft_version: $minecraft_version,
            platform: $platform,
            created_by: $created_by,
            expert_validated: false,
            community_rating: 0.0,
            created_at: datetime(),
            updated_at: datetime()
        })
        RETURN elementId(n) as node_id
        """
        
        try:
            with self.get_session() as session:
                result = session.run(query, {
                    "node_type": node_type,
                    "name": name,
                    "properties": json.dumps(properties),
                    "minecraft_version": minecraft_version,
                    "platform": platform,
                    "created_by": created_by
                })
                record = result.single()
                return record["node_id"] if record else None
        except Exception as e:
            logger.error(f"Error creating node: {e}")
            return None
    
    def create_relationship(self,
                          source_node_id: str,
                          target_node_id: str,
                          relationship_type: str,
                          properties: Dict[str, Any] = None,
                          confidence_score: float = 0.5,
                          minecraft_version: str = "latest",
                          created_by: Optional[str] = None) -> Optional[str]:
        """
        Create a relationship between two nodes.
        
        Args:
            source_node_id: ID of source node
            target_node_id: ID of target node
            relationship_type: Type of relationship
            properties: Additional properties
            confidence_score: Confidence score (0-1)
            minecraft_version: Minecraft version
            created_by: Creator identifier
            
        Returns:
            Optional[str]: Relationship ID if successful, None otherwise
        """
        if properties is None:
            properties = {}
            
        query = """
        MATCH (a:KnowledgeNode), (b:KnowledgeNode)
        WHERE elementId(a) = $source_id AND elementId(b) = $target_id
        CREATE (a)-[r:RELATIONSHIP {
            relationship_type: $relationship_type,
            properties: $properties,
            confidence_score: $confidence_score,
            minecraft_version: $minecraft_version,
            created_by: $created_by,
            expert_validated: false,
            community_votes: 0,
            created_at: datetime(),
            updated_at: datetime()
        }]->(b)
        RETURN elementId(r) as rel_id
        """
        
        try:
            with self.get_session() as session:
                result = session.run(query, {
                    "source_id": source_node_id,
                    "target_id": target_node_id,
                    "relationship_type": relationship_type,
                    "properties": json.dumps(properties),
                    "confidence_score": confidence_score,
                    "minecraft_version": minecraft_version,
                    "created_by": created_by
                })
                record = result.single()
                return record["rel_id"] if record else None
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return None
    
    def find_nodes_by_type(self, node_type: str, minecraft_version: str = "latest") -> List[Dict[str, Any]]:
        """
        Find nodes by type.
        
        Args:
            node_type: Type of nodes to find
            minecraft_version: Filter by Minecraft version
            
        Returns:
            List[Dict[str, Any]]: List of nodes
        """
        query = """
        MATCH (n:KnowledgeNode {node_type: $node_type})
        WHERE n.minecraft_version = $minecraft_version OR n.minecraft_version = 'latest'
        RETURN elementId(n) as id, n.name as name, n.properties as properties,
               n.platform as platform, n.expert_validated as expert_validated,
               n.community_rating as community_rating
        ORDER BY n.community_rating DESC, n.name
        """
        
        try:
            with self.get_session() as session:
                result = session.run(query, {
                    "node_type": node_type,
                    "minecraft_version": minecraft_version
                })
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Error finding nodes: {e}")
            return []
    
    def find_conversion_paths(self, 
                           java_node_id: str, 
                           max_depth: int = 3,
                           minecraft_version: str = "latest") -> List[Dict[str, Any]]:
        """
        Find conversion paths from Java to Bedrock concepts.
        
        Args:
            java_node_id: Starting Java node ID
            max_depth: Maximum path depth
            minecraft_version: Filter by Minecraft version
            
        Returns:
            List[Dict[str, Any]]: List of conversion paths
        """
        query = """
        MATCH path = (start:KnowledgeNode)-[*1..%d]->(end:KnowledgeNode)
        WHERE elementId(start) = $start_id
          AND (start.platform = 'java' OR start.platform = 'both')
          AND (end.platform = 'bedrock' OR end.platform = 'both')
          AND all(r IN relationships(path) WHERE 
                  r.minecraft_version = $version OR r.minecraft_version = 'latest')
          AND all(n IN nodes(path) WHERE 
                  n.minecraft_version = $version OR n.minecraft_version = 'latest')
        WITH path, reduce(score = 1.0, rel IN relationships(path) | score * rel.confidence_score) as confidence
        RETURN path, confidence
        ORDER BY confidence DESC
        LIMIT 20
        """ % max_depth
        
        try:
            with self.get_session() as session:
                result = session.run(query, {
                    "start_id": java_node_id,
                    "version": minecraft_version
                })
                paths = []
                for record in result:
                    path_data = {
                        "path": [dict(node) for node in record["path"].nodes],
                        "relationships": [dict(rel) for rel in record["path"].relationships],
                        "confidence": float(record["confidence"])
                    }
                    paths.append(path_data)
                return paths
        except Exception as e:
            logger.error(f"Error finding conversion paths: {e}")
            return []
    
    def search_nodes(self, query_text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search nodes by name or properties.
        
        Args:
            query_text: Search query
            limit: Maximum number of results
            
        Returns:
            List[Dict[str, Any]]: Search results
        """
        query = """
        MATCH (n:KnowledgeNode)
        WHERE toLower(n.name) CONTAINS toLower($query)
           OR any(prop IN keys(n.properties) WHERE toLower(toString(n.properties[prop])) CONTAINS toLower($query))
        RETURN elementId(n) as id, n.name as name, n.node_type as node_type,
               n.platform as platform, n.expert_validated as expert_validated,
               n.community_rating as community_rating, n.properties as properties
        ORDER BY n.community_rating DESC, n.name
        LIMIT $limit
        """
        
        try:
            with self.get_session() as session:
                result = session.run(query, {
                    "query": query_text,
                    "limit": limit
                })
                return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Error searching nodes: {e}")
            return []
    
    def get_node_relationships(self, node_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all relationships for a node.
        
        Args:
            node_id: Node ID
            
        Returns:
            Dict[str, List[Dict[str, Any]]]: Incoming and outgoing relationships
        """
        incoming_query = """
        MATCH (a:KnowledgeNode)-[r:RELATIONSHIP]->(b:KnowledgeNode)
        WHERE elementId(b) = $node_id
        RETURN elementId(a) as source_id, a.name as source_name, 
               elementId(r) as rel_id, r.relationship_type as relationship_type,
               r.confidence_score as confidence_score, r.properties as properties
        """
        
        outgoing_query = """
        MATCH (a:KnowledgeNode)-[r:RELATIONSHIP]->(b:KnowledgeNode)
        WHERE elementId(a) = $node_id
        RETURN elementId(b) as target_id, b.name as target_name,
               elementId(r) as rel_id, r.relationship_type as relationship_type,
               r.confidence_score as confidence_score, r.properties as properties
        """
        
        try:
            with self.get_session() as session:
                incoming_result = session.run(incoming_query, {"node_id": node_id})
                outgoing_result = session.run(outgoing_query, {"node_id": node_id})
                
                return {
                    "incoming": [dict(record) for record in incoming_result],
                    "outgoing": [dict(record) for record in outgoing_result]
                }
        except Exception as e:
            logger.error(f"Error getting node relationships: {e}")
            return {"incoming": [], "outgoing": []}
    
    def update_node_validation(self, node_id: str, expert_validated: bool, 
                             community_rating: Optional[float] = None) -> bool:
        """
        Update node validation status and rating.
        
        Args:
            node_id: Node ID
            expert_validated: Expert validation status
            community_rating: Community rating (optional)
            
        Returns:
            bool: True if successful, False otherwise
        """
        query = """
        MATCH (n:KnowledgeNode)
        WHERE elementId(n) = $node_id
        SET n.expert_validated = $expert_validated,
            n.community_rating = coalesce($community_rating, n.community_rating),
            n.updated_at = datetime()
        RETURN n
        """
        
        try:
            with self.get_session() as session:
                result = session.run(query, {
                    "node_id": node_id,
                    "expert_validated": expert_validated,
                    "community_rating": community_rating
                })
                return result.single() is not None
        except Exception as e:
            logger.error(f"Error updating node validation: {e}")
            return False
    
    def delete_node(self, node_id: str) -> bool:
        """
        Delete a node and all its relationships.
        
        Args:
            node_id: Node ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        query = """
        MATCH (n:KnowledgeNode)
        WHERE elementId(n) = $node_id
        DETACH DELETE n
        RETURN count(n) as deleted_count
        """
        
        try:
            with self.get_session() as session:
                result = session.run(query, {"node_id": node_id})
                record = result.single()
                return record and record["deleted_count"] > 0
        except Exception as e:
            logger.error(f"Error deleting node: {e}")
            return False


# Global instance for application-wide access
graph_db = GraphDatabaseManager()
