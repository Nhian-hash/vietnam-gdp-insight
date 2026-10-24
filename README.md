# Gói cập nhật dữ liệu GDP Việt Nam

Gói này chuẩn bị các tệp thay thế cho dữ liệu mà notebook hiện tại đọc, đồng thời bổ sung dữ liệu thực GDP và CPI để mở rộng hệ thống.

## Đã cập nhật

- GDP danh nghĩa Việt Nam theo USD hiện hành đến **2025** từ World Bank. Giá trị 2025 mới nhất trong API là khoảng **514,70 tỷ USD**; 2024 là **476,32 tỷ USD**.
- Cập nhật mới nhất về tăng trưởng GDP trong năm 2026 từ Cục Thống kê: quý I **8,15%**, quý II **8,81%**, quý III **9,95%** so với cùng kỳ; 9 tháng tăng **9,01%**. Đây là tốc độ tăng trưởng ước tính, không phải quy mô GDP.
- GDP giá cố định năm 2015 và tăng trưởng GDP thực đến 2025 được lưu riêng để dùng làm mục tiêu dự báo phù hợp hơn với tăng trưởng kinh tế.
- CPI tháng theo gốc 2019 từ PXWeb của Tổng cục Thống kê cho 2020–2025; tháng 1–9/2026 được suy ra từ chỉ số tháng 12/2025 và mức tăng CPI lũy kế chính thức mà NSO công bố. Các giá trị 2026 có sai số làm tròn do tỷ lệ công bố được làm tròn đến 0,01 điểm phần trăm.
- Chuỗi GDP tháng được tính lại đến tháng 12/2025 để các biểu đồ hiện tại có thể đọc mốc năm mới nhất; giá trị năm được đặt tại tháng 12 tương ứng để tháng 12/2025 khớp GDP năm 2025.

## Tệp

