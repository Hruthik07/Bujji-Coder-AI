"""
Validation Service
Pre-apply validation to catch syntax errors, type errors, and linting issues
"""
import ast
import subprocess
import tempfile
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues"""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation issue"""
    severity: ValidationSeverity
    file_path: str
    line_number: int
    column: Optional[int]
    message: str
    rule: Optional[str] = None  # Linter rule name
    fix_suggestion: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation for a file"""
    file_path: str
    valid: bool
    issues: List[ValidationIssue]
    syntax_valid: bool
    type_check_passed: Optional[bool] = None  # None if type checker not available
    linter_passed: Optional[bool] = None  # None if linter not available


class ValidationService:
    """Service for validating code before applying changes"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.temp_dir = None
    
    def validate_file(self, file_path: str, content: str) -> ValidationResult:
        """
        Validate a file's content.
        
        Args:
            file_path: Path to the file (relative to workspace)
            content: File content to validate
            
        Returns:
            ValidationResult with all issues found
        """
        full_path = self.workspace_path / file_path
        file_ext = full_path.suffix.lower()
        
        issues = []
        
        # Syntax validation
        syntax_valid = self._validate_syntax(content, file_ext)
        if not syntax_valid:
            syntax_issues = self._get_syntax_errors(content, file_ext)
            issues.extend(syntax_issues)
        
        # Type checking (if available)
        type_check_passed = None
        if file_ext == '.py':
            type_check_passed, type_issues = self._validate_types_python(full_path, content)
            issues.extend(type_issues)
        elif file_ext in ['.ts', '.tsx']:
            type_check_passed, type_issues = self._validate_types_typescript(full_path, content)
            issues.extend(type_issues)
        
        # Linter validation (if available)
        linter_passed = None
        if file_ext == '.py':
            linter_passed, linter_issues = self._lint_python(full_path, content)
            issues.extend(linter_issues)
        elif file_ext in ['.js', '.jsx', '.ts', '.tsx']:
            linter_passed, linter_issues = self._lint_javascript(full_path, content)
            issues.extend(linter_issues)
        
        # Determine overall validity (no errors)
        valid = syntax_valid and all(issue.severity == ValidationSeverity.ERROR for issue in issues) == False
        
        return ValidationResult(
            file_path=file_path,
            valid=valid,
            issues=issues,
            syntax_valid=syntax_valid,
            type_check_passed=type_check_passed,
            linter_passed=linter_passed
        )
    
    def validate_diff(self, diff_text: str, file_path: str) -> ValidationResult:
        """
        Validate a diff by applying it to a temp file and validating.
        
        Args:
            diff_text: Unified diff text
            file_path: Target file path
            
        Returns:
            ValidationResult
        """
        # Read original file
        full_path = self.workspace_path / file_path
        original_content = ""
        if full_path.exists():
            with open(full_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
        
        # Apply diff to temp file (simplified - would need proper diff application)
        # For now, we'll validate the original file
        # TODO: Implement proper diff application to temp file
        
        return self.validate_file(file_path, original_content)
    
    def _validate_syntax(self, content: str, file_ext: str) -> bool:
        """Validate syntax for the given file type"""
        try:
            if file_ext == '.py':
                ast.parse(content)
                return True
            elif file_ext in ['.js', '.jsx']:
                # Try using esprima if available, otherwise skip
                try:
                    import esprima
                    esprima.parseScript(content)
                    return True
                except ImportError:
                    # esprima not available, skip syntax check
                    return True
            elif file_ext in ['.ts', '.tsx']:
                # TypeScript syntax checking requires tsc
                return True  # Will be checked by type checker
            else:
                # Unknown file type, assume valid
                return True
        except SyntaxError:
            return False
        except Exception:
            # Other parsing errors, assume invalid
            return False
    
    def _get_syntax_errors(self, content: str, file_ext: str) -> List[ValidationIssue]:
        """Get detailed syntax error information"""
        issues = []
        
        if file_ext == '.py':
            try:
                ast.parse(content)
            except SyntaxError as e:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    file_path="",
                    line_number=e.lineno or 0,
                    column=e.offset or 0,
                    message=f"Syntax error: {e.msg}",
                    rule="syntax"
                ))
        
        return issues
    
    def _validate_types_python(self, file_path: Path, content: str) -> Tuple[Optional[bool], List[ValidationIssue]]:
        """Validate Python types using mypy"""
        issues = []
        
        # Check if mypy is available
        try:
            result = subprocess.run(
                ['mypy', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None, issues  # mypy not available
        
        # Write content to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Run mypy
            result = subprocess.run(
                ['mypy', '--no-error-summary', temp_path],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.workspace_path)
            )
            
            # Parse mypy output
            if result.returncode != 0:
                for line in result.stdout.split('\n'):
                    if ':' in line and 'error:' in line:
                        parts = line.split(':')
                        if len(parts) >= 4:
                            try:
                                line_num = int(parts[1])
                                col_num = int(parts[2]) if parts[2].isdigit() else None
                                msg = ':'.join(parts[3:]).strip()
                                
                                issues.append(ValidationIssue(
                                    severity=ValidationSeverity.ERROR,
                                    file_path=str(file_path.relative_to(self.workspace_path)),
                                    line_number=line_num,
                                    column=col_num,
                                    message=msg,
                                    rule="mypy"
                                ))
                            except (ValueError, IndexError):
                                continue
            
            passed = result.returncode == 0
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass
        
        return passed, issues
    
    def _validate_types_typescript(self, file_path: Path, content: str) -> Tuple[Optional[bool], List[ValidationIssue]]:
        """Validate TypeScript types using tsc"""
        issues = []
        
        # Check if tsc is available
        try:
            result = subprocess.run(
                ['tsc', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None, issues  # tsc not available
        
        # Write content to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Run tsc --noEmit
            result = subprocess.run(
                ['tsc', '--noEmit', temp_path],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.workspace_path)
            )
            
            # Parse tsc output
            if result.returncode != 0:
                for line in result.stdout.split('\n'):
                    if 'error TS' in line and ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 3:
                            try:
                                line_num = int(parts[1])
                                msg = ':'.join(parts[2:]).strip()
                                
                                issues.append(ValidationIssue(
                                    severity=ValidationSeverity.ERROR,
                                    file_path=str(file_path.relative_to(self.workspace_path)),
                                    line_number=line_num,
                                    column=None,
                                    message=msg,
                                    rule="typescript"
                                ))
                            except (ValueError, IndexError):
                                continue
            
            passed = result.returncode == 0
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass
        
        return passed, issues
    
    def _lint_python(self, file_path: Path, content: str) -> Tuple[Optional[bool], List[ValidationIssue]]:
        """Lint Python code using flake8"""
        issues = []
        
        # Check if flake8 is available
        try:
            result = subprocess.run(
                ['flake8', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None, issues  # flake8 not available
        
        # Write content to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Run flake8
            result = subprocess.run(
                ['flake8', '--format=default', temp_path],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.workspace_path)
            )
            
            # Parse flake8 output
            if result.returncode != 0:
                for line in result.stdout.split('\n'):
                    if ':' in line:
                        parts = line.split(':')
                        if len(parts) >= 4:
                            try:
                                line_num = int(parts[1])
                                col_num = int(parts[2]) if parts[2].isdigit() else None
                                code_and_msg = parts[3].strip().split(' ', 1)
                                rule = code_and_msg[0] if code_and_msg else None
                                msg = code_and_msg[1] if len(code_and_msg) > 1 else parts[3].strip()
                                
                                # Determine severity based on error code
                                severity = ValidationSeverity.ERROR
                                if rule and rule.startswith('W'):
                                    severity = ValidationSeverity.WARNING
                                elif rule and rule.startswith('E'):
                                    severity = ValidationSeverity.ERROR
                                else:
                                    severity = ValidationSeverity.WARNING
                                
                                issues.append(ValidationIssue(
                                    severity=severity,
                                    file_path=str(file_path.relative_to(self.workspace_path)),
                                    line_number=line_num,
                                    column=col_num,
                                    message=msg,
                                    rule=rule
                                ))
                            except (ValueError, IndexError):
                                continue
            
            passed = result.returncode == 0
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass
        
        return passed, issues
    
    def _lint_javascript(self, file_path: Path, content: str) -> Tuple[Optional[bool], List[ValidationIssue]]:
        """Lint JavaScript/TypeScript code using ESLint"""
        issues = []
        
        # Check if eslint is available
        try:
            result = subprocess.run(
                ['eslint', '--version'],
                capture_output=True,
                text=True,
                timeout=5
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None, issues  # eslint not available
        
        # Write content to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix=file_path.suffix, delete=False) as f:
            f.write(content)
            temp_path = f.name
        
        try:
            # Run eslint
            result = subprocess.run(
                ['eslint', '--format=json', temp_path],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.workspace_path)
            )
            
            # Parse eslint JSON output
            if result.returncode != 0:
                try:
                    import json
                    eslint_output = json.loads(result.stdout)
                    for file_result in eslint_output:
                        for message in file_result.get('messages', []):
                            severity_map = {1: ValidationSeverity.WARNING, 2: ValidationSeverity.ERROR}
                            severity = severity_map.get(message.get('severity', 1), ValidationSeverity.WARNING)
                            
                            issues.append(ValidationIssue(
                                severity=severity,
                                file_path=str(file_path.relative_to(self.workspace_path)),
                                line_number=message.get('line', 0),
                                column=message.get('column', None),
                                message=message.get('message', ''),
                                rule=message.get('ruleId')
                            ))
                except (json.JSONDecodeError, KeyError):
                    # Fallback to text parsing
                    for line in result.stdout.split('\n'):
                        if ':' in line and ('error' in line.lower() or 'warning' in line.lower()):
                            parts = line.split(':')
                            if len(parts) >= 3:
                                try:
                                    line_num = int(parts[1])
                                    msg = ':'.join(parts[2:]).strip()
                                    
                                    severity = ValidationSeverity.ERROR if 'error' in line.lower() else ValidationSeverity.WARNING
                                    
                                    issues.append(ValidationIssue(
                                        severity=severity,
                                        file_path=str(file_path.relative_to(self.workspace_path)),
                                        line_number=line_num,
                                        column=None,
                                        message=msg,
                                        rule="eslint"
                                    ))
                                except (ValueError, IndexError):
                                    continue
            
            passed = result.returncode == 0
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except Exception:
                pass
        
        return passed, issues
