"""Refresh official CPI values embedded in the offline dashboard after it is built."""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_paths import data_path


def rows(name: str) -> list[dict[str, str]]:
    with data_path(name).open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def replace_once(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Expected one dashboard marker {old!r}, found {count}")
    return text.replace(old, new, 1)


def as_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"true", "1", "yes"}


def main() -> None:
    reports = rows("du_lieu_cpi_cong_bo_thang.csv")
    if not reports:
        raise RuntimeError("No official NSO CPI monthly release rows are available")
    latest = max(reports, key=lambda row: row.get("thoi_gian", ""))
    period = latest["thoi_gian"][:7]
    month = int(latest.get("thang") or period[5:7])
    year = int(latest.get("nam") or period[:4])
    ytd_raw = latest.get("cpi_binh_quan_luy_ke_yoy_pct", "")
    has_ytd_average = bool(ytd_raw)
    published_rate = float(ytd_raw if has_ytd_average else latest["cpi_thay_doi_cung_ky_pct"])
    index_rows = rows("du_lieu_cpi_phan_tich_thang.csv")
    if not index_rows:
        raise RuntimeError("CPI source index series is empty")
    index_period = max(row.get("thoi_gian", "") for row in index_rows)[:7]

    # Re-index only within each detected source-base regime and break the line
    # at the base discontinuity; never show a fake fall caused by rebasing.
    regime_first: dict[str, float] = {}
    cpi_month_values: dict[str, float | None] = {}
    for row in index_rows:
        value = float(row["chi_so_cpi"])
        regime = row.get("che_do_goc_chi_so", "0")
        regime_first.setdefault(regime, value)
        month_key = row["thoi_gian"][:7]
        cpi_month_values[month_key] = None if as_bool(row.get("diem_gay_do_goc")) else value / regime_first[regime] * 100

    dashboard_path = ROOT / "dashboard.html"
    html = dashboard_path.read_text(encoding="utf-8")
    match = re.search(r"const D=(.*?);\s*const \$=id=>", html, flags=re.DOTALL)
    if not match:
        raise RuntimeError("Could not locate embedded dashboard data object")
    data = json.loads(match.group(1))
    data.setdefault("latest", {})
    data["latest"]["cpiPublishedRate"] = published_rate
    data["latest"]["cpiDate"] = period
    data["latest"]["cpiIndexDate"] = index_period
    data["latest"]["cpiMonthCount"] = month
    data["latest"].pop("cpiNineMonth", None)

    for item in data.get("monthlyMacro", []):
        item["cpi100"] = cpi_month_values.get(item.get("month"), None)

    catalog = [item for item in data.get("catalog", []) if item.get("dataset") != "CPI / lạm phát"]
    catalog.extend([
        {
            "dataset": "Chỉ số CPI theo gốc PXWeb",
            "file": "du_lieu_cpi_phan_tich_thang.csv",
            "source": "NSO PXWeb E11.07",
            "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2011.%20CPI/E%2011.%20CPI__Px_E_11/E11.07.px/",
            "frequency": "Tháng",
            "coverage": f"{min(row['thoi_gian'] for row in index_rows)[:7]}–{index_period}",
            "fields": "thoi_gian · chi_so_cpi · MoM/YoY chỉ trong cùng gốc",
            "note": "Mức chỉ số quan sát; biến động bị để trống qua điểm gãy gốc, không dùng để tính tỷ lệ năm qua đổi gốc.",
        },
        {
            "dataset": "Tỷ lệ CPI do NSO công bố",
            "file": "du_lieu_cpi_cong_bo_thang.csv",
            "source": "Cục Thống kê Việt Nam (NSO)",
            "url": latest.get("nguon", "https://www.nso.gov.vn/en/cpi/"),
            "frequency": "Tháng",
            "coverage": f"{min(row['thoi_gian'] for row in reports)[:7]}–{period}",
            "fields": "CPI MoM · so với tháng 12 · YoY · bình quân lũy kế · trạng thái",
            "note": "Sao chép tỷ lệ do thông cáo NSO công bố; không phải mức chỉ số CPI.",
        },
    ])
    data["catalog"] = catalog

    replacement = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    html = html[:match.start(1)] + replacement + html[match.end(1):]
    html = replace_once(
        html,
        'D.latest.cpiNineMonth',
        'D.latest.cpiPublishedRate',
    )
    old_label = "CPI bình quân 9 tháng"
    new_label = f"CPI bình quân {month} tháng" if has_ytd_average else f"CPI cùng kỳ tháng {month}"
    html = replace_once(html, old_label, new_label)
    old_period_text = "D.latest.cpiDate+' · CPI tái tạo'"
    new_period_text = "D.latest.cpiDate+' · NSO chính thức; mức chỉ số đến '+D.latest.cpiIndexDate"
    html = replace_once(html, old_period_text, new_period_text)
    old_note = "Chỉ số CPI 2026 được tái tạo từ tỷ lệ lũy kế chính thức làm tròn."
    new_note = "Tỷ lệ CPI tháng lấy nguyên trạng từ thông cáo NSO; chỉ số mức PXWeb được giữ riêng."
    html = replace_once(html, old_note, new_note)
    html = replace_once(
        html,
        "CPI (01/2020=100)",
        "CPI (gốc nguồn riêng; ngắt tại điểm gãy)",
    )
    html = replace_once(
        html,
        "Chỉ số tháng 1/2020 = 100 · trục chung để so diễn biến, không so trực tiếp mức giá với tỷ giá",
        "CPI được chuẩn hóa riêng theo từng gốc nguồn và ngắt tại điểm gãy; tỷ giá vẫn lấy 01/2020 = 100",
    )
    html = replace_once(
        html,
        "CPI và chỉ số tỷ giá đã quy về 100 từ tháng 1 năm 2020",
        "CPI chuẩn hóa theo từng gốc nguồn và tỷ giá VND/USD",
    )
    dashboard_path.write_text(html, encoding="utf-8")
    print(f"Dashboard CPI updated from NSO release {period}; index source ends {index_period}.")


if __name__ == "__main__":
    main()
