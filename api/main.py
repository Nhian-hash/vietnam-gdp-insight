"""FastAPI service for the V-MEST Vietnam GDP dashboard and data."""
from __future__ import annotations

import csv
import hashlib
from html import escape as html_escape
import io
import json
import math
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs
import zipfile
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from data_paths import data_path


ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data"
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
    """Resolve a cataloged CSV while keeping the public filename stable."""
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.csv", file_name):
        raise HTTPException(status_code=404, detail="Không tìm thấy bộ dữ liệu.")
    try:
        path = data_path(file_name)
    except (FileNotFoundError, ValueError, FileExistsError) as exc:
        raise HTTPException(status_code=404, detail="Không tìm thấy bộ dữ liệu.") from exc
    if not path.is_file() or DATA_ROOT.resolve() not in path.resolve().parents:
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
    catalog = read_manifest(DATA_ROOT / "catalog.json").get("files", {}).get(file_name, {})
    return {
        "file": file_name,
        "path": path.relative_to(ROOT).as_posix(),
        "title": info.get("title", file_name.removesuffix(".csv").replace("_", " ")),
        "frequency": info.get("frequency", "xem trường thời gian trong dữ liệu"),
        "source": info.get("source", catalog.get("source", "Xem data/catalog.json.")),
        "description": info.get("description", "Dữ liệu thực tế được giữ kèm đơn vị, trạng thái hoặc ghi chú nguồn khi có."),
        "columns": columns,
        "rows": len(rows),
        "bytes": path.stat().st_size,
    }


def catalogued_csv(dataset_path: str) -> Path:
    """Resolve a candidate target only when it is an existing catalogued CSV."""
    catalog = read_manifest(DATA_ROOT / "catalog.json").get("files", {})
    if not isinstance(catalog, dict):
        raise HTTPException(status_code=503, detail="Danh mục dữ liệu hiện không đọc được.")
    matched = None
    for record in catalog.values():
        if isinstance(record, dict) and record.get("path") == dataset_path:
            matched = record
            break
    if not matched or not isinstance(dataset_path, str) or not dataset_path.endswith(".csv"):
        raise HTTPException(status_code=404, detail="Chỉ có thể kiểm tra một tệp CSV đang có trong danh mục.")
    target = (ROOT / dataset_path).resolve()
    if DATA_ROOT.resolve() not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp dữ liệu hiện hành.")
    return target


