# GDP Insight Việt Nam

Dashboard phân tích GDP Việt Nam theo năm, quý và tháng, gồm ba khu vực kinh tế, động lực tăng trưởng, ngoại thương, IIP, bán lẻ, FDI, GRDP địa phương và kịch bản dự báo đến 2030.

## Truy cập dashboard

`index.html` là dashboard tĩnh, tự chứa dữ liệu. Sau khi bật GitHub Pages với nguồn GitHub Actions trong phần Settings → Pages, workflow sẽ triển khai website khi có commit lên nhánh `main`. URL dự kiến: `https://nhian-hash.github.io/vietnam-gdp-insight/`.

## Mã và dữ liệu

Tải `source_code_and_data.zip` để lấy mã phân tích, CSV, nguồn lưu trữ, manifest phiên bản và dashboard. Có thể dựng lại dashboard bằng Python với `pandas`, sau đó chạy `python build_dashboard.py`.

## API FastAPI

Repository có backend FastAPI tại `api/main.py`. Chạy cục bộ bằng `pip install -r requirements.txt` rồi `uvicorn api.main:app --reload`; dashboard nằm ở `/`, tài liệu API ở `/docs` và endpoint sức khỏe ở `/api/v1/health`.

`render.yaml` cấu hình triển khai API như một web service Python trên Render. GitHub Pages tiếp tục phục vụ dashboard tĩnh; FastAPI cần được triển khai riêng theo hướng dẫn `FASTAPI_DEPLOY.md`. Sau khi Render cấp domain, API có các endpoint dữ liệu GDP, CPI, GRDP, so sánh mô hình và dự báo 2030.

## Cách đọc

- Dự báo 2026–2030 là kịch bản mô hình, không phải số liệu chính thức.
- Số liệu thực, danh nghĩa, quan sát và ước tính được giữ riêng theo nguồn.
- Nguồn, tần suất và trạng thái dữ liệu được ghi trong `data_version_manifest.json`, thư mục `sources/` và danh mục trong dashboard.
- Gói công khai không chứa DOCX, PDF, PBIX hoặc notebook cá nhân.

