"""
Version Control System for Knowledge Graph Changes

This service provides Git-like version control functionality for knowledge graph
changes, including branching, merging, diff generation, and history tracking.
"""

import logging
import json
import hashlib
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.knowledge_graph_crud import (
    KnowledgeNodeCRUD
)

logger = logging.getLogger(__name__)


class ChangeType(Enum):
    """Types of changes in version control."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    BRANCH = "branch"


class ItemType(Enum):
    """Types of items that can be versioned."""
    NODE = "node"
    RELATIONSHIP = "relationship"
    PATTERN = "pattern"
    GRAPH = "graph"


@dataclass
class GraphChange:
    """Individual change in the knowledge graph."""
    change_id: str
    change_type: ChangeType
    item_type: ItemType
    item_id: str
    author_id: str
    author_name: str
    timestamp: datetime
    branch_name: str
    commit_hash: str
    parent_commit: Optional[str] = None
    previous_data: Dict[str, Any] = field(default_factory=dict)
    new_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    merged_from_branch: Optional[str] = None


@dataclass
class GraphBranch:
    """Branch in the knowledge graph version control."""
    branch_name: str
    created_at: datetime
    created_by: str
    created_by_name: str
    head_commit: Optional[str] = None
    base_commit: Optional[str] = None
    is_protected: bool = False
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphCommit:
    """Commit in the knowledge graph version control."""
    commit_hash: str
    author_id: str
    author_name: str
    timestamp: datetime
    message: str
    branch_name: str
    parent_commits: List[str] = field(default_factory=list)
    changes: List[GraphChange] = field(default_factory=list)
    tree_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphDiff:
    """Diff between two knowledge graph states."""
    base_hash: str
    target_hash: str
    added_nodes: List[Dict[str, Any]] = field(default_factory=list)
    modified_nodes: List[Dict[str, Any]] = field(default_factory=list)
    deleted_nodes: List[Dict[str, Any]] = field(default_factory=list)
    added_relationships: List[Dict[str, Any]] = field(default_factory=list)
    modified_relationships: List[Dict[str, Any]] = field(default_factory=list)
    deleted_relationships: List[Dict[str, Any]] = field(default_factory=list)
    added_patterns: List[Dict[str, Any]] = field(default_factory=list)
    modified_patterns: List[Dict[str, Any]] = field(default_factory=list)
    deleted_patterns: List[Dict[str, Any]] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MergeResult:
    """Result of merging branches."""
    success: bool
    merge_commit_hash: Optional[str] = None
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    resolved_conflicts: List[Dict[str, Any]] = field(default_factory=list)
    merge_strategy: str = ""
    merged_changes: List[GraphChange] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class GraphVersionControlService:
    """Git-like version control for knowledge graph."""
    
    def __init__(self):
        self.commits: Dict[str, GraphCommit] = {}
        self.branches: Dict[str, GraphBranch] = {}
        self.changes: List[GraphChange] = []
        self.head_branch = "main"
        self.tags: Dict[str, str] = {}  # tag_name -> commit_hash
        self.remote_refs: Dict[str, str] = {}  # remote_name -> commit_hash
        
        # Initialize main branch
        self._initialize_main_branch()
    
    async def create_commit(
        self,
        branch_name: str,
        author_id: str,
        author_name: str,
        message: str,
        changes: List[Dict[str, Any]],
        parent_commits: Optional[List[str]] = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Create a new commit in the knowledge graph.
        
        Args:
            branch_name: Name of branch to commit to
            author_id: ID of author
            author_name: Name of author
            message: Commit message
            changes: List of changes to commit
            parent_commits: List of parent commit hashes
            db: Database session
        
        Returns:
            Commit creation result
        """
        try:
            # Validate branch exists
            if branch_name not in self.branches:
                return {
                    "success": False,
                    "error": f"Branch '{branch_name}' does not exist"
                }
            
            branch = self.branches[branch_name]
            
            # Get parent commits
            if not parent_commits:
                parent_commits = [branch.head_commit] if branch.head_commit else []
            
            # Create GraphChange objects
            graph_changes = []
            for change_data in changes:
                change = GraphChange(
                    change_id=str(uuid.uuid4()),
                    change_type=ChangeType(change_data.get("change_type", "create")),
                    item_type=ItemType(change_data.get("item_type", "node")),
                    item_id=change_data.get("item_id"),
                    author_id=author_id,
                    author_name=author_name,
                    timestamp=datetime.utcnow(),
                    branch_name=branch_name,
                    commit_hash="",  # Will be filled after commit hash is generated
                    previous_data=change_data.get("previous_data", {}),
                    new_data=change_data.get("new_data", {}),
                    metadata=change_data.get("metadata", {})
                )
                graph_changes.append(change)
            
            # Calculate tree hash
            tree_hash = await self._calculate_tree_hash(graph_changes, db)
            
            # Generate commit hash
            commit_content = {
                "tree": tree_hash,
                "parents": parent_commits,
                "author": author_name,
                "timestamp": datetime.utcnow().isoformat(),
                "message": message,
                "changes": [
                    {
                        "change_type": change.change_type.value,
                        "item_type": change.item_type.value,
                        "item_id": change.item_id,
                        "previous_data": change.previous_data,
                        "new_data": change.new_data
                    }
                    for change in graph_changes
                ]
            }
            commit_hash = self._generate_commit_hash(commit_content)
            
            # Create commit object
            commit = GraphCommit(
                commit_hash=commit_hash,
                author_id=author_id,
                author_name=author_name,
                timestamp=datetime.utcnow(),
                message=message,
                branch_name=branch_name,
                parent_commits=parent_commits,
                changes=graph_changes,
                tree_hash=tree_hash
            )
            
            # Update change objects with commit hash
            for change in graph_changes:
                change.commit_hash = commit_hash
            
            # Store commit
            self.commits[commit_hash] = commit
            
            # Update branch head
            branch.head_commit = commit_hash
            
            # Add to changes history
            self.changes.extend(graph_changes)
            
            # If this is the main branch, update graph state
            if branch_name == self.head_branch:
                await self._update_graph_from_commit(commit, db)
            
            return {
                "success": True,
                "commit_hash": commit_hash,
                "branch_name": branch_name,
                "tree_hash": tree_hash,
                "changes_count": len(graph_changes),
                "parent_commits": parent_commits,
                "message": "Commit created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating commit: {e}")
            return {
                "success": False,
                "error": f"Commit creation failed: {str(e)}"
            }
    
    async def create_branch(
        self,
        branch_name: str,
        source_branch: str,
        author_id: str,
        author_name: str,
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a new branch from an existing branch.
        
        Args:
            branch_name: Name of new branch
            source_branch: Name of source branch
            author_id: ID of author creating branch
            author_name: Name of author
            description: Branch description
        
        Returns:
            Branch creation result
        """
        try:
            # Validate branch name
            if branch_name in self.branches:
                return {
                    "success": False,
                    "error": f"Branch '{branch_name}' already exists"
                }
            
            # Validate source branch
            if source_branch not in self.branches:
                return {
                    "success": False,
                    "error": f"Source branch '{source_branch}' does not exist"
                }
            
            source_branch_obj = self.branches[source_branch]
            
            # Create new branch
            new_branch = GraphBranch(
                branch_name=branch_name,
                created_at=datetime.utcnow(),
                created_by=author_id,
                created_by_name=author_name,
                head_commit=source_branch_obj.head_commit,
                base_commit=source_branch_obj.head_commit,
                is_protected=False,
                description=description,
                metadata={
                    "source_branch": source_branch,
                    "created_at": datetime.utcnow().isoformat()
                }
            )
            
            # Store branch
            self.branches[branch_name] = new_branch
            
            return {
                "success": True,
                "branch_name": branch_name,
                "source_branch": source_branch,
                "head_commit": new_branch.head_commit,
                "base_commit": new_branch.base_commit,
                "created_at": new_branch.created_at.isoformat(),
                "message": "Branch created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating branch: {e}")
            return {
                "success": False,
                "error": f"Branch creation failed: {str(e)}"
            }
    
    async def merge_branch(
        self,
        source_branch: str,
        target_branch: str,
        author_id: str,
        author_name: str,
        merge_message: str,
        merge_strategy: str = "merge_commit",
        db: AsyncSession = None
    ) -> MergeResult:
        """
        Merge source branch into target branch.
        
        Args:
            source_branch: Name of source branch to merge
            target_branch: Name of target branch
            author_id: ID of author performing merge
            author_name: Name of author
            merge_message: Message for merge commit
            merge_strategy: Strategy for merge (merge_commit, squash, rebase)
            db: Database session
        
        Returns:
            Merge result with conflicts and resolved changes
        """
        try:
            # Validate branches exist
            if source_branch not in self.branches:
                return MergeResult(
                    success=False,
                    conflicts=[{"error": f"Source branch '{source_branch}' does not exist"}]
                )
            
            if target_branch not in self.branches:
                return MergeResult(
                    success=False,
                    conflicts=[{"error": f"Target branch '{target_branch}' does not exist"}]
                )
            
            source = self.branches[source_branch]
            target = self.branches[target_branch]
            
            # Get commits to merge
            source_commits = await self._get_commits_since_base(
                source.head_commit, target.head_commit
            )
            
            if not source_commits:
                return MergeResult(
                    success=True,
                    merge_strategy=merge_strategy,
                    metadata={"message": "Nothing to merge - branches are already up to date"}
                )
            
            # Detect conflicts
            conflicts = await self._detect_merge_conflicts(
                source_commits, target.head_commit, db
            )
            
            # Resolve conflicts if possible
            resolved_conflicts = []
            if conflicts:
                # Try auto-resolution
                for conflict in conflicts:
                    resolution = await self._auto_resolve_conflict(conflict, merge_strategy)
                    if resolution:
                        resolved_conflicts.append(resolution)
                        conflicts.remove(conflict)
            
            # If there are still unresolved conflicts, fail merge
            if conflicts:
                return MergeResult(
                    success=False,
                    conflicts=conflicts,
                    resolved_conflicts=resolved_conflicts,
                    merge_strategy=merge_strategy,
                    metadata={"message": "Merge failed due to unresolved conflicts"}
                )
            
            # Create merge commit
            merge_changes = []
            for commit in source_commits:
                merge_changes.extend(commit.changes)
            
            if merge_strategy == "squash":
                # Combine all changes into single commit
                parent_commits = [target.head_commit]
            else:
                # Create merge commit with both parents
                parent_commits = [target.head_commit, source.head_commit]
            
            # Add merge metadata changes
            merge_change = GraphChange(
                change_id=str(uuid.uuid4()),
                change_type=ChangeType.MERGE,
                item_type=ItemType.GRAPH,
                item_id="graph",
                author_id=author_id,
                author_name=author_name,
                timestamp=datetime.utcnow(),
                branch_name=target_branch,
                commit_hash="",  # Will be filled later
                new_data={
                    "merge_source": source_branch,
                    "merge_target": target_branch,
                    "resolved_conflicts": len(resolved_conflicts),
                    "merge_strategy": merge_strategy
                },
                metadata={
                    "merge_commit": True,
                    "source_commits": len(source_commits)
                }
            )
            merge_changes.append(merge_change)
            
            # Convert changes to dict format for commit creation
            changes_dict = [
                {
                    "change_type": change.change_type.value,
                    "item_type": change.item_type.value,
                    "item_id": change.item_id,
                    "previous_data": change.previous_data,
                    "new_data": change.new_data,
                    "metadata": change.metadata
                }
                for change in merge_changes
            ]
            
            # Create merge commit
            commit_result = await self.create_commit(
                target_branch,
                author_id,
                author_name,
                f"Merge {source_branch} into {target_branch}: {merge_message}",
                changes_dict,
                parent_commits,
                db
            )
            
            if not commit_result["success"]:
                return MergeResult(
                    success=False,
                    conflicts=[{"error": "Failed to create merge commit"}],
                    merge_strategy=merge_strategy
                )
            
            return MergeResult(
                success=True,
                merge_commit_hash=commit_result["commit_hash"],
                resolved_conflicts=resolved_conflicts,
                merged_changes=merge_changes,
                merge_strategy=merge_strategy,
                metadata={"message": f"Successfully merged {source_branch} into {target_branch}"}
            )
            
        except Exception as e:
            logger.error(f"Error merging branch: {e}")
            return MergeResult(
                success=False,
                conflicts=[{"error": f"Merge failed: {str(e)}"}],
                merge_strategy=merge_strategy
            )
    
    async def generate_diff(
        self,
        base_hash: str,
        target_hash: str,
        item_types: Optional[List[str]] = None,
        db: AsyncSession = None
    ) -> GraphDiff:
        """
        Generate diff between two commits.
        
        Args:
            base_hash: Hash of base commit
            target_hash: Hash of target commit
            item_types: Types of items to include in diff
            db: Database session
        
        Returns:
            Diff between the two commits
        """
        try:
            # Get commits
            if base_hash not in self.commits:
                raise ValueError(f"Base commit '{base_hash}' not found")
            
            if target_hash not in self.commits:
                raise ValueError(f"Target commit '{target_hash}' not found")
            
            base_commit = self.commits[base_hash]
            target_commit = self.commits[target_hash]
            
            # Create diff object
            diff = GraphDiff(
                base_hash=base_hash,
                target_hash=target_hash
            )
            
            # Get changes between commits
            path_changes = await self._get_changes_between_commits(
                base_hash, target_hash
            )
            
            # Categorize changes
            for change in path_changes:
                if item_types and change.item_type.value not in item_types:
                    continue
                
                if change.change_type == ChangeType.CREATE:
                    if change.item_type == ItemType.NODE:
                        diff.added_nodes.append(change.new_data)
                    elif change.item_type == ItemType.RELATIONSHIP:
                        diff.added_relationships.append(change.new_data)
                    elif change.item_type == ItemType.PATTERN:
                        diff.added_patterns.append(change.new_data)
                
                elif change.change_type == ChangeType.UPDATE:
                    if change.item_type == ItemType.NODE:
                        diff.modified_nodes.append({
                            "item_id": change.item_id,
                            "previous": change.previous_data,
                            "new": change.new_data
                        })
                    elif change.item_type == ItemType.RELATIONSHIP:
                        diff.modified_relationships.append({
                            "item_id": change.item_id,
                            "previous": change.previous_data,
                            "new": change.new_data
                        })
                    elif change.item_type == ItemType.PATTERN:
                        diff.modified_patterns.append({
                            "item_id": change.item_id,
                            "previous": change.previous_data,
                            "new": change.new_data
                        })
                
                elif change.change_type == ChangeType.DELETE:
                    if change.item_type == ItemType.NODE:
                        diff.deleted_nodes.append({
                            "item_id": change.item_id,
                            "data": change.previous_data
                        })
                    elif change.item_type == ItemType.RELATIONSHIP:
                        diff.deleted_relationships.append({
                            "item_id": change.item_id,
                            "data": change.previous_data
                        })
                    elif change.item_type == ItemType.PATTERN:
                        diff.deleted_patterns.append({
                            "item_id": change.item_id,
                            "data": change.previous_data
                        })
            
            # Generate metadata
            diff.metadata = {
                "generated_at": datetime.utcnow().isoformat(),
                "total_changes": len(path_changes),
                "changes_by_type": self._count_changes_by_type(path_changes),
                "files_changed": len(set(change.item_id for change in path_changes))
            }
            
            return diff
            
        except Exception as e:
            logger.error(f"Error generating diff: {e}")
            # Return empty diff on error
            return GraphDiff(
                base_hash=base_hash,
                target_hash=target_hash,
                metadata={"error": str(e)}
            )
    
    async def get_commit_history(
        self,
        branch_name: str,
        limit: int = 50,
        since: Optional[str] = None,
        until: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get commit history for a branch.
        
        Args:
            branch_name: Name of branch
            limit: Maximum number of commits to return
            since: Get commits since this commit hash
            until: Get commits until this commit hash
        
        Returns:
            Commit history
        """
        try:
            if branch_name not in self.branches:
                return {
                    "success": False,
                    "error": f"Branch '{branch_name}' does not exist"
                }
            
            branch = self.branches[branch_name]
            if not branch.head_commit:
                return {
                    "success": True,
                    "commits": [],
                    "message": "No commits found on branch"
                }
            
            # Build commit history by following parents
            commits = []
            visited = set()
            to_visit = [branch.head_commit]
            
            while to_visit and len(commits) < limit:
                commit_hash = to_visit.pop(0)
                
                if commit_hash in visited or commit_hash not in self.commits:
                    continue
                
                visited.add(commit_hash)
                commit = self.commits[commit_hash]
                
                # Apply filters
                if since and since == commit_hash:
                    continue
                
                if until and until == commit_hash:
                    break
                
                commits.append({
                    "hash": commit.commit_hash,
                    "author": commit.author_name,
                    "timestamp": commit.timestamp.isoformat(),
                    "message": commit.message,
                    "branch_name": commit.branch_name,
                    "parent_commits": commit.parent_commits,
                    "tree_hash": commit.tree_hash,
                    "changes_count": len(commit.changes)
                })
                
                # Add parents to visit list
                to_visit.extend(commit.parent_commits)
            
            # Sort by timestamp (newest first)
            commits.sort(key=lambda x: x["timestamp"], reverse=True)
            
            return {
                "success": True,
                "branch_name": branch_name,
                "head_commit": branch.head_commit,
                "commits": commits,
                "total_commits": len(commits),
                "message": f"Retrieved {len(commits)} commits"
            }
            
        except Exception as e:
            logger.error(f"Error getting commit history: {e}")
            return {
                "success": False,
                "error": f"Failed to get commit history: {str(e)}"
            }
    
    async def create_tag(
        self,
        tag_name: str,
        commit_hash: str,
        author_id: str,
        author_name: str,
        message: str = ""
    ) -> Dict[str, Any]:
        """
        Create a tag pointing to a specific commit.
        
        Args:
            tag_name: Name of tag
            commit_hash: Hash of commit to tag
            author_id: ID of author creating tag
            author_name: Name of author
            message: Tag message
        
        Returns:
            Tag creation result
        """
        try:
            # Validate commit exists
            if commit_hash not in self.commits:
                return {
                    "success": False,
                    "error": f"Commit '{commit_hash}' not found"
                }
            
            # Validate tag name
            if tag_name in self.tags:
                return {
                    "success": False,
                    "error": f"Tag '{tag_name}' already exists"
                }
            
            # Create tag
            self.tags[tag_name] = commit_hash
            
            commit = self.commits[commit_hash]
            
            return {
                "success": True,
                "tag_name": tag_name,
                "commit_hash": commit_hash,
                "commit_message": commit.message,
                "author": author_name,
                "created_at": datetime.utcnow().isoformat(),
                "message": "Tag created successfully"
            }
            
        except Exception as e:
            logger.error(f"Error creating tag: {e}")
            return {
                "success": False,
                "error": f"Tag creation failed: {str(e)}"
            }
    
    async def revert_commit(
        self,
        commit_hash: str,
        author_id: str,
        author_name: str,
        revert_message: str,
        branch_name: str = None,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Revert a specific commit by creating a new revert commit.
        
        Args:
            commit_hash: Hash of commit to revert
            author_id: ID of author performing revert
            author_name: Name of author
            revert_message: Message for revert commit
            branch_name: Branch to create revert on (default: current head branch)
            db: Database session
        
        Returns:
            Revert result
        """
        try:
            # Validate commit exists
            if commit_hash not in self.commits:
                return {
                    "success": False,
                    "error": f"Commit '{commit_hash}' not found"
                }
            
            commit = self.commits[commit_hash]
            
            # Use specified branch or current head branch
            target_branch = branch_name or self.head_branch
            if target_branch not in self.branches:
                return {
                    "success": False,
                    "error": f"Branch '{target_branch}' does not exist"
                }
            
            # Create revert changes (inverse of original changes)
            revert_changes = []
            for change in commit.changes:
                revert_change = {
                    "change_type": "update" if change.change_type == ChangeType.CREATE else "create",
                    "item_type": change.item_type.value,
                    "item_id": change.item_id,
                    "previous_data": change.new_data,
                    "new_data": change.previous_data,
                    "metadata": {
                        "revert_of": commit_hash,
                        "original_change_type": change.change_type.value,
                        "original_change_id": change.change_id
                    }
                }
                revert_changes.append(revert_change)
            
            # Create revert commit
            commit_result = await self.create_commit(
                target_branch,
                author_id,
                author_name,
                f"Revert {commit_hash[:7]}: {revert_message}",
                revert_changes,
                [self.branches[target_branch].head_commit],
                db
            )
            
            if not commit_result["success"]:
                return commit_result
            
            return {
                "success": True,
                "revert_commit_hash": commit_result["commit_hash"],
                "original_commit_hash": commit_hash,
                "branch_name": target_branch,
                "reverted_changes_count": len(revert_changes),
                "message": "Commit reverted successfully"
            }
            
        except Exception as e:
            logger.error(f"Error reverting commit: {e}")
            return {
                "success": False,
                "error": f"Commit revert failed: {str(e)}"
            }
    
    async def get_branch_status(
        self,
        branch_name: str,
        db: AsyncSession = None
    ) -> Dict[str, Any]:
        """
        Get detailed status of a branch.
        
        Args:
            branch_name: Name of branch
            db: Database session
        
        Returns:
            Branch status information
        """
        try:
            if branch_name not in self.branches:
                return {
                    "success": False,
                    "error": f"Branch '{branch_name}' does not exist"
                }
            
            branch = self.branches[branch_name]
            
            # Get commit count
            commit_history = await self.get_commit_history(branch_name, limit=1000)
            commits = commit_history.get("commits", [])
            
            # Get ahead/behind info compared to main branch
            ahead_behind = await self._get_ahead_behind(branch_name, "main")
            
            # Get recent activity
            recent_changes = [
                change for change in self.changes[-100:]
                if change.branch_name == branch_name
            ]
            
            # Calculate statistics
            changes_by_type = {}
            for change in recent_changes:
                change_type = change.change_type.value
                changes_by_type[change_type] = changes_by_type.get(change_type, 0) + 1
            
            return {
                "success": True,
                "branch_name": branch_name,
                "head_commit": branch.head_commit,
                "base_commit": branch.base_commit,
                "created_at": branch.created_at.isoformat(),
                "created_by": branch.created_by_name,
                "is_protected": branch.is_protected,
                "description": branch.description,
                "total_commits": len(commits),
                "total_changes": len(recent_changes),
                "changes_by_type": changes_by_type,
                "recent_activity": len([c for c in recent_changes if 
                    (datetime.utcnow() - c.timestamp).total_seconds() < 86400]),
                "ahead_of_main": ahead_behind["ahead"],
                "behind_main": ahead_behind["behind"],
                "last_commit": commits[0] if commits else None,
                "last_activity": max(
                    (c.timestamp for c in recent_changes),
                    default=branch.created_at
                ).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting branch status: {e}")
            return {
                "success": False,
                "error": f"Failed to get branch status: {str(e)}"
            }
    
    # Private Helper Methods
    
    def _initialize_main_branch(self):
        """Initialize the main branch."""
        if "main" not in self.branches:
            self.branches["main"] = GraphBranch(
                branch_name="main",
                created_at=datetime.utcnow(),
                created_by="system",
                created_by_name="System",
                is_protected=True,
                description="Main branch",
                metadata={"initial": True}
            )
    
    def _generate_commit_hash(self, content: Dict[str, Any]) -> str:
        """Generate SHA-256 hash for commit content."""
        try:
            content_str = json.dumps(content, sort_keys=True)
            return hashlib.sha256(content_str.encode()).hexdigest()
        except Exception:
            return str(uuid.uuid4())
    
    async def _calculate_tree_hash(
        self, 
        changes: List[GraphChange], 
        db: AsyncSession
    ) -> str:
        """Calculate hash for tree state based on changes."""
        try:
            # Create tree representation
            tree_items = []
            
            for change in changes:
                item_data = change.new_data if change.change_type != ChangeType.DELETE else change.previous_data
                if item_data:
                    tree_items.append({
                        "type": change.item_type.value,
                        "id": change.item_id,
                        "data": item_data,
                        "timestamp": change.timestamp.isoformat()
                    })
            
            # Sort items for consistent hash
            tree_items.sort(key=lambda x: f"{x['type']}_{x['id']}")
            
            # Generate hash
            tree_str = json.dumps(tree_items, sort_keys=True)
            return hashlib.sha256(tree_str.encode()).hexdigest()
            
        except Exception as e:
            logger.error(f"Error calculating tree hash: {e}")
            return str(uuid.uuid4())
    
    async def _update_graph_from_commit(
        self, 
        commit: GraphCommit, 
        db: AsyncSession
    ):
        """Update the actual knowledge graph from a commit."""
        try:
            if not db:
                return
            
            # Apply changes in order
            for change in commit.changes:
                if change.item_type == ItemType.NODE:
                    if change.change_type == ChangeType.CREATE:
                        await KnowledgeNodeCRUD.create(db, change.new_data)
                    elif change.change_type == ChangeType.UPDATE:
                        await KnowledgeNodeCRUD.update(db, change.item_id, change.new_data)
                    elif change.change_type == ChangeType.DELETE:
                        await KnowledgeNodeCRUD.delete(db, change.item_id)
                
                elif change.item_type == ItemType.RELATIONSHIP:
                    # Handle relationship changes
                    pass
                
                elif change.item_type == ItemType.PATTERN:
                    # Handle pattern changes
                    pass
                    
        except Exception as e:
            logger.error(f"Error updating graph from commit: {e}")
    
    async def _get_commits_since_base(
        self, 
        source_hash: str, 
        base_hash: str
    ) -> List[GraphCommit]:
        """Get commits on source branch since base branch."""
        try:
            # This is a simplified implementation
            # In real Git, this would walk the commit graph
            commits = []
            visited = set()
            to_visit = [source_hash]
            
            while to_visit:
                commit_hash = to_visit.pop(0)
                
                if commit_hash in visited or commit_hash not in self.commits:
                    continue
                
                visited.add(commit_hash)
                commit = self.commits[commit_hash]
                commits.append(commit)
                
                # Stop if we reach the base commit
                if commit_hash == base_hash:
                    break
                
                # Add parents to visit list
                to_visit.extend(commit.parent_commits)
            
            return commits
            
        except Exception as e:
            logger.error(f"Error getting commits since base: {e}")
            return []
    
    async def _detect_merge_conflicts(
        self, 
        source_commits: List[GraphCommit], 
        target_hash: str,
        db: AsyncSession
    ) -> List[Dict[str, Any]]:
        """Detect conflicts between source and target branches."""
        try:
            conflicts = []
            
            # Get target commit changes
            target_commit = self.commits.get(target_hash)
            target_changes = set()
            if target_commit:
                target_changes = {
                    (change.item_type, change.item_id) for change in target_commit.changes
                    if change.change_type in [ChangeType.CREATE, ChangeType.UPDATE]
                }
            
            # Check for conflicts in source commits
            source_changes = {}
            for commit in source_commits:
                for change in commit.changes:
                    key = (change.item_type, change.item_id)
                    
                    if key in source_changes:
                        # Multiple changes to same item in source
                        source_changes[key].append(change)
                    else:
                        source_changes[key] = [change]
            
            # Find conflicts
            for key, source_change_list in source_changes.items():
                if key in target_changes:
                    # Same item modified in both branches
                    conflicts.append({
                        "type": "edit_conflict",
                        "item_type": key[0].value,
                        "item_id": key[1],
                        "source_changes": [
                            {
                                "change_id": change.change_id,
                                "change_type": change.change_type.value,
                                "author": change.author_name,
                                "timestamp": change.timestamp.isoformat(),
                                "new_data": change.new_data
                            }
                            for change in source_change_list
                        ],
                        "target_change": {
                            "item_type": key[0].value,
                            "item_id": key[1],
                            "modified_in_target": True
                        }
                    })
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Error detecting merge conflicts: {e}")
            return []
    
    async def _auto_resolve_conflict(
        self, 
        conflict: Dict[str, Any], 
        merge_strategy: str
    ) -> Optional[Dict[str, Any]]:
        """Attempt to auto-resolve a conflict."""
        try:
            if conflict["type"] == "edit_conflict":
                source_changes = conflict["source_changes"]
                
                # Simple auto-resolution: use the latest change
                if source_changes:
                    latest_change = max(
                        source_changes,
                        key=lambda x: datetime.fromisoformat(x["timestamp"])
                    )
                    
                    return {
                        "conflict_id": str(uuid.uuid4()),
                        "resolution_type": "auto",
                        "resolution_strategy": "use_latest",
                        "resolved_data": latest_change["new_data"],
                        "resolved_by": "system",
                        "resolved_at": datetime.utcnow().isoformat()
                    }
            
            # Could add more sophisticated auto-resolution strategies here
            return None
            
        except Exception as e:
            logger.error(f"Error auto-resolving conflict: {e}")
            return None
    
    async def _get_changes_between_commits(
        self, 
        base_hash: str, 
        target_hash: str
    ) -> List[GraphChange]:
        """Get changes between two commits."""
        try:
            # Simplified implementation
            # In real Git, this would walk the commit DAG
            changes = []
            visited = set()
            to_visit = [target_hash]
            
            while to_visit:
                commit_hash = to_visit.pop(0)
                
                if commit_hash in visited or commit_hash not in self.commits:
                    continue
                
                visited.add(commit_hash)
                commit = self.commits[commit_hash]
                
                if commit_hash == base_hash:
                    break
                
                # Add changes
                changes.extend(commit.changes)
                
                # Add parents to visit list
                to_visit.extend(commit.parent_commits)
            
            return changes
            
        except Exception as e:
            logger.error(f"Error getting changes between commits: {e}")
            return []
    
    def _count_changes_by_type(self, changes: List[GraphChange]) -> Dict[str, int]:
        """Count changes by type."""
        counts = {}
        for change in changes:
            change_type = f"{change.change_type.value}_{change.item_type.value}"
            counts[change_type] = counts.get(change_type, 0) + 1
        return counts
    
    async def _get_ahead_behind(
        self, 
        branch_name: str, 
        target_branch: str
    ) -> Dict[str, int]:
        """Get ahead/behind counts for branch compared to target."""
        try:
            if branch_name not in self.branches or target_branch not in self.branches:
                return {"ahead": 0, "behind": 0}
            
            branch = self.branches[branch_name]
            target = self.branches[target_branch]
            
            # Simplified implementation - count commits
            branch_history = await self.get_commit_history(branch_name, limit=1000)
            target_history = await self.get_commit_history(target_branch, limit=1000)
            
            branch_commits = set(c["hash"] for c in branch_history.get("commits", []))
            target_commits = set(c["hash"] for c in target_history.get("commits", []))
            
            ahead = len(branch_commits - target_commits)
            behind = len(target_commits - branch_commits)
            
            return {"ahead": ahead, "behind": behind}
            
        except Exception as e:
            logger.error(f"Error getting ahead/behind: {e}")
            return {"ahead": 0, "behind": 0}


# Singleton instance
graph_version_control_service = GraphVersionControlService()
