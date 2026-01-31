"""
Auto Fixer - Automatically fixes detected bugs using LLM
"""
from typing import List, Dict, Optional, Any
from pathlib import Path
from .bug_detector import Bug, BugDetector
from .diff_editor import DiffEditor
from .file_operations import FileOperations
from .llm_provider import get_provider
from .diff_extractor import DiffExtractor
from config import Config


class AutoFixer:
    """Automatically fixes bugs using LLM-generated diffs"""
    
    def __init__(self, workspace_path: str = ".", bug_detector: Optional[BugDetector] = None):
        self.workspace_path = Path(workspace_path).resolve()
        self.bug_detector = bug_detector or BugDetector(workspace_path)
        self.diff_editor = DiffEditor(workspace_path)
        self.file_ops = FileOperations(workspace_path)
        self.diff_extractor = DiffExtractor()
        
        # Use Claude for fixing (better reasoning)
        try:
            if Config.ANTHROPIC_API_KEY:
                self.llm_provider = get_provider("anthropic", Config.ANTHROPIC_API_KEY)
            else:
                # Fallback to OpenAI
                self.llm_provider = get_provider("openai", Config.OPENAI_API_KEY)
        except Exception as e:
            print(f"⚠️  LLM provider initialization failed: {e}")
            self.llm_provider = None
    
    def fix_bug(self, bug: Bug) -> Dict[str, Any]:
        """
        Fix a single bug
        
        Args:
            bug: Bug object to fix
            
        Returns:
            Dict with success status, diff, and result
        """
        if not self.llm_provider:
            return {"success": False, "error": "LLM provider not available"}
        
        # Read file
        file_result = self.file_ops.read_file(bug.file_path)
        
        if not file_result.get("exists"):
            return {"success": False, "error": f"File not found: {bug.file_path}"}
        
        file_content = file_result.get("content", "")
        
        # Generate fix using LLM
        fix_prompt = self._build_fix_prompt(bug, file_content)
        
        try:
            # Determine model
            model = Config.ANTHROPIC_MODEL if hasattr(Config, 'ANTHROPIC_MODEL') and Config.ANTHROPIC_API_KEY else Config.OPENAI_MODEL
            
            response = self.llm_provider.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": """You are a code fixer. Your job is to fix bugs by generating unified diffs.
                        
Rules:
1. Only fix the specific bug mentioned - don't change other code
2. Generate a unified diff in the format:
   ```diff
   --- a/file_path
   +++ b/file_path
   @@ -line,context +line,context @@
   -old code
   +new code
   ```
3. Be precise - only change what's necessary
4. Preserve code style and formatting
5. If the bug can't be fixed automatically, explain why"""
                    },
                    {
                        "role": "user",
                        "content": fix_prompt
                    }
                ],
                model=model,
                temperature=0.3,  # Lower temperature for more consistent fixes
                max_tokens=2000
            )
            
            # Extract diff from response
            diffs = self.diff_extractor.extract_diffs(response.content)
            
            if not diffs:
                # Try to find diff in response
                import re
                diff_match = re.search(r'```(?:diff)?\n(.*?)\n```', response.content, re.DOTALL)
                if diff_match:
                    diffs = [diff_match.group(1)]
            
            if diffs:
                # Apply fix
                try:
                    file_diffs = self.diff_editor.parse_diff(diffs[0])
                    if file_diffs:
                        result = self.diff_editor.apply_diffs(file_diffs, dry_run=False)
                        return {
                            "success": result.get("success", False),
                            "diff": diffs[0],
                            "result": result,
                            "response": response.content
                        }
                    else:
                        return {
                            "success": False,
                            "error": "Could not parse diff",
                            "response": response.content
                        }
                except Exception as e:
                    return {
                        "success": False,
                        "error": f"Failed to apply diff: {str(e)}",
                        "diff": diffs[0] if diffs else None,
                        "response": response.content
                    }
            else:
                return {
                    "success": False,
                    "error": "No diff found in LLM response",
                    "response": response.content
                }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"LLM call failed: {str(e)}"
            }
    
    def fix_bugs(self, bugs: List[Bug], max_fixes: Optional[int] = None) -> Dict[str, Any]:
        """
        Fix multiple bugs
        
        Args:
            bugs: List of Bug objects
            max_fixes: Maximum number of bugs to fix (None = all)
            
        Returns:
            Dict with results for each bug
        """
        results = {
            "total": len(bugs),
            "fixed": [],
            "failed": [],
            "skipped": []
        }
        
        bugs_to_fix = bugs[:max_fixes] if max_fixes else bugs
        
        for bug in bugs_to_fix:
            # Skip critical syntax errors - they need manual fixing
            if bug.bug_type == "syntax" and bug.severity == "critical":
                results["skipped"].append({
                    "bug": bug,
                    "reason": "Critical syntax errors require manual fixing"
                })
                continue
            
            fix_result = self.fix_bug(bug)
            
            if fix_result.get("success"):
                results["fixed"].append({
                    "bug": bug,
                    "fix": fix_result
                })
            else:
                results["failed"].append({
                    "bug": bug,
                    "error": fix_result.get("error"),
                    "response": fix_result.get("response")
                })
        
        return results
    
    def _build_fix_prompt(self, bug: Bug, file_content: str) -> str:
        """Build prompt for LLM to fix bug"""
        prompt = f"""Fix this bug in the code:

File: {bug.file_path}
Line: {bug.line_number}
Bug Type: {bug.bug_type}
Severity: {bug.severity}
Message: {bug.message}
Code Snippet: {bug.code_snippet}
Suggestion: {bug.suggestion or "Fix the bug"}

Full file content:
```python
{file_content}
```

Generate a unified diff to fix this bug. Only fix the specific bug mentioned above, don't change other code.
Use this format:
```diff
--- a/{bug.file_path}
+++ b/{bug.file_path}
@@ -line,context +line,context @@
-old code
+new code
```"""
        return prompt






