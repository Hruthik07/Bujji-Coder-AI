"""
Interactive Debug Mode - Cursor AI-style step-by-step debugging workflow
Combines hypothesis generation, instrumentation, and runtime debugging
"""
from typing import List, Dict, Optional, Any
from .hypothesis_generator import HypothesisGenerator, Hypothesis
from .code_instrumentation import CodeInstrumentation
from .runtime_debugger import RuntimeDebugger
from .bug_detector import BugDetector
from .auto_fixer import AutoFixer
from .rag_system import RAGSystem


class InteractiveDebugMode:
    """
    Interactive debugging workflow similar to Cursor AI
    Step-by-step process: Hypothesis → Instrumentation → Execution → Analysis → Fix
    """
    
    def __init__(self, workspace_path: str = ".", rag_system: Optional[RAGSystem] = None):
        self.workspace_path = workspace_path
        self.hypothesis_generator = HypothesisGenerator(rag_system)
        self.instrumentation = CodeInstrumentation(workspace_path)
        self.runtime_debugger = RuntimeDebugger(workspace_path)
        self.bug_detector = BugDetector(workspace_path)
        self.auto_fixer = AutoFixer(workspace_path)
        self.rag_system = rag_system
    
    def start_debug_session(
        self,
        bug_description: str,
        error_text: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Start an interactive debugging session
        
        Args:
            bug_description: User's description of the bug
            error_text: Optional error message/stack trace
            file_path: Optional file where bug occurs
            
        Returns:
            Dict with session info and initial hypotheses
        """
        # Get code context if file provided
        code_context = None
        if file_path:
            from .file_operations import FileOperations
            file_ops = FileOperations(self.workspace_path)
            file_result = file_ops.read_file(file_path)
            if file_result.get("exists"):
                code_context = file_result.get("content", "")
        
        # Generate hypotheses
        hypotheses = self.hypothesis_generator.generate_hypotheses(
            bug_description=bug_description,
            error_text=error_text,
            file_path=file_path,
            code_context=code_context
        )
        
        return {
            "session_id": f"debug_{id(self)}",
            "bug_description": bug_description,
            "error_text": error_text,
            "file_path": file_path,
            "hypotheses": [self._hypothesis_to_dict(h) for h in hypotheses],
            "status": "hypotheses_generated",
            "next_step": "select_hypothesis"
        }
    
    def test_hypothesis(
        self,
        hypothesis_id: str,
        hypotheses: List[Hypothesis],
        file_path: str,
        arguments: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Test a specific hypothesis by instrumenting and executing
        
        Args:
            hypothesis_id: ID of hypothesis to test
            hypotheses: List of all hypotheses
            file_path: File to test
            arguments: Command line arguments
            
        Returns:
            Dict with instrumentation and execution results
        """
        # Find hypothesis
        hypothesis = next((h for h in hypotheses if h.id == hypothesis_id), None)
        if not hypothesis:
            return {"error": f"Hypothesis {hypothesis_id} not found"}
        
        # Build instrumentation config based on hypothesis
        inst_config = self._build_instrumentation_config(hypothesis)
        
        # Instrument and execute
        result = self.runtime_debugger.debug_with_instrumentation(
            file_path=file_path,
            instrument_config=inst_config,
            arguments=arguments,
            restore_after=False  # Keep instrumentation for analysis
        )
        
        # Analyze results
        if "execution" in result:
            analysis = self.runtime_debugger.analyze_execution_trace(
                result["execution"],
                hypothesis.description
            )
            result["analysis"] = analysis
            
            # Determine if hypothesis is confirmed
            result["hypothesis_confirmed"] = self._evaluate_hypothesis(
                hypothesis,
                result["execution"],
                analysis
            )
        
        return result
    
    def generate_fix(
        self,
        confirmed_hypothesis: Hypothesis,
        execution_data: Dict[str, Any],
        file_path: str
    ) -> Dict[str, Any]:
        """
        Generate fix based on confirmed hypothesis
        
        Args:
            confirmed_hypothesis: The hypothesis that was confirmed
            execution_data: Runtime execution data
            file_path: File to fix
            
        Returns:
            Dict with suggested fix
        """
        # Use hypothesis's suggested fix if available
        if confirmed_hypothesis.suggested_fix:
            return {
                "fix_type": "hypothesis_based",
                "fix": confirmed_hypothesis.suggested_fix,
                "hypothesis": confirmed_hypothesis.description
            }
        
        # Otherwise, use auto-fixer with context
        # Create a bug object from the hypothesis
        from .bug_detector import Bug
        
        bug = Bug(
            file_path=file_path,
            line_number=0,  # Would need to determine from execution data
            bug_type="runtime",
            severity="high",
            message=confirmed_hypothesis.description,
            code_snippet="",
            suggestion=confirmed_hypothesis.reasoning
        )
        
        fix_result = self.auto_fixer.fix_bug(bug)
        return fix_result
    
    def complete_debug_session(
        self,
        file_path: str,
        fix_applied: bool = True
    ) -> Dict[str, Any]:
        """
        Complete debugging session and cleanup
        
        Args:
            file_path: File that was debugged
            fix_applied: Whether fix was applied
            
        Returns:
            Dict with cleanup results
        """
        # Restore file (remove instrumentation)
        restore_result = self.instrumentation.restore_file(file_path)
        
        return {
            "session_complete": True,
            "fix_applied": fix_applied,
            "restored": restore_result.get("success", False)
        }
    
    def _build_instrumentation_config(self, hypothesis: Hypothesis) -> Dict[str, Any]:
        """Build instrumentation config based on hypothesis"""
        config = {
            "instrument_functions": False,
            "instrument_variables": False,
            "instrument_conditions": False,
            "target_functions": []
        }
        
        # Parse hypothesis suggestions to determine what to instrument
        desc_lower = hypothesis.description.lower()
        inst_lower = " ".join(hypothesis.suggested_instrumentation).lower()
        
        if "function" in desc_lower or "function" in inst_lower:
            config["instrument_functions"] = True
        
        if "variable" in desc_lower or "variable" in inst_lower or "value" in inst_lower:
            config["instrument_variables"] = True
        
        if "condition" in desc_lower or "if" in inst_lower or "while" in inst_lower:
            config["instrument_conditions"] = True
        
        # Extract function names if mentioned
        import re
        func_matches = re.findall(r'function[:\s]+(\w+)', inst_lower)
        if func_matches:
            config["target_functions"] = func_matches
        
        return config
    
    def _evaluate_hypothesis(
        self,
        hypothesis: Hypothesis,
        execution_data: Dict[str, Any],
        analysis: Dict[str, Any]
    ) -> bool:
        """Evaluate if hypothesis is confirmed by execution data"""
        # Check if execution data supports the hypothesis
        issues = analysis.get("issues_found", [])
        suspicious = analysis.get("suspicious_patterns", [])
        
        # Simple heuristic: if issues found, hypothesis might be confirmed
        if issues or suspicious:
            return True
        
        # Check if execution trace matches hypothesis description
        desc_lower = hypothesis.description.lower()
        trace_text = str(execution_data).lower()
        
        # If hypothesis mentions something and trace shows it, likely confirmed
        key_terms = ["none", "null", "error", "exception", "crash", "loop"]
        for term in key_terms:
            if term in desc_lower and term in trace_text:
                return True
        
        return False
    
    def _hypothesis_to_dict(self, hypothesis: Hypothesis) -> Dict:
        """Convert Hypothesis to dict"""
        return {
            "id": hypothesis.id,
            "description": hypothesis.description,
            "confidence": hypothesis.confidence,
            "reasoning": hypothesis.reasoning,
            "suggested_instrumentation": hypothesis.suggested_instrumentation,
            "suggested_fix": hypothesis.suggested_fix
        }






