"""
Comprehensive tests for version_control.py API endpoints

This test suite covers all endpoints in the version control API with:
- Unit tests for all endpoint functions
- Mock dependencies for isolated testing
- Edge cases and error handling
- 100% code coverage target
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from fastapi import HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List

# Import the API module
from src.api.version_control import (
    router,
    create_commit,
    get_commit,
    get_commit_changes,
    create_branch,
    get_branches,
    get_branch,
    get_branch_history,
    get_branch_status,
    merge_branch,
    generate_diff,
    revert_commit,
    create_tag,
    get_tags,
    get_tag,
    get_version_control_status,
    get_version_control_stats,
    search_commits,
    get_changelog
)

# Import service classes for mocking
from src.services.graph_version_control import (
    GraphChange,
    GraphBranch,
    GraphCommit,
    GraphDiff,
    ChangeType,
    ItemType
)


class TestCommitEndpoints:
    """Test commit-related endpoints"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_service(self):
        """Mock version control service"""
        with patch('src.api.version_control.graph_version_control_service') as mock:
            yield mock
    
    @pytest.fixture
    def sample_commit_data(self):
        """Sample commit data for testing"""
        return {
            "branch_name": "main",
            "author_id": "user123",
            "author_name": "Test User",
            "message": "Test commit",
            "changes": [
                {
                    "change_type": "add",
                    "item_type": "node",
                    "item_id": "node1",
                    "new_data": {"name": "test node"}
                }
            ],
            "parent_commits": ["parent123"]
        }
    
    @pytest.mark.asyncio
    async def test_create_commit_success(self, mock_db, mock_service, sample_commit_data):
        """Test successful commit creation"""
        # Setup mock response
        mock_service.create_commit = AsyncMock(return_value={
            "success": True,
            "commit_hash": "abc123",
            "branch_name": "main",
            "message": "Test commit",
            "changes_count": 1
        })
        
        # Call the endpoint
        result = await create_commit(sample_commit_data, mock_db)
        
        # Verify service was called correctly
        mock_service.create_commit.assert_called_once_with(
            "main", "user123", "Test User", "Test commit",
            sample_commit_data["changes"], ["parent123"], mock_db
        )
        
        # Verify response
        assert result["success"] is True
        assert result["commit_hash"] == "abc123"
        assert result["message"] == "Test commit"
    
    @pytest.mark.asyncio
    async def test_create_commit_missing_fields(self, mock_db, mock_service):
        """Test commit creation with missing required fields"""
        commit_data = {
            "branch_name": "main",
            "author_id": "user123"
            # Missing author_name and message
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await create_commit(commit_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "author_id, author_name, and message are required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_commit_service_error(self, mock_db, mock_service, sample_commit_data):
        """Test commit creation with service error"""
        mock_service.create_commit.return_value = {
            "success": False,
            "error": "Branch not found"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await create_commit(sample_commit_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Branch not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_commit_unexpected_error(self, mock_db, mock_service, sample_commit_data):
        """Test commit creation with unexpected error"""
        mock_service.create_commit.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            await create_commit(sample_commit_data, mock_db)
        
        assert exc_info.value.status_code == 500
        assert "Commit creation failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_commit_success(self, mock_service):
        """Test successful commit retrieval"""
        # Setup mock commit
        mock_change = Mock()
        mock_change.change_id = "change1"
        mock_change.change_type.value = "create"
        mock_change.item_type.value = "node"
        mock_change.item_id = "node1"
        mock_change.previous_data = {}
        mock_change.new_data = {"name": "test"}
        mock_change.metadata = {}
        
        mock_commit = Mock()
        mock_commit.commit_hash = "abc123"
        mock_commit.author_name = "Test User"
        mock_commit.timestamp = datetime.now()
        mock_commit.message = "Test commit"
        mock_commit.branch_name = "main"
        mock_commit.parent_commits = ["parent123"]
        mock_commit.tree_hash = "tree123"
        mock_commit.changes = [mock_change]
        mock_commit.metadata = {}
        
        mock_service.commits = {"abc123": mock_commit}
        
        # Call the endpoint
        result = await get_commit("abc123")
        
        # Verify response
        assert result["success"] is True
        assert result["commit"]["hash"] == "abc123"
        assert result["commit"]["author"] == "Test User"
        assert result["commit"]["message"] == "Test commit"
        assert len(result["commit"]["changes"]) == 1
        assert result["commit"]["changes"][0]["change_id"] == "change1"
        assert result["commit"]["changes"][0]["change_type"] == "create"
    
    @pytest.mark.asyncio
    async def test_get_commit_not_found(self, mock_service):
        """Test getting non-existent commit"""
        mock_service.commits = {}
        
        with pytest.raises(HTTPException) as exc_info:
            await get_commit("nonexistent")
        
        assert exc_info.value.status_code == 404
        assert "Commit not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_commit_changes_success(self, mock_service):
        """Test successful commit changes retrieval"""
        # Setup mock change
        mock_change = Mock()
        mock_change.change_id = "change1"
        mock_change.change_type.value = "create"
        mock_change.item_type.value = "node"
        mock_change.item_id = "node1"
        mock_change.author_name = "Test User"
        mock_change.timestamp = datetime.now()
        mock_change.branch_name = "main"
        mock_change.previous_data = {}
        mock_change.new_data = {"name": "test"}
        mock_change.metadata = {}
        
        mock_commit = Mock()
        mock_commit.changes = [mock_change]
        
        mock_service.commits = {"abc123": mock_commit}
        
        # Call the endpoint
        result = await get_commit_changes("abc123")
        
        # Verify response
        assert result["success"] is True
        assert result["commit_hash"] == "abc123"
        assert len(result["changes"]) == 1
        assert result["total_changes"] == 1
        assert result["changes"][0]["change_id"] == "change1"
        assert result["changes"][0]["author"] == "Test User"
    
    @pytest.mark.asyncio
    async def test_get_commit_changes_not_found(self, mock_service):
        """Test getting changes for non-existent commit"""
        mock_service.commits = {}
        
        with pytest.raises(HTTPException) as exc_info:
            await get_commit_changes("nonexistent")
        
        assert exc_info.value.status_code == 404
        assert "Commit not found" in str(exc_info.value.detail)


class TestBranchEndpoints:
    """Test branch-related endpoints"""
    
    @pytest.fixture
    def mock_service(self):
        """Mock version control service"""
        with patch('src.api.version_control.graph_version_control_service') as mock:
            yield mock
    
    @pytest.fixture
    def sample_branch_data(self):
        """Sample branch data for testing"""
        return {
            "branch_name": "feature-branch",
            "source_branch": "main",
            "author_id": "user123",
            "author_name": "Test User",
            "description": "Test feature branch"
        }
    
    @pytest.mark.asyncio
    async def test_create_branch_success(self, mock_service, sample_branch_data):
        """Test successful branch creation"""
        mock_service.create_branch.return_value = {
            "success": True,
            "branch_name": "feature-branch",
            "head_commit": "commit123",
            "created_at": datetime.now().isoformat()
        }
        
        result = await create_branch(sample_branch_data)
        
        mock_service.create_branch.assert_called_once_with(
            "feature-branch", "main", "user123", "Test User", "Test feature branch"
        )
        
        assert result["success"] is True
        assert result["branch_name"] == "feature-branch"
    
    @pytest.mark.asyncio
    async def test_create_branch_missing_fields(self, mock_service):
        """Test branch creation with missing required fields"""
        branch_data = {
            "branch_name": "feature-branch"
            # Missing author_id and author_name
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await create_branch(branch_data)
        
        assert exc_info.value.status_code == 400
        assert "branch_name, author_id, and author_name are required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_branch_service_error(self, mock_service, sample_branch_data):
        """Test branch creation with service error"""
        mock_service.create_branch.return_value = {
            "success": False,
            "error": "Branch already exists"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await create_branch(sample_branch_data)
        
        assert exc_info.value.status_code == 400
        assert "Branch already exists" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_branches_success(self, mock_service):
        """Test successful branches retrieval"""
        # Setup mock branches
        mock_branch1 = Mock()
        mock_branch1.created_at = datetime.now() - timedelta(days=1)
        mock_branch1.created_by_name = "User1"
        mock_branch1.head_commit = "commit1"
        mock_branch1.base_commit = "base1"
        mock_branch1.is_protected = False
        mock_branch1.description = "Main branch"
        mock_branch1.metadata = {}
        
        mock_branch2 = Mock()
        mock_branch2.created_at = datetime.now()
        mock_branch2.created_by_name = "User2"
        mock_branch2.head_commit = "commit2"
        mock_branch2.base_commit = "base2"
        mock_branch2.is_protected = True
        mock_branch2.description = "Protected branch"
        mock_branch2.metadata = {}
        
        mock_service.branches = {
            "main": mock_branch1,
            "protected": mock_branch2
        }
        mock_service.head_branch = "main"
        
        result = await get_branches()
        
        assert result["success"] is True
        assert len(result["branches"]) == 2
        assert result["total_branches"] == 2
        assert result["default_branch"] == "main"
        
        # Check sorting (newest first)
        assert result["branches"][0]["name"] == "protected"  # Created later
        assert result["branches"][1]["name"] == "main"
    
    @pytest.mark.asyncio
    async def test_get_branch_success(self, mock_service):
        """Test successful branch retrieval"""
        mock_branch = Mock()
        mock_branch.created_at = datetime.now()
        mock_branch.created_by_name = "Test User"
        mock_branch.head_commit = "commit123"
        mock_branch.base_commit = "base123"
        mock_branch.is_protected = False
        mock_branch.description = "Test branch"
        mock_branch.metadata = {}
        
        mock_service.branches = {"main": mock_branch}
        
        result = await get_branch("main")
        
        assert result["success"] is True
        assert result["branch"]["name"] == "main"
        assert result["branch"]["created_by"] == "Test User"
        assert result["branch"]["head_commit"] == "commit123"
        assert result["branch"]["is_protected"] is False
    
    @pytest.mark.asyncio
    async def test_get_branch_not_found(self, mock_service):
        """Test getting non-existent branch"""
        mock_service.branches = {}
        
        with pytest.raises(HTTPException) as exc_info:
            await get_branch("nonexistent")
        
        assert exc_info.value.status_code == 404
        assert "Branch not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_branch_history_success(self, mock_service):
        """Test successful branch history retrieval"""
        mock_service.get_commit_history.return_value = {
            "success": True,
            "commits": [
                {
                    "hash": "commit1",
                    "author": "User1",
                    "timestamp": "2023-01-01T00:00:00",
                    "message": "First commit"
                }
            ],
            "total_commits": 1
        }
        
        result = await get_branch_history("main", 50, None, None)
        
        mock_service.get_commit_history.assert_called_once_with("main", 50, None, None)
        
        assert result["success"] is True
        assert len(result["commits"]) == 1
        assert result["total_commits"] == 1
    
    @pytest.mark.asyncio
    async def test_get_branch_history_service_error(self, mock_service):
        """Test branch history retrieval with service error"""
        mock_service.get_commit_history.return_value = {
            "success": False,
            "error": "Branch not found"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_branch_history("nonexistent")
        
        assert exc_info.value.status_code == 400
        assert "Branch not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_branch_status_success(self, mock_service):
        """Test successful branch status retrieval"""
        mock_service.get_branch_status.return_value = {
            "success": True,
            "status": {
                "ahead": 5,
                "behind": 2,
                "uncommitted_changes": 3
            }
        }
        
        result = await get_branch_status("main")
        
        mock_service.get_branch_status.assert_called_once_with("main")
        
        assert result["success"] is True
        assert result["status"]["ahead"] == 5
        assert result["status"]["behind"] == 2
    
    @pytest.mark.asyncio
    async def test_get_branch_status_service_error(self, mock_service):
        """Test branch status retrieval with service error"""
        mock_service.get_branch_status.return_value = {
            "success": False,
            "error": "Branch not found"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_branch_status("nonexistent")
        
        assert exc_info.value.status_code == 400
        assert "Branch not found" in str(exc_info.value.detail)


class TestMergeEndpoints:
    """Test merge-related endpoints"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_service(self):
        """Mock version control service"""
        with patch('src.api.version_control.graph_version_control_service') as mock:
            yield mock
    
    @pytest.fixture
    def sample_merge_data(self):
        """Sample merge data for testing"""
        return {
            "target_branch": "main",
            "author_id": "user123",
            "author_name": "Test User",
            "merge_message": "Merge feature branch",
            "merge_strategy": "merge_commit"
        }
    
    @pytest.mark.asyncio
    async def test_merge_branch_success(self, mock_db, mock_service, sample_merge_data):
        """Test successful branch merge"""
        # Setup mock merge result
        mock_merge_result = Mock()
        mock_merge_result.success = True
        mock_merge_result.merge_commit_hash = "merge123"
        mock_merge_result.resolved_conflicts = []
        mock_merge_result.conflicts = []
        mock_merge_result.merge_strategy = "merge_commit"
        mock_merge_result.merged_changes = []
        mock_merge_result.message = "Merge completed successfully"
        
        mock_service.merge_branch.return_value = mock_merge_result
        
        result = await merge_branch("feature-branch", sample_merge_data, mock_db)
        
        mock_service.merge_branch.assert_called_once_with(
            "feature-branch", "main", "user123", "Test User",
            "Merge feature branch", "merge_commit", mock_db
        )
        
        assert result["success"] is True
        assert result["merge_result"]["merge_commit_hash"] == "merge123"
        assert result["merge_result"]["conflicts_resolved"] == 0
        assert result["merge_result"]["remaining_conflicts"] == 0
    
    @pytest.mark.asyncio
    async def test_merge_branch_missing_fields(self, mock_db, mock_service):
        """Test branch merge with missing required fields"""
        merge_data = {
            "target_branch": "main"
            # Missing author_id and author_name
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await merge_branch("feature-branch", merge_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "target_branch, author_id, and author_name are required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_merge_branch_with_conflicts(self, mock_db, mock_service, sample_merge_data):
        """Test branch merge with conflicts"""
        # Setup mock merge result with conflicts
        mock_conflict = Mock()
        mock_conflict.get.return_value = "Conflict in node data"
        
        mock_merge_result = Mock()
        mock_merge_result.success = False
        mock_merge_result.conflicts = [mock_conflict]
        
        mock_service.merge_branch.return_value = mock_merge_result
        
        with pytest.raises(HTTPException) as exc_info:
            await merge_branch("feature-branch", sample_merge_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Merge failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_merge_branch_unexpected_error(self, mock_db, mock_service, sample_merge_data):
        """Test branch merge with unexpected error"""
        mock_service.merge_branch.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            await merge_branch("feature-branch", sample_merge_data, mock_db)
        
        assert exc_info.value.status_code == 500
        assert "Branch merge failed" in str(exc_info.value.detail)


class TestDiffEndpoints:
    """Test diff-related endpoints"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_service(self):
        """Mock version control service"""
        with patch('src.api.version_control.graph_version_control_service') as mock:
            yield mock
    
    @pytest.fixture
    def sample_diff_data(self):
        """Sample diff data for testing"""
        return {
            "base_hash": "commit123",
            "target_hash": "commit456",
            "item_types": ["node", "relationship"]
        }
    
    @pytest.mark.asyncio
    async def test_generate_diff_success(self, mock_db, mock_service, sample_diff_data):
        """Test successful diff generation"""
        # Setup mock diff
        mock_diff = Mock()
        mock_diff.base_hash = "commit123"
        mock_diff.target_hash = "commit456"
        mock_diff.added_nodes = [{"id": "node1", "name": "New node"}]
        mock_diff.modified_nodes = [{"id": "node2", "name": "Modified node"}]
        mock_diff.deleted_nodes = [{"id": "node3", "name": "Deleted node"}]
        mock_diff.added_relationships = []
        mock_diff.modified_relationships = []
        mock_diff.deleted_relationships = []
        mock_diff.added_patterns = []
        mock_diff.modified_patterns = []
        mock_diff.deleted_patterns = []
        mock_diff.conflicts = []
        mock_diff.metadata = {}
        
        mock_service.generate_diff.return_value = mock_diff
        
        result = await generate_diff(sample_diff_data, mock_db)
        
        mock_service.generate_diff.assert_called_once_with(
            "commit123", "commit456", ["node", "relationship"], mock_db
        )
        
        assert result["success"] is True
        assert result["diff"]["base_hash"] == "commit123"
        assert result["diff"]["target_hash"] == "commit456"
        assert result["diff"]["summary"]["added_nodes"] == 1
        assert result["diff"]["summary"]["modified_nodes"] == 1
        assert result["diff"]["summary"]["deleted_nodes"] == 1
        assert result["diff"]["summary"]["total_changes"] == 3
    
    @pytest.mark.asyncio
    async def test_generate_diff_missing_fields(self, mock_db, mock_service):
        """Test diff generation with missing required fields"""
        diff_data = {
            "base_hash": "commit123"
            # Missing target_hash
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await generate_diff(diff_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "base_hash and target_hash are required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_generate_diff_unexpected_error(self, mock_db, mock_service, sample_diff_data):
        """Test diff generation with unexpected error"""
        mock_service.generate_diff.side_effect = Exception("Diff generation error")
        
        with pytest.raises(HTTPException) as exc_info:
            await generate_diff(sample_diff_data, mock_db)
        
        assert exc_info.value.status_code == 500
        assert "Diff generation failed" in str(exc_info.value.detail)


class TestRevertEndpoints:
    """Test revert-related endpoints"""
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def mock_service(self):
        """Mock version control service"""
        with patch('src.api.version_control.graph_version_control_service') as mock:
            yield mock
    
    @pytest.fixture
    def sample_revert_data(self):
        """Sample revert data for testing"""
        return {
            "author_id": "user123",
            "author_name": "Test User",
            "revert_message": "Revert problematic commit",
            "branch_name": "main"
        }
    
    @pytest.mark.asyncio
    async def test_revert_commit_success(self, mock_db, mock_service, sample_revert_data):
        """Test successful commit revert"""
        mock_service.revert_commit.return_value = {
            "success": True,
            "revert_commit_hash": "revert123",
            "original_commit": "commit456",
            "message": "Commit reverted successfully"
        }
        
        result = await revert_commit("commit456", sample_revert_data, mock_db)
        
        mock_service.revert_commit.assert_called_once_with(
            "commit456", "user123", "Test User", "Revert problematic commit", "main", mock_db
        )
        
        assert result["success"] is True
        assert result["revert_commit_hash"] == "revert123"
        assert result["original_commit"] == "commit456"
    
    @pytest.mark.asyncio
    async def test_revert_commit_missing_fields(self, mock_db, mock_service):
        """Test commit revert with missing required fields"""
        revert_data = {
            "author_id": "user123"
            # Missing author_name
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await revert_commit("commit456", revert_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "author_id and author_name are required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_revert_commit_service_error(self, mock_db, mock_service, sample_revert_data):
        """Test commit revert with service error"""
        mock_service.revert_commit.return_value = {
            "success": False,
            "error": "Commit not found"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await revert_commit("nonexistent", sample_revert_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Commit not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_revert_commit_unexpected_error(self, mock_db, mock_service, sample_revert_data):
        """Test commit revert with unexpected error"""
        mock_service.revert_commit.side_effect = Exception("Database error")
        
        with pytest.raises(HTTPException) as exc_info:
            await revert_commit("commit456", sample_revert_data, mock_db)
        
        assert exc_info.value.status_code == 500
        assert "Commit revert failed" in str(exc_info.value.detail)


class TestTagEndpoints:
    """Test tag-related endpoints"""
    
    @pytest.fixture
    def mock_service(self):
        """Mock version control service"""
        with patch('src.api.version_control.graph_version_control_service') as mock:
            yield mock
    
    @pytest.fixture
    def sample_tag_data(self):
        """Sample tag data for testing"""
        return {
            "tag_name": "v1.0.0",
            "commit_hash": "commit123",
            "author_id": "user123",
            "author_name": "Test User",
            "message": "Release version 1.0.0"
        }
    
    @pytest.mark.asyncio
    async def test_create_tag_success(self, mock_service, sample_tag_data):
        """Test successful tag creation"""
        mock_service.create_tag.return_value = {
            "success": True,
            "tag_name": "v1.0.0",
            "commit_hash": "commit123",
            "created_at": datetime.now().isoformat()
        }
        
        result = await create_tag(sample_tag_data)
        
        mock_service.create_tag.assert_called_once_with(
            "v1.0.0", "commit123", "user123", "Test User", "Release version 1.0.0"
        )
        
        assert result["success"] is True
        assert result["tag_name"] == "v1.0.0"
        assert result["commit_hash"] == "commit123"
    
    @pytest.mark.asyncio
    async def test_create_tag_missing_fields(self, mock_service):
        """Test tag creation with missing required fields"""
        tag_data = {
            "tag_name": "v1.0.0",
            "commit_hash": "commit123"
            # Missing author_id and author_name
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await create_tag(tag_data)
        
        assert exc_info.value.status_code == 400
        assert "tag_name, commit_hash, author_id, and author_name are required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_tag_service_error(self, mock_service, sample_tag_data):
        """Test tag creation with service error"""
        mock_service.create_tag.return_value = {
            "success": False,
            "error": "Tag already exists"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await create_tag(sample_tag_data)
        
        assert exc_info.value.status_code == 400
        assert "Tag already exists" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_tags_success(self, mock_service):
        """Test successful tags retrieval"""
        # Setup mock commits and tags
        mock_commit1 = Mock()
        mock_commit1.message = "Release commit 1"
        mock_commit1.author_name = "User1"
        mock_commit1.timestamp = datetime.now() - timedelta(days=1)
        
        mock_commit2 = Mock()
        mock_commit2.message = "Release commit 2"
        mock_commit2.author_name = "User2"
        mock_commit2.timestamp = datetime.now()
        
        mock_service.commits = {
            "commit123": mock_commit1,
            "commit456": mock_commit2
        }
        mock_service.tags = {
            "v1.0.0": "commit123",
            "v1.1.0": "commit456"
        }
        
        result = await get_tags()
        
        assert result["success"] is True
        assert len(result["tags"]) == 2
        assert result["total_tags"] == 2
        
        # Check sorting (newest first)
        assert result["tags"][0]["name"] == "v1.1.0"  # Created later
        assert result["tags"][1]["name"] == "v1.0.0"
    
    @pytest.mark.asyncio
    async def test_get_tags_empty(self, mock_service):
        """Test getting tags when none exist"""
        mock_service.commits = {}
        mock_service.tags = {}
        
        result = await get_tags()
        
        assert result["success"] is True
        assert len(result["tags"]) == 0
        assert result["total_tags"] == 0
    
    @pytest.mark.asyncio
    async def test_get_tag_success(self, mock_service):
        """Test successful tag retrieval"""
        # Setup mock commit
        mock_change = Mock()
        mock_commit = Mock()
        mock_commit.commit_hash = "commit123"
        mock_commit.author_name = "Test User"
        mock_commit.timestamp = datetime.now()
        mock_commit.message = "Release commit"
        mock_commit.tree_hash = "tree123"
        mock_commit.changes = [mock_change]
        
        mock_service.commits = {"commit123": mock_commit}
        mock_service.tags = {"v1.0.0": "commit123"}
        
        result = await get_tag("v1.0.0")
        
        assert result["success"] is True
        assert result["tag"]["name"] == "v1.0.0"
        assert result["tag"]["commit_hash"] == "commit123"
        assert result["tag"]["commit"]["hash"] == "commit123"
        assert result["tag"]["commit"]["author"] == "Test User"
        assert result["tag"]["commit"]["message"] == "Release commit"
        assert result["tag"]["commit"]["changes_count"] == 1
    
    @pytest.mark.asyncio
    async def test_get_tag_not_found(self, mock_service):
        """Test getting non-existent tag"""
        mock_service.tags = {}
        
        with pytest.raises(HTTPException) as exc_info:
            await get_tag("nonexistent")
        
        assert exc_info.value.status_code == 404
        assert "Tag not found" in str(exc_info.value.detail)


class TestUtilityEndpoints:
    """Test utility endpoints"""
    
    @pytest.fixture
    def mock_service(self):
        """Mock version control service"""
        with patch('src.api.version_control.graph_version_control_service') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_get_version_control_status_success(self, mock_service):
        """Test successful version control status retrieval"""
        # Setup mock data
        mock_branch = Mock()
        mock_branch.head_commit = "commit123"
        mock_branch.is_protected = False
        
        mock_commit = Mock()
        mock_commit.commit_hash = "commit1"
        mock_commit.author_name = "User1"
        mock_commit.timestamp = datetime.now()
        mock_commit.message = "Test commit 1"
        mock_commit.branch_name = "main"
        
        mock_commit2 = Mock()
        mock_commit2.commit_hash = "commit2"
        mock_commit2.author_name = "User2"
        mock_commit2.timestamp = datetime.now() - timedelta(hours=1)
        mock_commit2.message = "Test commit 2"
        mock_commit2.branch_name = "feature"
        
        mock_service.commits = {
            "commit1": mock_commit,
            "commit2": mock_commit2
        }
        mock_service.branches = {
            "main": mock_branch,
            "protected": Mock(is_protected=True)
        }
        mock_service.tags = {"v1.0.0": "commit1"}
        mock_service.head_branch = "main"
        
        result = await get_version_control_status()
        
        assert result["success"] is True
        assert result["status"]["total_commits"] == 2
        assert result["status"]["total_branches"] == 2
        assert result["status"]["total_tags"] == 1
        assert result["status"]["head_branch"] == "main"
        assert result["status"]["head_commit"] == "commit123"
        assert len(result["status"]["recent_commits"]) == 2
        assert len(result["status"]["protected_branches"]) == 1
    
    @pytest.mark.asyncio
    async def test_get_version_control_status_empty(self, mock_service):
        """Test version control status with no data"""
        mock_service.commits = {}
        mock_service.branches = {}
        mock_service.tags = {}
        mock_service.head_branch = None
        
        result = await get_version_control_status()
        
        assert result["success"] is True
        assert result["status"]["total_commits"] == 0
        assert result["status"]["total_branches"] == 0
        assert result["status"]["total_tags"] == 0
        assert result["status"]["head_branch"] is None
        assert result["status"]["head_commit"] is None
        assert len(result["status"]["recent_commits"]) == 0
        assert len(result["status"]["protected_branches"]) == 0
    
    @pytest.mark.asyncio
    async def test_get_version_control_stats_success(self, mock_service):
        """Test successful version control stats retrieval"""
        # Setup mock commits
        mock_change1 = Mock()
        mock_change1.change_type.value = "create"
        mock_change1.item_type.value = "node"
        
        mock_change2 = Mock()
        mock_change2.change_type.value = "update"
        mock_change2.item_type.value = "relationship"
        
        mock_commit1 = Mock()
        mock_commit1.author_name = "User1"
        mock_commit1.branch_name = "main"
        mock_commit1.changes = [mock_change1]
        mock_commit1.timestamp = datetime.now()
        
        mock_commit2 = Mock()
        mock_commit2.author_name = "User2"
        mock_commit2.branch_name = "feature"
        mock_commit2.changes = [mock_change2]
        mock_commit2.timestamp = datetime.now() - timedelta(days=1)
        
        mock_commit3 = Mock()
        mock_commit3.author_name = "User1"
        mock_commit3.branch_name = "main"
        mock_commit3.changes = [mock_change1]
        mock_commit3.timestamp = datetime.now() - timedelta(days=2)
        
        mock_service.commits = {
            "commit1": mock_commit1,
            "commit2": mock_commit2,
            "commit3": mock_commit3
        }
        mock_service.branches = {"main": Mock(), "feature": Mock()}
        mock_service.tags = {"v1.0.0": "commit1"}
        
        result = await get_version_control_stats()
        
        assert result["success"] is True
        assert result["stats"]["total_commits"] == 3
        assert result["stats"]["total_branches"] == 2
        assert result["stats"]["total_tags"] == 1
        
        # Check top authors
        assert len(result["stats"]["top_authors"]) == 2
        assert result["stats"]["top_authors"][0][0] == "User1"
        assert result["stats"]["top_authors"][0][1] == 2
        
        # Check active branches
        assert len(result["stats"]["active_branches"]) == 2
        assert result["stats"]["active_branches"][0][0] == "main"
        assert result["stats"]["active_branches"][0][1] == 2
        
        # Check change types
        assert "create_node" in result["stats"]["change_types"]
        assert "update_relationship" in result["stats"]["change_types"]
        
        # Check averages
        assert result["stats"]["average_commits_per_author"] == 1.5
        assert result["stats"]["average_commits_per_branch"] == 1.5
    
    @pytest.mark.asyncio
    async def test_get_version_control_stats_empty(self, mock_service):
        """Test version control stats with no data"""
        mock_service.commits = {}
        mock_service.branches = {}
        mock_service.tags = {}
        
        result = await get_version_control_stats()
        
        assert result["success"] is True
        assert result["stats"]["total_commits"] == 0
        assert result["stats"]["total_branches"] == 0
        assert result["stats"]["total_tags"] == 0
        assert len(result["stats"]["top_authors"]) == 0
        assert len(result["stats"]["active_branches"]) == 0
        assert result["stats"]["average_commits_per_author"] == 0
        assert result["stats"]["average_commits_per_branch"] == 0
    
    @pytest.mark.asyncio
    async def test_search_commits_success(self, mock_service):
        """Test successful commit search"""
        # Setup mock commits
        mock_change1 = Mock()
        mock_change1.new_data = {"name": "feature implementation"}
        
        mock_commit1 = Mock()
        mock_commit1.commit_hash = "commit1"
        mock_commit1.author_name = "User1"
        mock_commit1.timestamp = datetime.now()
        mock_commit1.message = "Add new feature"
        mock_commit1.branch_name = "main"
        mock_commit1.changes = [mock_change1]
        
        mock_commit2 = Mock()
        mock_commit2.commit_hash = "commit2"
        mock_commit2.author_name = "User2"
        mock_commit2.timestamp = datetime.now() - timedelta(hours=1)
        mock_commit2.message = "Fix bug in feature"
        mock_commit2.branch_name = "feature"
        mock_commit2.changes = []
        
        # Mock dict.values() to return our commits
        mock_service.commits = {
            "commit1": mock_commit1,
            "commit2": mock_commit2
        }
        
        # Mock the dict.values() method
        mock_service.commits.values.return_value = [mock_commit1, mock_commit2]
        
        result = await search_commits("feature", None, None, 50)
        
        assert result["success"] is True
        assert result["query"] == "feature"
        assert len(result["results"]) == 2  # Both commits match "feature"
        assert result["total_results"] == 2
        assert result["limit"] == 50
    
    @pytest.mark.asyncio
    async def test_search_commits_with_filters(self, mock_service):
        """Test commit search with author and branch filters"""
        # Setup mock commits
        mock_commit1 = Mock()
        mock_commit1.commit_hash = "commit1"
        mock_commit1.author_name = "User1"
        mock_commit1.timestamp = datetime.now()
        mock_commit1.message = "Test commit"
        mock_commit1.branch_name = "main"
        mock_commit1.changes = []
        
        mock_commit2 = Mock()
        mock_commit2.commit_hash = "commit2"
        mock_commit2.author_name = "User2"
        mock_commit2.timestamp = datetime.now() - timedelta(hours=1)
        mock_commit2.message = "Test commit"
        mock_commit2.branch_name = "feature"
        mock_commit2.changes = []
        
        mock_service.commits = {
            "commit1": mock_commit1,
            "commit2": mock_commit2
        }
        
        # Mock the dict.values() method
        mock_service.commits.values.return_value = [mock_commit1, mock_commit2]
        
        result = await search_commits("test", "User1", "main", 50)
        
        assert result["success"] is True
        assert result["query"] == "test"
        assert result["filters"]["author"] == "User1"
        assert result["filters"]["branch"] == "main"
        assert len(result["results"]) == 1  # Only User1's commit on main branch
        assert result["results"][0]["author"] == "User1"
        assert result["results"][0]["branch"] == "main"
    
    @pytest.mark.asyncio
    async def test_search_commits_no_matches(self, mock_service):
        """Test commit search with no matches"""
        mock_commit = Mock()
        mock_commit.commit_hash = "commit1"
        mock_commit.author_name = "User1"
        mock_commit.timestamp = datetime.now()
        mock_commit.message = "Test commit"
        mock_commit.branch_name = "main"
        mock_commit.changes = []
        
        mock_service.commits = {"commit1": mock_commit}
        mock_service.commits.values.return_value = [mock_commit]
        
        result = await search_commits("nonexistent", None, None, 50)
        
        assert result["success"] is True
        assert result["query"] == "nonexistent"
        assert len(result["results"]) == 0
        assert result["total_results"] == 0
    
    @pytest.mark.asyncio
    async def test_get_changelog_success(self, mock_service):
        """Test successful changelog generation"""
        # Setup mock commit history response
        mock_service.get_commit_history.return_value = {
            "success": True,
            "commits": [
                {
                    "timestamp": "2023-01-02T00:00:00",
                    "hash": "commit2",
                    "author": "User2",
                    "message": "Add feature B",
                    "changes_count": 2,
                    "changes": [
                        {
                            "change_type": "create",
                            "item_type": "node",
                            "change_id": "change2"
                        },
                        {
                            "change_type": "update",
                            "item_type": "relationship",
                            "change_id": "change3"
                        }
                    ]
                },
                {
                    "timestamp": "2023-01-01T00:00:00",
                    "hash": "commit1",
                    "author": "User1",
                    "message": "Add feature A",
                    "changes_count": 1,
                    "changes": [
                        {
                            "change_type": "create",
                            "item_type": "node",
                            "change_id": "change1"
                        }
                    ]
                }
            ]
        }
        
        result = await get_changelog("main", None, 100)
        
        mock_service.get_commit_history.assert_called_once_with("main", 100, None)
        
        assert result["success"] is True
        assert result["branch_name"] == "main"
        assert result["total_commits"] == 2
        
        # Check changelog grouped by date
        assert "2023-01-02" in result["changelog_by_date"]
        assert "2023-01-01" in result["changelog_by_date"]
        assert len(result["changelog_by_date"]["2023-01-02"]) == 1
        assert len(result["changelog_by_date"]["2023-01-01"]) == 1
        
        # Check summary
        assert result["summary"]["total_changes"] == 3
        assert result["summary"]["date_range"]["start"] == "2023-01-01"
        assert result["summary"]["date_range"]["end"] == "2023-01-02"
    
    @pytest.mark.asyncio
    async def test_get_changelog_service_error(self, mock_service):
        """Test changelog generation with service error"""
        mock_service.get_commit_history.return_value = {
            "success": False,
            "error": "Branch not found"
        }
        
        with pytest.raises(HTTPException) as exc_info:
            await get_changelog("nonexistent")
        
        assert exc_info.value.status_code == 400
        assert "Branch not found" in str(exc_info.value.detail)


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling across all endpoints"""
    
    @pytest.fixture
    def mock_service(self):
        """Mock version control service"""
        with patch('src.api.version_control.graph_version_control_service') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_large_payload_handling(self, mock_service):
        """Test handling of large payloads"""
        # Test with large commit data
        large_changes = [
            {
                "change_type": "add",
                "item_type": "node",
                "item_id": f"node_{i}",
                "new_data": {"name": f"Node {i}", "data": "x" * 1000}
            }
            for i in range(1000)
        ]
        
        mock_service.create_commit.return_value = {
            "success": True,
            "commit_hash": "large123",
            "changes_count": 1000
        }
        
        commit_data = {
            "branch_name": "main",
            "author_id": "user123",
            "author_name": "Test User",
            "message": "Large commit test",
            "changes": large_changes
        }
        
        result = await create_commit(commit_data, Mock())
        
        assert result["success"] is True
        assert result["changes_count"] == 1000
    
    @pytest.mark.asyncio
    async def test_unicode_and_special_characters(self, mock_service):
        """Test handling of unicode and special characters"""
        special_data = {
            "branch_name": "feature-测试",
            "author_id": "user_éñ",
            "author_name": "Üser Ñame",
            "message": "Commit with émoticons 🚀 and üñíçødé",
            "changes": [{
                "change_type": "add",
                "item_type": "node",
                "item_id": "node_特殊字符",
                "new_data": {"name": "Nodé wïth spëcial chars 💫", "description": "Descripción en español"}
            }]
        }
        
        mock_service.create_branch.return_value = {
            "success": True,
            "branch_name": "feature-测试"
        }
        
        result = await create_branch(special_data)
        
        assert result["success"] is True
        assert result["branch_name"] == "feature-测试"
    
    @pytest.mark.asyncio
    async def test_null_and_empty_values(self, mock_service):
        """Test handling of null and empty values"""
        # Test with null/empty values in optional fields
        commit_data = {
            "branch_name": "main",
            "author_id": "user123",
            "author_name": "Test User",
            "message": "Test commit",
            "changes": [],  # Empty changes
            "parent_commits": None  # Null parent commits
        }
        
        mock_service.create_commit.return_value = {
            "success": True,
            "commit_hash": "null123"
        }
        
        result = await create_commit(commit_data, Mock())
        
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, mock_service):
        """Test handling of concurrent requests"""
        import asyncio
        
        mock_service.create_commit.return_value = {
            "success": True,
            "commit_hash": "concurrent123"
        }
        
        commit_data = {
            "branch_name": "main",
            "author_id": "user123",
            "author_name": "Test User",
            "message": "Concurrent test",
            "changes": []
        }
        
        # Create multiple concurrent requests
        tasks = [
            create_commit(commit_data, Mock())
            for _ in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        assert all(result["success"] for result in results)
        assert len(results) == 10


# Test the router configuration
class TestRouterConfiguration:
    """Test router configuration and setup"""
    
    def test_router_prefix_and_tags(self):
        """Test router has correct prefix and tags"""
        # The router should be properly configured
        assert router is not None
        assert hasattr(router, 'routes')
    
    def test_route_endpoints_exist(self):
        """Test all expected endpoints exist"""
        route_paths = [route.path for route in router.routes]
        
        expected_paths = [
            "/commits",
            "/commits/{commit_hash}",
            "/commits/{commit_hash}/changes",
            "/branches",
            "/branches/{branch_name}",
            "/branches/{branch_name}/history",
            "/branches/{branch_name}/status",
            "/branches/{source_branch}/merge",
            "/diff",
            "/commits/{commit_hash}/revert",
            "/tags",
            "/tags/{tag_name}",
            "/status",
            "/stats",
            "/search",
            "/changelog"
        ]
        
        for path in expected_paths:
            assert path in route_paths, f"Missing endpoint: {path}"


# Integration-style tests (still using mocks but testing more complex flows)
class TestIntegrationFlows:
    """Test integration flows between endpoints"""
    
    @pytest.fixture
    def mock_service(self):
        """Mock version control service"""
        with patch('src.api.version_control.graph_version_control_service') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_complete_branch_merge_flow(self, mock_service):
        """Test complete flow: create branch -> commit -> merge -> get status"""
        # Setup mocks for each step
        mock_service.create_branch.return_value = {
            "success": True,
            "branch_name": "feature-branch"
        }
        
        mock_service.create_commit.return_value = {
            "success": True,
            "commit_hash": "commit123"
        }
        
        mock_merge_result = Mock()
        mock_merge_result.success = True
        mock_merge_result.merge_commit_hash = "merge123"
        mock_merge_result.resolved_conflicts = []
        mock_merge_result.conflicts = []
        mock_merge_result.merge_strategy = "merge_commit"
        mock_merge_result.merged_changes = []
        mock_merge_result.message = "Merge completed"
        
        mock_service.merge_branch.return_value = mock_merge_result
        
        # Execute flow
        branch_data = {
            "branch_name": "feature-branch",
            "source_branch": "main",
            "author_id": "user123",
            "author_name": "Test User"
        }
        
        commit_data = {
            "branch_name": "feature-branch",
            "author_id": "user123",
            "author_name": "Test User",
            "message": "Feature commit",
            "changes": []
        }
        
        merge_data = {
            "target_branch": "main",
            "author_id": "user123",
            "author_name": "Test User",
            "merge_message": "Merge feature"
        }
        
        # Step 1: Create branch
        branch_result = await create_branch(branch_data)
        assert branch_result["success"] is True
        
        # Step 2: Create commit
        commit_result = await create_commit(commit_data, Mock())
        assert commit_result["success"] is True
        
        # Step 3: Merge branch
        merge_result = await merge_branch("feature-branch", merge_data, Mock())
        assert merge_result["success"] is True
        assert merge_result["merge_result"]["merge_commit_hash"] == "merge123"
    
    @pytest.mark.asyncio
    async def test_complete_tag_release_flow(self, mock_service):
        """Test complete flow: commits -> tag -> get changelog"""
        # Setup mocks
        mock_service.get_commit_history.return_value = {
            "success": True,
            "commits": [
                {
                    "timestamp": "2023-01-02T00:00:00",
                    "hash": "commit2",
                    "author": "User2",
                    "message": "Release prep",
                    "changes_count": 1,
                    "changes": []
                },
                {
                    "timestamp": "2023-01-01T00:00:00",
                    "hash": "commit1",
                    "author": "User1",
                    "message": "Feature implementation",
                    "changes_count": 2,
                    "changes": []
                }
            ]
        }
        
        mock_service.create_tag.return_value = {
            "success": True,
            "tag_name": "v1.0.0",
            "commit_hash": "commit2"
        }
        
        # Execute flow
        tag_data = {
            "tag_name": "v1.0.0",
            "commit_hash": "commit2",
            "author_id": "user123",
            "author_name": "Release Manager",
            "message": "Release version 1.0.0"
        }
        
        # Step 1: Create tag
        tag_result = await create_tag(tag_data)
        assert tag_result["success"] is True
        
        # Step 2: Get changelog
        changelog_result = await get_changelog("main", None, 100)
        assert changelog_result["success"] is True
        assert changelog_result["total_commits"] == 2
        assert changelog_result["summary"]["total_changes"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=backend/src/api/version_control.py", "--cov-report=term-missing"])
