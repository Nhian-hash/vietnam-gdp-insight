# Gợi ý bổ sung và trạng thái triển khai trên dashboard GDP

Các hạng mục bên dưới đã được đưa vào dashboard ngoại tuyến `dashboard.html` và được dựng lại bằng `build_dashboard.py`:

- **Đã triển khai:** KPI GDP danh nghĩa/thực, tăng trưởng quý, CPI và tỷ giá; EDA GDP và xu hướng cơ cấu ngành; scatter vĩ mô có Pearson/Spearman/n; ngoại thương/IIP; bán lẻ và FDI theo tần suất; GRDP sáu vùng và Top/Bottom 10 tỉnh; leaderboard nhiều chỉ số, backtest chân trời 1–5 năm và dự báo đến 2030; danh mục nguồn, QA, manifest phiên bản và tải CSV/JSON.
- **Cách giữ đúng dữ liệu:** không trộn GDP danh nghĩa với GDP thực; không chuyển tốc độ tăng trưởng quý thành quy mô GDP; bán lẻ thực 2026 vẫn được gắn nhãn lũy kế; FDI 9 tháng 2026 tách khỏi chuỗi năm; nội suy tháng không được dùng để backtest.
- **Chưa đưa bản đồ vào giao diện:** gói hiện tại chưa có dữ liệu ranh giới địa lý tỉnh có nguồn/giấy phép rõ ràng tương thích với phạm vi 63 tỉnh truyền thống. Dashboard hiển thị xếp hạng và so sánh vùng để tránh vẽ sai địa giới.

Thiết kế theo bố cục thanh điều hướng trái và các thẻ/charts như ảnh tham chiếu. Mỗi biểu đồ cần có bộ lọc kỳ, nguồn và trạng thái dữ liệu.

## 1. Tổng quan

**Thẻ KPI**

- GDP danh nghĩa mới nhất (USD hiện hành) và năm quan sát.
- Tăng trưởng GDP thực mới nhất theo năm.
- Tăng trưởng GDP theo quý gần nhất và lũy kế năm (hiển thị riêng với mức GDP).
- CPI bình quân năm hoặc CPI cùng kỳ; luôn ghi rõ cách tính.
- Tỷ giá VND/USD mới nhất và ngày/kỳ có số.
- Trạng thái nguồn: quan sát, sơ bộ, ước tính, hoặc tái tạo.

**Biểu đồ gợi ý:** đường GDP thực và danh nghĩa theo năm (hai biểu đồ riêng vì khác đơn vị); thanh tăng trưởng GDP thực; thẻ tăng trưởng quý 2026 từ `du_lieu_tang_truong_gdp_quy.csv`.

## 2. EDA và cơ cấu ngành

- Biểu đồ miền/đường tỷ trọng 4 thành phần GDP hiện hành: nông-lâm-thủy sản, công nghiệp-xây dựng, dịch vụ, thuế sản phẩm trừ trợ cấp.
- Bảng so sánh 2024–2025 cho giá trị danh nghĩa, tỷ trọng, thay đổi tỷ trọng theo điểm phần trăm.
- Biểu đồ tăng trưởng giá trị hiện hành từng ngành có nhãn “danh nghĩa”. Để phân tích tăng trưởng sản lượng, dùng chỉ số giá so sánh hoặc dữ liệu GDP thực theo ngành.
- Nguồn: `du_lieu_so_sanh_co_cau_nganh.csv`, `du_lieu_so_sanh_nganh_2025.csv`.

## 3. So sánh chỉ báo vĩ mô

- Bộ lọc năm để xem tăng trưởng GDP thực, lạm phát CPI, biến động tỷ giá, trade-to-GDP, cán cân thương mại/GDP, FDI thực hiện/GDP và bán lẻ/GDP.
- Biểu đồ scatter so sánh **tốc độ tăng trưởng** với đường hồi quy mô tả tùy chọn và hệ số Pearson/Spearman cùng số quan sát. Không so sánh trực tiếp các mức chuỗi đang có xu hướng dài hạn.
- CPI–tỷ giá theo tháng nên dùng biểu đồ 2 panel hoặc chuẩn hóa chỉ số 100 tại cùng tháng gốc; tránh hai trục tung dễ làm phóng đại quan hệ.
- Nguồn: `du_lieu_chi_so_kinh_te_hang_nam.csv`, `du_lieu_so_sanh_tuong_quan_vi_mo.csv`, `du_lieu_so_sanh_cpi_ty_gia_thang.csv`.

## 4. Ngoại thương và sản xuất