- `GDP_Vietnam_Annual.csv` — đầu vào CSV tương thích với notebook; có `Nam_Goc`, `Year`, `Date`, `GDP_USD`, `GDP_USD_Billion`.
- `GDP_Vietnam_Annual.xlsx` — bản Excel đã sửa thang đo USD và cập nhật năm 2025.
- `GDP_Vietnam_Monthly.csv` — cùng tên và các trường chính mà dashboard/notebook hiện tại dùng: `Date`, `Year`, `Month`, `GDP_USD_Billion`.
- `du_lieu_gdp_quoc_gia_co_cau_nganh.csv` — GDP và ba nhóm giá trị gia tăng theo schema tiếng Việt.
- `du_lieu_gdp_thuc_va_tang_truong.csv` — GDP thực USD 2015 và tốc độ tăng trưởng GDP thực.
- `du_lieu_tang_truong_gdp_quy.csv` — tốc độ tăng GDP chính thức theo quý đến quý III/2026; một số chỉ tiêu ngành chỉ có cho quý III theo báo cáo nguồn.
- `du_lieu_lam_phat_cpi.csv` — CPI chỉ số, ngày đầu tháng, đến 2026-09.
- `trang_thai_du_lieu.csv`, `refresh_manifest.json` — mốc dữ liệu, nguồn và ghi chú tình trạng từng chuỗi.
- `refresh_data.mjs` — script tải lại WDI và PXWeb, rồi ghi các CSV tương thích vào cùng thư mục.
- `DACN_refresh_2026.ipynb` — bản notebook đã đổi API sang HTTPS, làm mới biểu đồ theo dữ liệu đến 2025 và cập nhật mốc dự báo từ 2026.
- `du_lieu_chi_so_kinh_te_hang_nam.csv` — bảng năm ghép GDP, tỷ giá bình quân năm, thương mại, CPI, bán lẻ và FDI; có các tỷ lệ Trade/GDP, FDI/GDP và bán lẻ/GDP.
- `du_lieu_cpi_phan_tich_thang.csv`, `du_lieu_fx_bien_dong_thang.csv` — CPI MoM/YoY và tỷ giá MoM/YoY, biến động 12 tháng thường niên hóa; có cờ phân biệt CPI 2026 tái tạo.
- `du_lieu_so_sanh_co_cau_nganh.csv`, `du_lieu_so_sanh_nganh_2025.csv` — so sánh cơ cấu và biến động danh nghĩa của các khu vực kinh tế.
- `du_lieu_so_sanh_grdp_63_tinh_2025.csv`, `du_lieu_so_sanh_grdp_6_vung_2025.csv` — xếp hạng GRDP và GRDP/người; sáu vùng thống kê không cộng đồng thời với tỉnh thành phần.
- `du_lieu_so_sanh_iip_gdp_hang_nam.csv`, `du_lieu_so_sanh_tuong_quan_vi_mo.csv`, `du_lieu_so_sanh_cpi_ty_gia_thang.csv` — các bảng so sánh IIP–GDP theo độ trễ, tương quan vĩ mô và đối chiếu CPI–tỷ giá.
- `du_lieu_xuat_nhap_khau_thang_2026.csv`, `du_lieu_san_xuat_iip_thang_2026.csv` — dữ liệu NSO sơ bộ tháng 1–9/2026; IIP theo chỉ số gốc 2015=100.
- `du_lieu_iip_ban_le_xuat_nhap_khau.csv` — bảng tương thích gộp IIP, bán lẻ, xuất khẩu, nhập khẩu và cán cân thương mại theo tháng 1–9/2026.
- `du_lieu_fdi_giai_doan_1988_1990.csv` — số FDI gộp 3 năm theo nguồn; không chia thành các giá trị năm giả định.
- `du_lieu_phan_ra_gdp_thuc_hang_nam.csv`, `ket_qua_kiem_dinh_adf.csv` — chu kỳ/xu hướng HP và kiểm định dừng trên GDP thực năm quan sát.
- `du_lieu_du_bao_rolling_origin.csv`, `so_sanh_hieu_qua_mo_hinh_du_bao.csv` — dự báo ngoài mẫu cuốn chiếu, đối chiếu baseline với GRU/LSTM.
- `du_lieu_du_bao_gdp_thuc_den_2030.csv` — dự báo GDP thực 2026–2030 của Naive, Drift, xu hướng log tuyến tính, GRU và LSTM; đây là kịch bản mô hình, không phải số liệu chính thức.
- `du_lieu_du_bao_nhieu_chan_troi.csv`, `so_sanh_hieu_qua_mo_hinh_theo_chan_troi.csv` — dự báo kiểm thử rolling-origin và chỉ số đánh giá riêng cho chân trời 1–5 năm.
- `kiem_tra_chat_luong_du_lieu.csv`, `analysis_manifest.json`, `bao_cao_phan_tich_du_lieu.md`, `goi_y_bo_sung_dashboard.md` — kiểm tra khóa trùng/thiếu, cân đối và miền dữ liệu (lần chạy hiện tại 45/45 đạt), cấu hình phân tích, nhận định kết quả và trạng thái phát triển dashboard.
- `data_version_manifest.json`, `data_versions/` và `snapshot_data.py` — mã phiên bản theo nội dung, bản kê nguồn/đầu vào và ZIP bất biến của các CSV chuẩn hóa cho mỗi phiên bản dữ liệu mới.
- `dashboard.html` — dashboard ngoại tuyến theo từng trang: tổng quan KPI; EDA GDP; ba mục chuyển hướng riêng cho Nông–lâm–thủy sản, Công nghiệp–xây dựng và Dịch vụ; CPI/tỷ giá; ngoại thương/IIP; bán lẻ/FDI; GRDP; dự báo GDP đến 2030; quản lý nguồn và QA. Các trang ngành có bộ lọc, so sánh cấu trúc GDP hiện hành, tăng trưởng GDP thực, đóng góp và tải CSV. `build_dashboard.py` tạo lại dashboard từ các CSV cập nhật.
- `refresh_system.ps1`, `build_extended_data.mjs`, `extract_monthly_official.py`, `analyze_observed_data.py`, `snapshot_data.py` — pipeline cập nhật/tải nguồn, trích xuất workbook, đánh giá mô hình, kiểm tra chất lượng và đóng gói snapshot có thể tái lập.

