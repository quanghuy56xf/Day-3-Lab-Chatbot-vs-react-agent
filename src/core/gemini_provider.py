import os
import time
import threading
import google.generativeai as genai
from typing import Dict, Any, Optional, Generator, List
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger


class GeminiKeyPool:
    """
    Round-robin API key pool with automatic failover.
    When a key hits rate limit (429) or quota error, it rotates to the next key.
    The first key in the pool is treated as the paid/priority key.
    """
    
    def __init__(self, keys: List[str]):
        if not keys:
            raise ValueError("At least one API key is required.")
        self.keys = keys
        self.current_index = 0
        self._lock = threading.Lock()
        # Track cooldown timestamps per key (epoch time when key becomes available again)
        self.cooldowns: Dict[int, float] = {}
        logger.log_event("KEY_POOL_INIT", {
            "total_keys": len(keys),
            "paid_key_index": 0
        })
    
    def get_current_key(self) -> str:
        """Get the current active API key."""
        with self._lock:
            return self.keys[self.current_index]
    
    def get_current_index(self) -> int:
        """Get the index of the current key."""
        with self._lock:
            return self.current_index
    
    def rotate(self, failed_index: int, cooldown_seconds: int = 60) -> str:
        """
        Mark the failed key with a cooldown and rotate to the next available key.
        Returns the new active key.
        Raises RuntimeError if ALL keys are on cooldown.
        """
        with self._lock:
            # Set cooldown for the failed key
            self.cooldowns[failed_index] = time.time() + cooldown_seconds
            
            logger.log_event("KEY_ROTATE", {
                "failed_key_index": failed_index,
                "cooldown_seconds": cooldown_seconds
            })
            
            # Find the next available key
            now = time.time()
            for offset in range(1, len(self.keys) + 1):
                candidate = (failed_index + offset) % len(self.keys)
                cooldown_until = self.cooldowns.get(candidate, 0)
                if now >= cooldown_until:
                    self.current_index = candidate
                    logger.log_event("KEY_SWITCHED", {
                        "new_key_index": candidate,
                        "is_paid_key": candidate == 0
                    })
                    return self.keys[candidate]
            
            # All keys on cooldown - find the one that expires soonest
            soonest_index = min(self.cooldowns, key=self.cooldowns.get)
            wait_time = self.cooldowns[soonest_index] - now
            if wait_time > 0:
                logger.log_event("ALL_KEYS_COOLDOWN", {
                    "wait_seconds": round(wait_time, 1),
                    "next_available_index": soonest_index
                })
                time.sleep(wait_time + 0.5)
            
            self.current_index = soonest_index
            # Clear its cooldown
            del self.cooldowns[soonest_index]
            return self.keys[soonest_index]


class GeminiProvider(LLMProvider):
    """
    Gemini LLM Provider with round-robin API key rotation.
    Automatically handles rate limits by switching between multiple keys.
    """
    
    def __init__(self, model_name: str = "gemini-2.5-flash", api_key: Optional[str] = None):
        super().__init__(model_name, api_key)
        
        # Build key pool from environment
        keys_str = os.getenv("GEMINI_API_KEYS", "")
        if keys_str:
            keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        elif api_key:
            keys = [api_key]
        else:
            raise ValueError("No Gemini API keys configured. Set GEMINI_API_KEYS or pass api_key.")
        
        self.key_pool = GeminiKeyPool(keys)
        self._max_retries = len(keys)  # Try each key at most once per request
        
        # Initialize with first key
        self._configure_client(self.key_pool.get_current_key())
    
    def _configure_client(self, api_key: str):
        """Configure the Gemini client with a specific API key."""
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(self.model_name)
    
    def _is_rate_limit_error(self, error: Exception) -> bool:
        """Check if the error is a retryable error (rate limit, quota, timeout, unavailable)."""
        error_str = str(error).lower()
        return any(keyword in error_str for keyword in [
            "429", "resource_exhausted", "rate limit", "quota",
            "too many requests", "resourceexhausted",
            "no longer available", "not supported",
            "504", "deadline exceeded", "deadline_exceeded",
            "503", "service unavailable", "temporarily unavailable"
        ])

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Dict[str, Any]:
        start_time = time.time()
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
        
        last_error = None
        
        for attempt in range(self._max_retries):
            current_index = self.key_pool.get_current_index()
            try:
                # Ensure client is configured with current key
                self._configure_client(self.key_pool.get_current_key())
                
                response = self.model.generate_content(full_prompt)
                
                end_time = time.time()
                latency_ms = int((end_time - start_time) * 1000)
                
                content = response.text
                usage = {
                    "prompt_tokens": response.usage_metadata.prompt_token_count,
                    "completion_tokens": response.usage_metadata.candidates_token_count,
                    "total_tokens": response.usage_metadata.total_token_count
                }
                
                logger.log_event("GEMINI_REQUEST_SUCCESS", {
                    "key_index": current_index,
                    "attempt": attempt + 1,
                    "latency_ms": latency_ms
                })
                
                return {
                    "content": content,
                    "usage": usage,
                    "latency_ms": latency_ms,
                    "provider": "google",
                    "key_index": current_index
                }
                
            except Exception as e:
                last_error = e
                if self._is_rate_limit_error(e):
                    logger.log_event("GEMINI_RATE_LIMIT", {
                        "key_index": current_index,
                        "attempt": attempt + 1,
                        "error": str(e)[:200]
                    })
                    # Rotate to next key with 60s cooldown
                    new_key = self.key_pool.rotate(current_index, cooldown_seconds=60)
                    self._configure_client(new_key)
                    continue
                else:
                    # Non-rate-limit error, raise immediately
                    raise
        
        # All keys exhausted
        raise RuntimeError(
            f"Tất cả {self._max_retries} API key đều bị rate limit. "
            f"Lỗi cuối cùng: {last_error}"
        )

    def stream(self, prompt: str, system_prompt: Optional[str] = None) -> Generator[str, None, None]:
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\nUser: {prompt}"
        
        last_error = None
        
        for attempt in range(self._max_retries):
            current_index = self.key_pool.get_current_index()
            try:
                self._configure_client(self.key_pool.get_current_key())
                response = self.model.generate_content(full_prompt, stream=True)
                for chunk in response:
                    yield chunk.text
                return  # Success, exit the retry loop
                
            except Exception as e:
                last_error = e
                if self._is_rate_limit_error(e):
                    logger.log_event("GEMINI_RATE_LIMIT_STREAM", {
                        "key_index": current_index,
                        "attempt": attempt + 1,
                        "error": str(e)[:200]
                    })
                    new_key = self.key_pool.rotate(current_index, cooldown_seconds=60)
                    self._configure_client(new_key)
                    continue
                else:
                    raise
        
        raise RuntimeError(
            f"Tất cả {self._max_retries} API key đều bị rate limit (stream). "
            f"Lỗi cuối cùng: {last_error}"
        )
