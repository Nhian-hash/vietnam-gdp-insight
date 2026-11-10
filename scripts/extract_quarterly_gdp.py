"""Extract official quarterly GDP levels from the NSDP national-accounts workbook.

The workbook publishes a historical constant-2010-price series through 2025-Q4
and a newer constant-2020-price series from 2025-Q1. Keep these price bases in
separate files; do not splice or scale them into one observed series.
"""
from __future__ import annotations

import json
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_paths import data_path

SOURCE_FILE = data_path("GDP_VNM.xlsx")
SOURCE_URL = "https://nsdp.nso.gov.vn/GSO-chung/Tu%E1%BA%A5n%20Anh/excel%20chung/GDP_VNM.xlsx"
INDICATOR = "NGDP_R_PA_XDC"


def get_sheet_observations(sheet_name: str, base_year: int, min_year: int,
                           max_year: int, output_column: str) -> pd.DataFrame:
    workbook = load_workbook(SOURCE_FILE, read_only=True, data_only=True)
    if sheet_name not in workbook.sheetnames:
        raise RuntimeError(f"Thiếu sheet {sheet_name!r} trong workbook NSDP")
    worksheet = workbook[sheet_name]
    # The source workbook carries formatting out to thousands of empty columns.
    # Its actual period headers end within the first 100 columns.
    header_row = next(worksheet.iter_rows(min_row=10, max_row=10, min_col=1,
                                          max_col=120, values_only=True))
    indicator_row = None
    for row in worksheet.iter_rows(min_row=11, max_row=worksheet.max_row,
                                   min_col=1, max_col=120, values_only=True):
        if row[0] == INDICATOR:
            indicator_row = row
            break
    if indicator_row is None:
        raise RuntimeError(f"Không tìm thấy chỉ tiêu {INDICATOR} ở sheet {sheet_name}")

    unit_scale = worksheet.cell(row=6, column=2).value
    comment = worksheet.cell(row=7, column=2).value
    if unit_scale != 9:
        raise RuntimeError(f"Đơn vị/scale không như dự kiến: UNIT_MULT={unit_scale!r}")

    records = []
    for index, period in enumerate(header_row):
        if not isinstance(period, str):
            continue
        match = re.fullmatch(r"(\d{4})-Q([1-4])", period.strip())
        if not match:
            continue
        year, quarter = map(int, match.groups())
        value = indicator_row[index]
        if min_year <= year <= max_year and value is not None:
            records.append({
                "thoi_gian": period,
                "nam": year,
                "quy": quarter,
                output_column: float(value),
                "don_vi": "tỷ VND",
                "nam_goc_gia": base_year,
                "trang_thai_so_lieu": "Đã công bố (theo trạng thái workbook NSDP)",
                "ma_chi_tieu_nguon": INDICATOR,
                "sheet_nguon": sheet_name,
                "ghi_chu": "Mức GDP thực quý; giữ riêng theo năm gốc giá, không phải GDP tháng. "
                           "Workbook ghi trạng thái: " + str(comment).replace("\n", " "),
            })
    workbook.close()
    frame = pd.DataFrame(records)
    if frame.empty:
        raise RuntimeError(f"Không trích được quan sát quý từ {sheet_name}")
    frame = frame.sort_values(["nam", "quy"]).reset_index(drop=True)
    if frame["thoi_gian"].duplicated().any():
        raise RuntimeError(f"Trùng kỳ quý trong sheet {sheet_name}")
    return frame


def extract_annual_reference() -> pd.DataFrame:
    workbook = load_workbook(SOURCE_FILE, read_only=True, data_only=True)
    sheet_name = "Dataset_A_2004-2025"
    if sheet_name not in workbook.sheetnames:
        raise RuntimeError(f"Thiếu sheet {sheet_name!r} trong workbook NSDP")
    worksheet = workbook[sheet_name]
    header = next(worksheet.iter_rows(min_row=9, max_row=9, min_col=1,
                                     max_col=50, values_only=True))
    indicator_row = None
    for row in worksheet.iter_rows(min_row=10, max_row=worksheet.max_row,
                                   min_col=1, max_col=50, values_only=True):
        if row[0] == "NGDP_R_XDC":
            indicator_row = row
            break
    if indicator_row is None:
        raise RuntimeError("Không tìm thấy chỉ tiêu GDP năm NGDP_R_XDC")
    values = {}
    for index, year in enumerate(header):
        if isinstance(year, (int, float)) and 2010 <= int(year) <= 2025:
            value = indicator_row[index]
            if value is not None:
                values[int(year)] = float(value)
    workbook.close()
    return pd.DataFrame([{"nam": year, "gdp_thuc_nam_ty_vnd_gia_2010": value}
                         for year, value in sorted(values.items())])


