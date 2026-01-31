"""
Code Scanner - Scans codebase for analysis
Finds all code files that should be analyzed
"""
from pathlib import Path
from typing import List, Dict, Optional, Any
import os


class CodeScanner:
    """Scans codebase to find all code files"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.supported_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs', '.cpp', '.c'}
        self.ignore_patterns = {
            '__pycache__', '.git', 'node_modules', '.venv', 'venv',
            '.vector_db', '.cache', 'dist', 'build', '.pytest_cache',
            '.mypy_cache', '.ruff_cache', 'target', '.idea', '.vscode',
            '*.pyc', '*.pyo', '*.pyd', '.DS_Store'
        }
    
    def scan_codebase(self, extensions: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Scan and return all code files with metadata
        
        Args:
            extensions: Optional list of extensions to include (default: all supported)
            
        Returns:
            List of file info dicts with path, absolute_path, extension, size
        """
        if extensions:
            self.supported_extensions = {f'.{ext.lstrip(".")}' for ext in extensions}
        
        files = []
        for file_path in self._walk_directory(self.workspace_path):
            if self._should_analyze(file_path):
                try:
                    stat = file_path.stat()
                    files.append({
                        "path": str(file_path.relative_to(self.workspace_path)),
                        "absolute_path": str(file_path),
                        "extension": file_path.suffix,
                        "size": stat.st_size,
                        "language": self._get_language(file_path.suffix)
                    })
                except (OSError, PermissionError):
                    # Skip files we can't access
                    continue
        
        return sorted(files, key=lambda x: x["path"])
    
    def _walk_directory(self, root: Path):
        """Walk directory recursively, skipping ignored paths"""
        try:
            for item in root.iterdir():
                # Skip ignored directories/files
                if any(ignore in item.name for ignore in self.ignore_patterns):
                    continue
                
                if item.is_file():
                    yield item
                elif item.is_dir():
                    # Skip hidden directories (except .cursor for our own files)
                    if item.name.startswith('.') and item.name != '.cursor':
                        continue
                    yield from self._walk_directory(item)
        except (PermissionError, OSError):
            # Skip directories we can't access
            pass
    
    def _should_analyze(self, file_path: Path) -> bool:
        """Check if file should be analyzed"""
        # Check extension
        if file_path.suffix not in self.supported_extensions:
            return False
        
        # Check if in ignored path
        path_str = str(file_path)
        if any(ignore in path_str for ignore in self.ignore_patterns):
            return False
        
        # Skip hidden files (except in .cursor)
        if file_path.name.startswith('.') and '.cursor' not in path_str:
            return False
        
        return True
    
    def _get_language(self, extension: str) -> str:
        """Get language name from extension"""
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.cpp': 'cpp',
            '.c': 'c'
        }
        return lang_map.get(extension, 'unknown')
    
    def get_file_count(self) -> Dict[str, int]:
        """Get count of files by language"""
        files = self.scan_codebase()
        counts = {}
        for file_info in files:
            lang = file_info["language"]
            counts[lang] = counts.get(lang, 0) + 1
        return counts






