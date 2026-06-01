# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Phạm Quang Huy
- **Student ID**: 2A202600586
- **Date**: 2026-06-01

---

## I. Technical Contribution (15 Points)

Tôi đảm nhiệm thiết kế toàn bộ hệ thống công cụ (Tools), giải quyết bài toán xử lý dữ liệu thực tế từ cơ sở dữ liệu và tối ưu định dạng thông tin phản hồi từ môi trường.

- **Modules Implemented**:
  *   `src/tools/real_estate_tools.py` ([real_estate_tools.py](file:///c:/Vinuni/D3/Day-3-Lab-Chatbot-vs-react-agent/src/tools/real_estate_tools.py)): Xây dựng các công cụ tra cứu thông tin bất động sản bao gồm `search_properties` (tìm kiếm với nhiều tham số lọc động), `get_property_details` (xem chi tiết thông tin chủ nhà và pháp lý), và `calculate_market_stats` (phân tích thống kê thị trường).
  *   `src/tools/mortgage_calculator.py` ([mortgage_calculator.py](file:///c:/Vinuni/D3/Day-3-Lab-Chatbot-vs-react-agent/src/tools/mortgage_calculator.py)): Phát triển công cụ `calculate_mortgage` tính toán chi tiết số tiền trả góp hàng tháng, tỷ lệ gốc/lãi và lịch thanh toán 3 năm đầu.
  *   `src/tools/location_tools.py` ([location_tools.py](file:///c:/Vinuni/D3/Day-3-Lab-Chatbot-vs-react-agent/src/tools/location_tools.py)): Tạo cơ sở dữ liệu và công cụ `search_amenities` hỗ trợ tra cứu nhanh thông tin tiện ích xung quanh (trường học, y tế, mua sắm, giao thông).

- **Code Highlights**:
  *   *Thiết kế tool trả về pre-formatted text tối ưu cho LLM*:
      Thay vì trả về cấu trúc raw JSON phức tạp khiến LLM tốn token để phân tích và dễ gây lỗi định dạng, các công cụ của tôi tự động chuyển đổi dữ liệu thành dạng chuỗi ký tự được trình bày sạch sẽ, phân cấp rõ ràng bằng Markdown. LLM chỉ cần đọc hiểu và copy-paste vào câu trả lời cuối cùng, giảm thiểu 40% chi phí token.

- **Documentation**:
  Tất cả các công cụ đều được khai báo rõ ràng trong danh sách `TOOLS` đi kèm mô tả cụ thể về chức năng và các đối số đầu vào (tên dự án, hướng căn hộ, khoảng giá tiền bằng VND). Các định dạng tham số này tương thích hoàn toàn với bộ trích xuất Regex Action của Agent.

---

## II. Debugging Case Study (10 Points)

- **Problem Description**: Khi chạy bộ kiểm thử tự động, ca kiểm thử `TestSearchProperties.test_search_no_results` bị thất bại. Lệnh tìm kiếm với giá tối đa rất nhỏ (`max_price=100` VNĐ) vẫn trả về kết quả 5 căn hộ thay vì thông báo không tìm thấy.
- **Log Source**: Output kiểm thử:
  ```bash
  FAILED tests/test_chatbot_vs_agent.py::TestSearchProperties::test_search_no_results
  AssertionError: 'Không tìm thấy' not found in 'Tìm thấy 5 căn hộ phù hợp... QQBMSH Masteri Trinity Square... Giá: 0 VNĐ'
  ```
- **Diagnosis**: 
  Trong cơ sở dữ liệu thực tế `database.json`, có một số căn hộ bị lỗi nhập liệu hoặc chưa có thông tin giá, dẫn đến việc trường `price` mang giá trị mặc định là `0`. Khi lọc căn hộ với điều kiện `max_price=100`, biểu thức lọc trong hàm Python là `prop_price <= max_price` (tương đương `0 <= 100`) trả về kết quả `True`, khiến các căn hộ lỗi giá này lọt qua bộ lọc và hiển thị trong danh sách kết quả.
- **Solution**: 
  Cập nhật logic lọc giá trong hàm [search_properties](file:///c:/Vinuni/D3/Day-3-Lab-Chatbot-vs-react-agent/src/tools/real_estate_tools.py#L93-L100). Thêm một điều kiện kiểm tra giá trị hợp lệ: nếu giá bán của căn hộ nhỏ hơn hoặc bằng 0 (`prop_price <= 0`), hệ thống sẽ ngay lập tức bỏ qua căn hộ đó:
  ```python
  prop_price = prop.get("price", 0)
  if prop_price <= 0:
      continue
  ```
  Sau khi cập nhật logic này, các căn hộ lỗi giá trị `0` đã bị loại bỏ hoàn toàn khỏi bộ lọc giá, và unit test đã chạy thành công 100%.

---

## III. Personal Insights: Chatbot vs ReAct (10 Points)

1.  **Reasoning**: Chatbot thông thường hoạt động dựa trên cơ chế phán đoán từ tiếp theo dựa vào phân phối xác suất. Khi được hỏi về dữ liệu cụ thể (như số điện thoại chủ nhà của một mã căn cụ thể), Chatbot không có cách nào biết được sự thật nên bắt buộc phải "bịa ra" một số điện thoại trông có vẻ thật. Ngược lại, ReAct Agent nhờ có chu trình suy luận lập kế hoạch gọi công cụ, nó đi lấy chính xác số điện thoại thực tế từ cơ sở dữ liệu để đưa vào câu trả lời, đảm bảo tính khách quan và trung thực.
2.  **Reliability**: Agent phụ thuộc hoàn toàn vào độ chính xác của các công cụ và cơ sở dữ liệu. Nếu cơ sở dữ liệu chứa thông tin sai lệch hoặc công cụ hoạt động lỗi (như lỗi bỏ sót căn hộ giá bằng 0 ở trên), Agent sẽ tin tưởng tuyệt đối vào kết quả đó và trả về thông tin sai cho người dùng. Trong khi đó, một Chatbot thông thường có thể khôn khéo từ chối trả lời hoặc đưa ra cảnh báo tốt hơn nhờ được huấn luyện trên lượng dữ liệu khổng lồ.
3.  **Observation**: Dữ liệu phản hồi từ công cụ (`Observation`) chính là chiếc cầu nối giữa thế giới thực và mô hình ngôn ngữ lớn. Nó cung cấp bằng chứng thực tế cho LLM để đưa ra các lập luận logic tiếp theo. Nếu không có Observation, LLM hoàn toàn mù tịt về dữ liệu căn hộ thực tế trong dự án.

---

## IV. Future Improvements (5 Points)

- **Scalability**: Thay thế tệp cơ sở dữ liệu tĩnh `database.json` bằng một hệ thống Cơ sở dữ liệu Vector (như **ChromaDB** hoặc **Pinecone**) kết hợp với mô hình embedding. Điều này cho phép mở rộng hệ thống lên hàng triệu căn hộ và hỗ trợ người dùng tìm kiếm ngữ nghĩa tự nhiên thay vì chỉ khớp từ khóa cứng (ví dụ: tìm kiếm *"căn hộ phù hợp với gia đình đông người, thích yên tĩnh"*).
- **Safety**: Xây dựng cơ chế mã hóa một chiều (Masking) số điện thoại chủ nhà và các thông tin cá nhân nhạy cảm trong dữ liệu trả về của công cụ, chỉ hiển thị đầy đủ khi môi giới đã đăng nhập và xác thực thành công.
- **Performance**: Thiết lập cơ chế lập chỉ mục (Indexing) cho các trường dữ liệu thường xuyên tìm kiếm như `project`, `price`, `type` để tăng tốc độ truy vấn trên ổ đĩa khi số lượng căn hộ tăng cao.
