"""Điểm vào (entrypoint) của collector LIVE. Owner: Thành, triển khai ở W2-THANH-01.

Service `collector` (profile `live` trong docker-compose.yml, dùng chung image với replay) chạy
file này. Hiện mới là chỗ giữ chỗ: in thông báo "chưa triển khai" ra stderr rồi thoát với mã 2,
nên bật profile live sẽ thấy lỗi ngay thay vì tưởng đang thu dữ liệu. Ở tuần 2, file này sẽ đọc
SSE từ Wikimedia EventStreams, đóng gói event bằng `ingestion.envelope` rồi gửi vào Kafka raw topic.
"""

import sys

from wikipulse_core.logging import configure_logging


def main() -> None:
    """Cấu hình log, báo collector LIVE chưa triển khai ra stderr rồi thoát với mã 2."""
    configure_logging("collector")
    print("LIVE collector chưa triển khai. Owner: Thành; checkpoint W2-THANH-01.", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
