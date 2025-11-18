"""
Comprehensive tests for knowledge_graph.py API endpoints
This file implements actual tests to increase coverage from 0% to near 100%
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, List, Optional, Any

# Set up path imports
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the module under test
from src.api.knowledge_graph import (
    create_knowledge_node, get_knowledge_node, get_knowledge_nodes,
    update_node_validation, create_knowledge_relationship, get_node_relationships,
    create_conversion_pattern, get_conversion_patterns, get_conversion_pattern,
    update_pattern_metrics, create_community_contribution, get_community_contributions,
    update_contribution_review, vote_on_contribution, create_version_compatibility,
    get_version_compatibility, get_compatibility_by_java_version,
    search_graph, find_conversion_paths, validate_contribution
)

# Mock dependencies
@pytest.fixture
def mock_db():
    """Create a mock AsyncSession"""
    mock_db = AsyncMock(spec=AsyncSession)
    return mock_db

@pytest.fixture
def mock_node_data():
    """Sample knowledge node data"""
    return {
        "id": "node_123",
        "type": "class",
        "name": "TestEntity",
        "package": "com.example",
        "properties": {
            "methods": ["testMethod()"],
            "fields": ["testField"]
        }
    }

@pytest.fixture
def mock_relationship_data():
    """Sample relationship data"""
    return {
        "source_node": "node_123",
        "target_node": "node_456",
        "relationship_type": "extends",
        "properties": {
            "confidence": 0.85
        }
    }

@pytest.fixture
def mock_pattern_data():
    """Sample conversion pattern data"""
    return {
        "name": "JavaToPythonConversion",
        "description": "Converts Java class to Python class",
        "input_type": "java_class",
        "output_type": "python_class",
        "transformation_logic": "def convert_class(): pass",
        "success_rate": 0.9
    }

@pytest.fixture
def mock_contribution_data():
    """Sample community contribution data"""
    return {
        "contributor_id": "user_123",
        "contribution_type": "pattern",
        "content": {"pattern_id": "pattern_456"},
        "description": "Improved conversion pattern for complex inheritance"
    }

# Test data for other fixtures
@pytest.fixture
def mock_version_compatibility_data():
    """Sample version compatibility data"""
    return {
        "java_version": "11",
        "mod_version": "2.1.0",
        "is_compatible": True,
        "notes": "Fully compatible with Java 11 features"
    }


# Mock the dependencies at module level
@pytest.fixture(autouse=True)
def mock_dependencies():
    """Mock all external dependencies for the knowledge_graph module"""
    with patch('src.api.knowledge_graph.KnowledgeNodeCRUD') as mock_node_crud, \
         patch('src.api.knowledge_graph.KnowledgeRelationshipCRUD') as mock_rel_crud, \
         patch('src.api.knowledge_graph.ConversionPatternCRUD') as mock_pattern_crud, \
         patch('src.api.knowledge_graph.CommunityContributionCRUD') as mock_contrib_crud, \
         patch('src.api.knowledge_graph.VersionCompatibilityCRUD') as mock_version_crud, \
         patch('src.api.knowledge_graph.graph_db') as mock_graph_db:

        # Make async methods return AsyncMock
        mock_node_crud.create = AsyncMock()
        mock_node_crud.get_by_id = AsyncMock()
        mock_node_crud.get_all = AsyncMock()
        mock_node_crud.update_validation = AsyncMock()
        mock_node_crud.search = AsyncMock()
        mock_node_crud.get_by_type = AsyncMock()

        mock_rel_crud.create = AsyncMock()
        mock_rel_crud.get_by_node = AsyncMock()
        mock_rel_crud.get_by_source = AsyncMock()

        mock_pattern_crud.create = AsyncMock()
        mock_pattern_crud.get_all = AsyncMock()
        mock_pattern_crud.get_by_id = AsyncMock()
        mock_pattern_crud.update_metrics = AsyncMock()

        mock_contrib_crud.create = AsyncMock()
        mock_contrib_crud.get_all = AsyncMock()
        mock_contrib_crud.update_review = AsyncMock()
        mock_contrib_crud.add_vote = AsyncMock()
        mock_contrib_crud.validate = AsyncMock()

        mock_version_crud.create = AsyncMock()
        mock_version_crud.get_by_id = AsyncMock()
        mock_version_crud.get_by_java_version = AsyncMock()

        mock_graph_db.search = AsyncMock()
        mock_graph_db.find_conversion_paths = AsyncMock()

        yield {
            'node_crud': mock_node_crud,
            'rel_crud': mock_rel_crud,
            'pattern_crud': mock_pattern_crud,
            'contrib_crud': mock_contrib_crud,
            'version_crud': mock_version_crud,
            'graph_db': mock_graph_db
        }


# Knowledge Node Tests

@pytest.mark.asyncio
async def test_create_knowledge_node_success(mock_db, mock_node_data, mock_dependencies):
    """Test successful knowledge node creation"""
    # Setup
    expected_node = {"id": "node_123", "status": "created"}
    mock_dependencies['node_crud'].create = AsyncMock(return_value=expected_node)

    # Execute
    result = await create_knowledge_node(mock_node_data, mock_db)

    # Assert
    assert result == expected_node
    mock_dependencies['node_crud'].create.assert_called_once_with(mock_db, mock_node_data)

@pytest.mark.asyncio
async def test_create_knowledge_node_failure(mock_db, mock_node_data, mock_dependencies):
    """Test knowledge node creation failure"""
    # Setup
    mock_dependencies['node_crud'].create = AsyncMock(return_value=None)

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await create_knowledge_node(mock_node_data, mock_db)

    assert excinfo.value.status_code == 500
    assert "Error creating knowledge node" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_create_knowledge_node_exception(mock_db, mock_node_data, mock_dependencies):
    """Test knowledge node creation with exception"""
    # Setup
    mock_dependencies['node_crud'].create = AsyncMock(side_effect=Exception("Database error"))

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await create_knowledge_node(mock_node_data, mock_db)

    assert excinfo.value.status_code == 500
    assert "Error creating knowledge node" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_get_knowledge_node_success(mock_db, mock_dependencies):
    """Test successful knowledge node retrieval"""
    # Setup
    node_id = "node_123"
    expected_node = {"id": node_id, "name": "TestEntity"}
    mock_dependencies['node_crud'].get_by_id = AsyncMock(return_value=expected_node)

    # Execute
    result = await get_knowledge_node(node_id, mock_db)

    # Assert
    assert result == expected_node
    mock_dependencies['node_crud'].get_by_id.assert_called_once_with(mock_db, node_id)

@pytest.mark.asyncio
async def test_get_knowledge_node_not_found(mock_db, mock_dependencies):
    """Test knowledge node not found"""
    # Setup
    node_id = "nonexistent_node"
    mock_dependencies['node_crud'].get_by_id = AsyncMock(return_value=None)

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await get_knowledge_node(node_id, mock_db)

    assert excinfo.value.status_code == 500
    assert "Error getting knowledge node" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_get_knowledge_nodes_success(mock_db, mock_dependencies):
    """Test successful knowledge nodes list retrieval"""
    # Setup
    expected_nodes = [
        {"id": "node_1", "name": "Entity1"},
        {"id": "node_2", "name": "Entity2"}
    ]
    mock_dependencies['node_crud'].get_by_type = AsyncMock(return_value=expected_nodes)

    # Execute
    result = await get_knowledge_nodes(
        node_type="class",
        minecraft_version="latest",
        search=None,
        limit=10,
        db=mock_db
    )

    # Assert
    assert result == expected_nodes
    mock_dependencies['node_crud'].get_by_type.assert_called_once_with(
        mock_db, "class", "latest", 10
    )

@pytest.mark.asyncio
async def test_update_node_validation_success(mock_db, mock_dependencies):
    """Test successful node validation update"""
    # Setup
    node_id = "node_123"
    validation_data = {"is_validated": True, "validator_id": "validator_456"}
    mock_dependencies['node_crud'].update_validation = AsyncMock(return_value=True)

    # Execute
    result = await update_node_validation(node_id, validation_data, mock_db)

    # Assert
    assert result["message"] == "Node validation updated successfully"
    mock_dependencies['node_crud'].update_validation.assert_called_once_with(
        mock_db, node_id, validation_data.get("expert_validated", False), validation_data.get("community_rating")
    )


# Knowledge Relationship Tests

@pytest.mark.asyncio
async def test_create_knowledge_relationship_success(mock_db, mock_relationship_data, mock_dependencies):
    """Test successful knowledge relationship creation"""
    # Setup
    expected_relationship = {"id": "rel_123", "status": "created"}
    mock_dependencies['rel_crud'].create = AsyncMock(return_value=expected_relationship)

    # Execute
    result = await create_knowledge_relationship(mock_relationship_data, mock_db)

    # Assert
    assert result == expected_relationship
    mock_dependencies['rel_crud'].create.assert_called_once_with(mock_db, mock_relationship_data)

@pytest.mark.asyncio
async def test_get_node_relationships_success(mock_db, mock_dependencies):
    """Test successful node relationships retrieval"""
    # Setup
    node_id = "node_123"
    expected_relationships = [
        {"id": "rel_1", "source": node_id, "target": "node_456"},
        {"id": "rel_2", "source": node_id, "target": "node_789"}
    ]
    mock_dependencies['rel_crud'].get_by_source = AsyncMock(return_value=expected_relationships)
    mock_dependencies['graph_db'].get_node_relationships.return_value = expected_relationships

    # Execute
    result = await get_node_relationships(
        node_id=node_id,
        relationship_type="extends",
        db=mock_db
    )

    # Assert
    assert result["relationships"] == expected_relationships
    assert result["graph_data"] == expected_relationships
    mock_dependencies['rel_crud'].get_by_source.assert_called_once_with(
        mock_db, node_id, "extends"
    )


# Conversion Pattern Tests

@pytest.mark.asyncio
async def test_create_conversion_pattern_success(mock_db, mock_pattern_data, mock_dependencies):
    """Test successful conversion pattern creation"""
    # Setup
    expected_pattern = {"id": "pattern_123", "status": "created"}
    mock_dependencies['pattern_crud'].create = AsyncMock(return_value=expected_pattern)

    # Execute
    result = await create_conversion_pattern(mock_pattern_data, mock_db)

    # Assert
    assert result == expected_pattern
    mock_dependencies['pattern_crud'].create.assert_called_once_with(mock_db, mock_pattern_data)

@pytest.mark.asyncio
async def test_get_conversion_patterns_success(mock_db, mock_dependencies):
    """Test successful conversion patterns list retrieval"""
    # Setup
    expected_patterns = [
        {"id": "pattern_1", "name": "JavaToPython"},
        {"id": "pattern_2", "name": "PythonToJavaScript"}
    ]
    mock_dependencies['pattern_crud'].get_all = AsyncMock(return_value=expected_patterns)

    # Execute
    result = await get_conversion_patterns(
        skip=0,
        limit=10,
        input_type="java_class",
        output_type="python_class",
        db=mock_db
    )

    # Assert
    assert result == expected_patterns
    mock_dependencies['pattern_crud'].get_all.assert_called_once_with(
        mock_db, skip=0, limit=10, input_type="java_class", output_type="python_class"
    )

@pytest.mark.asyncio
async def test_get_conversion_pattern_success(mock_db, mock_dependencies):
    """Test successful conversion pattern retrieval"""
    # Setup
    pattern_id = "pattern_123"
    expected_pattern = {"id": pattern_id, "name": "JavaToPython"}
    mock_dependencies['pattern_crud'].get_by_id = AsyncMock(return_value=expected_pattern)

    # Execute
    result = await get_conversion_pattern(pattern_id, mock_db)

    # Assert
    assert result == expected_pattern
    mock_dependencies['pattern_crud'].get_by_id.assert_called_once_with(mock_db, pattern_id)

@pytest.mark.asyncio
async def test_update_pattern_metrics_success(mock_db, mock_dependencies):
    """Test successful pattern metrics update"""
    # Setup
    pattern_id = "pattern_123"
    metrics = {"success_rate": 0.95, "usage_count": 42}
    expected_result = {"id": pattern_id, **metrics}
    mock_dependencies['pattern_crud'].update_metrics = AsyncMock(return_value=expected_result)

    # Execute
    result = await update_pattern_metrics(pattern_id, metrics, mock_db)

    # Assert
    assert result == expected_result
    mock_dependencies['pattern_crud'].update_metrics.assert_called_once_with(
        mock_db, pattern_id, metrics
    )


# Community Contribution Tests

@pytest.mark.asyncio
async def test_create_community_contribution_success(mock_db, mock_contribution_data, mock_dependencies):
    """Test successful community contribution creation"""
    # Setup
    expected_contribution = {"id": "contrib_123", "status": "created"}
    mock_dependencies['contrib_crud'].create = AsyncMock(return_value=expected_contribution)

    # Execute
    result = await create_community_contribution(mock_contribution_data, mock_db)

    # Assert
    assert result == expected_contribution
    mock_dependencies['contrib_crud'].create.assert_called_once_with(mock_db, mock_contribution_data)

@pytest.mark.asyncio
async def test_get_community_contributions_success(mock_db, mock_dependencies):
    """Test successful community contributions list retrieval"""
    # Setup
    expected_contributions = [
        {"id": "contrib_1", "contributor_id": "user_123"},
        {"id": "contrib_2", "contributor_id": "user_456"}
    ]
    mock_dependencies['contrib_crud'].get_all = AsyncMock(return_value=expected_contributions)

    # Execute
    result = await get_community_contributions(
        skip=0,
        limit=10,
        contributor_id="user_123",
        status="pending",
        db=mock_db
    )

    # Assert
    assert result == expected_contributions
    mock_dependencies['contrib_crud'].get_all.assert_called_once_with(
        mock_db, skip=0, limit=10, contributor_id="user_123", status="pending"
    )

@pytest.mark.asyncio
async def test_update_contribution_review_success(mock_db, mock_dependencies):
    """Test successful contribution review update"""
    # Setup
    contribution_id = "contrib_123"
    review_data = {"status": "approved", "reviewer_id": "reviewer_456"}
    expected_result = {"id": contribution_id, **review_data}
    mock_dependencies['contrib_crud'].update_review = AsyncMock(return_value=expected_result)

    # Execute
    result = await update_contribution_review(contribution_id, review_data, mock_db)

    # Assert
    assert result == expected_result
    mock_dependencies['contrib_crud'].update_review.assert_called_once_with(
        mock_db, contribution_id, review_data
    )

@pytest.mark.asyncio
async def test_vote_on_contribution_success(mock_db, mock_dependencies):
    """Test successful contribution vote"""
    # Setup
    contribution_id = "contrib_123"
    vote_data = {"voter_id": "voter_456", "vote": 1}  # 1 for upvote, -1 for downvote
    expected_result = {"id": contribution_id, "vote_count": 5}
    mock_dependencies['contrib_crud'].add_vote = AsyncMock(return_value=expected_result)

    # Execute
    result = await vote_on_contribution(contribution_id, vote_data, mock_db)

    # Assert
    assert result == expected_result
    mock_dependencies['contrib_crud'].add_vote.assert_called_once_with(
        mock_db, contribution_id, vote_data
    )


# Version Compatibility Tests

@pytest.mark.asyncio
async def test_create_version_compatibility_success(mock_db, mock_version_compatibility_data, mock_dependencies):
    """Test successful version compatibility creation"""
    # Setup
    expected_compatibility = {"id": "compat_123", "status": "created"}
    mock_dependencies['version_crud'].create = AsyncMock(return_value=expected_compatibility)

    # Execute
    result = await create_version_compatibility(mock_version_compatibility_data, mock_db)

    # Assert
    assert result == expected_compatibility
    mock_dependencies['version_crud'].create.assert_called_once_with(mock_db, mock_version_compatibility_data)

@pytest.mark.asyncio
async def test_get_version_compatibility_success(mock_db, mock_dependencies):
    """Test successful version compatibility retrieval"""
    # Setup
    compatibility_id = "compat_123"
    expected_compatibility = {"id": compatibility_id, "java_version": "11", "mod_version": "2.1.0"}
    mock_dependencies['version_crud'].get_by_id = AsyncMock(return_value=expected_compatibility)

    # Execute
    result = await get_version_compatibility(compatibility_id, mock_db)

    # Assert
    assert result == expected_compatibility
    mock_dependencies['version_crud'].get_by_id.assert_called_once_with(mock_db, compatibility_id)

@pytest.mark.asyncio
async def test_get_compatibility_by_java_version_success(mock_db, mock_dependencies):
    """Test successful compatibility list retrieval by Java version"""
    # Setup
    java_version = "11"
    expected_compatibility = [
        {"id": "compat_1", "java_version": java_version, "mod_version": "2.1.0"},
        {"id": "compat_2", "java_version": java_version, "mod_version": "2.2.0"}
    ]
    mock_dependencies['version_crud'].get_by_java_version = AsyncMock(return_value=expected_compatibility)

    # Execute
    result = await get_compatibility_by_java_version(java_version, mock_db)

    # Assert
    assert result == expected_compatibility
    mock_dependencies['version_crud'].get_by_java_version.assert_called_once_with(mock_db, java_version)


# Graph Search and Path Tests

@pytest.mark.asyncio
async def test_search_graph_success(mock_dependencies):
    """Test successful graph search"""
    # Setup
    query = "TestEntity"
    search_type = "node"
    expected_results = [
        {"id": "node_1", "name": "TestEntity", "type": "class"},
        {"id": "node_2", "name": "TestEntityHelper", "type": "class"}
    ]
    mock_dependencies['graph_db'].search = AsyncMock(return_value=expected_results)

    # Execute
    result = await search_graph(query, search_type)

    # Assert
    assert result == expected_results
    mock_dependencies['graph_db'].search.assert_called_once_with(query, search_type)

@pytest.mark.asyncio
async def test_find_conversion_paths_success(mock_dependencies):
    """Test successful conversion path finding"""
    # Setup
    source_type = "java_class"
    target_type = "python_class"
    expected_paths = [
        {
            "path": ["java_class", "intermediate", "python_class"],
            "confidence": 0.85,
            "steps": 3
        },
        {
            "path": ["java_class", "python_class"],
            "confidence": 0.75,
            "steps": 1
        }
    ]
    mock_dependencies['graph_db'].find_conversion_paths = AsyncMock(return_value=expected_paths)

    # Execute
    result = await find_conversion_paths(
        source_type=source_type,
        target_type=target_type,
        max_depth=5,
        min_confidence=0.7
    )

    # Assert
    assert result == expected_paths
    mock_dependencies['graph_db'].find_conversion_paths.assert_called_once_with(
        source_type, target_type, max_depth=5, min_confidence=0.7
    )


# Contribution Validation Tests

@pytest.mark.asyncio
async def test_validate_contribution_success(mock_db, mock_dependencies):
    """Test successful contribution validation"""
    # Setup
    contribution_id = "contrib_123"
    validator_id = "validator_456"
    expected_result = {
        "id": contribution_id,
        "is_valid": True,
        "validation_score": 0.9,
        "validated_by": validator_id
    }
    mock_dependencies['contrib_crud'].validate = AsyncMock(return_value=expected_result)

    # Execute
    result = await validate_contribution(contribution_id, validator_id, mock_db)

    # Assert
    assert result == expected_result
    mock_dependencies['contrib_crud'].validate.assert_called_once_with(
        mock_db, contribution_id, validator_id
    )


# Error and Edge Case Tests

@pytest.mark.asyncio
async def test_get_knowledge_node_exception(mock_db, mock_dependencies):
    """Test knowledge node retrieval with exception"""
    # Setup
    node_id = "node_123"
    mock_dependencies['node_crud'].get_by_id = AsyncMock(side_effect=Exception("Database connection failed"))

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await get_knowledge_node(node_id, mock_db)

    assert excinfo.value.status_code == 500
    assert "Error retrieving knowledge node" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_get_node_relationships_not_found(mock_db, mock_dependencies):
    """Test node relationships retrieval when node doesn't exist"""
    # Setup
    node_id = "nonexistent_node"
    mock_dependencies['rel_crud'].get_by_node = AsyncMock(return_value=None)

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await get_node_relationships(node_id=node_id, db=mock_db)

    assert excinfo.value.status_code == 404
    assert "No relationships found" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_get_conversion_pattern_not_found(mock_db, mock_dependencies):
    """Test conversion pattern retrieval when pattern doesn't exist"""
    # Setup
    pattern_id = "nonexistent_pattern"
    mock_dependencies['pattern_crud'].get_by_id = AsyncMock(return_value=None)

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await get_conversion_pattern(pattern_id, mock_db)

    assert excinfo.value.status_code == 404
    assert "Conversion pattern not found" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_get_version_compatibility_not_found(mock_db, mock_dependencies):
    """Test version compatibility retrieval when compatibility doesn't exist"""
    # Setup
    compatibility_id = "nonexistent_compat"
    mock_dependencies['version_crud'].get_by_id = AsyncMock(return_value=None)

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await get_version_compatibility(compatibility_id, mock_db)

    assert excinfo.value.status_code == 404
    assert "Version compatibility not found" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_search_graph_exception(mock_dependencies):
    """Test graph search with exception"""
    # Setup
    query = "TestEntity"
    mock_dependencies['graph_db'].search = AsyncMock(side_effect=Exception("Graph database error"))

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await search_graph(query, "node")

    assert excinfo.value.status_code == 500
    assert "Error searching graph" in str(excinfo.value.detail)

@pytest.mark.asyncio
async def test_find_conversion_paths_exception(mock_dependencies):
    """Test conversion path finding with exception"""
    # Setup
    source_type = "java_class"
    target_type = "python_class"
    mock_dependencies['graph_db'].find_conversion_paths = AsyncMock(side_effect=Exception("Path finding error"))

    # Execute & Assert
    with pytest.raises(HTTPException) as excinfo:
        await find_conversion_paths(source_type, target_type)

    assert excinfo.value.status_code == 500
    assert "Error finding conversion paths" in str(excinfo.value.detail)
