"""FastAPI service for the Vietnam GDP Insight dashboard and data."""
from __future__ import annotations

import csv
import json
import math
import os
import re
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse


ROOT = Path(__file__).resolve().parents[1]
API_PREFIX = "/api/v1"
VERSION_FILE = ROOT / "data_version_manifest.json"
ANALYSIS_FILE = ROOT / "analysis_manifest.json"

DATASET_INFO: dict[str, dict[str, str]] = {
    "du_lieu_gdp_tong_hop.csv": {
        "title": "GDP Việt Nam tổng hợp",
        "frequency": "annual",
        "source": "World Bank WDI và NSO",
        "description": "GDP danh nghĩa và GDP thực theo năm; giữ rõ khác biệt về giá hiện hành và giá cố định.",
    },
    "du_lieu_gdp_thuc_va_tang_truong.csv": {
        "title": "GDP thực và tăng trưởng",
        "frequency": "annual",
        "source": "World Bank WDI",
        "description": "GDP thực USD giá cố định 2015 và tăng trưởng GDP thực quan sát.",
    },
    "du_lieu_gdp_nganh_chi_tiet.csv": {
        "title": "GDP theo hoạt động kinh tế",
        "frequency": "annual",
        "source": "NSO PXWeb E03.04-07",
        "description": "Giá trị hiện hành, giá cố định, tỷ trọng và chỉ số tăng trưởng theo ngành công bố.",
    },
    "du_lieu_gdp_nganh_chi_tiet_2026.csv": {
        "title": "GDP ngành quý III và 9 tháng 2026",
        "frequency": "quarterly / year-to-date",
        "source": "Thông cáo NSO quý III và 9 tháng 2026",
        "description": "Số ước tính quý và lũy kế; không phải GDP cả năm hay quy mô GDP danh nghĩa.",
    },
    "du_lieu_gdp_nganh_chi_tiet.csv": {
        "title": "GDP theo 3 khu vực và hoạt động kinh tế",
        "frequency": "annual",
        "source": "NSO PXWeb E03.04-07",
        "description": "Giá trị GDP danh nghĩa, giá trị GDP thực theo bảng nguồn, tăng trưởng và đóng góp; các cấp hoạt động được giữ nguyên để tránh cộng trùng.",
    },
    "du_lieu_tang_truong_gdp_quy.csv": {
        "title": "Tăng trưởng GDP theo quý",
        "frequency": "quarterly",
        "source": "NSO",
        "description": "Tăng trưởng so với cùng kỳ; không chuyển thành mức GDP quý.",
    },
    "du_lieu_du_bao_gdp_thuc_den_2030.csv": {
        "title": "Dự báo GDP thực đến 2030",
        "frequency": "annual forecast",
        "source": "Mô hình nội bộ, huấn luyện trên World Bank WDI đến 2025",
        "description": "Kịch bản ngoài mẫu của các mô hình; không phải số liệu hay dự báo chính thức.",
    },
    "du_lieu_grdp_63_tinh_thanh.csv": {
        "title": "GRDP địa phương và vùng",
        "frequency": "annual",
        "source": "NSO PXWeb; ước tính theo GRDP/người và dân số bình quân",
        "description": "63 đơn vị địa lý truyền thống và sáu vùng thống kê; không cộng tỉnh và vùng cùng lúc.",
    },
    "du_lieu_chi_so_kinh_te_hang_nam.csv": {
        "title": "Chỉ số kinh tế vĩ mô hằng năm",
        "frequency": "annual",
        "source": "NSO, World Bank, IMF và FRED; xem manifest nguồn",
        "description": "GDP, thương mại, CPI, FDI, bán lẻ và tỷ giá; có cột trạng thái và đơn vị.",
    },
    "du_lieu_cpi_phan_tich_thang.csv": {
        "title": "CPI và lạm phát theo tháng",
        "frequency": "monthly",
        "source": "NSO PXWeb; số 2026 tái tạo từ mức tăng CPI đã công bố",
        "description": "Chỉ số CPI và biến động tháng/năm; cờ trạng thái phân biệt quan sát và giá trị tái tạo.",
    },
    "du_lieu_xuat_nhap_khau_thang_2026.csv": {
        "title": "Xuất nhập khẩu năm 2026",
        "frequency": "monthly",
        "source": "NSO",
        "description": "Số sơ bộ tháng 1–9/2026; giữ nguyên trạng thái nguồn.",
    },
    "du_lieu_san_xuat_iip_thang_2026.csv": {
        "title": "Chỉ số sản xuất công nghiệp năm 2026",
        "frequency": "monthly",
        "source": "NSO",
        "description": "IIP theo chỉ số gốc 2015=100; không đồng nhất với giá trị tăng thêm ngành.",
    },
}

