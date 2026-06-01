# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Vũ Tuấn Hoàng
- **Student ID**: 2A202600830
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Tôi chịu trách nhiệm thiết kế hạ tầng cốt lõi, quản lý tài nguyên API và tích hợp hệ thống đo lường hiệu năng (Telemetry) cho dự án.

- **Modules Implemented**:
  *   `src/core/gemini_provider.py` ([gemini_provider.py](file:///c:/Vinuni/D3/Day-3-Lab-Chatbot-vs-react-agent/src/core/gemini_provider.py)): Thiết kế lớp `GeminiKeyPool` để lưu trữ và xoay vòng 7 API keys (1 key trả phí + 6 key miễn phí) theo thuật toán Round-robin, hỗ trợ thread-safe bằng `threading.Lock()` và áp dụng cơ chế cooldown 60 giây đối với key bị lỗi hạn mức.
  *   `src/telemetry/metrics.py` ([metrics.py](file:///c:/Vinuni/D3/Day-3-Lab-Chatbot-vs-react-agent/src/telemetry/metrics.py)): Xây dựng lớp `PerformanceTracker` tính toán Token tiêu thụ thực tế (Prompt/Completion) và quy đổi sang chi phí USD tương ứng của mô hình `gemini-2.5-flash`.
  *   `src/telemetry/logger.py` ([logger.py](file:///c:/Vinuni/D3/Day-3-Lab-Chatbot-vs-react-agent/src/telemetry/logger.py)): Thiết lập cấu trúc log JSON tiêu chuẩn để lưu trữ vết hội thoại và lịch sử hoạt động của Agent.

- **Code Highlights**:
  *   *Cơ chế xoay vòng Key an toàn và thread-safe*:
      ```python
      def rotate(self, failed_index: int, cooldown_seconds: int = 60) -> str:
          with self._lock:
              self.cooldowns[failed_index] = time.time() + cooldown_seconds
              now = time.time()
              for offset in range(1, len(self.keys) + 1):
                  candidate = (failed_index + offset) % len(self.keys)
                  if now >= self.cooldowns.get(candidate, 0):
                      self.current_index = candidate
                      return self.keys[candidate]
              # Nếu tất cả các key đều bị cooldown, tìm key có thời gian chờ ngắn nhất và ngủ
              ...
      ```

- **Documentation**:
  Core LLM Provider giao tiếp trực tiếp với `ReActAgent` thông qua phương thức `generate()`. Khi Agent yêu cầu một lượt sinh văn bản, `GeminiProvider` tự động quản lý kết nối, nếu gặp lỗi 429 (Rate Limit) hoặc 504 (Timeout), nó sẽ tự động kích hoạt xoay vòng key, cấu hình lại client và thử lại mà không làm gián đoạn chu trình ReAct chính.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**: Hệ thống liên tục bị sập ngay khi khởi động và báo lỗi kết nối tới API của Google với mã lỗi 404.
- **Log Source**: Trích xuất từ tệp log hệ thống:
  ```json
  {"timestamp": "2026-06-01T07:22:15.102Z", "event": "GEMINI_RATE_LIMIT", "data": {"key_index": 0, "attempt": 1, "error": "google.api_core.exceptions.NotFound: 404 This model models/gemini-2.0-flash is no longer available..."}}
  ```
- **Diagnosis**: Google đã tiến hành ngừng hỗ trợ (deprecate) dòng mô hình thử nghiệm `gemini-2.0-flash` đối với các tài khoản tạo mới và chuyển hoàn toàn sang `gemini-2.5-flash`. Mã nguồn cấu hình mặc định ban đầu vẫn trỏ tới mô hình cũ dẫn tới việc lỗi gọi API hàng loạt.
- **Solution**: 
  1. Thay đổi cấu hình mặc định trong tệp `.env` thành `DEFAULT_MODEL=gemini-2.5-flash`.
  2. Bổ sung cụm từ `"no longer available"` và `"not supported"` vào danh sách nhận diện lỗi cần kích hoạt xoay vòng key (`_is_rate_limit_error`) trong `GeminiProvider` để đảm bảo hệ thống tự phục hồi nếu một mô hình bất kỳ bị ngắt kết nối đột ngột.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1.  **Reasoning**: Khối `Thought` đóng vai trò là "chuỗi suy nghĩ" (Chain of Thought) giúp phân rã bài toán phức tạp thành các bước nhỏ hơn. So với Chatbot trả lời trực tiếp bằng trực giác dễ sai sót, ReAct Agent suy nghĩ trước: *"Ta cần thông tin A, nên gọi tool X"*, sau đó mới hành động, giúp đảm bảo tính logic và giảm thiểu tối đa hiện tượng ảo giác (hallucination).
2.  **Reliability**: Agent có thể hoạt động tệ hơn Chatbot trong các câu hỏi mang tính giao tiếp thông thường (chit-chat, hỏi thăm xã giao) hoặc kiến thức phổ thông đơn giản. Lúc này, Agent vẫn cố gắng phân tích cấu trúc ReAct hoặc kích hoạt bộ lọc off-topic không cần thiết, làm tăng đáng kể thời gian chờ (latency) và tiêu tốn token vô ích trong khi Chatbot có thể phản hồi lập tức.
3.  **Observation**: Kết quả phản hồi từ môi trường (`Observation`) là nguồn thông tin thực tế giúp định hình hành vi tiếp theo của Agent. Nếu kết quả trả về là rỗng, Agent sẽ tự động chuyển hướng tìm kiếm hoặc thu hẹp bộ lọc trong lượt suy nghĩ tiếp theo, thể hiện khả năng thích ứng động mà Chatbot một shot không có được.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Di chuyển cơ chế lưu trữ API keys từ tệp `.env` sang hệ thống quản lý bí mật chuyên dụng (như HashiCorp Vault hoặc AWS Secrets Manager) để tăng tính bảo mật cho môi trường sản xuất.
- **Safety**: Xây dựng một luồng giám sát thời gian thực tích hợp với hệ thống Prometheus & Grafana để theo dõi trực quan lượng Token tiêu thụ, tỉ lệ lỗi 429 của từng key, và độ trễ trung bình của hệ thống.
- **Performance**: Áp dụng cơ chế lưu bộ nhớ đệm (Caching) cho các kết quả gọi công cụ giống nhau trong một khoảng thời gian ngắn để giảm thiểu số lượt gọi API trùng lặp, tối ưu hóa độ trễ phản hồi cho người dùng.