def main() -> None:
    if not SOURCE_FILE.is_file():
        raise FileNotFoundError(f"Chưa có workbook nguồn: {SOURCE_FILE}")

    historical = get_sheet_observations(
        "Dataset_Q", 2010, 2010, 2025, "gdp_thuc_ty_vnd_gia_2010")
    latest = get_sheet_observations(
        "Dataset_QI.2026", 2020, 2025, 2026, "gdp_thuc_ty_vnd_gia_2020")
    historical_path = data_path("du_lieu_gdp_quy_muc_thuc_gia_2010.csv", for_write=True)
    latest_path = data_path("du_lieu_gdp_quy_muc_thuc_gia_2020.csv", for_write=True)
    historical.to_csv(historical_path, index=False, encoding="utf-8-sig", float_format="%.8f")
    latest.to_csv(latest_path, index=False, encoding="utf-8-sig", float_format="%.8f")

    annual = extract_annual_reference()
    quarterly_sum = historical.groupby("nam", as_index=False)["gdp_thuc_ty_vnd_gia_2010"].sum()
    quarterly_sum = quarterly_sum.rename(columns={"gdp_thuc_ty_vnd_gia_2010": "tong_4_quy_ty_vnd_gia_2010"})
    reconciliation = annual.merge(quarterly_sum, on="nam", how="inner")
    reconciliation["chenh_lech_ty_vnd"] = reconciliation["tong_4_quy_ty_vnd_gia_2010"] - reconciliation["gdp_thuc_nam_ty_vnd_gia_2010"]
    reconciliation["chenh_lech_pct"] = reconciliation["chenh_lech_ty_vnd"] / reconciliation["gdp_thuc_nam_ty_vnd_gia_2010"] * 100
    reconciliation["trang_thai_doi_chieu"] = reconciliation["chenh_lech_pct"].abs().le(0.01).map({True: "Khớp trong sai số làm tròn 0,01%", False: "Cần rà soát"})
    reconciliation["ghi_chu"] = "Tổng bốn mức GDP quý giá so sánh 2010 đối chiếu với mức GDP năm cùng workbook NSDP."
    reconciliation_path = data_path("doi_chieu_gdp_thuc_quy_va_nam.csv", for_write=True)
    reconciliation.to_csv(reconciliation_path, index=False, encoding="utf-8-sig", float_format="%.8f")

    source_manifest_path = data_path("quarterly_gdp_source_manifest.json", for_write=True)
    raw_manifest_path = data_path("quarterly_gdp_download_manifest.json")
    if raw_manifest_path.exists():
        raw_manifest = json.loads(raw_manifest_path.read_text(encoding="utf-8"))
    else:
        # Preserve a transparent fallback for workbooks that were initially
        # downloaded before the refresh script began recording HTTP metadata.
        stat = SOURCE_FILE.stat()
        retrieved_at = datetime.fromtimestamp(stat.st_mtime, timezone.utc).replace(
            microsecond=0).isoformat().replace("+00:00", "Z")
        digest = hashlib.sha256(SOURCE_FILE.read_bytes()).hexdigest()
        raw_manifest = {
            "retrieved_at_utc": retrieved_at,
            "retrieval_timestamp_source": "filesystem_last_modified_fallback",
            "source": "National Summary Data Page (NSDP), Cục Thống kê Việt Nam",
            "source_url": SOURCE_URL,
            "file": SOURCE_FILE.name,
            "bytes": stat.st_size,
            "sha256": digest,
            "note": "Thời điểm tải ban đầu không có log HTTP; timestamp dùng thời gian sửa đổi tệp cục bộ làm mốc xấp xỉ.",
        }
        raw_manifest_path.write_text(json.dumps(raw_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    manifest = {
        "source": "National Summary Data Page (NSDP), Cục Thống kê Việt Nam",
        "source_url": SOURCE_URL,
        "workbook": "data/nso/raw/quarterly/GDP_VNM.xlsx",
        "retrieved_at_utc": raw_manifest.get("retrieved_at_utc"),
        "retrieval_timestamp_source": raw_manifest.get("retrieval_timestamp_source", "download_manifest"),
        "indicator_code": INDICATOR,
        "indicator_name": "Real Gross Domestic Product, production approach",
        "historical_series": {
            "sheet": "Dataset_Q", "frequency": "quarterly", "price_base_year": 2010,
            "unit": "billion VND", "period_start": historical["thoi_gian"].iloc[0],
            "period_end": historical["thoi_gian"].iloc[-1], "observations": int(len(historical)),
            "status": "Workbook metadata says Published",
        },
        "newer_price_base_series": {
            "sheet": "Dataset_QI.2026", "frequency": "quarterly", "price_base_year": 2020,
            "unit": "billion VND", "period_start": latest["thoi_gian"].iloc[0],
            "period_end": latest["thoi_gian"].iloc[-1], "observations": int(len(latest)),
            "status": "Workbook metadata says Published",
        },
        "reconciliation": {
            "method": "Sum four quarterly real GDP levels at constant 2010 prices; compare with annual real GDP at constant 2010 prices in same workbook.",
            "years": int(len(reconciliation)),
            "max_absolute_difference_pct": float(reconciliation["chenh_lech_pct"].abs().max()),
            "tolerance_pct": 0.01,
            "all_within_tolerance": bool(reconciliation["chenh_lech_pct"].abs().le(0.01).all()),
        },
        "limitations": [
            "Keep the constant-2010 and constant-2020 series separate; this build does not chain-link or splice price bases.",
            "The newer-base file covers overlapping quarters 2025-Q1 to 2025-Q3 and 2026-Q1 to 2026-Q3; 2025-Q4 is unavailable there.",
            "The workbook identifies the series as published but does not provide historical release-vintage values per observation.",
        ],
        "outputs": [
            "data/nso/processed/du_lieu_gdp_quy_muc_thuc_gia_2010.csv",
            "data/nso/processed/du_lieu_gdp_quy_muc_thuc_gia_2020.csv",
            "data/derived/quality/doi_chieu_gdp_thuc_quy_va_nam.csv",
        ],
    }
    source_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"GDP quarterly constant-2010: {len(historical)} observations, {historical['thoi_gian'].iloc[0]}–{historical['thoi_gian'].iloc[-1]}")
    print(f"GDP quarterly constant-2020: {len(latest)} observations, {latest['thoi_gian'].iloc[0]}–{latest['thoi_gian'].iloc[-1]}")
    print(f"Annual reconciliation: {len(reconciliation)} years; max absolute difference {reconciliation['chenh_lech_pct'].abs().max():.6f}%")


if __name__ == "__main__":
    main()
