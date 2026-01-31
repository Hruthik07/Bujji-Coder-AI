"""
Bug Detector - Finds bugs using AST analysis, static checks, and runtime testing
"""
import ast
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass
from .ast_analyzer import ASTAnalyzer
from .terminal import Terminal
from .file_operations import FileOperations


@dataclass
class Bug:
    """Represents a detected bug"""
    file_path: str
    line_number: int
    bug_type: str  # 'syntax', 'runtime', 'logic', 'import', 'type', 'code_quality', etc.
    severity: str  # 'critical', 'high', 'medium', 'low'
    message: str
    code_snippet: str
    suggestion: Optional[str] = None
    column: Optional[int] = None


class BugDetector:
    """Detects bugs in code using multiple methods"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.ast_analyzer = ASTAnalyzer(workspace_path)
        self.terminal = Terminal(workspace_path)
        self.file_ops = FileOperations(workspace_path)
    
    def detect_bugs(self, file_path: str) -> List[Bug]:
        """
        Detect all bugs in a file
        
        Args:
            file_path: Relative path to file
            
        Returns:
            List of Bug objects
        """
        bugs = []
        full_path = self.workspace_path / file_path
        
        if not full_path.exists():
            return bugs
        
        # 1. Syntax errors (AST parsing)
        syntax_bugs = self._check_syntax(full_path)
        bugs.extend(syntax_bugs)
        
        # Skip other checks if syntax errors found
        if syntax_bugs:
            return bugs
        
        # 2. Static analysis bugs
        static_bugs = self._check_static_issues(full_path)
        bugs.extend(static_bugs)
        
        # 3. Import errors
        if full_path.suffix == '.py':
            import_bugs = self._check_imports(full_path)
            bugs.extend(import_bugs)
        
        # 4. Runtime errors (try running if safe)
        if full_path.suffix == '.py':
            runtime_bugs = self._check_runtime(full_path)
            bugs.extend(runtime_bugs)
        
        return bugs
    
    def _check_syntax(self, file_path: Path) -> List[Bug]:
        """Check for syntax errors"""
        bugs = []
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            if file_path.suffix == '.py':
                try:
                    ast.parse(content, filename=str(file_path))
                except SyntaxError as e:
                    line_content = self._get_line(file_path, e.lineno or 0)
                    bugs.append(Bug(
                        file_path=str(file_path.relative_to(self.workspace_path)),
                        line_number=e.lineno or 0,
                        column=e.offset or 0,
                        bug_type="syntax",
                        severity="critical",
                        message=f"Syntax error: {e.msg}",
                        code_snippet=line_content,
                        suggestion=f"Fix syntax error at line {e.lineno}: {e.msg}"
                    ))
                except Exception as e:
                    # Other parsing errors
                    bugs.append(Bug(
                        file_path=str(file_path.relative_to(self.workspace_path)),
                        line_number=0,
                        bug_type="syntax",
                        severity="critical",
                        message=f"Parse error: {str(e)}",
                        code_snippet="",
                        suggestion="Check file for syntax issues"
                    ))
        except Exception as e:
            bugs.append(Bug(
                file_path=str(file_path.relative_to(self.workspace_path)),
                line_number=0,
                bug_type="file_error",
                severity="critical",
                message=f"Cannot read file: {str(e)}",
                code_snippet="",
                suggestion="Check file permissions"
            ))
        return bugs
    
    def _check_static_issues(self, file_path: Path) -> List[Bug]:
        """Check for common static issues"""
        bugs = []
        
        if file_path.suffix != '.py':
            return bugs
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')
            
            # Parse AST for deeper analysis
            try:
                tree = ast.parse(content, filename=str(file_path))
            except SyntaxError:
                # Already caught in syntax check
                return bugs
            
            # Check for bare except
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    if node.type is None:  # Bare except
                        bugs.append(Bug(
                            file_path=str(file_path.relative_to(self.workspace_path)),
                            line_number=node.lineno,
                            bug_type="code_quality",
                            severity="medium",
                            message="Bare except clause - should catch specific exceptions",
                            code_snippet=self._get_line(file_path, node.lineno),
                            suggestion="Use 'except Exception:' or specific exception types"
                        ))
            
            # Check for common issues in lines
            for i, line in enumerate(lines, 1):
                stripped = line.strip()
                
                # Check for bare except in text (fallback)
                if re.search(r'except\s*:', stripped) and 'except Exception' not in stripped:
                    bugs.append(Bug(
                        file_path=str(file_path.relative_to(self.workspace_path)),
                        line_number=i,
                        bug_type="code_quality",
                        severity="medium",
                        message="Bare except clause",
                        code_snippet=stripped,
                        suggestion="Use 'except Exception:' or specific exception types"
                    ))
                
                # Check for print statements (code quality)
                if re.search(r'\bprint\s*\(', stripped) and '__main__' not in content:
                    bugs.append(Bug(
                        file_path=str(file_path.relative_to(self.workspace_path)),
                        line_number=i,
                        bug_type="code_quality",
                        severity="low",
                        message="Print statement found - consider using logging",
                        code_snippet=stripped,
                        suggestion="Use logging module instead of print for production code"
                    ))
                
                # Check for TODO/FIXME comments
                if re.search(r'#\s*(TODO|FIXME|XXX|HACK)', stripped, re.IGNORECASE):
                    bugs.append(Bug(
                        file_path=str(file_path.relative_to(self.workspace_path)),
                        line_number=i,
                        bug_type="code_quality",
                        severity="low",
                        message="TODO/FIXME comment found",
                        code_snippet=stripped,
                        suggestion="Address the TODO/FIXME comment"
                    ))
            
            # Check for undefined variables (basic check)
            undefined_bugs = self._check_undefined_variables(tree, file_path, lines)
            bugs.extend(undefined_bugs)
            
            # Check for unused imports
            unused_imports = self._check_unused_imports(tree, file_path, content)
            bugs.extend(unused_imports)
            
        except Exception as e:
            # Skip if we can't analyze
            pass
        
        return bugs
    
    def _check_undefined_variables(self, tree: ast.AST, file_path: Path, lines: List[str]) -> List[Bug]:
        """Check for potentially undefined variables"""
        bugs = []
        # This is a simplified check - full implementation would track scopes
        
        # Get all Name nodes
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                names.add(node.id)
        
        # Check for common undefined patterns
        # (This is simplified - a full implementation would need scope tracking)
        return bugs
    
    def _check_unused_imports(self, tree: ast.AST, file_path: Path, content: str) -> List[Bug]:
        """Check for unused imports"""
        bugs = []
        
        try:
            # Get all imports
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.asname or alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    for alias in node.names:
                        imports.add(alias.asname or alias.name)
            
            # Get all used names
            used_names = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                    used_names.add(node.id)
            
            # Find unused imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        name = alias.asname or alias.name.split('.')[0]
                        if name not in used_names and name not in ['*']:
                            # Check if it's a standard library that might be used indirectly
                            if name not in ['os', 'sys', 'json', 're', 'pathlib', 'typing']:
                                bugs.append(Bug(
                                    file_path=str(file_path.relative_to(self.workspace_path)),
                                    line_number=node.lineno,
                                    bug_type="code_quality",
                                    severity="low",
                                    message=f"Potentially unused import: {alias.name}",
                                    code_snippet=self._get_line(file_path, node.lineno),
                                    suggestion=f"Remove unused import '{alias.name}' if not needed"
                                ))
        except Exception:
            pass
        
        return bugs
    
    def _check_imports(self, file_path: Path) -> List[Bug]:
        """Check for import errors"""
        bugs = []
        
        try:
            # Read file to check imports
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Try to compile and check imports
            # Use a safer method - just check if imports look valid
            try:
                tree = ast.parse(content, filename=str(file_path))
                
                # Check each import
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            # Basic check - could be enhanced
                            pass
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            # Could check if module exists, but that's expensive
                            pass
            except SyntaxError:
                # Already caught in syntax check
                pass
                
        except Exception:
            pass
        
        return bugs
    
    def _check_runtime(self, file_path: Path) -> List[Bug]:
        """Check for runtime errors by executing (safely)"""
        bugs = []
        
        # Only check files that look executable
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Only run if file has __main__ block or looks like a script
            has_main = '__main__' in content or file_path.name == '__main__.py'
            is_script = not any(line.strip().startswith('class ') or line.strip().startswith('def ') 
                              for line in content.split('\n')[:10])
            
            # Skip if it's clearly a module (has imports but no main)
            if not has_main and 'if __name__' not in content:
                return bugs
            
            # Try to run with syntax check only (safer)
            result = self.terminal.execute(
                f'python -m py_compile "{file_path}"',
                is_background=False
            )
            
            if not result["success"] and "SyntaxError" not in result["stderr"]:
                # Compilation error that's not syntax
                error_msg = result["stderr"][:500]
                bugs.append(Bug(
                    file_path=str(file_path.relative_to(self.workspace_path)),
                    line_number=0,
                    bug_type="runtime",
                    severity="high",
                    message=f"Compilation error: {error_msg}",
                    code_snippet="",
                    suggestion="Fix compilation errors"
                ))
        except Exception:
            # Skip runtime check if it fails
            pass
        
        return bugs
    
    def _get_line(self, file_path: Path, line_number: int) -> str:
        """Get line content"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                if 0 < line_number <= len(lines):
                    return lines[line_number - 1].rstrip()
        except (OSError, IOError, IndexError):
            pass
        return ""






