"""
Comprehensive tests for version_control.py API endpoints
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.version_control import router
from src.services.graph_version_control import (
    GraphChange, GraphBranch, ChangeType, ItemType
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
    
    @pytest.mark.asyncio
    async def test_create_commit_success(self, mock_db, mock_service):
        """Test successful commit creation"""
        mock_service.create_commit.return_value = {
            "success": True,
            "commit_hash": "abc123",
            "branch_name": "main",
            "message": "Test commit",
            "changes_count": 3
        }
        
        commit_data = {
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
            ]
        }
        
        from src.api.version_control import create_commit
        result = await create_commit(commit_data, mock_db)
        
        # Verify service was called correctly
        mock_service.create_commit.assert_called_once_with(
            "main", "user123", "Test User", "Test commit", 
            commit_data["changes"], None, mock_db
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
        
        from src.api.version_control import create_commit
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await create_commit(commit_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "author_id, author_name, and message are required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_create_commit_service_error(self, mock_db, mock_service):
        """Test commit creation with service error"""
        mock_service.create_commit.return_value = {
            "success": False,
            "error": "Branch not found"
        }
        
        commit_data = {
            "branch_name": "nonexistent",
            "author_id": "user123",
            "author_name": "Test User",
            "message": "Test commit"
        }
        
        from src.api.version_control import create_commit
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await create_commit(commit_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Branch not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_commit_success(self, mock_service):
        """Test successful commit retrieval"""
        # Mock commit object
        mock_commit = Mock(spec=GraphChange)
        mock_commit.commit_hash = "abc123"
        mock_commit.author_name = "Test User"
        mock_commit.timestamp = datetime.now()
        mock_commit.message = "Test commit"
        mock_commit.branch_name = "main"
        mock_commit.parent_commits = ["def456"]
        mock_commit.tree_hash = "tree789"
        mock_commit.metadata = {"key": "value"}
        
        # Mock change
        mock_change = Mock()
        mock_change.change_id = "change1"
        mock_change.change_type.value = "add"
        mock_change.item_type.value = "node"
        mock_change.item_id = "node1"
        mock_change.previous_data = None
        mock_change.new_data = {"name": "test"}
        mock_change.metadata = {}
        mock_change.author_name = "Test User"
        mock_change.timestamp = datetime.now()
        mock_change.branch_name = "main"
        
        mock_commit.changes = [mock_change]
        
        mock_service.commits = {"abc123": mock_commit}
        
        from src.api.version_control import get_commit
        result = await get_commit("abc123")
        
        # Verify response
        assert result["success"] is True
        assert result["commit"]["hash"] == "abc123"
        assert result["commit"]["author"] == "Test User"
        assert result["commit"]["message"] == "Test commit"
        assert len(result["commit"]["changes"]) == 1
        
        change = result["commit"]["changes"][0]
        assert change["change_type"] == "add"
        assert change["item_type"] == "node"
        assert change["item_id"] == "node1"
    
    @pytest.mark.asyncio
    async def test_get_commit_not_found(self, mock_service):
        """Test commit retrieval for non-existent commit"""
        mock_service.commits = {}
        
        from src.api.version_control import get_commit
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_commit("nonexistent")
        
        assert exc_info.value.status_code == 404
        assert "Commit not found" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_commit_changes_success(self, mock_service):
        """Test successful commit changes retrieval"""
        # Mock commit with changes
        mock_commit = Mock(spec=Commit)
        mock_commit.changes = []
        
        # Create mock change
        mock_change = Mock()
        mock_change.change_id = "change1"
        mock_change.change_type.value = "add"
        mock_change.item_type.value = "node"
        mock_change.item_id = "node1"
        mock_change.previous_data = None
        mock_change.new_data = {"name": "test"}
        mock_change.metadata = {}
        mock_change.author_name = "Test User"
        mock_change.timestamp = datetime.now()
        mock_change.branch_name = "main"
        
        mock_commit.changes = [mock_change]
        
        mock_service.commits = {"abc123": mock_commit}
        
        from src.api.version_control import get_commit_changes
        result = await get_commit_changes("abc123")
        
        # Verify response
        assert result["success"] is True
        assert result["commit_hash"] == "abc123"
        assert result["total_changes"] == 1
        
        change = result["changes"][0]
        assert change["change_id"] == "change1"
        assert change["change_type"] == "add"
        assert change["item_type"] == "node"
        assert change["author"] == "Test User"


class TestBranchEndpoints:
    """Test branch-related endpoints"""
    
    @pytest.fixture
    def mock_service(self):
        """Mock version control service"""
        with patch('src.api.version_control.graph_version_control_service') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_create_branch_success(self, mock_service):
        """Test successful branch creation"""
        mock_service.create_branch.return_value = {
            "success": True,
            "branch_name": "feature-branch",
            "source_branch": "main",
            "created_by": "Test User"
        }
        
        branch_data = {
            "branch_name": "feature-branch",
            "source_branch": "main",
            "author_id": "user123",
            "author_name": "Test User",
            "description": "Test feature branch"
        }
        
        from src.api.version_control import create_branch
        result = await create_branch(branch_data)
        
        # Verify service was called correctly
        mock_service.create_branch.assert_called_once_with(
            "feature-branch", "main", "user123", "Test User", "Test feature branch"
        )
        
        # Verify response
        assert result["success"] is True
        assert result["branch_name"] == "feature-branch"
    
    @pytest.mark.asyncio
    async def test_create_branch_missing_fields(self, mock_service):
        """Test branch creation with missing required fields"""
        branch_data = {
            "branch_name": "feature-branch"
            # Missing author_id and author_name
        }
        
        from src.api.version_control import create_branch
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await create_branch(branch_data)
        
        assert exc_info.value.status_code == 400
        assert "branch_name, author_id, and author_name are required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_branches_success(self, mock_service):
        """Test successful branches list retrieval"""
        # Mock branches
        mock_branch1 = Mock(spec=Branch)
        mock_branch1.created_at = datetime.now()
        mock_branch1.created_by_name = "User1"
        mock_branch1.head_commit = "abc123"
        mock_branch1.base_commit = "def456"
        mock_branch1.is_protected = False
        mock_branch1.description = "Main branch"
        mock_branch1.metadata = {}
        
        mock_branch2 = Mock(spec=Branch)
        mock_branch2.created_at = datetime.now()
        mock_branch2.created_by_name = "User2"
        mock_branch2.head_commit = "ghi789"
        mock_branch2.base_commit = "jkl012"
        mock_branch2.is_protected = True
        mock_branch2.description = "Protected branch"
        mock_branch2.metadata = {}
        
        mock_service.branches = {
            "main": mock_branch1,
            "protected": mock_branch2
        }
        mock_service.head_branch = "main"
        
        from src.api.version_control import get_branches
        result = await get_branches()
        
        # Verify response
        assert result["success"] is True
        assert result["total_branches"] == 2
        assert result["default_branch"] == "main"
        assert len(result["branches"]) == 2
        
        # Check branch data structure
        for branch in result["branches"]:
            assert "name" in branch
            assert "created_at" in branch
            assert "created_by" in branch
            assert "head_commit" in branch
            assert "is_protected" in branch
            assert "description" in branch
    
    @pytest.mark.asyncio
    async def test_get_branch_success(self, mock_service):
        """Test successful single branch retrieval"""
        mock_branch = Mock(spec=Branch)
        mock_branch.created_at = datetime.now()
        mock_branch.created_by_name = "Test User"
        mock_branch.head_commit = "abc123"
        mock_branch.base_commit = "def456"
        mock_branch.is_protected = False
        mock_branch.description = "Test branch"
        mock_branch.metadata = {}
        
        mock_service.branches = {"feature-branch": mock_branch}
        
        from src.api.version_control import get_branch
        result = await get_branch("feature-branch")
        
        # Verify response
        assert result["success"] is True
        assert result["branch"]["name"] == "feature-branch"
        assert result["branch"]["created_by"] == "Test User"
        assert result["branch"]["head_commit"] == "abc123"
        assert result["branch"]["is_protected"] is False
    
    @pytest.mark.asyncio
    async def test_get_branch_not_found(self, mock_service):
        """Test branch retrieval for non-existent branch"""
        mock_service.branches = {}
        
        from src.api.version_control import get_branch
        from fastapi import HTTPException
        
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
                    "hash": "abc123",
                    "author": "User1",
                    "timestamp": "2023-01-01T00:00:00",
                    "message": "First commit"
                },
                {
                    "hash": "def456",
                    "author": "User2",
                    "timestamp": "2023-01-02T00:00:00",
                    "message": "Second commit"
                }
            ],
            "total_commits": 2
        }
        
        from src.api.version_control import get_branch_history
        result = await get_branch_history("main", limit=50)
        
        # Verify service call
        mock_service.get_commit_history.assert_called_once_with("main", 50, None, None)
        
        # Verify response
        assert result["success"] is True
        assert result["total_commits"] == 2
        assert len(result["commits"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_branch_status_success(self, mock_service):
        """Test successful branch status retrieval"""
        mock_service.get_branch_status.return_value = {
            "success": True,
            "branch_name": "main",
            "head_commit": "abc123",
            "ahead_commits": 5,
            "behind_commits": 2,
            "total_commits": 100
        }
        
        from src.api.version_control import get_branch_status
        result = await get_branch_status("main")
        
        # Verify service call
        mock_service.get_branch_status.assert_called_once_with("main")
        
        # Verify response
        assert result["success"] is True
        assert result["branch_name"] == "main"
        assert result["head_commit"] == "abc123"
        assert result["ahead_commits"] == 5


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
    
    @pytest.mark.asyncio
    async def test_merge_branch_success(self, mock_db, mock_service):
        """Test successful branch merge"""
        # Mock merge result
        mock_merge_result = Mock()
        mock_merge_result.success = True
        mock_merge_result.merge_commit_hash = "merge123"
        mock_merge_result.conflicts = []
        mock_merge_result.resolved_conflicts = []
        mock_merge_result.merged_changes = [{"change_id": "c1"}, {"change_id": "c2"}]
        mock_merge_result.merge_strategy = "merge_commit"
        mock_merge_result.message = "Merge successful"
        
        mock_service.merge_branch.return_value = mock_merge_result
        
        merge_data = {
            "target_branch": "main",
            "author_id": "user123",
            "author_name": "Test User",
            "merge_message": "Merge feature branch",
            "merge_strategy": "merge_commit"
        }
        
        from src.api.version_control import merge_branch
        result = await merge_branch("feature-branch", merge_data, mock_db)
        
        # Verify service call
        mock_service.merge_branch.assert_called_once_with(
            "feature-branch", "main", "user123", "Test User",
            "Merge feature branch", "merge_commit", mock_db
        )
        
        # Verify response
        assert result["success"] is True
        assert result["merge_result"]["merge_commit_hash"] == "merge123"
        assert result["merge_result"]["conflicts_resolved"] == 0
        assert result["merge_result"]["remaining_conflicts"] == 0
        assert result["merge_result"]["merged_changes_count"] == 2
    
    @pytest.mark.asyncio
    async def test_merge_branch_conflicts(self, mock_db, mock_service):
        """Test branch merge with conflicts"""
        # Mock merge result with conflicts
        mock_merge_result = Mock()
        mock_merge_result.success = False
        mock_merge_result.conflicts = [
            {"item_id": "node1", "error": "Data conflict"},
            {"item_id": "node2", "error": "Schema mismatch"}
        ]
        mock_merge_result.resolved_conflicts = []
        mock_merge_result.merged_changes = []
        
        mock_service.merge_branch.return_value = mock_merge_result
        
        merge_data = {
            "target_branch": "main",
            "author_id": "user123",
            "author_name": "Test User"
        }
        
        from src.api.version_control import merge_branch
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await merge_branch("feature-branch", merge_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "Merge failed" in str(exc_info.value.detail)
        assert "Data conflict" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_merge_branch_missing_fields(self, mock_db, mock_service):
        """Test branch merge with missing required fields"""
        merge_data = {
            "author_id": "user123"
            # Missing target_branch and author_name
        }
        
        from src.api.version_control import merge_branch
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await merge_branch("feature-branch", merge_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "target_branch, author_id, and author_name are required" in str(exc_info.value.detail)


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
    
    @pytest.mark.asyncio
    async def test_generate_diff_success(self, mock_db, mock_service):
        """Test successful diff generation"""
        # Mock diff result
        mock_diff = Mock()
        mock_diff.base_hash = "abc123"
        mock_diff.target_hash = "def456"
        mock_diff.added_nodes = [{"id": "node1", "name": "New node"}]
        mock_diff.modified_nodes = [{"id": "node2", "changes": ["name updated"]}]
        mock_diff.deleted_nodes = [{"id": "node3", "name": "Deleted node"}]
        mock_diff.added_relationships = [{"id": "rel1", "source": "node1", "target": "node2"}]
        mock_diff.modified_relationships = []
        mock_diff.deleted_relationships = []
        mock_diff.added_patterns = []
        mock_diff.modified_patterns = []
        mock_diff.deleted_patterns = []
        mock_diff.conflicts = []
        mock_diff.metadata = {}
        
        mock_service.generate_diff.return_value = mock_diff
        
        diff_data = {
            "base_hash": "abc123",
            "target_hash": "def456",
            "item_types": ["node", "relationship"]
        }
        
        from src.api.version_control import generate_diff
        result = await generate_diff(diff_data, mock_db)
        
        # Verify service call
        mock_service.generate_diff.assert_called_once_with(
            "abc123", "def456", ["node", "relationship"], mock_db
        )
        
        # Verify response
        assert result["success"] is True
        assert result["diff"]["base_hash"] == "abc123"
        assert result["diff"]["target_hash"] == "def456"
        
        summary = result["diff"]["summary"]
        assert summary["added_nodes"] == 1
        assert summary["modified_nodes"] == 1
        assert summary["deleted_nodes"] == 1
        assert summary["added_relationships"] == 1
        assert summary["total_changes"] == 4
        assert summary["conflicts"] == 0
    
    @pytest.mark.asyncio
    async def test_generate_diff_missing_hashes(self, mock_db, mock_service):
        """Test diff generation with missing required hashes"""
        diff_data = {
            "base_hash": "abc123"
            # Missing target_hash
        }
        
        from src.api.version_control import generate_diff
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await generate_diff(diff_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "base_hash and target_hash are required" in str(exc_info.value.detail)


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
    
    @pytest.mark.asyncio
    async def test_revert_commit_success(self, mock_db, mock_service):
        """Test successful commit revert"""
        mock_service.revert_commit.return_value = {
            "success": True,
            "revert_commit_hash": "revert123",
            "original_commit": "abc123",
            "message": "Revert original commit"
        }
        
        revert_data = {
            "author_id": "user123",
            "author_name": "Test User",
            "revert_message": "Reverting problematic commit",
            "branch_name": "main"
        }
        
        from src.api.version_control import revert_commit
        result = await revert_commit("abc123", revert_data, mock_db)
        
        # Verify service call
        mock_service.revert_commit.assert_called_once_with(
            "abc123", "user123", "Test User", "Reverting problematic commit", "main", mock_db
        )
        
        # Verify response
        assert result["success"] is True
        assert result["revert_commit_hash"] == "revert123"
        assert result["original_commit"] == "abc123"
    
    @pytest.mark.asyncio
    async def test_revert_commit_missing_fields(self, mock_db, mock_service):
        """Test commit revert with missing required fields"""
        revert_data = {
            "author_id": "user123"
            # Missing author_name
        }
        
        from src.api.version_control import revert_commit
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await revert_commit("abc123", revert_data, mock_db)
        
        assert exc_info.value.status_code == 400
        assert "author_id and author_name are required" in str(exc_info.value.detail)


class TestTagEndpoints:
    """Test tag-related endpoints"""
    
    @pytest.fixture
    def mock_service(self):
        """Mock version control service"""
        with patch('src.api.version_control.graph_version_control_service') as mock:
            yield mock
    
    @pytest.mark.asyncio
    async def test_create_tag_success(self, mock_service):
        """Test successful tag creation"""
        mock_service.create_tag.return_value = {
            "success": True,
            "tag_name": "v1.0.0",
            "commit_hash": "abc123",
            "message": "Release version 1.0.0"
        }
        
        tag_data = {
            "tag_name": "v1.0.0",
            "commit_hash": "abc123",
            "author_id": "user123",
            "author_name": "Test User",
            "message": "Release version 1.0.0"
        }
        
        from src.api.version_control import create_tag
        result = await create_tag(tag_data)
        
        # Verify service call
        mock_service.create_tag.assert_called_once_with(
            "v1.0.0", "abc123", "user123", "Test User", "Release version 1.0.0"
        )
        
        # Verify response
        assert result["success"] is True
        assert result["tag_name"] == "v1.0.0"
        assert result["commit_hash"] == "abc123"
    
    @pytest.mark.asyncio
    async def test_create_tag_missing_fields(self, mock_service):
        """Test tag creation with missing required fields"""
        tag_data = {
            "tag_name": "v1.0.0",
            "commit_hash": "abc123"
            # Missing author_id and author_name
        }
        
        from src.api.version_control import create_tag
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await create_tag(tag_data)
        
        assert exc_info.value.status_code == 400
        assert "tag_name, commit_hash, author_id, and author_name are required" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_tags_success(self, mock_service):
        """Test successful tags list retrieval"""
        # Mock commits for tag details
        mock_commit1 = Mock(spec=Commit)
        mock_commit1.message = "Release commit 1"
        mock_commit1.author_name = "User1"
        mock_commit1.timestamp = datetime(2023, 1, 1)
        
        mock_commit2 = Mock(spec=Commit)
        mock_commit2.message = "Release commit 2"
        mock_commit2.author_name = "User2"
        mock_commit2.timestamp = datetime(2023, 2, 1)
        
        mock_service.commits = {
            "abc123": mock_commit1,
            "def456": mock_commit2
        }
        mock_service.tags = {
            "v1.0.0": "abc123",
            "v1.1.0": "def456"
        }
        
        from src.api.version_control import get_tags
        result = await get_tags()
        
        # Verify response
        assert result["success"] is True
        assert result["total_tags"] == 2
        assert len(result["tags"]) == 2
        
        # Check tag data structure
        for tag in result["tags"]:
            assert "name" in tag
            assert "commit_hash" in tag
            assert "commit_message" in tag
            assert "author" in tag
            assert "timestamp" in tag
    
    @pytest.mark.asyncio
    async def test_get_tag_success(self, mock_service):
        """Test successful single tag retrieval"""
        mock_commit = Mock(spec=Commit)
        mock_commit.commit_hash = "abc123"
        mock_commit.author_name = "Test User"
        mock_commit.timestamp = datetime.now()
        mock_commit.message = "Release commit"
        mock_commit.tree_hash = "tree123"
        mock_commit.changes = [Mock(), Mock(), Mock()]  # 3 changes
        
        mock_service.commits = {"abc123": mock_commit}
        mock_service.tags = {"v1.0.0": "abc123"}
        
        from src.api.version_control import get_tag
        result = await get_tag("v1.0.0")
        
        # Verify response
        assert result["success"] is True
        assert result["tag"]["name"] == "v1.0.0"
        assert result["tag"]["commit_hash"] == "abc123"
        assert result["tag"]["commit"]["message"] == "Release commit"
        assert result["tag"]["commit"]["changes_count"] == 3
    
    @pytest.mark.asyncio
    async def test_get_tag_not_found(self, mock_service):
        """Test tag retrieval for non-existent tag"""
        mock_service.tags = {}
        
        from src.api.version_control import get_tag
        from fastapi import HTTPException
        
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
    async def test_get_version_control_status(self, mock_service):
        """Test version control status retrieval"""
        # Mock branches
        mock_branch = Mock(spec=Branch)
        mock_branch.created_at = datetime.now()
        mock_branch.created_by_name = "User1"
        mock_branch.head_commit = "abc123"
        mock_branch.base_commit = "def456"
        mock_branch.is_protected = True
        mock_branch.description = "Main branch"
        mock_branch.metadata = {}
        
        # Mock commits
        mock_commit1 = Mock(spec=Commit)
        mock_commit1.commit_hash = "abc123"
        mock_commit1.author_name = "User1"
        mock_commit1.timestamp = datetime(2023, 1, 1)
        mock_commit1.message = "First commit"
        mock_commit1.branch_name = "main"
        
        mock_commit2 = Mock(spec=Commit)
        mock_commit2.commit_hash = "def456"
        mock_commit2.author_name = "User2"
        mock_commit2.timestamp = datetime(2023, 1, 2)
        mock_commit2.message = "Second commit"
        mock_commit2.branch_name = "feature"
        
        mock_service.commits = {
            "abc123": mock_commit1,
            "def456": mock_commit2
        }
        mock_service.branches = {
            "main": mock_branch,
            "protected": mock_branch
        }
        mock_service.tags = {"v1.0.0": "abc123"}
        mock_service.head_branch = "main"
        
        from src.api.version_control import get_version_control_status
        result = await get_version_control_status()
        
        # Verify response
        assert result["success"] is True
        assert result["status"]["total_commits"] == 2
        assert result["status"]["total_branches"] == 2
        assert result["status"]["total_tags"] == 1
        assert result["status"]["head_branch"] == "main"
        assert len(result["status"]["recent_commits"]) == 2
        assert len(result["status"]["protected_branches"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_version_control_stats(self, mock_service):
        """Test version control statistics retrieval"""
        # Mock commit with changes
        mock_commit = Mock(spec=Commit)
        mock_commit.author_name = "Test User"
        mock_commit.timestamp = datetime(2023, 1, 1)
        mock_commit.branch_name = "main"
        
        # Mock change
        mock_change = Mock()
        mock_change.change_type.value = "add"
        mock_change.item_type.value = "node"
        
        mock_commit.changes = [mock_change]
        
        mock_service.commits = {"abc123": mock_commit}
        mock_service.branches = {"main": Mock()}
        mock_service.tags = {"v1.0.0": "abc123"}
        
        from src.api.version_control import get_version_control_stats
        result = await get_version_control_stats()
        
        # Verify response
        assert result["success"] is True
        assert result["stats"]["total_commits"] == 1
        assert result["stats"]["total_branches"] == 1
        assert result["stats"]["total_tags"] == 1
        assert "top_authors" in result["stats"]
        assert "active_branches" in result["stats"]
        assert "change_types" in result["stats"]
        assert "commits_per_day" in result["stats"]
    
    @pytest.mark.asyncio
    async def test_search_commits_success(self, mock_service):
        """Test successful commit search"""
        mock_commit = Mock(spec=Commit)
        mock_commit.commit_hash = "abc123"
        mock_commit.author_name = "Test User"
        mock_commit.timestamp = datetime.now()
        mock_commit.message = "Fix bug in node processing"
        mock_commit.branch_name = "main"
        mock_commit.tree_hash = "tree123"
        
        # Mock change with search term
        mock_change = Mock()
        mock_change.new_data = {"name": "test node"}
        mock_change.previous_data = None
        
        mock_commit.changes = [mock_change]
        
        mock_service.commits = {"abc123": mock_commit}
        
        from src.api.version_control import search_commits
        result = await search_commits(query="node", limit=50)
        
        # Verify response
        assert result["success"] is True
        assert result["query"] == "node"
        assert result["total_results"] == 1
        assert len(result["results"]) == 1
        
        commit_result = result["results"][0]
        assert commit_result["hash"] == "abc123"
        assert commit_result["author"] == "Test User"
        assert commit_result["message"] == "Fix bug in node processing"
    
    @pytest.mark.asyncio
    async def test_search_commits_with_filters(self, mock_service):
        """Test commit search with author and branch filters"""
        mock_commit = Mock(spec=Commit)
        mock_commit.commit_hash = "abc123"
        mock_commit.author_name = "Specific User"
        mock_commit.timestamp = datetime.now()
        mock_commit.message = "Test commit"
        mock_commit.branch_name = "feature-branch"
        mock_commit.tree_hash = "tree123"
        mock_commit.changes = []
        
        mock_service.commits = {"abc123": mock_commit}
        
        from src.api.version_control import search_commits
        result = await search_commits(
            query="test",
            author="Specific User",
            branch="feature-branch",
            limit=10
        )
        
        # Verify response
        assert result["success"] is True
        assert result["filters"]["author"] == "Specific User"
        assert result["filters"]["branch"] == "feature-branch"
        assert result["limit"] == 10
    
    @pytest.mark.asyncio
    async def test_get_changelog_success(self, mock_service):
        """Test successful changelog generation"""
        mock_service.get_commit_history.return_value = {
            "success": True,
            "commits": [
                {
                    "hash": "abc123",
                    "author": "User1",
                    "timestamp": "2023-01-01T00:00:00",
                    "message": "Add feature X",
                    "changes_count": 2,
                    "changes": [
                        {"change_type": "add", "item_type": "node"},
                        {"change_type": "add", "item_type": "node"}
                    ]
                },
                {
                    "hash": "def456",
                    "author": "User2",
                    "timestamp": "2023-01-01T12:00:00",
                    "message": "Fix bug Y",
                    "changes_count": 1,
                    "changes": [
                        {"change_type": "modify", "item_type": "relationship"}
                    ]
                }
            ]
        }
        
        from src.api.version_control import get_changelog
        result = await get_changelog(branch_name="main", limit=100)
        
        # Verify service call
        mock_service.get_commit_history.assert_called_once_with("main", 100, None)
        
        # Verify response
        assert result["success"] is True
        assert result["branch_name"] == "main"
        assert result["total_commits"] == 2
        assert "changelog_by_date" in result
        assert "summary" in result
        
        # Check changelog grouping
        changelog_by_date = result["changelog_by_date"]
        assert "2023-01-01" in changelog_by_date
        assert len(changelog_by_date["2023-01-01"]) == 2
    
    @pytest.mark.asyncio
    async def test_get_changelog_with_since_commit(self, mock_service):
        """Test changelog generation with since commit parameter"""
        mock_service.get_commit_history.return_value = {
            "success": True,
            "commits": [
                {
                    "hash": "def456",
                    "author": "User2",
                    "timestamp": "2023-01-02T00:00:00",
                    "message": "New commit",
                    "changes_count": 1
                }
            ]
        }
        
        from src.api.version_control import get_changelog
        result = await get_changelog(branch_name="main", since="abc123", limit=100)
        
        # Verify service call
        mock_service.get_commit_history.assert_called_once_with("main", 100, "abc123")
        
        # Verify response
        assert result["success"] is True
        assert result["since_commit"] == "abc123"
        assert result["total_commits"] == 1


class TestErrorHandling:
    """Test error handling in version control endpoints"""
    
    @pytest.mark.asyncio
    async def test_create_commit_service_exception(self):
        """Test handling of service exceptions during commit creation"""
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('src.api.version_control.graph_version_control_service') as mock_service:
            mock_service.create_commit.side_effect = Exception("Database error")
            
            from src.api.version_control import create_commit
            from fastapi import HTTPException
            
            commit_data = {
                "branch_name": "main",
                "author_id": "user123",
                "author_name": "Test User",
                "message": "Test commit"
            }
            
            with pytest.raises(HTTPException) as exc_info:
                await create_commit(commit_data, mock_db)
            
            assert exc_info.value.status_code == 500
            assert "Commit creation failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_commit_exception(self):
        """Test handling of exceptions during commit retrieval"""
        with patch('src.api.version_control.graph_version_control_service') as mock_service:
            mock_service.commits = Mock()
            mock_service.commits.__getitem__ = Mock(side_effect=Exception("Service error"))
            
            from src.api.version_control import get_commit
            from fastapi import HTTPException
            
            with pytest.raises(HTTPException) as exc_info:
                await get_commit("abc123")
            
            assert exc_info.value.status_code == 500
            assert "Failed to get commit" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_branches_exception(self):
        """Test handling of exceptions during branches retrieval"""
        with patch('src.api.version_control.graph_version_control_service') as mock_service:
            mock_service.branches = Mock()
            mock_service.branches.items = Mock(side_effect=Exception("Service error"))
            
            from src.api.version_control import get_branches
            from fastapi import HTTPException
            
            with pytest.raises(HTTPException) as exc_info:
                await get_branches()
            
            assert exc_info.value.status_code == 500
            assert "Failed to get branches" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_generate_diff_service_exception(self):
        """Test handling of service exceptions during diff generation"""
        mock_db = AsyncMock(spec=AsyncSession)
        
        with patch('src.api.version_control.graph_version_control_service') as mock_service:
            mock_service.generate_diff.side_effect = Exception("Diff generation error")
            
            from src.api.version_control import generate_diff
            from fastapi import HTTPException
            
            diff_data = {
                "base_hash": "abc123",
                "target_hash": "def456"
            }
            
            with pytest.raises(HTTPException) as exc_info:
                await generate_diff(diff_data, mock_db)
            
            assert exc_info.value.status_code == 500
            assert "Diff generation failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_search_commits_service_exception(self):
        """Test handling of exceptions during commit search"""
        with patch('src.api.version_control.graph_version_control_service') as mock_service:
            mock_service.commits = Mock()
            mock_service.commits.values = Mock(side_effect=Exception("Search error"))
            
            from src.api.version_control import search_commits
            from fastapi import HTTPException
            
            with pytest.raises(HTTPException) as exc_info:
                await search_commits(query="test")
            
            assert exc_info.value.status_code == 500
            assert "Search failed" in str(exc_info.value.detail)
    
    @pytest.mark.asyncio
    async def test_get_changelog_service_exception(self):
        """Test handling of exceptions during changelog generation"""
        with patch('src.api.version_control.graph_version_control_service') as mock_service:
            mock_service.get_commit_history.side_effect = Exception("History error")
            
            from src.api.version_control import get_changelog
            from fastapi import HTTPException
            
            with pytest.raises(HTTPException) as exc_info:
                await get_changelog(branch_name="main")
            
            assert exc_info.value.status_code == 500
            assert "Changelog generation failed" in str(exc_info.value.detail)