def validate_candidate_csv(dataset_path: str, candidate: bytes) -> dict[str, Any]:
    """Check candidate structure against its live file without writing to disk."""
    target = catalogued_csv(dataset_path)
    if not candidate:
        raise HTTPException(status_code=422, detail="Tệp CSV đang rỗng.")
    if len(candidate) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Tệp CSV vượt giới hạn 8 MB.")
    try:
        content = candidate.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=422, detail="CSV cần được mã hóa UTF-8 hoặc UTF-8 BOM.") from exc

    try:
        reader = csv.reader(io.StringIO(content, newline=""), strict=True)
        rows = list(reader)
    except csv.Error as exc:
        raise HTTPException(status_code=422, detail=f"Cấu trúc CSV không hợp lệ: {exc}.") from exc
    if not rows:
        raise HTTPException(status_code=422, detail="CSV chưa có dòng tiêu đề.")

    current_columns, current_rows = read_csv_rows(target)
    candidate_columns = [value.strip() for value in rows[0]]
    errors: list[str] = []
    warnings: list[str] = []
    if not candidate_columns or any(not name for name in candidate_columns):
        errors.append("Tên cột không được để trống.")
    if len(candidate_columns) != len(set(candidate_columns)):
        errors.append("Tên cột bị trùng.")
    if candidate_columns != current_columns:
        errors.append("Tên hoặc thứ tự cột không khớp bộ dữ liệu đang dùng.")

    field_count = len(candidate_columns)
    valid_rows: list[list[str]] = []
    malformed_lines: list[int] = []
    blank_lines = 0
    seen: set[tuple[str, ...]] = set()
    duplicate_count = 0
    missing_by_column = {name: 0 for name in candidate_columns}
    numeric_columns: set[str] = set()
    for column in current_columns:
        nonempty = [row.get(column) for row in current_rows if row.get(column) is not None]
        if nonempty and sum(isinstance(value, (int, float)) and not isinstance(value, bool) for value in nonempty) / len(nonempty) >= 0.8:
            numeric_columns.add(column)
    invalid_numeric: dict[str, int] = {name: 0 for name in numeric_columns}

    for line_number, cells in enumerate(rows[1:], start=2):
        if not cells or all(not value.strip() for value in cells):
            blank_lines += 1
            continue
        if len(cells) != field_count:
            malformed_lines.append(line_number)
            continue
        normalized = tuple(value.strip() for value in cells)
        if normalized in seen:
            duplicate_count += 1
        else:
            seen.add(normalized)
        valid_rows.append(cells)
        for column, value in zip(candidate_columns, cells):
            value = value.strip()
            if not value:
                missing_by_column[column] = missing_by_column.get(column, 0) + 1
            elif column in numeric_columns:
                try:
                    numeric = float(value)
                    if not math.isfinite(numeric):
                        raise ValueError("non-finite")
                except ValueError:
                    invalid_numeric[column] += 1

    if malformed_lines:
        errors.append(f"{len(malformed_lines)} dòng có số trường khác tiêu đề (ví dụ dòng {', '.join(map(str, malformed_lines[:5]))}).")
    if not valid_rows:
        errors.append("CSV không có dòng dữ liệu hợp lệ.")
    if duplicate_count:
        errors.append(f"Phát hiện {duplicate_count} dòng trùng hoàn toàn.")
    for column, count in invalid_numeric.items():
        if count:
            errors.append(f"Cột số '{column}' có {count} giá trị không phải số hữu hạn.")
    if blank_lines:
        warnings.append(f"Bỏ qua {blank_lines} dòng trắng cuối/giữa tệp.")
    missing_total = sum(missing_by_column.values())
    if missing_total:
        warnings.append(f"Có {missing_total} ô trống; cần đối chiếu với trạng thái công bố của nguồn.")

    return {
        "ok": not errors,
        "dataset_path": dataset_path,
        "dataset_title": dataset_description(target.name, target)["title"],
        "current_rows": len(current_rows),
        "candidate_rows": len(valid_rows),
        "columns_match": candidate_columns == current_columns,
        "columns": candidate_columns,
        "missing_cells": missing_total,
        "missing_by_column": {key: value for key, value in missing_by_column.items() if value},
        "duplicate_rows": duplicate_count,
        "errors": errors,
        "warnings": warnings,
        "preview": [dict(zip(candidate_columns, row)) for row in valid_rows[:8]],
        "candidate_sha256": hashlib.sha256(candidate).hexdigest(),
        "candidate_bytes": len(candidate),
    }


def version_history(limit: int = 12) -> list[dict[str, Any]]:
    history: list[dict[str, Any]] = []
    for path in (ROOT / "data_versions").glob("gdp-*.json"):
        if not re.fullmatch(r"gdp-[A-Za-z0-9_-]+\.json", path.name):
            continue
        manifest = read_manifest(path)
        if not manifest.get("version_id"):
            continue
        history.append({
            "version_id": manifest["version_id"],
            "created_utc": manifest.get("created_utc"),
            "retrieved_at_utc": manifest.get("retrieved_at_utc"),
            "archive_url": f"/data_versions/{manifest['version_id']}.zip",
            "file_count": len(manifest.get("files", [])),
        })
    history.sort(key=lambda item: str(item.get("created_utc") or ""), reverse=True)
    return history[:limit]


