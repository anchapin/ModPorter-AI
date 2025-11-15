"""
Simplified comprehensive tests for version_control.py API endpoints
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.version_control import router
from src.services.graph_version_control import ChangeType, ItemType


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
    async def test_get_commit_not_found(self, mock_service):
        """Test commit retrieval for non-existent commit"""
        mock_service.commits = {}
        
        from src.api.version_control import get_commit
        from fastapi import HTTPException
        
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
        mock_service.branches = {
            "main": Mock(
                created_at=datetime.now(),
                created_by_name="User1",
                head_commit="abc123",
                base_commit="def456",
                is_protected=False,
                description="Main branch",
                metadata={}
            ),
            "protected": Mock(
                created_at=datetime.now(),
                created_by_name="User2",
                head_commit="ghi789",
                base_commit="jkl012",
                is_protected=True,
                description="Protected branch",
                metadata={}
            )
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
    async def test_get_branch_not_found(self, mock_service):
        """Test branch retrieval for non-existent branch"""
        mock_service.branches = {}
        
        from src.api.version_control import get_branch
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            await get_branch("nonexistent")
        
        assert exc_info.value.status_code == 404
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
    async def test_get_tags_success(self, mock_service):
        """Test successful tags list retrieval"""
        mock_service.commits = {
            "abc123": Mock(
                message="Release commit 1",
                author_name="User1",
                timestamp=datetime(2023, 1, 1)
            ),
            "def456": Mock(
                message="Release commit 2",
                author_name="User2",
                timestamp=datetime(2023, 2, 1)
            )
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
        mock_service.commits = {
            "abc123": Mock(
                author_name="User1",
                timestamp=datetime(2023, 1, 1),
                message="First commit",
                branch_name="main"
            )
        }
        mock_service.branches = {
            "main": Mock(
                created_at=datetime.now(),
                created_by_name="User1",
                head_commit="abc123",
                base_commit="def456",
                is_protected=True,
                description="Main branch",
                metadata={}
            )
        }
        mock_service.tags = {"v1.0.0": "abc123"}
        mock_service.head_branch = "main"
        
        from src.api.version_control import get_version_control_status
        result = await get_version_control_status()
        
        # Verify response
        assert result["success"] is True
        assert result["status"]["total_commits"] == 1
        assert result["status"]["total_branches"] == 1
        assert result["status"]["total_tags"] == 1
        assert result["status"]["head_branch"] == "main"
        assert len(result["status"]["recent_commits"]) == 1
    
    @pytest.mark.asyncio
    async def test_search_commits_success(self, mock_service):
        """Test successful commit search"""
        mock_commit = Mock()
        mock_commit.commit_hash = "abc123"
        mock_commit.author_name = "Test User"
        mock_commit.timestamp = datetime.now()
        mock_commit.message = "Fix bug in node processing"
        mock_commit.branch_name = "main"
        mock_commit.tree_hash = "tree123"
        mock_commit.changes = []
        
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
