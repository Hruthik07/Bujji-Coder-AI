"""
Code Instrumentation - Automatically inserts debug logging statements
Similar to Cursor AI's instrumentation feature
"""
import ast
import re
from pathlib import Path
from typing import List, Dict, Optional, Any, Set
from dataclasses import dataclass


@dataclass
class InstrumentationPoint:
    """Represents a point where instrumentation should be added"""
    line_number: int
    type: str  # 'function_entry', 'function_exit', 'variable', 'condition', 'loop'
    context: str  # Function name, variable name, etc.
    code_snippet: str


class CodeInstrumentation:
    """
    Automatically inserts debug logging statements into code
    to capture runtime data for debugging
    """
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.instrumentation_id = "__debug_instrumentation__"
    
    def instrument_file(
        self,
        file_path: str,
        instrument_functions: bool = True,
        instrument_variables: bool = True,
        instrument_conditions: bool = True,
        target_functions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Instrument a file with debug logging
        
        Args:
            file_path: Path to file to instrument
            instrument_functions: Add logs at function entry/exit
            instrument_variables: Add logs for variable assignments
            instrument_conditions: Add logs for if/while conditions
            target_functions: Specific functions to instrument (None = all)
            
        Returns:
            Dict with instrumented code and metadata
        """
        full_path = self.workspace_path / file_path
        
        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Parse AST
            try:
                tree = ast.parse(original_content, filename=str(full_path))
            except SyntaxError:
                return {"error": "File has syntax errors, cannot instrument"}
            
            # Find instrumentation points
            points = self._find_instrumentation_points(
                tree,
                instrument_functions,
                instrument_variables,
                instrument_conditions,
                target_functions
            )
            
            # Generate instrumented code
            instrumented_code = self._insert_instrumentation(original_content, points)
            
            # Create backup
            backup_path = full_path.with_suffix(full_path.suffix + '.backup')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            return {
                "success": True,
                "file_path": file_path,
                "backup_path": str(backup_path),
                "instrumentation_points": len(points),
                "points": [self._point_to_dict(p) for p in points],
                "instrumented_code": instrumented_code
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    def _find_instrumentation_points(
        self,
        tree: ast.AST,
        instrument_functions: bool,
        instrument_variables: bool,
        instrument_conditions: bool,
        target_functions: Optional[List[str]]
    ) -> List[InstrumentationPoint]:
        """Find where to insert instrumentation"""
        points = []
        
        for node in ast.walk(tree):
            # Function entry/exit points
            if instrument_functions and isinstance(node, ast.FunctionDef):
                if target_functions is None or node.name in target_functions:
                    points.append(InstrumentationPoint(
                        line_number=node.lineno,
                        type="function_entry",
                        context=node.name,
                        code_snippet=f"def {node.name}(...)"
                    ))
                    # Find function exit (return statements)
                    for child in ast.walk(node):
                        if isinstance(child, ast.Return):
                            points.append(InstrumentationPoint(
                                line_number=child.lineno,
                                type="function_exit",
                                context=node.name,
                                code_snippet="return"
                            ))
            
            # Variable assignments
            if instrument_variables and isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        points.append(InstrumentationPoint(
                            line_number=node.lineno,
                            type="variable",
                            context=target.id,
                            code_snippet=ast.unparse(node) if hasattr(ast, 'unparse') else str(node)
                        ))
            
            # Condition checks
            if instrument_conditions:
                if isinstance(node, ast.If):
                    points.append(InstrumentationPoint(
                        line_number=node.lineno,
                        type="condition",
                        context="if",
                        code_snippet=ast.unparse(node.test) if hasattr(ast, 'unparse') else str(node.test)
                    ))
                elif isinstance(node, ast.While):
                    points.append(InstrumentationPoint(
                        line_number=node.lineno,
                        type="condition",
                        context="while",
                        code_snippet=ast.unparse(node.test) if hasattr(ast, 'unparse') else str(node.test)
                    ))
        
        return sorted(points, key=lambda x: x.line_number, reverse=True)  # Reverse for insertion
    
    def _insert_instrumentation(
        self,
        original_content: str,
        points: List[InstrumentationPoint]
    ) -> str:
        """Insert instrumentation logs into code"""
        lines = original_content.split('\n')
        
        # Insert logs (from end to start to preserve line numbers)
        for point in points:
            log_line = self._generate_log_statement(point)
            # Insert after the line (or before for function entry)
            if point.type == "function_entry":
                # Insert at start of function
                indent = self._get_line_indent(lines[point.line_number - 1])
                lines.insert(point.line_number, indent + log_line)
            else:
                # Insert after the line
                indent = self._get_line_indent(lines[point.line_number - 1])
                lines.insert(point.line_number, indent + log_line)
        
        return '\n'.join(lines)
    
    def _generate_log_statement(self, point: InstrumentationPoint) -> str:
        """Generate debug log statement"""
        log_id = self.instrumentation_id
        
        if point.type == "function_entry":
            return f'print(f"[{log_id}] ENTER {point.context}()")'
        elif point.type == "function_exit":
            return f'print(f"[{log_id}] EXIT {point.context}()")'
        elif point.type == "variable":
            return f'print(f"[{log_id}] VAR {point.context} = {{{point.context}}}")'
        elif point.type == "condition":
            return f'print(f"[{log_id}] COND {point.context}: {{{point.code_snippet}}}")'
        else:
            return f'print(f"[{log_id}] DEBUG at line {point.line_number}")'
    
    def _get_line_indent(self, line: str) -> str:
        """Get indentation of a line"""
        return len(line) - len(line.lstrip())
    
    def _point_to_dict(self, point: InstrumentationPoint) -> Dict:
        """Convert point to dict"""
        return {
            "line_number": point.line_number,
            "type": point.type,
            "context": point.context,
            "code_snippet": point.code_snippet
        }
    
    def restore_file(self, file_path: str) -> Dict[str, Any]:
        """Restore file from backup (remove instrumentation)"""
        full_path = self.workspace_path / file_path
        backup_path = full_path.with_suffix(full_path.suffix + '.backup')
        
        if not backup_path.exists():
            return {"error": "No backup found"}
        
        try:
            with open(backup_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Remove backup
            backup_path.unlink()
            
            return {"success": True, "file_path": file_path}
        except Exception as e:
            return {"error": str(e)}
    
    def clean_instrumentation(self, file_path: str) -> Dict[str, Any]:
        """Remove instrumentation from file without backup"""
        full_path = self.workspace_path / file_path
        
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Remove instrumentation lines
            lines = content.split('\n')
            cleaned_lines = [
                line for line in lines
                if self.instrumentation_id not in line
            ]
            
            cleaned_content = '\n'.join(cleaned_lines)
            
            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_content)
            
            return {"success": True, "file_path": file_path}
        except Exception as e:
            return {"error": str(e)}






