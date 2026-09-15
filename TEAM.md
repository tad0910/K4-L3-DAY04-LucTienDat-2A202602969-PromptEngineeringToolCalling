# TEAM — Day04, K4-L3B

**Làm nhóm.** Mỗi người tự viết và commit phần INDIVIDUAL của mình.

## Thông tin bài nộp

- Tên nhóm: NhomGG 
- Người đại diện / MSSV: Lục Tiến Đạt / 2A202602969
- Tên repo: `K4-DAY04-NhomGG`
- URL repo, nhánh nộp, commit chốt: https://github.com/tad0910/K4-DAY04-NhomGG , nhánh main
- Deadline áp dụng: 23:59 ngày học (Asia/Ho_Chi_Minh)

## Thành viên

| Họ và tên | MSSV | GitHub | Vai trò và công việc | File/commit/PR |
|---|---|---|---|---|
| Trần Tuấn Hoàng | 2A202602832 |  | Prompt Engineering & Phân tích Trace v0-v3 | `starter_v0/artifacts/system_prompt.md`, `version_log.csv` |
| Nguyễn Văn Đại | 2A202602477 |  | Thiết kế UI/UX Web Chat App & Transcript | `starter_v0/ui_app.py`, `starter_v0/transcripts/` |
| Lục Tiến Đạt | 2A202602969 | tad0910 | Phát triển Bonus Tool & Benchmark Evaluation | `starter_v0/tools/diagnose_network/`, `data/eval_group.json` |

## Nhận xét chung

- **Kết quả và bằng chứng:** Đạt độ chính xác tổng thể tăng từ 70% (v0) lên 83.33% (v3) trên bộ 30 test case base, 90% độ chính xác chọn tool, và 90% trên bộ 10 test case của nhóm. Toàn bộ file run evidence JSON được lưu tại `starter_v0/runs/`.
- **Thay đổi hiệu quả nhất:** Thêm quy tắc xử lý thiếu thông tin (`missing_info` ➔ `clarify`) và ranh giới an toàn tạo ticket (`wrong_boundary` ➔ bắt buộc xác nhận `confirmed=True`), kết hợp chuẩn hóa schema `tools.yaml`.
- **Giới hạn còn lại:** Đối với các câu prompt cố tình bypass an toàn kiểu phức tạp (adversarial injection), hệ thống cần thêm một lớp Guardrail kiểm duyệt đầu vào (Input filtering).
- **Cách phân công và tích hợp:** Phân công theo 3 mảng độc lập: Prompt Engineering (Hoàng), Web UI & UX (Đại), và Bonus Tool & Benchmark (Đạt). Tích hợp liên tục qua Git repo chung.

---

## INDIVIDUAL

### Trần Tuấn Hoàng — 2A202602832

- **Phần việc và file/commit/PR:**
  - Tối ưu hóa `system_prompt.md` qua các phiên bản `v0 ➔ v1 ➔ v2 ➔ v3`.
  - Phân tích log lỗi trace để đặt giả thuyết và ghi nhận dữ liệu vào `version_log.csv` và `REPORT.md`.
- **Quyết định, khó khăn và cách xử lý:**
  - *Khó khăn:* Ban đầu model hay tự đoán mò mã thiết bị `LT-204` khi người dùng chỉ nói chung chung "laptop của mình".
  - *Cách xử lý:* Thêm quy tắc tường minh trong System Prompt cấm đoán mò và bắt buộc gọi tool `clarify` với `response_type='text'`.
- **Điều đã học:** Hiểu sâu về cơ chế Function Calling/Tool Calling của LLM, cách thiết kế Prompt có cấu trúc và ranh giới an toàn (Confirmation boundary).
- **AI/công cụ đã dùng và cách kiểm tra:** OpenRouter API (`openai/gpt-4o-mini`), Antigravity IDE, kiểm tra bằng `run_eval.py`.
- **Thời điểm đã tự nộp URL repo chung trên VLearn:** Trước deadline 23:59.

---

### Nguyễn Văn Đại — 2A202602477

- **Phần việc và file/commit/PR:**
  - Xây dựng ứng dụng Web Chat UI hoàn chỉnh tại `starter_v0/ui_app.py`.
  - Thiết kế giao diện Dark Mode cao cấp (Glassmorphism), hiển thị trực quan các khối Tool Call, Input parameters, Tool Results / Execution Error.
  - Tích hợp bộ chọn phiên bản Agent (v0/v1/v2/v3), Quick Prompts và tính năng tải file Transcript JSON một chạm.
- **Quyết định, khó khăn và cách xử lý:**
  - *Khó khăn:* Cần một giải pháp giao diện chạy nhanh, nhẹ, không yêu cầu cài đặt thư viện nặng và dễ dàng demo trực tiếp.
  - *Cách xử lý:* Sử dụng kiến trúc Web Server chuẩn Python kết hợp HTML5/CSS3/JavaScript hiện đại nhúng sẵn, mở port 8080 cục bộ để demo mượt mà.
- **Điều đã học:** Cách thiết kế trải nghiệm người dùng (UX) cho AI Agent có tương tác công cụ (Agentic UX), biểu diễn luồng suy nghĩ và kết quả tool một cách minh bạch cho người dùng cuối.
- **AI/công cụ đã dùng và cách kiểm tra:** Google Chrome DevTools, Antigravity IDE, kiểm thử các luồng chat đơn lượt và đa lượt trên Web UI.
- **Thời điểm đã tự nộp URL repo chung trên VLearn:** Trước deadline 23:59.

---

### Lục Tiến Đạt — 2A202602969

- **Phần việc và file/commit/PR:**
  - Phát triển tính năng mở rộng (Bonus Tool): `diagnose_network` trong `starter_v0/tools/diagnose_network/` và khai báo vào `tools.yaml`.
  - Soạn thảo bộ 10 test case nhóm chất lượng cao trong `starter_v0/data/eval_group.json` (5 single-turn, 5 multi-turn).
  - Thực thi toàn bộ quy trình benchmark tự động cho bộ base, group và adversarial safety suite.
- **Quyết định, khó khăn và cách xử lý:**
  - *Khó khăn:* Đảm bảo tool mới tích hợp liền mạch vào hệ thống tool registry mà không làm ảnh hưởng các tool có sẵn.
  - *Cách xử lý:* Viết hàm xử lý theo chuẩn đầu ra dict, đăng ký vào `TOOL_FUNCTIONS` và kiểm thử độc lập với bộ `eval_group.json` đạt 90% PASS.
- **Điều đã học:** Quy trình xây dựng Custom Tools mở rộng cho AI Agent, cách viết bộ kiểm thử benchmark đánh giá định lượng (Evaluation Metrics) và kiểm thử an toàn (Adversarial Probes).
- **AI/công cụ đã dùng và cách kiểm tra:** Python, OpenRouter, Git/GitHub, `run_eval.py`.
- **Thời điểm đã tự nộp URL repo chung trên VLearn:** Trước deadline 23:59.
