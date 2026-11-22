"""Pure deterministic rules for V-MEST dashboard insights."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .insight_config import OVERVIEW_REFERENCE_YEARS

SUPPORTED_INSIGHT_SECTIONS = frozenset({"overview", "gdp-real-structure"})

REAL_GDP_SOURCE = "World Bank WDI"
SECTOR_SOURCE = "NSO/GSO"

_SECTOR_SHARES = (
    ("ty_trong_nong_lam_thuy_san_pct", "nông, lâm, thủy sản"),
    ("ty_trong_cong_nghiep_xay_dung_pct", "công nghiệp và xây dựng"),
    ("ty_trong_dich_vu_pct", "dịch vụ"),
)
_REAL_GDP_SCALE = 1_000_000_000

_STATUS_LABELS = {
    "uoc_tinh": "ước tính",
    "so_bo": "sơ bộ",
    "chinh_thuc": "chính thức",
    "chinh_thuc_theo_bang_nguon": "chính thức theo bảng nguồn",
    "cong_bo_chinh_thuc_nso": "công bố chính thức NSO",
    "uoc_tinh_chinh_thuc": "ước tính chính thức",
    "uoc_tinh_luy_ke_chinh_thuc": "ước tính lũy kế chính thức",
}


def _number(value: Any) -> float | None:
    """Return a finite numeric value; blanks, booleans and invalid values are absent."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _year(value: Any) -> int | None:
    number = _number(value)
    if number is None or not number.is_integer():
        return None
    return int(number)


def _annual_rows(rows: Any, value_columns: tuple[str, ...]) -> dict[int, dict[str, Any]]:
    """Index valid annual rows and omit duplicate years to avoid double counting."""
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return {}

    indexed: dict[int, dict[str, Any]] = {}
    duplicates: set[int] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        year = _year(row.get("nam"))
        if year is None or not any(_number(row.get(column)) is not None for column in value_columns):
            continue
        if year in indexed:
            duplicates.add(year)
        indexed[year] = dict(row)

    for duplicate_year in duplicates:
        indexed.pop(duplicate_year, None)
    return indexed


def _source(data: Mapping[str, Any], key: str, default: str) -> str:
    value = data.get(key)
    return str(value).strip() if value is not None and str(value).strip() else default


def _status_text(row: Mapping[str, Any]) -> str | None:
    value = row.get("trang_thai")
    if value is None or not str(value).strip():
        return None
    raw = str(value).strip()
    return _STATUS_LABELS.get(raw, raw.replace("_", " "))


def _status_clause(row: Mapping[str, Any], source: str) -> str:
    status = _status_text(row)
    if status:
        return f"trạng thái {status}; nguồn {source}"
    return f"nguồn {source}"


def _status_pair_clause(
    current: Mapping[str, Any],
    baseline: Mapping[str, Any],
    current_year: int,
    baseline_year: int,
    source: str,
) -> str:
    current_status = _status_text(current)
    baseline_status = _status_text(baseline)
    if current_status and baseline_status and current_status != baseline_status:
        return (
            f"trạng thái năm {baseline_year} {baseline_status}, "
            f"năm {current_year} {current_status}; nguồn {source}"
        )
    status = current_status or baseline_status
    if status:
        return f"trạng thái {status}; nguồn {source}"
    return f"nguồn {source}"


def format_vi(value: float, digits: int = 2) -> str:
    """Format a finite number with Vietnamese decimal and thousands separators."""
    rounded = round(value, digits)
    if rounded == 0:
        rounded = 0.0
    formatted = f"{abs(rounded):,.{digits}f}"
    integer, fraction = formatted.split(".")
    integer = integer.replace(",", ".")
    sign = "-" if rounded < 0 else ""
    return f"{sign}{integer},{fraction}"


def _format_signed_vi(value: float, digits: int = 2) -> str:
    formatted = format_vi(value, digits)
    return f"+{formatted}" if value > 0 else formatted