## Áp dụng dữ liệu và dashboard vào đồ án

Các tệp cùng tên như `GDP_Vietnam_Annual.csv`, `GDP_Vietnam_Annual.xlsx` và `GDP_Vietnam_Monthly.csv` đã được cập nhật để thay tệp dữ liệu cũ. Dashboard mới đọc trực tiếp các CSV trong gói này và chạy ngoại tuyến. Để cập nhật PBIX, mở **Transform data / Data source settings**, trỏ các truy vấn tới CSV mới rồi **Refresh**; nếu PBIX dùng bản sao nhúng, cần thay nguồn truy vấn thay vì chỉ chép file vào thư mục. Notebook cũ không bị sửa; `DACN_refresh_2026.ipynb` là bản riêng dùng bộ dữ liệu mới.

## Giới hạn cần giữ khi trình bày khóa luận

`GDP_Vietnam_Monthly.csv` là chuỗi **nội suy Cubic Spline từ dữ liệu năm**, không phải GDP quan sát theo tháng. Các mốc GDP năm được neo vào tháng 12; tháng 12/2025 khớp quan sát năm 2025. Các tháng còn lại vẫn chỉ là giá trị nội suy. Không dùng các tháng nội suy để tính MAPE/độ chính xác như thể đó là dữ liệu thực. File quý 2026 chỉ có tốc độ tăng so với cùng kỳ, không có mức GDP để ghép thành chuỗi quy mô. Khi đánh giá mô hình, dùng chuỗi GDP quý chính thức có mức GDP hoặc tốc độ tăng GDP; không coi spline là dữ liệu thực.

World Bank phân ngành theo giá trị gia tăng nông nghiệp, công nghiệp và dịch vụ. Các giá trị ba ngành không nhất thiết cộng bằng GDP vì còn thuế sản phẩm ròng và các điều chỉnh thống kê. Dữ liệu 2026 CPI trong file là chuỗi mức chỉ số suy ra từ tỷ lệ CPI lũy kế đã công bố, không phải bản ghi mức CPI gốc PXWeb.

## Phân tích so sánh và lựa chọn mô hình

