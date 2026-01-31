"""
Hypothesis Generator - Generates multiple theories about bug causes
Similar to Cursor AI's hypothesis generation
"""
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from .llm_provider import get_provider
from .rag_system import RAGSystem
from config import Config


@dataclass
class Hypothesis:
    """Represents a hypothesis about a bug"""
    id: str
    description: str
    confidence: float  # 0.0 to 1.0
    reasoning: str
    suggested_instrumentation: List[str]  # What to log to test this
    suggested_fix: Optional[str] = None


class HypothesisGenerator:
    """
    Generates multiple hypotheses about potential bug causes
    Uses LLM + codebase context to propose theories
    """
    
    def __init__(self, rag_system: Optional[RAGSystem] = None):
        self.rag_system = rag_system
        
        # Use Claude for hypothesis generation (better reasoning)
        try:
            if Config.ANTHROPIC_API_KEY:
                self.llm_provider = get_provider("anthropic", Config.ANTHROPIC_API_KEY)
            else:
                self.llm_provider = get_provider("openai", Config.OPENAI_API_KEY)
        except Exception as e:
            print(f"⚠️  LLM provider initialization failed: {e}")
            self.llm_provider = None
    
    def generate_hypotheses(
        self,
        bug_description: str,
        error_text: Optional[str] = None,
        file_path: Optional[str] = None,
        code_context: Optional[str] = None
    ) -> List[Hypothesis]:
        """
        Generate multiple hypotheses about bug cause
        
        Args:
            bug_description: User's description of the bug
            error_text: Optional error message/stack trace
            file_path: Optional file where bug occurs
            code_context: Optional code context around bug
            
        Returns:
            List of Hypothesis objects
        """
        if not self.llm_provider:
            return []
        
        # Get codebase context if available
        rag_context = ""
        if self.rag_system and self.rag_system.is_indexed:
            try:
                query = f"{bug_description} {error_text or ''}"
                rag_context = self.rag_system.get_context_for_query(query, use_hybrid=True)
            except Exception:
                pass
        
        # Build prompt
        prompt = self._build_hypothesis_prompt(
            bug_description,
            error_text,
            file_path,
            code_context,
            rag_context
        )
        
        try:
            model = Config.ANTHROPIC_MODEL if hasattr(Config, 'ANTHROPIC_MODEL') and Config.ANTHROPIC_API_KEY else Config.OPENAI_MODEL
            
            response = self.llm_provider.chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": """You are a debugging expert. Generate multiple hypotheses about potential bug causes.
                        
For each hypothesis, provide:
1. A clear description of the theory
2. Confidence level (0.0 to 1.0)
3. Reasoning for why this could be the cause
4. What instrumentation/logging would help verify this hypothesis
5. Optional: Suggested fix if this hypothesis is correct

Generate 3-5 different hypotheses, considering:
- Variable state issues
- Logic errors
- Type mismatches
- Edge cases
- Race conditions
- Resource issues
- Integration problems"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                model=model,
                temperature=0.7,  # Higher temperature for creativity
                max_tokens=2000
            )
            
            # Parse hypotheses from response
            hypotheses = self._parse_hypotheses(response.content)
            return hypotheses
        
        except Exception as e:
            print(f"⚠️  Hypothesis generation failed: {e}")
            return []
    
    def _build_hypothesis_prompt(
        self,
        bug_description: str,
        error_text: Optional[str],
        file_path: Optional[str],
        code_context: Optional[str],
        rag_context: str
    ) -> str:
        """Build prompt for hypothesis generation"""
        parts = [f"Bug Description: {bug_description}"]
        
        if error_text:
            parts.append(f"\nError/Stack Trace:\n{error_text}")
        
        if file_path:
            parts.append(f"\nFile: {file_path}")
        
        if code_context:
            parts.append(f"\nCode Context:\n{code_context}")
        
        if rag_context:
            parts.append(f"\nRelevant Codebase Context:\n{rag_context[:1000]}")
        
        parts.append("\n\nGenerate 3-5 hypotheses about what could be causing this bug.")
        parts.append("For each hypothesis, provide description, confidence, reasoning, and suggested instrumentation.")
        
        return "\n".join(parts)
    
    def _parse_hypotheses(self, response_text: str) -> List[Hypothesis]:
        """Parse hypotheses from LLM response"""
        hypotheses = []
        
        # Try to extract structured hypotheses
        # Look for numbered or bulleted hypotheses
        import re
        
        # Pattern for hypothesis blocks
        hypothesis_pattern = r'(?:Hypothesis|Theory|Theory \d+|Hypothesis \d+)[:\-]?\s*(.+?)(?=(?:Hypothesis|Theory|$))'
        
        matches = re.finditer(hypothesis_pattern, response_text, re.IGNORECASE | re.DOTALL)
        
        for i, match in enumerate(matches):
            content = match.group(1).strip()
            
            # Extract description
            description = content.split('\n')[0].strip()
            
            # Extract confidence if mentioned
            confidence_match = re.search(r'confidence[:\s]+([\d.]+)', content, re.IGNORECASE)
            confidence = float(confidence_match.group(1)) if confidence_match else 0.5
            
            # Extract reasoning
            reasoning_match = re.search(r'reasoning[:\s]+(.+?)(?=(?:suggest|instrument|fix|$))', content, re.IGNORECASE | re.DOTALL)
            reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided"
            
            # Extract instrumentation suggestions
            inst_match = re.search(r'(?:instrument|log|debug)[:\s]+(.+?)(?=(?:fix|suggest|$))', content, re.IGNORECASE | re.DOTALL)
            instrumentation = []
            if inst_match:
                inst_text = inst_match.group(1)
                instrumentation = [line.strip() for line in inst_text.split('\n') if line.strip() and not line.strip().startswith('-')]
            
            # Extract fix suggestion
            fix_match = re.search(r'(?:fix|solution)[:\s]+(.+?)(?=(?:hypothesis|theory|$))', content, re.IGNORECASE | re.DOTALL)
            suggested_fix = fix_match.group(1).strip() if fix_match else None
            
            hypotheses.append(Hypothesis(
                id=f"hypothesis_{i+1}",
                description=description,
                confidence=confidence,
                reasoning=reasoning,
                suggested_instrumentation=instrumentation,
                suggested_fix=suggested_fix
            ))
        
        # If no structured format found, create simple hypotheses
        if not hypotheses:
            lines = response_text.split('\n')
            current_hypothesis = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Check if this looks like a hypothesis start
                if re.match(r'^\d+[\.\)]|^[-*]|^(?:hypothesis|theory)', line, re.IGNORECASE):
                    if current_hypothesis:
                        hypotheses.append(current_hypothesis)
                    current_hypothesis = Hypothesis(
                        id=f"hypothesis_{len(hypotheses)+1}",
                        description=line,
                        confidence=0.5,
                        reasoning="",
                        suggested_instrumentation=[],
                        suggested_fix=None
                    )
                elif current_hypothesis:
                    # Add to current hypothesis
                    if not current_hypothesis.reasoning:
                        current_hypothesis.reasoning = line
                    else:
                        current_hypothesis.reasoning += " " + line
            
            if current_hypothesis:
                hypotheses.append(current_hypothesis)
        
        # Ensure we have at least one hypothesis
        if not hypotheses:
            hypotheses.append(Hypothesis(
                id="hypothesis_1",
                description="Need more information to generate hypotheses",
                confidence=0.3,
                reasoning="Insufficient context provided",
                suggested_instrumentation=["Add logging to reproduce the bug"],
                suggested_fix=None
            ))
        
        return hypotheses[:5]  # Limit to 5 hypotheses






