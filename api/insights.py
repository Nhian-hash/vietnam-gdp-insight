"""Pure deterministic rules for V-MEST dashboard insights."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .insight_config import OVERVIEW_REFERENCE_YEARS

SUPPORTED_INSIGHT_SECTIONS = frozenset({"overview", "gdp-real-structure", "macro", "growth-drivers", "trade"})

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
    "theo_bang_nguon": "theo bảng nguồn",
    "IMF_observed": "quan sát IMF",
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



_CPI_YOY_COLUMN = "cpi_thay_doi_cung_ky_pct"
_CPI_YTD_COLUMN = "cpi_binh_quan_luy_ke_yoy_pct"
_FX_COLUMN = "ty_gia_usd_vnd"
_IIP_COLUMN = "chi_so_iip_toan_nganh_2015_100"

_GDP_EXPENDITURE_COMPONENTS = (
    ("dong_gop_von_co_dinh_diem_pct", "vốn cố định"),
    ("dong_gop_ton_kho_diem_pct", "thay đổi tồn kho"),
    ("dong_gop_tieu_dung_nha_nuoc_diem_pct", "tiêu dùng nhà nước"),
    ("dong_gop_tieu_dung_ho_gia_dinh_diem_pct", "tiêu dùng hộ gia đình"),
    ("dong_gop_can_can_hang_hoa_dich_vu_diem_pct", "cán cân hàng hóa và dịch vụ"),
    ("dong_gop_chenh_lech_thong_ke_diem_pct", "chênh lệch thống kê"),
)


def _month_key(value: Any) -> tuple[int, int] | None:
    """Parse an ISO-like monthly period without assuming a particular day."""
    if value is None:
        return None
    parts = str(value).strip().split("-")
    if len(parts) < 2:
        return None
    try:
        year, month = int(parts[0]), int(parts[1])
    except (TypeError, ValueError):
        return None
    return (year, month) if year > 0 and 1 <= month <= 12 else None


def _monthly_rows(rows: Any, value_columns: tuple[str, ...]) -> dict[tuple[int, int], dict[str, Any]]:
    """Index monthly rows and drop duplicate periods rather than choosing arbitrarily."""
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return {}
    indexed: dict[tuple[int, int], dict[str, Any]] = {}
    duplicates: set[tuple[int, int]] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        period = _month_key(row.get("thoi_gian"))
        if period is None or not any(_number(row.get(column)) is not None for column in value_columns):
            continue
        if period in indexed:
            duplicates.add(period)
        indexed[period] = dict(row)
    for duplicate_period in duplicates:
        indexed.pop(duplicate_period, None)
    return indexed


def _month_label(period: tuple[int, int]) -> str:
    year, month = period
    return f"{month:02d}/{year}"


def _date_label(value: Any) -> str | None:
    period = _month_key(value)
    if period is None:
        return None
    parts = str(value).strip().split("-")
    if len(parts) < 3:
        return f"{period[1]:02d}/{period[0]}"
    try:
        day = int(parts[2][:2])
    except (TypeError, ValueError):
        return f"{period[1]:02d}/{period[0]}"
    return f"{day:02d}/{period[1]:02d}/{period[0]}"


def _macro(data: Mapping[str, Any]) -> list[str]:
    statements: list[str] = []
    cpi_source = _source(data, "cpi_source", "NSO")
    cpi_by_month = _monthly_rows(
        data.get("cpi_rows"),
        (_CPI_YOY_COLUMN, _CPI_YTD_COLUMN),
    )
    if cpi_by_month:
        latest_period = max(cpi_by_month)
        latest = cpi_by_month[latest_period]
        month_label = _month_label(latest_period)
        ytd_value = _number(latest.get(_CPI_YTD_COLUMN))
        yoy_value = _number(latest.get(_CPI_YOY_COLUMN))
        cpi_status = _status_clause(latest, cpi_source)
        release_date = _date_label(latest.get("ngay_cong_bo"))
        release_suffix = f", công bố ngày {release_date}" if release_date else ""
        if ytd_value is not None:
            statements.append(
                f"CPI bình quân lũy kế đến tháng {month_label} tăng "
                f"{format_vi(ytd_value)}% so với cùng kỳ "
                f"({cpi_status}{release_suffix})."
            )
        if yoy_value is not None:
            statements.append(
                f"CPI tháng {month_label} tăng {format_vi(yoy_value)}% "
                f"so với cùng kỳ ({cpi_status}{release_suffix})."
            )

        comparable = [
            (period, row, _number(row.get(_CPI_YOY_COLUMN)))
            for period, row in cpi_by_month.items()
            if _number(row.get(_CPI_YOY_COLUMN)) is not None
        ]
        if len(comparable) >= 2:
            peak_period, peak_row, peak_value = max(comparable, key=lambda item: item[2])
            first_period = min(period for period, _, _ in comparable)
            last_period = max(period for period, _, _ in comparable)
            statements.append(
                f"Trong các tháng có số liệu CPI cùng kỳ từ {_month_label(first_period)} "
                f"đến {_month_label(last_period)}, mức cao nhất là "
                f"{format_vi(peak_value)}% vào tháng {_month_label(peak_period)} "
                f"({_status_clause(peak_row, cpi_source)})."
            )

    fx_source = _source(data, "fx_source", "IMF IFS")
    fx_by_month = _monthly_rows(data.get("fx_rows"), (_FX_COLUMN,))
    if fx_by_month:
        latest_period = max(fx_by_month)
        latest = fx_by_month[latest_period]
        latest_value = _number(latest.get(_FX_COLUMN))
        if latest_value is not None:
            comparison = ""
            previous_year, previous_month = latest_period
            previous_period = (
                (previous_year - 1, 12) if previous_month == 1
                else (previous_year, previous_month - 1)
            )
            previous = fx_by_month.get(previous_period)
            previous_value = _number(previous.get(_FX_COLUMN)) if previous else None
            if previous_value is not None:
                difference = latest_value - previous_value
                percent = difference / previous_value * 100 if previous_value != 0 else None
                comparison = (
                    f", chênh {_format_signed_vi(difference)} VND/USD"
                    f"{f' ({_format_signed_vi(percent)}%)' if percent is not None else ''} "
                    f"so với tháng {_month_label(previous_period)}"
                )
            rate_type = str(latest.get("loai_ty_gia") or "").strip()
            rate_label = "tỷ giá"
            if rate_type == "binh_quan_ky":
                rate_label = "tỷ giá bình quân kỳ"
            statements.append(
                f"{rate_label.capitalize()} đạt {format_vi(latest_value)} VND/USD "
                f"tháng {_month_label(latest_period)}{comparison} "
                f"({_status_clause(latest, fx_source)})."
            )
    return statements


def _growth_drivers(data: Mapping[str, Any]) -> list[str]:
    rows = _annual_rows(
        data.get("contribution_rows"),
        ("tang_truong_gdp_thuc_chi_tieu_pct",)
        + tuple(column for column, _ in _GDP_EXPENDITURE_COMPONENTS),
    )
    if not rows:
        return []
    source = _source(data, "source", "NSO")
    latest_year = max(rows)
    latest = rows[latest_year]
    statements: list[str] = []
    growth = _number(latest.get("tang_truong_gdp_thuc_chi_tieu_pct"))
    status = _status_clause(latest, source)
    if growth is not None:
        statements.append(
            f"Tăng trưởng GDP thực theo phương pháp chi tiêu năm {latest_year} "
            f"đạt {format_vi(growth)}% ({status})."
        )

    components = [
        (column, label, _number(latest.get(column)))
        for column, label in _GDP_EXPENDITURE_COMPONENTS
        if _number(latest.get(column)) is not None
    ]
    positive = [item for item in components if item[2] > 0]
    negative = [item for item in components if item[2] < 0]
    if positive or negative:
        pieces: list[str] = []
        if positive:
            _, label, value = max(positive, key=lambda item: item[2])
            pieces.append(f"đóng góp dương lớn nhất là {label} ({_format_signed_vi(value)} điểm phần trăm)")
        if negative:
            _, label, value = min(negative, key=lambda item: item[2])
            pieces.append(f"đóng góp âm lớn nhất là {label} ({format_vi(value)} điểm phần trăm)")
        if len(pieces) == 2:
            description = f"{pieces[0]} và {pieces[1]}"
        else:
            description = pieces[0]
        statements.append(
            f"Theo bảng phân rã GDP theo chi tiêu năm {latest_year}, {description} "
            f"({_status_clause(latest, source)})."
        )
    return statements


def _trade(data: Mapping[str, Any]) -> list[str]:
    statements: list[str] = []
    trade_source = _source(data, "trade_source", "NSO")
    trade_columns = (
        "kim_ngach_xuat_khau_usd",
        "kim_ngach_nhap_khau_usd",
        "can_can_thuong_mai_usd",
    )
    trade_by_month = _monthly_rows(data.get("trade_rows"), trade_columns)
    if trade_by_month:
        period = max(trade_by_month)
        row = trade_by_month[period]
        parts: list[str] = []
        export_value = _number(row.get("kim_ngach_xuat_khau_usd"))
        import_value = _number(row.get("kim_ngach_nhap_khau_usd"))
        balance_value = _number(row.get("can_can_thuong_mai_usd"))
        if export_value is not None:
            parts.append(f"xuất khẩu {format_vi(export_value / 1_000_000_000)} tỷ USD")
        if import_value is not None:
            parts.append(f"nhập khẩu {format_vi(import_value / 1_000_000_000)} tỷ USD")
        if balance_value is not None:
            balance_label = "thặng dư" if balance_value > 0 else "thâm hụt" if balance_value < 0 else "cân bằng"
            parts.append(f"{balance_label} thương mại {format_vi(abs(balance_value) / 1_000_000_000)} tỷ USD")
        if parts:
            statements.append(
                f"Tháng {_month_label(period)}, {', '.join(parts)} "
                f"({_status_clause(row, trade_source)})."
            )

    iip_source = _source(data, "iip_source", "NSO")
    iip_by_month = _monthly_rows(
        data.get("iip_rows"),
        (_IIP_COLUMN, "tang_truong_mom_pct", "tang_truong_yoy_pct"),
    )
    if iip_by_month:
        period = max(iip_by_month)
        row = iip_by_month[period]
        index_value = _number(row.get(_IIP_COLUMN))
        if index_value is not None:
            details: list[str] = []
            mom_value = _number(row.get("tang_truong_mom_pct"))
            yoy_value = _number(row.get("tang_truong_yoy_pct"))
            if mom_value is not None:
                details.append(f"so với tháng trước { _format_signed_vi(mom_value)}%")
            if yoy_value is not None:
                details.append(f"so với cùng kỳ {_format_signed_vi(yoy_value)}%")
            comparison = f", {', '.join(details)}" if details else ""
            statements.append(
                f"IIP toàn ngành đạt {format_vi(index_value)} điểm (2015=100) "
                f"trong tháng {_month_label(period)}{comparison} "
                f"({_status_clause(row, iip_source)})."
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
    if section_id == "macro":
        return _macro(data)
    if section_id == "growth-drivers":
        return _growth_drivers(data)
    if section_id == "trade":
        return _trade(data)
    raise ValueError(f"Unsupported insight section: {section_id}")
