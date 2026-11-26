# Kịch bản thuyết trình WikiPulse

## Slide 1

Kính chào thầy và các bạn. Nhóm em xin trình bày WikiPulse, hệ thống theo dõi hoạt động Wikipedia theo thời gian thực. Bài trình bày giới thiệu bài toán, cách hệ thống hoạt động, kết quả kiểm thử và các giới hạn của phiên bản hiện tại.

## Slide 2

Wikipedia thay đổi liên tục khi mọi người sửa bài, tạo trang hoặc thực hiện các thao tác khác. Khi lượng sự kiện lớn, người theo dõi khó nhận ra trang nào đang thu hút hoạt động và chỉnh sửa nào nên được xem trước. Luồng dữ liệu công khai giúp chúng ta quan sát những thay đổi đó. Tuy nhiên, dữ liệu có thể đến muộn, bị lặp khi kết nối gián đoạn hoặc không hợp lệ. Vì vậy, hệ thống cần xử lý liên tục và trình bày kết quả có thể hiểu được.

## Slide 3

WikiPulse trả lời ba nhu cầu chính: theo dõi hoạt động của từng phiên bản Wikipedia, tìm những trang đang được chỉnh sửa nhiều và ưu tiên những chỉnh sửa có dấu hiệu cần xem xét. Hệ thống nhận dữ liệu trực tiếp hoặc phát lại dữ liệu mẫu để kiểm tra với đầu vào đã biết. Phiên bản trong báo cáo được thử nghiệm trên một node. Xác thực, phân quyền, khả năng duy trì hoạt động khi có sự cố và mô hình học máy chưa nằm trong phạm vi này. Điểm ưu tiên không kết luận một chỉnh sửa là phá hoại.

## Slide 4

Sơ đồ kiến trúc này được lấy trực tiếp từ báo cáo. Ở bên trái, hệ thống nhận dữ liệu trực tiếp từ Wikimedia qua collector, tức bộ thu thập, hoặc phát lại dữ liệu mẫu. Cả hai nhánh đưa sự kiện vào Kafka, hàng đợi giữa nguồn và xử lý. Spark là bộ xử lý sự kiện, tạo dữ liệu thô, dữ liệu đã chuẩn hóa và kết quả đã chốt. Parquet phục vụ phân tích, còn Cassandra cung cấp dữ liệu cho API, giao diện cung cấp dữ liệu, để dashboard hiển thị. Kết quả phân tích như xu hướng cần được cấu hình ghi vào Cassandra để hiển thị qua API. Các nhánh lưu trữ có mục đích khác nhau và không tạo thành một giao dịch chung.

## Slide 5

Sơ đồ trong báo cáo minh họa hai sự kiện A và B đi từ Wikimedia đến collector rồi được gửi vào Kafka. Nếu xác nhận của B đến trước, collector chưa chuyển vị trí tiếp tục đọc vượt qua A. Khi A cũng được xác nhận, vị trí mới có thể tiến tới B. Nếu kết nối bị gián đoạn trong cùng tiến trình, collector thử kết nối lại từ vị trí đã xác nhận. Vị trí này chỉ được giữ trong bộ nhớ, nên việc khởi động lại hoặc giới hạn lưu của nguồn có thể dẫn tới thiếu hay lặp sự kiện. Bộ phát lại dùng dữ liệu mẫu để kiểm thử với đầu vào đã biết.

## Slide 6

Hình cho thấy các nhánh xử lý cùng đọc dữ liệu từ Kafka. Bronze thô giữ bản ghi nguồn; nhánh Bronze lỗi ghi các bản ghi không hợp lệ, và hai nhánh này có thể chồng lấp. Nhánh Silver lọc sự kiện ngoài phạm vi, chuẩn hóa và loại bản trùng trong giới hạn trạng thái. Các truy vấn phân tích tính hoạt động, xu hướng và điểm ưu tiên. Hình cũng phân biệt kết quả tạm tính phục vụ từ Cassandra với kết quả đã chốt ở tầng Gold; danh sách ưu tiên và chi tiết sự kiện có đích lưu theo cấu hình, không ghi vào Gold. Đây là lý do không nên cộng số bản ghi của các nhánh như những tập hoàn toàn tách biệt.

## Slide 7

