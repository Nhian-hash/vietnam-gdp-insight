# Chạy hệ thống GDP Insight bằng FastAPI

FastAPI phục vụ dashboard và REST API trên cùng một máy chủ. Toàn bộ mục dashboard (Tổng quan, EDA, ba khu vực kinh tế, GRDP, dự báo và quản lý dữ liệu) dùng chung một địa chỉ: `http://127.0.0.1:8501/`. Các mục được chuyển bên trong giao diện, không cần mở từng địa chỉ riêng.

GitHub chỉ lưu mã nguồn và dữ liệu. FastAPI đang chạy cục bộ trên máy tính; GitHub Pages không chạy backend Python.

## Khởi động

Mở PowerShell tại thư mục `outputs/Vietnam-GDP-Refresh`, cài thư viện lần đầu và chạy:

```powershell
python -m pip install -r requirements.txt
./run_fastapi.ps1
```

Hoặc chạy trực tiếp:

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8501
```

Giữ cửa sổ PowerShell mở khi sử dụng. Nhấn `Ctrl+C` trong cửa sổ đó để dừng máy chủ. Nếu cổng 8501 đã được ứng dụng khác sử dụng, hãy dừng ứng dụng đó trước khi chạy FastAPI.

## Địa chỉ hệ thống

- Dashboard đầy đủ: `http://127.0.0.1:8501/`
- Swagger UI để xem/thử REST API: `http://127.0.0.1:8501/docs`
- OpenAPI JSON: `http://127.0.0.1:8501/openapi.json`
- Health: `http://127.0.0.1:8501/api/v1/health`

## Endpoint dữ liệu

| Endpoint | Chức năng |
| --- | --- |
| `GET /api/v1/metadata` | Phiên bản dữ liệu và manifest phân tích |
| `GET /api/v1/datasets` | Danh mục CSV, schema, nguồn và số dòng |
| `GET /api/v1/datasets/{file_name}` | Đọc dữ liệu có phân trang và lọc năm |
| `GET /api/v1/summary` | GDP năm, tăng trưởng quý và CPI mới nhất |
| `GET /api/v1/sectors` | Danh sách ba khu vực và hoạt động thành phần |
| `GET /api/v1/sectors/{sector_code}` | Dữ liệu ngành; lọc bằng `from_year`, `to_year`, `activity` |
| `GET /api/v1/forecast` | Kịch bản GDP thực 2026–2030 |
| `GET /api/v1/model-comparison` | So sánh sai số dự báo trên backtest |
| `GET /api/v1/grdp?year=2025&level=region` | So sánh GRDP vùng hoặc tỉnh |

Ví dụ: `http://127.0.0.1:8501/api/v1/sectors/industry?from_year=2015&to_year=2025`.

Ba mã khu vực là `agriculture`, `industry`, `services`. Dữ liệu 2026 theo quý/9 tháng được trả riêng, không xem là GDP cả năm. Dự báo đến 2030 là kịch bản mô hình, không phải số liệu chính thức.
