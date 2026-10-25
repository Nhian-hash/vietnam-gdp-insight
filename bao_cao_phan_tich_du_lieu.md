# Báo cáo phân tích bộ dữ liệu GDP Việt Nam

**Mốc cập nhật:** 23/10/2026. Báo cáo chỉ sử dụng các dữ liệu và giới hạn đã ghi trong manifest; số ước tính, số sơ bộ và số tái tạo được gắn nhãn riêng.

## Những kết quả có thể đưa lên dashboard

### Quy mô và tăng trưởng GDP

- GDP danh nghĩa năm 2025 trong bộ World Bank mới nhất: khoảng **514,70 tỷ USD**. GDP thực năm 2025 theo USD cố định 2015 là khoảng **437,71 tỷ USD**, tăng trưởng thực **8,02%** so với 2024.
- Thông cáo NSO mới nhất ghi nhận GDP tăng **8,15%** ở quý I, **8,81%** ở quý II, **9,95%** ở quý III; 9 tháng tăng **9,01%** so với cùng kỳ. Đây là **tốc độ tăng trưởng**, không phải quy mô GDP quý. [NSO – Báo cáo quý III và 9 tháng 2026](https://www.nso.gov.vn/bai-top/2026/10/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/)

### Cơ cấu ngành

Trong cơ cấu GDP hiện hành năm 2025 theo bảng NSO, tỷ trọng nông, lâm, thủy sản là **11,65%**, công nghiệp và xây dựng **37,65%**, dịch vụ **42,74%**, thuế sản phẩm trừ trợ cấp **7,96%**. Tốc độ tăng giá trị ngành tính từ bảng giá hiện hành là tăng danh nghĩa, không nên diễn giải là tăng trưởng sản lượng thực.

### Tỷ giá và lạm phát

- Tỷ giá IMF là bình quân tháng VND/USD đến **2026-07**. File biến động cung cấp thay đổi tháng, thay đổi cùng kỳ và độ lệch chuẩn trượt 12 tháng thường niên hóa. Chỉ số biến động là mô tả lịch sử, không phải dự báo tỷ giá.
- CPI NSO tháng 9/2026 tăng **0,62%** so với tháng trước, **4,20%** so với tháng 12/2025 và **5,08%** so với cùng kỳ; CPI bình quân 9 tháng tăng **4,52%** so với cùng kỳ. [NSO – CPI tháng 9 và 9 tháng 2026](https://www.nso.gov.vn/en/data-and-statistics/2026/10/consumer-price-index-gold-price-index-and-us-dollar-price-index-in-september-2026-q3-2026-and-the-nine-months-of-2026/)
- Chỉ số CPI mức tháng 1–9/2026 trong CSV được tái tạo từ CPI tháng 12/2025 và tỷ lệ lũy kế chính thức đã làm tròn; tăng trưởng tháng suy ra từ các chỉ số này có sai số làm tròn. Dùng số CPI công bố trực tiếp cho KPI chính thức nếu cần công bố chính xác.

### Sản xuất, thương mại và đầu tư

- IIP toàn ngành tháng 9/2026 có chỉ số **223,99** trên gốc bình quân năm 2015=100. So với tháng 8 tăng **3,26%**, so với cùng kỳ tăng **16,65%**; lũy kế 9 tháng tăng **12,33%**. Tỷ lệ lũy kế là một so sánh giai đoạn, không phải giá trị riêng tháng 9. [NSO – Workbook IIP tháng 9/2026](https://www.nso.gov.vn/wp-content/uploads/2026/10/IIP-Eng9.xlsx)
- Bộ bảng thương mại tháng 2026 đến tháng 9 là số **sơ bộ**. Tổng 9 tháng trong workbook là xuất khẩu khoảng **434,32 tỷ USD**, nhập khẩu **453,71 tỷ USD**, nhập siêu xấp xỉ **19,39 tỷ USD**. Bản tin NSO cũng nêu nhập siêu 9 tháng khoảng **19,42 tỷ USD**; chênh lệch nhỏ phản ánh phiên bản cập nhật/độ chính xác của các bảng nguồn. Vì vậy, cần hiển thị giá trị tính từ workbook cùng với nhãn “sơ bộ”, và dùng con số bản tin khi cần trích dẫn báo cáo tổng hợp. [NSO – Bảng xuất nhập khẩu hàng tháng 2026](https://www.nso.gov.vn/en/data-and-statistics/2026/03/exports-and-imports-value-by-months-of-2026/), [NSO – cập nhật cán cân 9 tháng](https://www.nso.gov.vn/tin-tuc-thong-ke/2026/10/xuat-sieu-tro-lai-tin-hieu-dao-chieu-cac-thang-cuoi-nam/)
- FDI 9 tháng 2026 được lưu riêng: vốn đăng ký tổng hợp **50,36 tỷ USD**, vốn thực hiện lũy kế **21,07 tỷ USD**. Vốn đăng ký tổng hợp bao gồm cấp mới, điều chỉnh và góp vốn/mua cổ phần; định nghĩa khác với vốn đăng ký dự án cấp phép trong chuỗi năm. [NSO – Báo cáo quý III và 9 tháng 2026](https://www.nso.gov.vn/bai-top/2026/10/bao-cao-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/)

### GRDP tỉnh, vùng

- Bảng so sánh 2025 xếp TP. Hồ Chí Minh và Hà Nội là hai địa phương có quy mô GRDP lớn nhất trong bộ 63 địa phương truyền thống; tiếp theo là Bình Dương, Đồng Nai và Hải Phòng. GRDP 2025 được tính từ GRDP/người nhân dân số bình quân và mang nhãn ước tính.
- Theo 6 vùng thống kê trong cùng bảng, Đồng bằng sông Hồng và Đông Nam Bộ lần lượt chiếm khoảng **29,91%** và **29,66%** tổng GRDP của sáu vùng. Sáu dòng vùng là tổng hợp cấp vùng, không được cộng lại với các tỉnh nằm bên dưới.

## Kiểm định và lựa chọn mô hình

- ADF trên log GDP thực năm (n=41, có xu hướng tuyến tính và hằng số) cho p≈**0,881**: chưa đủ bằng chứng bác bỏ nghiệm đơn vị. ADF trên sai phân log (n=40, có hằng số) cho p≈**0,0006**: bác bỏ nghiệm đơn vị ở mức 5% theo đặc tả đã chọn.
- Phân rã dùng HP filter trên log GDP thực năm, λ=6,25. Chu kỳ HP là sai lệch quanh xu hướng thống kê; không coi là GDP tiềm năng. Chuỗi năm không có mùa vụ theo tháng để phân rã seasonal.
- Backtest expanding-window một bước, huấn luyện chỉ dùng năm trước dự báo, kiểm thử **2016–2025**. MAPE/RMSE cùng tính trên 10 năm và cùng một mục tiêu GDP thực USD 2015:

| Mô hình | MAPE | RMSE |
|---|---:|---:|
| Drift – tăng trưởng log trung bình trong tập huấn luyện | 1,50% | 6,65 tỷ USD 2015 |
| Xu hướng log tuyến tính | 4,78% | 18,77 tỷ USD 2015 |
| Naive – giữ mức năm trước | 5,84% | 21,20 tỷ USD 2015 |
| GRU | 8,53% | 30,23 tỷ USD 2015 |
| LSTM | 11,07% | 39,35 tỷ USD 2015 |

Trong lần backtest này, Drift thắng các mô hình còn lại. Điều này không chứng minh Drift luôn tốt hơn; 10 năm kiểm thử là mẫu nhỏ, nhưng đủ để cảnh báo không nên triển khai GRU/LSTM chỉ dựa trên độ mới của thuật toán. Các tham số GRU/LSTM được cố định trước, chuẩn hóa theo tập huấn luyện của từng fold, không xáo trộn thời gian và không dùng spline tháng.

## Cách đọc tương quan

- Tăng trưởng IIP và GDP thực cùng năm có tương quan Pearson khoảng **0,74** (n=14), nhưng IIP trễ một năm chỉ khoảng **0,16** (n=13). Mẫu ngắn và quan hệ cùng năm không chứng minh khả năng dự báo.
- Tương quan giữa CPI, tỷ giá và GDP chỉ là mô tả. Không diễn giải thành quan hệ nhân quả; mức GDP danh nghĩa và tỷ giá đều có xu hướng dài hạn nên chỉ so sánh tăng trưởng/tỷ lệ, không tương quan trực tiếp các mức.
- Bán lẻ thực theo năm là proxy giảm phát bằng CPI chung. Khác biệt về rổ giá và cơ cấu dịch vụ khiến nó không thay thế chỉ số khối lượng bán lẻ chính thức.

## Gợi ý dùng kết quả trong khóa luận

1. Dùng GDP thực năm để kiểm định, huấn luyện và backtest chính; đưa spline tháng vào giao diện chỉ để minh họa/giữ tương thích.
2. Trình bày baseline trước GRU/LSTM. Nếu muốn giữ GRU/LSTM làm phương pháp chính, cần bổ sung dữ liệu GDP quý thực có mức quan sát, mở rộng cửa sổ lịch sử và kiểm định rolling-origin nhiều chân trời.
3. Cho dashboard bộ lọc kỳ, đơn vị, loại số liệu (quan sát/sơ bộ/ước tính/tái tạo), nguồn và trạng thái để người xem không nhầm mức, tốc độ tăng, số lũy kế hay chỉ số.

Các chi tiết biến, đơn vị và số liệu gốc nằm trong `README.md`, `refresh_manifest.json`, `analysis_manifest.json` và các CSV tương ứng.
