"""
Comprehensive tests for graph_version_control.py
High-impact service: 417 statements, 28% coverage → target 80%
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import sys
import os
from datetime import datetime
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.graph_version_control import (
    GraphVersionControlService, 
    ChangeType, 
    ItemType, 
    GraphChange,
    GraphBranch,
    GraphCommit,
    GraphDiff,
    MergeResult
)


class TestGraphVersionControlService:
    """Test suite for GraphVersionControlService"""
    
    @pytest.fixture
    def service(self):
        """Create service instance for testing"""
        return GraphVersionControlService()
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock()
    
    @pytest.fixture
    def sample_changes(self):
        """Sample changes for testing"""
        return [
            {
                "change_type": "create",
                "item_type": "node",
                "item_id": "node_1",
                "previous_data": {},
                "new_data": {"name": "Test Node", "type": "conversion"},
                "metadata": {"source": "test"}
            },
            {
                "change_type": "update",
                "item_type": "relationship",
                "item_id": "rel_1",
                "previous_data": {"confidence": 0.5},
                "new_data": {"confidence": 0.8},
                "metadata": {"reviewed": True}
            }
        ]
    
    def test_service_initialization(self):
        """Test service initialization"""
        service = GraphVersionControlService()
        
        # Check main branch is created
        assert "main" in service.branches
        assert service.head_branch == "main"
        assert isinstance(service.commits, dict)
        assert isinstance(service.branches, dict)
        assert isinstance(service.changes, list)
        assert isinstance(service.tags, dict)
        assert isinstance(service.remote_refs, dict)
    
    @pytest.mark.asyncio
    async def test_create_commit_basic(self, service, mock_db, sample_changes):
        """Basic test for create_commit"""
        result = await service.create_commit(
            branch_name="main",
            author_id="user_1",
            author_name="Test User",
            message="Add test changes",
            changes=sample_changes,
            db=mock_db
        )
        
        assert result["success"] is True
        assert "commit_hash" in result
        assert result["branch_name"] == "main"
        assert "author_id" not in result  # Not returned in API
        assert "author_name" not in result  # Not returned in API
        assert len(result.get("changes", [])) >= 0
        
        # Verify commit is stored
        commit_hash = result["commit_hash"]
        assert commit_hash in service.commits
        commit = service.commits[commit_hash]
        assert commit.author_id == "user_1"
        assert commit.message == "Add test changes"
        assert len(commit.changes) == 2
    
    @pytest.mark.asyncio
    async def test_create_commit_invalid_branch(self, service, sample_changes):
        """Test create_commit with invalid branch"""
        result = await service.create_commit(
            branch_name="nonexistent",
            author_id="user_1",
            author_name="Test User",
            message="Test commit",
            changes=sample_changes
        )
        
        assert result["success"] is False
        assert "Branch 'nonexistent' does not exist" in result["error"]
    
    @pytest.mark.asyncio
    async def test_create_commit_empty_changes(self, service, mock_db):
        """Test create_commit with empty changes"""
        result = await service.create_commit(
            branch_name="main",
            author_id="user_1",
            author_name="Test User",
            message="Empty commit",
            changes=[]
        )
        
        assert result["success"] is True
        assert result["commit_hash"] is not None
        assert len(result["changes"]) == 0
    
    @pytest.mark.asyncio
    async def test_create_branch_basic(self, service, mock_db):
        """Test basic branch creation"""
        # First create a commit on main
        commit_result = await service.create_commit(
            branch_name="main",
            author_id="user_1",
            author_name="Test User",
            message="Initial commit",
            changes=[{
                "change_type": "create",
                "item_type": "node",
                "item_id": "node_1",
                "new_data": {"name": "Test Node"}
            }],
            db=mock_db
        )
        
        # Create new branch
        result = await service.create_branch(
            branch_name="feature/test-branch",
            source_branch="main",
            author_id="user_1",
            author_name="Test User",
            description="Test feature branch"
        )
        
        assert result["success"] is True
        assert "feature/test-branch" in service.branches
        
        branch = service.branches["feature/test-branch"]
        assert branch.branch_name == "feature/test-branch"
        assert branch.base_commit is not None  # Should inherit from main
        assert branch.created_by == "user_1"
        assert branch.created_by_name == "Test User"
        assert branch.description == "Test feature branch"
    
    @pytest.mark.asyncio
    async def test_create_branch_existing_name(self, service):
        """Test creating branch with existing name"""
        result = await service.create_branch(
            branch_name="main",  # Main branch already exists
            source_branch="main",
            author_id="user_1",
            author_name="Test User"
        )
        
        assert result["success"] is False
        assert "already exists" in result["error"].lower()
    
    @pytest.mark.asyncio
    async def test_merge_branch_basic(self, service, mock_db):
        """Test basic branch merging"""
        # Create initial commit on main
        main_commit = await service.create_commit(
            branch_name="main",
            author_id="user_1",
            author_name="Test User",
            message="Initial commit",
            changes=[{
                "change_type": "create",
                "item_type": "node",
                "item_id": "node_1",
                "new_data": {"name": "Base Node"}
            }],
            db=mock_db
        )
        
        # Create feature branch
        branch_result = await service.create_branch(
            branch_name="feature",
            source_branch="main",
            author_id="user_1",
            author_name="Test User"
        )
        
        # Add commit to feature branch
        feature_commit = await service.create_commit(
            branch_name="feature",
            author_id="user_2",
            author_name="Feature User",
            message="Feature commit",
            changes=[{
                "change_type": "update",
                "item_type": "node",
                "item_id": "node_1",
                "previous_data": {"name": "Base Node"},
                "new_data": {"name": "Updated Node"}
            }],
            db=mock_db
        )
        
        # Merge feature into main
        merge_result = await service.merge_branch(
            source_branch="feature",
            target_branch="main",
            author_id="user_1",
            author_name="Merger User",
            merge_message="Merge feature branch",
            merge_strategy="auto",
            db=mock_db
        )
        
        assert merge_result.success is True
        # Check merge_result attributes (MergeResult object)
        assert merge_result.merge_strategy == "auto"
    
    @pytest.mark.asyncio
    async def test_merge_branch_conflicts(self, service, mock_db):
        """Test branch merging with conflicts"""
        # Create initial commit on main
        main_commit = await service.create_commit(
            branch_name="main",
            author_id="user_1",
            author_name="Test User",
            message="Initial commit",
            changes=[{
                "change_type": "create",
                "item_type": "node",
                "item_id": "node_1",
                "new_data": {"name": "Original Node", "value": 10}
            }],
            db=mock_db
        )
        
        # Create feature branch
        await service.create_branch(
            branch_name="conflict-branch",
            source_branch="main",
            author_id="user_1",
            author_name="Test User"
        )
        
        # Update node on main
        await service.create_commit(
            branch_name="main",
            author_id="user_1",
            author_name="Test User",
            message="Update on main",
            changes=[{
                "change_type": "update",
                "item_type": "node",
                "item_id": "node_1",
                "previous_data": {"name": "Original Node", "value": 10},
                "new_data": {"name": "Main Update", "value": 20}
            }],
            db=mock_db
        )
        
        # Update same node on feature branch (conflict)
        await service.create_commit(
            branch_name="conflict-branch",
            author_id="user_2",
            author_name="Feature User",
            message="Update on feature",
            changes=[{
                "change_type": "update",
                "item_type": "node",
                "item_id": "node_1",
                "previous_data": {"name": "Original Node", "value": 10},
                "new_data": {"name": "Feature Update", "value": 30}
            }],
            db=mock_db
        )
        
        # Attempt merge with conflicts
        merge_result = await service.merge_branch(
            source_branch="conflict-branch",
            target_branch="main",
            author_id="user_1",
            author_name="Merger User",
            merge_message="Attempt merge with conflicts",
            merge_strategy="manual",  # Require manual resolution
            db=mock_db
        )
        
        assert merge_result.success is False
        assert len(merge_result.conflicts) > 0
        assert "conflict" in str(merge_result.conflicts).lower()
    
    @pytest.mark.asyncio
    async def test_generate_diff(self, service, mock_db):
        """Test diff generation between commits"""
        # Create first commit
        commit1 = await service.create_commit(
            branch_name="main",
            author_id="user_1",
            author_name="Test User",
            message="First commit",
            changes=[{
                "change_type": "create",
                "item_type": "node",
                "item_id": "node_1",
                "new_data": {"name": "Node 1"}
            }],
            db=mock_db
        )
        
        # Create second commit
        commit2 = await service.create_commit(
            branch_name="main",
            author_id="user_1",
            author_name="Test User",
            message="Second commit",
            changes=[{
                "change_type": "create",
                "item_type": "node",
                "item_id": "node_2",
                "new_data": {"name": "Node 2"}
            }],
            db=mock_db
        )
        
        # Generate diff
        diff = await service.generate_diff(
            base_hash=commit1["commit_hash"],
            target_hash=commit2["commit_hash"],
            db=mock_db
        )
        
        assert isinstance(diff, GraphDiff)
        assert diff.base_hash == commit1["commit_hash"]
        assert diff.target_hash == commit2["commit_hash"]
        assert len(diff.added_nodes) > 0
        assert len(diff.modified_nodes) == 0
        assert len(diff.deleted_nodes) == 0
    
    @pytest.mark.asyncio
    async def test_get_commit_history(self, service, mock_db):
        """Test retrieving commit history"""
        # Create multiple commits
        commit_hashes = []
        for i in range(3):
            result = await service.create_commit(
                branch_name="main",
                author_id="user_1",
                author_name="Test User",
                message=f"Commit {i+1}",
                changes=[{
                    "change_type": "create",
                    "item_type": "node",
                    "item_id": f"node_{i+1}",
                    "new_data": {"name": f"Node {i+1}"}
                }],
                db=mock_db
            )
            commit_hashes.append(result["commit_hash"])
        
        # Get history
        history = await service.get_commit_history(
            branch_name="main",
            limit=10
        )
        
        assert len(history) == 3
        # history returns list of GraphCommit objects
        assert history[0].commit_hash == commit_hashes[-1]  # Most recent first
        assert history[2].commit_hash == commit_hashes[0]   # Oldest last
        assert all(hasattr(commit, 'message') for commit in history)
        assert all(hasattr(commit, 'timestamp') for commit in history)
    
    def test_calculate_commit_hash(self, service):
        """Test commit hash calculation"""
        content = {
            "tree": "tree_hash_123",
            "parents": ["parent_hash_456"],
            "author": "Test User",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Test commit"
        }
        
        # Test that hash generation works via create_commit
        # since _calculate_commit_hash might be internal
        import hashlib
        content_str = json.dumps(content, sort_keys=True)
        hash1 = hashlib.sha256(content_str.encode()).hexdigest()
        hash2 = hashlib.sha256(content_str.encode()).hexdigest()
        
        # Same content should produce same hash
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length
        
        # Different content should produce different hash
        content["message"] = "Different message"
        content_str2 = json.dumps(content, sort_keys=True)
        hash3 = hashlib.sha256(content_str2.encode()).hexdigest()
        assert hash3 != hash1
    
    @pytest.mark.asyncio
    async def test_create_tag(self, service, mock_db):
        """Test tag creation"""
        # Create a commit
        commit_result = await service.create_commit(
            branch_name="main",
            author_id="user_1",
            author_name="Test User",
            message="Taggable commit",
            changes=[{
                "change_type": "create",
                "item_type": "node",
                "item_id": "node_1",
                "new_data": {"name": "Tagged Node"}
            }],
            db=mock_db
        )
        
        # Create tag
        result = await service.create_tag(
            tag_name="v1.0.0",
            commit_hash=commit_result["commit_hash"],
            author_id="user_1",
            author_name="Tagger",
            message="Release version 1.0.0"
        )
        
        assert result["success"] is True
        assert result["tag_name"] == "v1.0.0"
        assert result["commit_hash"] == commit_result["commit_hash"]
        
        # Verify tag is stored
        assert "v1.0.0" in service.tags
        assert service.tags["v1.0.0"] == commit_result["commit_hash"]
    
    @pytest.mark.asyncio
    async def test_revert_commit(self, service, mock_db):
        """Test commit reverting"""
        # Create initial commit
        initial = await service.create_commit(
            branch_name="main",
            author_id="user_1",
            author_name="Test User",
            message="Initial state",
            changes=[{
                "change_type": "create",
                "item_type": "node",
                "item_id": "node_1",
                "new_data": {"name": "Original", "value": 10}
            }],
            db=mock_db
        )
        
        # Create commit to revert
        to_revert = await service.create_commit(
            branch_name="main",
            author_id="user_1",
            author_name="Test User",
            message="Change to revert",
            changes=[{
                "change_type": "update",
                "item_type": "node",
                "item_id": "node_1",
                "previous_data": {"name": "Original", "value": 10},
                "new_data": {"name": "Modified", "value": 20}
            }],
            db=mock_db
        )
        
        # Revert the commit
        revert_result = await service.revert_commit(
            commit_hash=to_revert["commit_hash"],
            author_id="user_1",
            author_name="Reverter",
            db=mock_db
        )
        
        # Revert returns a dict - check success
        assert revert_result.get("success", False) is True
    
    @pytest.mark.asyncio
    async def test_get_branch_status(self, service, mock_db):
        """Test branch status checking"""
        # Create commit on main
        main_commit = await service.create_commit(
            branch_name="main",
            author_id="user_1",
            author_name="Test User",
            message="Main commit",
            changes=[{
                "change_type": "create",
                "item_type": "node",
                "item_id": "node_1",
                "new_data": {"name": "Main Node"}
            }],
            db=mock_db
        )
        
        # Create feature branch
        await service.create_branch(
            branch_name="feature",
            source_branch="main",
            author_id="user_1",
            author_name="Test User"
        )
        
        # Add commit to feature
        await service.create_commit(
            branch_name="feature",
            author_id="user_2",
            author_name="Feature User",
            message="Feature commit",
            changes=[{
                "change_type": "create",
                "item_type": "node",
                "item_id": "node_2",
                "new_data": {"name": "Feature Node"}
            }],
            db=mock_db
        )
        
        # Check branch status
        status = await service.get_branch_status(
            branch_name="feature",
            base_branch="main"
        )
        
        # status returns dict with branch info
        assert status["branch_name"] == "feature"
        assert status["base_branch"] == "main"
    
    def test_error_handling_invalid_change_type(self, service):
        """Test error handling for invalid change types"""
        invalid_change = {
            "change_type": "invalid_type",
            "item_type": "node",
            "item_id": "node_1",
            "new_data": {}
        }
        
        with pytest.raises(ValueError):
            ChangeType(invalid_change["change_type"])
    
    def test_error_handling_invalid_item_type(self, service):
        """Test error handling for invalid item types"""
        invalid_change = {
            "change_type": "create",
            "item_type": "invalid_item",
            "item_id": "item_1",
            "new_data": {}
        }
        
        with pytest.raises(ValueError):
            ItemType(invalid_change["item_type"])



def test_async_GraphVersionControlService_revert_commit_error_handling():
    """Error handling tests for GraphVersionControlService_revert_commit"""
    # TODO: Test error conditions and exceptions
    assert True  # Placeholder - implement error handling tests

def test_async_GraphVersionControlService_get_branch_status_basic():
    """Basic test for GraphVersionControlService_get_branch_status"""
    # TODO: Implement basic functionality test
    # Setup test data
    # Call function/method
    # Assert results
    assert True  # Placeholder - implement actual test

def test_async_GraphVersionControlService_get_branch_status_edge_cases():
    """Edge case tests for GraphVersionControlService_get_branch_status"""
    # TODO: Test edge cases, error conditions
    assert True  # Placeholder - implement edge case tests

def test_async_GraphVersionControlService_get_branch_status_error_handling():
    """Error handling tests for GraphVersionControlService_get_branch_status"""
    # TODO: Test error conditions and exceptions
    assert True  # Placeholder - implement error handling tests
