# Phân tích dữ liệu mở rộng: động lực GDP Việt Nam

## Tóm tắt kỳ mới nhất

- GDP thực theo bảng NSO (giá cố định 2010) năm 2025: tăng **8.02%**; kỳ 2025 trong bảng NSO mang trạng thái ước tính. Chuỗi mục tiêu World Bank trong hệ thống vẫn giữ riêng, không thay thế nhau do khác nguồn, đơn vị và phương pháp.
- Tăng trưởng theo phương pháp chi tiêu, đóng góp vào tăng GDP 2025:
- Vốn cố định: +2.95 điểm phần trăm
- Tồn kho: +0.18 điểm phần trăm
- Tiêu dùng nhà nước: +1.06 điểm phần trăm
- Tiêu dùng hộ gia đình: +3.99 điểm phần trăm
- Cán cân hàng hóa & dịch vụ: -0.59 điểm phần trăm
- Sai số thống kê: +0.43 điểm phần trăm
- Cơ cấu tăng GDP sản xuất năm 2025: nông nghiệp 3.78%; công nghiệp-xây dựng 8.95%; dịch vụ 8.62%. Đây là các tốc độ tăng của giá trị gia tăng thực, không phải mức đóng góp điểm phần trăm.
- Cán cân vãng lai/GDP năm 2025: 6.44% theo bảng cán cân thanh toán NSO.
- Cơ cấu đầu tư theo sở hữu (giá hiện hành, kỳ mới nhất trong bảng): Nhà nước: 29.7%, Ngoài nhà nước: 53.9%, Khu vực FDI: 16.4%. Tỷ trọng dùng tổng đầu tư làm mẫu số; có trạng thái sơ bộ/ước tính theo nguồn.
- Dữ liệu giá hàng hóa quốc tế: tới 2026-09, gồm 7 chuỗi được chọn (dầu, than, khí, gạo, urê, quặng sắt, đồng); đơn vị USD danh nghĩa từ Pink Sheet.

## Những lớp phân tích được bổ sung

1. **Chi tiêu GDP thực:** GDP, tiêu dùng hộ gia đình/nhà nước, tích lũy tài sản cố định, thay đổi tồn kho, cán cân hàng hóa-dịch vụ và sai số thống kê; tính đóng góp điểm phần trăm bằng `100 × (X_t − X_(t−1)) / GDP_(t−1)`. Các thành phần lá được dùng để tránh cộng trùng tiêu dùng/tổng đầu tư với tiểu mục.
2. **GDP theo sản xuất:** mức giá cố định 2010 và chỉ số tăng trưởng năm trước theo ngành; tách mức tăng của ngành khỏi tỷ trọng GDP danh nghĩa.
3. **Lao động và năng suất:** cơ cấu/số lao động theo ngành, thất nghiệp theo vùng và chỉ tiêu năng suất danh nghĩa của NSO. Bổ sung proxy năng suất thực ba khu vực bằng GDP thực ngành chia việc làm; proxy này là chỉ báo xấp xỉ, không thay chuỗi năng suất chính thức.
4. **Đầu tư:** vốn giải ngân theo sở hữu ở cả giá hiện hành, giá cố định 2010, tỷ trọng và tốc độ tăng; vốn thực theo ngành dùng để so sánh phân bổ vốn.
5. **Tài khóa và tiền tệ:** thu/chi ngân sách, chi đầu tư phát triển, tín dụng theo kỳ hạn/loại tiền, lãi suất tiền gửi/cho vay và tỷ lệ tín dụng/GDP danh nghĩa.
6. **Đối ngoại và cú sốc đầu vào:** cán cân thanh toán, tài khoản vãng lai, các mức giá hàng hóa thế giới và biến động theo năm.
7. **TFP:** phân rã NSO theo kỳ 5 năm, không nội suy thành chuỗi năm.

## So sánh mô tả với tăng trưởng GDP thực

- Tăng GDP thực × Thất nghiệp trong độ tuổi: Pearson -0.51, Spearman -0.17, n=16 (2010-2025). Đây là tương quan mô tả, không phải tác động nhân quả.
- Tăng GDP thực × Tăng vốn FDI thực: Pearson 0.51, Spearman 0.46, n=15 (2011-2025). Đây là tương quan mô tả, không phải tác động nhân quả.
- Tăng GDP thực × Tăng đầu tư thực toàn nền kinh tế: Pearson 0.39, Spearman 0.41, n=15 (2011-2025). Đây là tương quan mô tả, không phải tác động nhân quả.
- Tăng GDP thực × Tăng tín dụng danh nghĩa: Pearson 0.36, Spearman 0.30, n=10 (2016-2025). Đây là tương quan mô tả, không phải tác động nhân quả.

