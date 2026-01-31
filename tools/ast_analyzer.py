"""
AST-based code analysis module - provides semantic code understanding
"""
import ast
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from dataclasses import dataclass

try:
    import tree_sitter
    from tree_sitter import Language, Parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False


@dataclass
class CodeSymbol:
    """Represents a code symbol (function, class, variable, etc.)"""
    name: str
    type: str  # 'function', 'class', 'method', 'variable', 'import'
    file_path: str
    line_start: int
    line_end: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    parent: Optional[str] = None  # For methods, the class name


class ASTAnalyzer:
    """Analyzes code using AST parsing for better code understanding"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.parsers = {}
        self._init_parsers()
    
    def _init_parsers(self):
        """Initialize language parsers"""
        if TREE_SITTER_AVAILABLE:
            try:
                # Try to load tree-sitter languages
                # Note: In production, you'd need to build these from grammars
                pass
            except Exception:
                pass
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a file and extract its structure.
        
        Args:
            file_path: Path to the file
            
        Returns:
            dict with file structure information
        """
        file_path_obj = self._resolve_path(file_path)
        
        if not file_path_obj.exists():
            return {"error": f"File not found: {file_path}"}
        
        extension = file_path_obj.suffix.lower()
        
        if extension == '.py':
            return self._analyze_python(file_path_obj)
        elif extension in ['.js', '.jsx', '.ts', '.tsx']:
            return self._analyze_javascript(file_path_obj)
        else:
            return {"error": f"Unsupported file type: {extension}"}
    
    def _analyze_python(self, file_path: Path) -> Dict[str, Any]:
        """Analyze Python file using built-in AST"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            
            symbols = []
            imports = []
            classes = []
            functions = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append({
                            "name": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno
                        })
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append({
                            "name": f"{module}.{alias.name}" if module else alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                            "from": module
                        })
                elif isinstance(node, ast.ClassDef):
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            methods.append({
                                "name": item.name,
                                "line": item.lineno,
                                "args": self._get_function_args(item),
                                "docstring": ast.get_docstring(item)
                            })
                    
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "line_end": self._get_node_end_line(node, content),
                        "bases": [self._get_name(base) for base in node.bases],
                        "methods": methods,
                        "docstring": ast.get_docstring(node)
                    })
                    
                    symbols.append(CodeSymbol(
                        name=node.name,
                        type="class",
                        file_path=str(file_path.relative_to(self.workspace_path)),
                        line_start=node.lineno,
                        line_end=self._get_node_end_line(node, content),
                        docstring=ast.get_docstring(node)
                    ))
                
                elif isinstance(node, ast.FunctionDef):
                    # Check if it's a method (has a parent class)
                    parent_class = None
                    for parent in ast.walk(tree):
                        if isinstance(parent, ast.ClassDef):
                            if any(isinstance(child, ast.FunctionDef) and child.name == node.name 
                                   for child in parent.body):
                                parent_class = parent.name
                                break
                    
                    func_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "line_end": self._get_node_end_line(node, content),
                        "args": self._get_function_args(node),
                        "docstring": ast.get_docstring(node),
                        "parent": parent_class
                    }
                    functions.append(func_info)
                    
                    symbols.append(CodeSymbol(
                        name=node.name,
                        type="method" if parent_class else "function",
                        file_path=str(file_path.relative_to(self.workspace_path)),
                        line_start=node.lineno,
                        line_end=self._get_node_end_line(node, content),
                        signature=self._get_function_signature(node),
                        docstring=ast.get_docstring(node),
                        parent=parent_class
                    ))
            
            return {
                "file": str(file_path.relative_to(self.workspace_path)),
                "language": "python",
                "imports": imports,
                "classes": classes,
                "functions": functions,
                "symbols": [
                    {
                        "name": s.name,
                        "type": s.type,
                        "line_start": s.line_start,
                        "line_end": s.line_end,
                        "signature": s.signature,
                        "parent": s.parent
                    }
                    for s in symbols
                ],
                "total_symbols": len(symbols)
            }
        
        except SyntaxError as e:
            return {"error": f"Syntax error: {str(e)}", "line": e.lineno}
        except Exception as e:
            return {"error": str(e)}
    
    def _analyze_javascript(self, file_path: Path) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript file (simplified - would use tree-sitter in production)"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            # Simple regex-based extraction for JS (AST would be better with tree-sitter)
            functions = []
            classes = []
            imports = []
            
            for i, line in enumerate(lines, 1):
                line_stripped = line.strip()
                
                # Detect imports
                if line_stripped.startswith(('import ', 'const ', 'let ', 'var ')):
                    if 'from' in line_stripped or 'require(' in line_stripped:
                        imports.append({"line": i, "content": line_stripped})
                
                # Detect function declarations
                if line_stripped.startswith('function ') or 'function(' in line_stripped:
                    # Extract function name
                    match = __import__('re').search(r'function\s+(\w+)', line_stripped)
                    if match:
                        functions.append({
                            "name": match.group(1),
                            "line": i,
                            "type": "function"
                        })
                
                # Detect class declarations
                if line_stripped.startswith('class '):
                    match = __import__('re').search(r'class\s+(\w+)', line_stripped)
                    if match:
                        classes.append({
                            "name": match.group(1),
                            "line": i,
                            "type": "class"
                        })
            
            return {
                "file": str(file_path.relative_to(self.workspace_path)),
                "language": "javascript",
                "imports": imports,
                "classes": classes,
                "functions": functions,
                "total_symbols": len(functions) + len(classes)
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    def find_symbols(self, query: str, file_path: Optional[str] = None) -> List[CodeSymbol]:
        """
        Find symbols (functions, classes) matching a query.
        
        Args:
            query: Symbol name or pattern to search for
            file_path: Optional file to search in, otherwise searches all files
            
        Returns:
            List of matching CodeSymbol objects
        """
        symbols = []
        
        if file_path:
            files = [self._resolve_path(file_path)]
        else:
            files = self._get_code_files(self.workspace_path)
        
        for file in files:
            if file.suffix == '.py':
                analysis = self._analyze_python(file)
                if "symbols" in analysis:
                    for symbol_data in analysis["symbols"]:
                        if query.lower() in symbol_data["name"].lower():
                            symbols.append(CodeSymbol(
                                name=symbol_data["name"],
                                type=symbol_data["type"],
                                file_path=symbol_data.get("file", str(file)),
                                line_start=symbol_data["line_start"],
                                line_end=symbol_data["line_end"],
                                signature=symbol_data.get("signature"),
                                parent=symbol_data.get("parent")
                            ))
        
        return symbols
    
    def get_file_structure(self, file_path: str) -> Dict[str, Any]:
        """Get the structure of a file (classes, functions, imports)"""
        return self.analyze_file(file_path)
    
    def find_functions(self, name_pattern: str, file_path: Optional[str] = None) -> List[Dict]:
        """Find functions matching a name pattern"""
        symbols = self.find_symbols(name_pattern, file_path)
        return [
            {
                "name": s.name,
                "file": s.file_path,
                "line": s.line_start,
                "signature": s.signature,
                "parent": s.parent
            }
            for s in symbols if s.type in ["function", "method"]
        ]
    
    def find_classes(self, name_pattern: str, file_path: Optional[str] = None) -> List[Dict]:
        """Find classes matching a name pattern"""
        symbols = self.find_symbols(name_pattern, file_path)
        return [
            {
                "name": s.name,
                "file": s.file_path,
                "line": s.line_start,
                "parent": s.parent
            }
            for s in symbols if s.type == "class"
        ]
    
    def _get_function_args(self, node: ast.FunctionDef) -> List[str]:
        """Extract function arguments"""
        args = []
        for arg in node.args.args:
            arg_name = arg.arg
            if arg.annotation:
                arg_name += f": {ast.unparse(arg.annotation)}"
            args.append(arg_name)
        return args
    
    def _get_function_signature(self, node: ast.FunctionDef) -> str:
        """Get function signature as string"""
        try:
            # Try to use ast.unparse (Python 3.9+)
            return ast.unparse(node)
        except AttributeError:
            # Fallback for older Python versions
            args = ', '.join(self._get_function_args(node))
            return f"def {node.name}({args})"
    
    def _get_node_end_line(self, node: ast.AST, content: str) -> int:
        """Estimate end line of a node"""
        lines = content.split('\n')
        if hasattr(node, 'end_lineno') and node.end_lineno:
            return node.end_lineno
        # Fallback: estimate based on node depth
        return node.lineno + 10
    
    def _get_name(self, node: ast.AST) -> str:
        """Extract name from AST node"""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return f"{self._get_name(node.value)}.{node.attr}"
        return str(node)
    
    def _get_code_files(self, directory: Path) -> List[Path]:
        """Get all code files in a directory recursively"""
        code_files = []
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx'}
        
        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', '.venv', 'venv', 'env'}]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    code_files.append(Path(root) / file)
        
        return code_files
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to workspace or absolute"""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.workspace_path / p