- Mọi so sánh theo tháng/quý/năm được giữ ở đúng tần suất. Ví dụ, số tăng GDP quý 2026 là tỷ lệ so cùng kỳ, không ghép với chuỗi GDP năm như thể cùng đại lượng.
- ADF thực hiện trên log GDP thực năm và sai phân log của chuỗi này. Kết quả hiện tại không bác bỏ nghiệm đơn vị ở mức GDP thực (p≈0,881), nhưng bác bỏ ở sai phân log (p≈0,0006). Đây là kiểm định trên 41 quan sát năm, nhạy với cấu trúc xu hướng và thay đổi chế độ.
- Phân rã xu hướng/chu kỳ dùng HP filter trên log GDP thực năm với λ=6,25. Thành phần chu kỳ nhạy ở hai đầu chuỗi và không phải ước tính GDP tiềm năng. Không thực hiện seasonal decomposition vì GDP thực đầu vào là dữ liệu năm, không có chu kỳ mùa vụ quan sát.
- Đánh giá dự báo dùng expanding-window rolling-origin với chân trời 1–5 năm. Chân trời một năm kiểm thử 2016–2025 (10 điểm); chân trời năm năm có 6 điểm kiểm thử vì dữ liệu quan sát kết thúc năm 2025. Số fold giảm theo chân trời (10, 9, 8, 7, 6). Mỗi fold chỉ sử dụng dữ liệu có sẵn đến năm gốc; chuẩn hóa được fit trên tập huấn luyện, không chia ngẫu nhiên chuỗi thời gian.
- Trong lần chạy hiện tại, Drift có MAPE≈1,50% và RMSE≈6,65 tỷ USD (giá 2015); GRU có MAPE≈8,53%; LSTM≈11,07%. Với chỉ 41 điểm năm và 10 năm kiểm thử, đây là kết quả thăm dò, chưa đủ để khẳng định mô hình thắng ổn định. Không nên đưa GRU/LSTM thành mô hình chính nếu không vượt baseline qua nhiều cửa sổ kiểm thử và nhiều lần cập nhật dữ liệu.
- Trong kết quả hiện tại, Drift có MAPE thấp nhất ở cả năm chân trời (xấp xỉ 1,50%, 2,15%, 2,91%, 3,96%, 4,36% từ chân trời 1 đến 5 năm). Sai số tăng theo thời hạn và số fold nhỏ dần; đây là mô tả của cửa sổ kiểm thử hiện tại, không bảo đảm Drift sẽ luôn tốt nhất khi có dữ liệu mới.
- Dự báo 2026–2030 được tạo sau backtest bằng cùng định nghĩa GDP thực năm: Naive giữ mức 2025, Drift ngoại suy mức thay đổi log trung bình, xu hướng tuyến tính ngoại suy hồi quy trên log GDP, GRU/LSTM dự báo đệ quy 5 bước sau khi fit trên toàn bộ chuỗi quan sát đến 2025. Dashboard hiển thị dải P80 kinh nghiệm từ sai số log tuyệt đối cùng chân trời; thứ hạng phân vị dùng hiệu chỉnh hữu hạn mẫu `ceil((n+1)×0,8)`. Đây không phải khoảng tin cậy có bảo đảm coverage 80%: chuỗi thời gian có phụ thuộc và mẫu hiệu chuẩn nhỏ. Không diễn giải dự báo thành số GDP chính thức.
- Tương quan IIP tăng trưởng cùng năm và GDP thực tăng trưởng 2012–2025 hiện khoảng 0,74 (n=14); tương quan IIP trễ một năm khoảng 0,16 (n=13). Đây là mô tả mẫu ngắn, không phải bằng chứng IIP dự báo hoặc gây ra GDP. IIP tháng 2026 chưa có GDP tháng quan sát để kiểm định độ trễ tháng.
- Dashboard cho phép scatter GDP thực với CPI, biến động tỷ giá, IIP trễ 0–3 năm và tăng trưởng bán lẻ thực ước tính; hiển thị Pearson, Spearman và số quan sát. CPI và tỷ giá theo tháng được quy chỉ số 100 tại tháng 1/2020 để so hình dạng chuỗi, không so hai mức tuyệt đối trên cùng đơn vị.
- Bán lẻ thực theo năm là proxy gần đúng, tính từ tăng trưởng bán lẻ danh nghĩa đã giảm lạm phát CPI chung; đây không phải chỉ số khối lượng bán lẻ chính thức. Tăng trưởng thực bán lẻ lũy kế 2026 của NSO phải được hiển thị riêng và không gán thành tăng trưởng thực riêng từng tháng.
- Chuỗi FDI năm của NSO bắt đầu năm 1991; nguồn gộp 1988–1990 được lưu thành một giai đoạn riêng. FDI lũy kế 9 tháng 2026 có định nghĩa vốn đăng ký khác với chuỗi FDI cấp phép năm, nên không nối thẳng thành một chuỗi đồng nhất.
- GRDP địa phương được ước tính bằng GRDP/người × dân số bình quân. Bảng có 63 đơn vị địa lý truyền thống và 6 vùng thống kê cho 2018–2025; số năm 2025 là ước tính, và không cộng vùng với tỉnh trong cùng phép tổng hợp.

## Cập nhật và chạy lại

