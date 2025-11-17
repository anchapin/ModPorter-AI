"""
Version Control API Endpoints

This module provides REST API endpoints for knowledge graph version control,
including commits, branches, merging, and history tracking.
"""

import logging
from typing import Dict, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_db
from ..services.graph_version_control import graph_version_control_service

logger = logging.getLogger(__name__)

router = APIRouter()


# Commit Endpoints

@router.post("/commits")
async def create_commit(
    commit_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Create a new commit in the knowledge graph."""
    try:
        branch_name = commit_data.get("branch_name", "main")
        author_id = commit_data.get("author_id")
        author_name = commit_data.get("author_name")
        message = commit_data.get("message")
        changes = commit_data.get("changes", [])
        parent_commits = commit_data.get("parent_commits")
        
        if not all([author_id, author_name, message]):
            raise HTTPException(
                status_code=400,
                detail="author_id, author_name, and message are required"
            )
        
        result = await graph_version_control_service.create_commit(
            branch_name, author_id, author_name, message, changes, parent_commits, db
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating commit: {e}")
        raise HTTPException(status_code=500, detail=f"Commit creation failed: {str(e)}")


@router.get("/commits/{commit_hash}")
async def get_commit(commit_hash: str):
    """Get details of a specific commit."""
    try:
        if commit_hash not in graph_version_control_service.commits:
            raise HTTPException(
                status_code=404,
                detail="Commit not found"
            )
        
        commit = graph_version_control_service.commits[commit_hash]
        
        return {
            "success": True,
            "commit": {
                "hash": commit.commit_hash,
                "author": commit.author_name,
                "timestamp": commit.timestamp.isoformat(),
                "message": commit.message,
                "branch_name": commit.branch_name,
                "parent_commits": commit.parent_commits,
                "tree_hash": commit.tree_hash,
                "changes": [
                    {
                        "change_id": change.change_id,
                        "change_type": change.change_type.value,
                        "item_type": change.item_type.value,
                        "item_id": change.item_id,
                        "previous_data": change.previous_data,
                        "new_data": change.new_data,
                        "metadata": change.metadata
                    }
                    for change in commit.changes
                ],
                "metadata": commit.metadata
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting commit: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get commit: {str(e)}")


@router.get("/commits/{commit_hash}/changes")
async def get_commit_changes(commit_hash: str):
    """Get changes from a specific commit."""
    try:
        if commit_hash not in graph_version_control_service.commits:
            raise HTTPException(
                status_code=404,
                detail="Commit not found"
            )
        
        commit = graph_version_control_service.commits[commit_hash]
        
        changes = []
        for change in commit.changes:
            change_data = {
                "change_id": change.change_id,
                "change_type": change.change_type.value,
                "item_type": change.item_type.value,
                "item_id": change.item_id,
                "author": change.author_name,
                "timestamp": change.timestamp.isoformat(),
                "branch_name": change.branch_name,
                "previous_data": change.previous_data,
                "new_data": change.new_data,
                "metadata": change.metadata
            }
            changes.append(change_data)
        
        return {
            "success": True,
            "commit_hash": commit_hash,
            "changes": changes,
            "total_changes": len(changes)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting commit changes: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get commit changes: {str(e)}")


# Branch Endpoints

@router.post("/branches")
async def create_branch(branch_data: Dict[str, Any]):
    """Create a new branch."""
    try:
        branch_name = branch_data.get("branch_name")
        source_branch = branch_data.get("source_branch", "main")
        author_id = branch_data.get("author_id")
        author_name = branch_data.get("author_name")
        description = branch_data.get("description", "")
        
        if not all([branch_name, author_id, author_name]):
            raise HTTPException(
                status_code=400,
                detail="branch_name, author_id, and author_name are required"
            )
        
        result = await graph_version_control_service.create_branch(
            branch_name, source_branch, author_id, author_name, description
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating branch: {e}")
        raise HTTPException(status_code=500, detail=f"Branch creation failed: {str(e)}")


@router.get("/branches")
async def get_branches():
    """Get list of all branches."""
    try:
        branches = []
        
        for branch_name, branch in graph_version_control_service.branches.items():
            branches.append({
                "name": branch_name,
                "created_at": branch.created_at.isoformat(),
                "created_by": branch.created_by_name,
                "head_commit": branch.head_commit,
                "base_commit": branch.base_commit,
                "is_protected": branch.is_protected,
                "description": branch.description,
                "metadata": branch.metadata
            })
        
        # Sort by creation date (newest first)
        branches.sort(key=lambda x: x["created_at"], reverse=True)
        
        return {
            "success": True,
            "branches": branches,
            "total_branches": len(branches),
            "default_branch": graph_version_control_service.head_branch
        }
        
    except Exception as e:
        logger.error(f"Error getting branches: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get branches: {str(e)}")


@router.get("/branches/{branch_name}")
async def get_branch(branch_name: str):
    """Get details of a specific branch."""
    try:
        if branch_name not in graph_version_control_service.branches:
            raise HTTPException(
                status_code=404,
                detail="Branch not found"
            )
        
        branch = graph_version_control_service.branches[branch_name]
        
        return {
            "success": True,
            "branch": {
                "name": branch_name,
                "created_at": branch.created_at.isoformat(),
                "created_by": branch.created_by_name,
                "head_commit": branch.head_commit,
                "base_commit": branch.base_commit,
                "is_protected": branch.is_protected,
                "description": branch.description,
                "metadata": branch.metadata
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting branch: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get branch: {str(e)}")


@router.get("/branches/{branch_name}/history")
async def get_branch_history(
    branch_name: str,
    limit: int = Query(50, le=1000, description="Maximum number of commits to return"),
    since: Optional[str] = Query(None, description="Get commits since this commit hash"),
    until: Optional[str] = Query(None, description="Get commits until this commit hash")
):
    """Get commit history for a branch."""
    try:
        result = await graph_version_control_service.get_commit_history(
            branch_name, limit, since, until
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting branch history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get branch history: {str(e)}")


@router.get("/branches/{branch_name}/status")
async def get_branch_status(branch_name: str):
    """Get detailed status of a branch."""
    try:
        result = await graph_version_control_service.get_branch_status(branch_name)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting branch status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get branch status: {str(e)}")


# Merge Endpoints

@router.post("/branches/{source_branch}/merge")
async def merge_branch(
    source_branch: str,
    merge_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Merge source branch into target branch."""
    try:
        target_branch = merge_data.get("target_branch")
        author_id = merge_data.get("author_id")
        author_name = merge_data.get("author_name")
        merge_message = merge_data.get("merge_message")
        merge_strategy = merge_data.get("merge_strategy", "merge_commit")
        
        if not all([target_branch, author_id, author_name]):
            raise HTTPException(
                status_code=400,
                detail="target_branch, author_id, and author_name are required"
            )
        
        result = await graph_version_control_service.merge_branch(
            source_branch, target_branch, author_id, author_name,
            merge_message, merge_strategy, db
        )
        
        if not result.success:
            raise HTTPException(
                status_code=400,
                detail=f"Merge failed: {', '.join(c.get('error', 'Unknown conflict') for c in result.conflicts)}"
            )
        
        return {
            "success": True,
            "merge_result": {
                "merge_commit_hash": result.merge_commit_hash,
                "conflicts_resolved": len(result.resolved_conflicts),
                "remaining_conflicts": len(result.conflicts),
                "merge_strategy": result.merge_strategy,
                "merged_changes_count": len(result.merged_changes),
                "message": result.message
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error merging branch: {e}")
        raise HTTPException(status_code=500, detail=f"Branch merge failed: {str(e)}")


# Diff Endpoints

@router.post("/diff")
async def generate_diff(
    diff_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Generate diff between two commits."""
    try:
        base_hash = diff_data.get("base_hash")
        target_hash = diff_data.get("target_hash")
        item_types = diff_data.get("item_types")
        
        if not all([base_hash, target_hash]):
            raise HTTPException(
                status_code=400,
                detail="base_hash and target_hash are required"
            )
        
        diff = await graph_version_control_service.generate_diff(
            base_hash, target_hash, item_types, db
        )
        
        return {
            "success": True,
            "diff": {
                "base_hash": diff.base_hash,
                "target_hash": diff.target_hash,
                "summary": {
                    "added_nodes": len(diff.added_nodes),
                    "modified_nodes": len(diff.modified_nodes),
                    "deleted_nodes": len(diff.deleted_nodes),
                    "added_relationships": len(diff.added_relationships),
                    "modified_relationships": len(diff.modified_relationships),
                    "deleted_relationships": len(diff.deleted_relationships),
                    "added_patterns": len(diff.added_patterns),
                    "modified_patterns": len(diff.modified_patterns),
                    "deleted_patterns": len(diff.deleted_patterns),
                    "total_changes": (
                        len(diff.added_nodes) + len(diff.modified_nodes) + len(diff.deleted_nodes) +
                        len(diff.added_relationships) + len(diff.modified_relationships) + len(diff.deleted_relationships) +
                        len(diff.added_patterns) + len(diff.modified_patterns) + len(diff.deleted_patterns)
                    ),
                    "conflicts": len(diff.conflicts)
                },
                "changes": {
                    "added_nodes": diff.added_nodes,
                    "modified_nodes": diff.modified_nodes,
                    "deleted_nodes": diff.deleted_nodes,
                    "added_relationships": diff.added_relationships,
                    "modified_relationships": diff.modified_relationships,
                    "deleted_relationships": diff.deleted_relationships,
                    "added_patterns": diff.added_patterns,
                    "modified_patterns": diff.modified_patterns,
                    "deleted_patterns": diff.deleted_patterns
                },
                "conflicts": diff.conflicts,
                "metadata": diff.metadata
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating diff: {e}")
        raise HTTPException(status_code=500, detail=f"Diff generation failed: {str(e)}")


# Revert Endpoints

@router.post("/commits/{commit_hash}/revert")
async def revert_commit(
    commit_hash: str,
    revert_data: Dict[str, Any],
    db: AsyncSession = Depends(get_db)
):
    """Revert a specific commit."""
    try:
        author_id = revert_data.get("author_id")
        author_name = revert_data.get("author_name")
        revert_message = revert_data.get("revert_message")
        branch_name = revert_data.get("branch_name")
        
        if not all([author_id, author_name]):
            raise HTTPException(
                status_code=400,
                detail="author_id and author_name are required"
            )
        
        result = await graph_version_control_service.revert_commit(
            commit_hash, author_id, author_name, revert_message, branch_name, db
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reverting commit: {e}")
        raise HTTPException(status_code=500, detail=f"Commit revert failed: {str(e)}")


# Tag Endpoints

@router.post("/tags")
async def create_tag(tag_data: Dict[str, Any]):
    """Create a new tag."""
    try:
        tag_name = tag_data.get("tag_name")
        commit_hash = tag_data.get("commit_hash")
        author_id = tag_data.get("author_id")
        author_name = tag_data.get("author_name")
        message = tag_data.get("message", "")
        
        if not all([tag_name, commit_hash, author_id, author_name]):
            raise HTTPException(
                status_code=400,
                detail="tag_name, commit_hash, author_id, and author_name are required"
            )
        
        result = await graph_version_control_service.create_tag(
            tag_name, commit_hash, author_id, author_name, message
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating tag: {e}")
        raise HTTPException(status_code=500, detail=f"Tag creation failed: {str(e)}")


@router.get("/tags")
async def get_tags():
    """Get list of all tags."""
    try:
        tags = []
        
        for tag_name, commit_hash in graph_version_control_service.tags.items():
            # Get commit details
            if commit_hash in graph_version_control_service.commits:
                commit = graph_version_control_service.commits[commit_hash]
                tags.append({
                    "name": tag_name,
                    "commit_hash": commit_hash,
                    "commit_message": commit.message,
                    "author": commit.author_name,
                    "timestamp": commit.timestamp.isoformat()
                })
        
        # Sort by timestamp (newest first)
        tags.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "success": True,
            "tags": tags,
            "total_tags": len(tags)
        }
        
    except Exception as e:
        logger.error(f"Error getting tags: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tags: {str(e)}")


@router.get("/tags/{tag_name}")
async def get_tag(tag_name: str):
    """Get details of a specific tag."""
    try:
        if tag_name not in graph_version_control_service.tags:
            raise HTTPException(
                status_code=404,
                detail="Tag not found"
            )
        
        commit_hash = graph_version_control_service.tags[tag_name]
        commit = graph_version_control_service.commits[commit_hash]
        
        return {
            "success": True,
            "tag": {
                "name": tag_name,
                "commit_hash": commit_hash,
                "commit": {
                    "hash": commit.commit_hash,
                    "author": commit.author_name,
                    "timestamp": commit.timestamp.isoformat(),
                    "message": commit.message,
                    "tree_hash": commit.tree_hash,
                    "changes_count": len(commit.changes)
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting tag: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get tag: {str(e)}")


# Utility Endpoints

@router.get("/status")
async def get_version_control_status():
    """Get overall version control system status."""
    try:
        total_commits = len(graph_version_control_service.commits)
        total_branches = len(graph_version_control_service.branches)
        total_tags = len(graph_version_control_service.tags)
        
        # Get current head
        head_branch = graph_version_control_service.head_branch
        head_commit = None
        if head_branch in graph_version_control_service.branches:
            head_commit = graph_version_control_service.branches[head_branch].head_commit
        
        # Get recent activity
        recent_commits = []
        for commit in graph_version_control_service.commits.values():
            recent_commits.append({
                "hash": commit.commit_hash,
                "author": commit.author_name,
                "timestamp": commit.timestamp.isoformat(),
                "message": commit.message,
                "branch": commit.branch_name
            })
        
        recent_commits.sort(key=lambda x: x["timestamp"], reverse=True)
        recent_commits = recent_commits[:10]
        
        return {
            "success": True,
            "status": {
                "total_commits": total_commits,
                "total_branches": total_branches,
                "total_tags": total_tags,
                "head_branch": head_branch,
                "head_commit": head_commit,
                "recent_commits": recent_commits,
                "protected_branches": [
                    name for name, branch in graph_version_control_service.branches.items()
                    if branch.is_protected
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting version control status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")


@router.get("/stats")
async def get_version_control_stats():
    """Get version control statistics."""
    try:
        commits_by_author = {}
        commits_by_branch = {}
        commits_by_type = {}
        commits_per_day = {}
        
        # Analyze commits
        for commit in graph_version_control_service.commits.values():
            # By author
            author = commit.author_name
            commits_by_author[author] = commits_by_author.get(author, 0) + 1
            
            # By branch
            branch = commit.branch_name
            commits_by_branch[branch] = commits_by_branch.get(branch, 0) + 1
            
            # By change type
            for change in commit.changes:
                change_type = f"{change.change_type.value}_{change.item_type.value}"
                commits_by_type[change_type] = commits_by_type.get(change_type, 0) + 1
            
            # By day
            date_key = commit.timestamp.strftime("%Y-%m-%d")
            commits_per_day[date_key] = commits_per_day.get(date_key, 0) + 1
        
        # Sort for ranking
        top_authors = sorted(commits_by_author.items(), key=lambda x: x[1], reverse=True)[:10]
        active_branches = sorted(commits_by_branch.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "success": True,
            "stats": {
                "total_commits": len(graph_version_control_service.commits),
                "total_branches": len(graph_version_control_service.branches),
                "total_tags": len(graph_version_control_service.tags),
                "top_authors": top_authors,
                "active_branches": active_branches,
                "change_types": commits_by_type,
                "commits_per_day": commits_per_day,
                "average_commits_per_author": sum(commits_by_author.values()) / len(commits_by_author) if commits_by_author else 0,
                "average_commits_per_branch": sum(commits_by_branch.values()) / len(commits_by_branch) if commits_by_branch else 0
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting version control stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


@router.get("/search")
async def search_commits(
    query: str = Query(..., description="Search query for commits"),
    author: Optional[str] = Query(None, description="Filter by author"),
    branch: Optional[str] = Query(None, description="Filter by branch"),
    limit: int = Query(50, le=1000, description="Maximum results")
):
    """Search commits by message, author, or content."""
    try:
        query_lower = query.lower()
        
        matching_commits = []
        for commit_hash, commit in graph_version_control_service.commits.values():
            # Apply filters
            if author and commit.author_name.lower() != author.lower():
                continue
            
            if branch and commit.branch_name != branch:
                continue
            
            # Search in message and changes
            matches = False
            
            # Search message
            if query_lower in commit.message.lower():
                matches = True
            
            # Search in changes
            if not matches:
                for change in commit.changes:
                    if query_lower in str(change.new_data).lower():
                        matches = True
                        break
                    if query_lower in str(change.previous_data).lower():
                        matches = True
                        break
            
            if matches:
                matching_commits.append({
                    "hash": commit.commit_hash,
                    "author": commit.author_name,
                    "timestamp": commit.timestamp.isoformat(),
                    "message": commit.message,
                    "branch": commit.branch_name,
                    "changes_count": len(commit.changes),
                    "tree_hash": commit.tree_hash
                })
        
        # Sort by timestamp (newest first)
        matching_commits.sort(key=lambda x: x["timestamp"], reverse=True)
        matching_commits = matching_commits[:limit]
        
        return {
            "success": True,
            "query": query,
            "filters": {
                "author": author,
                "branch": branch
            },
            "results": matching_commits,
            "total_results": len(matching_commits),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"Error searching commits: {e}")
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/changelog")
async def get_changelog(
    branch_name: str = Query("main", description="Branch to get changelog for"),
    since: Optional[str] = Query(None, description="Get changes since this commit hash"),
    limit: int = Query(100, le=1000, description="Maximum commits to include")
):
    """Get changelog for a branch."""
    try:
        # Get commit history
        history_result = await graph_version_control_service.get_commit_history(
            branch_name, limit, since
        )
        
        if not history_result["success"]:
            raise HTTPException(status_code=400, detail=history_result["error"])
        
        commits = history_result["commits"]
        
        # Generate changelog entries
        changelog = []
        for commit in commits:
            entry = {
                "date": commit["timestamp"],
                "hash": commit["hash"],
                "author": commit["author"],
                "message": commit["message"],
                "changes_summary": {
                    "total": commit["changes_count"],
                    "by_type": {}
                }
            }
            
            # Summarize changes by type
            if "changes" in commit:
                for change in commit["changes"]:
                    change_type = f"{change['change_type']}_{change['item_type']}"
                    entry["changes_summary"]["by_type"][change_type] = (
                        entry["changes_summary"]["by_type"].get(change_type, 0) + 1
                    )
            
            changelog.append(entry)
        
        # Group by date
        changelog_by_date = {}
        for entry in changelog:
            date = entry["date"][:10]  # YYYY-MM-DD
            if date not in changelog_by_date:
                changelog_by_date[date] = []
            changelog_by_date[date].append(entry)
        
        return {
            "success": True,
            "branch_name": branch_name,
            "since_commit": since,
            "total_commits": len(commits),
            "changelog_by_date": changelog_by_date,
            "summary": {
                "total_changes": sum(entry["changes_summary"]["total"] for entry in changelog),
                "date_range": {
                    "start": commits[-1]["timestamp"][:10] if commits else None,
                    "end": commits[0]["timestamp"][:10] if commits else None
                }
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting changelog: {e}")
        raise HTTPException(status_code=500, detail=f"Changelog generation failed: {str(e)}")
