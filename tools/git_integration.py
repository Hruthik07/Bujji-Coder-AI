"""
Git Integration Service
Wrapper around GitPython for safe git operations
"""
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
import os
import time

try:
    import git
    from git import Repo, InvalidGitRepositoryError
    GIT_AVAILABLE = True
except ImportError:
    GIT_AVAILABLE = False
    git = None
    Repo = None
    InvalidGitRepositoryError = Exception


class GitService:
    """Service for git operations"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.repo = None
        self.is_repo = False
        
        # Caching for git status (5-10 second TTL)
        self._status_cache: Optional[Dict[str, Any]] = None
        self._status_cache_time: float = 0.0
        self._status_cache_ttl: float = 8.0  # 8 seconds
        
        if not GIT_AVAILABLE:
            return
        
        # Try to initialize git repo
        try:
            self.repo = Repo(self.workspace_path)
            self.is_repo = True
        except InvalidGitRepositoryError:
            self.is_repo = False
        except Exception:
            self.is_repo = False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get repository status with caching to improve performance.
        
        Returns:
            dict with staged, unstaged, untracked files, branch, and is_repo flag
        """
        # Early return if not a git repo
        if not self.is_repo or not self.repo:
            return {
                "staged": [],
                "unstaged": [],
                "untracked": [],
                "branch": None,
                "is_repo": False,
                "has_changes": False
            }
        
        # Check cache first
        current_time = time.time()
        if (self._status_cache is not None and 
            current_time - self._status_cache_time < self._status_cache_ttl):
            return self._status_cache
        
        # Cache miss or expired, compute status
        try:
            # Get current branch
            try:
                branch = self.repo.active_branch.name
            except Exception:
                branch = "detached"
            
            # Get status
            staged = []
            unstaged = []
            untracked = []
            
            # Get staged changes (index vs HEAD) - limit to prevent timeout
            try:
                diff_head = self.repo.index.diff("HEAD")
                for item in list(diff_head)[:100]:  # Limit to 100 items
                    path = item.a_path if hasattr(item, 'a_path') and item.a_path else item.b_path
                    staged.append({
                        "path": path,
                        "status": item.change_type,
                        "old_path": getattr(item, 'a_path', None),
                        "new_path": getattr(item, 'b_path', None)
                    })
            except Exception as e:
                # If diff fails, continue with empty staged
                pass
            
            # Get unstaged changes (working tree vs index) - limit to prevent timeout
            try:
                diff_none = self.repo.index.diff(None)
                for item in list(diff_none)[:100]:  # Limit to 100 items
                    path = item.a_path if hasattr(item, 'a_path') and item.a_path else item.b_path
                    unstaged.append({
                        "path": path,
                        "status": item.change_type,
                        "old_path": getattr(item, 'a_path', None),
                        "new_path": getattr(item, 'b_path', None)
                    })
            except Exception as e:
                # If diff fails, continue with empty unstaged
                pass
            
            # Get untracked files - limit to prevent timeout
            try:
                untracked_paths = self.repo.untracked_files[:100]  # Limit to 100 items
                for path in untracked_paths:
                    untracked.append({
                        "path": path,
                        "status": "U"
                    })
            except Exception as e:
                # If untracked files fails, continue with empty untracked
                pass
            
            has_changes = len(staged) > 0 or len(unstaged) > 0 or len(untracked) > 0
            
            status = {
                "staged": staged,
                "unstaged": unstaged,
                "untracked": untracked,
                "branch": branch,
                "is_repo": True,
                "has_changes": has_changes
            }
            
            # Update cache
            self._status_cache = status
            self._status_cache_time = current_time
            
            return status
        except Exception as e:
            status = {
                "staged": [],
                "unstaged": [],
                "untracked": [],
                "branch": None,
                "is_repo": True,
                "has_changes": False,
                "error": str(e)
            }
            # Cache error result too (shorter TTL for errors)
            self._status_cache = status
            self._status_cache_time = current_time
            return status
    
    def invalidate_status_cache(self):
        """Invalidate the status cache (call after git operations)"""
        self._status_cache = None
        self._status_cache_time = 0.0
    
    def get_branches(self) -> Dict[str, Any]:
        """
        Get all branches (local and remote)
        
        Returns:
            dict with branches list, current branch, and remotes
        """
        if not self.is_repo or not self.repo:
            return {
                "branches": [],
                "current": None,
                "remotes": []
            }
        
        try:
            branches = []
            for branch in self.repo.branches:
                branches.append({
                    "name": branch.name,
                    "is_remote": False,
                    "is_current": branch == self.repo.active_branch
                })
            
            # Get remote branches
            remotes = []
            for remote in self.repo.remotes:
                for ref in remote.refs:
                    branch_name = ref.name.replace(f"{remote.name}/", "")
                    if branch_name not in [b["name"] for b in branches]:
                        branches.append({
                            "name": branch_name,
                            "is_remote": True,
                            "remote": remote.name,
                            "is_current": False
                        })
                    remotes.append({
                        "name": remote.name,
                        "url": remote.url
                    })
            
            current = self.repo.active_branch.name if self.repo.active_branch else None
            
            return {
                "branches": branches,
                "current": current,
                "remotes": list(set([r["name"] for r in remotes]))
            }
        except Exception as e:
            return {
                "branches": [],
                "current": None,
                "remotes": [],
                "error": str(e)
            }
    
    def get_current_branch(self) -> Optional[str]:
        """Get current branch name"""
        if not self.is_repo or not self.repo:
            return None
        
        try:
            return self.repo.active_branch.name
        except Exception:
            return None
    
    def stage_files(self, files: List[str]) -> Dict[str, Any]:
        """
        Stage specific files
        
        Args:
            files: List of file paths (relative to workspace)
            
        Returns:
            dict with success status and message
        """
        if not self.is_repo or not self.repo:
            return {"success": False, "message": "Not a git repository"}
        
        try:
            # Validate file paths
            staged_files = []
            for file_path in files:
                full_path = self.workspace_path / file_path
                if not full_path.exists():
                    continue
                
                # Ensure path is relative to workspace
                rel_path = str(full_path.relative_to(self.workspace_path))
                self.repo.index.add([rel_path])
                staged_files.append(rel_path)
            
            return {
                "success": True,
                "message": f"Staged {len(staged_files)} file(s)",
                "files": staged_files
            }
        except Exception as e:
            return {"success": False, "message": f"Error staging files: {str(e)}"}
    
    def unstage_files(self, files: List[str]) -> Dict[str, Any]:
        """
        Unstage files
        
        Args:
            files: List of file paths (relative to workspace)
            
        Returns:
            dict with success status and message
        """
        if not self.is_repo or not self.repo:
            return {"success": False, "message": "Not a git repository"}
        
        try:
            unstaged_files = []
            for file_path in files:
                full_path = self.workspace_path / file_path
                if not full_path.exists():
                    continue
                
                rel_path = str(full_path.relative_to(self.workspace_path))
                self.repo.index.reset([rel_path])
                unstaged_files.append(rel_path)
            
            return {
                "success": True,
                "message": f"Unstaged {len(unstaged_files)} file(s)",
                "files": unstaged_files
            }
        except Exception as e:
            return {"success": False, "message": f"Error unstaging files: {str(e)}"}
    
    def commit(self, message: str, files: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Create commit with message
        
        Args:
            message: Commit message
            files: Optional list of specific files to commit (if None, commits all staged)
            
        Returns:
            dict with success status, commit hash, and message
        """
        if not self.is_repo or not self.repo:
            return {"success": False, "message": "Not a git repository"}
        
        try:
            # Stage specific files if provided
            if files:
                self.stage_files(files)
            
            # Check if there are staged changes
            if not self.repo.index.diff("HEAD") and not self.repo.untracked_files:
                return {"success": False, "message": "No changes to commit"}
            
            # Create commit
            commit = self.repo.index.commit(message)
            
            return {
                "success": True,
                "commit_hash": commit.hexsha[:7],
                "message": message,
                "full_hash": commit.hexsha
            }
        except Exception as e:
            return {"success": False, "message": f"Error creating commit: {str(e)}"}
    
    def get_diff(self, file_path: Optional[str] = None, staged: bool = False) -> Dict[str, Any]:
        """
        Get diff for file or all changes
        
        Args:
            file_path: Optional file path (if None, returns all diffs)
            staged: If True, get staged diff, else unstaged
            
        Returns:
            dict with diff text and file path
        """
        if not self.is_repo or not self.repo:
            return {"diff": "", "file": file_path or ""}
        
        try:
            if file_path:
                # Get diff for specific file
                full_path = self.workspace_path / file_path
                rel_path = str(full_path.relative_to(self.workspace_path))
                
                if staged:
                    # Staged diff
                    diff_index = self.repo.index.diff("HEAD", paths=[rel_path])
                else:
                    # Unstaged diff
                    diff_index = self.repo.index.diff(None, paths=[rel_path])
                
                diff_text = ""
                for diff_item in diff_index:
                    diff_text += diff_item.diff.decode('utf-8', errors='ignore')
                
                return {"diff": diff_text, "file": rel_path}
            else:
                # Get all diffs
                if staged:
                    diff_index = self.repo.index.diff("HEAD")
                else:
                    diff_index = self.repo.index.diff(None)
                
                all_diffs = []
                for diff_item in diff_index:
                    diff_text = diff_item.diff.decode('utf-8', errors='ignore')
                    file_path = diff_item.a_path if hasattr(diff_item, 'a_path') else diff_item.b_path
                    all_diffs.append({
                        "file": file_path,
                        "diff": diff_text
                    })
                
                return {"diffs": all_diffs, "file": None}
        except Exception as e:
            return {"diff": "", "file": file_path or "", "error": str(e)}
    
    def switch_branch(self, branch_name: str) -> Dict[str, Any]:
        """
        Switch to a branch
        
        Args:
            branch_name: Name of branch to switch to
            
        Returns:
            dict with success status and branch name
        """
        if not self.is_repo or not self.repo:
            return {"success": False, "message": "Not a git repository"}
        
        try:
            # Check if branch exists
            if branch_name not in [b.name for b in self.repo.branches]:
                return {"success": False, "message": f"Branch '{branch_name}' not found"}
            
            # Switch branch
            self.repo.heads[branch_name].checkout()
            
            return {
                "success": True,
                "branch": branch_name,
                "message": f"Switched to branch '{branch_name}'"
            }
        except Exception as e:
            return {"success": False, "message": f"Error switching branch: {str(e)}"}
    
    def create_branch(self, branch_name: str) -> Dict[str, Any]:
        """
        Create a new branch
        
        Args:
            branch_name: Name of new branch
            
        Returns:
            dict with success status and branch name
        """
        if not self.is_repo or not self.repo:
            return {"success": False, "message": "Not a git repository"}
        
        try:
            # Check if branch already exists
            if branch_name in [b.name for b in self.repo.branches]:
                return {"success": False, "message": f"Branch '{branch_name}' already exists"}
            
            # Create and checkout branch
            new_branch = self.repo.create_head(branch_name)
            new_branch.checkout()
            
            return {
                "success": True,
                "branch": branch_name,
                "message": f"Created and switched to branch '{branch_name}'"
            }
        except Exception as e:
            return {"success": False, "message": f"Error creating branch: {str(e)}"}
    
    def get_commit_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent commit history
        
        Args:
            limit: Number of commits to return
            
        Returns:
            List of commit dicts with hash, message, author, date
        """
        if not self.is_repo or not self.repo:
            return []
        
        try:
            commits = []
            for commit in self.repo.iter_commits(max_count=limit):
                commits.append({
                    "hash": commit.hexsha[:7],
                    "full_hash": commit.hexsha,
                    "message": commit.message.strip(),
                    "author": commit.author.name,
                    "date": commit.committed_datetime.isoformat(),
                    "summary": commit.message.split('\n')[0].strip()
                })
            return commits
        except Exception as e:
            return []