SECTORS: dict[str, str] = {
    "agriculture": "Nông, lâm, thủy sản",
    "industry": "Công nghiệp và xây dựng",
    "services": "Dịch vụ",
}


def read_manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def csv_path(file_name: str) -> Path:
    """Return a safe, root-level CSV path from the public dataset bundle."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.csv", file_name):
        raise HTTPException(status_code=404, detail="Không tìm thấy bộ dữ liệu.")
    path = (ROOT / file_name).resolve()
    if path.parent != ROOT.resolve() or not path.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy bộ dữ liệu.")
    return path


def number_or_text(value: str | None) -> Any:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    if re.fullmatch(r"-?(0|[1-9]\d*)", text):
        try:
            return int(text)
        except ValueError:
            return text
    try:
        numeric = float(text)
    except ValueError:
        return text
    return numeric if math.isfinite(numeric) else None


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, Any]]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            columns = list(reader.fieldnames or [])
            rows = [
                {key: number_or_text(value) for key, value in row.items() if key is not None}
                for row in reader
            ]
    except (OSError, csv.Error) as exc:
        raise HTTPException(status_code=500, detail=f"Không đọc được {path.name}.") from exc
    return columns, rows


def year_of(row: dict[str, Any]) -> int | None:
    for key in ("nam", "year", "nam_du_bao"):
        value = row.get(key)
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            return int(value)
    for key in ("thoi_gian", "date", "period", "time"):
        value = row.get(key)
        if isinstance(value, str):
            match = re.match(r"(\d{4})", value)
            if match:
                return int(match.group(1))
    return None


def latest_row(file_name: str, year_field: str = "nam") -> dict[str, Any] | None:
    _, rows = read_csv_rows(csv_path(file_name))
    valid = [row for row in rows if year_of({**row, "nam": row.get(year_field)}) is not None]
    return max(valid, key=lambda row: year_of({**row, "nam": row.get(year_field)}) or 0) if valid else None


def data_cutoff() -> dict[str, Any]:
    return read_manifest(VERSION_FILE).get("data_cutoff", {})


def dataset_description(file_name: str, path: Path) -> dict[str, Any]:
    columns, rows = read_csv_rows(path)
    info = DATASET_INFO.get(file_name, {})
    return {
        "file": file_name,
        "title": info.get("title", file_name.removesuffix(".csv").replace("_", " ")),
        "frequency": info.get("frequency", "xem trường thời gian trong dữ liệu"),
        "source": info.get("source", "Xem manifest và thư mục sources/ trong mã nguồn."),
        "description": info.get("description", "Dữ liệu thực tế được giữ kèm đơn vị, trạng thái hoặc ghi chú nguồn khi có."),
        "columns": columns,
        "rows": len(rows),
        "bytes": path.stat().st_size,
    }


app = FastAPI(
    title="Vietnam GDP Insight API",
    description=(
        "API đọc dữ liệu GDP Việt Nam, các chỉ báo vĩ mô, GRDP địa phương, "
        "so sánh mô hình và kịch bản dự báo đến 2030. Số dự báo là kịch bản mô hình, không phải số liệu chính thức."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

default_origins = [
    "https://nhian-hash.github.io",
    "http://localhost:8000",
    "http://localhost:8502",
    "http://127.0.0.1:8000",
    "http://127.0.0.1:8502",
]
configured_origins = [value.strip() for value in os.getenv("CORS_ORIGINS", "").split(",") if value.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(set(default_origins + configured_origins)),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


@app.get("/", include_in_schema=False)
def dashboard() -> FileResponse:
    """Serve the same dashboard UI from the API service origin."""
    page = ROOT / "index.html"
    if not page.is_file():
        page = ROOT / "dashboard.html"
    if not page.is_file():
        raise HTTPException(status_code=404, detail="Chưa có tệp dashboard.html hoặc index.html.")
    return FileResponse(page, media_type="text/html")


@app.get(f"{API_PREFIX}/health", tags=["Hệ thống"])
def health() -> dict[str, Any]:
    version = read_manifest(VERSION_FILE)
    return {
        "status": "ok",
        "service": "Vietnam GDP Insight API",
        "api_version": app.version,
        "data_version": version.get("version_id"),
        "data_cutoff": version.get("data_cutoff", {}),
    }


@app.get(f"{API_PREFIX}/metadata", tags=["Hệ thống"])
def metadata() -> dict[str, Any]:
    return {
        "data_version": read_manifest(VERSION_FILE),
        "analysis": read_manifest(ANALYSIS_FILE),
        "forecast_note": "Các giá trị 2026–2030 là kịch bản mô hình ngoài mẫu, không phải số liệu chính thức.",
    }


@app.get(f"{API_PREFIX}/datasets", tags=["Dữ liệu"])
def list_datasets() -> dict[str, Any]:
    files = sorted(ROOT.glob("*.csv"), key=lambda path: path.name.casefold())
    return {
        "data_version": read_manifest(VERSION_FILE).get("version_id"),
        "data_cutoff": data_cutoff(),
        "count": len(files),
        "datasets": [dataset_description(path.name, path) for path in files],
    }


@app.get(f"{API_PREFIX}/datasets/{{file_name}}", tags=["Dữ liệu"])
def get_dataset(
    file_name: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(1000, ge=1, le=10000),
    from_year: int | None = Query(None, ge=1900, le=2200),
    to_year: int | None = Query(None, ge=1900, le=2200),
) -> dict[str, Any]:
    if from_year is not None and to_year is not None and from_year > to_year:
        raise HTTPException(status_code=422, detail="from_year phải nhỏ hơn hoặc bằng to_year.")
    path = csv_path(file_name)
    columns, rows = read_csv_rows(path)
    if from_year is not None or to_year is not None:
        def in_range(row: dict[str, Any]) -> bool:
            year = year_of(row)
            if year is None:
                return False
            return (from_year is None or year >= from_year) and (to_year is None or year <= to_year)
        rows = [row for row in rows if in_range(row)]
    total = len(rows)
    return {
        "dataset": dataset_description(file_name, path),
        "data_cutoff": data_cutoff(),
        "offset": offset,
        "limit": limit,
        "total_rows": total,
        "rows": rows[offset:offset + limit],
    }


@app.get(f"{API_PREFIX}/summary", tags=["Phân tích"])
def summary() -> dict[str, Any]:
    annual = latest_row("du_lieu_gdp_tong_hop.csv")
    real = latest_row("du_lieu_gdp_thuc_va_tang_truong.csv")
    _, quarter_rows = read_csv_rows(csv_path("du_lieu_tang_truong_gdp_quy.csv"))
    quarterly = max(quarter_rows, key=lambda row: str(row.get("thoi_gian") or ""), default=None)
    _, cpi_rows = read_csv_rows(csv_path("du_lieu_cpi_phan_tich_thang.csv"))
    cpi = max(cpi_rows, key=lambda row: str(row.get("thoi_gian") or ""), default=None)
    return {
        "data_cutoff": data_cutoff(),
        "latest_annual_gdp": {
            "year": annual.get("nam") if annual else None,
            "nominal_gdp_usd": annual.get("gdp_danh_nghia_usd") if annual else None,
            "real_gdp_usd_2015": real.get("gdp_thuc_usd_2015") if real else None,
            "real_growth_percent": real.get("tang_truong_gdp_thuc_pct") if real else None,
            "nominal_unit": "USD current prices",
            "real_unit": "USD constant 2015 prices",
        },
        "latest_quarter": {
            "period": quarterly.get("thoi_gian") if quarterly else None,
            "growth_yoy_percent": quarterly.get("tang_truong_gdp_so_voi_cung_ky_pct") if quarterly else None,
            "status": quarterly.get("trang_thai") if quarterly else None,
        },
        "latest_cpi": {
            "period": cpi.get("thoi_gian") if cpi else None,
            "index": cpi.get("chi_so_cpi") if cpi else None,
            "inflation_yoy_percent": cpi.get("tang_cpi_yoy_pct") if cpi else None,
            "status": cpi.get("trang_thai_chi_so") if cpi else None,
        },
        "forecast_note": "Dự báo đến 2030 là kịch bản mô hình, không phải số liệu chính thức.",
    }


@app.get(f"{API_PREFIX}/forecast", tags=["Dự báo"])
def forecast(
    model: str | None = None,
    from_year: int = Query(2026, ge=2026, le=2030),
    to_year: int = Query(2030, ge=2026, le=2030),
) -> dict[str, Any]:
    if from_year > to_year:
        raise HTTPException(status_code=422, detail="from_year phải nhỏ hơn hoặc bằng to_year.")
    _, rows = read_csv_rows(csv_path("du_lieu_du_bao_gdp_thuc_den_2030.csv"))
    available_models = sorted({str(row.get("mo_hinh")) for row in rows if row.get("mo_hinh")})
    if model is not None and model not in available_models:
        raise HTTPException(status_code=422, detail={"message": "Mô hình không tồn tại.", "available_models": available_models})
    selected = [
        row for row in rows
        if isinstance(row.get("nam_du_bao"), int)
        and from_year <= row["nam_du_bao"] <= to_year
        and (model is None or row.get("mo_hinh") == model)
    ]
    selected.sort(key=lambda row: (row["nam_du_bao"], str(row.get("mo_hinh"))))
    return {
        "target": "annual real GDP, constant 2015 USD",
        "methodology": "Expanding-window rolling-origin backtests; model projection is not official data.",
        "data_cutoff": data_cutoff(),
        "available_models": available_models,
        "model": model,
        "from_year": from_year,
        "to_year": to_year,
        "count": len(selected),
        "rows": selected,
    }


@app.get(f"{API_PREFIX}/model-comparison", tags=["So sánh"])
def model_comparison() -> dict[str, Any]:
    file_name = "so_sanh_hieu_qua_mo_hinh_du_bao.csv"
    columns, rows = read_csv_rows(csv_path(file_name))
    rows.sort(key=lambda row: float(row.get("MAPE_pct") or math.inf))
    return {"metric": "MAPE_pct", "columns": columns, "count": len(rows), "rows": rows}


@app.get(f"{API_PREFIX}/grdp", tags=["So sánh"])
def regional_grdp(
    year: int = Query(2025, ge=2018, le=2025),
    level: str = Query("region", pattern="^(region|province)$"),
) -> dict[str, Any]:
    file_name = "du_lieu_grdp_63_tinh_thanh.csv"
    _, rows = read_csv_rows(csv_path(file_name))
    geography_type = "vung_thong_ke" if level == "region" else "tinh_thanh_63_truyen_thong"
    selected = [row for row in rows if row.get("nam") == year and row.get("loai_dia_ban") == geography_type]
    selected.sort(key=lambda row: float(row.get("quy_mo_grdp_vnd") or 0), reverse=True)
    return {
        "year": year,
        "level": level,
        "count": len(selected),
        "unit": "billion VND, current prices",
        "note": "Không cộng GRDP cấp tỉnh và cấp vùng trong cùng một tổng.",
        "rows": selected,
    }


@app.get(f"{API_PREFIX}/sectors", tags=["Ngành kinh tế"])
def list_sectors() -> dict[str, Any]:
    """Summarize the three GDP sectors without mixing annual and partial-year values."""
    _, annual_rows = read_csv_rows(csv_path("du_lieu_gdp_nganh_chi_tiet.csv"))
    _, partial_rows = read_csv_rows(csv_path("du_lieu_gdp_nganh_chi_tiet_2026.csv"))
    sectors = []
    for code, title in SECTORS.items():
        rows = [row for row in annual_rows if row.get("khu_vuc_ma") == code]
        years = sorted({row["nam"] for row in rows if isinstance(row.get("nam"), int)})
        activities = sorted({str(row["hoat_dong_kinh_te"]) for row in rows if row.get("hoat_dong_kinh_te")})
        latest_partial_periods = sorted({
            str(row["ky"]) for row in partial_rows
            if row.get("khu_vuc_ma") == code and row.get("ky")
        })
        sectors.append({
            "code": code,
            "title": title,
            "annual_from": years[0] if years else None,
            "annual_to": years[-1] if years else None,
            "activity_count": len(activities),
            "activities": activities,
            "partial_periods": latest_partial_periods,
        })
    return {
        "count": len(sectors),
        "data_cutoff": data_cutoff(),
        "sectors": sectors,
        "note": "GDP 2026 quý III/9 tháng là số ước tính theo kỳ, không phải quy mô GDP cả năm.",
    }


@app.get(f"{API_PREFIX}/sectors/{{sector_code}}", tags=["Ngành kinh tế"])
def sector_detail(
    sector_code: str,
    from_year: int = Query(2005, ge=1980, le=2200),
    to_year: int = Query(2025, ge=1980, le=2200),
    activity: str | None = Query(None, min_length=1, max_length=160),
) -> dict[str, Any]:
    """Return published annual sector/activity rows and separately labeled 2026 releases."""
    code = sector_code.strip().lower()
    if code not in SECTORS:
        raise HTTPException(
            status_code=404,
            detail={"message": "Mã khu vực không hợp lệ.", "available_sectors": list(SECTORS)},
        )
    if from_year > to_year:
        raise HTTPException(status_code=422, detail="from_year phải nhỏ hơn hoặc bằng to_year.")

    _, all_annual_rows = read_csv_rows(csv_path("du_lieu_gdp_nganh_chi_tiet.csv"))
    sector_rows = [
        row for row in all_annual_rows
        if row.get("khu_vuc_ma") == code
        and isinstance(row.get("nam"), int)
        and from_year <= row["nam"] <= to_year
    ]
    all_activities = sorted({
        str(row["hoat_dong_kinh_te"]) for row in all_annual_rows
        if row.get("khu_vuc_ma") == code and row.get("hoat_dong_kinh_te")
    })
    if activity is not None:
        selected_activity = activity.strip()
        if selected_activity not in all_activities:
            raise HTTPException(
                status_code=422,
                detail={"message": "Hoạt động kinh tế không thuộc khu vực này.", "available_activities": all_activities},
            )
        sector_rows = [row for row in sector_rows if row.get("hoat_dong_kinh_te") == selected_activity]

    _, all_partial_rows = read_csv_rows(csv_path("du_lieu_gdp_nganh_chi_tiet_2026.csv"))
    partial_rows = [
        row for row in all_partial_rows
        if row.get("khu_vuc_ma") == code
        and (activity is None or row.get("hoat_dong_kinh_te") == activity.strip())
    ]
    sector_rows.sort(key=lambda row: (row["nam"], str(row.get("hoat_dong_kinh_te"))))
    partial_rows.sort(key=lambda row: (str(row.get("ky")), str(row.get("hoat_dong_kinh_te"))))
    return {
        "sector_code": code,
        "sector_title": SECTORS[code],
        "activity_filter": activity.strip() if activity else None,
        "annual_period": {"from_year": from_year, "to_year": to_year},
        "annual_count": len(sector_rows),
        "annual_rows": sector_rows,
        "partial_2026_count": len(partial_rows),
        "partial_2026_rows": partial_rows,
        "available_activities": all_activities,
        "units": {
            "gdp_hien_hanh_ty_vnd": "billion VND, current prices",
            "gdp_thuc_ty_vnd_theo_bang_nguon": "billion VND, source constant-price basis",
            "tang_truong_gdp_thuc_yoy_pct": "percent year over year",
        },
        "note": "Không cộng hoạt động cấp cha với hoạt động cấp con. Bản ghi 2026 là tăng trưởng/cơ cấu theo quý hoặc 9 tháng, không phải mức GDP năm.",
        "data_cutoff": data_cutoff(),
    }

