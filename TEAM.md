# TEAM — Day04, K4-L3B

**Làm nhóm.** Mỗi người tự viết và commit phần INDIVIDUAL của mình.

## Thông tin bài nộp

- Tên nhóm: NhomGG 
- Người đại diện / MSSV: Lục Tiến Đạt / 2A202602969
- Tên repo: `K4-DAY04-NhomGG`
- URL repo, nhánh nộp, commit chốt: https://github.com/tad0910/K4-L3-DAY04-LucTienDat-2A202602969-PromptEngineeringToolCalling , nhánh main, commit `a51f3c0`
- Deadline áp dụng: 23:59 ngày học (Asia/Ho_Chi_Minh)

## Thành viên và Phân chia Vai trò (Theo D04 Guide)

| Họ và tên | MSSV | GitHub | Vai trò (D04 Guide) | Công việc chính | Sản phẩm bàn giao / File |
|---|---|---|---|---|---|
| **Trần Tuấn Hoàng** | 2A202602832 |  | **Vai A — Hướng dẫn và công cụ** | Đọc lỗi; sửa `system_prompt.md`, chuẩn hóa mô tả `tools.yaml`, xử lý missing info & confirmation boundaries | `starter_v0/artifacts/system_prompt.md`, `tools.yaml` |
| **Nguyễn Văn Đại** | 2A202602477 |  | **Vai C — Giao diện và hội thoại** | Xây dựng Web Chat UI; hiển thị tool calls, inputs, results/errors, quản lý phiên chat & lưu transcript | `starter_v0/app.py`, `starter_v0/transcripts/` |
| **Lục Tiến Đạt** | 2A202602969 | tad0910 | **Vai B + D — Dữ liệu & kiểm tra + Tích hợp & báo cáo** | Soạn 10 test case nhóm; phát triển bonus tool `diagnose_network`; chạy benchmark v0–v3, group, adversarial; tích hợp repo & viết report | `starter_v0/tools/diagnose_network/`, `data/eval_group.json`, `REPORT.md`, `version_log.csv` |

---

## Nhận xét chung

- **Kết quả và bằng chứng:** Đạt độ chính xác tổng thể tăng từ 70% (v0) lên **100.0% (30/30 PASS)** ở v3 trên bộ 30 test case base (`case_accuracy: 1.0`, `tool_routing_accuracy: 1.0`, `argument_accuracy: 1.0`, `multiturn_accuracy: 1.0`), và đạt 90% trên bộ 10 test case của nhóm (`eval_group.json`). Toàn bộ file run evidence JSON được lưu tại `starter_v0/runs/`.
- **Thay đổi hiệu quả nhất:** Thêm quy tắc xử lý thiếu thông tin (`missing_info` ➔ `clarify`) và ranh giới an toàn tạo ticket (`wrong_boundary` ➔ bắt buộc xác nhận `confirmed=True`), kết hợp chuẩn hóa schema `tools.yaml`.
- **Giới hạn còn lại:** Đối với các câu prompt cố tình bypass an toàn kiểu phức tạp (adversarial injection), hệ thống cần thêm một lớp Guardrail kiểm duyệt đầu vào (Input filtering).
- **Cách phân công và tích hợp:** Phân chia rõ ràng theo 4 vai trò A, B, C, D (Nhóm 3 người ghép B+D cho Đạt, A cho Hoàng, C cho Đại). Phối hợp qua Git repo chung và khớp nối bằng chứng tại từng checkpoint.

---

## INDIVIDUAL

### Trần Tuấn Hoàng — 2A202602832 (Vai A — Hướng dẫn và công cụ)

- **Phần việc và file/commit/PR:**
  - Chịu trách nhiệm Vai A: Đọc log lỗi từ các lần chạy eval v0 để phân tích nguyên nhân gốc rễ.
  - Tối ưu hóa `starter_v0/artifacts/system_prompt.md` qua các phiên bản `v0 ➔ v1 ➔ v2 ➔ v3` (bổ sung quy tắc thiếu thông tin, xác nhận tạo ticket an toàn, và triage đa nguồn).
  - Tinh chỉnh mô tả và ràng buộc schema `starter_v0/artifacts/tools.yaml` (bổ sung `required: [question, response_type]` cho tool `clarify`).
- **Quyết định, khó khăn và cách xử lý:**
  - *Khó khăn:* Model ở v0 hay tự đoán mã thiết bị `LT-204` khi người dùng chỉ nói chung chung "laptop của mình".
  - *Cách xử lý:* Thêm quy tắc tường minh trong System Prompt cấm đoán mò và bắt buộc gọi tool `clarify` với `response_type='text'`.
