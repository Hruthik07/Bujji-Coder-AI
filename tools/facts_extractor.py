"""
Facts Extractor
Extracts structured facts from conversations for efficient memory storage
"""
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class Fact:
    """Structured fact from conversation"""
    fact_type: str  # file_created, function_added, decision_made, error_fixed, etc.
    content: str
    metadata: Dict[str, Any]
    timestamp: Optional[str] = None


class FactsExtractor:
    """Extracts structured facts from conversation messages"""
    
    def __init__(self):
        # Patterns for extracting facts
        self.file_pattern = re.compile(r'(?:created|added|modified|wrote)\s+(?:file|files)?\s*:?\s*([^\s,]+\.\w+)', re.IGNORECASE)
        self.function_pattern = re.compile(r'(?:added|created|implemented)\s+(?:function|method)\s+(\w+)', re.IGNORECASE)
        self.class_pattern = re.compile(r'(?:added|created|implemented)\s+class\s+(\w+)', re.IGNORECASE)
        self.error_pattern = re.compile(r'(?:fixed|resolved|solved)\s+(?:error|bug|issue)\s*:?\s*(.+)', re.IGNORECASE)
    
    def extract_facts(self, messages: List[Dict[str, str]]) -> List[Fact]:
        """Extract facts from conversation messages"""
        facts = []
        
        for msg in messages:
            content = msg.get("content", "")
            role = msg.get("role", "")
            
            # Only extract from assistant messages (they contain actions)
            if role == "assistant":
                facts.extend(self._extract_from_message(content))
        
        return facts
    
    def _extract_from_message(self, content: str) -> List[Fact]:
        """Extract facts from a single message"""
        facts = []
        
        # Extract file creations
        file_matches = self.file_pattern.findall(content)
        for file_path in file_matches:
            facts.append(Fact(
                fact_type="file_created",
                content=f"File created: {file_path}",
                metadata={"file_path": file_path}
            ))
        
        # Extract function additions
        func_matches = self.function_pattern.findall(content)
        for func_name in func_matches:
            facts.append(Fact(
                fact_type="function_added",
                content=f"Function added: {func_name}",
                metadata={"function_name": func_name}
            ))
        
        # Extract class additions
        class_matches = self.class_pattern.findall(content)
        for class_name in class_matches:
            facts.append(Fact(
                fact_type="class_added",
                content=f"Class added: {class_name}",
                metadata={"class_name": class_name}
            ))
        
        # Extract error fixes
        error_matches = self.error_pattern.findall(content)
        for error_desc in error_matches:
            facts.append(Fact(
                fact_type="error_fixed",
                content=f"Error fixed: {error_desc[:100]}",
                metadata={"error_description": error_desc[:200]}
            ))
        
        # Extract decisions (heuristic: look for "decided", "chose", etc.)
        if re.search(r'(?:decided|chose|selected|using)\s+', content, re.IGNORECASE):
            decision_match = re.search(r'(?:decided|chose|selected|using)\s+(.+)', content, re.IGNORECASE)
            if decision_match:
                decision = decision_match.group(1)[:200]
                facts.append(Fact(
                    fact_type="decision_made",
                    content=f"Decision: {decision}",
                    metadata={"decision": decision}
                ))
        
        return facts
    
    def format_facts(self, facts: List[Fact]) -> str:
        """Format facts for context injection"""
        if not facts:
            return ""
        
        formatted = ["[Key Facts from Conversation]:"]
        for fact in facts:
            formatted.append(f"- {fact.content}")
        
        return "\n".join(formatted)
    
    def update_facts(self, existing_facts: List[Fact], new_messages: List[Dict[str, str]]) -> List[Fact]:
        """Update facts with new messages"""
        new_facts = self.extract_facts(new_messages)
        
        # Merge, avoiding duplicates
        all_facts = existing_facts.copy()
        existing_content = {fact.content for fact in existing_facts}
        
        for fact in new_facts:
            if fact.content not in existing_content:
                all_facts.append(fact)
                existing_content.add(fact.content)
        
        return all_facts






