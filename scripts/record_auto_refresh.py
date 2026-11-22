"""Record the last successful auto-refresh that changed source data."""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from data_paths import data_path


def latest(name: str, period_column: str) -> str | None:
    path = data_path(name)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        values = [str(row.get(period_column, "")).strip() for row in rows]
    values = [value for value in values if value]
    return max(values) if values else None


def latest_record(name: str) -> dict[str, str] | None:
    path = data_path(name)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    return max(rows, key=lambda row: str(row.get("thoi_gian") or ""), default=None)


def main() -> None:
    cpi_release = latest_record("du_lieu_cpi_cong_bo_thang.csv")
    manifest = {
        "status": "ok",
        "last_successful_data_update_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "check_interval_hours": 6,
        "latest_periods": {
            "cpi_monthly_index": latest("du_lieu_lam_phat_cpi.csv", "thoi_gian"),
            "cpi_official_release": cpi_release.get("thoi_gian") if cpi_release else None,
        },
        "schedule": "GitHub Actions kiểm tra mỗi 6 giờ; có thể chạy thủ công.",
        "policy": "Chỉ phát hành khi tải nguồn thành công, kiểm tra dữ liệu đạt và nội dung nguồn thay đổi. Không tự tạo quan sát khi nguồn chưa công bố.",
        "sources": {
            "World Bank WDI": {
                "url": "https://api.worldbank.org/v2/country/VNM/indicator/NY.GDP.MKTP.KD?date=1985:2026&format=json&per_page=1000",
                "latest_annual_gdp_year": latest("GDP_Vietnam_Annual.csv", "Year"),
                "latest_real_gdp_year": latest("du_lieu_gdp_thuc_va_tang_truong.csv", "nam"),
                "datasets": ["GDP_Vietnam_Annual.csv", "du_lieu_gdp_quoc_gia_co_cau_nganh.csv", "du_lieu_gdp_thuc_va_tang_truong.csv"],
            },
            "NSO PXWeb CPI index": {
                "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2011.%20CPI/E%2011.%20CPI__Px_E_11/E11.07.px/",
                "latest_observation": latest("du_lieu_lam_phat_cpi.csv", "thoi_gian"),
                "note": "Mức chỉ số PXWeb có thể đổi gốc; không dùng tỷ lệ qua điểm gãy gốc.",
                "datasets": ["du_lieu_lam_phat_cpi.csv", "du_lieu_cpi_phan_tich_thang.csv"],
            },
            "NSO official monthly CPI releases": {
                "url": "https://www.nso.gov.vn/en/cpi/",
                "latest_observation": cpi_release.get("thoi_gian") if cpi_release else None,
                "latest_report_url": cpi_release.get("nguon") if cpi_release else None,
                "note": "Tỷ lệ CPI tháng được sao chép nguyên trạng từ thông cáo NSO; tách khỏi mức chỉ số.",
                "datasets": ["du_lieu_cpi_cong_bo_thang.csv"],
            },
            "IMF Exchange Rates": {
                "url": "https://api.imf.org/external/sdmx/3.0/data/dataflow/IMF.STA/ER/+/VNM.XDC_USD.PA_RT.M?startPeriod=1980-01&endPeriod=2026-12&format=jsondata",
                "latest_observation": latest("du_lieu_ty_gia_usd_vnd.csv", "thoi_gian"),
                "datasets": ["du_lieu_ty_gia_usd_vnd.csv", "du_lieu_fx_bien_dong_thang.csv"],
            },
            "NSO PXWeb annual tables and World Bank commodity prices": {
                "method": "Tải lại các bảng PXWeb và bảng giá hàng hóa World Bank trong mỗi lần kiểm tra.",
                "datasets": ["dữ liệu NSO theo năm", "du_lieu_gia_hang_hoa_quoc_te.csv"],
            },
        },
        "not_yet_automated": [
            "Tăng trưởng GDP quý từ thông cáo báo chí NSO",
            "Thương mại, bán lẻ, IIP và FDI tháng lấy từ workbook/thông cáo NSO theo kỳ",
        ],
        "deployment": "Khi có thay đổi nguồn hợp lệ, GitHub lưu phiên bản mới và Render tự triển khai theo commit.",
    }
    target = ROOT / "auto_refresh_manifest.json"
    target.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Đã ghi trạng thái đồng bộ: {target}")


if __name__ == "__main__":
    main()