Các hệ số được tính trên cặp quan sát đầy đủ từng cặp; n nhỏ và các biến vĩ mô có thể đồng thời chịu cú sốc chung, xu hướng, thay đổi phương pháp đo hoặc trạng thái sơ bộ. Không dùng các tương quan này làm bằng chứng nhân quả hoặc khẳng định một biến giúp dự báo ngoài mẫu.

## Diễn biến TFP theo kỳ NSO

- 2011-2015: TFP đóng góp 34.75%, vốn 49.97%, lao động 15.28%; tăng trưởng TFP 2.15%.
- 2016-2020: TFP đóng góp 46.04%, vốn 52.16%, lao động 1.80%; tăng trưởng TFP 2.88%.
- 2021-2025: TFP đóng góp 46.84%, vốn 43.75%, lao động 9.41%; tăng trưởng TFP 2.91%.

## Proxy năng suất thực theo khu vực

Từ dữ liệu việc làm và GDP thực cùng kỳ, proxy năng suất nông nghiệp tăng khoảng **247.89%** trong giai đoạn 2005–2025. Đây là phép chia hai chuỗi gộp, chịu ảnh hưởng thay đổi phạm vi ngành và ước tính việc làm; không nên so sánh trực tiếp với năng suất danh nghĩa của NSO.

## Giới hạn sử dụng và độ tin cậy

- Các bảng NSO ghi rõ **ước tính/sơ bộ** ở năm 2025; nhãn này được giữ trong các CSV chuẩn hóa và cần cập nhật khi NSO hiệu chỉnh.
- Bảng đầu tư, GDP và tài khóa có thể khác năm gốc, phạm vi thống kê và khái niệm giải ngân/chi ngân sách. Không ghép giá hiện hành với chuỗi thực để tính tăng trưởng thực.
- Năng suất ngành NSO được lưu riêng với nhãn giá hiện hành; chỉ proxy mới dùng GDP giá cố định 2010.
- GDP năm là quan sát năm. Không tạo số GDP tháng/quý nội suy và không đưa biến giải thích chưa được backtest vào môודל dự báo GDP hiện có.
- Hệ thống dự báo đến 2030 giữ nguyên mô hình/rolling-origin hiện hành; các bộ mới mở rộng EDA và so sánh. Muốn đưa biến ngoại sinh vào mô hình cần dữ liệu phát hành theo thời gian thực (vintage), thiết kế dự báo đúng thời điểm, kiểm định rolling-origin, so sánh với baseline và kiểm soát rò rỉ dữ liệu.
- Giá hàng hóa World Bank là giá USD danh nghĩa quốc tế, không phải giá nhập khẩu thực tế của Việt Nam hay giá bán trong nước.

## Nguồn

- [Danh mục Tài khoản quốc gia NSO](https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/?tablelist=true) — GDP theo sản xuất/chi tiêu, tài khóa, tín dụng, lãi suất, cán cân thanh toán, TFP.
- [Danh mục Lao động NSO](https://pxweb.nso.gov.vn/pxweb/en/E%2002.%20Population%20and%20Employment/E%2002.%20Population%20and%20Employment__Px_E_02/?tablelist=true) — việc làm, năng suất lao động, thất nghiệp.
- [Danh mục Đầu tư NSO](https://pxweb.nso.gov.vn/pxweb/en/E%2004.%20Investment%20and%20construction/E%2004.%20Investment%20and%20construction__Px_E_04/?tablelist=true) — giải ngân theo sở hữu/ngành.
- [World Bank Commodity Markets / Pink Sheet](https://www.worldbank.org/en/research/commodity-markets) — giá hàng hóa theo tháng.

## QA

- 45/45 kiểm tra mở rộng đạt; các điều kiện kiểm tra gồm khóa trùng, bảng không rỗng, tổng tỷ trọng lao động, phân rã tăng trưởng, proxy dương và tổng TFP + vốn + lao động.
- Dữ liệu thô PXWeb ở `data/nso/raw/expanded/`, Pink Sheet ở `data/world_bank/raw/expanded/`; manifest ghi URL và thời điểm tải.
