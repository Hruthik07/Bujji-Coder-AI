"""
File operations module - handles reading, writing, and editing files
"""
import os
from pathlib import Path
from typing import Optional, List
from config import Config


class FileOperations:
    """Handles file reading, writing, and editing operations"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
    
    def read_file(self, file_path: str, offset: Optional[int] = None, limit: Optional[int] = None) -> dict:
        """
        Read a file from the filesystem.
        
        Args:
            file_path: Path to the file (relative or absolute)
            offset: Optional line number to start reading from
            limit: Optional number of lines to read
            
        Returns:
            dict with 'content', 'lines', 'exists', 'error' keys
        """
        try:
            full_path = self._resolve_path(file_path)
            
            if not full_path.exists():
                return {
                    "exists": False,
                    "content": None,
                    "error": f"File not found: {file_path}"
                }
            
            if full_path.is_dir():
                return {
                    "exists": False,
                    "content": None,
                    "error": f"Path is a directory: {file_path}"
                }
            
            # Check file size
            file_size = full_path.stat().st_size
            if file_size > Config.MAX_FILE_SIZE:
                return {
                    "exists": True,
                    "content": None,
                    "error": f"File too large ({file_size} bytes). Max size: {Config.MAX_FILE_SIZE} bytes"
                }
            
            with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            if offset is not None or limit is not None:
                start = offset - 1 if offset else 0
                end = start + limit if limit else len(lines)
                lines = lines[start:end]
            
            content = ''.join(lines)
            
            return {
                "exists": True,
                "content": content,
                "lines": len(lines),
                "path": str(full_path)
            }
            
        except Exception as e:
            return {
                "exists": False,
                "content": None,
                "error": str(e)
            }
    
    def write_file(self, file_path: str, contents: str) -> dict:
        """
        Write contents to a file (creates or overwrites).
        
        Args:
            file_path: Path to the file
            contents: Content to write
            
        Returns:
            dict with 'success', 'path', 'error' keys
        """
        try:
            full_path = self._resolve_path(file_path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(contents)
            
            return {
                "success": True,
                "path": str(full_path),
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "path": None,
                "error": str(e)
            }
    
    def search_replace(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> dict:
        """
        Perform exact string replacement in a file.
        
        Args:
            file_path: Path to the file
            old_string: Text to replace
            new_string: Replacement text
            replace_all: If True, replace all occurrences
            
        Returns:
            dict with 'success', 'replacements', 'error' keys
        """
        try:
            full_path = self._resolve_path(file_path)
            
            if not full_path.exists():
                return {
                    "success": False,
                    "replacements": 0,
                    "error": f"File not found: {file_path}"
                }
            
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if replace_all:
                count = content.count(old_string)
                new_content = content.replace(old_string, new_string)
            else:
                if old_string not in content:
                    return {
                        "success": False,
                        "replacements": 0,
                        "error": "old_string not found in file"
                    }
                count = 1
                new_content = content.replace(old_string, new_string, 1)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            return {
                "success": True,
                "replacements": count,
                "error": None
            }
        except Exception as e:
            return {
                "success": False,
                "replacements": 0,
                "error": str(e)
            }
    
    def list_directory(self, directory_path: str = ".", ignore_globs: Optional[List[str]] = None) -> dict:
        """
        List files and directories in a given path.
        
        Args:
            directory_path: Path to directory
            ignore_globs: Optional list of glob patterns to ignore
            
        Returns:
            dict with 'items', 'path', 'error' keys
        """
        try:
            full_path = self._resolve_path(directory_path)
            
            if not full_path.exists():
                return {
                    "items": [],
                    "path": str(full_path),
                    "error": f"Directory not found: {directory_path}"
                }
            
            if not full_path.is_dir():
                return {
                    "items": [],
                    "path": str(full_path),
                    "error": f"Path is not a directory: {directory_path}"
                }
            
            items = []
            for item in full_path.iterdir():
                # Skip dot-files by default
                if item.name.startswith('.'):
                    continue
                
                # Apply ignore patterns if provided
                if ignore_globs:
                    import fnmatch
                    if any(fnmatch.fnmatch(item.name, pattern) for pattern in ignore_globs):
                        continue
                
                items.append({
                    "name": item.name,
                    "path": str(item.relative_to(self.workspace_path)),
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None
                })
            
            return {
                "items": sorted(items, key=lambda x: (x["type"] == "file", x["name"])),
                "path": str(full_path),
                "error": None
            }
        except Exception as e:
            return {
                "items": [],
                "path": None,
                "error": str(e)
            }
    
    def _resolve_path(self, file_path: str) -> Path:
        """Resolve a file path relative to workspace or absolute"""
        path = Path(file_path)
        if path.is_absolute():
            return path
        return self.workspace_path / path