Hệ thống áp dụng ba quy tắc mặc định cho chỉnh sửa. Một chỉnh sửa bị cộng 30 điểm nếu xóa ít nhất 500 byte, 20 điểm nếu có dấu hiệu hoàn tác theo quy tắc tiếng Anh, và 10 điểm nếu người sửa ẩn danh nhưng không phải bot. Các dấu hiệu có thể xuất hiện cùng lúc, do đó tổng mặc định cao nhất là 60 điểm. Ví dụ, một chỉnh sửa khớp cả ba dấu hiệu nhận 60 điểm. Điểm này chỉ giúp sắp xếp thứ tự để con người xem xét thêm bối cảnh; nó không tự kết luận có hành vi phá hoại.

## Slide 8

Sơ đồ triển khai trong báo cáo cho thấy các thành phần chạy trong môi trường Docker Compose. Collector nhận luồng LIVE; bộ phát lại chạy khi cần. Kafka đưa dữ liệu đến Spark, còn Cassandra phục vụ dữ liệu cho API và dashboard. Ở giữa hình, HDFS là lựa chọn lưu trữ phân tán; cấu hình mặc định dùng ổ cục bộ. Dữ liệu phân tích như xu hướng cần được cấu hình ghi vào Cassandra để có thể xem qua API. Về riêng tư, dữ liệu thô có thể chứa định danh. Tầng làm sạch thay định danh trực tiếp bằng mã băm và loại bình luận gốc, nhưng không bảo đảm ẩn danh tuyệt đối vì tên trang vẫn có thể chứa danh tính.

## Slide 9

Dashboard có bốn trang. Overview hiển thị hoạt động theo cửa sổ thời gian; Trending liệt kê những trang đang thu hút chỉnh sửa. Suspicious Edits trình bày các chỉnh sửa cần ưu tiên cùng lý do, còn System Status cho biết trạng thái API và Cassandra. Ảnh bên phải là ảnh chụp thật từ trang Overview với dữ liệu LIVE của enwiki vào ngày 25 tháng 11 năm 2026. Những số phía trên ứng với cửa sổ được chọn từ 16 giờ 09 đến 16 giờ 10 UTC; cột mới nhất trong biểu đồ có thể chưa đủ một phút. Các số này chỉ minh họa một thời điểm và không phải số toàn cầu.

## Slide 10

Nhóm dùng một bộ dữ liệu cố định gồm 11 bản ghi để đối chiếu với kết quả tính độc lập. Sau khi lọc và loại trùng, tầng Silver còn 7 sự kiện. Điều này không có nghĩa bốn bản ghi còn lại đều là lỗi; các nhánh xử lý có thể chồng lấp và có cả những điều kiện lọc khác. Trong lượt kiểm tra riêng trên Windows, 43 kiểm thử dashboard đạt. Hai lượt smoke local và HDFS cũng đạt. Các số này thuộc những phép thử và phạm vi khác nhau; chúng không chứng minh mọi bài thử của toàn bộ project đã được chạy.

## Slide 11

Trong một phiên LIVE được mô tả ở báo cáo, khoảng cách từ mốc collector bắt đầu đến lần kiểm tra cuối là khoảng 15 phút 25 giây. Snapshot bộ đếm gần nhất ghi nhận 35.243 sự kiện nhận và 35.242 sự kiện gửi thành công; bộ đếm không ghi nhận lỗi phân tích hay gửi tại thời điểm đó. Đây là số của toàn luồng collector, khác với ảnh dashboard của riêng enwiki. Chênh lệch một sự kiện tại một thời điểm không đủ để kết luận mất dữ liệu. Các mẫu cũng không loại trừ việc collector khởi động lại giữa các lần kiểm tra.

## Slide 12

WikiPulse kết hợp thu thập, xử lý, lưu trữ và dashboard để hỗ trợ theo dõi hoạt động Wikipedia cũng như các chỉnh sửa cần ưu tiên xem xét. Nhóm đã kiểm thử bằng dữ liệu mẫu và nguồn thật trong những điều kiện cụ thể. Phiên bản thử nghiệm vẫn chạy trên một node, chưa có xác thực hay phân quyền, và vị trí tiếp tục đọc của collector chỉ nằm trong bộ nhớ. Những hướng tiếp theo gồm lưu vị trí đọc bền vững, cải thiện bảo mật và phục hồi, đồng thời đánh giá tải với dữ liệu đại diện hơn. Các cải tiến này cần được kiểm chứng riêng trước khi vận hành. Nhóm em cảm ơn thầy và các bạn đã lắng nghe.
