import time
from typing import Dict, Any, List
from src.telemetry.logger import logger

class PerformanceTracker:
    """
    Tracking industry-standard metrics for LLMs.
    """
    def __init__(self):
        self.session_metrics = []

    def track_request(self, provider: str, model: str, usage: Dict[str, int], latency_ms: int):
        """
        Logs a single request metric to our telemetry.
        """
        metric = {
            "provider": provider,
            "model": model,
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
            "latency_ms": latency_ms,
            "cost_estimate": self._calculate_cost(model, usage) # Mock cost calculation
        }
        self.session_metrics.append(metric)
        logger.log_event("LLM_METRIC", metric)

    def _calculate_cost(self, model: str, usage: Dict[str, int]) -> float:
        """
        Calculate estimated cost based on model pricing.
        Gemini 3.5 Flash pricing (per 1M tokens):
          - Input: $0.15
          - Output: $0.60
        """
        prompt_tokens = usage.get("prompt_tokens", 0)
        completion_tokens = usage.get("completion_tokens", 0)
        
        if "gemini" in model.lower():
            input_cost = (prompt_tokens / 1_000_000) * 0.15
            output_cost = (completion_tokens / 1_000_000) * 0.60
            return round(input_cost + output_cost, 6)
        elif "gpt" in model.lower():
            # GPT-4o pricing estimate
            input_cost = (prompt_tokens / 1_000_000) * 5.0
            output_cost = (completion_tokens / 1_000_000) * 15.0
            return round(input_cost + output_cost, 6)
        
        return (usage.get("total_tokens", 0) / 1000) * 0.01

# Global tracker instance
tracker = PerformanceTracker()
