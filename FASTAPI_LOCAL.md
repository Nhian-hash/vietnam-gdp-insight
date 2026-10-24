# FastAPI cục bộ cho GDP Insight

FastAPI chạy cùng dashboard và bộ CSV trong thư mục này. GitHub chỉ lưu bản sao mã nguồn; dashboard/API đang chạy trên máy tại địa chỉ localhost.

## Khởi động

Mở PowerShell tại thư mục `outputs/Vietnam-GDP-Refresh` rồi chạy:

```powershell
python -m pip install -r requirements.txt
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Giữ cửa sổ terminal mở khi dùng hệ thống. Nhấn `Ctrl+C` trong cửa sổ đó để dừng API.

## Trang web và tài liệu API

- Dashboard: `http://127.0.0.1:8000/`
- Swagger UI: `http://127.0.0.1:8000/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`
- Health: `http://127.0.0.1:8000/api/v1/health`

## Endpoint chính

| Endpoint | Chức năng |
| --- | --- |
| `GET /api/v1/metadata` | Phiên bản dữ liệu và manifest phân tích |
| `GET /api/v1/datasets` | Danh mục CSV, schema, nguồn và số dòng |
| `GET /api/v1/datasets/{file_name}` | Đọc dữ liệu có phân trang và lọc năm |
| `GET /api/v1/summary` | GDP năm, tăng trưởng quý và CPI mới nhất |
| `GET /api/v1/sectors` | Danh sách ba khu vực, phạm vi năm và hoạt động thành phần |
| `GET /api/v1/sectors/{sector_code}` | Chuỗi từng hoạt động; lọc bằng `from_year`, `to_year`, `activity` |
| `GET /api/v1/forecast` | Kịch bản GDP thực 2026–2030; lọc theo mô hình/chân trời |
| `GET /api/v1/model-comparison` | So sánh sai số dự báo trên backtest |
| `GET /api/v1/grdp?year=2025&level=region` | So sánh GRDP vùng hoặc tỉnh |

Ba mã khu vực là `agriculture`, `industry`, `services`. Dữ liệu GDP năm và bản tin quý III/9 tháng 2026 được trả riêng; không suy ra quy mô GDP năm từ số tăng trưởng lũy kế. Các mức dự báo là kịch bản mô hình, không phải số liệu chính thức.

## Dùng thử trong trình duyệt

Ví dụ:

- `http://127.0.0.1:8000/api/v1/sectors`
- `http://127.0.0.1:8000/api/v1/sectors/industry?from_year=2015&to_year=2025`
- `http://127.0.0.1:8000/api/v1/forecast?model=Drift_mean_log_change`

