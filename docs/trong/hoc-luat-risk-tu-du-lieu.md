### 1. Dữ liệu của mình thực sự cho thấy gì?

Mình kiểm lại mẫu LIVE trong repo. Có **6 edit trên 5 bài**, gồm 5 edit `enwiki` và 1 edit `viwiki`. Hai trường hợp đáng chú ý nhất là:

| Quan sát thực tế | Điều có thể suy ra |
|---|---|
| Một edit làm bài giảm từ **28.846 xuống 22.728 byte**, mất **21,2%**. | Biết chính xác quy mô thay đổi. Muốn biết 21,2% có bất thường hay không, cần so với lịch sử các bài tương tự. |
| Trên cùng một bài, một edit thêm **20 byte**. Bảy giây sau, người khác sửa tiếp trên đúng phiên bản đó, giảm **103 byte**, với tóm tắt có dấu hiệu hoàn tác. | Luật hiện tại cộng điểm cho **lần sửa thứ hai**. Trong khi đó, nếu muốn học edit nào cần xem xét, **lần sửa thứ nhất** cũng đáng được mở diff. Chỉ hai con số byte chưa đủ để kết luận edit nào gây hại. |

Mẫu này được chọn để kiểm thử. Trong cả sáu edit, mỗi người chỉ xuất hiện một lần, nên chưa thể dùng nó để kết luận “một người sửa ba lần trong năm phút” là dấu hiệu đáng ngờ. [Fixture LIVE](../../tests/fixtures/recentchange_live_sample.jsonl) · [Khảo sát dữ liệu của nhóm](../thanh/ingestion-spike.md)

### 2. Hai luật có thể tự học theo thời gian

| Luật | WikiPulse học gì từ lịch sử? | Người tuần tra sẽ thấy gì? |
|---|---|---|
| **Mức xóa bất thường so với bài tương tự** | Mỗi ngày, tính lại phân bố tỷ lệ xóa từ các edit trước đó, theo từng wiki và nhóm độ dài bài trước khi sửa. Khi một bài còn ít lịch sử, dùng nhóm bài tương tự làm mốc. | *“Edit này xóa 21,2% bài. Mức xóa lớn hơn 99% các edit trong nhóm so sánh.”* Con số 99% ở đây minh họa cách giải thích, chỉ hiển thị khi đã đo được. |
| **Chuỗi sửa làm bài mất nội dung bất thường** | Dùng `revision_old` và `revision_new` nối các lần sửa liên tiếp. Đo phần trăm nội dung mất từ đầu chuỗi, số lần sửa và thời gian diễn ra. So cả chuỗi với những chuỗi trước đó trên cùng wiki. | *“Ba lần sửa liên tiếp làm bài mất tổng cộng 55%, dù từng lần riêng lẻ chỉ xóa một phần nhỏ.”* Sửa nhanh chỉ đáng chú ý khi đi kèm tác động cụ thể. |

**Hai luật này làm được bằng dữ liệu Silver.** Chúng học được *độ hiếm* mà chưa cần người gán nhãn. Gỡ nguồn dẫn, rải URL và thay văn bản giữ nguyên độ dài thì cần thêm nội dung của hai phiên bản. Silver hiện chỉ có metadata và độ dài nên chưa đủ để kiểm chứng các luật đó. [Schema Silver](../contracts.md#silver--linh--sink)

### 3. Machine learning nên học điều gì?

Mình chọn **cây quyết định nông**, vì đầu ra mà nhóm muốn vẫn là **bộ luật đọc được**. Cho cây học từ tỷ lệ xóa, độ dài ban đầu, tỷ lệ mất cộng dồn và độ hiếm của thay đổi. Với nhãn *“edit này cần người tuần tra xử lý”*, cây có thể tìm ra liệu cùng một tỷ lệ xóa có đáng ưu tiên khác nhau giữa bài ngắn và bài dài, hoặc liệu chuỗi xóa liên tiếp có cung cấp thêm thông tin. Khi đó, ngưỡng chia do dữ liệu gợi ra và nhóm có thể kiểm tra từng nhánh.

Phần quyết định chất lượng là **lấy nhãn từ đâu**. Mình sẽ lấy cả edit bị cảnh báo lẫn một mẫu ngẫu nhiên từ edit điểm thấp, để người đọc diff đánh giá. Việc một revision **bị người khác hoàn tác sau đó** có thể dùng làm tín hiệu phụ để tìm ca đáng xem. Nó chỉ được dùng sau thời điểm dự đoán và vẫn cần phân biệt hoàn tác vì sai nội dung với hoàn tác do tranh chấp biên tập. Wikimedia cũng phân biệt hai mục tiêu này trong nghiên cứu của họ. [Nghiên cứu ORES của Wikimedia](https://meta.wikimedia.org/wiki/Research:ORES:_Facilitating_re-mediation_of_Wikipedia%27s_socio-technical_problems)