1. Cài Node.js và Python dependencies `xlrd`, `openpyxl`, `pandas`, `numpy`, `statsmodels`, `torch`.
2. Trên Windows, chạy `./refresh_system.ps1` để tải nguồn mới rồi chạy lần lượt trích xuất, phân tích, QA, snapshot và dựng dashboard. Nếu muốn dùng nguồn workbook đã có sẵn trong `sources/` mà không tải lại, chạy `./refresh_system.ps1 -SkipSourceDownload`.
3. Có thể chạy riêng từng bước: `node build_extended_data.mjs`, `python extract_monthly_official.py`, `python analyze_observed_data.py`, `python build_dashboard.py`.
4. `analyze_observed_data.py` gọi `snapshot_data.py` sau khi phân tích thành công. Script tạo ZIP dữ liệu chuẩn hóa theo mã nội dung; chạy lại với cùng dữ liệu sẽ giữ nguyên phiên bản thay vì tạo snapshot trùng.

Dashboard có tải các bảng đang hiển thị ra CSV/JSON; có thể chọn chân trời 1–5 năm để xem backtest và so sánh mô hình. Dải P80 được tính riêng cho từng mô hình và từng chân trời, kèm số mẫu hiệu chuẩn trong bảng dự báo. Tệp ZIP của phiên bản hiện tại mở từ mục danh mục nguồn dữ liệu.

Phân hệ GRDP hiện dùng xếp hạng và so sánh sáu vùng/63 địa phương theo năm; không vẽ bản đồ ranh giới địa lý do gói dữ liệu hiện tại chưa kèm tệp ranh giới tỉnh đáng tin cậy. Điều này tránh gán sai vị trí/địa giới cho chuỗi 63 tỉnh truyền thống.

Tệp trống trong các bảng ghép biểu thị ngoài phạm vi nguồn, kỳ chưa có số liệu hoặc phép so sánh không phù hợp; không tự điền 0. Mốc cắt dữ liệu và nguồn cụ thể xem `refresh_manifest.json` và `analysis_manifest.json`.

## Nguồn

