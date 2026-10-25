# Chạy API V-MEST với FastAPI

Ứng dụng cung cấp REST API đọc các CSV đã phát hành cùng phiên bản dữ liệu, phục vụ dashboard tại `/` và tài liệu tương tác tại `/docs`. API không huấn luyện lại mô hình theo từng yêu cầu; endpoint dự báo đọc các kịch bản đã tạo và đánh giá trong pipeline hiện hữu.

## Chạy trên máy cá nhân

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn api.main:app --reload
```

Mở `http://127.0.0.1:8000/` để xem dashboard, `http://127.0.0.1:8000/docs` để gọi thử API, hoặc `http://127.0.0.1:8000/api/v1/health` để kiểm tra service.

## Triển khai trên Render

`render.yaml` khai báo web service Python. Repository đưa lên GitHub cần chứa mã nguồn API, `dashboard.html`, `assets/`, `data/`, `data_paths.py`, `requirements.txt` và các manifest dữ liệu; không cần tạo gói ZIP riêng. Đăng nhập Render bằng GitHub, chọn **New → Blueprint**, kết nối repository chứa toàn bộ hệ thống, chọn nhánh `main`, kiểm tra cấu hình trong `render.yaml` rồi xác nhận tạo service. Nếu hệ thống nằm trong thư mục con của repository, đặt thư mục đó làm **Root Directory**. Render sẽ cấp domain `onrender.com`; sau khi deploy, kiểm tra `/`, `/api/v1/health` và `/docs` trên domain đó.

Render cần quyền đọc repository để theo dõi commit. Với gói Free, dịch vụ ngủ sau 15 phút không có lượt truy cập và lượt mở đầu tiên có thể mất khoảng một phút để khởi động. Gói Free phù hợp cho demo/khóa luận; nếu cần truy cập liên tục, cần chọn gói không ngủ khi nhàn rỗi. GitHub Pages chỉ chạy trang tĩnh; FastAPI cần chạy trên web service. Cấu hình hiện tại để FastAPI phục vụ dashboard tại `/`, API tại `/api/v1/...` và Swagger tại `/docs` cùng một domain.

`CORS_ORIGINS` mặc định cho phép `https://nhian-hash.github.io` và có thể mở rộng bằng cách đặt các origin cách nhau bằng dấu phẩy trong cấu hình Render.

## API endpoints

| Endpoint | Mục đích |
| --- | --- |
| `GET /api/v1/health` | Tình trạng service, phiên bản dữ liệu và mốc cập nhật |
| `GET /api/v1/metadata` | Manifest dữ liệu và phương pháp phân tích |
| `GET /api/v1/datasets` | Danh mục CSV, trường, tần suất và nguồn |
| `GET /api/v1/datasets/{file_name}` | Đọc dữ liệu phân trang; hỗ trợ `offset`, `limit`, `from_year`, `to_year` |
| `GET /api/v1/summary` | GDP năm, tăng trưởng quý và CPI mới nhất |
| `GET /api/v1/forecast` | Kịch bản GDP thực 2026–2030; có thể lọc `model`, `from_year`, `to_year` |
| `GET /api/v1/model-comparison` | So sánh sai số backtest giữa các mô hình |
| `GET /api/v1/grdp?year=2025&level=region` | Xếp hạng GRDP tỉnh hoặc vùng |
| `GET /docs` | Swagger UI tương tác |

GDP danh nghĩa, GDP thực, tốc độ tăng cùng kỳ và dự báo giữ đơn vị/phạm vi riêng. Dự báo là kịch bản mô hình, không phải công bố chính thức.
