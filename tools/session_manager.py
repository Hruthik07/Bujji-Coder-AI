"""
Session Manager
Manages conversation sessions and cross-session memory
"""
import uuid
from typing import Optional, Dict, Any
from pathlib import Path
from tools.memory_db import MemoryDB


class SessionManager:
    """Manages conversation sessions"""
    
    def __init__(self, workspace_path: str = ".", db_path: Optional[str] = None):
        self.workspace_path = Path(workspace_path).resolve()
        if db_path:
            self.memory_db = MemoryDB(db_path)
        else:
            self.memory_db = MemoryDB(str(self.workspace_path / ".memory.db"))
    
    def create_session(self, workspace_path: Optional[str] = None) -> str:
        """Create a new session and return session ID"""
        session_id = str(uuid.uuid4())
        return session_id
    
    def load_session_context(self, session_id: str) -> Dict[str, Any]:
        """Load session context from database"""
        summary = self.memory_db.get_conversation_summary(session_id)
        facts = self.memory_db.get_relevant_facts(session_id)
        file_changes = self.memory_db.get_file_changes(session_id)
        
        return {
            "session_id": session_id,
            "summary": summary,
            "facts": facts,
            "file_changes": file_changes
        }
    
    def save_session_summary(self, session_id: str, summary: str):
        """Save session summary"""
        self.memory_db.save_conversation_summary(session_id, summary)
    
    def get_session_facts(self, session_id: str, query: Optional[str] = None) -> list:
        """Get relevant facts for session"""
        return self.memory_db.get_relevant_facts(session_id, query)






