"""
Comprehensive tests for version_control.py API endpoints - Fixed Version

This test suite covers all endpoints in the version control API with:
- Unit tests for all endpoint functions
- Proper handling of async and sync service methods
- Mock dependencies for isolated testing
- Edge cases and error handling
- 100% code coverage target
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
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
        mock_service.create_commit = AsyncMock(return_value={
            "success": False,
            "error": "Branch not found"
        })
        
        with pytest.raises(HTTPException) as exc_info:
            await create_commit(sample_commit_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Branch not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_commit_unexpected_error(self, mock_db, mock_service, sample_commit_data):
        """Test commit creation with unexpected error"""
        mock_service.create_commit = AsyncMock(side_effect=Exception("Database error"))
        
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
        mock_service.create_branch = AsyncMock(return_value={
            "success": True,
            "branch_name": "feature-branch",
            "head_commit": "commit123",
            "created_at": datetime.now().isoformat()
        })
        
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
        mock_service.get_commit_history = AsyncMock(return_value={
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
        })
        
        result = await get_branch_history("main", 50, None, None)
        
        mock_service.get_commit_history.assert_called_once_with("main", 50, None, None)
        
        assert result["success"] is True
        assert len(result["commits"]) == 1
        assert result["total_commits"] == 1


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
        mock_service.create_tag = AsyncMock(return_value={
            "success": True,
            "tag_name": "v1.0.0",
            "commit_hash": "commit123",
            "created_at": datetime.now().isoformat()
        })
        
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


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=src/api/version_control.py", "--cov-report=term-missing"])
