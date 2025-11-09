"""
Knowledge Graph API Endpoints

This module provides REST API endpoints for the knowledge graph
and community curation system.
"""

from typing import Dict, List, Optional, Any

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from db.base import get_db
from db.knowledge_graph_crud import (
    KnowledgeNodeCRUD, KnowledgeRelationshipCRUD, ConversionPatternCRUD,
    CommunityContributionCRUD, VersionCompatibilityCRUD
)
from db.graph_db import graph_db
from db.models import (
    KnowledgeNode as KnowledgeNodeModel,
    KnowledgeRelationship as KnowledgeRelationshipModel,
    ConversionPattern as ConversionPatternModel,
    CommunityContribution as CommunityContributionModel,
    VersionCompatibility as VersionCompatibilityModel
)

router = APIRouter()


# Knowledge Node Endpoints

@router.post("/nodes")
async def create_knowledge_node(
    node_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create a new knowledge node."""
    try:
        node = await KnowledgeNodeCRUD.create(db, node_data)
        if not node:
            raise HTTPException(status_code=400, detail="Failed to create knowledge node")
        return node
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating knowledge node: {str(e)}")


@router.get("/nodes/{node_id}")
async def get_knowledge_node(
    node_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get knowledge node by ID."""
    try:
        node = await KnowledgeNodeCRUD.get_by_id(db, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Knowledge node not found")
        return node
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting knowledge node: {str(e)}")


@router.get("/nodes", response_model=List[KnowledgeNodeModel])
async def get_knowledge_nodes(
    node_type: Optional[str] = Query(None, description="Filter by node type"),
    minecraft_version: str = Query("latest", description="Minecraft version"),
    search: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(100, le=500, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
):
    """Get knowledge nodes with optional filtering."""
    try:
        if search:
            return await KnowledgeNodeCRUD.search(db, search, limit)
        elif node_type:
            return await KnowledgeNodeCRUD.get_by_type(db, node_type, minecraft_version, limit)
        else:
            # Get all nodes (could be expensive, consider pagination)
            query = select(KnowledgeNodeModel).limit(limit)
            result = await db.execute(query)
            return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting knowledge nodes: {str(e)}")


@router.put("/nodes/{node_id}/validation")
async def update_node_validation(
    node_id: str,
    validation_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update node validation status and rating."""
    try:
        expert_validated = validation_data.get("expert_validated", False)
        community_rating = validation_data.get("community_rating")
        
        success = await KnowledgeNodeCRUD.update_validation(
            db, node_id, expert_validated, community_rating
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Knowledge node not found or update failed")
        
        return {"message": "Node validation updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating node validation: {str(e)}")


# Knowledge Relationship Endpoints

@router.post("/relationships", response_model=KnowledgeRelationshipModel)
async def create_knowledge_relationship(
    relationship_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create a new knowledge relationship."""
    try:
        relationship = await KnowledgeRelationshipCRUD.create(db, relationship_data)
        if not relationship:
            raise HTTPException(status_code=400, detail="Failed to create knowledge relationship")
        return relationship
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating knowledge relationship: {str(e)}")


@router.get("/relationships/{node_id}", response_model=List[KnowledgeRelationshipModel])
async def get_node_relationships(
    node_id: str,
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type"),
    db: AsyncSession = Depends(get_db)
):
    """Get relationships for a specific node."""
    try:
        # Get from PostgreSQL
        relationships = await KnowledgeRelationshipCRUD.get_by_source(db, node_id, relationship_type)
        
        # Also get from Neo4j for graph visualization
        neo4j_relationships = graph_db.get_node_relationships(node_id)
        
        return {
            "relationships": relationships,
            "graph_data": neo4j_relationships
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting relationships: {str(e)}")


# Conversion Pattern Endpoints

@router.post("/patterns", response_model=ConversionPatternModel)
async def create_conversion_pattern(
    pattern_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create a new conversion pattern."""
    try:
        pattern = await ConversionPatternCRUD.create(db, pattern_data)
        if not pattern:
            raise HTTPException(status_code=400, detail="Failed to create conversion pattern")
        return pattern
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating conversion pattern: {str(e)}")


@router.get("/patterns", response_model=List[ConversionPatternModel])
async def get_conversion_patterns(
    minecraft_version: str = Query("latest", description="Minecraft version"),
    validation_status: Optional[str] = Query(None, description="Filter by validation status"),
    limit: int = Query(50, le=200, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
):
    """Get conversion patterns with optional filtering."""
    try:
        return await ConversionPatternCRUD.get_by_version(
            db, minecraft_version, validation_status, limit
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conversion patterns: {str(e)}")


@router.get("/patterns/{pattern_id}", response_model=ConversionPatternModel)
async def get_conversion_pattern(
    pattern_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get conversion pattern by ID."""
    try:
        pattern = await ConversionPatternCRUD.get_by_id(db, pattern_id)
        if not pattern:
            raise HTTPException(status_code=404, detail="Conversion pattern not found")
        return pattern
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting conversion pattern: {str(e)}")


@router.put("/patterns/{pattern_id}/metrics")
async def update_pattern_metrics(
    pattern_id: str,
    metrics: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update pattern success metrics."""
    try:
        success_rate = metrics.get("success_rate")
        usage_count = metrics.get("usage_count")
        
        success = await ConversionPatternCRUD.update_success_rate(
            db, pattern_id, success_rate, usage_count
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Conversion pattern not found or update failed")
        
        return {"message": "Pattern metrics updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating pattern metrics: {str(e)}")


# Community Contribution Endpoints

@router.post("/contributions", response_model=CommunityContributionModel)
async def create_community_contribution(
    contribution_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Create a new community contribution."""
    try:
        contribution = await CommunityContributionCRUD.create(db, contribution_data)
        if not contribution:
            raise HTTPException(status_code=400, detail="Failed to create community contribution")
        
        # Add background task to validate contribution
        background_tasks.add_task(validate_contribution, contribution.id)
        
        return contribution
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating community contribution: {str(e)}")


@router.get("/contributions", response_model=List[CommunityContributionModel])
async def get_community_contributions(
    contributor_id: Optional[str] = Query(None, description="Filter by contributor ID"),
    review_status: Optional[str] = Query(None, description="Filter by review status"),
    contribution_type: Optional[str] = Query(None, description="Filter by contribution type"),
    limit: int = Query(50, le=200, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
):
    """Get community contributions with optional filtering."""
    try:
        if contributor_id:
            return await CommunityContributionCRUD.get_by_contributor(db, contributor_id, review_status)
        else:
            # Get all contributions with filters
            query = select(CommunityContributionModel)
            
            if review_status:
                query = query.where(CommunityContributionModel.review_status == review_status)
            
            if contribution_type:
                query = query.where(CommunityContributionModel.contribution_type == contribution_type)
            
            query = query.order_by(desc(CommunityContributionModel.created_at)).limit(limit)
            result = await db.execute(query)
            return result.scalars().all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting community contributions: {str(e)}")


@router.put("/contributions/{contribution_id}/review")
async def update_contribution_review(
    contribution_id: str,
    review_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Update contribution review status."""
    try:
        review_status = review_data.get("review_status")
        validation_results = review_data.get("validation_results")
        
        success = await CommunityContributionCRUD.update_review_status(
            db, contribution_id, review_status, validation_results
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Community contribution not found or update failed")
        
        return {"message": "Contribution review status updated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating contribution review: {str(e)}")


@router.post("/contributions/{contribution_id}/vote")
async def vote_on_contribution(
    contribution_id: str,
    vote_data: Dict[str, str],
    db: AsyncSession = Depends(get_db)
):
    """Vote on a community contribution."""
    try:
        vote_type = vote_data.get("vote_type")  # "up" or "down"
        
        if vote_type not in ["up", "down"]:
            raise HTTPException(status_code=400, detail="Invalid vote type. Must be 'up' or 'down'")
        
        success = await CommunityContributionCRUD.vote(db, contribution_id, vote_type)
        
        if not success:
            raise HTTPException(status_code=404, detail="Community contribution not found or vote failed")
        
        return {"message": "Vote recorded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error voting on contribution: {str(e)}")


# Version Compatibility Endpoints

@router.post("/compatibility", response_model=VersionCompatibilityModel)
async def create_version_compatibility(
    compatibility_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create a new version compatibility entry."""
    try:
        compatibility = await VersionCompatibilityCRUD.create(db, compatibility_data)
        if not compatibility:
            raise HTTPException(status_code=400, detail="Failed to create version compatibility entry")
        return compatibility
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating version compatibility: {str(e)}")


@router.get("/compatibility/{java_version}/{bedrock_version}", response_model=VersionCompatibilityModel)
async def get_version_compatibility(
    java_version: str,
    bedrock_version: str,
    db: AsyncSession = Depends(get_db)
):
    """Get compatibility between Java and Bedrock versions."""
    try:
        compatibility = await VersionCompatibilityCRUD.get_compatibility(db, java_version, bedrock_version)
        if not compatibility:
            raise HTTPException(status_code=404, detail="Version compatibility not found")
        return compatibility
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting version compatibility: {str(e)}")


@router.get("/compatibility/{java_version}", response_model=List[VersionCompatibilityModel])
async def get_compatibility_by_java_version(
    java_version: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all compatibility entries for a Java version."""
    try:
        return await VersionCompatibilityCRUD.get_by_java_version(db, java_version)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting compatibility by Java version: {str(e)}")


# Graph Visualization Endpoints

@router.get("/graph/search")
async def search_graph(
    query: str = Query(..., description="Search query"),
    limit: int = Query(20, le=100, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db)
):
    """Search knowledge graph nodes and relationships."""
    try:
        # Search in Neo4j
        neo4j_results = graph_db.search_nodes(query, limit)
        
        # Also search in PostgreSQL for additional metadata
        pg_results = await KnowledgeNodeCRUD.search(db, query, limit)
        
        return {
            "neo4j_results": neo4j_results,
            "postgresql_results": pg_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching graph: {str(e)}")


@router.get("/graph/paths/{node_id}")
async def find_conversion_paths(
    node_id: str,
    max_depth: int = Query(3, le=5, ge=1, description="Maximum path depth"),
    minecraft_version: str = Query("latest", description="Minecraft version"),
    db: AsyncSession = Depends(get_db)
):
    """Find conversion paths from a Java concept to Bedrock concepts."""
    try:
        # Verify node exists and is a Java concept
        node = await KnowledgeNodeCRUD.get_by_id(db, node_id)
        if not node:
            raise HTTPException(status_code=404, detail="Knowledge node not found")
        
        if node.platform not in ["java", "both"]:
            raise HTTPException(status_code=400, detail="Node must be a Java concept")
        
        # Find paths in Neo4j
        paths = graph_db.find_conversion_paths(
            node.neo4j_id or node_id, 
            max_depth, 
            minecraft_version
        )
        
        return {
            "source_node": node,
            "conversion_paths": paths,
            "minecraft_version": minecraft_version
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding conversion paths: {str(e)}")


# Background Tasks

async def validate_contribution(contribution_id: str):
    """Background task to validate community contributions."""
    # This would implement AI-based validation logic
    # For now, just log the validation request
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Validating community contribution: {contribution_id}")
    
    # TODO: Implement actual validation logic using AI Engine
    # - Check if contribution follows format
    # - Validate Java/Bedrock compatibility
    # - Run automated tests
    # - Provide validation results