- **Điều đã học:** Hiểu sâu về kỹ thuật Prompt Engineering cho AI Agent có Tool Calling, cách thiết lập ranh giới an toàn (Confirmation boundary) trước các hành động ghi dữ liệu.
- **AI/công cụ đã dùng và cách kiểm tra:** OpenRouter API (`openai/gpt-4o-mini`), Antigravity IDE, kiểm tra chéo cùng Vai B qua `run_eval.py`.
- **Thời điểm đã tự nộp URL repo chung trên VLearn:** Trước deadline 23:59.

---

### Nguyễn Văn Đại — 2A202602477 (Vai C — Giao diện và hội thoại)

- **Phần việc và file/commit/PR:**
  - Chịu trách nhiệm Vai C: Xây dựng ứng dụng Web Chat UI hoàn chỉnh tại `starter_v0/app.py` (hoạt động ở port 8501).
  - Thiết kế giao diện Dark Mode cao cấp (Glassmorphism), hiển thị trực quan và tách biệt các khối Tool Call, Input parameters, Tool Results / Execution Error.
  - Tích hợp bộ chọn phiên bản Agent (v0/v1/v2/v3), gợi ý nhanh (Quick Prompts) và tính năng tải file Transcript JSON một chạm (`/api/transcript`).
  - Thực hiện các phiên chat live đa lượt để kiểm thử và lưu trữ transcript mẫu kèm ảnh chụp màn hình minh chứng `ui_screenshot.png`.
- **Quyết định, khó khăn và cách xử lý:**
  - *Khó khăn:* Cần giao diện trực quan, nhẹ nhàng, hiển thị minh bạch toàn bộ các bước gọi tool nội bộ mà không cần cài đặt thêm dependency nặng.
  - *Cách xử lý:* Xây dựng ứng dụng web độc lập bằng Python HTTP Server kết hợp HTML5/CSS3/JavaScript hiện đại, mở cổng 8501 để demo trực tiếp mượt mà.
- **Điều đã học:** Cách thiết kế trải nghiệm người dùng cho hệ thống AI Agent (Agentic UX), trực quan hóa dữ liệu JSON đầu vào/đầu ra của công cụ một cách thân thiện.
- **AI/công cụ đã dùng và cách kiểm tra:** Google Chrome DevTools, Antigravity IDE, kiểm thử giao diện qua các kịch bản chat thực tế.
- **Thời điểm đã tự nộp URL repo chung trên VLearn:** Trước deadline 23:59.

---

### Lục Tiến Đạt — 2A202602969 (Vai B + D — Dữ liệu & kiểm tra + Tích hợp & báo cáo)

- **Phần việc và file/commit/PR:**
  - Chịu trách nhiệm Vai B: Soạn thảo bộ 10 test case nhóm chất lượng cao trong `starter_v0/data/eval_group.json` (5 single-turn, 5 multi-turn); thực thi toàn bộ quy trình benchmark tự động `v0–v3`, group eval và 12 case an toàn `eval_adversarial.json`.
  - Phát triển tính năng mở rộng (Bonus Tool 10đ): `diagnose_network` trong `starter_v0/tools/diagnose_network/` và khai báo vào `tools.yaml`.
  - Chịu trách nhiệm Vai D: Quản lý và theo dõi repository Git chung, ghép nối bằng chứng đo lường thực tế vào `starter_v0/artifacts/version_log.csv` và hoàn thiện toàn bộ báo cáo `starter_v0/artifacts/REPORT.md`, chuẩn bị kịch bản demo 4 tình huống.
- **Quyết định, khó khăn và cách xử lý:**
  - *Khó khăn:* Khắc phục lỗi Rate Limit API khi chạy bộ benchmark 30 case liên tục và đảm bảo tool mở rộng tích hợp chuẩn xác vào tool registry.
  - *Cách xử lý:* Thêm cơ chế retry backoff cho provider, chuyển sang OpenRouter và viết tool mới theo chuẩn module độc lập, kiểm thử đạt 90% PASS.
- **Điều đã học:** Quy trình đánh giá AI Agent định lượng có kiểm chứng (Benchmark Evaluation), kỹ thuật phát triển Custom Tools và quản trị tích hợp dự án nhóm.
- **AI/công cụ đã dùng và cách kiểm tra:** Python, OpenRouter, Git/GitHub, `run_eval.py`, PowerShell.
- **Thời điểm đã tự nộp URL repo chung trên VLearn:** Trước deadline 23:59.