- World Bank API: [GDP hiện hành](https://api.worldbank.org/v2/country/VNM/indicator/NY.GDP.MKTP.CD?date=1985:2026&format=json), [GDP thực cố định 2015](https://api.worldbank.org/v2/country/VNM/indicator/NY.GDP.MKTP.KD?date=1985:2026&format=json), [tăng trưởng GDP thực](https://api.worldbank.org/v2/country/VNM/indicator/NY.GDP.MKTP.KD.ZG?date=1985:2026&format=json), và các chỉ báo giá trị gia tăng ngành `NV.AGR.TOTL.CD`, `NV.IND.TOTL.CD`, `NV.SRV.TOTL.CD`.
- NSO PXWeb: [CPI tháng so với gốc 2019](https://pxweb.nso.gov.vn/pxweb/en/E%2011.%20CPI/E%2011.%20CPI__Px_E_11/E11.07.px/).
- NSO CPI tháng 9/2026: [thông cáo chính thức](https://www.nso.gov.vn/en/data-and-statistics/2026/10/consumer-price-index-gold-price-index-and-us-dollar-price-index-in-september-2026-q3-2026-and-the-nine-months-of-2026/); các mức lũy kế tháng 1–8/2026 nằm trong kho thông cáo CPI trên nso.gov.vn.
- NSO GDP quý III và 9 tháng năm 2026: [thông cáo chính thức](https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/10/thong-cao-bao-chi-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/).

Ngày tải: xem `refresh_manifest.json`.

## Mở rộng dữ liệu và phân tích động lực GDP

Gói dữ liệu bổ sung lấy từ các bảng PXWeb chính thức của Cục Thống kê (NSO) và World Bank Pink Sheet. Dữ liệu gốc được lưu tại `sources/expanded/`; `source_manifest.json` ghi URL truy cập. Các bảng chuẩn hóa được đưa vào dashboard và snapshot có mã nội dung.

| Lớp dữ liệu | Tệp chuẩn hóa | Phạm vi / đơn vị | Phân tích được bổ sung |
|---|---|---|---|
| GDP theo chi tiêu | `du_lieu_gdp_theo_chi_tieu.csv` | 2005–2025; giá cố định 2010, tỷ VND | Mức và tốc độ tăng thành phần chi tiêu; tách tổng với thành phần con |
| Đóng góp vào tăng GDP | `du_lieu_dong_gop_gdp_theo_chi_tieu.csv` | 2006–2025; điểm phần trăm | Đóng góp vốn cố định, tồn kho, tiêu dùng hộ/nhà nước, cán cân hàng hóa-dịch vụ và sai số thống kê |
| GDP theo ngành, giá thực | `du_lieu_gdp_thuc_theo_nganh.csv` | 2005–2025; giá cố định 2010 | Tách tốc độ tăng ngành khỏi tỷ trọng GDP hiện hành |
| Lao động theo ngành | `du_lieu_lao_dong_theo_nganh.csv` | 2005, 2007–2025; nghìn người và % | Dịch chuyển cơ cấu việc làm nông nghiệp/công nghiệp/dịch vụ |
| Năng suất lao động | `du_lieu_nang_suat_lao_dong.csv`, `du_lieu_nang_suat_thuc_theo_khu_vuc.csv` | 2005, 2007–2025; NSO danh nghĩa và proxy thực giá 2010 | Theo dõi năng suất chính thức danh nghĩa tách biệt với proxy thực GDP/người lao động |
| Thất nghiệp | `du_lieu_that_nghiep_vung.csv` | 2010–2025; % lực lượng lao động trong độ tuổi | So sánh toàn quốc và sáu vùng, thành thị/nông thôn |
| Đầu tư | `du_lieu_dau_tu_theo_loai_hinh.csv`, `du_lieu_dau_tu_theo_nganh_thuc.csv` | 2010–2025; hiện hành và giá cố định 2010 | Cơ cấu sở hữu, tăng trưởng đầu tư thực, phân bổ vốn theo ngành |
| Tài khóa | `du_lieu_tai_khoa_ngan_sach.csv` | Thu từ 2000, chi từ 2005; tỷ VND hiện hành và % cơ cấu | Chi đầu tư phát triển/GDP và tỷ trọng trong tổng chi; tổng thu/chi |
| Tài chính | `du_lieu_tin_dung_du_no.csv`, `du_lieu_lai_suat_ngan_hang.csv` | 2015–2025; nghìn tỷ VND và %/năm | Tăng trưởng dư nợ, tỷ lệ tín dụng/GDP, lãi tiền gửi và cho vay |
| Cán cân thanh toán | `du_lieu_can_can_thanh_toan.csv` | 2018–2025; triệu USD, có tỷ lệ/GDP | Tài khoản vãng lai, hàng hóa/dịch vụ, đầu tư và cán cân tài chính |
| TFP | `du_lieu_dong_gop_tfp.csv` | Ba kỳ 5 năm 2011–2025 | So sánh đóng góp vốn, lao động, TFP và tăng trưởng TFP |
| Giá hàng hóa quốc tế | `du_lieu_gia_hang_hoa_quoc_te.csv` | Tháng, chuỗi theo phạm vi nguồn đến 2026-09; USD danh nghĩa | Dầu, than, khí châu Âu, gạo Việt Nam 5%, urê, quặng sắt và đồng |
| Bảng phân tích tích hợp | `du_lieu_so_sanh_dong_luc_gdp.csv`, `du_lieu_tuong_quan_dong_luc_gdp.csv` | Năm, 1985–2025 tùy biến số | So sánh GDP, ngành, đầu tư, lao động, CPI, ngân sách, tín dụng, cán cân và giá hàng hóa |

`phan_tich_du_lieu_mo_rong.md` ghi kết quả số liệu của lần cập nhật đang có. Trong bảng GDP theo chi tiêu, đóng góp được tính là `100 × (thành phần_t − thành phần_t−1) / GDP_(t−1)`. Chỉ dùng các thành phần lá để không cộng trùng tiêu dùng cuối cùng với tiêu dùng hộ/nhà nước hoặc tổng tích lũy với vốn cố định/tồn kho. Năm 2010 được để trống đóng góp do chuỗi đổi sang giá cố định 2010; tốc độ tăng GDP chính thức của NSO vẫn được giữ. Cơ cấu đóng góp kiểm tra khớp tốc độ tăng GDP theo bảng nguồn với sai lệch tối đa khoảng 0,005 điểm phần trăm do làm tròn.

### Cách đọc kết quả và các giới hạn phương pháp

- GDP thực theo ngành là giá trị gia tăng theo giá cố định 2010. Tăng trưởng ngành là phần trăm thay đổi mức thực; không đồng nhất với tỷ trọng đóng góp điểm phần trăm vào GDP.
- Chỉ tiêu năng suất NSO trong PXWeb có đơn vị triệu VND/lao động theo mức giá của năm, vì vậy tăng trưởng trực tiếp từ chuỗi này là tăng trưởng danh nghĩa. Proxy năng suất thực được tính bằng GDP giá cố định 2010 chia số lao động nghìn người; do nhóm ngành và phạm vi đo lường có thể không khớp hoàn toàn, chỉ nên coi là chỉ báo xấp xỉ.
- Tỷ lệ chi đầu tư phát triển ngân sách/GDP và cơ cấu đầu tư theo sở hữu dùng giá hiện hành. Không gọi đây là tăng trưởng đầu tư thực; chỉ chuỗi đầu tư có giá cố định 2010 mới dùng để tính tăng trưởng thực.
- Tín dụng là dư nợ danh nghĩa cuối năm; tài khoản vãng lai thuộc cán cân thanh toán, khác cán cân xuất nhập khẩu hàng hóa. Giá hàng hóa thế giới là giá USD danh nghĩa, không phải giá nhập khẩu thực tế của Việt Nam.
- NSO gắn nhãn **ước tính** hoặc **sơ bộ** cho một số giá trị 2025. Trạng thái đó được giữ nguyên qua CSV và dashboard; các số sẽ thay đổi khi NSO hiệu chỉnh.
- Pearson/Spearman được tính trên các năm có đủ cặp số liệu; dashboard hiển thị `n` và giai đoạn từng cặp. Đây là tương quan mô tả trên mẫu ngắn, không chứng minh nhân quả và không tự động xác nhận giá trị dự báo.
- Bộ dữ liệu mở rộng hiện dùng cho EDA và đối chiếu. Mô hình dự báo đến 2030 đang giữ biến mục tiêu GDP thực và backtest rolling-origin hiện hành; chưa đưa các biến giải thích vào như mô hình đa biến vì chuỗi ngắn, tần suất khác nhau và chưa có kho dữ liệu vintage theo ngày công bố. Muốn nâng mô hình cần dựng tập dữ liệu theo thời điểm thông tin thực sự sẵn có, so sánh baseline ngoài mẫu, kiểm soát rò rỉ và kiểm tra ổn định qua nhiều lần cập nhật.

Nguồn chính: [NSO – Tài khoản quốc gia và ngân sách](https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/?tablelist=true), [NSO – Dân số và việc làm](https://pxweb.nso.gov.vn/pxweb/en/E%2002.%20Population%20and%20Employment/E%2002.%20Population%20and%20Employment__Px_E_02/?tablelist=true), [NSO – Đầu tư và xây dựng](https://pxweb.nso.gov.vn/pxweb/en/E%2004.%20Investment%20and%20construction/E%2004.%20Investment%20and%20construction__Px_E_04/?tablelist=true), [World Bank – Commodity Markets/Pink Sheet](https://www.worldbank.org/en/research/commodity-markets).

### Cập nhật các bảng mở rộng

Pipeline `refresh_system.ps1` nay tải thêm PXWeb và World Bank Pink Sheet bằng `refresh_expanded_data.mjs`, giữ bản nguồn thô, chuẩn hóa/phân tích bằng `analyze_expanded_data.py`, chạy QA, đóng snapshot mới và dựng `dashboard.html`. Với `-SkipSourceDownload`, pipeline chạy trên các tệp nguồn đã có trong thư mục `sources/expanded/`.

## GDP chi tiết theo 3 khu vực kinh tế

- `du_lieu_gdp_nganh_chi_tiet.csv` chứa 20 hoạt động kinh tế (1 nông-lâm-thủy sản, 5 công nghiệp-xây dựng, 14 dịch vụ) và dòng thuế sản phẩm để đối chiếu tổng GDP, giai đoạn 2005–2025. Nguồn gốc là [PXWeb E03.04-05](https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.04-05.px/) (giá hiện hành và tỷ trọng) cùng [PXWeb E03.06-07](https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.06-07.px/) (mức giá cố định và chỉ số tăng trưởng).
- `du_lieu_gdp_nganh_chi_tiet_2026.csv` giữ riêng số quý III và lũy kế 9 tháng 2026 từ [thông cáo NSO](https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/10/thong-cao-bao-chi-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/). Đây là số ước tính giữa năm; không ghép thành GDP cả năm hay thành mức GDP danh nghĩa cho tiểu ngành.
- Dashboard có ba nút chuyển hướng và ba trang riêng cho từng khu vực. Mỗi trang so sánh quy mô/tỷ trọng GDP hiện hành, tăng trưởng GDP thực, đóng góp điểm phần trăm, thay đổi tỷ trọng 5 năm, và số công bố 2026. Danh mục nguồn nêu kỳ, trường và giới hạn của từng bộ dữ liệu.
- Tăng trưởng thực lấy từ chỉ số NSO `năm trước = 100 − 100`; tăng danh nghĩa được giữ thành cột riêng. Đóng góp GDP thực tính bằng `100 × (VAᵢ,t − VAᵢ,t−1) / GDPₜ₋₁`; bỏ năm 2010 khi mức giá có điểm đổi mốc. Ba kiểm tra đối chiếu GDP danh nghĩa, tỷ trọng 100% và tổng đóng góp thực đều đạt trong lần chạy mới.
- **Giới hạn độ sâu của nguồn:** Bảng GDP năm chỉ công bố nông-lâm-thủy sản như một nhóm gộp; không có giá trị GDP năm riêng cho trồng trọt, chăn nuôi, lâm nghiệp và thủy sản. Bảng cũng không tách GDP chế biến chế tạo thành các ngành nhỏ hơn. Dashboard chỉ hiển thị mức chi tiết NSO thực sự công bố; các bảng IIP hoặc sản lượng vật chất có thể mở rộng phân tích ngành con nhưng là chỉ số sản lượng, không thay cho GDP/giá trị tăng thêm.
- Báo cáo phân tích mới: `phan_tich_gdp_chi_tiet_hoat_dong.md`. Hai CSV GDP chi tiết được thêm vào `snapshot_data.py` và phiên bản ZIP.

## API FastAPI

- `api/main.py` phục vụ toàn bộ dashboard tại một địa chỉ gốc `/`; các mục Tổng quan, EDA, ba khu vực, dữ liệu và dự báo là điều hướng bên trong cùng dashboard. REST API dùng `/api/v1/...`; Swagger UI dùng `/docs`.
- Cài dependencies một lần bằng `python -m pip install -r requirements.txt`, sau đó chạy `./run_fastapi.ps1` trong PowerShell hoặc dùng lệnh `python -m uvicorn api.main:app --host 127.0.0.1 --port 8000`.
- Mở `http://127.0.0.1:8000/` để dùng toàn bộ hệ thống; `http://127.0.0.1:8000/docs` dành cho xem/thử API.
- API có danh mục/đọc dữ liệu, tổng quan vĩ mô, dự báo 2030, so sánh mô hình, GRDP và truy vấn chuyên sâu ba khu vực kinh tế. Hướng dẫn chạy: `FASTAPI_LOCAL.md`.
