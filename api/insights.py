"""Pure deterministic rules for V-MEST dashboard insights."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

from .insight_config import OVERVIEW_REFERENCE_YEARS

SUPPORTED_INSIGHT_SECTIONS = frozenset({"overview", "gdp-real-structure", "macro", "growth-drivers", "trade", "agriculture", "industry", "services", "retail-fdi", "regional", "models"})

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
    "uoc_tinh_chinh_thuc": "ước tính chính thức",
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



_SECTOR_SECTION_LABELS = {
    "agriculture": "Nông, lâm, thủy sản",
    "industry": "Công nghiệp và xây dựng",
    "services": "Dịch vụ",
}


def _sector_year(row: Mapping[str, Any]) -> int | None:
    """Read the year prefix used by the NSO quarterly and year-to-date data."""
    period = str(row.get("ky") or "").strip()
    try:
        return int(period[:4])
    except (TypeError, ValueError):
        return None


def _sector_period_order(row: Mapping[str, Any]) -> tuple[int, int]:
    """Sort a sector period by year and quarter/YTD order for deterministic selection."""
    period = str(row.get("ky") or "").strip().upper()
    year = _sector_year(row) or 0
    if "9M" in period:
        return year, 9
    if "Q" in period:
        try:
            return year, int(period.rsplit("Q", 1)[1])
        except (TypeError, ValueError):
            pass
    return year, 0


def _sector_insights(section_id: str, data: Mapping[str, Any]) -> list[str]:
    """Describe official NSO sector growth, contribution shares and fastest sub-sector."""
    area_label = _SECTOR_SECTION_LABELS.get(section_id)
    rows = data.get("sector_rows")
    if area_label is None or not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return []

    sector_rows = [
        dict(row)
        for row in rows
        if isinstance(row, Mapping) and row.get("khu_vuc_ma") == section_id
    ]
    if not sector_rows:
        return []

    source = _source(data, "source", SECTOR_SOURCE)
    statements: list[str] = []
    ytd_rows = [
        row for row in sector_rows
        if row.get("cap_phan_tich") == "9m_broad"
        and _sector_year(row) is not None
        and _number(row.get("tang_truong_gdp_thuc_yoy_pct")) is not None
    ]
    latest_ytd = max(ytd_rows, key=_sector_period_order) if ytd_rows else None

    if latest_ytd is not None:
        period_label = str(latest_ytd.get("ky_hien_thi") or latest_ytd.get("ky") or "").strip()
        growth = _number(latest_ytd.get("tang_truong_gdp_thuc_yoy_pct"))
        gdp_share = _number(latest_ytd.get("ty_trong_gdp_9_thang_pct"))
        contribution_share = _number(latest_ytd.get("ty_trong_dong_gop_tang_truong_pct"))
        details: list[str] = []
        if gdp_share is not None:
            details.append(f"tỷ trọng GDP là {format_vi(gdp_share)}%")
        if contribution_share is not None:
            details.append(
                f"tỷ trọng đóng góp vào mức tăng tổng giá trị tăng thêm "
                f"là {format_vi(contribution_share)}%"
            )
        detail_text = f"; {'; '.join(details)}" if details else ""
        statements.append(
            f"Trong {period_label}, khu vực {area_label} tăng {format_vi(growth)}% "
            f"so với cùng kỳ{detail_text} "
            f"({_status_clause(latest_ytd, source)})."
        )

        subsector_rows = [
            row for row in sector_rows
            if row.get("cap_phan_tich") == "9m_subsector"
            and row.get("ky") == latest_ytd.get("ky")
            and _number(row.get("tang_truong_gdp_thuc_yoy_pct")) is not None
            and str(row.get("hoat_dong_kinh_te") or "").strip()
        ]
        if subsector_rows:
            top = max(
                subsector_rows,
                key=lambda row: (
                    _number(row.get("tang_truong_gdp_thuc_yoy_pct"))
                    if _number(row.get("tang_truong_gdp_thuc_yoy_pct")) is not None
                    else -math.inf
                ),
            )
            top_growth = _number(top.get("tang_truong_gdp_thuc_yoy_pct"))
            activity = str(top.get("hoat_dong_kinh_te")).strip()
            statements.append(
                f"Trong các phân ngành có số liệu của khu vực {area_label} "
                f"trong {period_label}, {activity} có tốc độ tăng cao nhất, "
                f"đạt {format_vi(top_growth)}% so với cùng kỳ "
                f"({_status_clause(top, source)})."
            )

    quarter_rows = [
        row for row in sector_rows
        if row.get("cap_phan_tich") == "q3_broad"
        and _sector_year(row) is not None
        and _number(row.get("tang_truong_gdp_thuc_yoy_pct")) is not None
    ]
    latest_quarter = max(quarter_rows, key=_sector_period_order) if quarter_rows else None
    if latest_quarter is not None:
        period_label = str(latest_quarter.get("ky_hien_thi") or latest_quarter.get("ky") or "").strip()
        growth = _number(latest_quarter.get("tang_truong_gdp_thuc_yoy_pct"))
        contribution_share = _number(latest_quarter.get("ty_trong_dong_gop_tang_truong_pct"))
        contribution_text = (
            f"; tỷ trọng đóng góp vào mức tăng tổng giá trị tăng thêm "
            f"là {format_vi(contribution_share)}%"
            if contribution_share is not None else ""
        )
        statements.append(
            f"Riêng {period_label}, khu vực {area_label} tăng {format_vi(growth)}% "
            f"so với cùng kỳ{contribution_text} "
            f"({_status_clause(latest_quarter, source)})."
        )
    return statements



_REGIONAL_PROVINCE_TYPE = "tinh_thanh_63_truyen_thong"
_REGIONAL_TYPE = "vung_thong_ke"
_REGIONAL_EXPECTED_PROVINCES = 63
_REGIONAL_EXPECTED_REGIONS = 6
_MODEL_LABELS = {
    "Drift_mean_log_change": "Drift",
    "Linear_log_trend": "xu hướng log tuyến tính",
    "Naive_last_value": "Naive",
    "GRU_logGDP": "GRU",
    "LSTM_logGDP": "LSTM",
    "SeasonalDrift": "Seasonal Drift",
    "ETS_DampedAdditive": "ETS xu hướng giảm tốc",
    "LogTrendQuarterDummies": "Log trend + biến giả quý",
    "SeasonalNaive": "Seasonal Naive",
}


def _retail_fdi(data: Mapping[str, Any]) -> list[str]:
    statements: list[str] = []
    retail_source = _source(data, "retail_source", "NSO")
    retail_rows = _monthly_rows(
        data.get("retail_rows"),
        ("tong_muc_ban_le_vnd", "tang_truong_danh_nghia_yoy_pct", "tang_truong_thuc_yoy_luy_ke_pct"),
    )
    if retail_rows:
        period = max(retail_rows)
        row = retail_rows[period]
        total = _number(row.get("tong_muc_ban_le_vnd"))
        nominal_yoy = _number(row.get("tang_truong_danh_nghia_yoy_pct"))
        real_ytd = _number(row.get("tang_truong_thuc_yoy_luy_ke_pct"))
        if total is not None:
            details: list[str] = []
            if nominal_yoy is not None:
                details.append(f"tăng danh nghĩa so với cùng kỳ {_format_signed_vi(nominal_yoy)}%")
            if real_ytd is not None:
                details.append(f"tăng thực lũy kế {_format_signed_vi(real_ytd)}%")
            detail_text = f"; {'; '.join(details)}" if details else ""
            statements.append(
                f"Tháng {_month_label(period)}, tổng mức bán lẻ đạt "
                f"{format_vi(total / 1_000_000_000_000)} nghìn tỷ VND giá hiện hành"
                f"{detail_text} ({_status_clause(row, retail_source)})."
            )

    fdi_source = _source(data, "fdi_source", "NSO")
    fdi_rows = _monthly_rows(
        data.get("fdi_rows"),
        (
            "von_fdi_dang_ky_tong_hop_usd",
            "von_fdi_thuc_hien_luy_ke_usd",
            "tang_truong_dang_ky_yoy_pct",
            "tang_truong_thuc_hien_yoy_pct",
        ),
    )
    if fdi_rows:
        period = max(fdi_rows)
        row = fdi_rows[period]
        registered = _number(row.get("von_fdi_dang_ky_tong_hop_usd"))
        realized = _number(row.get("von_fdi_thuc_hien_luy_ke_usd"))
        registered_growth = _number(row.get("tang_truong_dang_ky_yoy_pct"))
        realized_growth = _number(row.get("tang_truong_thuc_hien_yoy_pct"))
        date_label = _date_label(row.get("thoi_gian")) or _month_label(period)
        period_name = str(row.get("ky_bao_cao") or "").strip()
        if period_name == "9_thang":
            period_name = f"lũy kế 9 tháng/{period[0]}"
        elif period_name:
            period_name = f"lũy kế {period_name}/{period[0]}"
        else:
            period_name = f"lũy kế đến {date_label}"
        parts: list[str] = []
        if registered is not None:
            registered_text = f"vốn FDI đăng ký tổng hợp {format_vi(registered / 1_000_000_000)} tỷ USD"
            if registered_growth is not None:
                registered_text += f" ({_format_signed_vi(registered_growth)}% so với cùng kỳ)"
            parts.append(registered_text)
        if realized is not None:
            realized_text = f"vốn FDI thực hiện {format_vi(realized / 1_000_000_000)} tỷ USD"
            if realized_growth is not None:
                realized_text += f" ({_format_signed_vi(realized_growth)}% so với cùng kỳ)"
            parts.append(realized_text)
        if parts:
            statements.append(
                f"Tại ngày {date_label}, {period_name} ghi nhận "
                f"{' và '.join(parts)} ({_status_clause(row, fdi_source)})."
            )
    return statements


def _regional(data: Mapping[str, Any]) -> list[str]:
    rows = data.get("grdp_rows")
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return []

    provinces_by_year: dict[int, list[dict[str, Any]]] = {}
    regions_by_year: dict[int, list[dict[str, Any]]] = {}
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        year = _year(item.get("nam"))
        value = _number(item.get("quy_mo_grdp_vnd"))
        if year is None or value is None:
            continue
        row = dict(item)
        if row.get("loai_dia_ban") == _REGIONAL_PROVINCE_TYPE and str(row.get("ma_tinh") or "").strip():
            provinces_by_year.setdefault(year, []).append(row)
        elif row.get("loai_dia_ban") == _REGIONAL_TYPE and str(row.get("ma_vung_kinh_te") or "").strip():
            regions_by_year.setdefault(year, []).append(row)

    complete_years: list[int] = []
    for year in set(provinces_by_year).intersection(regions_by_year):
        province_rows = provinces_by_year[year]
        region_rows = regions_by_year[year]
        province_codes = {str(row.get("ma_tinh")).strip() for row in province_rows}
        region_codes = {str(row.get("ma_vung_kinh_te")).strip() for row in region_rows}
        if (
            len(province_rows) == _REGIONAL_EXPECTED_PROVINCES
            and len(province_codes) == _REGIONAL_EXPECTED_PROVINCES
            and len(region_rows) == _REGIONAL_EXPECTED_REGIONS
            and len(region_codes) == _REGIONAL_EXPECTED_REGIONS
        ):
            complete_years.append(year)
    if not complete_years:
        return []

    year = max(complete_years)
    source = _source(data, "source", "NSO PXWeb")
    statements: list[str] = []
    province_rows = provinces_by_year[year]
    province_total = sum(
        value for row in province_rows
        if (value := _number(row.get("quy_mo_grdp_vnd"))) is not None
    )
    ranked_provinces = sorted(
        province_rows,
        key=lambda row: _number(row.get("quy_mo_grdp_vnd")) or -math.inf,
        reverse=True,
    )
    if province_total > 0 and len(ranked_provinces) >= 5:
        top_three = ranked_provinces[:3]
        top_five = ranked_provinces[:5]
        top_statuses = {_status_text(row) for row in top_five if _status_text(row)}
        status_clause = (
            f"trạng thái {_status_text(top_five[0])}; nguồn {source}"
            if len(top_statuses) <= 1 and top_statuses
            else _status_clause(top_five[0], source)
        )
        leaders = ", ".join(
            f"{str(row.get('ten_tinh')).strip()} "
            f"{format_vi((_number(row.get('quy_mo_grdp_vnd')) or 0) / 1000)}"
            for row in top_three
        )
        top_five_share = sum(
            _number(row.get("quy_mo_grdp_vnd")) or 0
            for row in top_five
        ) / province_total * 100
        statements.append(
            f"Năm {year}, ba tỉnh/thành có quy mô GRDP cao nhất trong phạm vi 63 đơn vị "
            f"truyền thống là {leaders} nghìn tỷ VND; nhóm 5 đơn vị đầu chiếm "
            f"{format_vi(top_five_share)}% tổng quy mô GRDP tỉnh/thành "
            f"({status_clause})."
        )

    region_rows = regions_by_year[year]
    region_total = sum(
        value for row in region_rows
        if (value := _number(row.get("quy_mo_grdp_vnd"))) is not None
    )
    if region_total > 0 and len(region_rows) == _REGIONAL_EXPECTED_REGIONS:
        top_region = max(
            region_rows,
            key=lambda row: _number(row.get("quy_mo_grdp_vnd")) or -math.inf,
        )
        region_value = _number(top_region.get("quy_mo_grdp_vnd"))
        if region_value is not None:
            statements.append(
                f"Trong 6 vùng thống kê năm {year}, {str(top_region.get('ten_tinh')).strip()} "
                f"có tỷ trọng quy mô GRDP lớn nhất, đạt "
                f"{format_vi(region_value / region_total * 100)}% tổng quy mô của 6 vùng "
                f"({_status_clause(top_region, source)})."
            )
    return statements


def _training_model_winners(
    rows: Any,
    horizon_column: str,
    period_start_column: str,
    period_end_column: str,
) -> list[dict[str, Any]]:
    """Find the lowest-MAPE model at each tested horizon without recomputing scores."""
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
        return []
    groups: dict[int, list[dict[str, Any]]] = {}
    for item in rows:
        if not isinstance(item, Mapping):
            continue
        horizon = _year(item.get(horizon_column))
        mape = _number(item.get("MAPE_pct"))
        if horizon is None or horizon <= 0 or mape is None:
            continue
        groups.setdefault(horizon, []).append(dict(item))

    winners: list[dict[str, Any]] = []
    for horizon, candidates in sorted(groups.items()):
        model_names = [str(row.get("mo_hinh") or "").strip() for row in candidates]
        if len(model_names) != len(set(model_names)):
            continue
        winner = min(candidates, key=lambda row: (_number(row.get("MAPE_pct")) if _number(row.get("MAPE_pct")) is not None else math.inf))
        winner["horizon"] = horizon
        winner["period_start"] = winner.get(period_start_column)
        winner["period_end"] = winner.get(period_end_column)
        winners.append(winner)
    return winners


def _training_lab(data: Mapping[str, Any]) -> list[str]:
    statements: list[str] = []
    source = _source(data, "source", "V-MEST backtest artifacts")
    annual = _training_model_winners(
        data.get("annual_rows"),
        "chan_troi_nam",
        "nam_dau",
        "nam_cuoi",
    )
    if annual:
        details = "; ".join(
            f"{row['horizon']} năm: "
            f"{_MODEL_LABELS.get(str(row.get('mo_hinh')), str(row.get('mo_hinh')))} "
            f"{format_vi(_number(row.get('MAPE_pct')) or 0)}% "
            f"(n={row.get('so_diem_kiem_thu')}; {row.get('period_start')}–{row.get('period_end')})"
            for row in annual
        )
        statements.append(
            f"Backtest GDP năm theo expanding-window có MAPE thấp nhất theo chân trời là "
            f"{details} (kết quả kiểm định ngoài mẫu; nguồn {source})."
        )

    quarterly = _training_model_winners(
        data.get("quarterly_rows"),
        "chan_troi_quy",
        "ky_dau",
        "ky_cuoi",
    )
    if quarterly:
        details = "; ".join(
            f"{row['horizon']} quý: "
            f"{_MODEL_LABELS.get(str(row.get('mo_hinh')), str(row.get('mo_hinh')))} "
            f"{format_vi(_number(row.get('MAPE_pct')) or 0)}% "
            f"(n={row.get('so_diem_kiem_thu')}; {row.get('period_start')}–{row.get('period_end')})"
            for row in quarterly
        )
        statements.append(
            f"Backtest GDP quý theo expanding-window có MAPE thấp nhất theo chân trời là "
            f"{details} (kết quả kiểm định ngoài mẫu; nguồn {source})."
        )

    annual_rows = data.get("annual_rows")
    one_year = [
        row for row in annual_rows
        if isinstance(row, Mapping) and _number(row.get("chan_troi_nam")) == 1
    ] if isinstance(annual_rows, Sequence) and not isinstance(annual_rows, (str, bytes)) else []
    neural_by_model = {
        str(row.get("mo_hinh")): row
        for row in one_year
        if str(row.get("mo_hinh")) in {"GRU_logGDP", "LSTM_logGDP"}
        and _number(row.get("MAPE_pct")) is not None
    }
    drift = next(
        (
            row for row in one_year
            if str(row.get("mo_hinh")) == "Drift_mean_log_change"
            and _number(row.get("MAPE_pct")) is not None
        ),
        None,
    )
    if len(neural_by_model) == 2 and drift is not None:
        gru = _number(neural_by_model["GRU_logGDP"].get("MAPE_pct"))
        lstm = _number(neural_by_model["LSTM_logGDP"].get("MAPE_pct"))
        drift_mape = _number(drift.get("MAPE_pct"))
        start = drift.get("nam_dau")
        end = drift.get("nam_cuoi")
        sample_count = drift.get("so_diem_kiem_thu")
        if gru is not None and lstm is not None and drift_mape is not None:
            statements.append(
                f"Ở chân trời 1 năm, MAPE của GRU là {format_vi(gru)}% và LSTM là "
                f"{format_vi(lstm)}%, so với Drift {format_vi(drift_mape)}% "
                f"({sample_count} origin kiểm thử, {start}–{end}); hai mạng nơ-ron "
                f"chỉ mang tính thăm dò với chuỗi 41 quan sát GDP năm 1985–2025 "
                f"(kết quả backtest; nguồn {source})."
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
    if section_id in _SECTOR_SECTION_LABELS:
        return _sector_insights(section_id, data)
    if section_id == "retail-fdi":
        return _retail_fdi(data)
    if section_id == "regional":
        return _regional(data)
    if section_id == "models":
        return _training_lab(data)
    raise ValueError(f"Unsupported insight section: {section_id}")
