"""
Task Classifier - Routes tasks to appropriate LLM model
DeepSeek Coder for code generation, Claude Sonnet for everything else
"""
import re
from typing import Dict, List, Optional, Any


class TaskClassifier:
    """Classifies user tasks to determine which model to use"""
    
    # Code generation keywords
    CODE_GENERATION_KEYWORDS = [
        "create", "generate", "write", "make", "build", "add", "implement",
        "code", "function", "class", "file", "app", "api", "endpoint",
        "todo", "component", "module", "script", "program"
    ]
    
    # Non-code generation keywords (use Claude)
    COMPLEX_TASK_KEYWORDS = [
        "explain", "why", "how", "analyze", "debug", "fix", "error",
        "refactor", "optimize", "improve", "review", "understand",
        "what", "where", "when", "help", "problem", "issue"
    ]
    
    def __init__(self):
        self.code_generation_patterns = [
            r"create\s+(a|an|the)?\s*\w+",
            r"generate\s+\w+",
            r"write\s+(a|an)?\s*\w+\s+(function|class|file)",
            r"make\s+(a|an)?\s*\w+",
            r"build\s+(a|an)?\s*\w+",
            r"add\s+\w+\s+(function|class|method)",
            r"implement\s+\w+",
        ]
        
        self.complex_patterns = [
            r"explain\s+",
            r"why\s+",
            r"how\s+",
            r"analyze\s+",
            r"debug\s+",
            r"refactor\s+",
            r"what\s+(is|does|are)",
        ]
    
    def classify(self, user_message: str, conversation_history: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Classify task to determine which model to use
        
        Returns:
            dict with 'provider', 'model', 'reason', 'confidence'
        """
        message_lower = user_message.lower()
        
        # Check for explicit code generation intent
        code_gen_score = self._score_code_generation(message_lower)
        complex_score = self._score_complex_task(message_lower)
        
        # Check conversation context for code generation
        if conversation_history:
            recent_context = self._analyze_recent_context(conversation_history[-6:])
            code_gen_score += recent_context.get("code_gen_bias", 0)
            complex_score += recent_context.get("complex_bias", 0)
        
        # Decision logic
        if code_gen_score > complex_score and code_gen_score >= 2:
            return {
                "provider": "deepseek",
                "model": "deepseek-coder",
                "reason": "Code generation task detected",
                "confidence": min(code_gen_score / 5.0, 1.0)
            }
        else:
            return {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
                "reason": "Complex reasoning or non-code task",
                "confidence": min(complex_score / 5.0, 1.0) if complex_score > 0 else 0.5
            }
    
    def _score_code_generation(self, message: str) -> float:
        """Score how likely this is a code generation task"""
        score = 0.0
        
        # Check keywords
        for keyword in self.CODE_GENERATION_KEYWORDS:
            if keyword in message:
                score += 1.0
        
        # Check patterns
        for pattern in self.code_generation_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                score += 1.5
        
        # Check for code-related phrases
        if any(phrase in message for phrase in ["new file", "new function", "new class", "todo app", "rest api"]):
            score += 2.0
        
        return score
    
    def _score_complex_task(self, message: str) -> float:
        """Score how likely this is a complex reasoning task"""
        score = 0.0
        
        # Check keywords
        for keyword in self.COMPLEX_TASK_KEYWORDS:
            if keyword in message:
                score += 1.0
        
        # Check patterns
        for pattern in self.complex_patterns:
            if re.search(pattern, message, re.IGNORECASE):
                score += 1.5
        
        # Check for question words
        if message.strip().startswith(("why", "how", "what", "where", "when")):
            score += 2.0
        
        return score
    
    def _analyze_recent_context(self, recent_messages: List[Dict]) -> Dict[str, float]:
        """Analyze recent conversation for context clues"""
        code_gen_bias = 0.0
        complex_bias = 0.0
        
        for msg in recent_messages:
            content = msg.get("content", "").lower()
            
            # If recent messages mention code generation
            if any(word in content for word in ["created", "generated", "added", "implemented"]):
                code_gen_bias += 0.5
            
            # If recent messages mention explanations or debugging
            if any(word in content for word in ["explained", "debugged", "analyzed", "refactored"]):
                complex_bias += 0.5
        
        return {
            "code_gen_bias": code_gen_bias,
            "complex_bias": complex_bias
        }

