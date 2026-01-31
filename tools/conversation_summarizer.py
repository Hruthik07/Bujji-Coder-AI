"""
Conversation Summarizer
Summarizes old conversation messages to preserve context while saving tokens
"""
from typing import List, Dict, Optional
from tools.llm_provider import LLMProvider, get_provider
from config import Config


class ConversationSummarizer:
    """Summarizes conversation history to save tokens"""
    
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        # Use Claude for summarization (better at preserving important info)
        # Fallback gracefully if Anthropic is not available
        self.provider = llm_provider
        if not self.provider:
            try:
                if Config.ANTHROPIC_API_KEY:
                    self.provider = get_provider("anthropic", Config.ANTHROPIC_API_KEY)
                    self.summary_model = "claude-3-5-sonnet-20241022"
                else:
                    self.provider = None
                    self.summary_model = None
            except (ImportError, Exception) as e:
                # #region agent log
                import json as json_lib; log_file = open(r"c:\Users\gdhru\Bujji_Coder_AI\.cursor\debug.log", "a", encoding="utf-8"); log_file.write(json_lib.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"conversation_summarizer.py:28","message":"Anthropic provider initialization failed, falling back","data":{"error_type":type(e).__name__,"error_message":str(e)},"timestamp":int(__import__("time").time()*1000)})+"\n"); log_file.close()
                # #endregion
                # Fallback to OpenAI if available
                try:
                    if Config.OPENAI_API_KEY:
                        self.provider = get_provider("openai", Config.OPENAI_API_KEY)
                        self.summary_model = Config.OPENAI_MODEL
                    else:
                        self.provider = None
                        self.summary_model = None
                except Exception as e2:
                    # #region agent log
                    import json as json_lib; log_file = open(r"c:\Users\gdhru\Bujji_Coder_AI\.cursor\debug.log", "a", encoding="utf-8"); log_file.write(json_lib.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"conversation_summarizer.py:40","message":"All LLM providers failed to initialize","data":{"error_type":type(e2).__name__,"error_message":str(e2)},"timestamp":int(__import__("time").time()*1000)})+"\n"); log_file.close()
                    # #endregion
                    self.provider = None
                    self.summary_model = None
        
        if not self.provider:
            self.summary_model = None
    
    def summarize_messages(
        self,
        messages: List[Dict[str, str]],
        max_summary_tokens: int = 500,
        preserve_recent: int = 5
    ) -> Dict[str, any]:
        """
        Summarize old messages, keeping recent ones verbatim
        
        Args:
            messages: Full message list
            max_summary_tokens: Maximum tokens for summary
            preserve_recent: Number of recent messages to keep verbatim
            
        Returns:
            dict with 'summary_message' and 'recent_messages'
        """
        # #region agent log
        import json as json_lib; log_file = open(r"c:\Users\gdhru\Bujji_Coder_AI\.cursor\debug.log", "a", encoding="utf-8"); log_file.write(json_lib.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"conversation_summarizer.py:64","message":"summarize_messages called","data":{"has_provider":self.provider is not None,"message_count":len(messages)},"timestamp":int(__import__("time").time()*1000)})+"\n"); log_file.close()
        # #endregion
        
        if not self.provider:
            # #region agent log
            import json as json_lib; log_file = open(r"c:\Users\gdhru\Bujji_Coder_AI\.cursor\debug.log", "a", encoding="utf-8"); log_file.write(json_lib.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"conversation_summarizer.py:68","message":"No provider available, returning messages as-is","data":{},"timestamp":int(__import__("time").time()*1000)})+"\n"); log_file.close()
            # #endregion
            return {
                "summary_message": None,
                "recent_messages": messages,
                "original_count": len(messages),
                "summary_count": 0
            }
        
        if len(messages) <= preserve_recent:
            return {
                "summary_message": None,
                "recent_messages": messages,
                "original_count": len(messages),
                "summary_count": 0
            }
        
        # Split into old and recent
        old_messages = messages[:-preserve_recent]
        recent_messages = messages[-preserve_recent:]
        
        # Create summary prompt
        summary_prompt = self._create_summary_prompt(old_messages, max_summary_tokens)
        
        try:
            # Generate summary using Claude
            summary_response = self.provider.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a conversation summarizer. Create concise summaries that preserve key information: files created, functions added, decisions made, errors fixed, and important context."
                    },
                    {
                        "role": "user",
                        "content": summary_prompt
                    }
                ],
                model=self.summary_model,
                temperature=0.3,  # Lower temperature for more consistent summaries
                max_tokens=max_summary_tokens
            )
            
            summary_text = summary_response.content
            
            # Create summary message
            summary_message = {
                "role": "system",
                "content": f"[Previous conversation summary]: {summary_text}"
            }
            
            return {
                "summary_message": summary_message,
                "recent_messages": recent_messages,
                "original_count": len(old_messages),
                "summary_count": 1,
                "tokens_saved": len(old_messages) - 1  # Approximate
            }
        
        except Exception as e:
            # If summarization fails, just keep recent messages
            print(f"⚠️  Summarization failed: {e}")
            return {
                "summary_message": None,
                "recent_messages": recent_messages,
                "original_count": len(old_messages),
                "summary_count": 0
            }
    
    def _create_summary_prompt(self, messages: List[Dict[str, str]], max_tokens: int) -> str:
        """Create prompt for summarization"""
        # Format messages for summary
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted.append(f"{role.upper()}: {content[:500]}")  # Truncate long messages
        
        messages_text = "\n".join(formatted)
        
        return f"""Summarize this conversation history, preserving:
- Files created or modified
- Functions/classes added
- Important decisions made
- Errors fixed and solutions
- Key context for future reference

Keep the summary under {max_tokens} tokens and focus on actionable information.

Conversation:
{messages_text}

Summary:"""
    
    def merge_summary(
        self,
        existing_summary: Optional[str],
        new_messages: List[Dict[str, str]]
    ) -> str:
        """Merge new messages into existing summary"""
        if not existing_summary:
            # Create new summary
            result = self.summarize_messages(new_messages)
            return result["summary_message"]["content"] if result["summary_message"] else ""
        
        # Merge with existing
        merge_prompt = f"""Update this conversation summary with new information:

Existing Summary:
{existing_summary}

New Messages:
{self._format_messages(new_messages)}

Create an updated summary that combines both, preserving all important information."""

        try:
            response = self.provider.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": "You merge conversation summaries, preserving all important information."
                    },
                    {
                        "role": "user",
                        "content": merge_prompt
                    }
                ],
                model=self.summary_model,
                temperature=0.3,
                max_tokens=500
            )
            return response.content
        except Exception as e:
            print(f"⚠️  Summary merge failed: {e}")
            return existing_summary
    
    def _format_messages(self, messages: List[Dict[str, str]]) -> str:
        """Format messages for display"""
        formatted = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")[:300]  # Truncate
            formatted.append(f"{role.upper()}: {content}")
        return "\n".join(formatted)

