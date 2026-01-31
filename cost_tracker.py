"""
Cost tracking utility for OpenAI API usage
"""
from typing import Dict, Optional
from config import Config

# Pricing per 1K tokens (as of 2024)
PRICING = {
    "gpt-4": {
        "input": 0.03,   # $0.03 per 1K input tokens
        "output": 0.06   # $0.06 per 1K output tokens
    },
    "gpt-4-turbo": {
        "input": 0.01,
        "output": 0.03
    },
    "gpt-3.5-turbo": {
        "input": 0.0005,  # $0.0005 per 1K input tokens (much cheaper!)
        "output": 0.0015  # $0.0015 per 1K output tokens
    },
    "gpt-3.5-turbo-16k": {
        "input": 0.003,
        "output": 0.004
    },
    "deepseek-coder": {
        "input": 0.00014,  # $0.14 per 1M tokens = $0.00014 per 1K
        "output": 0.00028  # $0.28 per 1M tokens = $0.00028 per 1K
    },
    "deepseek-chat": {
        "input": 0.00014,
        "output": 0.00028
    },
    "claude-3-5-sonnet-20241022": {
        "input": 0.003,   # $3 per 1M tokens = $0.003 per 1K
        "output": 0.015   # $15 per 1M tokens = $0.015 per 1K
    },
    "claude-3-opus": {
        "input": 0.015,
        "output": 0.075
    },
    "claude-3-sonnet": {
        "input": 0.003,
        "output": 0.015
    }
}


class CostTracker:
    """Track API usage and costs"""
    
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0
        self.model = Config.OPENAI_MODEL
        self.model_usage = {}  # Track usage per model
    
    def record_usage(self, input_tokens: int, output_tokens: int, model: Optional[str] = None):
        """Record token usage from an API call"""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_requests += 1
        
        # Track per-model usage
        model_name = model or self.model
        if model_name not in self.model_usage:
            self.model_usage[model_name] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "requests": 0
            }
        self.model_usage[model_name]["input_tokens"] += input_tokens
        self.model_usage[model_name]["output_tokens"] += output_tokens
        self.model_usage[model_name]["requests"] += 1
        
        # Update current model if different
        if model and model != self.model:
            self.model = model
    
    def get_cost(self, model: Optional[str] = None) -> float:
        """Calculate total cost in USD"""
        model_name = model or self.model
        
        if model_name and model_name in PRICING:
            pricing = PRICING[model_name]
            if model_name in self.model_usage:
                usage = self.model_usage[model_name]
                input_cost = (usage["input_tokens"] / 1000) * pricing["input"]
                output_cost = (usage["output_tokens"] / 1000) * pricing["output"]
                return input_cost + output_cost
        
        # Fallback: calculate for all models
        total_cost = 0.0
        for model_name, usage in self.model_usage.items():
            if model_name in PRICING:
                pricing = PRICING[model_name]
                input_cost = (usage["input_tokens"] / 1000) * pricing["input"]
                output_cost = (usage["output_tokens"] / 1000) * pricing["output"]
                total_cost += input_cost + output_cost
        
        return total_cost
    
    def get_stats(self) -> Dict:
        """Get usage statistics"""
        return {
            "model": self.model,
            "total_requests": self.total_requests,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "estimated_cost_usd": round(self.get_cost(), 4),
            "cost_per_request": round(self.get_cost() / max(self.total_requests, 1), 4)
        }
    
    def print_stats(self):
        """Print usage statistics"""
        stats = self.get_stats()
        print("\n" + "="*50)
        print("API Usage Statistics")
        print("="*50)
        print(f"Model: {stats['model']}")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Input Tokens: {stats['total_input_tokens']:,}")
        print(f"Output Tokens: {stats['total_output_tokens']:,}")
        print(f"Total Tokens: {stats['total_tokens']:,}")
        print(f"Estimated Cost: ${stats['estimated_cost_usd']:.4f}")
        if stats['total_requests'] > 0:
            print(f"Avg Cost per Request: ${stats['cost_per_request']:.4f}")
        print("="*50 + "\n")
    
    @staticmethod
    def compare_models():
        """Compare costs between different models"""
        print("\n" + "="*60)
        print("Model Cost Comparison (per 1K tokens)")
        print("="*60)
        print(f"{'Model':<20} {'Input ($)':<15} {'Output ($)':<15}")
        print("-"*60)
        for model, pricing in PRICING.items():
            print(f"{model:<20} ${pricing['input']:<14.4f} ${pricing['output']:<14.4f}")
        print("="*60)
        print("\n💡 Tip: GPT-3.5-turbo is ~60x cheaper than GPT-4!")
        print("   It's still very effective for most coding tasks.\n")

