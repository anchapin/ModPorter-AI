"""
CRUD operations for Knowledge Graph and Community Curation System

This module provides database operations for knowledge graph models
using both PostgreSQL and Neo4j databases.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, desc

from .models import (
    KnowledgeNode, KnowledgeRelationship, ConversionPattern,
    CommunityContribution, VersionCompatibility
)
from .graph_db import graph_db
from .graph_db_optimized import optimized_graph_db

# Initialize logger
logger = logging.getLogger(__name__)

# Try to import performance monitoring and caching, but don't fail if not available
try:
    from ..utils.graph_performance_monitor import performance_monitor, monitor_graph_operation
    from ..utils.graph_cache import graph_cache, cached_node, cached_operation
    from ..db.neo4j_config import neo4j_config
    PERFORMANCE_ENABLED = True
except ImportError:
    PERFORMANCE_ENABLED = False
    logger.warning("Performance monitoring and caching not available, using basic implementation")
    
    # Create dummy decorators
    def monitor_graph_operation(op_name):
        def decorator(func):
            return func
        return decorator
    
    def cached_node(op_name, ttl=None):
        def decorator(func):
            return func
        return decorator
    
    def cached_operation(cache_type="default", ttl=None):
        def decorator(func):
            return func
        return decorator

logger = logging.getLogger(__name__)


class KnowledgeNodeCRUD:
    """CRUD operations for knowledge nodes with performance optimizations."""
    
    @staticmethod
    @monitor_graph_operation("node_creation")
    async def create(db: AsyncSession, node_data: Dict[str, Any]) -> Optional[KnowledgeNode]:
        """Create a new knowledge node with performance monitoring."""
        try:
            # Create in PostgreSQL
            db_node = KnowledgeNode(**node_data)
            db.add(db_node)
            await db.commit()
            await db.refresh(db_node)
            
            # Use optimized graph DB if available
            graph_manager = optimized_graph_db if PERFORMANCE_ENABLED else graph_db
            
            # Create in Neo4j with performance tracking
            node_id = graph_manager.create_node(
                node_type=node_data["node_type"],
                name=node_data["name"],
                properties=node_data.get("properties", {}),
                minecraft_version=node_data.get("minecraft_version", "latest"),
                platform=node_data.get("platform", "both"),
                created_by=node_data.get("created_by")
            )
            
            if node_id:
                # Store Neo4j ID in PostgreSQL record
                await db.execute(
                    update(KnowledgeNode)
                    .where(KnowledgeNode.id == db_node.id)
                    .values({"neo4j_id": node_id})
                )
                await db.commit()
                await db.refresh(db_node)
                
                # Cache the node
                if PERFORMANCE_ENABLED:
                    graph_cache.cache_node(db_node.id, {
                        "id": db_node.id,
                        "neo4j_id": node_id,
                        "node_type": db_node.node_type,
                        "name": db_node.name,
                        "properties": db_node.properties,
                        "platform": db_node.platform
                    })
            
            return db_node
        except Exception as e:
            logger.error(f"Error creating knowledge node: {e}")
            await db.rollback()
            return None
    
    @staticmethod
    async def create_batch(db: AsyncSession, nodes_data: List[Dict[str, Any]]) -> List[Optional[KnowledgeNode]]:
        """Create multiple knowledge nodes in batch for better performance."""
        if not PERFORMANCE_ENABLED or not hasattr(optimized_graph_db, 'create_node_batch'):
            # Fallback to individual creation
            return [await KnowledgeNodeCRUD.create(db, data) for data in nodes_data]
        
        try:
            # Create nodes in PostgreSQL first
            db_nodes = []
            for node_data in nodes_data:
                db_node = KnowledgeNode(**node_data)
                db.add(db_node)
                db_nodes.append(db_node)
            
            await db.commit()
            
            # Refresh all nodes
            for db_node in db_nodes:
                await db.refresh(db_node)
            
            # Create in Neo4j using batch operation
            neo4j_nodes = []
            for i, node_data in enumerate(nodes_data):
                neo4j_node = node_data.copy()
                neo4j_node['properties'] = node_data.get('properties', {})
                neo4j_nodes.append(neo4j_node)
            
            neo4j_ids = optimized_graph_db.create_node_batch(neo4j_nodes)
            
            # Update PostgreSQL records with Neo4j IDs
            for db_node, neo4j_id in zip(db_nodes, neo4j_ids):
                if neo4j_id:
                    await db.execute(
                        update(KnowledgeNode)
                        .where(KnowledgeNode.id == db_node.id)
                        .values({"neo4j_id": neo4j_id})
                    )
            
            await db.commit()
            
            # Refresh nodes again
            for db_node in db_nodes:
                await db.refresh(db_node)
            
            return db_nodes
        except Exception as e:
            logger.error(f"Error creating knowledge nodes in batch: {e}")
            await db.rollback()
            return [None] * len(nodes_data)
    
    @staticmethod
    async def get_by_id(db: AsyncSession, node_id: str) -> Optional[KnowledgeNode]:
        """Get knowledge node by ID."""
        try:
            result = await db.execute(
                select(KnowledgeNode).where(KnowledgeNode.id == node_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting knowledge node: {e}")
            return None
    
    @staticmethod
    async def get_by_type(db: AsyncSession, 
                         node_type: str, 
                         minecraft_version: str = "latest",
                         limit: int = 100) -> List[KnowledgeNode]:
        """Get knowledge nodes by type."""
        try:
            result = await db.execute(
                select(KnowledgeNode)
                .where(
                    KnowledgeNode.node_type == node_type,
                    func.lower(KnowledgeNode.minecraft_version).in_([minecraft_version, "latest"])
                )
                .order_by(desc(KnowledgeNode.community_rating), KnowledgeNode.name)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting knowledge nodes by type: {e}")
            return []
    
    @staticmethod
    @cached_node("search", ttl=300)  # Cache for 5 minutes
    @monitor_graph_operation("search")
    async def search(db: AsyncSession, 
                   query_text: str,
                   limit: int = 20) -> List[KnowledgeNode]:
        """Search knowledge nodes with caching and performance monitoring."""
        # Check cache first if performance features are enabled
        if PERFORMANCE_ENABLED:
            cached_results = graph_cache.get_cached_search(query_text, {"limit": limit})
            if cached_results:
                logger.debug(f"Search cache hit for query: {query_text}")
                return cached_results
        
        try:
            # Optimized PostgreSQL query with better indexing
            result = await db.execute(
                select(KnowledgeNode)
                .where(
                    func.lower(KnowledgeNode.name).contains(func.lower(query_text))
                )
                .order_by(desc(KnowledgeNode.community_rating), KnowledgeNode.name)
                .limit(limit)
            )
            nodes = result.scalars().all()
            
            # Cache the results
            if PERFORMANCE_ENABLED and nodes:
                graph_cache.cache_search(query_text, {"limit": limit}, nodes, ttl=300)
            
            return nodes
        except Exception as e:
            logger.error(f"Error searching knowledge nodes: {e}")
            return []
    
    @staticmethod
    async def update_validation(db: AsyncSession, 
                             node_id: str,
                             expert_validated: bool,
                             community_rating: Optional[float] = None) -> bool:
        """Update node validation status."""
        try:
            # Update in PostgreSQL
            update_data = {
                "expert_validated": expert_validated,
                "updated_at": datetime.utcnow()
            }
            if community_rating is not None:
                update_data["community_rating"] = community_rating
            
            result = await db.execute(
                update(KnowledgeNode)
                .where(KnowledgeNode.id == node_id)
                .values(update_data)
            )
            await db.commit()
            
            # Update in Neo4j
            db_node = await KnowledgeNodeCRUD.get_by_id(db, node_id)
            if db_node and db_node.neo4j_id:
                return graph_db.update_node_validation(
                    db_node.neo4j_id, expert_validated, community_rating
                )
            
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating node validation: {e}")
            await db.rollback()
            return False


class KnowledgeRelationshipCRUD:
    """CRUD operations for knowledge relationships."""
    
    @staticmethod
    async def create(db: AsyncSession, relationship_data: Dict[str, Any]) -> Optional[KnowledgeRelationship]:
        """Create a new knowledge relationship."""
        try:
            # Create in PostgreSQL
            db_relationship = KnowledgeRelationship(**relationship_data)
            db.add(db_relationship)
            await db.commit()
            await db.refresh(db_relationship)
            
            # Create in Neo4j
            rel_id = graph_db.create_relationship(
                source_node_id=relationship_data["source_node_id"],
                target_node_id=relationship_data["target_node_id"],
                relationship_type=relationship_data["relationship_type"],
                properties=relationship_data.get("properties", {}),
                confidence_score=relationship_data.get("confidence_score", 0.5),
                minecraft_version=relationship_data.get("minecraft_version", "latest"),
                created_by=relationship_data.get("created_by")
            )
            
            if rel_id:
                # Store Neo4j ID in PostgreSQL record
                await db.execute(
                    update(KnowledgeRelationship)
                    .where(KnowledgeRelationship.id == db_relationship.id)
                    .values({"neo4j_id": rel_id})
                )
                await db.commit()
                await db.refresh(db_relationship)
            
            return db_relationship
        except Exception as e:
            logger.error(f"Error creating knowledge relationship: {e}")
            await db.rollback()
            return None
    
    @staticmethod
    async def get_by_source(db: AsyncSession, 
                          source_node_id: str,
                          relationship_type: Optional[str] = None) -> List[KnowledgeRelationship]:
        """Get relationships by source node."""
        try:
            query = select(KnowledgeRelationship).where(
                KnowledgeRelationship.source_node_id == source_node_id
            )
            
            if relationship_type:
                query = query.where(KnowledgeRelationship.relationship_type == relationship_type)
            
            result = await db.execute(query.order_by(desc(KnowledgeRelationship.confidence_score)))
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting relationships: {e}")
            return []


class ConversionPatternCRUD:
    """CRUD operations for conversion patterns."""
    
    @staticmethod
    async def create(db: AsyncSession, pattern_data: Dict[str, Any]) -> Optional[ConversionPattern]:
        """Create a new conversion pattern."""
        try:
            db_pattern = ConversionPattern(**pattern_data)
            db.add(db_pattern)
            await db.commit()
            await db.refresh(db_pattern)
            return db_pattern
        except Exception as e:
            logger.error(f"Error creating conversion pattern: {e}")
            await db.rollback()
            return None
    
    @staticmethod
    async def get_by_id(db: AsyncSession, pattern_id: str) -> Optional[ConversionPattern]:
        """Get conversion pattern by ID."""
        try:
            result = await db.execute(
                select(ConversionPattern).where(ConversionPattern.id == pattern_id)
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting conversion pattern: {e}")
            return None
    
    @staticmethod
    async def get_by_version(db: AsyncSession, 
                           minecraft_version: str,
                           validation_status: Optional[str] = None,
                           limit: int = 50) -> List[ConversionPattern]:
        """Get conversion patterns by Minecraft version."""
        try:
            query = select(ConversionPattern).where(
                func.lower(ConversionPattern.minecraft_version) == func.lower(minecraft_version)
            )
            
            if validation_status:
                query = query.where(ConversionPattern.validation_status == validation_status)
            
            result = await db.execute(
                query.order_by(desc(ConversionPattern.success_rate), ConversionPattern.name)
                .limit(limit)
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting conversion patterns: {e}")
            return []
    
    @staticmethod
    async def update_success_rate(db: AsyncSession, 
                               pattern_id: str,
                               success_rate: float,
                               usage_count: int) -> bool:
        """Update pattern success metrics."""
        try:
            result = await db.execute(
                update(ConversionPattern)
                .where(ConversionPattern.id == pattern_id)
                .values({
                    "success_rate": success_rate,
                    "usage_count": usage_count,
                    "updated_at": datetime.utcnow()
                })
            )
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating pattern success rate: {e}")
            await db.rollback()
            return False


class CommunityContributionCRUD:
    """CRUD operations for community contributions."""
    
    @staticmethod
    async def create(db: AsyncSession, contribution_data: Dict[str, Any]) -> Optional[CommunityContribution]:
        """Create a new community contribution."""
        try:
            db_contribution = CommunityContribution(**contribution_data)
            db.add(db_contribution)
            await db.commit()
            await db.refresh(db_contribution)
            return db_contribution
        except Exception as e:
            logger.error(f"Error creating community contribution: {e}")
            await db.rollback()
            return None
    
    @staticmethod
    async def get_by_contributor(db: AsyncSession, 
                               contributor_id: str,
                               review_status: Optional[str] = None) -> List[CommunityContribution]:
        """Get contributions by contributor."""
        try:
            query = select(CommunityContribution).where(
                CommunityContribution.contributor_id == contributor_id
            )
            
            if review_status:
                query = query.where(CommunityContribution.review_status == review_status)
            
            result = await db.execute(query.order_by(desc(CommunityContribution.created_at)))
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting contributions: {e}")
            return []
    
    @staticmethod
    async def update_review_status(db: AsyncSession, 
                                contribution_id: str,
                                review_status: str,
                                validation_results: Optional[Dict[str, Any]] = None) -> bool:
        """Update contribution review status."""
        try:
            update_data = {
                "review_status": review_status,
                "updated_at": datetime.utcnow()
            }
            
            if validation_results:
                update_data["validation_results"] = validation_results
            
            result = await db.execute(
                update(CommunityContribution)
                .where(CommunityContribution.id == contribution_id)
                .values(update_data)
            )
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error updating review status: {e}")
            await db.rollback()
            return False
    
    @staticmethod
    async def vote(db: AsyncSession, contribution_id: str, vote_type: str) -> bool:
        """Add vote to contribution."""
        try:
            if vote_type == "up":
                result = await db.execute(
                    update(CommunityContribution)
                    .where(CommunityContribution.id == contribution_id)
                    .values({"votes": CommunityContribution.votes + 1, "updated_at": datetime.utcnow()})
                )
            elif vote_type == "down":
                result = await db.execute(
                    update(CommunityContribution)
                    .where(CommunityContribution.id == contribution_id)
                    .values({"votes": CommunityContribution.votes - 1, "updated_at": datetime.utcnow()})
                )
            else:
                return False
            
            await db.commit()
            return result.rowcount > 0
        except Exception as e:
            logger.error(f"Error voting on contribution: {e}")
            await db.rollback()
            return False


class VersionCompatibilityCRUD:
    """CRUD operations for version compatibility."""
    
    @staticmethod
    async def create(db: AsyncSession, compatibility_data: Dict[str, Any]) -> Optional[VersionCompatibility]:
        """Create new version compatibility entry."""
        try:
            db_compatibility = VersionCompatibility(**compatibility_data)
            db.add(db_compatibility)
            await db.commit()
            await db.refresh(db_compatibility)
            return db_compatibility
        except Exception as e:
            logger.error(f"Error creating version compatibility: {e}")
            await db.rollback()
            return None
    
    @staticmethod
    async def get_compatibility(db: AsyncSession, 
                              java_version: str,
                              bedrock_version: str) -> Optional[VersionCompatibility]:
        """Get compatibility between Java and Bedrock versions."""
        try:
            result = await db.execute(
                select(VersionCompatibility)
                .where(
                    VersionCompatibility.java_version == java_version,
                    VersionCompatibility.bedrock_version == bedrock_version
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting version compatibility: {e}")
            return None
    
    @staticmethod
    async def get_by_java_version(db: AsyncSession, 
                                java_version: str) -> List[VersionCompatibility]:
        """Get all compatibility entries for a Java version."""
        try:
            result = await db.execute(
                select(VersionCompatibility)
                .where(VersionCompatibility.java_version == java_version)
                .order_by(desc(VersionCompatibility.compatibility_score))
            )
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting compatibility by Java version: {e}")
            return []
