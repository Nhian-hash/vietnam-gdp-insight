"""Create an immutable, content-addressed snapshot of the refreshed GDP inputs."""
from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from data_paths import data_path

ROOT = Path(__file__).resolve().parent
SNAPSHOT_FILES = [
    "GDP_Vietnam_Annual.csv",
    "du_lieu_gdp_tong_hop.csv",
    "du_lieu_gdp_thuc_va_tang_truong.csv",
    "du_lieu_gdp_co_cau_3_nganh.csv",
    "du_lieu_tang_truong_gdp_quy.csv",
    "du_lieu_cpi_phan_tich_thang.csv",
    "du_lieu_ty_gia_usd_vnd.csv",
    "du_lieu_xuat_nhap_khau_thang_2026.csv",
    "du_lieu_san_xuat_iip_thang_2026.csv",
    "du_lieu_grdp_63_tinh_thanh.csv",
    "du_lieu_ban_le_tieu_dung_thang_2026.csv",
    "du_lieu_fdi_dau_tu.csv",
    "du_lieu_fdi_luy_ke_2026.csv",
    "du_lieu_chi_so_kinh_te_hang_nam.csv",
    "du_lieu_gdp_theo_chi_tieu.csv",
    "du_lieu_dong_gop_gdp_theo_chi_tieu.csv",
    "du_lieu_gdp_thuc_theo_nganh.csv",
    "du_lieu_gdp_nganh_chi_tiet.csv",
    "du_lieu_gdp_nganh_chi_tiet_2026.csv",
    "du_lieu_lao_dong_theo_nganh.csv",
    "du_lieu_nang_suat_lao_dong.csv",
    "du_lieu_nang_suat_thuc_theo_khu_vuc.csv",
    "du_lieu_that_nghiep_vung.csv",
    "du_lieu_dau_tu_theo_loai_hinh.csv",
    "du_lieu_dau_tu_theo_nganh_thuc.csv",
    "du_lieu_tai_khoa_ngan_sach.csv",
    "du_lieu_tin_dung_du_no.csv",
    "du_lieu_lai_suat_ngan_hang.csv",
    "du_lieu_can_can_thanh_toan.csv",
    "du_lieu_dong_gop_tfp.csv",
    "du_lieu_gia_hang_hoa_quoc_te.csv",
    "du_lieu_so_sanh_dong_luc_gdp.csv",
    "du_lieu_tuong_quan_dong_luc_gdp.csv",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    files = []
    for name in SNAPSHOT_FILES:
        path = data_path(name)
        if not path.is_file():
            continue
        files.append({
            "file": name,
            "path": path.relative_to(ROOT).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })
    if not files:
        raise RuntimeError("No snapshot input files were found")

    # Version identity depends on the standardized data inputs, not on run time.
    content_files = files
    fingerprint_input = json.dumps(content_files, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    fingerprint = hashlib.sha256(fingerprint_input).hexdigest()
    created = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    refresh_path = ROOT / "refresh_manifest.json"
    refresh = json.loads(refresh_path.read_text(encoding="utf-8")) if refresh_path.exists() else {}
    expanded_manifest_path = ROOT / "data" / "nso" / "raw" / "expanded" / "source_manifest.json"
    expanded_refresh = json.loads(expanded_manifest_path.read_text(encoding="utf-8")) if expanded_manifest_path.exists() else {}
    retrieved_candidates = [value for value in [refresh.get("retrieved_at_utc"), expanded_refresh.get("retrieved_at_utc")] if value]
    latest_retrieved = max(retrieved_candidates) if retrieved_candidates else None
    version_id = f"gdp-{fingerprint[:12]}"
    archive_relative = f"data_versions/{version_id}.zip"
    archive_path = ROOT / archive_relative
    archive_path.parent.mkdir(parents=True, exist_ok=True)

    if not archive_path.exists():
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for item in content_files:
                archive.write(ROOT / item["path"], arcname=item["path"])

    manifest = {
        "version_id": version_id,
        "fingerprint_sha256": fingerprint,
        "created_utc": created,
        "retrieved_at_utc": latest_retrieved,
        "base_sources_retrieved_at_utc": refresh.get("retrieved_at_utc"),
        "expanded_sources_retrieved_at_utc": expanded_refresh.get("retrieved_at_utc"),
        "data_cutoff": refresh.get("data_cutoff", {}),
        "archive": archive_relative.replace("\\", "/"),
        "files": content_files,
        "versioning_note": "Một phiên bản mới được tạo khi nội dung các CSV dữ liệu chuẩn hóa thay đổi. Tệp ZIP giữ ảnh chụp bất biến để truy vết và tái lập phân tích.",
    }
    history_manifest_path = ROOT / "data_versions" / f"{version_id}.json"
    if not history_manifest_path.exists():
        history_manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "data_version_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Data version: {version_id} ({len(files)} files) -> {archive_path}")


if __name__ == "__main__":
    main()
