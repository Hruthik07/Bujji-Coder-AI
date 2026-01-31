"""
Diff-based code editing system
Implements unified diff parsing and application similar to Cursor AI
"""
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum


class DiffOperation(Enum):
    """Types of diff operations"""
    ADD = "+"
    REMOVE = "-"
    KEEP = " "


@dataclass
class DiffHunk:
    """Represents a hunk (block) of changes in a diff"""
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: List[Tuple[DiffOperation, str]]


@dataclass
class FileDiff:
    """Represents a diff for a single file"""
    old_path: str
    new_path: str
    hunks: List[DiffHunk]
    metadata: Optional[Dict] = None


class DiffEditor:
    """
    Parses and applies unified diffs to files.
    Similar to how Cursor AI applies code changes.
    """
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        # Initialize validation service
        try:
            from tools.validation_service import ValidationService
            self.validation_service = ValidationService(workspace_path=str(self.workspace_path))
        except Exception as e:
            print(f"⚠️  Validation service initialization failed: {e}")
            self.validation_service = None
    
    def parse_diff(self, diff_text: str) -> List[FileDiff]:
        """
        Parse a unified diff string into FileDiff objects.
        
        Args:
            diff_text: Unified diff string (may contain multiple files)
            
        Returns:
            List of FileDiff objects
        """
        file_diffs = []
        current_file = None
        current_hunks = []
        current_hunk = None
        
        lines = diff_text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # File header: --- a/path or +++ b/path
            if line.startswith('---'):
                # Save previous file if exists
                if current_file:
                    file_diffs.append(current_file)
                
                old_path = self._extract_path(line)
                new_path = None
                
                # Look for +++ line
                if i + 1 < len(lines) and lines[i + 1].startswith('+++'):
                    new_path = self._extract_path(lines[i + 1])
                    i += 1
                
                current_file = FileDiff(
                    old_path=old_path or "",
                    new_path=new_path or old_path or "",
                    hunks=[]
                )
                current_hunks = []
            
            # Hunk header: @@ -old_start,old_count +new_start,new_count @@
            elif line.startswith('@@'):
                if current_file:
                    hunk_info = self._parse_hunk_header(line)
                    if hunk_info:
                        current_hunk = DiffHunk(
                            old_start=hunk_info['old_start'],
                            old_count=hunk_info['old_count'],
                            new_start=hunk_info['new_start'],
                            new_count=hunk_info['new_count'],
                            lines=[]
                        )
                        current_hunks.append(current_hunk)
            
            # Diff line: +, -, or space
            elif line.startswith(('+', '-', ' ')) and current_hunk:
                operation = DiffOperation.ADD if line.startswith('+') else \
                           DiffOperation.REMOVE if line.startswith('-') else \
                           DiffOperation.KEEP
                content = line[1:] if line.startswith(('+', '-', ' ')) else line
                current_hunk.lines.append((operation, content))
            
            i += 1
        
        # Save last file
        if current_file:
            current_file.hunks = current_hunks
            file_diffs.append(current_file)
        
        return file_diffs
    
    def apply_diff(self, file_diff: FileDiff, dry_run: bool = False) -> Dict[str, Any]:
        """
        Apply a FileDiff to the actual file.
        
        Args:
            file_diff: FileDiff object to apply
            dry_run: If True, only validate without applying
            
        Returns:
            dict with success status and details
        """
        file_path = self._resolve_path(file_diff.new_path or file_diff.old_path)
        
        if not file_path.exists() and file_diff.old_path:
            return {
                "success": False,
                "error": f"File not found: {file_path}",
                "file": str(file_path)
            }
        
        try:
            # Read current file content
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    current_lines = f.readlines()
            else:
                current_lines = []
            
            # Apply hunks
            new_lines = current_lines.copy()
            offset = 0  # Track line number shifts
            
            for hunk in file_diff.hunks:
                result = self._apply_hunk(new_lines, hunk, file_diff.old_path and file_path.exists())
                if not result["success"]:
                    return {
                        "success": False,
                        "error": result.get("error"),
                        "file": str(file_path),
                        "hunk": f"lines {hunk.old_start}-{hunk.old_start + hunk.old_count}"
                    }
                new_lines = result["lines"]
                offset += (hunk.new_count - hunk.old_count)
            
            if not dry_run:
                # Write modified content
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.writelines(new_lines)
            
            return {
                "success": True,
                "file": str(file_path),
                "hunks_applied": len(file_diff.hunks),
                "dry_run": dry_run
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "file": str(file_path)
            }
    
    def apply_diffs(self, diffs: List[FileDiff], dry_run: bool = False) -> Dict[str, Any]:
        """
        Apply multiple file diffs.
        
        Args:
            diffs: List of FileDiff objects
            dry_run: If True, only validate without applying
            
        Returns:
            dict with results for each file
        """
        results = {
            "success": True,
            "files": [],
            "errors": []
        }
        
        for file_diff in diffs:
            result = self.apply_diff(file_diff, dry_run=dry_run)
            results["files"].append(result)
            
            if not result["success"]:
                results["success"] = False
                results["errors"].append({
                    "file": result.get("file"),
                    "error": result.get("error")
                })
        
        return results
    
    def generate_diff(self, old_content: str, new_content: str, 
                     file_path: str = "file.txt") -> str:
        """
        Generate a unified diff from old and new content.
        
        Args:
            old_content: Original file content
            new_content: New file content
            file_path: Path to the file
            
        Returns:
            Unified diff string
        """
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        # Simple diff algorithm (could use difflib for better results)
        from difflib import unified_diff
        
        diff_lines = list(unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=''
        ))
        
        return '\n'.join(diff_lines)
    
    def preview_diff(self, diff_text: str) -> Dict[str, Any]:
        """
        Preview a diff without applying it.
        Shows what would change.
        
        Args:
            diff_text: Unified diff string
            
        Returns:
            dict with preview information
        """
        file_diffs = self.parse_diff(diff_text)
        
        preview = {
            "files_affected": len(file_diffs),
            "files": []
        }
        
        for file_diff in file_diffs:
            file_path = file_diff.new_path or file_diff.old_path
            file_info = {
                "file": file_path,
                "hunks": len(file_diff.hunks),
                "changes": {
                    "additions": 0,
                    "deletions": 0,
                    "modifications": 0
                }
            }
            
            for hunk in file_diff.hunks:
                for op, line in hunk.lines:
                    if op == DiffOperation.ADD:
                        file_info["changes"]["additions"] += 1
                    elif op == DiffOperation.REMOVE:
                        file_info["changes"]["deletions"] += 1
                    elif op == DiffOperation.KEEP and line.strip():
                        file_info["changes"]["modifications"] += 1
            
            preview["files"].append(file_info)
        
        return preview
    
    def validate_diff(self, diff_text: str, use_validation_service: bool = True) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """
        Validate that a diff can be applied safely.
        
        Args:
            diff_text: Unified diff string
            use_validation_service: If True, use ValidationService for detailed validation
            
        Returns:
            Tuple of (is_valid, error_message, validation_result_dict)
        """
        validation_results = {}
        
        try:
            file_diffs = self.parse_diff(diff_text)
            
            if not file_diffs:
                return False, "No valid diff found", None
            
            for file_diff in file_diffs:
                file_path = self._resolve_path(file_diff.new_path or file_diff.old_path)
                rel_path = str(file_path.relative_to(self.workspace_path))
                
                # Check if file exists (for modifications)
                if file_diff.old_path and not file_path.exists():
                    return False, f"File does not exist: {file_path}", None
                
                # Validate hunks
                for hunk in file_diff.hunks:
                    if hunk.old_start < 1 or hunk.new_start < 1:
                        return False, f"Invalid hunk start line: {hunk.old_start}", None
                    
                    if file_path.exists():
                        with open(file_path, 'r', encoding='utf-8') as f:
                            lines = f.readlines()
                        
                        # Check if hunk range is valid
                        if hunk.old_start > len(lines):
                            return False, f"Hunk start line {hunk.old_start} exceeds file length {len(lines)}", None
                
                # If validation service is available, validate the resulting file content
                if use_validation_service and self.validation_service:
                    try:
                        # Apply diff to get new content
                        new_content = self._get_file_content_after_diff(file_diff)
                        if new_content is not None:
                            # Validate the new content
                            validation_result = self.validation_service.validate_file(rel_path, new_content)
                            validation_results[rel_path] = {
                                "valid": validation_result.valid,
                                "syntax_valid": validation_result.syntax_valid,
                                "type_check_passed": validation_result.type_check_passed,
                                "linter_passed": validation_result.linter_passed,
                                "issues": [
                                    {
                                        "severity": issue.severity.value,
                                        "line_number": issue.line_number,
                                        "column": issue.column,
                                        "message": issue.message,
                                        "rule": issue.rule
                                    }
                                    for issue in validation_result.issues
                                ]
                            }
                            
                            # If there are critical errors, mark as invalid
                            if not validation_result.valid or any(
                                issue.severity.value == "error" for issue in validation_result.issues
                            ):
                                error_messages = [
                                    f"{issue.message} (line {issue.line_number})"
                                    for issue in validation_result.issues
                                    if issue.severity.value == "error"
                                ]
                                if error_messages:
                                    return False, f"Validation errors: {'; '.join(error_messages[:3])}", validation_results
                    except Exception as e:
                        # Validation failed, but don't block diff application
                        print(f"⚠️  Validation error: {e}")
            
            return True, None, validation_results if validation_results else None
        
        except Exception as e:
            return False, str(e), None
    
    def _get_file_content_after_diff(self, file_diff: FileDiff) -> Optional[str]:
        """Apply diff to get the resulting file content (without saving)"""
        try:
            file_path = self._resolve_path(file_diff.new_path or file_diff.old_path)
            
            # Read original content
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
            else:
                lines = []
            
            # Apply all hunks
            for hunk in file_diff.hunks:
                result = self._apply_hunk(lines, hunk, file_path.exists())
                if not result.get("success"):
                    return None
                lines = result["new_lines"]
            
            return ''.join(lines)
        except Exception as e:
            print(f"⚠️  Error getting file content after diff: {e}")
            return None
    
    def _apply_hunk(self, lines: List[str], hunk: DiffHunk, 
                   file_exists: bool) -> Dict[str, Any]:
        """Apply a single hunk to lines"""
        try:
            # Convert to 0-based indexing
            start_idx = hunk.old_start - 1
            
            # Remove old lines
            removed = []
            for i in range(hunk.old_count):
                if start_idx + i < len(lines):
                    removed.append(lines[start_idx + i])
            
            # Build new lines from hunk
            new_lines = []
            for op, content in hunk.lines:
                if op == DiffOperation.ADD:
                    new_lines.append(content + ('\n' if not content.endswith('\n') else ''))
                elif op == DiffOperation.KEEP:
                    new_lines.append(content + ('\n' if not content.endswith('\n') else ''))
                # REMOVE lines are skipped
            
            # Replace in original lines
            result_lines = lines[:start_idx] + new_lines + lines[start_idx + hunk.old_count:]
            
            return {
                "success": True,
                "lines": result_lines
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _parse_hunk_header(self, header: str) -> Optional[Dict[str, int]]:
        """Parse a hunk header: @@ -old_start,old_count +new_start,new_count @@"""
        pattern = r'@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@'
        match = re.match(pattern, header)
        
        if match:
            return {
                "old_start": int(match.group(1)),
                "old_count": int(match.group(2) or 1),
                "new_start": int(match.group(3)),
                "new_count": int(match.group(4) or 1)
            }
        return None
    
    def _extract_path(self, line: str) -> Optional[str]:
        """Extract file path from --- or +++ line"""
        # Format: --- a/path or +++ b/path
        parts = line.split(None, 2)
        if len(parts) >= 2:
            path = parts[1]
            # Remove a/ or b/ prefix if present
            if '/' in path:
                path = '/'.join(path.split('/')[1:])
            return path
        return None
    
    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to workspace"""
        p = Path(file_path)
        if p.is_absolute():
            return p
        return self.workspace_path / p
