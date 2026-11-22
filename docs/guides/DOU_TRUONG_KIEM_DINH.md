# Đấu trường kiểm định dự báo theo mốc lịch sử

## Mục tiêu và chuỗi GDP

Đấu trường dùng biến mục tiêu GDP thực Việt Nam theo năm trong `data/world_bank/processed/du_lieu_gdp_thuc_va_tang_truong.csv`. Chuỗi có 41 quan sát từ 1985 đến 2025, đơn vị USD cố định năm 2015, chỉ tiêu World Bank WDI `NY.GDP.MKTP.KD`. Không nội suy thêm quan sát để backtest.

## Cách tái tạo artifact

Chạy trên môi trường phân tích cục bộ có các thư viện trong `requirements-analysis.txt`:

```powershell
python scripts/build_backtest_arena.py
python scripts/build_dashboard.py
```

Lệnh đầu tạo `data/derived/forecast/backtest_arena.json`. Lệnh thứ hai dựng `dashboard.html`. FastAPI chỉ đọc JSON đã có, không huấn luyện mô hình trong request.

## Thiết kế kiểm định

- Cutoff lịch sử: 2008, 2019 và 2021. Tại từng cutoff, tập huấn luyện kết thúc ở năm cutoff; các năm sau là holdout nếu nguồn có số thực tế.
- Cutoff `LATEST` dùng toàn bộ chuỗi đến 2025 và dự báo 2026–2030; chưa có giá trị thực tế nên không tính điểm xếp hạng.
- Hỗ trợ chân trời 1–5 năm. Từng cutoff huấn luyện lại Naive, Drift, SARIMAX(1,1,0), GRU và LSTM.
- GRU/LSTM chuẩn hóa log GDP riêng trong cửa sổ huấn luyện của cutoff. Không dùng ngẫu nhiên hoán đổi quan sát, không fit scaler trên holdout.
- MAE, RMSE và MAPE tính trên các năm holdout có GDP thực tế. MAPE chỉ được tính khi giá trị thực dương.
- Khoảng 95% của SARIMAX lấy trên log GDP rồi biến đổi ngược; empirical coverage được báo cùng số điểm kiểm thử `n`.

## Endpoint

`GET /api/v1/backtest-arena?cutoff_year=2019&horizon=3`

`cutoff_year` nhận `2008`, `2019`, `2021` hoặc `LATEST`; `horizon` nhận số nguyên 1–5. Response có chuỗi huấn luyện, số thực tế holdout, dự báo từng mô hình, metrics, nguồn và ghi chú giới hạn.

## Giới hạn diễn giải

GDP năm chỉ có 41 quan sát; các cửa sổ ở cutoff sớm để lại ít mẫu cho GRU/LSTM. Các kịch bản cutoff là phép thử lịch sử hữu hạn. Tỷ lệ bao phủ 95% tính trên tối đa năm điểm, vì vậy chỉ mang tính mô tả và không chứng minh độ bao phủ dài hạn.

