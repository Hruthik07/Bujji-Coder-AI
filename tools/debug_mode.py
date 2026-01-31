"""
Debug Mode - Comprehensive codebase debugging system
Orchestrates scanning, bug detection, and auto-fixing
Combines static analysis with runtime debugging (better than Cursor AI!)
"""
from pathlib import Path
from typing import List, Dict, Optional, Any
from .code_scanner import CodeScanner
from .bug_detector import BugDetector, Bug
from .auto_fixer import AutoFixer
from .interactive_debug_mode import InteractiveDebugMode


class DebugMode:
    """Main debug mode orchestrator"""
    
    def __init__(self, workspace_path: str = ".", rag_system=None):
        self.workspace_path = Path(workspace_path).resolve()
        self.scanner = CodeScanner(workspace_path)
        self.detector = BugDetector(workspace_path)
        self.fixer = AutoFixer(workspace_path, self.detector)
        self.interactive_debug = InteractiveDebugMode(workspace_path, rag_system)
    
    def debug_codebase(
        self,
        auto_fix: bool = True,
        file_pattern: Optional[str] = None,
        max_files: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Debug entire codebase
        
        Args:
            auto_fix: If True, automatically fix bugs
            file_pattern: Optional pattern to filter files (e.g., "*.py")
            max_files: Maximum number of files to analyze (None = all)
            
        Returns:
            Dict with scan results, bugs found, and fixes applied
        """
        results = {
            "files_scanned": 0,
            "files_analyzed": 0,
            "bugs_found": [],
            "bugs_fixed": [],
            "bugs_failed": [],
            "bugs_skipped": [],
            "summary": {}
        }
        
        # 1. Scan all files
        print("[SCAN] Scanning codebase...")
        # #region agent log
        import json as json_lib; log_file = open(r"c:\Users\gdhru\Bujji_Coder_AI\.cursor\debug.log", "a", encoding="utf-8"); log_file.write(json_lib.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"debug_mode.py:52","message":"Starting codebase scan","data":{"workspace_path":str(self.scanner.workspace_path)},"timestamp":int(__import__("time").time()*1000)})+"\n"); log_file.close()
        # #endregion
        try:
            files = self.scanner.scan_codebase()
            # #region agent log
            import json as json_lib; log_file = open(r"c:\Users\gdhru\Bujji_Coder_AI\.cursor\debug.log", "a", encoding="utf-8"); log_file.write(json_lib.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"debug_mode.py:56","message":"Scan completed","data":{"files_found":len(files)},"timestamp":int(__import__("time").time()*1000)})+"\n"); log_file.close()
            # #endregion
        except Exception as e:
            # #region agent log
            import json as json_lib; log_file = open(r"c:\Users\gdhru\Bujji_Coder_AI\.cursor\debug.log", "a", encoding="utf-8"); log_file.write(json_lib.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"debug_mode.py:59","message":"Scan failed","data":{"error_type":type(e).__name__,"error_message":str(e)},"timestamp":int(__import__("time").time()*1000)})+"\n"); log_file.close()
            # #endregion
            files = []
        
        # Filter by pattern if provided
        if file_pattern:
            import fnmatch
            files_before = len(files)
            files = [f for f in files if fnmatch.fnmatch(f["path"], file_pattern)]
            # #region agent log
            import json as json_lib; log_file = open(r"c:\Users\gdhru\Bujji_Coder_AI\.cursor\debug.log", "a", encoding="utf-8"); log_file.write(json_lib.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"debug_mode.py:68","message":"Pattern filter applied","data":{"pattern":file_pattern,"before":files_before,"after":len(files)},"timestamp":int(__import__("time").time()*1000)})+"\n"); log_file.close()
            # #endregion
        
        # Limit files if specified
        if max_files:
            files = files[:max_files]
        
        results["files_scanned"] = len(files)
        # #region agent log
        import json as json_lib; log_file = open(r"c:\Users\gdhru\Bujji_Coder_AI\.cursor\debug.log", "a", encoding="utf-8"); log_file.write(json_lib.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"debug_mode.py:76","message":"Files scanned count set","data":{"count":len(files)},"timestamp":int(__import__("time").time()*1000)})+"\n"); log_file.close()
        # #endregion
        
        # 2. Detect bugs in each file
        print(f"[BUGS] Detecting bugs in {len(files)} files...")
        all_bugs = []
        files_with_bugs = 0
        
        for file_info in files:
            try:
                bugs = self.detector.detect_bugs(file_info["path"])
                if bugs:
                    all_bugs.extend(bugs)
                    files_with_bugs += 1
                    print(f"  Found {len(bugs)} bug(s) in {file_info['path']}")
            except Exception as e:
                print(f"  [WARN] Error analyzing {file_info['path']}: {e}")
                continue
        
        results["files_analyzed"] = len(files)
        results["bugs_found"] = [self._bug_to_dict(bug) for bug in all_bugs]
        
        # 3. Auto-fix if requested
        if auto_fix and all_bugs:
            print(f"[FIX] Auto-fixing {len(all_bugs)} bug(s)...")
            fix_results = self.fixer.fix_bugs(all_bugs)
            
            results["bugs_fixed"] = [
                {
                    "bug": self._bug_to_dict(item["bug"]),
                    "fix": item["fix"]
                }
                for item in fix_results["fixed"]
            ]
            
            results["bugs_failed"] = [
                {
                    "bug": self._bug_to_dict(item["bug"]),
                    "error": item.get("error", "Unknown error")
                }
                for item in fix_results["failed"]
            ]
            
            results["bugs_skipped"] = [
                {
                    "bug": self._bug_to_dict(item["bug"]),
                    "reason": item.get("reason", "Skipped")
                }
                for item in fix_results["skipped"]
            ]
            
            print(f"  ✅ Fixed: {len(results['bugs_fixed'])}")
            print(f"  [FAIL] Failed: {len(results['bugs_failed'])}")
            print(f"  [SKIP] Skipped: {len(results['bugs_skipped'])}")
        
        # 4. Generate summary
        results["summary"] = {
            "total_files": len(files),
            "files_with_bugs": files_with_bugs,
            "total_bugs": len(all_bugs),
            "bugs_fixed": len(results["bugs_fixed"]),
            "bugs_failed": len(results["bugs_failed"]),
            "bugs_skipped": len(results["bugs_skipped"]),
            "by_severity": self._count_by_severity(all_bugs),
            "by_type": self._count_by_type(all_bugs)
        }
        
        return results
    
    def debug_file(self, file_path: str, auto_fix: bool = True) -> Dict[str, Any]:
        """
        Debug a single file
        
        Args:
            file_path: Path to file to debug
            auto_fix: If True, automatically fix bugs
            
        Returns:
            Dict with bugs found and fixes applied
        """
        results = {
            "file": file_path,
            "bugs_found": [],
            "bugs_fixed": [],
            "bugs_failed": []
        }
        
        # Detect bugs
        bugs = self.detector.detect_bugs(file_path)
        results["bugs_found"] = [self._bug_to_dict(bug) for bug in bugs]
        
        # Auto-fix if requested
        if auto_fix and bugs:
            fix_results = self.fixer.fix_bugs(bugs)
            
            results["bugs_fixed"] = [
                {
                    "bug": self._bug_to_dict(item["bug"]),
                    "fix": item["fix"]
                }
                for item in fix_results["fixed"]
            ]
            
            results["bugs_failed"] = [
                {
                    "bug": self._bug_to_dict(item["bug"]),
                    "error": item.get("error", "Unknown error")
                }
                for item in fix_results["failed"]
            ]
        
        return results
    
    def _bug_to_dict(self, bug: Bug) -> Dict:
        """Convert Bug to dict"""
        return {
            "file_path": bug.file_path,
            "line_number": bug.line_number,
            "column": bug.column,
            "bug_type": bug.bug_type,
            "severity": bug.severity,
            "message": bug.message,
            "code_snippet": bug.code_snippet,
            "suggestion": bug.suggestion
        }
    
    def _count_by_severity(self, bugs: List[Bug]) -> Dict[str, int]:
        """Count bugs by severity"""
        counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for bug in bugs:
            counts[bug.severity] = counts.get(bug.severity, 0) + 1
        return counts
    
    def _count_by_type(self, bugs: List[Bug]) -> Dict[str, int]:
        """Count bugs by type"""
        counts = {}
        for bug in bugs:
            counts[bug.bug_type] = counts.get(bug.bug_type, 0) + 1
        return counts

