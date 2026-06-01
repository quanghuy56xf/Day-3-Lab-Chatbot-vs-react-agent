import os
import re
from typing import List, Dict, Any, Optional
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker

class ReActAgent:
    """
    A ReAct-style Agent that follows the Thought-Action-Observation loop
    for real estate consultation at Vinhomes Ocean Park.
    """
    
    def __init__(self, llm: LLMProvider, tools: List[Dict[str, Any]], max_steps: int = 5):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.history = []

    def get_system_prompt(self) -> str:
        """
        Build the system prompt that instructs the agent to follow the ReAct format.
        Includes available tools and their descriptions.
        """
        tool_descriptions = "\n".join(
            [f"  - {t['name']}: {t['description']}" for t in self.tools]
        )
        return f"""Bạn là một trợ lý tư vấn bất động sản chuyên nghiệp tại khu đô thị Vinhomes Ocean Park 1 (Gia Lâm, Hà Nội).
Bạn có quyền truy cập các công cụ sau để tra cứu dữ liệu căn hộ thực tế:

{tool_descriptions}

Quy tắc bắt buộc:
1. Luôn suy nghĩ trước khi hành động. Viết ra suy luận của bạn.
2. Sử dụng đúng định dạng sau cho MỖI bước:

Thought: <suy nghĩ và phân tích của bạn>
Action: tool_name(param1="value1", param2="value2")

3. Sau khi nhận được Observation (kết quả), tiếp tục suy nghĩ và hành động nếu cần.
4. Khi đã có đủ thông tin, đưa ra câu trả lời cuối cùng:

Thought: <tổng kết>
Final Answer: <câu trả lời đầy đủ cho người dùng bằng tiếng Việt>

5. KHÔNG BAO GIỜ bịa thông tin. Chỉ trả lời dựa trên dữ liệu từ công cụ.
6. Giá tiền luôn tính bằng VND. 1 tỷ = 1,000,000,000 VND.
7. Nếu người dùng nói giá bằng "tỷ", hãy nhân với 1000000000 để ra VND.
8. Trả lời bằng tiếng Việt, lịch sự và chuyên nghiệp.
9. Mỗi Action CHỈ gọi MỘT tool duy nhất.
10. NẾU câu hỏi KHÔNG liên quan đến bất động sản, mua bán căn hộ, vay ngân hàng, hoặc tiện ích xung quanh Vinhomes Ocean Park, hãy từ chối lịch sự và hướng dẫn người dùng quay lại chủ đề BĐS. KHÔNG gọi bất kỳ tool nào cho câu hỏi lệch chủ đề."""

    def _parse_action(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Parse the Action line from the LLM output.
        Expected format: Action: tool_name(param1="value1", param2=value2)
        Returns dict with 'tool_name' and 'args' keys, or None.
        """
        # Match Action: tool_name(...)
        action_match = re.search(
            r'Action:\s*(\w+)\(([^)]*)\)', text, re.IGNORECASE
        )
        if not action_match:
            return None
        
        tool_name = action_match.group(1)
        args_str = action_match.group(2).strip()
        
        # Parse keyword arguments
        args = {}
        if args_str:
            # Match key=value pairs, handling quoted strings and numbers
            param_pattern = re.findall(
                r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s\)]+))',
                args_str
            )
            for match in param_pattern:
                key = match[0]
                # Pick the first non-empty value from the capture groups
                value = match[1] or match[2] or match[3]
                # Try to convert numeric values
                try:
                    if '.' in value:
                        value = float(value)
                    else:
                        value = int(value)
                except (ValueError, TypeError):
                    pass
                args[key] = value
        
        return {"tool_name": tool_name, "args": args}

    def _parse_final_answer(self, text: str) -> Optional[str]:
        """Extract the Final Answer from LLM output, if present."""
        match = re.search(r'Final Answer:\s*(.*)', text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def _is_off_topic(self, user_input: str) -> bool:
        """
        Guardrail: Check if user query is clearly off-topic.
        Returns True if the query has NO relation to real estate.
        Uses keyword matching to avoid wasting LLM calls.
        """
        text = user_input.lower().strip()
        
        # On-topic keywords (real estate related)
        on_topic_keywords = [
            "căn hộ", "nhà", "phòng ngủ", "studio", "bất động sản", "bds",
            "vinhomes", "ocean park", "the london", "the paris", "the zurich", "the beverly",
            "giá", "tỷ", "triệu", "mua", "bán", "thuê", "trả góp", "vay",
            "diện tích", "hướng", "tầng", "m2", "m²", "phân khu",
            "chủ nhà", "liên hệ", "sđt", "điện thoại",
            "tìm", "so sánh", "thống kê", "trung bình",
            "1pn", "2pn", "3pn", "1 phòng", "2 phòng", "3 phòng",
            "trường", "bệnh viện", "siêu thị", "tiện ích", "xung quanh",
            "lãi suất", "ngân hàng", "trả hàng tháng", "thanh toán",
            "đầu tư", "cho thuê", "pháp lý", "sổ đỏ", "sổ hồng",
            "nội thất", "ban công", "view", "hồ",
            "xin chào", "chào", "hello", "hi", "cảm ơn",
        ]
        
        # Check if any on-topic keyword is present
        for keyword in on_topic_keywords:
            if keyword in text:
                return False
        
        # If the message is very short (< 5 words), give benefit of the doubt
        if len(text.split()) <= 3:
            return False
        
        # If nothing matches, likely off-topic
        logger.log_event("GUARDRAIL_OFF_TOPIC", {
            "input": user_input,
            "reason": "No real estate keywords detected"
        })
        return True

    def run(self, user_input: str) -> str:
        """
        Execute the ReAct loop:
        1. Check guardrails (off-topic filter).
        2. Generate Thought + Action from LLM.
        3. Parse Action and execute Tool.
        4. Append Observation to prompt and repeat until Final Answer.
        """
        # === GUARDRAIL: Off-topic check ===
        if self._is_off_topic(user_input):
            logger.log_event("AGENT_BLOCKED", {
                "input": user_input,
                "reason": "off_topic"
            })
            return (
                "Xin lỗi, tôi là trợ lý tư vấn bất động sản chuyên về **Vinhomes Ocean Park 1**. "
                "Tôi chỉ có thể hỗ trợ các câu hỏi liên quan đến:\n\n"
                "🏠 Tìm kiếm và xem chi tiết căn hộ\n"
                "📊 Phân tích giá và thống kê thị trường\n"
                "🏦 Tính toán vay mua nhà trả góp\n"
                "📍 Tiện ích xung quanh (trường học, bệnh viện, siêu thị)\n\n"
                "Hãy thử hỏi tôi ví dụ: *\"Tìm căn 2PN ở The Zurich giá dưới 5 tỷ\"* 😊"
            )

        logger.log_event("AGENT_START", {
            "input": user_input, 
            "model": self.llm.model_name,
            "max_steps": self.max_steps
        })
        
        # Build the conversation with system prompt + user question
        conversation = f"User: {user_input}\n\n"
        steps = 0
        final_answer = None

        while steps < self.max_steps:
            steps += 1
            logger.log_event("AGENT_STEP", {"step": steps})
            
            # Generate LLM response
            try:
                result = self.llm.generate(
                    conversation, 
                    system_prompt=self.get_system_prompt()
                )
            except Exception as e:
                logger.error(f"LLM generation failed at step {steps}: {e}")
                return f"Xin lỗi, đã có lỗi xảy ra khi xử lý yêu cầu: {e}"
            
            llm_output = result.get("content", "")
            usage = result.get("usage", {})
            latency = result.get("latency_ms", 0)
            provider = result.get("provider", "unknown")
            
            # Track metrics
            tracker.track_request(
                provider=provider,
                model=self.llm.model_name,
                usage=usage,
                latency_ms=latency
            )
            
            logger.log_event("LLM_RESPONSE", {
                "step": steps,
                "output_preview": llm_output[:500],
                "usage": usage,
                "latency_ms": latency
            })
            
            # Append LLM output to conversation
            conversation += llm_output + "\n"
            
            # Check for Final Answer first
            final_answer = self._parse_final_answer(llm_output)
            if final_answer:
                logger.log_event("AGENT_FINAL_ANSWER", {
                    "step": steps, 
                    "answer_preview": final_answer[:200]
                })
                break
            
            # Parse and execute Action
            action = self._parse_action(llm_output)
            if action:
                tool_name = action["tool_name"]
                tool_args = action["args"]
                
                logger.log_event("TOOL_CALL", {
                    "step": steps,
                    "tool": tool_name,
                    "args": str(tool_args)
                })
                
                # Execute the tool
                observation = self._execute_tool(tool_name, tool_args)
                
                logger.log_event("TOOL_RESULT", {
                    "step": steps,
                    "tool": tool_name,
                    "result_preview": observation[:300]
                })
                
                # Feed observation back into the conversation
                conversation += f"\nObservation: {observation}\n\n"
            else:
                # No action and no final answer - the LLM might be confused
                # Nudge it to take action or provide a final answer
                logger.log_event("AGENT_NO_ACTION", {
                    "step": steps,
                    "output_preview": llm_output[:200]
                })
                conversation += (
                    "\nObservation: Bạn chưa gọi công cụ nào và cũng chưa đưa ra Final Answer. "
                    "Hãy sử dụng một trong các công cụ có sẵn hoặc đưa ra Final Answer.\n\n"
                )
        
        if final_answer:
            logger.log_event("AGENT_END", {"steps": steps, "status": "success"})
            return final_answer
        else:
            logger.log_event("AGENT_END", {"steps": steps, "status": "max_steps_reached"})
            # Try to extract any useful content from the last response
            return (
                "Xin lỗi, tôi đã thực hiện quá nhiều bước mà chưa tìm được câu trả lời hoàn chỉnh. "
                "Vui lòng thử lại với câu hỏi cụ thể hơn."
            )

    def _execute_tool(self, tool_name: str, args: Dict[str, Any]) -> str:
        """
        Execute a tool by name with the given arguments.
        Maps tool names to their actual Python functions.
        """
        for tool in self.tools:
            if tool['name'] == tool_name:
                func = tool.get('function')
                if func:
                    try:
                        return func(**args)
                    except TypeError as e:
                        return f"Lỗi tham số khi gọi {tool_name}: {e}. Hãy kiểm tra lại tên và giá trị tham số."
                    except Exception as e:
                        return f"Lỗi khi thực thi {tool_name}: {e}"
                else:
                    return f"Tool {tool_name} không có hàm thực thi."
        
        available = ", ".join([t['name'] for t in self.tools])
        return f"Không tìm thấy công cụ '{tool_name}'. Các công cụ có sẵn: {available}"
