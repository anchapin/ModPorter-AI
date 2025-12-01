"""
Optimized Graph Database Abstraction Layer for Knowledge Graph

This module provides a high-performance interface for interacting with Neo4j
for the knowledge graph and community curation system with optimizations for
concurrent access, connection pooling, and query efficiency.
"""

import os
from typing import Dict, List, Optional, Any
import logging
import json
import time
from contextlib import contextmanager
from threading import Lock
from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable, AuthError

logger = logging.getLogger(__name__)


class OptimizedGraphDatabaseManager:
    """Optimized Neo4j graph database manager with performance enhancements."""

    def __init__(self):
        """Initialize the Neo4j driver with optimized settings."""
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "password")
        self.driver: Optional[Driver] = None

        # Performance optimization settings
        self.max_connection_lifetime = 3600  # 1 hour
        self.max_connection_pool_size = 50  # Connection pool size
        self.connection_acquisition_timeout = 60  # seconds

        # Query cache for frequently accessed data
        self._query_cache = {}
        self._cache_lock = Lock()
        self._cache_ttl = 300  # 5 minutes TTL for cache
        self._cache_timestamps = {}

        # Batch operation buffer
        self._batch_buffer = {"nodes": [], "relationships": []}
        self._batch_lock = Lock()
        self._batch_threshold = 100  # Auto-flush at 100 operations

    def connect(self) -> bool:
        """
        Establish optimized connection to Neo4j database.

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password),
                max_connection_lifetime=self.max_connection_lifetime,
                max_connection_pool_size=self.max_connection_pool_size,
                connection_acquisition_timeout=self.connection_acquisition_timeout,
            )

            # Test connection with optimized query
            with self.driver.session(database="neo4j") as session:
                session.run("RETURN 1").single()

            # Create performance indexes if they don't exist
            self._ensure_indexes()

            logger.info("Successfully connected to Neo4j with optimized settings")
            return True

        except (ServiceUnavailable, AuthError, Exception) as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            return False

    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def _ensure_indexes(self):
        """Create performance indexes for common queries."""
        index_queries = [
            "CREATE INDEX node_type_index IF NOT EXISTS FOR (n:KnowledgeNode) ON (n.node_type)",
            "CREATE INDEX node_name_index IF NOT EXISTS FOR (n:KnowledgeNode) ON (n.name)",
            "CREATE INDEX node_version_index IF NOT EXISTS FOR (n:KnowledgeNode) ON (n.minecraft_version)",
            "CREATE INDEX node_platform_index IF NOT EXISTS FOR (n:KnowledgeNode) ON (n.platform)",
            "CREATE INDEX rel_type_index IF NOT EXISTS FOR ()-[r:RELATIONSHIP]-() ON (r.relationship_type)",
            "CREATE INDEX rel_confidence_index IF NOT EXISTS FOR ()-[r:RELATIONSHIP]-() ON (r.confidence_score)",
            "CREATE INDEX rel_version_index IF NOT EXISTS FOR ()-[r:RELATIONSHIP]-() ON (r.minecraft_version)",
        ]

        try:
            with self.driver.session(database="neo4j") as session:
                for query in index_queries:
                    session.run(query)
            logger.info("Performance indexes ensured")
        except Exception as e:
            logger.warning(f"Could not create indexes: {e}")

    @contextmanager
    def get_session(self, database="neo4j"):
        """
        Get a Neo4j session with optimized configuration.

        Yields:
            Session: Neo4j session
        """
        if not self.driver:
            if not self.connect():
                raise ConnectionError("Could not connect to Neo4j")

        session = self.driver.session(
            database=database,
            default_access_mode=READ_ACCESS if database == "neo4j" else WRITE_ACCESS,
        )

        try:
            yield session
        finally:
            session.close()

    def _get_cache_key(self, query: str, params: Dict[str, Any]) -> str:
        """Generate a cache key for a query."""
        return f"{query}:{hash(frozenset(params.items()))}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached result is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        return time.time() - self._cache_timestamps[cache_key] < self._cache_ttl

    def create_node(
        self,
        node_type: str,
        name: str,
        properties: Dict[str, Any] = None,
        minecraft_version: str = "latest",
        platform: str = "both",
        created_by: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a knowledge node with optimized query.

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

        # Optimized query with parameterized labels
        query = f"""
        CREATE (n:KnowledgeNode:{node_type.replace(":", "_")} {{
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
        }})
        RETURN elementId(n) as node_id
        """

        try:
            with self.get_session() as session:
                result = session.run(
                    query,
                    {
                        "node_type": node_type,
                        "name": name,
                        "properties": json.dumps(properties),
                        "minecraft_version": minecraft_version,
                        "platform": platform,
                        "created_by": created_by,
                    },
                )
                record = result.single()
                return record["node_id"] if record else None
        except Exception as e:
            logger.error(f"Error creating node: {e}")
            return None

    def create_node_batch(self, nodes: List[Dict[str, Any]]) -> List[Optional[str]]:
        """
        Create multiple nodes in a single transaction for better performance.

        Args:
            nodes: List of node data dictionaries

        Returns:
            List[Optional[str]]: List of node IDs
        """
        if not nodes:
            return []

        # Build UNWIND query for batch creation
        query = """
        UNWIND $nodes AS nodeData
        CREATE (n:KnowledgeNode {
            node_type: nodeData.node_type,
            name: nodeData.name,
            properties: nodeData.properties,
            minecraft_version: nodeData.minecraft_version,
            platform: nodeData.platform,
            created_by: nodeData.created_by,
            expert_validated: false,
            community_rating: 0.0,
            created_at: datetime(),
            updated_at: datetime()
        })
        RETURN elementId(n) as node_id
        """

        # Prepare node data with proper JSON serialization
        prepared_nodes = []
        for node in nodes:
            prepared_node = node.copy()
            if "properties" in prepared_node and isinstance(
                prepared_node["properties"], dict
            ):
                prepared_node["properties"] = json.dumps(prepared_node["properties"])
            prepared_nodes.append(prepared_node)

        try:
            with self.get_session() as session:
                result = session.run(query, {"nodes": prepared_nodes})
                return [record["node_id"] for record in result]
        except Exception as e:
            logger.error(f"Error creating nodes in batch: {e}")
            return [None] * len(nodes)

    def create_relationship(
        self,
        source_node_id: str,
        target_node_id: str,
        relationship_type: str,
        properties: Dict[str, Any] = None,
        confidence_score: float = 0.5,
        minecraft_version: str = "latest",
        created_by: Optional[str] = None,
    ) -> Optional[str]:
        """
        Create a relationship with optimized query.

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

        # Optimized query with index hints
        query = """
        MATCH (a:KnowledgeNode), (b:KnowledgeNode)
        USING INDEX a:KnowledgeNode(node_type)
        USING INDEX b:KnowledgeNode(node_type)
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
                result = session.run(
                    query,
                    {
                        "source_id": source_node_id,
                        "target_id": target_node_id,
                        "relationship_type": relationship_type,
                        "properties": json.dumps(properties),
                        "confidence_score": confidence_score,
                        "minecraft_version": minecraft_version,
                        "created_by": created_by,
                    },
                )
                record = result.single()
                return record["rel_id"] if record else None
        except Exception as e:
            logger.error(f"Error creating relationship: {e}")
            return None

    def create_relationship_batch(
        self, relationships: List[Dict[str, Any]]
    ) -> List[Optional[str]]:
        """
        Create multiple relationships in a single transaction.

        Args:
            relationships: List of relationship data dictionaries

        Returns:
            List[Optional[str]]: List of relationship IDs
        """
        if not relationships:
            return []

        query = """
        UNWIND $relationships AS relData
        MATCH (a:KnowledgeNode), (b:KnowledgeNode)
        WHERE elementId(a) = relData.source_id AND elementId(b) = relData.target_id
        CREATE (a)-[r:RELATIONSHIP {
            relationship_type: relData.relationship_type,
            properties: relData.properties,
            confidence_score: relData.confidence_score,
            minecraft_version: relData.minecraft_version,
            created_by: relData.created_by,
            expert_validated: false,
            community_votes: 0,
            created_at: datetime(),
            updated_at: datetime()
        }]->(b)
        RETURN elementId(r) as rel_id
        """

        # Prepare relationship data
        prepared_relationships = []
        for rel in relationships:
            prepared_rel = rel.copy()
            if "properties" in prepared_rel and isinstance(
                prepared_rel["properties"], dict
            ):
                prepared_rel["properties"] = json.dumps(prepared_rel["properties"])
            prepared_relationships.append(prepared_rel)

        try:
            with self.get_session() as session:
                result = session.run(query, {"relationships": prepared_relationships})
                return [record["rel_id"] for record in result]
        except Exception as e:
            logger.error(f"Error creating relationships in batch: {e}")
            return [None] * len(relationships)

    def find_nodes_by_type(
        self, node_type: str, minecraft_version: str = "latest"
    ) -> List[Dict[str, Any]]:
        """
        Find nodes by type with caching and optimized query.

        Args:
            node_type: Type of nodes to find
            minecraft_version: Filter by Minecraft version

        Returns:
            List[Dict[str, Any]]: List of nodes
        """
        cache_key = self._get_cache_key(
            "find_nodes_by_type",
            {"node_type": node_type, "minecraft_version": minecraft_version},
        )

        # Check cache first
        with self._cache_lock:
            if cache_key in self._query_cache and self._is_cache_valid(cache_key):
                return self._query_cache[cache_key]

        # Optimized query with index hints
        query = """
        MATCH (n:KnowledgeNode)
        USING INDEX n:KnowledgeNode(node_type)
        WHERE n.node_type = $node_type
          AND (n.minecraft_version = $minecraft_version OR n.minecraft_version = 'latest')
        RETURN elementId(n) as id, n.name as name, n.properties as properties,
               n.platform as platform, n.expert_validated as expert_validated,
               n.community_rating as community_rating
        ORDER BY n.community_rating DESC, n.name
        """

        try:
            with self.get_session() as session:
                result = session.run(
                    query,
                    {"node_type": node_type, "minecraft_version": minecraft_version},
                )
                nodes = [dict(record) for record in result]

                # Cache the result
                with self._cache_lock:
                    self._query_cache[cache_key] = nodes
                    self._cache_timestamps[cache_key] = time.time()

                return nodes
        except Exception as e:
            logger.error(f"Error finding nodes: {e}")
            return []

    def search_nodes(self, query_text: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Search nodes with optimized full-text search.

        Args:
            query_text: Search query
            limit: Maximum number of results

        Returns:
            List[Dict[str, Any]]: Search results
        """
        cache_key = self._get_cache_key(
            "search_nodes", {"query_text": query_text, "limit": limit}
        )

        # Check cache first
        with self._cache_lock:
            if cache_key in self._query_cache and self._is_cache_valid(cache_key):
                return self._query_cache[cache_key]

        # Optimized search query with proper indexing
        query = """
        MATCH (n:KnowledgeNode)
        USING INDEX n:KnowledgeNode(name)
        WHERE toLower(n.name) CONTAINS toLower($query)
        OPTIONAL MATCH (n)-[r:RELATIONSHIP]-()
        WITH n, count(r) as relationship_count
        RETURN elementId(n) as id, n.name as name, n.node_type as node_type,
               n.platform as platform, n.expert_validated as expert_validated,
               n.community_rating as community_rating, n.properties as properties,
               relationship_count
        ORDER BY n.community_rating DESC, relationship_count DESC, n.name
        LIMIT $limit
        """

        try:
            with self.get_session() as session:
                result = session.run(query, {"query": query_text, "limit": limit})
                nodes = [dict(record) for record in result]

                # Cache the result
                with self._cache_lock:
                    self._query_cache[cache_key] = nodes
                    self._cache_timestamps[cache_key] = time.time()

                return nodes
        except Exception as e:
            logger.error(f"Error searching nodes: {e}")
            return []

    def get_node_neighbors(
        self, node_id: str, depth: int = 1, max_nodes: int = 100
    ) -> Dict[str, Any]:
        """
        Get node neighbors with optimized traversal.

        Args:
            node_id: Node ID
            depth: Traversal depth
            max_nodes: Maximum number of nodes to return

        Returns:
            Dict[str, Any]: Neighbors and relationships
        """
        cache_key = self._get_cache_key(
            "get_node_neighbors",
            {"node_id": node_id, "depth": depth, "max_nodes": max_nodes},
        )

        # Check cache first
        with self._cache_lock:
            if cache_key in self._query_cache and self._is_cache_valid(cache_key):
                return self._query_cache[cache_key]

        # Optimized traversal query
        query = f"""
        MATCH (start:KnowledgeNode)-[r*1..{depth}]-(neighbor:KnowledgeNode)
        WHERE elementId(start) = $node_id
        WITH start, collect(DISTINCT neighbor) as neighbors, 
             collect(DISTINCT r) as relationships
        UNWIND neighbors[0..$max_nodes-1] as node
        RETURN elementId(node) as id, node.name as name, node.node_type as node_type,
               node.properties as properties, node.community_rating as community_rating
        LIMIT $max_nodes
        """

        try:
            with self.get_session() as session:
                result = session.run(
                    query, {"node_id": node_id, "max_nodes": max_nodes}
                )
                neighbors = [dict(record) for record in result]

                result_data = {"neighbors": neighbors, "total_count": len(neighbors)}

                # Cache the result
                with self._cache_lock:
                    self._query_cache[cache_key] = result_data
                    self._cache_timestamps[cache_key] = time.time()

                return result_data
        except Exception as e:
            logger.error(f"Error getting node neighbors: {e}")
            return {"neighbors": [], "total_count": 0}

    def update_node_validation(
        self,
        node_id: str,
        expert_validated: bool,
        community_rating: Optional[float] = None,
    ) -> bool:
        """
        Update node validation status with optimized query.

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
                result = session.run(
                    query,
                    {
                        "node_id": node_id,
                        "expert_validated": expert_validated,
                        "community_rating": community_rating,
                    },
                )
                success = result.single() is not None

                # Invalidate cache for this node
                with self._cache_lock:
                    keys_to_remove = [
                        k for k in self._query_cache.keys() if node_id in k
                    ]
                    for key in keys_to_remove:
                        del self._query_cache[key]
                        if key in self._cache_timestamps:
                            del self._cache_timestamps[key]

                return success
        except Exception as e:
            logger.error(f"Error updating node validation: {e}")
            return False

    def get_node_relationships(self, node_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get all relationships for a node with optimized queries.

        Args:
            node_id: Node ID

        Returns:
            Dict[str, List[Dict[str, Any]]]: Incoming and outgoing relationships
        """
        cache_key = self._get_cache_key("get_node_relationships", {"node_id": node_id})

        # Check cache first
        with self._cache_lock:
            if cache_key in self._query_cache and self._is_cache_valid(cache_key):
                return self._query_cache[cache_key]

        # Optimized parallel queries for incoming and outgoing
        incoming_query = """
        MATCH (a:KnowledgeNode)-[r:RELATIONSHIP]->(b:KnowledgeNode)
        WHERE elementId(b) = $node_id
        RETURN elementId(a) as source_id, a.name as source_name, 
               elementId(r) as rel_id, r.relationship_type as relationship_type,
               r.confidence_score as confidence_score, r.properties as properties
        ORDER BY r.confidence_score DESC
        """

        outgoing_query = """
        MATCH (a:KnowledgeNode)-[r:RELATIONSHIP]->(b:KnowledgeNode)
        WHERE elementId(a) = $node_id
        RETURN elementId(b) as target_id, b.name as target_name,
               elementId(r) as rel_id, r.relationship_type as relationship_type,
               r.confidence_score as confidence_score, r.properties as properties
        ORDER BY r.confidence_score DESC
        """

        try:
            with self.get_session() as session:
                # Run both queries concurrently in separate transactions
                incoming_result = session.run(incoming_query, {"node_id": node_id})
                outgoing_result = session.run(outgoing_query, {"node_id": node_id})

                relationships = {
                    "incoming": [dict(record) for record in incoming_result],
                    "outgoing": [dict(record) for record in outgoing_result],
                }

                # Cache the result
                with self._cache_lock:
                    self._query_cache[cache_key] = relationships
                    self._cache_timestamps[cache_key] = time.time()

                return relationships
        except Exception as e:
            logger.error(f"Error getting node relationships: {e}")
            return {"incoming": [], "outgoing": []}

    def delete_node(self, node_id: str) -> bool:
        """
        Delete a node and all its relationships with optimized query.

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
                success = record and record["deleted_count"] > 0

                # Invalidate cache for this node
                if success:
                    with self._cache_lock:
                        keys_to_remove = [
                            k for k in self._query_cache.keys() if node_id in k
                        ]
                        for key in keys_to_remove:
                            del self._query_cache[key]
                            if key in self._cache_timestamps:
                                del self._cache_timestamps[key]

                return success
        except Exception as e:
            logger.error(f"Error deleting node: {e}")
            return False

    def clear_cache(self):
        """Clear the query cache."""
        with self._cache_lock:
            self._query_cache.clear()
            self._cache_timestamps.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics for monitoring."""
        with self._cache_lock:
            current_time = time.time()
            valid_entries = sum(
                1
                for ts in self._cache_timestamps.values()
                if current_time - ts < self._cache_ttl
            )

            return {
                "total_entries": len(self._query_cache),
                "valid_entries": valid_entries,
                "expired_entries": len(self._query_cache) - valid_entries,
                "cache_ttl": self._cache_ttl,
            }


# Global optimized instance for application-wide access
optimized_graph_db = OptimizedGraphDatabaseManager()
