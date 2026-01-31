"""
Memory Database
Persistent storage for conversation facts, summaries, and session data
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime
from tools.facts_extractor import Fact


class MemoryDB:
    """SQLite database for persistent memory storage"""
    
    def __init__(self, db_path: str = ".memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize database schema"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                summary TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(session_id)
            )
        """)
        
        # Facts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                fact_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # File changes table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS file_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                file_path TEXT NOT NULL,
                change_type TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_session ON facts(session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_changes_session ON file_changes(session_id)")
        
        conn.commit()
        conn.close()
    
    def save_conversation_summary(self, session_id: str, summary: str):
        """Save or update conversation summary"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO conversations (session_id, summary, timestamp)
            VALUES (?, ?, ?)
        """, (session_id, summary, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_conversation_summary(self, session_id: str) -> Optional[str]:
        """Get conversation summary for session"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT summary FROM conversations WHERE session_id = ?", (session_id,))
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else None
    
    def save_facts(self, session_id: str, facts: List[Fact]):
        """Save facts to database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        for fact in facts:
            cursor.execute("""
                INSERT INTO facts (session_id, fact_type, content, metadata, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (
                session_id,
                fact.fact_type,
                fact.content,
                json.dumps(fact.metadata),
                datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def get_relevant_facts(self, session_id: str, query: Optional[str] = None) -> List[Dict]:
        """Get relevant facts for session, optionally filtered by query"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        if query:
            # Simple keyword search
            cursor.execute("""
                SELECT fact_type, content, metadata FROM facts
                WHERE session_id = ? AND content LIKE ?
                ORDER BY timestamp DESC
            """, (session_id, f"%{query}%"))
        else:
            cursor.execute("""
                SELECT fact_type, content, metadata FROM facts
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT 50
            """, (session_id,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "fact_type": row[0],
                "content": row[1],
                "metadata": json.loads(row[2]) if row[2] else {}
            })
        
        conn.close()
        return results
    
    def save_file_change(self, session_id: str, file_path: str, change_type: str):
        """Record file change"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO file_changes (session_id, file_path, change_type, timestamp)
            VALUES (?, ?, ?, ?)
        """, (session_id, file_path, change_type, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_file_changes(self, session_id: str) -> List[Dict]:
        """Get file changes for session"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT file_path, change_type, timestamp FROM file_changes
            WHERE session_id = ?
            ORDER BY timestamp DESC
        """, (session_id,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "file_path": row[0],
                "change_type": row[1],
                "timestamp": row[2]
            })
        
        conn.close()
        return results






