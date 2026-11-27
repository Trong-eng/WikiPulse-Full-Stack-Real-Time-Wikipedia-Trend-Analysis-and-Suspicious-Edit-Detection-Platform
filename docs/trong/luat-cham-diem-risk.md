### A. Xóa hoặc thay đổi nội dung bài

| Luật | Điều kiện đề xuất | Vì sao tính vào risk score? |
|---|---|---|
| **1. Xóa trắng hoặc gần trắng** | Mất **từ 90%** dung lượng bài trong một edit → **65 điểm**. | Gần như toàn bộ nội dung trước đó biến mất. Nếu xóa nhầm hoặc cố ý làm hỏng bài, đây là ca cần kiểm tra sớm. |
| **2. Xóa một phần đáng kể** | Mất **từ 20% đến dưới 50%** → **25 điểm**. Mất **từ 50% đến dưới 90%** → **45 điểm**. | Một edit có thể làm biến mất cả mục hoặc nhiều luận điểm. Phần bài bị mất càng lớn thì tác động tiềm tàng càng cao. |
| **3. Xóa dần qua nhiều lần sửa** | Cùng người sửa, cùng bài, ít nhất **3 edit liên tiếp trong 5 phút**, lần nào cũng làm bài ngắn đi. So với đầu chuỗi, bài mất **từ 50%** → **55 điểm**. | Xét từng edit có thể bỏ sót tác động cộng dồn. Ví dụ, bài từ 100% xuống 80%, rồi 65%, rồi 45% là đã mất **55%** so với ban đầu. |
| **4. Thay gần hết văn bản** | **Từ 80% phần văn xuôi cũ** bị thay, trong khi dung lượng mới vẫn bằng **70–130%** dung lượng cũ → **40 điểm**. Bỏ qua đoạn chỉ đổi vị trí. | Người sửa có thể thay toàn bộ thông điệp mà độ dài bài hầu như giữ nguyên. Mức điểm vừa phải vì viết lại bài cũng có thể là biên tập hợp lệ. |

### B. Gỡ nguồn dẫn

| Luật | Điều kiện đề xuất | Vì sao tính vào risk score? |
|---|---|---|
| **5. Gỡ phần lớn chú thích nguồn** | Mất **từ 75%** số chú thích nguồn có trước edit → **50 điểm**. Chuyển chú thích sang vị trí khác vẫn tính là còn. | Bài có thể giữ nguyên các khẳng định nhưng mất căn cứ để người đọc kiểm chứng. Tác động này dễ bị bỏ sót nếu chỉ nhìn độ dài. |

Với luật 5, nên hiện **“mất 1/1 nguồn”** hoặc **“mất 12/12 nguồn”**. Cả hai đều là 100% và cùng kích hoạt luật, nhưng người tuần tra cần thấy sự khác nhau về quy mô. Nếu bài ban đầu có 0 nguồn thì bỏ qua luật này.

### C. Chèn liên kết hoặc văn bản lặp

| Luật | Điều kiện đề xuất | Vì sao tính vào risk score? |
|---|---|---|
| **6. Chèn cụm liên kết cùng tên miền** | Một edit thêm **ít nhất 2 URL khác nhau** cùng tên miền ngoài Wikimedia vào thân bài, ngoài chú thích → **25 điểm**. | Có thể là quảng bá một website. Điểm thấp vì hai liên kết cùng nguồn đôi khi vẫn hữu ích cho bài. |
| **7. Rải cùng một liên kết qua nhiều bài** | Cùng người sửa chèn **cùng một URL** vào ít nhất **3 bài trên cùng wiki trong 10 phút** → **65 điểm** từ bài thứ ba. | Việc cùng một đích liên kết xuất hiện nhanh trên nhiều bài là dấu hiệu quảng bá mạnh hơn việc chèn link vào một bài đơn lẻ. |
| **8. Chèn lặp một đoạn văn** | Một đoạn dài ít nhất **20 ký tự** xuất hiện **từ 4 lần** và chiếm **từ 60%** phần văn xuôi vừa thêm → **45 điểm**. Bỏ qua bảng, mẫu, danh sách và trích dẫn. | Nội dung lặp chiếm phần lớn thay đổi có thể làm bài khó đọc, dù edit chỉ thêm chữ và không xóa gì. |

**Cách gộp điểm:** Mỗi nhóm lấy điểm luật cao nhất. Điểm cuối là `min(100, max(A, B) + C)`. Xóa trắng bài đồng thời làm mất hết nguồn sẽ được **65 điểm** để tránh đếm hai lần cùng một tác động. Gỡ **80% nguồn** rồi chèn một cụm liên kết cùng tên miền được **50 + 25 = 75 điểm** vì có thêm dấu hiệu quảng bá. Các mức điểm này là **trọng số đề xuất để thử nghiệm**.
