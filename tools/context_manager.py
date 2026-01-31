"""
Context Manager
Intelligent context assembly with token-based management, summarization, and facts
"""
from typing import List, Dict, Optional, Any
from tools.token_counter import TokenCounter
from tools.conversation_summarizer import ConversationSummarizer
from tools.facts_extractor import FactsExtractor, Fact
from tools.memory_db import MemoryDB
from config import Config


class ContextManager:
    """Manages context assembly with intelligent memory management"""
    
    def __init__(
        self,
        max_context_tokens: int = 10000,  # For DeepSeek (16K limit)
        max_context_tokens_claude: int = 150000,  # For Claude (200K limit)
        summarization_threshold: float = 0.75,  # Summarize at 75% of limit
        preserve_recent: int = 8
    ):
        self.token_counter = TokenCounter()
        self.summarizer = ConversationSummarizer()
        self.facts_extractor = FactsExtractor()
        self.memory_db = MemoryDB()
        
        self.max_context_tokens = max_context_tokens
        self.max_context_tokens_claude = max_context_tokens_claude
        self.summarization_threshold = summarization_threshold
        self.preserve_recent = preserve_recent
    
    def assemble_context(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]],
        rag_context: str,
        system_prompt: str,
        model: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assemble optimal context for LLM call
        
        Returns:
            dict with 'messages', 'token_count', 'facts', 'summary_used'
        """
        # Determine max tokens based on model
        max_tokens = self.max_context_tokens_claude if "claude" in model.lower() else self.max_context_tokens
        threshold = int(max_tokens * self.summarization_threshold)
        
        # Load relevant facts from database if session_id provided
        facts = []
        if session_id:
            facts = self.memory_db.get_relevant_facts(session_id, user_message)
        
        # Build initial context
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add RAG context if available
        if rag_context:
            messages.append({
                "role": "system",
                "content": f"<codebase_context>\n{rag_context}\n</codebase_context>"
            })
        
        # Add facts if available
        if facts:
            facts_text = self._format_facts_for_context(facts)
            messages.append({
                "role": "system",
                "content": facts_text
            })
        
        # Process conversation history
        history_messages = self._process_conversation_history(
            conversation_history,
            model,
            threshold,
            session_id
        )
        
        messages.extend(history_messages)
        messages.append({"role": "user", "content": user_message})
        
        # Count tokens
        token_count = self.token_counter.count_messages(messages, model)
        
        # If still over limit, apply aggressive truncation
        if token_count > max_tokens:
            messages = self._truncate_aggressively(messages, max_tokens, model)
            token_count = self.token_counter.count_messages(messages, model)
        
        return {
            "messages": messages,
            "token_count": token_count,
            "facts_count": len(facts),
            "summary_used": len([m for m in messages if "[Previous conversation summary]" in m.get("content", "")]) > 0
        }
    
    def _process_conversation_history(
        self,
        conversation_history: List[Dict[str, str]],
        model: str,
        threshold: int,
        session_id: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """Process conversation history with summarization if needed"""
        if not conversation_history:
            return []
        
        # Count tokens in history
        history_tokens = self.token_counter.count_messages(conversation_history, model)
        
        # If under threshold, return as-is
        if history_tokens < threshold:
            return conversation_history
        
        # Need summarization
        print(f"[INFO] Context size ({history_tokens} tokens) exceeds threshold ({threshold}). Summarizing...")
        
        # Summarize old messages
        summary_result = self.summarizer.summarize_messages(
            conversation_history,
            max_summary_tokens=500,
            preserve_recent=self.preserve_recent
        )
        
        # Build result
        result = []
        
        # Add summary if available
        if summary_result["summary_message"]:
            result.append(summary_result["summary_message"])
        
        # Add recent messages
        result.extend(summary_result["recent_messages"])
        
        # Extract and save facts if session_id provided
        if session_id:
            facts = self.facts_extractor.extract_facts(conversation_history)
            if facts:
                self.memory_db.save_facts(session_id, facts)
        
        return result
    
    def _format_facts_for_context(self, facts: List[Dict]) -> str:
        """Format facts for context injection"""
        if not facts:
            return ""
        
        formatted = ["[Key Facts from Previous Conversations]:"]
        for fact in facts[:10]:  # Limit to top 10 most relevant
            formatted.append(f"- {fact['content']}")
        
        return "\n".join(formatted)
    
    def _truncate_aggressively(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int,
        model: str
    ) -> List[Dict[str, str]]:
        """Aggressively truncate messages to fit within limit"""
        # Keep system messages
        system_messages = [m for m in messages if m.get("role") == "system"]
        other_messages = [m for m in messages if m.get("role") != "system"]
        
        # Keep last user message
        if other_messages:
            last_message = other_messages[-1]
            other_messages = other_messages[:-1]
        else:
            last_message = None
        
        # Calculate system token count
        system_tokens = self.token_counter.count_messages(system_messages, model)
        remaining_tokens = max_tokens - system_tokens - 500  # Leave room for response
        
        # Truncate other messages
        result = system_messages.copy()
        current_tokens = 0
        
        # Add messages from end (most recent first)
        for msg in reversed(other_messages):
            msg_tokens = self.token_counter.count_messages([msg], model)
            if current_tokens + msg_tokens <= remaining_tokens:
                result.insert(len(system_messages), msg)
                current_tokens += msg_tokens
            else:
                break
        
        # Add last message
        if last_message:
            result.append(last_message)
        
        return result
    
    def update_memory(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        conversation_history: List[Dict[str, str]]
    ):
        """Update memory database with new information"""
        # Extract facts from new exchange
        new_facts = self.facts_extractor.extract_facts([
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_response}
        ])
        
        if new_facts:
            self.memory_db.save_facts(session_id, new_facts)
        
        # Update conversation summary periodically
        if len(conversation_history) % 20 == 0:  # Every 20 messages
            summary_result = self.summarizer.summarize_messages(conversation_history)
            if summary_result["summary_message"]:
                summary_text = summary_result["summary_message"]["content"]
                self.memory_db.save_conversation_summary(session_id, summary_text)






