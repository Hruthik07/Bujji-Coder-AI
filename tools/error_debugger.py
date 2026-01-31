"""
Error-Aware Debugging System
Integrates error parsing with RAG for context-aware debugging
"""
from pathlib import Path
from typing import Dict, List, Optional, Any

from .error_parser import ErrorParser, ParsedError
from .rag_system import RAGSystem
from .file_operations import FileOperations


class ErrorDebugger:
    """
    Error-aware debugging system.
    Parses errors, retrieves relevant code context, and suggests fixes.
    """
    
    def __init__(self, rag_system: RAGSystem, workspace_path: str = "."):
        self.rag_system = rag_system
        self.workspace_path = Path(workspace_path).resolve()
        self.error_parser = ErrorParser()
        self.file_ops = FileOperations(workspace_path)
    
    def debug_error(self, error_text: str) -> Dict[str, Any]:
        """
        Debug an error by parsing it and retrieving relevant context.
        
        Args:
            error_text: Full error output including stack trace
            
        Returns:
            Dict with error analysis and context
        """
        # Parse error
        parsed_error = self.error_parser.parse_error(error_text)
        
        # Get error context
        context = self._get_error_context(parsed_error)
        
        # Retrieve relevant code
        relevant_code = self._retrieve_relevant_code(parsed_error)
        
        return {
            "error": {
                "type": parsed_error.error_type,
                "message": parsed_error.error_message,
                "primary_file": parsed_error.primary_file,
                "primary_line": parsed_error.primary_line
            },
            "stack_trace": [
                {
                    "file": frame.file_path,
                    "line": frame.line_number,
                    "function": frame.function_name
                }
                for frame in parsed_error.stack_trace
            ],
            "context": context,
            "relevant_code": relevant_code,
            "suggestions": self._generate_suggestions(parsed_error, relevant_code)
        }
    
    def _get_error_context(self, parsed_error: ParsedError) -> Dict[str, Any]:
        """Get context around the error location"""
        if not parsed_error.primary_file or not parsed_error.primary_line:
            return {}
        
        try:
            file_path = self.workspace_path / parsed_error.primary_file
            if not file_path.exists():
                return {}
            
            # Read file around error line
            result = self.file_ops.read_file(
                str(file_path),
                offset=max(1, parsed_error.primary_line - 10),
                limit=20
            )
            
            if result.get("exists"):
                lines = result.get("content", "").split('\n')
                error_line_idx = parsed_error.primary_line - max(1, parsed_error.primary_line - 10) - 1
                
                return {
                    "file": parsed_error.primary_file,
                    "error_line": parsed_error.primary_line,
                    "code_snippet": result.get("content", ""),
                    "error_line_content": lines[error_line_idx] if 0 <= error_line_idx < len(lines) else ""
                }
        
        except Exception as e:
            return {"error": str(e)}
        
        return {}
    
    def _retrieve_relevant_code(self, parsed_error: ParsedError) -> List[Dict[str, Any]]:
        """Retrieve relevant code chunks using RAG"""
        if not self.rag_system or not self.rag_system.is_indexed:
            return []
        
        # Build query from error
        query = f"{parsed_error.error_type}: {parsed_error.error_message}"
        
        # Add function name if available
        if parsed_error.stack_trace:
            func_name = parsed_error.stack_trace[-1].function_name
            if func_name:
                query += f" in {func_name}"
        
        # Retrieve relevant chunks
        chunks = self.rag_system.retrieve(query, top_k=5, use_hybrid=True)
        
        return chunks
    
    def _generate_suggestions(self, parsed_error: ParsedError, 
                            relevant_code: List[Dict]) -> List[str]:
        """Generate fix suggestions based on error and code"""
        suggestions = []
        
        error_type = parsed_error.error_type
        error_msg = parsed_error.error_message.lower()
        
        # Common error patterns
        if "nameerror" in error_type.lower() or "name" in error_msg:
            suggestions.append("Check if the variable/function name is defined and spelled correctly")
            suggestions.append("Verify imports if it's a module or class name")
        
        if "attributeerror" in error_type.lower() or "attribute" in error_msg:
            suggestions.append("Check if the object has the attribute you're trying to access")
            suggestions.append("Verify the object type matches your expectations")
        
        if "typeerror" in error_type.lower() or "type" in error_msg:
            suggestions.append("Check argument types match function signature")
            suggestions.append("Verify you're passing the correct number of arguments")
        
        if "importerror" in error_type.lower() or "import" in error_msg:
            suggestions.append("Verify the module is installed: pip install <module>")
            suggestions.append("Check import path is correct")
            suggestions.append("Ensure the module file exists in the expected location")
        
        if "indentationerror" in error_type.lower():
            suggestions.append("Check indentation consistency (use spaces or tabs, not both)")
            suggestions.append("Verify all blocks are properly indented")
        
        if "syntaxerror" in error_type.lower():
            suggestions.append("Check for missing colons, parentheses, or brackets")
            suggestions.append("Verify string quotes are properly closed")
        
        # Add context-specific suggestions
        if relevant_code:
            suggestions.append("Review the relevant code chunks retrieved from your codebase")
            suggestions.append("Check if similar patterns exist elsewhere that work correctly")
        
        return suggestions
    
    def get_fix_context(self, error_text: str) -> str:
        """
        Get formatted context for LLM to generate fixes.
        
        Args:
            error_text: Error output
            
        Returns:
            Formatted context string
        """
        debug_info = self.debug_error(error_text)
        
        context_parts = []
        
        # Error info
        context_parts.append(f"Error: {debug_info['error']['type']}")
        context_parts.append(f"Message: {debug_info['error']['message']}")
        context_parts.append(f"File: {debug_info['error']['primary_file']}")
        context_parts.append(f"Line: {debug_info['error']['primary_line']}")
        context_parts.append("")
        
        # Code context
        if debug_info.get('context', {}).get('code_snippet'):
            context_parts.append("Code around error:")
            context_parts.append(debug_info['context']['code_snippet'])
            context_parts.append("")
        
        # Relevant code
        if debug_info.get('relevant_code'):
            context_parts.append("Relevant code from codebase:")
            for chunk in debug_info['relevant_code'][:3]:
                context_parts.append(f"<file: {chunk['file_path']}, lines {chunk['start_line']}-{chunk['end_line']}>")
                context_parts.append(chunk['content'][:200])
                context_parts.append("")
        
        return "\n".join(context_parts)
