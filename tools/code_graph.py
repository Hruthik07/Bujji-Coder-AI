"""
Code Graph Builder - Creates call graphs, import graphs, and symbol relationships
"""
import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from .ast_analyzer import ASTAnalyzer


@dataclass
class SymbolNode:
    """Represents a symbol (function, class, variable) in the code graph"""
    name: str
    file_path: str
    symbol_type: str  # 'function', 'class', 'method', 'variable'
    line_start: int
    line_end: int
    parent: Optional[str] = None  # Parent class for methods
    signature: Optional[str] = None


@dataclass
class GraphEdge:
    """Represents a relationship between symbols"""
    source: str  # Symbol name or file path
    target: str
    edge_type: str  # 'calls', 'imports', 'inherits', 'contains'
    metadata: Dict = field(default_factory=dict)


@dataclass
class CodeGraph:
    """Complete code graph with nodes and edges"""
    nodes: Dict[str, SymbolNode] = field(default_factory=dict)
    edges: List[GraphEdge] = field(default_factory=list)
    imports: Dict[str, List[str]] = field(default_factory=dict)  # file -> imported modules
    call_graph: Dict[str, Set[str]] = field(default_factory=dict)  # function -> called functions


class CodeGraphBuilder:
    """
    Builds code graphs from codebase.
    Tracks: call graphs, import dependencies, symbol relationships
    """
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.ast_analyzer = ASTAnalyzer(workspace_path)
        self.graph = CodeGraph()
    
    def build_graph(self, files: Optional[List[Path]] = None) -> CodeGraph:
        """
        Build complete code graph from codebase.
        
        Args:
            files: Optional list of files to process, otherwise scans all
            
        Returns:
            CodeGraph object
        """
        if files is None:
            files = self._get_code_files()
        
        # First pass: collect all symbols
        for file_path in files:
            self._add_file_symbols(file_path)
        
        # Second pass: build relationships
        for file_path in files:
            self._analyze_file_relationships(file_path)
        
        return self.graph
    
    def _add_file_symbols(self, file_path: Path):
        """Add symbols from a file to the graph"""
        if file_path.suffix != '.py':
            return
        
        try:
            analysis = self.ast_analyzer.analyze_file(str(file_path))
            if "error" in analysis:
                return
            
            file_str = str(file_path.relative_to(self.workspace_path))
            
            # Add classes
            for cls in analysis.get('classes', []):
                node_id = f"{file_str}::{cls['name']}"
                self.graph.nodes[node_id] = SymbolNode(
                    name=cls['name'],
                    file_path=file_str,
                    symbol_type="class",
                    line_start=cls['line'],
                    line_end=cls.get('line_end', cls['line'] + 10),
                    signature=cls['name']
                )
            
            # Add functions
            for func in analysis.get('functions', []):
                node_id = f"{file_str}::{func['name']}"
                parent = func.get('parent')
                self.graph.nodes[node_id] = SymbolNode(
                    name=func['name'],
                    file_path=file_str,
                    symbol_type="method" if parent else "function",
                    line_start=func['line'],
                    line_end=func.get('line_end', func['line'] + 10),
                    parent=parent,
                    signature=func.get('args', [])
                )
            
            # Track imports
            imports = []
            for imp in analysis.get('imports', []):
                imports.append(imp.get('name', ''))
            if imports:
                self.graph.imports[file_str] = imports
        
        except Exception as e:
            print(f"Error adding symbols from {file_path}: {e}")
    
    def _analyze_file_relationships(self, file_path: Path):
        """Analyze relationships in a file (calls, imports, etc.)"""
        if file_path.suffix != '.py':
            return
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            tree = ast.parse(content, filename=str(file_path))
            file_str = str(file_path.relative_to(self.workspace_path))
            
            # Build call graph
            call_visitor = CallGraphVisitor(file_str, self.graph)
            call_visitor.visit(tree)
            
        except Exception as e:
            print(f"Error analyzing relationships in {file_path}: {e}")
    
    def get_call_graph(self, function_name: Optional[str] = None) -> Dict[str, Set[str]]:
        """
        Get call graph.
        
        Args:
            function_name: Optional function to get callers/callees for
            
        Returns:
            Call graph dictionary
        """
        if function_name:
            # Return callers and callees for specific function
            callers = {src for src, targets in self.graph.call_graph.items() 
                      if function_name in targets}
            callees = self.graph.call_graph.get(function_name, set())
            return {
                "function": function_name,
                "callers": callers,
                "callees": callees
            }
        
        return self.graph.call_graph
    
    def get_import_graph(self) -> Dict[str, List[str]]:
        """Get import dependency graph"""
        return self.graph.imports
    
    def find_related_symbols(self, symbol_name: str, 
                            relationship_types: List[str] = None) -> List[SymbolNode]:
        """
        Find symbols related to a given symbol.
        
        Args:
            symbol_name: Name of symbol to find relationships for
            relationship_types: Types of relationships to consider
            
        Returns:
            List of related symbol nodes
        """
        if relationship_types is None:
            relationship_types = ['calls', 'imports', 'inherits']
        
        related = []
        
        # Find symbol node
        symbol_node = None
        for node_id, node in self.graph.nodes.items():
            if node.name == symbol_name:
                symbol_node = node
                break
        
        if not symbol_node:
            return related
        
        # Find related via edges
        for edge in self.graph.edges:
            if edge.source == symbol_name or edge.target == symbol_name:
                if edge.edge_type in relationship_types:
                    # Find the related node
                    related_name = edge.target if edge.source == symbol_name else edge.source
                    for node_id, node in self.graph.nodes.items():
                        if node.name == related_name:
                            related.append(node)
                            break
        
        return related
    
    def get_symbol_dependencies(self, symbol_name: str) -> Dict[str, List[str]]:
        """
        Get all dependencies for a symbol (what it depends on).
        
        Args:
            symbol_name: Symbol to analyze
            
        Returns:
            Dict with dependency types and lists
        """
        dependencies = {
            "calls": [],
            "imports": [],
            "inherits": []
        }
        
        # Find symbol
        symbol_node = None
        for node_id, node in self.graph.nodes.items():
            if node.name == symbol_name:
                symbol_node = node
                break
        
        if not symbol_node:
            return dependencies
        
        # Find dependencies via edges
        for edge in self.graph.edges:
            if edge.source == symbol_name:
                if edge.edge_type == 'calls':
                    dependencies['calls'].append(edge.target)
                elif edge.edge_type == 'imports':
                    dependencies['imports'].append(edge.target)
                elif edge.edge_type == 'inherits':
                    dependencies['inherits'].append(edge.target)
        
        return dependencies
    
    def _get_code_files(self) -> List[Path]:
        """Get all Python files in workspace"""
        code_files = []
        for file_path in self.workspace_path.rglob('*.py'):
            # Skip hidden directories and common ignore patterns
            if any(part.startswith('.') for part in file_path.parts):
                continue
            if '__pycache__' in file_path.parts:
                continue
            if 'node_modules' in file_path.parts:
                continue
            code_files.append(file_path)
        return code_files


class CallGraphVisitor(ast.NodeVisitor):
    """AST visitor to build call graph"""
    
    def __init__(self, file_path: str, graph: CodeGraph):
        self.file_path = file_path
        self.graph = graph
        self.current_function = None
    
    def visit_FunctionDef(self, node):
        """Track current function"""
        old_function = self.current_function
        func_id = f"{self.file_path}::{node.name}"
        self.current_function = func_id
        
        # Initialize call graph entry
        if func_id not in self.graph.call_graph:
            self.graph.call_graph[func_id] = set()
        
        self.generic_visit(node)
        self.current_function = old_function
    
    def visit_Call(self, node):
        """Track function calls"""
        if self.current_function:
            # Get called function name
            if isinstance(node.func, ast.Name):
                called_name = node.func.id
                # Add edge
                self.graph.edges.append(GraphEdge(
                    source=self.current_function,
                    target=called_name,
                    edge_type="calls"
                ))
                # Add to call graph
                self.graph.call_graph[self.current_function].add(called_name)
        
        self.generic_visit(node)