def _overview(data: Mapping[str, Any]) -> list[str]:
    growth_by_year = _annual_rows(
        data.get("growth_rows"),
        ("tang_truong_gdp_thuc_pct",),
    )
    if not growth_by_year:
        return []

    source = _source(data, "source", REAL_GDP_SOURCE)
    latest_year = max(growth_by_year)
    latest = growth_by_year[latest_year]
    latest_growth = _number(latest.get("tang_truong_gdp_thuc_pct"))
    if latest_growth is None:
        return []

    qualifier = _status_clause(latest, source)
    statements = [
        f"Tăng trưởng GDP thực năm {latest_year} đạt {format_vi(latest_growth)}% ({qualifier})."
    ]

    reference_years = range(latest_year - OVERVIEW_REFERENCE_YEARS, latest_year)
    if all(year in growth_by_year for year in reference_years):
        reference_values = [
            _number(growth_by_year[year].get("tang_truong_gdp_thuc_pct"))
            for year in reference_years
        ]
        if all(value is not None for value in reference_values):
            average = sum(value for value in reference_values if value is not None) / OVERVIEW_REFERENCE_YEARS
            difference = latest_growth - average
            statements.append(
                f"Tăng trưởng GDP thực bình quân giai đoạn "
                f"{latest_year - OVERVIEW_REFERENCE_YEARS}–{latest_year - 1} "
                f"là {format_vi(average)}%; năm {latest_year} chênh lệch "
                f"{_format_signed_vi(difference)} điểm phần trăm so với mức này "
                f"({qualifier})."
            )

    if len(growth_by_year) >= 2:
        rank = 1
        for year, row in growth_by_year.items():
            if year == latest_year:
                continue
            other_growth = _number(row.get("tang_truong_gdp_thuc_pct"))
            if other_growth is not None and other_growth > latest_growth:
                rank += 1
        first_year = min(growth_by_year)
        last_year = max(growth_by_year)
        count = len(growth_by_year)
        statements.append(
            f"Trong chuỗi {source} giai đoạn {first_year}–{last_year} "
            f"({count} quan sát), tăng trưởng GDP thực năm {latest_year} "
            f"xếp thứ {rank}/{count} tính từ mức cao nhất ({qualifier})."
        )

    return statements


def _gdp_real_structure(data: Mapping[str, Any]) -> list[str]:
    real_by_year = _annual_rows(
        data.get("real_rows"),
        ("gdp_thuc_usd_2015",),
    )
    sector_columns = tuple(column for column, _ in _SECTOR_SHARES)
    sector_by_year = _annual_rows(data.get("sector_rows"), sector_columns)
    statements: list[str] = []

    real_source = _source(data, "real_source", REAL_GDP_SOURCE)
    if real_by_year:
        latest_real_year = max(real_by_year)
        real_row = real_by_year[latest_real_year]
        real_value = _number(real_row.get("gdp_thuc_usd_2015"))
        if real_value is not None:
            statements.append(
                f"GDP thực năm {latest_real_year} đạt "
                f"{format_vi(real_value / _REAL_GDP_SCALE)} tỷ USD "
                f"giá cố định 2015 ({_status_clause(real_row, real_source)})."
            )

    if not sector_by_year:
        return statements

    sector_source = _source(data, "sector_source", SECTOR_SOURCE)
    latest_sector_year = max(sector_by_year)
    latest_sector_row = sector_by_year[latest_sector_year]
    available_shares = [
        (column, label, _number(latest_sector_row.get(column)))
        for column, label in _SECTOR_SHARES
        if _number(latest_sector_row.get(column)) is not None
    ]
    if not available_shares:
        return statements

    top_column, top_label, top_share = max(
        available_shares,
        key=lambda item: item[2] if item[2] is not None else -math.inf,
    )
    baseline_year = latest_sector_year - 5
    baseline_row = sector_by_year.get(baseline_year)
    baseline_share = _number(baseline_row.get(top_column)) if baseline_row else None

    if baseline_row is not None and baseline_share is not None and top_share is not None:
        difference = top_share - baseline_share
        status = _status_pair_clause(
            latest_sector_row,
            baseline_row,
            latest_sector_year,
            baseline_year,
            sector_source,
        )
        statements.append(
            f"Cơ cấu GDP giá hiện hành năm {latest_sector_year} có tỷ trọng cao nhất "
            f"ở khu vực {top_label} ({format_vi(top_share)}%); chênh lệch so với "
            f"năm {baseline_year} là {_format_signed_vi(difference)} điểm phần trăm "
            f"({status})."
        )
    elif top_share is not None:
        status = _status_clause(latest_sector_row, sector_source)
        statements.append(
            f"Cơ cấu GDP giá hiện hành năm {latest_sector_year} có tỷ trọng cao nhất "
            f"ở khu vực {top_label} ({format_vi(top_share)}%) ({status})."
        )

    return statements


def generate_insights(section_id: str, data: Mapping[str, Any]) -> list[str]:
    """Generate deterministic, non-causal insight sentences from supplied rows."""
    if not isinstance(data, Mapping):
        return []
    if section_id == "overview":
        return _overview(data)
    if section_id == "gdp-real-structure":
        return _gdp_real_structure(data)
    raise ValueError(f"Unsupported insight section: {section_id}")
