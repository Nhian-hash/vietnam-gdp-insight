"""Fail-closed checks for scheduled upstream data refreshes."""
from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_paths import data_path


def read_rows(name: str) -> list[dict[str, str]]:
    path = data_path(name)
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def unique_nonempty(rows: list[dict[str, str]], key: str, label: str) -> list[str]:
    values = [row.get(key, "").strip() for row in rows]
    require(bool(values) and all(values), f"{label}: thiếu giá trị khóa {key}")
    require(len(values) == len(set(values)), f"{label}: có khóa trùng ở {key}")
    return values


def main() -> None:
    annual = read_rows("GDP_Vietnam_Annual.csv")
    annual_years = unique_nonempty(annual, "Year", "World Bank GDP danh nghĩa")
    require(annual_years == sorted(annual_years), "World Bank GDP danh nghĩa chưa được sắp xếp theo năm")
    require("2025" in annual_years, "World Bank GDP danh nghĩa không còn quan sát năm 2025")
    for row in annual:
        value = float(row["GDP_USD"])
        require(value > 0, f"GDP danh nghĩa không dương tại năm {row['Year']}")

    real = read_rows("du_lieu_gdp_thuc_va_tang_truong.csv")
    real_years = unique_nonempty(real, "nam", "World Bank GDP thực")
    require("2025" in real_years, "World Bank GDP thực không còn quan sát năm 2025")
    require(all(float(row["gdp_thuc_usd_2015"]) > 0 for row in real), "GDP thực có giá trị không dương")

    cpi = read_rows("du_lieu_lam_phat_cpi.csv")
    cpi_dates = unique_nonempty(cpi, "thoi_gian", "NSO CPI")
    require(len(cpi) >= 60, "NSO CPI trả về ít hơn 60 quan sát tháng")
    require(cpi_dates == sorted(cpi_dates), "NSO CPI chưa được sắp xếp theo thời gian")
    require(all(float(row["chi_so_cpi"]) > 0 for row in cpi), "NSO CPI có giá trị không dương")
    require(cpi_dates[-1][:7] <= date.today().strftime("%Y-%m"), "NSO CPI có kỳ quan sát nằm trong tương lai")

    fx = read_rows("du_lieu_ty_gia_usd_vnd.csv")
    fx_dates = unique_nonempty(fx, "thoi_gian", "IMF tỷ giá")
    require(len(fx) >= 120, "IMF tỷ giá trả về ít hơn 120 tháng")
    require(fx_dates == sorted(fx_dates), "IMF tỷ giá chưa được sắp xếp theo thời gian")
    require(all(float(row["ty_gia_usd_vnd"]) > 0 for row in fx), "IMF tỷ giá có giá trị không dương")
    require(fx_dates[-1][:7] <= date.today().strftime("%Y-%m"), "IMF tỷ giá có kỳ quan sát nằm trong tương lai")

    for name in ("kiem_tra_chat_luong_du_lieu.csv", "kiem_tra_du_lieu_mo_rong.csv"):
        try:
            checks = read_rows(name)
        except FileNotFoundError:
            continue
        status_column = "ket_qua" if checks and "ket_qua" in checks[0] else "trang_thai"
        failures = [row for row in checks if row.get(status_column, "").strip().lower() not in {"dat", "ok", "pass"}]
        require(not failures, f"{name}: {len(failures)} kiểm tra chưa đạt; dừng phát hành để rà soát")

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print(
        "Nguồn đạt kiểm tra: "
        f"GDP World Bank đến {annual_years[-1]}, CPI NSO đến {cpi_dates[-1][:7]}, "
        f"tỷ giá IMF đến {fx_dates[-1][:7]}."
    )


if __name__ == "__main__":
    main()