app = FastAPI(
    title="V-MEST API",
    description=(
        "API đọc dữ liệu GDP Việt Nam, các chỉ báo vĩ mô, GRDP địa phương, "
        "so sánh mô hình và kịch bản dự báo đến 2030. Số dự báo là kịch bản mô hình, không phải số liệu chính thức."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.mount("/assets", StaticFiles(directory=str(ROOT / "assets")), name="assets")

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
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


def _source_urls(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value] if value.startswith(("https://", "http://")) else []
    if isinstance(value, dict):
        return [url for child in value.values() for url in _source_urls(child)]
    if isinstance(value, list):
        return [url for child in value for url in _source_urls(child)]
    return []


def _project_info_markup() -> tuple[str, str]:
    manifests: dict[str, Any] = {}
    for name, path in {
        "catalog": ROOT / "data" / "catalog.json",
        "refresh": ROOT / "refresh_manifest.json",
        "analysis": ROOT / "analysis_manifest.json",
    }.items():
        try:
            manifests[name] = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            manifests[name] = {}

    files = manifests["catalog"].get("files", {})
    records = files.values() if isinstance(files, dict) else files if isinstance(files, list) else []
    file_count = len(files) if isinstance(files, (dict, list)) else 0
    sources = sorted({
        str(record.get("source")) for record in records
        if isinstance(record, dict) and record.get("source") and record.get("source") != "Phân tích hệ thống"
    })
    urls = sorted(set(_source_urls(manifests["refresh"].get("sources", {}))))
    models = manifests["analysis"].get("forecast_evaluation", {}).get("models", [])
    labels = {
        "Naive_last_value": "Naive — giữ nguyên mức GDP gần nhất",
        "Drift_mean_log_change": "Drift — ngoại suy thay đổi log trung bình",
        "Linear_log_trend": "Xu hướng tuyến tính trên log GDP",
        "GRU_logGDP": "GRU",
        "LSTM_logGDP": "LSTM",
    }
    model_items = "".join(f"<li>{html_escape(labels.get(name, str(name)))}</li>" for name in models)
    source_items = "".join(
        f'<li><a href="{html_escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">{html_escape(url)}</a></li>'
        for url in urls
    ) or "<li>Chưa có URL nguồn trong manifest.</li>"
    source_text = " · ".join(html_escape(name) for name in sources) or "Chưa phân loại"

    nav = '<button type="button" class="nav-link" data-page="project-info"><span class="nav-icon">ⓘ</span>Thông tin đề tài</button>'
    section = f'''<section id="project-info" class="section page">
  <div class="section-head"><div><h2>Thông tin đề tài</h2><span class="sub">Thông tin sinh viên, hướng dẫn, dữ liệu và phương pháp nghiên cứu</span></div></div>
  <div class="grid-equal">
    <article class="panel"><div class="panel-title">Thông tin sinh viên và đề tài</div>
      <div class="status-row"><span>Họ tên</span><strong>Bùi Nhĩ Ân</strong></div>
      <div class="status-row"><span>MSSV</span><strong>2311553345</strong></div>
      <div class="status-row"><span>Giảng viên hướng dẫn</span><strong>ThS. Vương Xuân Chí</strong></div>
      <div class="panel-title" style="margin-top:14px">Tên đề tài</div>
      <p>Xây dựng hệ thống xử lý và phân tích dự báo GDP toàn diện (End-to-End) tại Việt Nam</p>
    </article>
    <article class="panel"><div class="panel-title">Quy mô dữ liệu</div><div class="data-footer">
      <div class="data-box"><b>{file_count}</b><span>Tệp dữ liệu<br>trong catalog</span></div>
      <div class="data-box"><b>{len(urls)}</b><span>Địa chỉ nguồn<br>trong manifest</span></div>
      <div class="data-box"><b>{len(sources)}</b><span>Nhóm nguồn<br>bên ngoài</span></div>
    </div><div class="footnote" style="margin-top:12px">Nguồn ngoài: {source_text}</div></article>
  </div>
  <article class="panel" style="margin-top:14px"><div class="panel-title">Thuật toán và mô hình dự báo · {len(models)} mô hình</div>
    <div class="panel-sub">Các mô hình được so sánh để dự báo GDP thực đến năm 2030</div>
    <ol class="table" style="padding-left:24px">{model_items}</ol>
    <div class="footnote">Kỹ thuật phân tích bổ sung: nội suy Cubic Spline chỉ để tương thích/hiển thị; kiểm định ADF; bộ lọc HP; tương quan Pearson và Spearman; backtest expanding-window rolling-origin. MAPE, sMAPE, MAE, RMSE và MASE là chỉ số đánh giá, không phải thuật toán.</div>
  </article>
  <details class="panel" style="margin-top:14px"><summary class="panel-title" style="cursor:pointer">Danh sách địa chỉ nguồn dữ liệu ({len(urls)} địa chỉ)</summary>
    <div class="panel-sub" style="margin:6px 0 10px">Các URL được ghi trong refresh manifest. Chọn một địa chỉ để mở nguồn gốc.</div>
    <ol style="padding-left:24px;overflow-wrap:anywhere">{source_items}</ol>
  </details>
</section>'''
    return nav, section


@app.get("/", include_in_schema=False)
def dashboard() -> Response:
    """Serve the refreshed dashboard, falling back to a legacy index file."""
    page = ROOT / "dashboard.html"
    if not page.is_file():
        page = ROOT / "index.html"
    if not page.is_file():
        raise HTTPException(status_code=404, detail="Chưa có tệp dashboard.html hoặc index.html.")

    html = page.read_text(encoding="utf-8")
    html = re.sub(
        r'<footer id="page-footer"[^>]*>.*?</footer>',
        '<footer id="page-footer" class="footnote page-footer" style="display:none"></footer>',
        html,
        count=1,
        flags=re.DOTALL,
    )
    if 'id="project-info"' not in html:
        nav_item, info_section = _project_info_markup()
        html = html.replace("</nav>", nav_item + "</nav>", 1)
        footer_marker = '<footer id="page-footer"'
        if footer_marker in html:
            html = html.replace(footer_marker, info_section + "\n      " + footer_marker, 1)
        else:
            html = html.replace("</main>", info_section + "</main>", 1)
        meta_key = "'data-status':['Quản lý dữ liệu','Danh mục cấu trúc, nguồn và chất lượng dữ liệu']"
        info_meta = "'project-info':['Thông tin đề tài','Sinh viên · giảng viên hướng dẫn · dữ liệu · thuật toán']"
        if meta_key in html:
            html = html.replace(meta_key, meta_key + "," + info_meta, 1)
        else:
            html = html.replace("}[page];$('top-title')", "," + info_meta + "}[page];$('top-title')", 1)
    export_script = r"""<script>
(() => {
  const endpoint = '/api/v1/exports';
  const csvCell = value => `"${String(value ?? '').replaceAll('"', '""')}"`;
  function submitExport(fileName, contentType, content) {
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = endpoint;
    form.enctype = 'application/x-www-form-urlencoded';
    form.acceptCharset = 'UTF-8';
    form.style.display = 'none';
    for (const [name, value] of Object.entries({file_name: fileName, content_type: contentType, content})) {
      const field = document.createElement('textarea');
      field.name = name;
      field.value = value;
      form.appendChild(field);
    }
    document.body.appendChild(form);
    form.submit();
    window.setTimeout(() => form.remove(), 1000);
  }
  window.downloadCsv = (fileName, headers, rows) => {
    const csv = '\ufeff' + [headers.map(csvCell).join(','), ...rows.map(row => headers.map(key => csvCell(row[key])).join(','))].join('\r\n');
    submitExport(fileName, 'text/csv; charset=utf-8', csv);
  };
  window.downloadJson = (fileName, value) => submitExport(fileName, 'application/json; charset=utf-8', JSON.stringify(value, null, 2));
})();
</script>"""
    release_markup = r'''<style>
.vmest-release-center{margin-top:14px}.vmest-release-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.vmest-release-box{border:1px solid var(--line,#dbe3ee);border-radius:12px;padding:14px;background:var(--surface,#fff);min-width:0}.vmest-release-controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:12px 0}.vmest-release-controls select,.vmest-release-controls input{max-width:100%;min-height:42px}.vmest-release-status{font-weight:700}.vmest-release-report{margin-top:12px}.vmest-release-table{max-height:300px;overflow:auto}.vmest-release-note{line-height:1.6}.vmest-release-box .panel-title{margin-bottom:6px}@media(max-width:760px){.vmest-release-grid{grid-template-columns:1fr}.vmest-release-controls>*{width:100%}}
</style>
<article class="panel vmest-release-center" id="release-center">
  <div class="section-head"><div><div class="panel-title">Trung tâm vận hành dữ liệu</div><div class="panel-sub">Theo dõi phiên bản đang chạy, kiểm tra CSV cập nhật và chuẩn bị gói thay đổi</div></div><span id="ops-live-status" class="status-tag">Đang kết nối…</span></div>
  <div class="vmest-release-grid">
    <div class="vmest-release-box"><div class="panel-title">Bản dữ liệu công khai</div><div class="status-row"><span>Phiên bản đang chạy</span><strong id="ops-current-version">—</strong></div><div class="status-row"><span>Số bộ dữ liệu</span><strong id="ops-dataset-count">—</strong></div><div class="status-row"><span>Cập nhật nguồn gần nhất</span><strong id="ops-source-date">—</strong></div><div class="vmest-release-controls"><a id="ops-current-snapshot" class="select export-btn" href="#" download>Tải snapshot hiện hành</a></div></div>
    <div class="vmest-release-box"><div class="panel-title">Kiểm tra dữ liệu ứng viên</div><div class="panel-sub">Chọn CSV hiện có để thay thế, tải tệp mới và đối chiếu cấu trúc/giá trị trước khi đưa vào repo.</div><div class="vmest-release-controls"><select id="ops-dataset-target" class="select" aria-label="Bộ dữ liệu cần cập nhật"></select><input id="ops-candidate-file" type="file" accept=".csv,text/csv" aria-label="Chọn tệp CSV ứng viên"></div><div class="vmest-release-controls"><button id="ops-validate" class="select export-btn" type="button">Kiểm tra và xem trước</button><button id="ops-package" class="select export-btn" type="button" disabled>Tải gói đề xuất</button></div><div id="ops-release-report" class="vmest-release-report" aria-live="polite"></div></div>
  </div>
  <div class="footnote vmest-release-note" style="margin-top:12px">Các chức năng xem, lọc, tải dữ liệu và đổi giao diện vẫn mở cho mọi người. Kiểm tra và đóng gói ứng viên không ghi đè dữ liệu công khai. Để phát hành/khôi phục thật, chủ repo cập nhật hoặc khôi phục tệp trong GitHub; Render tự triển khai theo phiên bản đã duyệt. Tệp CSV được kiểm tra tạm thời trong bộ nhớ, không lưu lên máy chủ.</div>
  <div class="vmest-release-grid" style="margin-top:12px"><div class="vmest-release-box"><div class="panel-title">Lịch sử snapshot</div><div class="panel-sub">Tải một bản chụp dữ liệu trước đó để đối chiếu hoặc phục hồi qua repo.</div><div class="vmest-release-controls"><select id="ops-history-version" class="select" aria-label="Chọn snapshot dữ liệu"></select><a id="ops-history-download" class="select export-btn" href="#" download>Tải snapshot đã chọn</a></div></div><div class="vmest-release-box"><div class="panel-title">Quy trình phát hành</div><ol class="vmest-release-note" style="padding-left:22px;margin:6px 0"><li>Kiểm tra schema, dòng trùng, ô trống và giá trị số.</li><li>Tải gói đề xuất gồm CSV cùng manifest kiểm tra.</li><li>Đưa tệp vào đúng đường dẫn trong repo, xem lại diff rồi commit.</li><li>Render tự deploy từ GitHub; bản mới xuất hiện sau khi deploy thành công.</li></ol></div></div>
</article>'''
    if 'id="release-center"' not in html:
        html = re.subn(
            r'(<section id="data-status"[^>]*>)',
            lambda match: match.group(1) + release_markup,
            html,
            count=1,
        )[0]
    operations_script = r"""<script>
(() => {
  const api = '/api/v1/operations';
  const el = id => document.getElementById(id);
  const show = (node, value) => { if (node) node.textContent = value ?? ''; };
  let candidateReport = null;
  async function jsonRequest(url, options) {
    const response = await fetch(url, options);
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(payload.detail || `Lỗi máy chủ (${response.status})`);
    return payload;
  }
  function renderPreview(report) {
    const root = el('ops-release-report');
    root.replaceChildren();
    const summary = document.createElement('div');
    summary.className = report.ok ? 'status-tag' : 'status-tag warn';
    summary.textContent = report.ok ? `Đạt kiểm tra cấu trúc · ${Number(report.candidate_rows).toLocaleString('vi-VN')} dòng · ${Number(report.columns.length).toLocaleString('vi-VN')} cột` : `Chưa đạt · ${report.errors.length} lỗi cần xử lý`;
    root.appendChild(summary);
    const metrics = document.createElement('p');
    metrics.className = 'panel-sub';
    metrics.textContent = `Dữ liệu hiện hành: ${Number(report.current_rows).toLocaleString('vi-VN')} dòng · Ứng viên: ${Number(report.candidate_rows).toLocaleString('vi-VN')} dòng · Ô trống: ${Number(report.missing_cells).toLocaleString('vi-VN')} · Trùng hoàn toàn: ${Number(report.duplicate_rows).toLocaleString('vi-VN')}`;
    root.appendChild(metrics);
    for (const message of [...report.errors, ...report.warnings]) {
      const line = document.createElement('p'); line.className = 'footnote'; line.textContent = `${report.errors.includes(message) ? 'Lỗi: ' : 'Lưu ý: '}${message}`; root.appendChild(line);
    }
    if (report.preview?.length) {
      const wrap = document.createElement('div'); wrap.className = 'table-wrap vmest-release-table';
      const table = document.createElement('table'); table.className = 'table';
      const head = document.createElement('thead'), headRow = document.createElement('tr');
      for (const key of report.columns) { const th = document.createElement('th'); th.textContent = key; headRow.appendChild(th); }
      head.appendChild(headRow); table.appendChild(head);
      const body = document.createElement('tbody');
      for (const row of report.preview) { const tr = document.createElement('tr'); for (const key of report.columns) { const td = document.createElement('td'); td.textContent = row[key] ?? ''; tr.appendChild(td); } body.appendChild(tr); }
      table.appendChild(body); wrap.appendChild(table); root.appendChild(wrap);
    }
  }
  async function init() {
    try {
      const [status, datasets, versions] = await Promise.all([
        jsonRequest(`${api}/status`), jsonRequest(`${api}/datasets`), jsonRequest(`${api}/versions`)
      ]);
      show(el('ops-live-status'), 'Đang hoạt động');
      show(el('ops-current-version'), status.version_id || '—');
      show(el('ops-dataset-count'), Number(status.dataset_count || 0).toLocaleString('vi-VN'));
      show(el('ops-source-date'), status.retrieved_at_utc || 'Chưa ghi nhận');
      el('ops-current-snapshot').href = status.archive_url || '#';
      const target = el('ops-dataset-target');
      target.replaceChildren();
      for (const item of datasets.datasets || []) target.add(new Option(`${item.title} · ${item.path}`, item.path));
      const history = el('ops-history-version'); history.replaceChildren();
      for (const item of versions.versions || []) history.add(new Option(`${item.version_id} · ${item.created_utc || 'không rõ ngày'}`, item.archive_url));
      const setArchive = () => { el('ops-history-download').href = history.value || '#'; };
      history.addEventListener('change', setArchive); setArchive();
    } catch (error) {
      show(el('ops-live-status'), 'Chưa kết nối API');
      show(el('ops-release-report'), error.message);
    }
  }
  el('ops-candidate-file')?.addEventListener('change', () => { candidateReport = null; el('ops-package').disabled = true; el('ops-release-report').replaceChildren(); });
  el('ops-validate')?.addEventListener('click', async () => {
    const file = el('ops-candidate-file').files?.[0], datasetPath = el('ops-dataset-target').value;
    if (!file) { show(el('ops-release-report'), 'Hãy chọn tệp CSV để kiểm tra.'); return; }
    if (file.size > 8 * 1024 * 1024) { show(el('ops-release-report'), 'Tệp vượt giới hạn 8 MB.'); return; }
    const button = el('ops-validate'); button.disabled = true; button.textContent = 'Đang kiểm tra…';
    try {
      candidateReport = await jsonRequest(`${api}/validate?dataset_path=${encodeURIComponent(datasetPath)}`, {method:'POST',headers:{'Content-Type':'text/csv'},body:file});
      renderPreview(candidateReport); el('ops-package').disabled = !candidateReport.ok;
    } catch (error) { candidateReport = null; el('ops-package').disabled = true; show(el('ops-release-report'), error.message); }
    finally { button.disabled = false; button.textContent = 'Kiểm tra và xem trước'; }
  });
  el('ops-package')?.addEventListener('click', async () => {
    const file = el('ops-candidate-file').files?.[0], datasetPath = el('ops-dataset-target').value;
    if (!file || !candidateReport?.ok) return;
    const button = el('ops-package'); button.disabled = true; button.textContent = 'Đang tạo gói…';
    try {
      const response = await fetch(`${api}/package?dataset_path=${encodeURIComponent(datasetPath)}`, {method:'POST',headers:{'Content-Type':'text/csv'},body:file});
      if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail?.message || body.detail || `Lỗi máy chủ (${response.status})`); }
      const blob = await response.blob(), url = URL.createObjectURL(blob), link = document.createElement('a');
      link.href = url; link.download = `de_xuat_${file.name.replace(/[^A-Za-z0-9_.-]/g,'_').replace(/\.csv$/i,'')}.zip`; document.body.appendChild(link); link.click(); link.remove(); URL.revokeObjectURL(url);
    } catch (error) { show(el('ops-release-report'), error.message); }
    finally { button.disabled = false; button.textContent = 'Tải gói đề xuất'; }
  });
  init();
})();
</script>"""
    all_scripts = export_script + operations_script
    html, inserted = re.subn(r"</body\s*>", lambda match: all_scripts + match.group(0), html, count=1, flags=re.IGNORECASE)
    if not inserted:
        html += export_script
    return Response(
        content=html,
        media_type="text/html; charset=utf-8",
        headers={"Cache-Control": "no-store"},
    )


@app.get("/data_versions/{archive_name}", include_in_schema=False)
def download_version_archive(archive_name: str) -> FileResponse:
    """Serve snapshot ZIPs referenced by the public data version manifest."""
    if not re.fullmatch(r"gdp-[A-Za-z0-9_-]+\.zip", archive_name):
        raise HTTPException(status_code=404, detail="Không tìm thấy bản snapshot.")
    archive = ROOT / "data_versions" / archive_name
    if not archive.is_file() or archive.resolve().parent != (ROOT / "data_versions").resolve():
        raise HTTPException(status_code=404, detail="Không tìm thấy bản snapshot.")
    return FileResponse(
        archive,
        media_type="application/zip",
        filename=archive_name,
        headers={"Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )


@app.post(f"{API_PREFIX}/exports", tags=["Tải dữ liệu"])
async def export_download(request: Request) -> Response:
    """Return dashboard-generated CSV/JSON as an HTTP attachment for mobile browsers."""
    body = await request.body()
    if len(body) > 12 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Tệp xuất vượt quá giới hạn 12 MB.")
    try:
        fields = parse_qs(body.decode("utf-8"), keep_blank_values=True, strict_parsing=True)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail="Dữ liệu xuất không hợp lệ.") from exc

    file_name = fields.get("file_name", [""])[0]
    content_type = fields.get("content_type", [""])[0]
    content = fields.get("content", [""])[0]
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}\.(csv|json)", file_name, flags=re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Tên tệp xuất không hợp lệ.")
    media_types = {"csv": "text/csv; charset=utf-8", "json": "application/json; charset=utf-8"}
    extension = file_name.rsplit(".", 1)[-1].lower()
    if content_type != media_types[extension]:
        raise HTTPException(status_code=400, detail="Định dạng tệp xuất không khớp.")
    if extension == "json":
        try:
            json.loads(content)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail="Nội dung JSON không hợp lệ.") from exc

    return Response(
        content=content.encode("utf-8"),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file_name}"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@app.get(f"{API_PREFIX}/health", tags=["Hệ thống"])
