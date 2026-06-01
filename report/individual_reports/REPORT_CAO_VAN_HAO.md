# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Cao Văn Hào
- **Student ID**: 2A202600874
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Tôi đảm nhiệm vai trò thiết kế vòng lặp ReAct logic chính, bộ phân tích cú pháp (Parser) hành động và cơ chế bảo vệ chống lỗi vòng lặp của Agent.

- **Modules Implemented**:
  *   `src/agent/agent.py` ([agent.py](file:///c:/Vinuni/D3/Day-3-Lab-Chatbot-vs-react-agent/src/agent/agent.py)): Hiện thực hóa lớp `ReActAgent` và chu trình lặp `Thought ➔ Action ➔ Observation`.
  *   *Bộ phân tích hành động bằng Regex* (`_parse_action`): Viết biểu thức chính quy để trích xuất tên công cụ và toàn bộ danh sách đối số truyền vào dạng `key="value"`.
  *   *Cơ chế Nudge* (Nudge Mechanism): Tự động chèn thông báo nhắc nhở vào context của LLM nếu nó không tạo ra hành động hoặc câu trả lời cuối cùng để tránh bị treo vòng lặp.
  *   *Bộ lọc Off-topic* (`_is_off_topic`): Triển khai lớp bảo vệ ban đầu dựa trên từ khóa tiếng Việt liên quan đến Bất động sản để nhanh chóng từ chối các yêu cầu ngoài phạm vi mà không tốn phí API.

- **Code Highlights**:
  *   *Regex Action Parser mạnh mẽ*:
      ```python
      def _parse_action(self, text: str) -> Optional[Dict[str, Any]]:
          action_match = re.search(r'Action:\s*(\w+)\(([^)]*)\)', text, re.IGNORECASE)
          if not action_match:
              return None
          tool_name = action_match.group(1)
          args_str = action_match.group(2).strip()
          args = {}
          if args_str:
              param_pattern = re.findall(r'(\w+)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|([^,\s\)]+))', args_str)
              for match in param_pattern:
                  key = match[0]
                  value = match[1] or match[2] or match[3]
                  # Tự động ép kiểu dữ liệu số nguyên hoặc số thực nếu có thể
                  ...
                  args[key] = value
          return {"tool_name": tool_name, "args": args}
      ```

- **Documentation**:
  `ReActAgent` hoạt động dựa trên Prompt hệ thống định hướng cấu trúc chặt chẽ. Khi người dùng nhập câu hỏi, `run()` sẽ kiểm tra qua `_is_off_topic()`. Nếu hợp lệ, nó sẽ bắt đầu chạy vòng lặp tối đa 6 bước. Ở mỗi bước, đầu ra từ LLM được dẫn qua `_parse_final_answer()` và `_parse_action()`. Nếu tìm thấy Action, nó thực thi tool và nạp kết quả Observation vào hội thoại để tiếp tục bước sau.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**: Khi người dùng nhập câu hỏi mơ hồ dạng mở như *"Hãy tư vấn cho tôi"*, Agent bị rơi vào trạng thái đứng im, không đưa ra câu trả lời và liên tục lặp lại các bước suy nghĩ trống cho đến khi đạt giới hạn bước cứng (`max_steps`).
- **Log Source**: Trích xuất log hệ thống:
  ```json
  {"timestamp": "2026-06-01T07:45:10.128Z", "event": "AGENT_NO_ACTION", "data": {"step": 2, "output_preview": "Thought: Tôi cần tư vấn cho khách hàng về Vinhomes Ocean Park..."}}
  ```
- **Diagnosis**: LLM đã viết ra phần suy nghĩ (`Thought`) nhưng do câu hỏi quá mở, nó không biết nên gọi công cụ nào và cũng không thể đưa ra câu trả lời ngay lập tức. Kết quả là nó không sinh ra dòng `Action:` hoặc `Final Answer:`, dẫn đến việc bộ parser trả về `None` và Agent bị kẹt ở bước tiếp theo mà không tiến triển.
- **Solution**: Triển khai cơ chế **Nudge Mechanism**. Nếu ở một bước bất kỳ, LLM không đưa ra `Action` hoặc `Final Answer`, hệ thống điều phối Python sẽ tự động chèn một `Observation` nhắc nhở giả lập:
  ```python
  conversation += "\nObservation: Bạn chưa gọi công cụ nào và cũng chưa đưa ra Final Answer. Hãy sử dụng một trong các công cụ có sẵn hoặc đưa ra Final Answer.\n\n"
  ```
  Thông báo này ép LLM phải quay lại đúng định dạng quy định ở bước kế tiếp, giải quyết triệt để lỗi treo suy nghĩ.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1.  **Reasoning**: Việc bắt buộc LLM viết ra `Thought` giúp kích hoạt khả năng "tự lập luận". Thay vì đoán từ tiếp theo một cách ngẫu nhiên như Chatbot thông thường, LLM phải tự thiết lập kế hoạch hoạt động trước khi đưa ra hành động, giúp đảm bảo các hành động được gọi hoàn toàn có mục đích rõ ràng.
2.  **Reliability**: Trong các trường hợp người dùng nhập câu hỏi cực kỳ mơ hồ, Agent có xu hướng hoạt động kém tin cậy hơn Chatbot. Chatbot có thể tự do đưa ra các câu trả lời mang tính khơi gợi xã giao rất mượt mà, trong khi Agent cố gắng ép mình vào cấu trúc phân tích logic hoặc tìm kiếm công cụ để gọi, dễ gây ra lỗi phân tích cú pháp hoặc đưa ra phản hồi khô khan.
3.  **Observation**: Phản hồi môi trường là yếu tố cốt lõi giúp điều chỉnh hành vi của Agent. Không có Observation, Agent chỉ là một mô hình sinh văn bản tĩnh. Nhờ có kết quả của Tool trả về, Agent có thể nhận ra một căn hộ đã bán để loại trừ, hoặc nhận ra bộ lọc quá hẹp để tự động nới lỏng trong lượt suy nghĩ kế tiếp.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Nâng cấp luồng điều khiển của Agent từ vòng lặp tuyến tính đơn giản sang kiến trúc đồ thị trạng thái sử dụng thư viện **LangGraph**. Điều này cho phép phân nhánh hội thoại phức tạp, quay lui trạng thái (backtracking) khi gặp lỗi và hỗ trợ con người can thiệp (human-in-the-loop) để kiểm duyệt trước khi đưa ra câu trả lời cuối cùng.
- **Safety**: Xây dựng bộ lọc đầu vào (Input Guardrails) nâng cao bằng mô hình nhỏ chạy cục bộ để lọc các nội dung độc hại, spam hoặc tấn công chèn lệnh (prompt injection) trước khi đưa vào Agent chính.
- **Performance**: Chuyển đổi bộ parser dạng Regex hiện tại sang định dạng gọi hàm cấu trúc chuẩn (Structured Outputs/Function Calling) của Gemini API để tăng độ chính xác 100% khi phân tích tham số gọi công cụ.
