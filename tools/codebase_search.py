"""
Codebase search module - semantic and text-based code search
"""
import os
import re
from pathlib import Path
from typing import List, Dict, Optional
from config import Config
from .ast_analyzer import ASTAnalyzer


class CodebaseSearch:
    """Handles codebase search operations"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.ast_analyzer = ASTAnalyzer(workspace_path)
    
    def grep(self, pattern: str, path: str = ".", output_mode: str = "content", 
             context_lines: int = 0, case_insensitive: bool = False) -> dict:
        """
        Search for patterns in files using regex.
        
        Args:
            pattern: Regex pattern to search for
            output_mode: 'content', 'files_with_matches', or 'count'
            path: Directory or file to search in
            context_lines: Number of context lines to include
            case_insensitive: Case-insensitive search
            
        Returns:
            dict with search results
        """
        try:
            search_path = self._resolve_path(path)
            flags = re.IGNORECASE if case_insensitive else 0
            compiled_pattern = re.compile(pattern, flags)
            
            results = []
            files_with_matches = set()
            match_count = 0
            
            if search_path.is_file():
                files_to_search = [search_path]
            else:
                files_to_search = self._get_code_files(search_path)
            
            for file_path in files_to_search:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                    
                    file_matches = []
                    for line_num, line in enumerate(lines, 1):
                        if compiled_pattern.search(line):
                            match_count += 1
                            files_with_matches.add(str(file_path))
                            
                            if output_mode == "content":
                                start = max(0, line_num - context_lines - 1)
                                end = min(len(lines), line_num + context_lines)
                                context = lines[start:end]
                                
                                file_matches.append({
                                    "line": line_num,
                                    "content": line.rstrip(),
                                    "context": [l.rstrip() for l in context]
                                })
                    
                    if file_matches:
                        results.append({
                            "file": str(file_path.relative_to(self.workspace_path)),
                            "matches": file_matches
                        })
                
                except Exception:
                    continue
            
            if output_mode == "files_with_matches":
                return {
                    "files": sorted(list(files_with_matches)),
                    "count": len(files_with_matches)
                }
            elif output_mode == "count":
                return {
                    "count": match_count
                }
            else:
                return {
                    "results": results,
                    "total_matches": match_count
                }
        
        except Exception as e:
            return {
                "error": str(e),
                "results": []
            }
    
    def semantic_search(self, query: str, target_directories: Optional[List[str]] = None) -> dict:
        """
        Perform semantic search across the codebase.
        This is a simplified version - in production, you'd use embeddings/vector search.
        
        Args:
            query: Natural language query
            target_directories: Optional list of directories to limit search
            
        Returns:
            dict with relevant code snippets
        """
        # Simplified semantic search using keyword matching and file analysis
        # In a real implementation, you'd use embeddings/vector databases
        
        query_lower = query.lower()
        query_keywords = set(query_lower.split())
        
        search_paths = []
        if target_directories:
            for dir_path in target_directories:
                search_paths.append(self._resolve_path(dir_path))
        else:
            search_paths = [self.workspace_path]
        
        results = []
        
        for search_path in search_paths:
            if not search_path.exists():
                continue
            
            files = self._get_code_files(search_path)
            
            for file_path in files:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    
                    content_lower = content.lower()
                    # Simple relevance scoring based on keyword matches
                    score = sum(1 for keyword in query_keywords if keyword in content_lower)
                    
                    if score > 0:
                        # Extract relevant snippets
                        lines = content.split('\n')
                        relevant_lines = []
                        for i, line in enumerate(lines):
                            line_lower = line.lower()
                            if any(keyword in line_lower for keyword in query_keywords):
                                start = max(0, i - 2)
                                end = min(len(lines), i + 3)
                                snippet = '\n'.join(lines[start:end])
                                relevant_lines.append({
                                    "line": i + 1,
                                    "snippet": snippet
                                })
                        
                        if relevant_lines:
                            results.append({
                                "file": str(file_path.relative_to(self.workspace_path)),
                                "score": score,
                                "snippets": relevant_lines[:5]  # Limit snippets per file
                            })
                
                except Exception:
                    continue
        
        # Sort by relevance score
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return {
            "query": query,
            "results": results[:Config.MAX_SEARCH_RESULTS]
        }
    
    def ast_search(self, query: str, symbol_type: Optional[str] = None) -> dict:
        """
        Search for code symbols (functions, classes) using AST analysis.
        
        Args:
            query: Name or pattern to search for
            symbol_type: Optional filter ('function', 'class', 'method')
            
        Returns:
            dict with matching symbols
        """
        symbols = self.ast_analyzer.find_symbols(query)
        
        if symbol_type:
            symbols = [s for s in symbols if s.type == symbol_type]
        
        return {
            "query": query,
            "symbol_type": symbol_type,
            "results": [
                {
                    "name": s.name,
                    "type": s.type,
                    "file": s.file_path,
                    "line": s.line_start,
                    "line_end": s.line_end,
                    "signature": s.signature,
                    "parent": s.parent
                }
                for s in symbols
            ],
            "count": len(symbols)
        }
    
    def get_code_structure(self, file_path: str) -> dict:
        """
        Get the AST structure of a file (classes, functions, imports).
        
        Args:
            file_path: Path to the file
            
        Returns:
            dict with file structure
        """
        return self.ast_analyzer.get_file_structure(file_path)
    
    def find_functions(self, name_pattern: str, file_path: Optional[str] = None) -> dict:
        """Find functions matching a name pattern"""
        functions = self.ast_analyzer.find_functions(name_pattern, file_path)
        return {
            "pattern": name_pattern,
            "functions": functions,
            "count": len(functions)
        }
    
    def find_classes(self, name_pattern: str, file_path: Optional[str] = None) -> dict:
        """Find classes matching a name pattern"""
        classes = self.ast_analyzer.find_classes(name_pattern, file_path)
        return {
            "pattern": name_pattern,
            "classes": classes,
            "count": len(classes)
        }
    
    def _get_code_files(self, directory: Path) -> List[Path]:
        """Get all code files in a directory recursively"""
        code_files = []
        extensions = {
            '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs',
            '.cpp', '.c', '.h', '.hpp', '.rb', '.php', '.swift', '.kt',
            '.md', '.json', '.yaml', '.yml', '.xml', '.html', '.css'
        }
        
        for root, dirs, files in os.walk(directory):
            # Skip common ignore directories
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