def health() -> dict[str, Any]:
    version = read_manifest(VERSION_FILE)
    return {
        "status": "ok",
        "service": "V-MEST API",
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
    files = sorted(DATA_ROOT.rglob("*.csv"), key=lambda path: (path.parent.as_posix().casefold(), path.name.casefold()))
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


@app.get(f"{API_PREFIX}/operations/status", tags=["Vận hành dữ liệu"])
def operations_status() -> dict[str, Any]:
    manifest = read_manifest(VERSION_FILE)
    files = list(DATA_ROOT.rglob("*.csv"))
    return {
        "status": "ok",
        "version_id": manifest.get("version_id"),
        "created_utc": manifest.get("created_utc"),
        "retrieved_at_utc": manifest.get("retrieved_at_utc"),
        "data_cutoff": manifest.get("data_cutoff", {}),
        "dataset_count": len(files),
        "archive_url": f"/data_versions/{manifest['version_id']}.zip" if manifest.get("version_id") else None,
        "storage_mode": "source-controlled",
        "write_enabled": False,
        "publish_method": "GitHub commit followed by Render auto-deploy",
    }


@app.get(f"{API_PREFIX}/operations/datasets", tags=["Vận hành dữ liệu"])
def operations_datasets() -> dict[str, Any]:
    files = sorted(DATA_ROOT.rglob("*.csv"), key=lambda path: (path.parent.as_posix().casefold(), path.name.casefold()))
    return {"datasets": [dataset_description(path.name, path) | {"path": path.relative_to(ROOT).as_posix()} for path in files]}


@app.get(f"{API_PREFIX}/operations/versions", tags=["Vận hành dữ liệu"])
def operations_versions() -> dict[str, Any]:
    return {"versions": version_history()}


async def _candidate_body(request: Request) -> bytes:
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Tệp CSV vượt giới hạn 8 MB.")
    candidate = await request.body()
    if len(candidate) > 8 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Tệp CSV vượt giới hạn 8 MB.")
    return candidate


@app.post(f"{API_PREFIX}/operations/validate", tags=["Vận hành dữ liệu"])
async def validate_candidate(
    request: Request,
    dataset_path: str = Query(..., min_length=1, max_length=300),
) -> dict[str, Any]:
    """Non-mutating quality check; candidate content is held in memory only."""
    candidate = await _candidate_body(request)
    return validate_candidate_csv(dataset_path, candidate)


@app.post(f"{API_PREFIX}/operations/package", tags=["Vận hành dữ liệu"])
async def package_candidate(
    request: Request,
    dataset_path: str = Query(..., min_length=1, max_length=300),
) -> Response:
    """Build a downloadable GitHub-ready candidate package without publishing it."""
    candidate = await _candidate_body(request)
    report = validate_candidate_csv(dataset_path, candidate)
    if not report["ok"]:
        raise HTTPException(status_code=422, detail={"message": "Bản ứng viên chưa đạt kiểm tra.", "validation": report})

    current = read_manifest(VERSION_FILE)
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    package_manifest = {
        "release_type": "candidate",
        "status": "not_published",
        "created_utc": created,
        "based_on_data_version": current.get("version_id"),
        "target_path": dataset_path,
        "candidate_sha256": report["candidate_sha256"],
        "validation": {
            "ok": report["ok"],
            "rows": report["candidate_rows"],
            "columns": report["columns"],
            "missing_cells": report["missing_cells"],
            "duplicate_rows": report["duplicate_rows"],
            "warnings": report["warnings"],
        },
        "publication_note": "Tệp chỉ là đề xuất. Đối chiếu nguồn, cập nhật đúng đường dẫn trong GitHub, xem diff và để Render triển khai sau khi commit được duyệt.",
    }
    readme = (
        "V-MEST - GÓI ĐỀ XUẤT CẬP NHẬT DỮ LIỆU\n\n"
        "Tệp CSV trong gói nằm tại đúng đường dẫn repo ghi trong V-MEST_release_manifest.json.\n"
        "Gói này chưa được phát hành và không thay đổi dữ liệu đang chạy.\n"
        "Hãy đối chiếu nguồn, xem diff, commit vào GitHub; Render sẽ tự động deploy.\n"
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        archive.writestr(dataset_path, candidate)
        archive.writestr("V-MEST_release_manifest.json", json.dumps(package_manifest, ensure_ascii=False, indent=2))
        archive.writestr("README_phat_hanh.txt", readme)
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": 'attachment; filename="vmest_data_candidate.zip"',
            "Cache-Control": "no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


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