- Xuất khẩu/nhập khẩu theo tháng: hai đường riêng; cán cân thương mại là cột âm/dương theo USD.
- So sánh tháng 2026, cùng kỳ 9 tháng, và tổng năm theo đúng khoảng thời gian có trong nguồn. Khi chỉ có số sơ bộ, gắn nhãn ở tiêu đề và tooltip.
- IIP: đường chỉ số 2015=100 theo tháng; các thẻ so sánh Sep/Sep, Sep/Aug và 9 tháng/cùng kỳ. Không nối chung với chuỗi IIP năm trước=100.
- Thêm biểu đồ IIP và GDP tăng trưởng theo năm; dropdown lag 0–3 năm. Ghi rõ mẫu n nhỏ và chỉ mô tả.
- Nguồn: `du_lieu_xuat_nhap_khau_thang_2026.csv`, `du_lieu_so_sanh_ngoai_thuong_thang_2026.csv`, `du_lieu_san_xuat_iip_thang_2026.csv`, `du_lieu_san_xuat_iip_so_sanh_2026.csv`, `du_lieu_so_sanh_iip_gdp_hang_nam.csv`.

## 5. Bán lẻ và FDI

- Bán lẻ: so sánh giá trị hiện hành từng tháng với cùng kỳ; tăng trưởng thực lũy kế là một thẻ/đường riêng và phải ghi “lũy kế”, không thể hiện như tốc độ thực mỗi tháng.
- FDI: biểu đồ năm so vốn đăng ký dự án cấp phép với vốn thực hiện; bảng 9 tháng 2026 tách riêng vì phạm vi vốn đăng ký tổng hợp khác chuỗi năm.
- Nguồn: `du_lieu_ban_le_tieu_dung.csv`, `du_lieu_ban_le_tieu_dung_thang_2026.csv`, `du_lieu_fdi_dau_tu.csv`, `du_lieu_fdi_luy_ke_2026.csv`, `du_lieu_fdi_giai_doan_1988_1990.csv`.

## 6. GRDP địa phương

- Bản đồ tỉnh năm 2025 theo GRDP, GRDP/người hoặc tăng trưởng GRDP giá so sánh; cho chọn chỉ tiêu rõ ràng.
- Thanh Top 10/Bottom 10 tỉnh theo GRDP, GRDP/người, hoặc tăng trưởng; không xếp hạng theo mức danh nghĩa nếu người xem đang so hiệu quả tăng trưởng.
- So sánh 6 vùng thống kê bằng tỷ trọng và GRDP/người; khi drill-down vào tỉnh, không cộng đồng thời với tổng vùng.
- Nhãn “63 địa phương truyền thống” và “GRDP 2025 ước tính”; dữ liệu này chưa được chuẩn hóa sang địa giới hành chính mới.
- Nguồn: `du_lieu_so_sanh_grdp_63_tinh_2025.csv`, `du_lieu_so_sanh_grdp_6_vung_2025.csv`, `du_lieu_grdp_63_tinh_thanh.csv`.

## 7. Training Lab và so sánh mô hình

- Đồ thị thực tế/dự báo trên cùng 10 năm kiểm thử, có thể lọc năm kiểm thử.
- Bảng leaderboard dùng RMSE, MAE, MAPE, sMAPE và MASE; tất cả cùng 10 năm rolling-origin.
- Hiển thị baseline Drift cùng GRU/LSTM để tránh dashboard chỉ cho thấy mô hình neural.
- Mỗi dự báo chỉ dùng dữ liệu trước năm đó; không trộn dự báo ngoài mẫu với fitted values.
- Kết quả hiện tại: Drift tốt nhất trong lần chạy 2016–2025; GRU/LSTM kém hơn. Hiện cảnh báo “kết quả thăm dò – 41 quan sát năm”.
- Nguồn: `du_lieu_du_bao_rolling_origin.csv`, `so_sanh_hieu_qua_mo_hinh_du_bao.csv`, `du_lieu_phan_ra_gdp_thuc_hang_nam.csv`, `ket_qua_kiem_dinh_adf.csv`.

## 8. Trạng thái dữ liệu và khả năng truy xuất

Trong tooltip hoặc trang Quản lý dữ liệu, hiển thị tần suất, đơn vị, mốc mới nhất, nguồn, trạng thái và số dòng kiểm tra. Dùng `kiem_tra_chat_luong_du_lieu.csv`, `refresh_manifest.json`, `analysis_manifest.json`. Ô trống phải được giữ là null; giao diện không tự đổi thành 0.
