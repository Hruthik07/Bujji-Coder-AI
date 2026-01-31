"""
Auto-extract unified diffs from LLM responses
"""
import re
from typing import List, Optional, Tuple


class DiffExtractor:
    """
    Extracts unified diffs from LLM text responses.
    Handles various formats and edge cases.
    """
    
    def __init__(self):
        # Pattern to match diff blocks
        self.diff_pattern = re.compile(
            r'(?:^|\n)(---\s+a/.*?\n\+\+\+\s+b/.*?\n(?:@@.*?@@\n(?:[+\- ].*\n?)*)+)',
            re.MULTILINE
        )
    
    def extract_diffs(self, text: str) -> List[str]:
        """
        Extract all unified diffs from text.
        
        Args:
            text: Text that may contain diffs
            
        Returns:
            List of diff strings
        """
        diffs = []
        
        # Find all diff blocks
        matches = self.diff_pattern.finditer(text)
        
        for match in matches:
            diff_text = match.group(1).strip()
            if self._is_valid_diff(diff_text):
                diffs.append(diff_text)
        
        return diffs
    
    def extract_first_diff(self, text: str) -> Optional[str]:
        """
        Extract the first diff found in text.
        
        Args:
            text: Text that may contain a diff
            
        Returns:
            First diff string or None
        """
        diffs = self.extract_diffs(text)
        return diffs[0] if diffs else None
    
    def has_diff(self, text: str) -> bool:
        """Check if text contains a diff"""
        return len(self.extract_diffs(text)) > 0
    
    def clean_diff(self, diff_text: str) -> str:
        """
        Clean and normalize a diff string.
        Removes markdown code blocks, extra whitespace, etc.
        """
        # Remove markdown code blocks
        diff_text = re.sub(r'```(?:diff)?\s*\n', '', diff_text)
        diff_text = re.sub(r'```\s*$', '', diff_text, flags=re.MULTILINE)
        
        # Remove leading/trailing whitespace
        diff_text = diff_text.strip()
        
        # Ensure proper line endings
        lines = diff_text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Remove markdown formatting
            line = re.sub(r'^```', '', line)
            line = re.sub(r'```$', '', line)
            
            # Keep diff lines (starting with ---, +++, @@, +, -, or space)
            if re.match(r'^(---|\+\+\+|@@|[+\- ])', line):
                cleaned_lines.append(line)
            elif line.strip() == '':
                # Keep empty lines between hunks
                if cleaned_lines and cleaned_lines[-1].strip():
                    cleaned_lines.append('')
        
        return '\n'.join(cleaned_lines)
    
    def _is_valid_diff(self, diff_text: str) -> bool:
        """Check if a string is a valid unified diff"""
        lines = diff_text.split('\n')
        
        # Must have at least --- and +++ lines
        has_old_file = any(line.startswith('---') for line in lines)
        has_new_file = any(line.startswith('+++') for line in lines)
        has_hunk = any(line.startswith('@@') for line in lines)
        
        return has_old_file and has_new_file and has_hunk
    
    def extract_with_context(self, text: str) -> List[Tuple[str, Optional[str]]]:
        """
        Extract diffs with surrounding context.
        
        Args:
            text: Text containing diffs
            
        Returns:
            List of (diff_text, context) tuples
        """
        results = []
        diffs = self.extract_diffs(text)
        
        for diff in diffs:
            # Find context before diff
            diff_start = text.find(diff)
            context_start = max(0, diff_start - 200)
            context = text[context_start:diff_start].strip()
            
            results.append((diff, context if context else None))
        
        return results
    
    def split_text_and_diffs(self, text: str) -> Tuple[str, List[str]]:
        """
        Split text into non-diff content and diffs.
        
        Args:
            text: Text that may contain diffs
            
        Returns:
            Tuple of (text_without_diffs, list_of_diffs)
        """
        diffs = self.extract_diffs(text)
        text_without_diffs = text
        
        # Remove diffs from text
        for diff in diffs:
            text_without_diffs = text_without_diffs.replace(diff, '', 1)
        
        return text_without_diffs.strip(), diffs
