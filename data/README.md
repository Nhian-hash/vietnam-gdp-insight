# Tổ chức dữ liệu

Mỗi nhà cung cấp có thư mục riêng. Trong đó, `raw/` giữ bản tải nguyên gốc; `processed/` giữ bảng đã chuẩn hóa nhưng còn phản ánh trực tiếp một nguồn.

- `nso/` — Cục Thống kê Việt Nam: PXWeb, báo cáo tháng, GDP, ngành, GRDP, thương mại, lao động, đầu tư và các chỉ báo trong nước.
- `world_bank/` — World Bank WDI và Pink Sheet.
- `imf/` — chuỗi tỷ giá và phản hồi API IMF.
- `derived/combined/` — bảng ghép nhiều nguồn.
- `derived/macro/` — chỉ báo biến đổi, chu kỳ và bảng vĩ mô.
- `derived/comparison/` — bảng đối chiếu ngành, địa phương, thương mại và các biến.
- `derived/forecast/` — dự báo, backtest và so sánh mô hình.
- `derived/quality/` — kiểm định, kiểm tra chất lượng và trạng thái tải dữ liệu.
- `derived/compatibility/` — chuỗi tương thích cũ, gồm GDP tháng nội suy; không xem đây là quan sát GDP tháng.

`catalog.json` ánh xạ tên tệp API sang đường dẫn, nguồn và loại dữ liệu. Các script Python và Node.js dùng danh mục này để đọc/ghi dữ liệu sau khi cập nhật.
