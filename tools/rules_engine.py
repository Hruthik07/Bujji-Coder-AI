"""
Rules Engine
Parses and manages .cursorrules files for project-specific instructions
"""
from pathlib import Path
from typing import Optional, List, Dict, Any
import re
import os
import time


class RulesEngine:
    """Manages .cursorrules files and injects them into system prompts"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.rules_file = self.workspace_path / ".cursorrules"
        self.rules_content = None
        self.rules_loaded = False
        self._file_mtime: float = 0.0  # Track file modification time for cache invalidation
    
    def load_rules(self) -> bool:
        """
        Load rules from .cursorrules file with caching.
        
        Returns:
            True if rules file exists and was loaded, False otherwise
        """
        try:
            if not self.rules_file.exists():
                self.rules_content = None
                self.rules_loaded = False
                self._file_mtime = 0.0
                return False
            
            # Check if file has changed (cache invalidation)
            current_mtime = os.path.getmtime(self.rules_file)
            if self.rules_loaded and current_mtime == self._file_mtime:
                # File hasn't changed, use cached content
                return True
            
            # File changed or not loaded, read it
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                self.rules_content = f.read().strip()
            self.rules_loaded = True
            self._file_mtime = current_mtime
            return True
        except Exception as e:
            print(f"[WARN] Error loading rules file: {e}")
            self.rules_content = None
            self.rules_loaded = False
            self._file_mtime = 0.0
            return False
    
    def get_rules(self) -> Optional[str]:
        """
        Get current rules content
        
        Returns:
            Rules content as string, or None if not loaded
        """
        if not self.rules_loaded:
            self.load_rules()
        return self.rules_content
    
    def save_rules(self, content: str) -> Dict[str, Any]:
        """
        Save rules to .cursorrules file
        
        Args:
            content: Rules content to save
            
        Returns:
            Dict with success status and message
        """
        try:
            # Validate content (basic check)
            if not content.strip():
                return {"success": False, "message": "Rules content cannot be empty"}
            
            # Save to file
            with open(self.rules_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Reload rules
            self.rules_content = content.strip()
            self.rules_loaded = True
            
            return {
                "success": True,
                "message": "Rules saved successfully",
                "path": str(self.rules_file.relative_to(self.workspace_path))
            }
        except Exception as e:
            return {"success": False, "message": f"Error saving rules: {str(e)}"}
    
    def inject_into_prompt(self, base_prompt: str) -> str:
        """
        Inject rules into system prompt
        
        Args:
            base_prompt: Base system prompt
            
        Returns:
            System prompt with rules injected
        """
        if not self.rules_loaded:
            self.load_rules()
        
        if not self.rules_content:
            return base_prompt
        
        # Inject rules as a section in the prompt
        rules_section = f"""

<project_rules>
The following are project-specific rules and guidelines that should be followed:

{self.rules_content}
</project_rules>
"""
        
        # Insert rules before the closing of the prompt
        # Try to insert before "Always be helpful" or at the end
        if "Always be helpful" in base_prompt:
            return base_prompt.replace(
                "Always be helpful",
                f"{rules_section}\nAlways be helpful"
            )
        else:
            return base_prompt + rules_section
    
    def validate_rules(self, content: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate rules content
        
        Args:
            content: Optional content to validate (if None, validates current rules)
            
        Returns:
            Dict with validation status and any errors
        """
        rules_to_validate = content if content is not None else self.rules_content
        
        if not rules_to_validate:
            return {"valid": True, "errors": []}
        
        errors = []
        warnings = []
        
        # Basic validation checks
        lines = rules_to_validate.split('\n')
        
        # Check for extremely long lines (potential formatting issues)
        for i, line in enumerate(lines, 1):
            if len(line) > 500:
                warnings.append(f"Line {i}: Very long line ({len(line)} chars) - consider breaking it up")
        
        # Check for common issues
        if len(rules_to_validate) > 10000:
            warnings.append("Rules file is very large (>10KB) - may impact prompt size")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def get_rules_info(self) -> Dict[str, Any]:
        """
        Get information about current rules
        
        Returns:
            Dict with rules metadata
        """
        if not self.rules_loaded:
            self.load_rules()
        
        return {
            "exists": self.rules_file.exists(),
            "loaded": self.rules_loaded,
            "path": str(self.rules_file.relative_to(self.workspace_path)),
            "size": len(self.rules_content) if self.rules_content else 0,
            "line_count": len(self.rules_content.split('\n')) if self.rules_content else 0
        }
