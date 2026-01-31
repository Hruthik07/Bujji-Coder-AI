"""
Runtime Debugger - Executes code and collects runtime data
Similar to Cursor AI's runtime debugging
"""
import subprocess
import re
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from .terminal import Terminal
from .code_instrumentation import CodeInstrumentation
from .error_parser import ErrorParser


class RuntimeDebugger:
    """
    Executes code and collects runtime data for debugging
    Analyzes execution traces, variable states, and error conditions
    """
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = Path(workspace_path).resolve()
        self.terminal = Terminal(workspace_path)
        self.instrumentation = CodeInstrumentation(workspace_path)
        self.error_parser = ErrorParser()
        self.instrumentation_id = "__debug_instrumentation__"
    
    def debug_execution(
        self,
        file_path: str,
        arguments: Optional[List[str]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Execute file and collect runtime debugging data
        
        Args:
            file_path: Path to file to execute
            arguments: Command line arguments
            timeout: Execution timeout in seconds
            
        Returns:
            Dict with execution trace, variable states, and errors
        """
        full_path = self.workspace_path / file_path
        
        if not full_path.exists():
            return {"error": f"File not found: {file_path}"}
        
        # Execute the file
        cmd = f'python "{full_path}"'
        if arguments:
            cmd += " " + " ".join(arguments)
        
        result = self.terminal.execute(cmd, is_background=False)
        
        # Parse output for instrumentation data
        trace_data = self._parse_instrumentation_output(result.get("stdout", ""))
        error_data = None
        
        if result.get("stderr"):
            error_data = self.error_parser.parse_error(result.get("stderr", ""))
        
        # Convert ParsedError to dict
        error_dict = None
        if error_data:
            error_dict = {
                "error_type": error_data.error_type,
                "error_message": error_data.error_message,
                "primary_file": error_data.primary_file,
                "primary_line": error_data.primary_line,
                "stack_trace": [
                    {
                        "file_path": frame.file_path,
                        "line_number": frame.line_number,
                        "function_name": frame.function_name
                    }
                    for frame in error_data.stack_trace
                ]
            }
        
        return {
            "success": result.get("success", False),
            "file_path": file_path,
            "returncode": result.get("returncode", -1),
            "execution_trace": trace_data,
            "error": error_dict,
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "timing": {
                "executed": True,
                "timeout": timeout
            }
        }
    
    def debug_with_instrumentation(
        self,
        file_path: str,
        instrument_config: Optional[Dict[str, Any]] = None,
        arguments: Optional[List[str]] = None,
        restore_after: bool = True
    ) -> Dict[str, Any]:
        """
        Instrument file, execute, collect data, and optionally restore
        
        Args:
            file_path: Path to file
            instrument_config: Instrumentation configuration
            arguments: Command line arguments
            restore_after: Restore original file after execution
            
        Returns:
            Dict with instrumentation results and execution data
        """
        # Instrument the file
        inst_config = instrument_config or {
            "instrument_functions": True,
            "instrument_variables": True,
            "instrument_conditions": True
        }
        
        inst_result = self.instrumentation.instrument_file(file_path, **inst_config)
        
        if "error" in inst_result:
            return {"error": inst_result["error"]}
        
        try:
            # Execute instrumented file
            exec_result = self.debug_execution(file_path, arguments)
            
            # Combine results
            result = {
                "instrumentation": inst_result,
                "execution": exec_result,
                "runtime_data": self._extract_runtime_data(exec_result.get("execution_trace", []))
            }
            
            # Restore if requested
            if restore_after:
                restore_result = self.instrumentation.restore_file(file_path)
                result["restored"] = restore_result.get("success", False)
            
            return result
        
        except Exception as e:
            # Restore on error
            if restore_after:
                self.instrumentation.restore_file(file_path)
            return {"error": str(e)}
    
    def _parse_instrumentation_output(self, output: str) -> List[Dict[str, Any]]:
        """Parse instrumentation logs from output"""
        trace = []
        lines = output.split('\n')
        
        for line in lines:
            if self.instrumentation_id in line:
                # Parse instrumentation log
                # Format: [__debug_instrumentation__] TYPE context
                match = re.search(rf'\[{self.instrumentation_id}\]\s+(\w+)\s+(.+)', line)
                if match:
                    trace_type = match.group(1)
                    context = match.group(2)
                    
                    trace.append({
                        "type": trace_type.lower(),
                        "context": context,
                        "raw": line
                    })
        
        return trace
    
    def _extract_runtime_data(self, trace: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Extract meaningful runtime data from trace"""
        data = {
            "function_calls": [],
            "variable_states": {},
            "condition_results": [],
            "execution_flow": []
        }
        
        for entry in trace:
            entry_type = entry.get("type", "")
            context = entry.get("context", "")
            
            if entry_type == "enter":
                # Function entry
                func_name = context.replace("()", "")
                data["function_calls"].append({
                    "function": func_name,
                    "action": "enter"
                })
                data["execution_flow"].append(f"Enter {func_name}()")
            
            elif entry_type == "exit":
                # Function exit
                func_name = context.replace("()", "")
                data["function_calls"].append({
                    "function": func_name,
                    "action": "exit"
                })
                data["execution_flow"].append(f"Exit {func_name}()")
            
            elif entry_type == "var":
                # Variable assignment
                # Format: VAR name = {value}
                var_match = re.search(r'VAR\s+(\w+)\s*=\s*(.+)', context)
                if var_match:
                    var_name = var_match.group(1)
                    var_value = var_match.group(2).strip('{}')
                    data["variable_states"][var_name] = var_value
                    data["execution_flow"].append(f"Set {var_name} = {var_value}")
            
            elif entry_type == "cond":
                # Condition check
                data["condition_results"].append({
                    "condition": context,
                    "result": "unknown"  # Would need to parse actual result
                })
                data["execution_flow"].append(f"Check: {context}")
        
        return data
    
    def analyze_execution_trace(
        self,
        trace_data: Dict[str, Any],
        bug_description: str
    ) -> Dict[str, Any]:
        """
        Analyze execution trace to identify potential issues
        
        Args:
            trace_data: Runtime data from execution
            bug_description: Description of the bug
            
        Returns:
            Analysis with potential issues and suggestions
        """
        analysis = {
            "issues_found": [],
            "suspicious_patterns": [],
            "suggestions": []
        }
        
        runtime_data = trace_data.get("runtime_data", {})
        execution_flow = runtime_data.get("execution_flow", [])
        variable_states = runtime_data.get("variable_states", {})
        
        # Check for suspicious patterns
        # 1. Functions that enter but never exit (potential crash)
        function_calls = runtime_data.get("function_calls", [])
        entered_functions = set()
        exited_functions = set()
        
        for call in function_calls:
            if call.get("action") == "enter":
                entered_functions.add(call.get("function"))
            elif call.get("action") == "exit":
                exited_functions.add(call.get("function"))
        
        never_exited = entered_functions - exited_functions
        if never_exited:
            analysis["issues_found"].append({
                "type": "function_never_exited",
                "functions": list(never_exited),
                "severity": "high",
                "description": "Functions that were entered but never exited (possible crash or infinite loop)"
            })
        
        # 2. Check for None or unexpected variable values
        for var_name, var_value in variable_states.items():
            if var_value == "None" or var_value == "null":
                analysis["suspicious_patterns"].append({
                    "type": "null_variable",
                    "variable": var_name,
                    "value": var_value,
                    "description": f"Variable {var_name} is None/null"
                })
        
        # 3. Check execution flow length (potential infinite loop)
        if len(execution_flow) > 1000:
            analysis["issues_found"].append({
                "type": "potential_infinite_loop",
                "severity": "high",
                "description": "Very long execution trace, possible infinite loop"
            })
        
        return analysis

