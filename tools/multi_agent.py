"""
Multi-Agent System for Code Generation and Validation
Implements separate agents for retrieval, planning, and validation
"""
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

from .rag_system import RAGSystem
from .diff_editor import DiffEditor
from .file_operations import FileOperations


class AgentRole(Enum):
    """Roles for different agents"""
    RETRIEVER = "retriever"
    PLANNER = "planner"
    VALIDATOR = "validator"
    EXECUTOR = "executor"


@dataclass
class AgentTask:
    """Represents a task for an agent"""
    role: AgentRole
    query: str
    context: Optional[Dict] = None
    result: Optional[Any] = None


class RetrievalAgent:
    """Agent responsible for retrieving relevant code context"""
    
    def __init__(self, rag_system: RAGSystem):
        self.rag_system = rag_system
    
    def execute(self, task: AgentTask) -> Dict[str, Any]:
        """Retrieve relevant code for the query"""
        if not self.rag_system or not self.rag_system.is_indexed:
            return {"status": "error", "message": "RAG system not available"}
        
        chunks = self.rag_system.retrieve(task.query, top_k=10, use_hybrid=True)
        
        return {
            "status": "success",
            "chunks": chunks,
            "count": len(chunks)
        }


class PlanningAgent:
    """Agent responsible for planning code changes"""
    
    def __init__(self, rag_system: Optional[RAGSystem] = None):
        self.rag_system = rag_system
    
    def execute(self, task: AgentTask) -> Dict[str, Any]:
        """Plan the code changes needed"""
        query = task.query
        context = task.context or {}
        
        # Analyze what needs to be done
        plan = {
            "steps": [],
            "files_affected": [],
            "dependencies": []
        }
        
        # Extract file mentions from query
        import re
        file_pattern = r'\b[\w/]+\.(py|js|ts|jsx|tsx)\b'
        files = re.findall(file_pattern, query)
        plan["files_affected"] = list(set(files))
        
        # Determine steps based on query
        if "add" in query.lower() or "create" in query.lower():
            plan["steps"].append("Create new code")
        if "modify" in query.lower() or "change" in query.lower() or "update" in query.lower():
            plan["steps"].append("Modify existing code")
        if "refactor" in query.lower():
            plan["steps"].append("Refactor code structure")
        if "fix" in query.lower() or "debug" in query.lower():
            plan["steps"].append("Fix errors")
        
        # Get dependencies if RAG available
        if self.rag_system and self.rag_system.code_graph:
            for file in plan["files_affected"]:
                # Find related files via imports
                imports = self.rag_system.code_graph.get_import_graph()
                if file in imports:
                    plan["dependencies"].extend(imports[file])
        
        return {
            "status": "success",
            "plan": plan
        }


class ValidationAgent:
    """Agent responsible for validating code changes"""
    
    def __init__(self, diff_editor: DiffEditor, file_ops: FileOperations):
        self.diff_editor = diff_editor
        self.file_ops = file_ops
    
    def execute(self, task: AgentTask) -> Dict[str, Any]:
        """Validate code changes"""
        diff_text = task.context.get("diff_text", "") if task.context else ""
        
        if not diff_text:
            return {"status": "error", "message": "No diff provided"}
        
        # Validate diff
        is_valid, error = self.diff_editor.validate_diff(diff_text)
        
        if not is_valid:
            return {
                "status": "invalid",
                "error": error,
                "suggestions": self._get_validation_suggestions(error)
            }
        
        # Preview diff
        preview = self.diff_editor.preview_diff(diff_text)
        
        return {
            "status": "valid",
            "preview": preview,
            "files_affected": preview.get("files_affected", 0)
        }
    
    def _get_validation_suggestions(self, error: str) -> List[str]:
        """Get suggestions for fixing validation errors"""
        suggestions = []
        
        if "not found" in error.lower():
            suggestions.append("Ensure the file exists before applying the diff")
        if "line" in error.lower() and "exceeds" in error.lower():
            suggestions.append("Check that the line numbers in the diff match the current file")
        if "syntax" in error.lower():
            suggestions.append("Verify the diff syntax is correct (unified diff format)")
        
        return suggestions


class MultiAgentSystem:
    """
    Coordinates multiple agents for complex code tasks.
    Implements a pipeline: Retrieve -> Plan -> Execute -> Validate
    """
    
    def __init__(self, rag_system: Optional[RAGSystem], 
                 diff_editor: DiffEditor,
                 file_ops: FileOperations):
        self.retrieval_agent = RetrievalAgent(rag_system) if rag_system else None
        self.planning_agent = PlanningAgent(rag_system)
        self.validation_agent = ValidationAgent(diff_editor, file_ops)
        self.rag_system = rag_system
    
    def process_request(self, query: str) -> Dict[str, Any]:
        """
        Process a complex request using multiple agents.
        
        Args:
            query: User request
            
        Returns:
            Dict with results from all agents
        """
        results = {
            "query": query,
            "agents": {}
        }
        
        # Step 1: Retrieve relevant context
        if self.retrieval_agent:
            retrieval_task = AgentTask(role=AgentRole.RETRIEVER, query=query)
            retrieval_result = self.retrieval_agent.execute(retrieval_task)
            results["agents"]["retriever"] = retrieval_result
        
        # Step 2: Plan the changes
        planning_task = AgentTask(
            role=AgentRole.PLANNER,
            query=query,
            context=results["agents"].get("retriever", {})
        )
        planning_result = self.planning_agent.execute(planning_task)
        results["agents"]["planner"] = planning_result
        
        # Step 3: Validation (if diff is provided)
        # This would be called after code generation
        
        return results
    
    def validate_and_apply(self, diff_text: str) -> Dict[str, Any]:
        """
        Validate and apply a diff using the validation agent.
        
        Args:
            diff_text: Unified diff to validate and apply
            
        Returns:
            Dict with validation and application results
        """
        # Validate
        validation_task = AgentTask(
            role=AgentRole.VALIDATOR,
            query="validate diff",
            context={"diff_text": diff_text}
        )
        validation_result = self.validation_agent.execute(validation_task)
        
        if validation_result["status"] != "valid":
            return {
                "status": "validation_failed",
                "validation": validation_result
            }
        
        # Apply if valid
        file_diffs = self.diff_editor.parse_diff(diff_text)
        apply_result = self.diff_editor.apply_diffs(file_diffs, dry_run=False)
        
        return {
            "status": "success",
            "validation": validation_result,
            "application": apply_result
        }
