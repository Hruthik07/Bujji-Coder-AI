"""
Error Parser - Parses stack traces and extracts error context
"""
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class StackFrame:
    """Represents a single stack frame"""
    file_path: str
    line_number: int
    function_name: Optional[str] = None
    code_snippet: Optional[str] = None


@dataclass
class ParsedError:
    """Represents a parsed error with context"""
    error_type: str
    error_message: str
    stack_trace: List[StackFrame]
    primary_file: Optional[str] = None
    primary_line: Optional[int] = None


class ErrorParser:
    """
    Parses Python stack traces and errors.
    Extracts file paths, line numbers, and error context.
    """
    
    def __init__(self):
        # Python traceback patterns
        self.traceback_pattern = re.compile(
            r'File\s+["\']([^"\']+)["\'],\s+line\s+(\d+),\s+in\s+(\w+)',
            re.MULTILINE
        )
        
        # Error type and message pattern
        self.error_pattern = re.compile(
            r'^(\w+(?:Error|Exception|Warning)):\s*(.+)$',
            re.MULTILINE
        )
    
    def parse_error(self, error_text: str) -> ParsedError:
        """
        Parse a complete error/stack trace.
        
        Args:
            error_text: Full error output including stack trace
            
        Returns:
            ParsedError object
        """
        lines = error_text.split('\n')
        
        # Extract error type and message
        error_type = "Error"
        error_message = ""
        
        for line in lines:
            error_match = self.error_pattern.match(line)
            if error_match:
                error_type = error_match.group(1)
                error_message = error_match.group(2).strip()
                break
        
        # Extract stack frames
        stack_frames = []
        for match in self.traceback_pattern.finditer(error_text):
            file_path = match.group(1)
            line_number = int(match.group(2))
            function_name = match.group(3)
            
            stack_frames.append(StackFrame(
                file_path=file_path,
                line_number=line_number,
                function_name=function_name
            ))
        
        # Determine primary file and line (usually the last frame)
        primary_file = stack_frames[-1].file_path if stack_frames else None
        primary_line = stack_frames[-1].line_number if stack_frames else None
        
        return ParsedError(
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_frames,
            primary_file=primary_file,
            primary_line=primary_line
        )
    
    def extract_error_context(self, error_text: str) -> Dict[str, any]:
        """
        Extract error context for debugging.
        
        Args:
            error_text: Error output
            
        Returns:
            Dict with error context
        """
        parsed = self.parse_error(error_text)
        
        return {
            "error_type": parsed.error_type,
            "error_message": parsed.error_message,
            "primary_file": parsed.primary_file,
            "primary_line": parsed.primary_line,
            "stack_depth": len(parsed.stack_trace),
            "stack_frames": [
                {
                    "file": frame.file_path,
                    "line": frame.line_number,
                    "function": frame.function_name
                }
                for frame in parsed.stack_trace
            ]
        }
    
    def get_files_to_retrieve(self, error_text: str) -> List[Tuple[str, int]]:
        """
        Get list of files and lines to retrieve for error context.
        
        Args:
            error_text: Error output
            
        Returns:
            List of (file_path, line_number) tuples
        """
        parsed = self.parse_error(error_text)
        
        files_to_retrieve = []
        for frame in parsed.stack_trace:
            files_to_retrieve.append((frame.file_path, frame.line_number))
        
        return files_to_retrieve
    
    def is_python_error(self, text: str) -> bool:
        """Check if text contains a Python error"""
        return bool(self.traceback_pattern.search(text) or self.error_pattern.search(text))
