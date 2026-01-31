"""
Terminal operations module - executes shell commands
"""
import subprocess
import os
import sys
from typing import Optional, Dict
from config import Config


class Terminal:
    """Handles terminal command execution"""
    
    def __init__(self, workspace_path: str = "."):
        self.workspace_path = os.path.abspath(workspace_path)
        self.shell = Config.DEFAULT_SHELL
    
    def execute(self, command: str, is_background: bool = False) -> dict:
        """
        Execute a terminal command.
        
        Args:
            command: Command to execute
            is_background: Whether to run in background
            
        Returns:
            dict with 'success', 'stdout', 'stderr', 'returncode', 'error' keys
        """
        try:
            # Change to workspace directory
            original_cwd = os.getcwd()
            os.chdir(self.workspace_path)
            
            try:
                if is_background:
                    # Run in background (non-blocking)
                    if sys.platform == "win32":
                        # Windows background execution
                        process = subprocess.Popen(
                            command,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            creationflags=subprocess.CREATE_NEW_CONSOLE
                        )
                    else:
                        # Unix background execution
                        process = subprocess.Popen(
                            command,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            start_new_session=True
                        )
                    
                    return {
                        "success": True,
                        "stdout": "",
                        "stderr": "",
                        "returncode": 0,
                        "pid": process.pid,
                        "error": None,
                        "background": True
                    }
                else:
                    # Run in foreground (blocking)
                    result = subprocess.run(
                        command,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=300  # 5 minute timeout
                    )
                    
                    return {
                        "success": result.returncode == 0,
                        "stdout": result.stdout,
                        "stderr": result.stderr,
                        "returncode": result.returncode,
                        "error": None,
                        "background": False
                    }
            
            finally:
                os.chdir(original_cwd)
        
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "error": "Command timed out after 5 minutes"
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": "",
                "returncode": -1,
                "error": str(e)
            }

