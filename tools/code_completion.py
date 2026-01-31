"""
Code Completion Engine
Provides context-aware code completions using RAG + AST analysis
Similar to Cursor AI's inline autocomplete feature
"""
import re
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
from tools.rag_system import RAGSystem
from tools.ast_analyzer import ASTAnalyzer
from tools.llm_provider import get_provider
from config import Config


@dataclass
class CompletionCandidate:
    """Represents a code completion suggestion"""
    text: str
    label: str  # Display label
    kind: str  # 'function', 'variable', 'class', 'keyword', 'snippet'
    detail: Optional[str] = None  # Additional info
    documentation: Optional[str] = None  # Documentation string
    score: float = 0.0  # Relevance score
    insert_text: Optional[str] = None  # Text to insert (may differ from label)


class CodeCompletionEngine:
    """
    Generates context-aware code completions using:
    - RAG: Find similar code patterns
    - AST: Understand current context
    - LLM: Generate intelligent completions
    """
    
    def __init__(self, rag_system: Optional[RAGSystem] = None, workspace_path: str = "."):
        self.rag_system = rag_system
        self.ast_analyzer = ASTAnalyzer(workspace_path)
        self.completion_cache = {}  # Cache completions for performance
        
        # Use DeepSeek for completions (fast, cheap, code-focused)
        try:
            self.llm_provider = get_provider("deepseek", Config.DEEPSEEK_API_KEY) if Config.DEEPSEEK_API_KEY else None
        except (ImportError, ValueError, Exception):
            self.llm_provider = None
    
    def get_completions(
        self,
        file_path: str,
        file_content: str,
        cursor_line: int,
        cursor_column: int,
        language: str = "python",
        max_completions: int = 10
    ) -> List[CompletionCandidate]:
        """
        Get code completions for current cursor position
        
        Args:
            file_path: Path to current file
            file_content: Full file content
            cursor_line: Current line (0-indexed)
            cursor_column: Current column (0-indexed)
            language: Programming language
            max_completions: Maximum number of completions to return
            
        Returns:
            List of completion candidates, sorted by relevance
        """
        # Extract context around cursor
        context = self._extract_context(file_content, cursor_line, cursor_column)
        
        # Check cache first
        cache_key = self._get_cache_key(file_path, context, cursor_line, cursor_column)
        if cache_key in self.completion_cache:
            return self.completion_cache[cache_key][:max_completions]
        
        # Get completions from multiple sources
        completions = []
        
        # 1. AST-based completions (symbols in current file)
        ast_completions = self._get_ast_completions(file_path, file_content, context, language)
        completions.extend(ast_completions)
        
        # 2. RAG-based completions (similar code from codebase)
        if self.rag_system and self.rag_system.is_indexed:
            rag_completions = self._get_rag_completions(context, file_path, language)
            completions.extend(rag_completions)
        
        # 3. LLM-based completions (intelligent generation)
        if self.llm_provider:
            llm_completions = self._get_llm_completions(context, file_path, language)
            completions.extend(llm_completions)
        
        # 4. Language-specific completions (keywords, built-ins)
        lang_completions = self._get_language_completions(context, language)
        completions.extend(lang_completions)
        
        # Deduplicate and rank
        completions = self._deduplicate_completions(completions)
        completions = self._rank_completions(completions, context)
        
        # Cache results
        self.completion_cache[cache_key] = completions
        
        return completions[:max_completions]
    
    def _extract_context(
        self,
        file_content: str,
        cursor_line: int,
        cursor_column: int,
        context_lines: int = 10
    ) -> Dict[str, Any]:
        """Extract context around cursor position"""
        lines = file_content.split('\n')
        
        # Get lines around cursor
        start_line = max(0, cursor_line - context_lines)
        end_line = min(len(lines), cursor_line + context_lines)
        context_lines_list = lines[start_line:end_line]
        
        # Get current line up to cursor
        current_line = lines[cursor_line] if cursor_line < len(lines) else ""
        prefix = current_line[:cursor_column] if cursor_column <= len(current_line) else current_line
        
        # Extract word being typed
        word_match = re.search(r'\w+$', prefix)
        word_prefix = word_match.group(0) if word_match else ""
        
        # Extract recent code (last 5 lines)
        recent_code = '\n'.join(lines[max(0, cursor_line - 5):cursor_line])
        
        return {
            "prefix": prefix,
            "word_prefix": word_prefix,
            "current_line": current_line,
            "cursor_line": cursor_line,
            "cursor_column": cursor_column,
            "context_lines": context_lines_list,
            "recent_code": recent_code,
            "full_file": file_content
        }
    
    def _get_ast_completions(
        self,
        file_path: str,
        file_content: str,
        context: Dict[str, Any],
        language: str
    ) -> List[CompletionCandidate]:
        """Get completions from AST analysis of current file"""
        completions = []
        
        if language == "python":
            try:
                # Analyze file structure
                analysis = self.ast_analyzer.analyze_file(file_path)
                
                word_prefix = context["word_prefix"].lower()
                
                # Get functions
                for func in analysis.get("functions", []):
                    if word_prefix in func["name"].lower() or not word_prefix:
                        completions.append(CompletionCandidate(
                            text=func["name"],
                            label=func["name"] + "()",
                            kind="function",
                            detail=func.get("signature", ""),
                            documentation=func.get("docstring", ""),
                            score=0.8 if word_prefix in func["name"].lower() else 0.5
                        ))
                
                # Get classes
                for cls in analysis.get("classes", []):
                    if word_prefix in cls["name"].lower() or not word_prefix:
                        completions.append(CompletionCandidate(
                            text=cls["name"],
                            label=cls["name"],
                            kind="class",
                            detail=f"Class at line {cls['line_start']}",
                            documentation=cls.get("docstring", ""),
                            score=0.8 if word_prefix in cls["name"].lower() else 0.5
                        ))
                
                # Get variables (from imports and assignments)
                for var in analysis.get("variables", []):
                    if word_prefix in var["name"].lower() or not word_prefix:
                        completions.append(CompletionCandidate(
                            text=var["name"],
                            label=var["name"],
                            kind="variable",
                            detail=f"Variable at line {var['line_start']}",
                            score=0.7 if word_prefix in var["name"].lower() else 0.4
                        ))
                
            except Exception as e:
                # If AST analysis fails, continue without it
                pass
        
        return completions
    
    def _get_rag_completions(
        self,
        context: Dict[str, Any],
        file_path: str,
        language: str
    ) -> List[CompletionCandidate]:
        """Get completions from RAG system (similar code in codebase)"""
        completions = []
        
        if not self.rag_system or not self.rag_system.is_indexed:
            return completions
        
        # Build query from context
        query = self._build_completion_query(context)
        
        # Retrieve similar code chunks
        chunks = self.rag_system.retrieve(query, top_k=5, use_hybrid=True)
        
        word_prefix = context["word_prefix"].lower()
        
        for chunk in chunks:
            # Extract function/class names from chunk
            content = chunk.get("content", "")
            
            # Look for function definitions
            func_patterns = [
                r'def\s+(\w+)\s*\(',
                r'function\s+(\w+)\s*\(',
                r'const\s+(\w+)\s*=',
                r'let\s+(\w+)\s*=',
                r'var\s+(\w+)\s*='
            ]
            
            for pattern in func_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    name = match.group(1)
                    if word_prefix in name.lower() or not word_prefix:
                        # Extract function signature if available
                        lines = content.split('\n')
                        func_line = next((i for i, line in enumerate(lines) if name in line), 0)
                        signature = lines[func_line] if func_line < len(lines) else name
                        
                        completions.append(CompletionCandidate(
                            text=name,
                            label=name + "()",
                            kind="function",
                            detail=f"From {chunk.get('file_path', 'unknown')}",
                            documentation=signature[:200],
                            score=0.6
                        ))
        
        return completions
    
    def _get_llm_completions(
        self,
        context: Dict[str, Any],
        file_path: str,
        language: str
    ) -> List[CompletionCandidate]:
        """Get intelligent completions from LLM"""
        completions = []
        
        if not self.llm_provider:
            return completions
        
        # Build prompt for completion
        prompt = self._build_completion_prompt(context, file_path, language)
        
        try:
            response = self.llm_provider.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a code completion assistant. Generate concise, context-aware code completions for {language}."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=Config.DEEPSEEK_MODEL if Config.DEEPSEEK_API_KEY else "gpt-3.5-turbo",
                temperature=0.3,  # Lower temperature for more consistent completions
                max_tokens=200  # Short completions only
            )
            
            # Parse LLM response
            completion_text = response.content.strip()
            
            # Extract completion suggestions
            lines = completion_text.split('\n')[:5]  # Top 5 suggestions
            for line in lines:
                line = line.strip()
                if line and len(line) < 100:  # Reasonable completion length
                    # Determine kind
                    kind = "snippet"
                    if line.endswith('()'):
                        kind = "function"
                    elif line.startswith('class ') or line.startswith('def '):
                        kind = "snippet"
                    
                    completions.append(CompletionCandidate(
                        text=line,
                        label=line[:50],  # Truncate for display
                        kind=kind,
                        score=0.7
                    ))
        
        except Exception as e:
            # If LLM fails, continue without it
            pass
        
        return completions
    
    def _get_language_completions(
        self,
        context: Dict[str, Any],
        language: str
    ) -> List[CompletionCandidate]:
        """Get language-specific completions (keywords, built-ins)"""
        completions = []
        word_prefix = context["word_prefix"].lower()
        
        # Python keywords and built-ins
        if language == "python":
            keywords = [
                "def", "class", "if", "else", "elif", "for", "while",
                "try", "except", "finally", "with", "import", "from",
                "return", "yield", "async", "await", "lambda"
            ]
            
            builtins = [
                "print", "len", "range", "enumerate", "zip", "map", "filter",
                "list", "dict", "set", "tuple", "str", "int", "float", "bool",
                "open", "type", "isinstance", "hasattr", "getattr", "setattr"
            ]
            
            for keyword in keywords:
                if word_prefix in keyword or not word_prefix:
                    completions.append(CompletionCandidate(
                        text=keyword,
                        label=keyword,
                        kind="keyword",
                        score=0.5
                    ))
            
            for builtin in builtins:
                if word_prefix in builtin or not word_prefix:
                    completions.append(CompletionCandidate(
                        text=builtin,
                        label=builtin + "()",
                        kind="function",
                        detail="Built-in function",
                        score=0.6
                    ))
        
        # JavaScript/TypeScript keywords
        elif language in ["javascript", "typescript"]:
            keywords = [
                "function", "const", "let", "var", "if", "else", "for", "while",
                "try", "catch", "finally", "async", "await", "import", "export",
                "return", "class", "extends", "super", "this"
            ]
            
            for keyword in keywords:
                if word_prefix in keyword or not word_prefix:
                    completions.append(CompletionCandidate(
                        text=keyword,
                        label=keyword,
                        kind="keyword",
                        score=0.5
                    ))
        
        return completions
    
    def _build_completion_query(self, context: Dict[str, Any]) -> str:
        """Build query for RAG retrieval from context"""
        prefix = context["prefix"]
        recent_code = context["recent_code"]
        
        # Extract meaningful parts
        query_parts = []
        
        # Last function/class definition
        func_match = re.search(r'(def|class|function)\s+(\w+)', recent_code)
        if func_match:
            query_parts.append(func_match.group(2))
        
        # Current line context
        if prefix.strip():
            # Remove common patterns
            clean_prefix = re.sub(r'^\s*(self\.|this\.)', '', prefix)
            if clean_prefix.strip():
                query_parts.append(clean_prefix.strip())
        
        return " ".join(query_parts) if query_parts else "code completion"
    
    def _build_completion_prompt(
        self,
        context: Dict[str, Any],
        file_path: str,
        language: str
    ) -> str:
        """Build prompt for LLM completion generation"""
        prefix = context["prefix"]
        recent_code = context["recent_code"]
        word_prefix = context["word_prefix"]
        
        return f"""Generate code completions for {language} code.

File: {file_path}
Current line: {context['current_line']}
Cursor position: column {context['cursor_column']}
Typing: "{word_prefix}"

Recent code context:
{recent_code}

Current line prefix: {prefix}

Generate 3-5 concise completion suggestions that would make sense at this position.
Return only the completion text, one per line, without explanations."""
    
    def _deduplicate_completions(
        self,
        completions: List[CompletionCandidate]
    ) -> List[CompletionCandidate]:
        """Remove duplicate completions"""
        seen = set()
        unique = []
        
        for comp in completions:
            # Use label as key for deduplication
            key = comp.label.lower()
            if key not in seen:
                seen.add(key)
                unique.append(comp)
        
        return unique
    
    def _rank_completions(
        self,
        completions: List[CompletionCandidate],
        context: Dict[str, Any]
    ) -> List[CompletionCandidate]:
        """Rank completions by relevance"""
        word_prefix = context["word_prefix"].lower()
        
        # Boost score for prefix matches
        for comp in completions:
            comp_lower = comp.label.lower()
            
            # Exact prefix match gets highest score
            if comp_lower.startswith(word_prefix) and word_prefix:
                comp.score += 0.3
            
            # Contains prefix
            elif word_prefix in comp_lower and word_prefix:
                comp.score += 0.1
            
            # Functions get slight boost
            if comp.kind == "function":
                comp.score += 0.1
        
        # Sort by score (descending)
        completions.sort(key=lambda x: x.score, reverse=True)
        
        return completions
    
    def _get_cache_key(
        self,
        file_path: str,
        context: Dict[str, Any],
        line: int,
        column: int
    ) -> str:
        """Generate cache key for completion request"""
        prefix = context["prefix"][-20:]  # Last 20 chars
        return f"{file_path}:{line}:{column}:{prefix}"
    
    def clear_cache(self):
        """Clear completion cache"""
        self.completion_cache.clear()






