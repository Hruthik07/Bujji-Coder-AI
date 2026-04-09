"""
Cost tracking utility for OpenAI API usage
Persists cost history to SQLite so data survives restarts.
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from config import Config

# Pricing per 1K tokens (as of 2024)
PRICING = {
    "gpt-4": {
        "input": 0.03,  # $0.03 per 1K input tokens
        "output": 0.06,  # $0.06 per 1K output tokens
    },
    "gpt-4-turbo": {"input": 0.01, "output": 0.03},
    "gpt-3.5-turbo": {
        "input": 0.0005,  # $0.0005 per 1K input tokens (much cheaper!)
        "output": 0.0015,  # $0.0015 per 1K output tokens
    },
    "gpt-3.5-turbo-16k": {"input": 0.003, "output": 0.004},
    "deepseek-coder": {
        "input": 0.00014,  # $0.14 per 1M tokens = $0.00014 per 1K
        "output": 0.00028,  # $0.28 per 1M tokens = $0.00028 per 1K
    },
    "deepseek-chat": {"input": 0.00014, "output": 0.00028},
    "claude-3-5-sonnet-20241022": {
        "input": 0.003,  # $3 per 1M tokens = $0.003 per 1K
        "output": 0.015,  # $15 per 1M tokens = $0.015 per 1K
    },
    "claude-3-opus": {"input": 0.015, "output": 0.075},
    "claude-3-sonnet": {"input": 0.003, "output": 0.015},
}


class CostTracker:
    """Track API usage and costs, persisted to SQLite across restarts."""

    def __init__(self, db_path: Optional[str] = None):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_requests = 0
        self.model = Config.OPENAI_MODEL
        self.model_usage: Dict[str, Dict] = {}

        # SQLite persistence
        self._db_path = Path(db_path or Config.COST_DB_PATH)
        self._init_db()
        self._restore_totals_from_db()

    def _init_db(self) -> None:
        """Create the cost_history table if it doesn't exist."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cost_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL
                )
                """
            )
            conn.commit()
            conn.close()
        except Exception:
            pass  # Non-fatal: in-memory tracking still works

    def _restore_totals_from_db(self) -> None:
        """Reload running totals from DB on startup so stats persist across restarts."""
        try:
            conn = sqlite3.connect(str(self._db_path))
            rows = conn.execute(
                "SELECT model, SUM(input_tokens), SUM(output_tokens), COUNT(*) "
                "FROM cost_history GROUP BY model"
            ).fetchall()
            conn.close()
            for model, inp, out, req in rows:
                self.model_usage[model] = {
                    "input_tokens": inp or 0,
                    "output_tokens": out or 0,
                    "requests": req or 0,
                }
                self.total_input_tokens += inp or 0
                self.total_output_tokens += out or 0
                self.total_requests += req or 0
        except Exception:
            pass  # Fresh start if DB is missing or corrupt

    def _cost_for(self, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for a given model and token counts."""
        if model_name in PRICING:
            p = PRICING[model_name]
            return (input_tokens / 1000) * p["input"] + (output_tokens / 1000) * p["output"]
        return 0.0

    def record_usage(
        self, input_tokens: int, output_tokens: int, model: Optional[str] = None
    ):
        """Record token usage from an API call and persist to SQLite."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_requests += 1

        # Track per-model usage in memory
        model_name = model or self.model
        if model_name not in self.model_usage:
            self.model_usage[model_name] = {
                "input_tokens": 0,
                "output_tokens": 0,
                "requests": 0,
            }
        self.model_usage[model_name]["input_tokens"] += input_tokens
        self.model_usage[model_name]["output_tokens"] += output_tokens
        self.model_usage[model_name]["requests"] += 1

        if model and model != self.model:
            self.model = model

        # Persist to SQLite (non-fatal)
        try:
            cost = self._cost_for(model_name, input_tokens, output_tokens)
            conn = sqlite3.connect(str(self._db_path))
            conn.execute(
                "INSERT INTO cost_history (timestamp, model, input_tokens, output_tokens, cost_usd) "
                "VALUES (?, ?, ?, ?, ?)",
                (datetime.utcnow().isoformat(), model_name, input_tokens, output_tokens, cost),
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

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
            "cost_per_request": round(self.get_cost() / max(self.total_requests, 1), 4),
        }

    def get_history(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        model: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict]:
        """
        Return historical cost records from SQLite with optional filters.

        Args:
            start_date: ISO date string (e.g. "2024-01-01")
            end_date: ISO date string (e.g. "2024-12-31")
            model: Filter to a specific model name
            limit: Maximum number of records to return (newest first)
        """
        try:
            conn = sqlite3.connect(str(self._db_path))
            conn.row_factory = sqlite3.Row
            query = "SELECT * FROM cost_history WHERE 1=1"
            params: list = []
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date + "T23:59:59")
            if model:
                query += " AND model = ?"
                params.append(model)
            query += " ORDER BY id DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(query, params).fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception:
            return []

    def print_stats(self):
        """Print usage statistics"""
        stats = self.get_stats()
        print("\n" + "=" * 50)
        print("API Usage Statistics")
        print("=" * 50)
        print(f"Model: {stats['model']}")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Input Tokens: {stats['total_input_tokens']:,}")
        print(f"Output Tokens: {stats['total_output_tokens']:,}")
        print(f"Total Tokens: {stats['total_tokens']:,}")
        print(f"Estimated Cost: ${stats['estimated_cost_usd']:.4f}")
        if stats["total_requests"] > 0:
            print(f"Avg Cost per Request: ${stats['cost_per_request']:.4f}")
        print("=" * 50 + "\n")

    @staticmethod
    def compare_models():
        """Compare costs between different models"""
        print("\n" + "=" * 60)
        print("Model Cost Comparison (per 1K tokens)")
        print("=" * 60)
        print(f"{'Model':<20} {'Input ($)':<15} {'Output ($)':<15}")
        print("-" * 60)
        for model, pricing in PRICING.items():
            print(f"{model:<20} ${pricing['input']:<14.4f} ${pricing['output']:<14.4f}")
        print("=" * 60)
        print("\n💡 Tip: GPT-3.5-turbo is ~60x cheaper than GPT-4!")
        print("   It's still very effective for most coding tasks.\n")
