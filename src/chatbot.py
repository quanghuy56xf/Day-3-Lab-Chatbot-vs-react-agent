"""
Chatbot Baseline - Simple LLM chatbot WITHOUT tools.
Used as a comparison baseline against the ReAct Agent.
The chatbot only uses the LLM's internal knowledge, no data lookup.
"""
from typing import Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker
import time


class ChatbotBaseline:
    """
    A simple chatbot that answers questions using only the LLM.
    No tools, no ReAct loop - just prompt in, answer out.
    This serves as a baseline to compare against the ReAct Agent.
    """

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    def get_system_prompt(self) -> str:
        return """Bạn là một trợ lý tư vấn bất động sản tại khu đô thị Vinhomes Ocean Park 1 (Gia Lâm, Hà Nội).
Hãy trả lời câu hỏi của khách hàng dựa trên kiến thức chung của bạn.
Trả lời bằng tiếng Việt, lịch sự và chuyên nghiệp.
Nếu không biết thông tin chính xác, hãy nói rõ rằng bạn không có dữ liệu cụ thể."""

    def run(self, user_input: str) -> str:
        """
        Simple one-shot LLM call - no tools, no loop.
        """
        logger.log_event("CHATBOT_START", {
            "input": user_input,
            "model": self.llm.model_name
        })

        try:
            start = time.time()
            result = self.llm.generate(
                user_input,
                system_prompt=self.get_system_prompt()
            )
            elapsed = int((time.time() - start) * 1000)

            content = result.get("content", "")
            usage = result.get("usage", {})

            tracker.track_request(
                provider=result.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=usage,
                latency_ms=elapsed
            )

            logger.log_event("CHATBOT_RESPONSE", {
                "latency_ms": elapsed,
                "tokens": usage.get("total_tokens", 0),
                "answer_preview": content[:200]
            })

            return content

        except Exception as e:
            logger.error(f"Chatbot error: {e}")
            return f"Xin lỗi, đã có lỗi xảy ra: {e}"
