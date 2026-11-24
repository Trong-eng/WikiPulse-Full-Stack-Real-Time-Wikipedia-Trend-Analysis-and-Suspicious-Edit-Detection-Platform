# W2-MANH-01 — Hoàn thiện 4 trang Dashboard, tích hợp Trends, Suspicious Edits và Event Detail

Trạng thái: REVIEW · Owner: Mạnh · Reviewer: Nhân · Liên quan: [checkpoints](../checkpoints.md), [contracts.md](../contracts.md), BL-NHAN-02, BL-THANH-37

## Mục tiêu

Kết nối toàn bộ module `dashboard/` với các API thực tế của Tuần 2 (`GET /api/v1/trends`, `GET /api/v1/suspicious-edits`, `GET /api/v1/events/{event_id}`) thay cho trạng thái `501 NOT_IMPLEMENTED` của Tuần 1. Hoàn thiện bộ lọc (filters), trạng thái rỗng (empty state), xử lý lỗi thống nhất và nhãn tạm tính (`provisional: true`). Đồng thời xử lý các góp ý từ PR #4 (lỗi múi giờ UTC trên biểu đồ Overview, chuẩn hóa và đưa ảnh minh chứng Tuần 1 vào báo cáo LaTeX).

## Phạm vi / Không làm

- **Làm:**
  - Cập nhật `dashboard/api_client.py`: thêm phương thức gọi `trends`, `suspicious-edits`, `events/{event_id}`; xử lý chuẩn lỗi `{"detail": {"code", "message", ...}}` (bao gồm `CAPACITY_EXCEEDED`, `DEPENDENCY_UNAVAILABLE`, `EVENT_NOT_FOUND`).
  - Hoàn thiện `dashboard/views/trending.py`: bảng Top-N theo `trend_score`, các chỉ số (`edit_count`, `unique_editors`, `abs_byte_delta`), link mở bài viết Wikipedia thật, bộ lọc wiki/limit và empty state.
  - Hoàn thiện `dashboard/views/suspicious.py`: bảng chỉnh sửa đáng ngờ với `risk_score`, badges `risk_reasons` (`LARGE_DELETION`, `REVERT_PATTERN`, `ANONYMOUS_EDIT`), checkbox ẩn/hiện bot edits, xem chi tiết sự kiện qua `/api/v1/events/{event_id}`, và hiển thị disclaimer bắt buộc.
  - Sửa lỗi hiển thị múi giờ trên `dashboard/views/overview.py`: đảm bảo trục thời gian biểu đồ hiển thị đúng UTC thay vì múi giờ trình duyệt (UTC+7).
  - Cập nhật `dashboard/tests/` và `dashboard/README.md` theo hành vi mới (đóng `BL-NHAN-02`).
  - Chuẩn hóa ảnh minh chứng Tuần 1 (tên không dấu, crop gọn, cửa sổ `00:00` UTC) và chèn vào `docs/bao-cao-ky-thuat/main.tex` tại vị trí `\dukiensua` (đóng `BL-THANH-37`).
- **Không làm:**
  - Không sửa logic tính toán ở Spark (`processing/`) hay API/Cassandra (`api/`, `storage/`) — thuộc phạm vi của Linh và Nhân.
  - Kiểm thử E2E hai chế độ LIVE/REPLAY và đo độ trễ freshness — thuộc phạm vi Tuần 3 (`W3-MANH-01`).

## Các bước

- [x] Đồng bộ `main` mới nhất, tạo nhánh `manh/w2-manh-01-dashboard-features` và lập plan `docs/plans/W2-MANH-01.md`
- [x] Đối chiếu contract Tuần 2 trong `docs/contracts.md` và cập nhật `dashboard/api_client.py`
- [x] Hoàn thiện trang `Trending` (`dashboard/views/trending.py`) với bộ lọc, link Wikipedia, empty/error state
- [x] Hoàn thiện trang `Suspicious Edits` (`dashboard/views/suspicious_edits.py`) với risk badges, filter bot, xem chi tiết event và disclaimer
- [x] Sửa lỗi hiển thị múi giờ UTC trên biểu đồ ở `dashboard/views/overview.py`
- [x] Cập nhật unit tests & Streamlit AppTest trong `dashboard/tests/` và tài liệu `dashboard/README.md`
- [x] Cập nhật mục Dashboard trong `docs/bao-cao-ky-thuat/main.tex` (chờ bổ sung ảnh chụp UI mới khi chạy stack thực tế cho `BL-THANH-37`)
- [x] Chạy kiểm thử (`pytest`, `ruff`), cập nhật Kết quả, `checkpoints.md`, `backlog.md` và chuyển trạng thái sang REVIEW

## Quyết định

- Tuần thủ contract v0.2 đã thống nhất ở PR #3 và ghi tại `docs/contracts.md`:
  - `GET /api/v1/trends`: mặc định lấy cửa sổ mới nhất; khi rỗng (`data: []`, `window_start: null`) hiển thị thông báo empty state rõ ràng.
  - `GET /api/v1/suspicious-edits`: giữ bot edit từ API và dùng toggle/checkbox ở UI để lọc ẩn/hiện; không hiển thị hay truy vấn `user_hash`; luôn hiển thị disclaimer *"Điểm dùng để ưu tiên xem xét, không kết luận phá hoại."*
  - Lỗi `503 CAPACITY_EXCEEDED`: bắt riêng để hướng dẫn người dùng thu hẹp bộ lọc thay vì báo lỗi chung chung.
- Sửa lỗi múi giờ UTC ở biểu đồ `Overview` bằng cách định dạng nhãn thời gian UTC rõ ràng (chuỗi UTC hoặc cấu hình trục Altair `type="utc"`) kèm test để tránh hồi quy.

## Nhật ký

- 2026-11-25 — Tạo nhánh `manh/w2-manh-01-dashboard-features` từ `main` (`a56f1a9`) và khởi tạo plan `docs/plans/W2-MANH-01.md`.
- 2026-11-25 — Cập nhật `dashboard/api_client.py` (trends, suspicious-edits, event detail, format lỗi v0.2, privacy guard), hoàn thiện `views/trending.py`, `views/suspicious_edits.py`, sửa lỗi UTC biểu đồ `views/overview.py`, cập nhật `dashboard/README.md` và `dashboard/tests/`. Pass 43/43 tests dashboard, 231 unit tests toàn repo và `ruff check .`.

## Kết quả

| Kiểm tra | Lệnh | Kết quả |
|---|---|---|
| Lint code | `.venv\Scripts\ruff check .` | All checks passed! |
| Dashboard unit & AppTest | `.venv\Scripts\python -m pytest dashboard/tests -q` | 43 passed |
| Toàn bộ unit tests (non-integration/spark) | `.venv\Scripts\python -m pytest -q -m "not integration and not spark"` | 231 passed, 7 skipped, 67 deselected |
