"""Build an offline, single-file dashboard preview from the refreshed CSVs."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_paths import data_path

# Keep the history-specific evaluation inside Training Lab so the sidebar stays concise.
arena_fragment = (ROOT / "templates" / "backtest_arena.html").read_text(encoding="utf-8")


def frame(name: str) -> pd.DataFrame:
    return pd.read_csv(data_path(name), encoding="utf-8-sig")


def safe_num(value):
    return float(value) if pd.notna(value) else None


gdp = frame("du_lieu_gdp_tong_hop.csv")
real = frame("du_lieu_gdp_thuc_va_tang_truong.csv")
real["nam"] = pd.to_numeric(real["nam"], errors="coerce")
real = real.dropna(subset=["nam"]).sort_values("nam")
gdp["nam"] = pd.to_numeric(gdp["nam"], errors="coerce")
gdp = gdp.dropna(subset=["nam"])
gdp = real.merge(gdp[["nam", "gdp_danh_nghia_usd"]], on="nam", how="left")

sector = frame("du_lieu_gdp_co_cau_3_nganh.csv")
sector = sector.sort_values("nam")
sector_items = [
    {"year": int(r.nam), "shares": [
        {"label": "Nông, lâm, thủy sản", "value": safe_num(r.ty_trong_nong_lam_thuy_san_pct), "color": "#25b886"},
        {"label": "Công nghiệp, xây dựng", "value": safe_num(r.ty_trong_cong_nghiep_xay_dung_pct), "color": "#3288e8"},
        {"label": "Dịch vụ", "value": safe_num(r.ty_trong_dich_vu_pct), "color": "#7856d8"},
        {"label": "Thuế sản phẩm ròng", "value": safe_num(r.ty_trong_thue_san_pham_pct), "color": "#f4a62a"},
    ]} for r in sector.itertuples(index=False)
]

qgdp = frame("du_lieu_tang_truong_gdp_quy.csv")
trade = frame("du_lieu_xuat_nhap_khau_thang_2026.csv")
trade["kim_ngach_xuat_khau_usd"] = pd.to_numeric(trade["kim_ngach_xuat_khau_usd"], errors="coerce") / 1e9
trade["kim_ngach_nhap_khau_usd"] = pd.to_numeric(trade["kim_ngach_nhap_khau_usd"], errors="coerce") / 1e9
trade["can_can_thuong_mai_usd"] = pd.to_numeric(trade["can_can_thuong_mai_usd"], errors="coerce") / 1e9
iip = frame("du_lieu_san_xuat_iip_thang_2026.csv")
iip["chi_so_iip_toan_nganh_2015_100"] = pd.to_numeric(iip["chi_so_iip_toan_nganh_2015_100"], errors="coerce")
macro_annual = frame("du_lieu_chi_so_kinh_te_hang_nam.csv")
numeric_macro = ["nam", "tang_truong_gdp_thuc_pct", "lam_phat_cpi_yoy_pct", "trade_to_gdp_pct",
                 "can_can_thuong_mai_tren_gdp_pct", "von_fdi_thuc_hien_tren_gdp_pct",
                 "tang_truong_ban_le_danh_nghia_yoy_pct", "tang_truong_ban_le_thuc_uoc_tinh_yoy_pct",
                 "ty_gia_usd_vnd_binh_quan_nam", "tang_truong_gdp_danh_nghia_usd_yoy_pct"]
for col in numeric_macro:
    macro_annual[col] = pd.to_numeric(macro_annual[col], errors="coerce")
macro_annual = macro_annual.sort_values("nam")
sector_compare = frame("du_lieu_so_sanh_nganh_2025.csv")
retail_annual = frame("du_lieu_ban_le_tieu_dung.csv")
retail_monthly = frame("du_lieu_ban_le_tieu_dung_thang_2026.csv")
fdi_annual = frame("du_lieu_fdi_dau_tu.csv")
fdi_latest = frame("du_lieu_fdi_luy_ke_2026.csv")
cpi_fx = frame("du_lieu_so_sanh_cpi_ty_gia_thang.csv")
cpi_fx["thoi_gian"] = pd.to_datetime(cpi_fx["thoi_gian"], errors="coerce")
cpi_fx = cpi_fx[cpi_fx["thoi_gian"].ge("2020-01-01")].sort_values("thoi_gian")
cpi_base = pd.to_numeric(cpi_fx["chi_so_cpi"], errors="coerce").dropna().iloc[0]
fx_base = pd.to_numeric(cpi_fx["ty_gia_usd_vnd"], errors="coerce").dropna().iloc[0]
cpi_fx["cpi_index_100"] = pd.to_numeric(cpi_fx["chi_so_cpi"], errors="coerce") / cpi_base * 100
cpi_fx["fx_index_100"] = pd.to_numeric(cpi_fx["ty_gia_usd_vnd"], errors="coerce") / fx_base * 100
correlation_source = frame("du_lieu_so_sanh_tuong_quan_vi_mo.csv")
iip_annual = frame("du_lieu_so_sanh_iip_gdp_hang_nam.csv")
for col in ["nam", "tang_truong_gdp_thuc_pct", "tang_truong_iip_yoy_pct", "tang_truong_iip_t_minus_0_pct", "tang_truong_iip_t_minus_1_pct", "tang_truong_iip_t_minus_2_pct", "tang_truong_iip_t_minus_3_pct"]:
    iip_annual[col] = pd.to_numeric(iip_annual[col], errors="coerce")
grdp = frame("du_lieu_grdp_63_tinh_thanh.csv")
grdp["nam"] = pd.to_numeric(grdp["nam"], errors="coerce")
grdp["quy_mo_grdp_vnd"] = pd.to_numeric(grdp["quy_mo_grdp_vnd"], errors="coerce")
grdp["grdp_binh_quan_dau_nguoi_trieu_vnd"] = pd.to_numeric(grdp["grdp_binh_quan_dau_nguoi_trieu_vnd"], errors="coerce")
grdp["tang_truong_grdp_yoy_pct"] = pd.to_numeric(grdp["tang_truong_grdp_yoy_pct"], errors="coerce")
grdp = grdp.dropna(subset=["nam", "quy_mo_grdp_vnd"])
grdp["nam"] = grdp["nam"].astype(int)
region_rows = grdp[grdp["loai_dia_ban"].eq("vung_thong_ke")].copy()
province_rows = grdp[grdp["loai_dia_ban"].eq("tinh_thanh_63_truyen_thong")].copy()
grdp_years = sorted(grdp["nam"].unique().tolist())
regions_by_year = []
for year, group in region_rows.groupby("nam", sort=True):
    total = group["quy_mo_grdp_vnd"].sum()
    regions_by_year.append({"year": int(year), "items": [
        {"name": str(r.ten_vung_kinh_te), "share": float(r.quy_mo_grdp_vnd / total * 100),
         "perCapita": float(r.grdp_binh_quan_dau_nguoi_trieu_vnd),
         "growth": float(r.tang_truong_grdp_yoy_pct)}
        for r in group.sort_values("quy_mo_grdp_vnd", ascending=False).itertuples(index=False)
    ]})
provinces_by_year = []
for year, group in province_rows.groupby("nam", sort=True):
    provinces_by_year.append({"year": int(year), "items": [
        {"name": str(r.ten_tinh), "grdp": float(r.quy_mo_grdp_vnd),
         "perCapita": float(r.grdp_binh_quan_dau_nguoi_trieu_vnd),
         "growth": float(r.tang_truong_grdp_yoy_pct)}
        for r in group.itertuples(index=False)
    ]})
models = frame("so_sanh_hieu_qua_mo_hinh_du_bao.csv")
models["MAPE_pct"] = pd.to_numeric(models["MAPE_pct"], errors="coerce")
models["RMSE_usd_2015"] = pd.to_numeric(models["RMSE_usd_2015"], errors="coerce") / 1e9
fx = frame("du_lieu_ty_gia_usd_vnd.csv")
cpi_month = frame("du_lieu_cpi_phan_tich_thang.csv")
rolling = frame("du_lieu_du_bao_rolling_origin.csv")
rolling["nam_du_bao"] = pd.to_numeric(rolling["nam_du_bao"], errors="coerce")
rolling["gdp_thuc_thuc_te_usd_2015"] = pd.to_numeric(rolling["gdp_thuc_thuc_te_usd_2015"], errors="coerce")
rolling["gdp_thuc_du_bao_usd_2015"] = pd.to_numeric(rolling["gdp_thuc_du_bao_usd_2015"], errors="coerce")
rolling = rolling.dropna(subset=["nam_du_bao", "gdp_thuc_thuc_te_usd_2015", "gdp_thuc_du_bao_usd_2015"])
rolling = rolling.sort_values(["nam_du_bao", "mo_hinh"])
forecast_2030 = frame("du_lieu_du_bao_gdp_thuc_den_2030.csv")
forecast_2030["nam_du_bao"] = pd.to_numeric(forecast_2030["nam_du_bao"], errors="coerce")
forecast_2030["gdp_thuc_du_bao_usd_2015"] = pd.to_numeric(forecast_2030["gdp_thuc_du_bao_usd_2015"], errors="coerce")
forecast_2030 = forecast_2030.dropna(subset=["nam_du_bao", "gdp_thuc_du_bao_usd_2015"]).sort_values(["mo_hinh", "nam_du_bao"])
horizon_metrics = frame("so_sanh_hieu_qua_mo_hinh_theo_chan_troi.csv")
horizon_backtest = frame("du_lieu_du_bao_nhieu_chan_troi.csv")
horizon_backtest["nam_du_bao"] = pd.to_numeric(horizon_backtest["nam_du_bao"], errors="coerce")
horizon_backtest["chan_troi_nam"] = pd.to_numeric(horizon_backtest["chan_troi_nam"], errors="coerce")
horizon_backtest["gdp_thuc_thuc_te_usd_2015"] = pd.to_numeric(horizon_backtest["gdp_thuc_thuc_te_usd_2015"], errors="coerce")
horizon_backtest["gdp_thuc_du_bao_usd_2015"] = pd.to_numeric(horizon_backtest["gdp_thuc_du_bao_usd_2015"], errors="coerce")
quarter_gdp_2010 = frame("du_lieu_gdp_quy_muc_thuc_gia_2010.csv")
quarter_gdp_2020 = frame("du_lieu_gdp_quy_muc_thuc_gia_2020.csv")
quarter_reconciliation = frame("doi_chieu_gdp_thuc_quy_va_nam.csv")
quarter_backtest = frame("du_lieu_du_bao_gdp_quy_backtest.csv")
quarter_metrics = frame("so_sanh_hieu_qua_mo_hinh_gdp_quy.csv")
for column in ["nam", "quy", "gdp_thuc_ty_vnd_gia_2010"]:
    quarter_gdp_2010[column] = pd.to_numeric(quarter_gdp_2010[column], errors="coerce")
for column in ["nam", "quy", "gdp_thuc_ty_vnd_gia_2020"]:
    quarter_gdp_2020[column] = pd.to_numeric(quarter_gdp_2020[column], errors="coerce")
for column in ["nam", "gdp_thuc_nam_ty_vnd_gia_2010", "tong_4_quy_ty_vnd_gia_2010", "chenh_lech_pct"]:
    quarter_reconciliation[column] = pd.to_numeric(quarter_reconciliation[column], errors="coerce")
for column in ["chan_troi_quy", "chan_troi_nam", "MAPE_pct", "MAE_ty_vnd", "RMSE_ty_vnd", "MASE_mua_vu", "so_diem_kiem_thu"]:
    quarter_metrics[column] = pd.to_numeric(quarter_metrics[column], errors="coerce")
quarter_gdp_2010 = quarter_gdp_2010.dropna(subset=["gdp_thuc_ty_vnd_gia_2010"]).sort_values(["nam", "quy"])
quarter_gdp_2020 = quarter_gdp_2020.dropna(subset=["gdp_thuc_ty_vnd_gia_2020"]).sort_values(["nam", "quy"])
quality = frame("kiem_tra_chat_luong_du_lieu.csv")
activity_gdp = frame("du_lieu_gdp_nganh_chi_tiet.csv")
activity_updates = frame("du_lieu_gdp_nganh_chi_tiet_2026.csv")
activity_numeric = ["nam", "gdp_hien_hanh_ty_vnd", "ty_trong_gdp_hien_hanh_pct", "gdp_thuc_ty_vnd_theo_bang_nguon",
                    "chi_so_gdp_thuc_nam_truoc_100", "tang_truong_gdp_thuc_yoy_pct", "tang_truong_danh_nghia_yoy_pct",
                    "dong_gop_gdp_tang_truong_diem_pct", "bien_doi_ty_trong_5_nam_diem_pct", "bien_doi_ty_trong_10_nam_diem_pct"]
for col in activity_numeric:
    activity_gdp[col] = pd.to_numeric(activity_gdp[col], errors="coerce")
for col in ["tang_truong_gdp_thuc_yoy_pct", "ty_trong_dong_gop_tang_truong_pct", "ty_trong_gdp_9_thang_pct"]:
    activity_updates[col] = pd.to_numeric(activity_updates[col], errors="coerce")
version_path = ROOT / "data_version_manifest.json"
version = json.loads(version_path.read_text(encoding="utf-8")) if version_path.exists() else {"version_id": "Chưa tạo", "created_utc": "", "data_cutoff": {}, "files": []}

data_catalog = [
    {"dataset": "GDP thực quốc gia", "file": "du_lieu_gdp_thuc_va_tang_truong.csv", "source": "World Bank WDI", "url": "https://api.worldbank.org/v2/country/VNM/indicator/NY.GDP.MKTP.KD?date=1985:2025&format=json", "frequency": "Năm", "coverage": "1985–2025", "fields": "nam · gdp_thuc_usd_2015 · tang_truong_gdp_thuc_pct", "note": "Biến mục tiêu dự báo; giữ ở tần suất năm quan sát."},
    {"dataset": "GDP danh nghĩa & cơ cấu ngành", "file": "du_lieu_gdp_tong_hop.csv · du_lieu_gdp_co_cau_3_nganh.csv", "source": "World Bank WDI · NSO", "url": "https://api.worldbank.org/v2/country/VNM/indicator/NY.GDP.MKTP.CD?date=1985:2025&format=json", "frequency": "Năm", "coverage": "1985–2025 · cơ cấu 1986–2025", "fields": "gdp_danh_nghia_usd · giá trị gia tăng nông nghiệp/công nghiệp/dịch vụ · tỷ trọng ngành", "note": "Giá hiện hành, tách riêng với GDP thực; các ngành không nhất thiết cộng bằng GDP."},
    {"dataset": "GDP tăng trưởng theo quý", "file": "du_lieu_tang_truong_gdp_quy.csv", "source": "Cục Thống kê (NSO)", "url": "https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/10/thong-cao-bao-chi-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/", "frequency": "Quý", "coverage": "2026-Q1–Q3", "fields": "thoi_gian · tang_truong_gdp_so_voi_cung_ky_pct", "note": "Là tốc độ tăng trưởng cùng kỳ, không phải quy mô GDP quý."},
    {"dataset": "GDP thực theo quý · giá so sánh 2010", "file": "du_lieu_gdp_quy_muc_thuc_gia_2010.csv", "source": "NSDP / Cục Thống kê", "url": "https://nsdp.nso.gov.vn/GSO-chung/Tu%E1%BA%A5n%20Anh/excel%20chung/GDP_VNM.xlsx", "frequency": "Quý", "coverage": "2010-Q1–2025-Q4 · 64 quan sát", "fields": "GDP thực theo phương pháp sản xuất · tỷ VND giá 2010 · trạng thái nguồn", "note": "Mức GDP quan sát, được đối chiếu với GDP năm cùng workbook; không trộn với chuỗi giá 2020."},
    {"dataset": "GDP thực theo quý · giá so sánh 2020", "file": "du_lieu_gdp_quy_muc_thuc_gia_2020.csv", "source": "NSDP / Cục Thống kê", "url": "https://nsdp.nso.gov.vn/GSO-chung/Tu%E1%BA%A5n%20Anh/excel%20chung/GDP_VNM.xlsx", "frequency": "Quý", "coverage": "2025-Q1–Q3 · 2026-Q1–Q3", "fields": "GDP thực · tỷ VND giá 2020 · trạng thái nguồn", "note": "Chuỗi giá 2020 được tách riêng; không nối trực tiếp vào lịch sử giá 2010."},
    {"dataset": "Đối chiếu GDP quý với GDP năm", "file": "doi_chieu_gdp_thuc_quy_va_nam.csv", "source": "Tính từ workbook NSDP", "url": "https://nsdp.nso.gov.vn/", "frequency": "Năm", "coverage": "2010–2025", "fields": "GDP năm · tổng 4 quý · chênh lệch %", "note": "Đối chiếu mức GDP thực cùng năm gốc giá; sai số tối đa hiện khoảng 0,0018%."},
    {"dataset": "Backtest mô hình GDP thực quý", "file": "du_lieu_du_bao_gdp_quy_backtest.csv · so_sanh_hieu_qua_mo_hinh_gdp_quy.csv", "source": "Tính từ GDP quý NSDP", "url": "https://nsdp.nso.gov.vn/", "frequency": "Quý", "coverage": "Rolling-origin · 1, 4, 8, 12, 20 quý", "fields": "Seasonal Naive · Seasonal Drift · xu hướng log + mùa vụ · ETS", "note": "Bắt đầu sau 32 quý huấn luyện; origin chồng lấp, sai số không độc lập; chỉ bổ sung cho dự báo năm."},
    {"dataset": "CPI / lạm phát", "file": "du_lieu_cpi_phan_tich_thang.csv", "source": "NSO PXWeb · thông cáo NSO", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2011.%20CPI/E%2011.%20CPI__Px_E_11/E11.07.px/", "frequency": "Tháng", "coverage": "2020-01–2026-09", "fields": "thoi_gian · chi_so_cpi · CPI MoM/YoY · cờ nguồn", "note": "Mức CPI 2026 tái tạo từ tỷ lệ lũy kế công bố đã làm tròn; có cờ nhận diện."},
    {"dataset": "Tỷ giá VND/USD", "file": "du_lieu_fx_bien_dong_thang.csv · du_lieu_ty_gia_usd_vnd.csv", "source": "IMF International Financial Statistics", "url": "https://www.imf.org/en/Data", "frequency": "Tháng", "coverage": "1983-01–2026-07", "fields": "thoi_gian · ty_gia_usd_vnd · biến động MoM/YoY", "note": "Tỷ giá bình quân tháng VND trên USD; kỳ mới nhất trong dữ liệu là 2026-07."},
    {"dataset": "Xuất nhập khẩu hàng hóa", "file": "du_lieu_xuat_nhap_khau_thang_2026.csv", "source": "NSO · workbook thương mại", "url": "https://www.nso.gov.vn/wp-content/uploads/2026/03/E01-2026-7.xls", "frequency": "Tháng", "coverage": "2026-01–09", "fields": "thoi_gian · kim_ngach_xuat_khau_usd · kim_ngach_nhap_khau_usd · can_can_thuong_mai_usd", "note": "Dữ liệu tháng sơ bộ; USD được chuyển đổi từ đơn vị nghìn USD trong bảng nguồn."},
    {"dataset": "Chỉ số sản xuất công nghiệp (IIP)", "file": "du_lieu_san_xuat_iip_thang_2026.csv", "source": "NSO · workbook IIP", "url": "https://www.nso.gov.vn/wp-content/uploads/2026/10/IIP-Eng9.xlsx", "frequency": "Tháng", "coverage": "2026-01–09", "fields": "thoi_gian · chi_so_iip_toan_nganh_2015_100", "note": "IIP tháng theo gốc 2015=100; không ghép trực tiếp với chuỗi IIP năm có gốc khác."},
    {"dataset": "GRDP địa phương & vùng", "file": "du_lieu_grdp_63_tinh_thanh.csv", "source": "NSO PXWeb", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.12.px/", "frequency": "Năm", "coverage": "2018–2025 · 63 tỉnh truyền thống + 6 vùng", "fields": "ma_tinh · ten_tinh · ma_vung_kinh_te · nam · quy_mo_grdp_vnd · GRDP/người · tăng trưởng", "note": "Quy mô suy ra từ GRDP/người × dân số bình quân; 2025 ước tính; không cộng vùng cùng tỉnh thành phần."},
    {"dataset": "Backtest & dự báo GDP thực", "file": "du_lieu_du_bao_rolling_origin.csv · du_lieu_du_bao_gdp_thuc_den_2030.csv", "source": "Tính từ GDP thực World Bank", "url": "https://api.worldbank.org/v2/country/VNM/indicator/NY.GDP.MKTP.KD?date=1985:2025&format=json", "frequency": "Năm", "coverage": "Backtest 2005–2025 · dự báo 2026–2030", "fields": "nam_du_bao · mo_hinh · GDP thực thực tế/dự báo · sai số", "note": "Expanding-window backtest trên số liệu năm (tối thiểu 20 năm train); dự báo 2026–2030 là kịch bản mô hình, không phải số chính thức."},
    {"dataset": "Đấu trường kiểm định GDP theo mốc lịch sử", "file": "data/derived/forecast/backtest_arena.json", "source": "World Bank WDI · mô hình V-MEST", "url": "https://api.worldbank.org/v2/country/VNM/indicator/NY.GDP.MKTP.KD?date=1985:2025&format=json", "frequency": "Năm", "coverage": "Cutoff 2008/2019/2021/LATEST · chân trời 1–5 năm", "fields": "history · actual · forecast · MAE/RMSE/MAPE · SARIMAX coverage", "note": "Artifact tiền tính từ GDP thực USD cố định 2015; không huấn luyện trên Render. Cutoff LATEST chưa có thực tế để xếp hạng."},
    {"dataset": "Bán lẻ tiêu dùng", "file": "du_lieu_ban_le_tieu_dung.csv · du_lieu_ban_le_tieu_dung_thang_2026.csv", "source": "NSO", "url": "https://www.nso.gov.vn/", "frequency": "Năm · tháng", "coverage": "1990–2025 · 2026-01–09", "fields": "tổng mức bán lẻ · tăng danh nghĩa · tăng thực lũy kế", "note": "Tăng trưởng thực năm là proxy đã giảm CPI; chuỗi 2026 là lũy kế theo kỳ báo cáo."},
    {"dataset": "FDI", "file": "du_lieu_fdi_dau_tu.csv · du_lieu_fdi_luy_ke_2026.csv", "source": "NSO", "url": "https://www.nso.gov.vn/", "frequency": "Năm · lũy kế", "coverage": "1991–2025 · 9 tháng 2026", "fields": "vốn đăng ký · vốn thực hiện · tăng trưởng lũy kế", "note": "Số 9 tháng 2026 dùng định nghĩa đăng ký tổng hợp; tách khỏi vốn dự án cấp phép năm."},
    {"dataset": "GDP theo chi tiêu & đóng góp tăng trưởng", "file": "du_lieu_gdp_theo_chi_tieu.csv · du_lieu_dong_gop_gdp_theo_chi_tieu.csv", "source": "NSO PXWeb", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.09.px/", "frequency": "Năm", "coverage": "2005–2025", "fields": "tiêu dùng · tích lũy vốn · tồn kho · cán cân hàng hóa-dịch vụ · đóng góp điểm %", "note": "Giá cố định 2010; 2024 sơ bộ, 2025 ước tính. Không phân rã 2010 do đổi năm gốc."},
    {"dataset": "GDP thực theo ngành", "file": "du_lieu_gdp_thuc_theo_nganh.csv", "source": "NSO PXWeb", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.03.px/", "frequency": "Năm", "coverage": "2005–2025", "fields": "GDP giá cố định 2010 · ngành · tăng trưởng thực", "note": "Tách tốc độ tăng khỏi cơ cấu GDP danh nghĩa; 2025 ước tính."},
    {"dataset": "GDP hiện hành theo hoạt động kinh tế", "file": "du_lieu_gdp_nganh_chi_tiet.csv", "source": "NSO PXWeb · E03.04-05", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.04-05.px/", "frequency": "Năm", "coverage": "2005–2025", "fields": "hoạt động · GDP hiện hành · cơ cấu GDP · GDP giá cố định · chỉ số tăng trưởng · đóng góp điểm %", "note": "21 hoạt động kinh tế và thuế sản phẩm. 2025 ước tính. GDP danh nghĩa khác GDP thực; không so mức giá cố định qua điểm đổi mốc 2010."},
    {"dataset": "Tăng trưởng GDP chi tiết mới nhất", "file": "du_lieu_gdp_nganh_chi_tiet_2026.csv", "source": "Cục Thống kê (NSO)", "url": "https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/10/thong-cao-bao-chi-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/", "frequency": "Quý III · lũy kế 9 tháng", "coverage": "2026-Q3 · 2026-9M", "fields": "hoạt động · tăng GDP thực cùng kỳ · tỷ trọng đóng góp · cơ cấu GDP 9 tháng ở cấp khu vực", "note": "Ước tính NSO. Tỷ trọng đóng góp là phần của mức tăng tổng giá trị tăng thêm, không phải điểm % hay tỷ trọng GDP. Ngành con không có mức GDP hiện hành riêng."},
    {"dataset": "Việc làm theo ngành", "file": "du_lieu_lao_dong_theo_nganh.csv", "source": "NSO PXWeb", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2002.%20Population%20and%20Employment/E%2002.%20Population%20and%20Employment__Px_E_02/E02.42.px/", "frequency": "Năm", "coverage": "2005, 2007–2025", "fields": "số lao động · tỷ trọng theo hoạt động kinh tế", "note": "2025 sơ bộ; nguồn không có quan sát năm 2006."},
    {"dataset": "Năng suất lao động", "file": "du_lieu_nang_suat_lao_dong.csv · du_lieu_nang_suat_thuc_theo_khu_vuc.csv", "source": "NSO PXWeb · tính từ GDP và lao động", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2002.%20Population%20and%20Employment/E%2002.%20Population%20and%20Employment__Px_E_02/E02.57.px/", "frequency": "Năm", "coverage": "2005, 2007–2025", "fields": "NSO danh nghĩa · proxy GDP thực/lao động giá 2010", "note": "Chuỗi NSO là giá hiện hành; proxy ba khu vực không đồng nhất với chỉ tiêu năng suất chính thức."},
    {"dataset": "Thất nghiệp theo vùng", "file": "du_lieu_that_nghiep_vung.csv", "source": "NSO PXWeb", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2002.%20Population%20and%20Employment/E%2002.%20Population%20and%20Employment__Px_E_02/E02.59.px/", "frequency": "Năm", "coverage": "2010–2025", "fields": "vùng · thành thị/nông thôn · tỷ lệ thất nghiệp", "note": "2025 sơ bộ; không đo đầy đủ thiếu việc làm hoặc chất lượng việc làm."},
    {"dataset": "Đầu tư theo sở hữu và ngành", "file": "du_lieu_dau_tu_theo_loai_hinh.csv · du_lieu_dau_tu_theo_nganh_thuc.csv", "source": "NSO PXWeb", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2004.%20Investment%20and%20construction/E%2004.%20Investment%20and%20construction__Px_E_04/E04.01.px/", "frequency": "Năm", "coverage": "2010–2025", "fields": "giá hiện hành/giá cố định 2010 · sở hữu · cơ cấu · ngành", "note": "Vốn giải ngân không đồng nhất với FDI đăng ký/cấp phép; 2025 sơ bộ."},
    {"dataset": "Thu và chi ngân sách", "file": "du_lieu_tai_khoa_ngan_sach.csv", "source": "NSO PXWeb", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.16.px/", "frequency": "Năm", "coverage": "Thu 2000–2025 · chi 2005–2025", "fields": "thu/chi theo khoản · đầu tư phát triển · cơ cấu · % GDP", "note": "Giá hiện hành; 2025 ước tính. Chênh thu-chi giản lược không phải thâm hụt đã điều chỉnh."},
    {"dataset": "Tín dụng và lãi suất", "file": "du_lieu_tin_dung_du_no.csv · du_lieu_lai_suat_ngan_hang.csv", "source": "NSO PXWeb", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/?tablelist=true", "frequency": "Năm", "coverage": "2015–2025", "fields": "dư nợ theo kỳ hạn/loại tiền · tăng trưởng · lãi suất · tín dụng/GDP", "note": "Dư nợ danh nghĩa cuối năm; 2025 sơ bộ. Tương quan không thể hiện chiều nhân quả."},
    {"dataset": "Cán cân thanh toán", "file": "du_lieu_can_can_thanh_toan.csv", "source": "NSO PXWeb", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.20.px/", "frequency": "Năm", "coverage": "2018–2025", "fields": "tài khoản vãng lai · hàng hóa/dịch vụ · tài khoản tài chính · % GDP", "note": "Triệu USD; 2025 sơ bộ; không đồng nhất với cán cân hàng hóa hải quan."},
    {"dataset": "Đóng góp TFP", "file": "du_lieu_dong_gop_tfp.csv", "source": "NSO PXWeb", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/E03.27.px/", "frequency": "Kỳ 5 năm", "coverage": "2011–2015 · 2016–2020 · 2021–2025", "fields": "đóng góp vốn · lao động · TFP · tăng trưởng TFP", "note": "Giữ nguyên kỳ 5 năm công bố; không nội suy thành chuỗi năm."},
    {"dataset": "Giá hàng hóa quốc tế", "file": "du_lieu_gia_hang_hoa_quoc_te.csv", "source": "World Bank Pink Sheet", "url": "https://www.worldbank.org/en/research/commodity-markets", "frequency": "Tháng", "coverage": "Theo từng chuỗi đến 2026-09", "fields": "dầu · than · khí · gạo Việt Nam 5% · urê · quặng sắt · đồng", "note": "USD danh nghĩa quốc tế; không phải giá nhập khẩu hoặc giá trong nước Việt Nam."},
    {"dataset": "So sánh động lực GDP & tương quan", "file": "du_lieu_so_sanh_dong_luc_gdp.csv · du_lieu_tuong_quan_dong_luc_gdp.csv", "source": "NSO · World Bank · tính từ dữ liệu hệ thống", "url": "https://pxweb.nso.gov.vn/pxweb/en/E%2003.%20National%20Accounts%20and%20State%20budget/E%2003.%20National%20Accounts%20and%20State%20budget__Px_E_03/?tablelist=true", "frequency": "Năm", "coverage": "1985–2025 tùy biến số", "fields": "GDP · chi tiêu · ngành · lao động · đầu tư · tài khóa · tín dụng · đối ngoại · giá hàng hóa", "note": "Pearson/Spearman dùng cặp năm đủ dữ liệu; n riêng từng cặp; chỉ tương quan mô tả."},
]

annual_fx = macro_annual["ty_gia_usd_vnd_binh_quan_nam"].pct_change() * 100
macro_records = []
for idx, row in macro_annual.iterrows():
    macro_records.append({
        "year": int(row["nam"]), "realGrowth": safe_num(row["tang_truong_gdp_thuc_pct"]),
        "nominalGrowth": safe_num(row["tang_truong_gdp_danh_nghia_usd_yoy_pct"]),
        "inflation": safe_num(row["lam_phat_cpi_yoy_pct"]), "fxGrowth": safe_num(annual_fx.loc[idx]),
        "tradeToGdp": safe_num(row["trade_to_gdp_pct"]), "balanceToGdp": safe_num(row["can_can_thuong_mai_tren_gdp_pct"]),
        "fdiToGdp": safe_num(row["von_fdi_thuc_hien_tren_gdp_pct"]),
        "retailNominalGrowth": safe_num(row["tang_truong_ban_le_danh_nghia_yoy_pct"]),
        "retailRealGrowth": safe_num(row["tang_truong_ban_le_thuc_uoc_tinh_yoy_pct"]),
    })

activity_details = [{
    "year": int(r.nam), "sectorKey": str(r.khu_vuc_ma), "sector": str(r.khu_vuc),
    "activity": str(r.hoat_dong_kinh_te), "sourceActivity": str(r.hoat_dong_kinh_te_nguon),
    "nominal": safe_num(r.gdp_hien_hanh_ty_vnd), "share": safe_num(r.ty_trong_gdp_hien_hanh_pct),
    "realLevel": safe_num(r.gdp_thuc_ty_vnd_theo_bang_nguon), "realIndex": safe_num(r.chi_so_gdp_thuc_nam_truoc_100),
    "realGrowth": safe_num(r.tang_truong_gdp_thuc_yoy_pct), "nominalGrowth": safe_num(r.tang_truong_danh_nghia_yoy_pct),
    "contribution": safe_num(r.dong_gop_gdp_tang_truong_diem_pct), "shareChange5": safe_num(r.bien_doi_ty_trong_5_nam_diem_pct),
    "shareChange10": safe_num(r.bien_doi_ty_trong_10_nam_diem_pct), "status": str(r.trang_thai),
} for r in activity_gdp.itertuples(index=False)]
activity_update_records = [{
    "period": str(r.ky), "periodLabel": str(r.ky_hien_thi), "sectorKey": str(r.khu_vuc_ma),
    "activity": str(r.hoat_dong_kinh_te), "realGrowth": safe_num(r.tang_truong_gdp_thuc_yoy_pct),
    "contributionShare": safe_num(r.ty_trong_dong_gop_tang_truong_pct), "gdpShare": safe_num(r.ty_trong_gdp_9_thang_pct),
    "analysisLevel": str(r.cap_phan_tich), "status": str(r.trang_thai), "source": str(r.nguon_url),
} for r in activity_updates.itertuples(index=False)]

scatter_specs = [
    ("Tăng trưởng GDP thực và lạm phát CPI năm", "tang_truong_gdp_thuc_pct", "lam_phat_cpi_yoy_pct", "realGrowth", "inflation"),
    ("Tăng trưởng GDP thực và biến động tỷ giá bình quân năm", "tang_truong_gdp_thuc_pct", "tang_truong_ty_gia_binh_quan_nam_yoy_pct", "realGrowth", "fxGrowth"),
    ("Tăng trưởng GDP thực và IIP cùng năm", "tang_truong_gdp_thuc_pct", "tang_truong_iip_yoy_pct", "realGrowth", "iip0"),
    ("Tăng trưởng GDP thực và IIP năm trước", "tang_truong_gdp_thuc_pct", "tang_truong_iip_t_minus_1_pct", "realGrowth", "iip1"),
    ("Tăng trưởng GDP thực và IIP trễ 2 năm", "tang_truong_gdp_thuc_pct", "tang_truong_iip_t_minus_2_pct", "realGrowth", "iip2"),
    ("Tăng trưởng GDP thực và IIP trễ 3 năm", "tang_truong_gdp_thuc_pct", "tang_truong_iip_t_minus_3_pct", "realGrowth", "iip3"),
    ("Tăng trưởng GDP thực và tăng trưởng bán lẻ thực ước tính", "tang_truong_gdp_thuc_pct", "tang_truong_ban_le_thuc_uoc_tinh_yoy_pct", "realGrowth", "retailRealGrowth"),
    ("Tăng trưởng GDP danh nghĩa USD và biến động tỷ giá", "tang_truong_gdp_danh_nghia_usd_yoy_pct", "tang_truong_ty_gia_binh_quan_nam_yoy_pct", "nominalGrowth", "fxGrowth"),
]
corr_stats = {}
for _, row in correlation_source.iterrows():
    key = (str(row["bien_x"]), str(row["bien_y"]))
    corr_stats.setdefault(key, {})[str(row["phuong_phap"]).lower()] = safe_num(row["he_so_tuong_quan"])
    corr_stats[key]["n"] = int(row["so_quan_sat"])
annual_by_year = {int(row["nam"]): row for _, row in macro_annual.iterrows()}
iip_by_year = {int(row["nam"]): row for _, row in iip_annual.iterrows()}
scatter_data = []
for title, xsource, ysource, xkey, ykey in scatter_specs:
    points = []
    for year, annual_row in annual_by_year.items():
        if ykey in ("iip0", "iip1", "iip2", "iip3"):
            source_row = iip_by_year.get(year)
            xvalue = safe_num(annual_row[xsource])
            lag_column = {"iip0": "tang_truong_iip_t_minus_0_pct", "iip1": "tang_truong_iip_t_minus_1_pct", "iip2": "tang_truong_iip_t_minus_2_pct", "iip3": "tang_truong_iip_t_minus_3_pct"}[ykey]
            yvalue = safe_num(source_row[lag_column]) if source_row is not None else None
        else:
            xvalue = safe_num(annual_row[xsource])
            if ykey == "fxGrowth":
                yvalue = safe_num(annual_fx.loc[annual_row.name])
            else:
                yvalue = safe_num(annual_row[ysource])
        if xvalue is not None and yvalue is not None:
            points.append({"year": year, "x": xvalue, "y": yvalue})
    stats = corr_stats.get((xsource, ysource), {})
    if "pearson" not in stats and points:
        xs = pd.Series([point["x"] for point in points], dtype=float)
        ys = pd.Series([point["y"] for point in points], dtype=float)
        stats = {"pearson": safe_num(xs.corr(ys, method="pearson")), "spearman": safe_num(xs.corr(ys, method="spearman")), "n": len(points)}
    scatter_data.append({"title": title, "points": points, "pearson": stats.get("pearson"),
                         "spearman": stats.get("spearman"), "n": stats.get("n", len(points))})

sector_compare_rows = [{
    "name": str(row.nhom_nganh), "value": safe_num(row.gia_tri_danh_nghia_2025_vnd_ty),
    "share": safe_num(row.ty_trong_gdp_2025_pct), "growth": safe_num(row.tang_truong_danh_nghia_2025_yoy_pct),
    "shareChange": safe_num(row.thay_doi_ty_trong_2025_so_voi_2024_diem_pct),
} for row in sector_compare.itertuples(index=False)]
macro_by_year = {row["year"]: row for row in macro_records}
retail_annual_rows = [{"year": int(row.nam), "totalT": safe_num(row.tong_muc_ban_le_vnd / 1e12),
                       "realGrowth": macro_by_year.get(int(row.nam), {}).get("retailRealGrowth"),
                       "nominalGrowth": macro_by_year.get(int(row.nam), {}).get("retailNominalGrowth")}
                      for row in retail_annual.itertuples(index=False)]
retail_month_rows = [{"month": str(row.thoi_gian)[:7], "totalT": safe_num(row.tong_muc_ban_le_vnd / 1e12),
                      "nominalGrowth": safe_num(row.tang_truong_danh_nghia_yoy_pct),
                      "realCumulative": safe_num(row.tang_truong_thuc_yoy_luy_ke_pct)}
                     for row in retail_monthly.itertuples(index=False)]
fdi_annual_rows = [{"year": int(row.nam), "registeredB": safe_num(row.von_dang_ky_du_an_fdi_usd / 1e9),
                    "implementedB": safe_num(row.von_fdi_thuc_hien_usd / 1e9)}
                   for row in fdi_annual.itertuples(index=False)]
fdi_latest_row = fdi_latest.iloc[-1]
monthly_macro_rows = [{"month": row.thoi_gian.strftime("%Y-%m"), "cpi100": safe_num(row.cpi_index_100),
                       "fx100": safe_num(row.fx_index_100)} for row in cpi_fx.itertuples(index=False)]

# Additional official growth-driver datasets and derived analytical views.
def json_records(frame_value: pd.DataFrame):
    return json.loads(frame_value.to_json(orient="records", force_ascii=False))

growth_contributions = frame("du_lieu_dong_gop_gdp_theo_chi_tieu.csv")
growth_sectors = frame("du_lieu_gdp_thuc_theo_nganh.csv")
growth_sectors = growth_sectors[growth_sectors["ma_nganh"].isin(["nong_nghiep", "cong_nghiep_xay_dung", "dich_vu"])].copy()
growth_employment = frame("du_lieu_lao_dong_theo_nganh.csv")
activity_industry = {"Mining and quarrying", "Manufacturing", "Electricity, gas, stream and air conditioning supply",
                     "Water supply, sewerage, waste management and remediation activities", "Construction"}
def broad_activity(value):
    if value == "Agriculture, forestry and fishing": return "Nông, lâm, thủy sản"
    if value in activity_industry: return "Công nghiệp và xây dựng"
    return "Dịch vụ"
employment_groups = []
for measure, column in [("so_luong", "so_lao_dong_nghin_nguoi"), ("co_cau", "ty_trong_lao_dong_pct")]:
    subset = growth_employment[growth_employment["loai_chi_tieu"].eq(measure) & growth_employment["hoat_dong_kinh_te"].ne("TOTAL")].copy()
    subset["khu_vuc"] = subset["hoat_dong_kinh_te"].map(broad_activity)
    employment_groups.append(subset.groupby(["nam", "khu_vuc"], as_index=False)[column].sum())
labor_wide = employment_groups[0].merge(employment_groups[1], on=["nam", "khu_vuc"], how="outer").sort_values(["nam", "khu_vuc"])
productivity_proxy = frame("du_lieu_nang_suat_thuc_theo_khu_vuc.csv")
investment_expanded = frame("du_lieu_dau_tu_theo_loai_hinh.csv")
investment_real = investment_expanded[(investment_expanded["loai_gia_tri"].eq("gia_tri_thuc_2010_vnd_ty")) & investment_expanded["loai_hinh_so_huu"].ne("Tổng")].copy()
investment_real["gia_tri_nghin_ty_vnd"] = pd.to_numeric(investment_real["gia_tri"], errors="coerce") / 1000
investment_shares = investment_expanded[(investment_expanded["loai_gia_tri"].eq("ty_trong_pct")) & investment_expanded["loai_hinh_so_huu"].ne("Tổng")].rename(columns={"gia_tri": "ty_trong_pct"})
driver_panel = frame("du_lieu_so_sanh_dong_luc_gdp.csv")
credit_driver = frame("du_lieu_tin_dung_du_no.csv")
credit_driver = credit_driver[(credit_driver["chi_tieu"].str.lower().eq("outstanding")) & (credit_driver["ky_han_ngoai_te"].str.lower().eq("total")) & (credit_driver["loai_gia_tri"].eq("tang_truong_pct"))]
rates_driver = frame("du_lieu_lai_suat_ngan_hang.csv")
rate_labels = {
    "Deposits In Vietnamese Dong 3 - month term": "Tiền gửi VND 3 tháng",
    "Deposits In Vietnamese Dong 12 - month term": "Tiền gửi VND 12 tháng",
    "Bank loans In Vietnamese Dong: Short-term": "Cho vay VND ngắn hạn",
    "Bank loans In Vietnamese Dong: Medium and long-term": "Cho vay VND trung/dài hạn",
}
rates_driver = rates_driver[rates_driver["loai_lai_suat"].isin(rate_labels)].copy()
rates_driver["nhan"] = rates_driver["loai_lai_suat"].map(rate_labels)
bop_driver = frame("du_lieu_can_can_thanh_toan.csv")
bop_driver = bop_driver[bop_driver["chi_tieu"].str.lower().str.contains("current account as percent")].copy()
unemployment_driver = frame("du_lieu_that_nghiep_vung.csv")
tfp_driver = frame("du_lieu_dong_gop_tfp.csv")
commodity_driver = frame("du_lieu_gia_hang_hoa_quoc_te.csv")
commodity_driver["thoi_gian"] = pd.to_datetime(commodity_driver["thoi_gian"], errors="coerce")
commodity_driver["gia_usd"] = pd.to_numeric(commodity_driver["gia_usd"], errors="coerce")
commodity_driver["nam"] = commodity_driver["thoi_gian"].dt.year
commodity_base = commodity_driver[commodity_driver["nam"].eq(2015)].groupby("hang_hoa")["gia_usd"].mean()
commodity_driver["chi_so_2015_100"] = commodity_driver.apply(lambda r: r["gia_usd"] / commodity_base.get(r["hang_hoa"], float("nan")) * 100, axis=1)
commodity_driver = commodity_driver[commodity_driver["thoi_gian"].ge("2010-01-01")].copy()
commodity_driver["thoi_gian"] = commodity_driver["thoi_gian"].dt.strftime("%Y-%m")
growth_driver_data = {
    "contributions": json_records(growth_contributions),
    "sectorGrowth": json_records(growth_sectors[["nam", "nganh", "ma_nganh", "tang_truong_yoy_pct", "trang_thai"]]),
    "employment": json_records(labor_wide),
    "productivity": json_records(productivity_proxy[["nam", "khu_vuc", "nang_suat_thuc_proxy_trieu_vnd_2010_nguoi", "tang_truong_nang_suat_thuc_proxy_yoy_pct"]]),
    "investment": json_records(investment_real[["nam", "loai_hinh_so_huu", "gia_tri_nghin_ty_vnd", "trang_thai"]]),
    "investmentShares": json_records(investment_shares[["nam", "loai_hinh_so_huu", "ty_trong_pct", "trang_thai"]]),
    "panel": json_records(driver_panel),
    "creditGrowth": json_records(credit_driver[["nam", "gia_tri", "trang_thai"]].rename(columns={"gia_tri": "tang_truong_du_no_yoy_pct"})),
    "rates": json_records(rates_driver[["nam", "nhan", "gia_tri_pct", "trang_thai"]]),
    "currentAccount": json_records(bop_driver[["nam", "gia_tri", "trang_thai"]].rename(columns={"gia_tri": "can_can_vang_lai_tren_gdp_pct"})),
    "unemployment": json_records(unemployment_driver),
    "tfp": json_records(tfp_driver),
    "commodities": json_records(commodity_driver[["thoi_gian", "hang_hoa", "gia_usd", "don_vi_nguon", "chi_so_2015_100", "thay_doi_yoy_pct"]]),
    "correlations": json_records(frame("du_lieu_tuong_quan_dong_luc_gdp.csv")),
}

data = {
    "gdp": [
        {"year": int(r.nam), "realB": round(float(r.gdp_thuc_usd_2015) / 1e9, 4),
         "growth": round(float(r.tang_truong_gdp_thuc_pct), 4) if pd.notna(r.tang_truong_gdp_thuc_pct) else None,
         "nominalUsdB": round(float(r.gdp_danh_nghia_usd) / 1e9, 4) if pd.notna(r.gdp_danh_nghia_usd) else None}
        for r in gdp.itertuples(index=False)
    ],
    "sectors": sector_items,
    "activityDetails": activity_details,
    "activityUpdates": activity_update_records,
    "sectorCompare": sector_compare_rows,
    "macroAnnual": macro_records,
    "monthlyMacro": monthly_macro_rows,
    "scatterComparisons": scatter_data,
    "growthDrivers": growth_driver_data,
    "retailAnnual": retail_annual_rows,
    "retailMonthly": retail_month_rows,
    "fdiAnnual": fdi_annual_rows,
    "fdiLatest": {"period": str(fdi_latest_row.thoi_gian)[:10], "registeredB": safe_num(fdi_latest_row.von_fdi_dang_ky_tong_hop_usd / 1e9),
                   "implementedB": safe_num(fdi_latest_row.von_fdi_thuc_hien_luy_ke_usd / 1e9),
                   "registeredGrowth": safe_num(fdi_latest_row.tang_truong_dang_ky_yoy_pct),
                   "implementedGrowth": safe_num(fdi_latest_row.tang_truong_thuc_hien_yoy_pct), "periodLabel": str(fdi_latest_row.ky_bao_cao)},
    "quarterly": [{"period": str(r.thoi_gian), "growth": float(r.tang_truong_gdp_so_voi_cung_ky_pct)} for r in qgdp.itertuples(index=False)],
    "quarterlyGDP2010": [{"period": str(r.thoi_gian), "year": int(r.nam), "quarter": int(r.quy), "value": float(r.gdp_thuc_ty_vnd_gia_2010) / 1000} for r in quarter_gdp_2010.itertuples(index=False)],
    "quarterlyGDP2020": [{"period": str(r.thoi_gian), "year": int(r.nam), "quarter": int(r.quy), "value": float(r.gdp_thuc_ty_vnd_gia_2020) / 1000} for r in quarter_gdp_2020.itertuples(index=False)],
    "quarterlyReconciliation": [{"year": int(r.nam), "annual": float(r.gdp_thuc_nam_ty_vnd_gia_2010) / 1000, "quarterSum": float(r.tong_4_quy_ty_vnd_gia_2010) / 1000, "differencePct": float(r.chenh_lech_pct), "status": str(r.trang_thai_doi_chieu)} for r in quarter_reconciliation.itertuples(index=False)],
    "quarterlyMetrics": [{"horizon": int(r.chan_troi_quy), "model": str(r.mo_hinh), "n": int(r.so_diem_kiem_thu), "mape": float(r.MAPE_pct), "maeT": float(r.MAE_ty_vnd) / 1000, "rmseT": float(r.RMSE_ty_vnd) / 1000, "mase": float(r.MASE_mua_vu)} for r in quarter_metrics.itertuples(index=False)],
    "quarterlyBacktest": [{"target": str(r.ky_du_bao), "origin": str(r.ky_goc_du_bao), "horizon": int(r.chan_troi_quy), "model": str(r.mo_hinh), "actualT": float(r.gdp_thuc_thuc_te_ty_vnd_gia_2010) / 1000, "forecastT": float(r.gdp_thuc_du_bao_ty_vnd_gia_2010) / 1000} for r in quarter_backtest.itertuples(index=False)],
    "trade": [{"month": str(r.thoi_gian)[:7], "export": round(float(r.kim_ngach_xuat_khau_usd), 3),
               "import": round(float(r.kim_ngach_nhap_khau_usd), 3), "balance": round(float(r.can_can_thuong_mai_usd), 3)}
              for r in trade.itertuples(index=False)],
    "iip": [{"month": str(r.thoi_gian)[:7], "index": float(r.chi_so_iip_toan_nganh_2015_100)} for r in iip.itertuples(index=False)],
    "grdpYears": grdp_years,
    "regions": regions_by_year,
    "provinces": provinces_by_year,
    "models": [{"name": str(r.mo_hinh), "mape": float(r.MAPE_pct), "rmse": float(r.RMSE_usd_2015)} for r in models.itertuples(index=False)],
    "metricsByHorizon": [{"horizon": int(r.chan_troi_nam), "model": str(r.mo_hinh), "n": int(r.so_diem_kiem_thu), "mape": float(r.MAPE_pct), "smape": float(r.sMAPE_pct), "rmse": float(r.RMSE_usd_2015) / 1e9, "mae": float(r.MAE_usd_2015) / 1e9, "mase": float(r.MASE_vs_naive_train)} for r in horizon_metrics.itertuples(index=False)],
    "rolling": [{"year": int(r.nam_du_bao), "model": str(r.mo_hinh),
                  "actualB": float(r.gdp_thuc_thuc_te_usd_2015) / 1e9,
                  "forecastB": float(r.gdp_thuc_du_bao_usd_2015) / 1e9}
                 for r in rolling.itertuples(index=False)],
    "forecast2030": [{"year": int(r.nam_du_bao), "model": str(r.mo_hinh),
                      "horizon": int(r.chan_troi_nam), "valueB": float(r.gdp_thuc_du_bao_usd_2015) / 1e9,
                      "lower80B": float(r.can_duoi_80_kinh_nghiem_usd_2015) / 1e9,
                      "upper80B": float(r.can_tren_80_kinh_nghiem_usd_2015) / 1e9,
                      "calibrationN": int(r.so_mau_hieu_chuan)}
                     for r in forecast_2030.itertuples(index=False)],
    "rollingHorizons": [{"year": int(r.nam_du_bao), "originYear": int(r.nam_goc), "horizon": int(r.chan_troi_nam), "model": str(r.mo_hinh), "actualB": float(r.gdp_thuc_thuc_te_usd_2015) / 1e9, "forecastB": float(r.gdp_thuc_du_bao_usd_2015) / 1e9} for r in horizon_backtest.itertuples(index=False)],
    "quality": [{"file": str(r.tep), "rows": int(r.so_dong_du_lieu), "duplicates": int(r.so_dong_trung_khoa), "missingKey": int(r.so_o_thieu_tren_khoa), "missing": int(r.so_o_thieu), "status": str(r.ket_qua), "note": str(r.ghi_chu)} for r in quality.itertuples(index=False)],
    "version": {"id": version.get("version_id", "Chưa tạo"), "created": version.get("created_utc", ""), "cutoff": version.get("data_cutoff", {}), "fileCount": len(version.get("files", [])), "archive": version.get("archive", "")},
    "versionManifest": version,
    "catalog": data_catalog,
    "latest": {
        "nominalUsdB": round(float(gdp.loc[gdp["nam"].eq(2025), "gdp_danh_nghia_usd"].iloc[0]) / 1e9, 2),
        "realGrowth": round(float(real.loc[real["nam"].eq(2025), "tang_truong_gdp_thuc_pct"].iloc[0]), 2),
        "quarterGrowth": [float(v) for v in qgdp["tang_truong_gdp_so_voi_cung_ky_pct"].dropna().tolist()],
        "cpiNineMonth": 4.52,
        "fxDate": str(fx.iloc[-1]["thoi_gian"])[:7],
        "fxValue": float(fx.iloc[-1]["ty_gia_usd_vnd"]),
        "cpiDate": str(cpi_month.iloc[-1]["thoi_gian"])[:7],
        "provinceCount": int(province_rows["ten_tinh"].nunique()), "regionCount": int(region_rows["ten_vung_kinh_te"].nunique()),
    },
}

catalog_manifest = json.loads((ROOT / "data" / "catalog.json").read_text(encoding="utf-8"))
refresh_manifest = json.loads((ROOT / "refresh_manifest.json").read_text(encoding="utf-8"))
analysis_manifest = json.loads((ROOT / "analysis_manifest.json").read_text(encoding="utf-8"))

def collect_source_urls(value):
    if isinstance(value, str):
        return [value] if value.startswith("http://") or value.startswith("https://") else []
    if isinstance(value, dict):
        return [url for child in value.values() for url in collect_source_urls(child)]
    if isinstance(value, list):
        return [url for child in value for url in collect_source_urls(child)]
    return []

catalog_files = catalog_manifest.get("files", {})
catalog_records = catalog_files.values() if isinstance(catalog_files, dict) else catalog_files
external_sources = sorted({
    str(record.get("source", ""))
    for record in catalog_records
    if isinstance(record, dict) and record.get("source") and record.get("source") != "Phân tích hệ thống"
})
forecast_models = analysis_manifest.get("forecast_evaluation", {}).get("models", [])
model_labels = {
    "Naive_last_value": "Naive — giữ nguyên mức GDP gần nhất",
    "Drift_mean_log_change": "Drift — ngoại suy thay đổi log trung bình",
    "Linear_log_trend": "Xu hướng tuyến tính trên log GDP",
    "GRU_logGDP": "GRU",
    "LSTM_logGDP": "LSTM",
}
data["projectInfo"] = {
    "dataFileCount": len(catalog_files),
    "sourceGroups": external_sources,
    "sourceUrls": sorted(set(collect_source_urls(refresh_manifest.get("sources", {})) + ["https://nsdp.nso.gov.vn/", "https://nsdp.nso.gov.vn/GSO-chung/Tu%E1%BA%A5n%20Anh/excel%20chung/GDP_VNM.xlsx"])),
    "models": [{"name": name, "label": model_labels.get(name, name)} for name in forecast_models],
    "quarterlyModels": [{"name": name, "label": label} for name, label in {
        "SeasonalNaive": "Seasonal Naive — lặp lại mức cùng quý năm trước",
        "SeasonalDrift": "Seasonal Drift — xu thế cùng quý theo log GDP",
        "LogTrendQuarterDummies": "Xu hướng log + biến giả quý",
        "ETS_DampedAdditive": "ETS — xu hướng giảm tốc, mùa vụ cộng 4 quý",
    }.items()],
}

sector_page_specs = [
    ("agriculture", "Nông, lâm, thủy sản", "Tăng trưởng, cơ cấu GDP hiện hành và diễn biến GDP thực; số năm 2025 là ước tính NSO.",
     "Bảng GDP năm chỉ có một dòng tổng hợp nông, lâm nghiệp và thủy sản. Báo cáo 9 tháng 2026 tách riêng tốc độ tăng của nông nghiệp, lâm nghiệp và thủy sản; các mức GDP danh nghĩa chi tiết theo ba nhánh chưa được công bố trong bảng này."),
    ("industry", "Công nghiệp, xây dựng", "So sánh khai khoáng, chế biến chế tạo, điện, nước và xây dựng; danh nghĩa và thực được tách riêng.",
     "Bảng GDP năm công bố 5 hoạt động lớn trong khu vực này. Chỉ số IIP theo ngành sâu hơn là chỉ số sản lượng công nghiệp, không phải GDP/giá trị gia tăng; trang này không dùng IIP thay cho GDP."),
    ("services", "Dịch vụ", "Phân tích 14 hoạt động dịch vụ theo GDP danh nghĩa, tỷ trọng và tốc độ tăng GDP thực.",
     "Bảng năm có 14 hoạt động dịch vụ. Báo cáo 9 tháng 2026 chỉ nêu tăng trưởng và tỷ trọng đóng góp cho một số hoạt động; không suy ra quy mô GDP con khi nguồn không công bố."),
]
sector_pages_html = "".join(f'''\n      <section id="sector-{key}" class="section page">
        <div class="section-head"><div><h2>{title}</h2><span class="sub">{subtitle}</span></div><button id="download-activity-{key}" class="select export-btn" type="button">Tải dữ liệu khu vực</button></div>
        <div class="kpis">
          <article class="kpi"><div class="kpi-head"><span>GDP giá hiện hành · 2025</span><span class="kpi-icon">▤</span></div><div class="kpi-value" id="activity-{key}-nominal">—</div><div class="kpi-foot">Tỷ VND · NSO · ước tính</div></article>
          <article class="kpi"><div class="kpi-head"><span>Tỷ trọng GDP · 2025</span><span class="kpi-icon">◷</span></div><div class="kpi-value" id="activity-{key}-share">—</div><div class="kpi-foot">Giá hiện hành · có thuế sản phẩm tách riêng</div></article>
          <article class="kpi"><div class="kpi-head"><span>Tăng GDP thực · 2025</span><span class="kpi-icon">↗</span></div><div class="kpi-value" id="activity-{key}-growth">—</div><div class="kpi-foot">Chỉ số giá cố định của NSO</div></article>
          <article class="kpi"><div class="kpi-head"><span>Tăng GDP thực · 9 tháng 2026</span><span class="kpi-icon">▥</span></div><div class="kpi-value" id="activity-{key}-growth-2026">—</div><div class="kpi-foot">Ước tính cùng kỳ · nguồn NSO</div></article>
        </div>
        <div class="grid-main">
          <article class="panel"><div class="section-head"><div><div class="panel-title">Tăng trưởng GDP thực theo hoạt động</div><div class="panel-sub">% cùng kỳ năm trước · chỉ số giá cố định NSO · không dùng mức danh nghĩa để suy ra tăng trưởng thực</div></div><select id="activity-{key}-select" class="select" aria-label="Lọc hoạt động kinh tế"></select></div><div class="chart-wrap"><canvas id="activity-{key}-growth-chart" role="img" aria-label="Tăng trưởng GDP thực theo hoạt động kinh tế"></canvas></div><div class="footnote" id="activity-{key}-chart-note"></div></article>
          <article class="panel"><div class="panel-title">Cơ cấu danh nghĩa theo hoạt động · 2025</div><div class="panel-sub">Tỷ trọng trên GDP hiện hành; tổng khu vực này không bao gồm thuế sản phẩm ròng</div><div id="activity-{key}-composition" class="region-list"></div></article>
        </div>
        <div class="grid-equal" style="margin-top:14px">
          <article class="panel"><div class="panel-title">So sánh các hoạt động · năm gần nhất</div><div class="panel-sub">Mức GDP hiện hành, tỷ trọng GDP, tăng trưởng GDP thực và đóng góp vào tăng GDP</div><div id="activity-{key}-annual-table" class="table-wrap"></div></article>
          <article class="panel"><div class="section-head"><div><div class="panel-title">Cập nhật GDP mới nhất · quý III và 9 tháng 2026</div><div class="panel-sub">Chỉ tiêu GDP thực cùng kỳ; tỷ trọng đóng góp là phần trong mức tăng tổng giá trị tăng thêm</div></div><button id="download-activity-updates-{key}" class="select export-btn" type="button">Tải CSV 2026</button></div><div id="activity-{key}-update-table" class="table-wrap"></div><div class="footnote"><a href="https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/10/thong-cao-bao-chi-tinh-hinh-kinh-te-xa-hoi-quy-iii-va-9-thang-nam-2026/" target="_blank" rel="noopener">Mở thông cáo gốc của Cục Thống kê ↗</a></div></article>
        </div>
        <div class="footnote">{note}</div>
       </section>''' for key, title, subtitle, note in sector_page_specs)

html = r'''<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>V-MEST | Phân tích kinh tế Việt Nam</title>
<link rel="icon" type="image/png" href="assets/v-mest-logo.png">
<style>
:root{--bg:#f4f7fb;--surface:#fff;--text:#18324f;--muted:#6b7c91;--line:#e3eaf2;--blue:#3288e8;--green:#25b886;--orange:#f4a62a;--red:#e45a65;--purple:#7856d8;--shadow:0 5px 18px rgba(38,73,112,.07)}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 Inter,"Segoe UI",Arial,sans-serif}button,select{font:inherit;color:inherit}.app{display:grid;grid-template-columns:228px minmax(0,1fr);min-height:100vh}.sidebar{background:var(--surface);border-right:1px solid var(--line);padding:20px 14px;position:sticky;top:0;height:100vh}.brand{display:flex;align-items:center;gap:10px;padding:2px 10px 23px;font-size:19px;font-weight:800;letter-spacing:.2px}.brand-mark{width:30px;height:30px;border-radius:9px;background:linear-gradient(135deg,#3288e8,#67b4fb);display:grid;place-items:center;color:white;font-weight:900}.nav-label{font-size:10px;letter-spacing:1.1px;color:#9aa9ba;font-weight:700;padding:12px 11px 6px}.nav .nav-link{display:flex;align-items:center;gap:11px;width:100%;padding:10px 11px;margin:3px 0;border:0;border-radius:10px;background:transparent;text-align:left;color:#51647b;font-weight:600;cursor:pointer}.nav .nav-link:hover,.nav .nav-link.active{background:#eaf3fe;color:#1d66b3}.nav-icon{width:20px;text-align:center;font-size:16px}.side-bottom{position:absolute;bottom:18px;left:24px;color:#91a0b0;font-size:11px;line-height:1.7}.main{min-width:0}.topbar{height:68px;display:flex;align-items:center;justify-content:space-between;padding:0 28px;background:rgba(255,255,255,.88);border-bottom:1px solid var(--line);position:sticky;top:0;z-index:3;backdrop-filter:blur(12px)}.top-title{font-weight:700;font-size:15px}.top-sub{color:var(--muted);font-size:12px}.top-actions{display:flex;align-items:center;gap:10px}.pill{border:1px solid var(--line);background:#fff;border-radius:999px;padding:7px 11px;font-size:11px;color:#5c6e82}.theme-btn{border:1px solid var(--line);background:#fff;border-radius:10px;padding:7px 10px;cursor:pointer}.content{padding:25px 28px 50px;max-width:1600px;margin:auto}.welcome{display:flex;justify-content:space-between;align-items:end;gap:20px;margin-bottom:19px}.welcome h1{font-size:25px;letter-spacing:-.5px;margin:0 0 4px}.welcome p{margin:0;color:var(--muted)}.welcome-note{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:10px 14px;color:#52657b;font-size:12px;min-width:260px;box-shadow:var(--shadow)}.welcome-note b{color:var(--text)}.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:17px}.kpi{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px;box-shadow:var(--shadow);min-height:114px}.kpi-head{display:flex;align-items:center;justify-content:space-between;color:var(--muted);font-size:12px}.kpi-icon{width:34px;height:34px;border-radius:10px;display:grid;place-items:center;font-size:16px;color:var(--blue);background:#eaf3fe}.kpi:nth-child(2) .kpi-icon{color:var(--green);background:#e8f8f2}.kpi:nth-child(3) .kpi-icon{color:var(--purple);background:#f0ecfc}.kpi:nth-child(4) .kpi-icon{color:var(--orange);background:#fff5e2}.kpi-value{font-size:25px;font-weight:800;letter-spacing:-.5px;margin-top:5px}.kpi-foot{font-size:11px;color:var(--muted);margin-top:2px}.section{scroll-margin-top:84px;margin-top:17px}.page{display:none}.page.active{display:block}.page-footer{display:none}.page-footer.active{display:block}.section-head{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:0 2px 11px}.section-head h2{margin:0;font-size:16px}.section-head .sub{color:var(--muted);font-size:11px}.grid-main{display:grid;grid-template-columns:minmax(0,1.45fr) minmax(300px,.85fr);gap:14px}.grid-equal{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}.panel{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px 17px;box-shadow:var(--shadow);min-width:0}.panel-title{font-weight:700;font-size:13px;margin-bottom:3px}.panel-sub{font-size:11px;color:var(--muted);margin-bottom:12px}.chart-wrap{height:245px;position:relative}.chart-wrap.small{height:210px}.chart-wrap canvas{width:100%;height:100%;display:block}.controls{display:flex;gap:8px;align-items:center}.select{border:1px solid var(--line);background:var(--surface);border-radius:8px;padding:7px 9px;font-size:11px}.export-btn{cursor:pointer;color:#1d66b3;font-weight:650}.export-btn:hover{background:#eaf3fe}.interval-cell small{display:block;color:var(--muted);font-size:9px}.mini-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:10px}.mini{border-radius:9px;background:#f7f9fc;padding:9px}.mini span{display:block;color:var(--muted);font-size:10px}.mini b{font-size:14px}.legend{display:flex;gap:13px;flex-wrap:wrap;font-size:10px;color:var(--muted);margin:4px 0 0}.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}.region-list{display:grid;gap:10px}.region-row{display:grid;grid-template-columns:minmax(140px,1fr) 2fr 54px;gap:9px;align-items:center;font-size:11px}.region-name{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.track{height:8px;border-radius:99px;background:#edf1f6;overflow:hidden}.fill{height:100%;border-radius:99px;background:var(--blue)}.region-row:nth-child(2n) .fill{background:#53a0ef}.region-value{text-align:right;font-variant-numeric:tabular-nums;font-weight:700}.table-wrap{overflow:auto}.table{width:100%;border-collapse:collapse;font-size:11px}.table th,.table td{padding:9px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}.table th:first-child,.table td:first-child{text-align:left}.table th{color:var(--muted);font-weight:600}.table a{color:#1d66b3}.table tr[style*="background"]{color:var(--text)}#data-catalog .table td{min-width:130px;text-align:left;white-space:normal;vertical-align:top}#data-catalog .table td:nth-child(2){min-width:210px}#data-catalog .table td:nth-child(6){min-width:230px}#data-catalog .table td:nth-child(7){min-width:240px}.rank{display:inline-grid;place-items:center;width:22px;height:22px;background:#eaf3fe;color:#1d66b3;border-radius:7px;font-weight:700;margin-right:7px}.model-layout{display:grid;grid-template-columns:minmax(0,1.2fr) minmax(180px,.8fr);gap:12px;align-items:center}.model-callout{background:#eef8f3;border-radius:11px;padding:13px;color:#27674f;font-size:12px}.model-callout strong{display:block;font-size:14px;margin-bottom:4px}.status-row{display:grid;grid-template-columns:1fr auto auto;gap:10px;align-items:center;padding:9px 0;border-bottom:1px solid var(--line);font-size:11px}.status-tag{border-radius:999px;padding:4px 8px;font-size:10px;font-weight:700;background:#e8f8f2;color:#14865f}.status-tag.warn{background:#fff5e2;color:#a36b05}.footnote{margin-top:12px;color:var(--muted);font-size:10px;line-height:1.6}.data-footer{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.data-box{padding:12px 13px;background:var(--surface);border:1px solid var(--line);border-radius:11px}.data-box b{display:block;font-size:12px;margin-bottom:4px}.data-box span{font-size:11px;color:var(--muted)}.badge{display:inline-flex;align-items:center;background:#fff5e2;color:#946300;border-radius:999px;padding:4px 8px;font-size:10px;font-weight:700}.tooltip{position:fixed;pointer-events:none;opacity:0;background:#18324f;color:#fff;border-radius:7px;padding:6px 8px;font-size:11px;z-index:10;transform:translate(-50%,-120%);white-space:nowrap}.dark{--bg:#111b29;--surface:#1b2838;--text:#e5edf5;--muted:#9aabc0;--line:#2c3b4d;--shadow:0 5px 18px rgba(0,0,0,.14)}.dark .topbar{background:rgba(27,40,56,.9)}.dark .pill,.dark .theme-btn{background:var(--surface);color:var(--text)}.dark .welcome-note,.dark .select{background:var(--surface);color:var(--text)}.dark .export-btn{color:#8fc5ff}.dark .mini{background:#233449}.dark .track{background:#334257}.dark .badge{background:#423722;color:#ffd477}.dark .model-callout{background:#203d36;color:#a9e8ce}
.nav{max-height:calc(100vh - 150px);overflow:auto}
.section-head{flex-wrap:wrap;align-items:flex-start}.section-head>div:first-child{min-width:0;flex:1 1 250px}.section-head h2,.panel-title{word-break:normal;overflow-wrap:break-word;hyphens:none}.section-head .controls{flex-wrap:wrap;min-width:0;max-width:100%}.section-head>.select,.section-head>button{flex:0 1 auto;max-width:100%;white-space:normal}.panel-sub{max-width:100%;overflow-wrap:normal}.chart-wrap{min-width:0;overflow:hidden}.chart-empty{height:100%;display:grid;place-items:center;padding:16px;text-align:center;color:var(--muted);background:linear-gradient(180deg,rgba(244,247,251,.35),rgba(244,247,251,.8));border:1px dashed var(--line);border-radius:10px;font-size:12px}.chart-wrap canvas[hidden],.chart-empty[hidden]{display:none!important}.dark .chart-empty{background:linear-gradient(180deg,rgba(17,27,41,.15),rgba(17,27,41,.55))}
@media(max-width:1120px){.app{grid-template-columns:190px minmax(0,1fr)}.content{padding:20px}.kpis{grid-template-columns:repeat(2,minmax(0,1fr))}.grid-main{grid-template-columns:1fr}.welcome-note{min-width:210px}}
@media(max-width:900px){.grid-equal{grid-template-columns:1fr}}
@media(max-width:740px){.app{display:block}.sidebar{position:static;height:auto;padding:10px 14px;border-right:0;border-bottom:1px solid var(--line)}.brand{padding:2px 7px 9px}.nav-label,.side-bottom{display:none}.nav{display:flex;overflow:auto;gap:4px}.nav .nav-link{white-space:nowrap;width:auto;padding:8px}.topbar{height:58px;padding:0 15px}.top-actions .pill:first-child{display:none}.content{padding:17px 14px 35px}.welcome{align-items:start;flex-direction:column}.welcome-note{width:100%}.kpis{gap:9px}.kpi{padding:12px;min-height:105px}.kpi-value{font-size:21px}.grid-equal{grid-template-columns:1fr}.model-layout{grid-template-columns:1fr}.data-footer{grid-template-columns:1fr}.region-row{grid-template-columns:minmax(115px,1fr) 1.5fr 45px}}

/* Brand and sidebar refinement */
.app{grid-template-columns:248px minmax(0,1fr)}
.sidebar{display:flex;flex-direction:column;overflow:hidden;background:#f1f2f7;border-right:1px solid #e0e2eb;padding:22px 14px 18px}
.brand{display:flex;align-items:center;gap:11px;padding:2px 10px 14px;color:#273148;font-size:19px;font-weight:800;letter-spacing:.2px}
.brand-copy{display:flex;flex-direction:column;align-items:flex-start;gap:3px;min-width:0}
.brand-name{display:block;color:#263149;font-size:19px;line-height:1.1;font-weight:800;letter-spacing:.2px}
.brand-subtitle{display:block;max-width:170px;color:#687287;font-size:9.5px;line-height:1.4;font-weight:500;letter-spacing:.01em}
.nav-label{padding:13px 11px 9px;color:#82899b;font-size:9px;letter-spacing:1px;font-weight:700}
.nav{flex:1;min-height:0;max-height:calc(100vh - 190px);overflow:auto;padding:0 1px 8px;scrollbar-width:thin;scrollbar-color:#c7cad8 transparent}
.nav .nav-link{display:flex;align-items:center;gap:11px;width:100%;padding:11px 12px;margin:4px 0;border:0;border-radius:9px;background:transparent;text-align:left;color:#505b70;font-weight:550;line-height:1.4;cursor:pointer;transition:background .16s ease,color .16s ease}
.nav .nav-link:hover{background:rgba(106,99,173,.08);color:#30364d}
.nav .nav-link.active{background:rgba(106,99,173,.13);box-shadow:inset 3px 0 0 #756db5;color:#343653}
.nav-icon{width:20px;flex:0 0 20px;text-align:center;font-size:16px;color:#858da1}
.nav-link.active .nav-icon{color:#6f67ae}
.side-bottom{position:relative;left:auto;bottom:auto;margin:8px 2px 0;padding:10px 12px;border:1px solid #e0e2eb;border-radius:11px;background:rgba(255,255,255,.72);color:#4d586d;font-size:11px;line-height:1.65}
.dark .sidebar{background:#211f32;border-right-color:#3a374e}
.dark .brand,.dark .brand-name{color:#efedf9}
.dark .brand-subtitle{color:#b7b4cb}
.dark .nav-label{color:#aaa7bf}
.dark .nav .nav-link{color:#d0cede}
.dark .nav .nav-link:hover{background:rgba(172,163,235,.12);color:#f1efff}
.dark .nav .nav-link.active{background:rgba(172,163,235,.18);box-shadow:inset 3px 0 0 #b2a8f0;color:#f5f3ff}
.dark .nav-icon{color:#aaa7c1}
.dark .nav-link.active .nav-icon{color:#d0c9ff}
.dark .side-bottom{background:rgba(255,255,255,.04);border-color:#3a374e;color:#ddd9eb}
@media(max-width:1120px){.app{grid-template-columns:218px minmax(0,1fr)}}
@media(max-width:740px){.app{display:block}.sidebar{position:static;height:auto;min-height:0;overflow:visible;padding:10px 14px;border-right:0;border-bottom:1px solid #e0e2eb}.dark .sidebar{border-bottom-color:#3a374e}.brand{padding:2px 7px 10px}.nav-label{display:none}.nav{display:flex;flex:0 0 auto;max-height:none;overflow:auto;gap:5px;padding:0 0 5px}.nav .nav-link{white-space:nowrap;width:auto;flex:0 0 auto;padding:9px 10px;margin:0}.side-bottom{display:none}}
/* Typography hierarchy and chart emphasis */
body{color:#43516a}
.top-title,.welcome h1,.section-head h2,.panel-title{color:#243b5c}
.welcome p,.section-head .sub,.panel-sub,.kpi-head,.kpi-foot,.footnote,.table th{color:#788499}
.kpi-value{color:#1c4774}
.welcome-note{color:#67768d;border-color:#e2e7ef}
.welcome-note b{color:#243b5c}
.panel{border-color:#dce3ee;box-shadow:0 7px 20px rgba(38,57,85,.07),0 1px 3px rgba(38,57,85,.04);transition:border-color .18s ease,box-shadow .18s ease}
.panel:hover{border-color:#d3ddea;box-shadow:0 9px 24px rgba(38,57,85,.09),0 2px 5px rgba(38,57,85,.045)}
.chart-wrap{border:1px solid #e6eaf1;border-radius:10px;background:#fbfcfe;padding:5px 7px 4px}
.chart-empty{border-color:transparent;background:transparent}
.dark body{color:var(--text)}
.dark .top-title,.dark .welcome h1,.dark .section-head h2,.dark .panel-title,.dark .welcome-note b{color:var(--text)}
.dark .welcome p,.dark .section-head .sub,.dark .panel-sub,.dark .kpi-head,.dark .kpi-foot,.dark .footnote,.dark .table th{color:var(--muted)}
.dark .kpi-value{color:#c6ddfa}
.dark .welcome-note{color:var(--muted);border-color:var(--line)}
.dark .panel{border-color:#354357;box-shadow:0 7px 20px rgba(0,0,0,.18),0 1px 3px rgba(0,0,0,.12)}
.dark .panel:hover{border-color:#485a70}
.dark .chart-wrap{border-color:#344257;background:#1b2838}
/* Simplified header and student identification */
.topbar{height:62px}
.top-title{font-size:16px;line-height:1.3}
.top-sub,.top-actions .pill{display:none}
.top-actions{gap:0}
.side-bottom .student-name{display:block;color:inherit;font-size:12px;font-weight:700;line-height:1.4}
.side-bottom .student-id{display:block;margin-top:2px;color:#777f92;font-size:10px;line-height:1.4}
.dark .side-bottom .student-id{color:#b0adc4}
@media(max-width:740px){.topbar{height:58px}}
/* Highlight key numbers and bold content */
.brand-name{color:#b4232f}
.dark .brand-name{color:#ff7a84}
.top-title{color:#b4232f}
.welcome h1,.section-head h2,.panel-title{color:#202124}
.brand-highlight{color:#b4232f}
.kpi-value,.region-value,.rank,b,strong,.welcome-note b,.model-callout strong{color:#157347}
.kpi-value{font-weight:850}
.dark .top-title,.dark .brand-highlight{color:#ff7a84}
.dark .welcome h1,.dark .section-head h2,.dark .panel-title{color:#f3f4f6}
.dark .kpi-value,.dark .region-value,.dark .rank,.dark b,.dark strong,.dark .welcome-note b,.dark .model-callout strong{color:#75d69e}
</style>
<link rel="stylesheet" href="assets/backtest-arena.css">
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="brand"><img src="assets/v-mest-logo.png" alt="V-MEST" style="width:42px;height:42px;object-fit:contain;flex:0 0 auto"><div class="brand-copy"><span class="brand-name">V-MEST</span><span class="brand-subtitle">Hệ thống phân tích và dự báo GDP VN</span></div></div>
    <div class="nav-label">WORKSPACE</div>
    <nav class="nav" aria-label="Điều hướng chính">
      <button type="button" class="nav-link active" data-page="overview"><span class="nav-icon">⌂</span>Tổng quan</button>
      <button type="button" class="nav-link" data-page="macro"><span class="nav-icon">◷</span>EDA & Phân tích</button>
      <button type="button" class="nav-link" data-page="macro-compare"><span class="nav-icon">⌁</span>Vĩ mô & tương quan</button>
      <button type="button" class="nav-link" data-page="growth-drivers"><span class="nav-icon">↗</span>Động lực GDP</button>
      <button type="button" class="nav-link" data-page="sector-agriculture"><span class="nav-icon">♧</span>Nông, lâm, thủy sản</button>
      <button type="button" class="nav-link" data-page="sector-industry"><span class="nav-icon">▦</span>Công nghiệp, xây dựng</button>
      <button type="button" class="nav-link" data-page="sector-services"><span class="nav-icon">▤</span>Dịch vụ</button>
      <button type="button" class="nav-link" data-page="trade"><span class="nav-icon">⇄</span>Thương mại & IIP</button>
      <button type="button" class="nav-link" data-page="retail-fdi"><span class="nav-icon">▤</span>Bán lẻ & FDI</button>
      <button type="button" class="nav-link" data-page="regional"><span class="nav-icon">⌖</span>GRDP địa phương</button>
      <button type="button" class="nav-link" data-page="models"><span class="nav-icon">▥</span>Training Lab</button>
      <button type="button" class="nav-link" data-page="data-status"><span class="nav-icon">▤</span>Quản lý dữ liệu</button>
      <button type="button" class="nav-link" data-page="project-info"><span class="nav-icon">ⓘ</span>Thông tin đề tài</button>
    </nav>
     <div class="side-bottom"><span class="student-name">Bùi Nhĩ Ân</span><span class="student-id">MSSV 2311553345</span></div>
  </aside>
  <main class="main">
    <header class="topbar">
      <div><div><div id="top-title" class="top-title">Tổng quan GDP Việt Nam</div><div id="top-subtitle" class="top-sub">Vietnam · End-to-End Macro Analytics</div></div></div>
      <div class="top-actions"><span class="pill">Dataset: Việt Nam</span><span class="pill">GDP chi tiết · 25/10/2026</span><span id="version-pill" class="pill">Version —</span><button id="theme" class="theme-btn" aria-label="Đổi giao diện sáng tối">◐</button></div>
    </header>
    <div class="content">
      <section id="overview" class="section page active" style="margin-top:0">
        <div class="welcome"><div><h1>Chào mừng đến với <span class="brand-highlight">V-MEST</span></h1><p>Theo dõi tăng trưởng, biến động vĩ mô và dự báo trên dữ liệu có nguồn gốc.</p></div><div class="welcome-note">◷ &nbsp; <b>Mốc dữ liệu mới nhất</b><br>GDP năm 2025 · GDP quý III/2026 · CPI tháng 9/2026</div></div>
        <div class="kpis">
          <article class="kpi"><div class="kpi-head"><span>GDP danh nghĩa</span><span class="kpi-icon">▤</span></div><div class="kpi-value" id="nominal-kpi">—</div><div class="kpi-foot">USD hiện hành · 2025 · World Bank</div></article>
          <article class="kpi"><div class="kpi-head"><span>Tăng trưởng GDP thực</span><span class="kpi-icon">↗</span></div><div class="kpi-value" id="real-kpi">—</div><div class="kpi-foot">USD cố định 2015 · 2025</div></article>
          <article class="kpi"><div class="kpi-head"><span>GDP tăng trưởng quý III</span><span class="kpi-icon">▥</span></div><div class="kpi-value" id="q3-kpi">—</div><div class="kpi-foot">So với cùng kỳ · ước tính NSO</div></article>
          <article class="kpi"><div class="kpi-head"><span>CPI bình quân 9 tháng</span><span class="kpi-icon">◎</span></div><div class="kpi-value" id="cpi-kpi">—</div><div class="kpi-foot">So với cùng kỳ · 2026 · NSO</div></article>
        </div>
        <div class="grid-equal"><article class="panel"><div class="panel-title">Tăng trưởng GDP theo quý năm 2026</div><div class="panel-sub">% so với cùng kỳ · ước tính NSO · dữ liệu quý, không quy đổi thành mức GDP</div><div class="chart-wrap small"><canvas id="quarter-chart" role="img" aria-label="Tăng trưởng GDP theo quý năm 2026"></canvas></div></article><article class="panel"><div class="panel-title">Phạm vi dữ liệu và cách đọc dự báo</div><div class="data-footer"><div class="data-box"><b>41 năm</b><span>GDP thực quan sát<br>1985–2025</span></div><div class="data-box"><b>8 năm</b><span>GRDP địa phương<br>2018–2025</span></div><div class="data-box"><b>5 mô hình</b><span>Backtest 2005–25<br>dự báo đến 2030</span></div><div class="data-box"><b id="overview-fx">—</b><span>Tỷ giá VND/USD<br>kỳ quan sát gần nhất</span></div></div><div class="footnote">Backtest năm có 21 origin ở chân trời một năm; Drift đang có sai số thấp nhất trong mẫu lịch sử này. Dự báo 2026–2030 là kịch bản mô hình, không phải số liệu chính thức.</div></article></div>
      </section>

      <section id="macro" class="section page">
        <div class="section-head"><h2>EDA & Phân tích</h2><span class="sub">Mức GDP thực và cơ cấu GDP hiện hành được trình bày riêng</span></div>
        <div class="grid-main">
          <article class="panel"><div class="section-head"><div><div class="panel-title">GDP thực Việt Nam</div><div class="panel-sub" id="gdp-subtitle">USD cố định 2015 · tỷ USD · World Bank</div></div><div class="controls"><select id="gdp-metric" class="select" aria-label="Chọn chỉ tiêu GDP"><option value="realB">GDP thực (tỷ USD)</option><option value="growth">Tăng trưởng thực (%)</option></select><select id="start-year" class="select" aria-label="Lọc năm bắt đầu"><option value="1985">1985–2025</option><option value="2000">2000–2025</option><option value="2015">2015–2025</option></select><button id="download-gdp" class="select export-btn" type="button">Tải GDP CSV</button></div></div><div class="chart-wrap"><canvas id="gdp-chart" role="img" aria-label="Biểu đồ GDP thực theo năm"></canvas></div><div class="legend"><span><i class="dot" style="background:#3288e8"></i><span id="gdp-legend">GDP thực</span></span></div></article>
          <article class="panel"><div class="section-head"><div><div class="panel-title">Cơ cấu GDP theo ngành</div><div class="panel-sub">Giá hiện hành · tỷ trọng GDP · NSO</div></div><div class="controls"><select id="sector-year" class="select" aria-label="Chọn năm cơ cấu GDP"></select><button id="download-sectors" class="select export-btn" type="button">Tải cơ cấu</button></div></div><div id="sector-bars" class="region-list"></div><div class="footnote">Giá trị ngành là danh nghĩa; thuế sản phẩm ròng được tách riêng.</div></article>
        </div>
        <div class="grid-equal" style="margin-top:14px">
          <article class="panel"><div class="section-head"><div><div class="panel-title">Mức GDP thực quan sát theo quý</div><div class="panel-sub">2010-Q1–2025-Q4 · nghìn tỷ VND · giá so sánh 2010 · NSDP</div></div><button id="download-quarterly-gdp-2010" class="select export-btn" type="button">Tải CSV</button></div><div class="chart-wrap small"><canvas id="quarterly-gdp-2010-chart" role="img" aria-label="Mức GDP thực quý theo giá so sánh 2010"></canvas></div><div class="footnote">64 mức theo quý; tổng bốn quý được đối chiếu với GDP năm cùng workbook. Đây là quan sát quý, không phải chuỗi spline tháng.</div></article>
          <article class="panel"><div class="section-head"><div><div class="panel-title">GDP quý mới công bố · giá so sánh 2020</div><div class="panel-sub">2025-Q1–Q3 và 2026-Q1–Q3 · nghìn tỷ VND · NSDP</div></div><button id="download-quarterly-gdp-2020" class="select export-btn" type="button">Tải CSV</button></div><div class="chart-wrap small"><canvas id="quarterly-gdp-2020-chart" role="img" aria-label="Mức GDP thực quý theo giá so sánh 2020"></canvas></div><div class="footnote">Giữ riêng năm gốc 2020; không ghép trực tiếp với lịch sử giá 2010 vì hai mức giá khác hệ quy chiếu.</div></article>
        </div>
        <article class="panel" style="margin-top:14px"><div class="panel-title">Đối chiếu GDP năm với tổng bốn quý</div><div class="panel-sub">Cùng workbook NSDP · giá so sánh 2010</div><div id="quarterly-reconciliation-table" class="table-wrap"></div></article>
        <article class="panel" style="margin-top:14px"><div class="section-head"><div><div class="panel-title">Diễn biến tỷ trọng các cấu phần GDP</div><div class="panel-sub">Tỷ trọng danh nghĩa qua các năm · thuế sản phẩm trừ trợ cấp được giữ riêng</div></div></div><div class="chart-wrap small"><canvas id="sector-trend-chart" role="img" aria-label="Tỷ trọng các cấu phần GDP theo thời gian"></canvas></div><div class="panel-title" style="margin-top:10px">So sánh ngành 2024–2025</div><div id="sector-compare-table" class="table-wrap"></div></article>
      </section>

      <section id="macro-compare" class="section page">
        <div class="section-head"><h2>So sánh vĩ mô</h2><span class="sub">So sánh tỷ lệ và chỉ số hóa; không suy diễn quan hệ nhân quả</span></div>
        <article class="panel"><div class="panel-title">CPI và tỷ giá VND/USD</div><div class="panel-sub">Chỉ số tháng 1/2020 = 100 · trục chung để so diễn biến, không so trực tiếp mức giá với tỷ giá</div><div class="chart-wrap"><canvas id="macro-monthly-chart" role="img" aria-label="CPI và chỉ số tỷ giá đã quy về 100 từ tháng 1 năm 2020"></canvas></div><div class="legend"><span><i class="dot" style="background:#3288e8"></i>CPI</span><span><i class="dot" style="background:#25b886"></i>Tỷ giá VND/USD</span></div></article>
        <div class="grid-main" style="margin-top:14px"><article class="panel"><div class="section-head"><div><div class="panel-title">Scatter: tăng trưởng và chỉ báo vĩ mô</div><div class="panel-sub" id="scatter-summary">Tương quan mô tả · lọc đúng các năm có đủ dữ liệu</div></div><select id="scatter-select" class="select" aria-label="Chọn cặp biến so sánh"></select></div><div class="chart-wrap small"><canvas id="macro-scatter-chart" role="img" aria-label="Scatter so sánh các chỉ báo vĩ mô"></canvas></div></article><article class="panel"><div class="panel-title">Hệ số tương quan theo cặp biến</div><div class="panel-sub">Pearson và Spearman · số quan sát của từng phép so sánh</div><div id="correlation-table" class="table-wrap"></div><div class="footnote">Tương quan chỉ mô tả đồng biến/biến thiên trong mẫu, không chứng minh quan hệ dự báo hoặc nhân quả.</div></article></div>
        <article class="panel" style="margin-top:14px"><div class="section-head"><div><div class="panel-title">Chỉ báo vĩ mô theo năm</div><div class="panel-sub">Tỷ lệ/biến động được giữ đúng cách tính và tần suất trong nguồn</div></div><select id="macro-years" class="select" aria-label="Chọn số năm hiển thị"><option value="10">10 năm gần nhất</option><option value="20">20 năm gần nhất</option><option value="all">Toàn bộ</option></select></div><div id="macro-annual-table" class="table-wrap"></div></article>
      </section>

      <section id="growth-drivers" class="section page">
        <div class="section-head"><div><h2>Động lực GDP · dữ liệu mở rộng</h2><span class="sub">Chi tiêu, sản xuất, lao động, đầu tư, tài khóa, tín dụng, đối ngoại và giá hàng hóa</span></div><div class="controls"><button id="download-driver-panel" class="select export-btn" type="button">Tải bảng so sánh</button><button id="download-driver-data" class="select export-btn" type="button">Tải bộ chỉ báo</button></div></div>
        <div class="grid-equal">
          <article class="panel"><div class="section-head"><div><div class="panel-title">Đóng góp vào tăng GDP theo chi tiêu</div><div class="panel-sub" id="contribution-sub">Điểm phần trăm · giá cố định 2010 · thành phần không cộng trùng</div></div><select id="driver-year" class="select" aria-label="Chọn năm phân rã GDP"></select></div><div class="chart-wrap small"><canvas id="driver-contribution-chart" role="img" aria-label="Đóng góp của tiêu dùng, đầu tư, tồn kho, thương mại và sai số thống kê vào tăng trưởng GDP"></canvas></div><div id="contribution-table" class="table-wrap"></div><div class="footnote">Đóng góp = thay đổi thành phần chia GDP năm trước. Năm 2010 không phân rã vì chuỗi đổi năm gốc; cán cân thương mại có thể đóng góp âm.</div></article>
          <article class="panel"><div class="panel-title">Tăng trưởng GDP thực theo khu vực sản xuất</div><div class="panel-sub">% so với năm trước · GDP giá cố định 2010 · NSO</div><div class="chart-wrap small"><canvas id="sector-real-growth-chart" role="img" aria-label="Tăng trưởng GDP thực nông nghiệp, công nghiệp xây dựng và dịch vụ"></canvas></div><div class="legend"><span><i class="dot" style="background:#25b886"></i>Nông, lâm, thủy sản</span><span><i class="dot" style="background:#3288e8"></i>Công nghiệp và xây dựng</span><span><i class="dot" style="background:#7856d8"></i>Dịch vụ</span></div></article>
        </div>
        <div class="grid-equal" style="margin-top:14px">
          <article class="panel"><div class="panel-title">Cơ cấu lao động theo khu vực</div><div class="panel-sub">Tỷ trọng việc làm · nhóm ngành đã gộp để so sánh</div><div class="chart-wrap small"><canvas id="employment-share-chart" role="img" aria-label="Cơ cấu lao động theo ba khu vực kinh tế"></canvas></div><div class="footnote">Năm 2006 không có trong bảng NSO; 2025 sơ bộ.</div></article>
          <article class="panel"><div class="panel-title">Năng suất lao động thực: proxy theo khu vực</div><div class="panel-sub">Triệu VND giá 2010/người · GDP thực ngành chia số lao động</div><div class="chart-wrap small"><canvas id="productivity-proxy-chart" role="img" aria-label="Proxy năng suất lao động thực theo ba khu vực"></canvas></div><div class="footnote">Proxy gộp ngành; khác phạm vi và cách tính với chỉ tiêu năng suất lao động danh nghĩa chính thức của NSO.</div></article>
        </div>
        <div class="grid-equal" style="margin-top:14px">
          <article class="panel"><div class="panel-title">Đầu tư thực hiện theo khu vực sở hữu</div><div class="panel-sub">Nghìn tỷ VND giá cố định 2010 · so sánh Nhà nước, ngoài nhà nước và FDI</div><div class="chart-wrap small"><canvas id="investment-ownership-chart" role="img" aria-label="Vốn đầu tư thực theo khu vực sở hữu"></canvas></div><div id="investment-share-table" class="table-wrap"></div></article>
          <article class="panel"><div class="panel-title">Chi đầu tư phát triển ngân sách</div><div class="panel-sub">Tỷ lệ trên GDP danh nghĩa và tỷ lệ trong tổng chi ngân sách</div><div class="chart-wrap small"><canvas id="fiscal-investment-chart" role="img" aria-label="Chi đầu tư phát triển ngân sách so với GDP và tổng chi"></canvas></div><div class="footnote">So tỷ lệ trên GDP cùng giá hiện hành; đây không phải chi đầu tư công thực đã giảm phát.</div></article>
        </div>
        <div class="grid-equal" style="margin-top:14px">
          <article class="panel"><div class="panel-title">Tín dụng và cán cân vãng lai</div><div class="panel-sub">Tỷ lệ trên GDP danh nghĩa · %</div><div class="chart-wrap small"><canvas id="credit-current-chart" role="img" aria-label="Tín dụng và cán cân vãng lai so với GDP"></canvas></div><div class="footnote">Dư nợ tín dụng là giá trị danh nghĩa cuối năm; cán cân vãng lai lấy từ cán cân thanh toán NSO, không phải cán cân hàng hóa hải quan.</div></article>
          <article class="panel"><div class="panel-title">Đóng góp năng suất nhân tố tổng hợp (TFP)</div><div class="panel-sub">Tỷ trọng đóng góp tăng trưởng theo các kỳ 5 năm do NSO công bố</div><div class="chart-wrap small"><canvas id="tfp-chart" role="img" aria-label="Đóng góp TFP, vốn và lao động trong ba kỳ năm năm"></canvas></div><div id="tfp-table" class="table-wrap"></div></article>
        </div>
        <div class="grid-equal" style="margin-top:14px">
          <article class="panel"><div class="panel-title">Lãi suất tiền gửi và cho vay VND</div><div class="panel-sub">Lãi suất bình quân năm theo nhóm kỳ hạn · %/năm</div><div class="chart-wrap small"><canvas id="interest-rates-chart" role="img" aria-label="Lãi suất tiền gửi và cho vay bằng VND"></canvas></div></article>
          <article class="panel"><div class="panel-title">Thất nghiệp theo vùng</div><div class="panel-sub">Lực lượng lao động trong độ tuổi · toàn quốc · %</div><div class="chart-wrap small"><canvas id="unemployment-region-chart" role="img" aria-label="Tỷ lệ thất nghiệp theo sáu vùng kinh tế"></canvas></div><div class="footnote">Tỷ lệ thất nghiệp không bao quát đầy đủ thiếu việc làm và chất lượng việc làm.</div></article>
        </div>
        <article class="panel" style="margin-top:14px"><div class="panel-title">Chỉ số giá hàng hóa quốc tế</div><div class="panel-sub">Chỉ số giá tháng, 2015 bình quân năm = 100 · giá USD danh nghĩa · World Bank Pink Sheet</div><div class="chart-wrap"><canvas id="commodity-index-chart" role="img" aria-label="Chỉ số giá dầu, than, khí, gạo, urê, quặng sắt và đồng"></canvas></div><div class="footnote">Chỉ số hóa để so biến động tương đối giữa các chuỗi có đơn vị khác nhau. Đây là giá hàng hóa quốc tế, không đại diện trực tiếp cho giá đầu vào doanh nghiệp Việt Nam.</div></article>
        <div class="grid-equal" style="margin-top:14px">
          <article class="panel"><div class="panel-title">Tương quan mô tả với tăng trưởng GDP thực</div><div class="panel-sub">So sánh trên năm có đủ cặp dữ liệu · không suy luận nhân quả</div><div id="driver-correlation-table" class="table-wrap"></div></article>
          <article class="panel"><div class="panel-title">Bảng động lực GDP theo năm</div><div class="panel-sub">Biến thực, danh nghĩa, tỷ lệ và trạng thái nguồn giữ riêng</div><div class="controls" style="margin-bottom:8px"><select id="driver-table-years" class="select" aria-label="Chọn độ dài bảng động lực"><option value="10">10 năm gần nhất</option><option value="20">20 năm gần nhất</option><option value="all">Toàn bộ</option></select></div><div id="driver-annual-table" class="table-wrap"></div></article>
        </div>
      </section>

      __SECTOR_PAGES__

      <section id="trade" class="section page">
        <div class="section-head"><h2>Thương mại & sản xuất</h2><div class="controls"><span class="badge">Số liệu tháng 2026: sơ bộ</span><button id="download-trade" class="select export-btn" type="button">Tải ngoại thương</button><button id="download-iip" class="select export-btn" type="button">Tải IIP</button></div></div>
        <div class="grid-equal">
          <article class="panel"><div class="panel-title">Xuất khẩu và nhập khẩu hàng hóa</div><div class="panel-sub">Tỷ USD · từng tháng · dữ liệu sơ bộ NSO</div><div class="chart-wrap small"><canvas id="trade-flow-chart" role="img" aria-label="Kim ngạch xuất khẩu và nhập khẩu theo tháng năm 2026"></canvas></div><div class="panel-title" style="margin-top:8px">Cán cân thương mại (xuất khẩu trừ nhập khẩu)</div><div class="chart-wrap small"><canvas id="trade-chart" role="img" aria-label="Cán cân thương mại tháng một đến tháng chín năm 2026"></canvas></div><div class="mini-grid"><div class="mini"><span>Xuất khẩu 9 tháng</span><b id="export-total">—</b></div><div class="mini"><span>Nhập khẩu 9 tháng</span><b id="import-total">—</b></div><div class="mini"><span>Cán cân theo workbook</span><b id="trade-total">—</b></div></div><div class="footnote">Tổng từ bảng workbook tháng; có thể khác nhẹ bản tin tổng hợp do phiên bản sơ bộ.</div></article>
          <article class="panel"><div class="panel-title">IIP toàn ngành</div><div class="panel-sub">Chỉ số bình quân tháng năm 2015 = 100 · 2026</div><div class="chart-wrap small"><canvas id="iip-chart" role="img" aria-label="Chỉ số sản xuất công nghiệp từ tháng một đến tháng chín năm 2026"></canvas></div><div class="mini-grid"><div class="mini"><span>Tháng 9 vs tháng 8</span><b>+3,26%</b></div><div class="mini"><span>Tháng 9 cùng kỳ</span><b>+16,65%</b></div><div class="mini"><span>9 tháng cùng kỳ</span><b>+12,33%</b></div></div><div class="footnote">So sánh lũy kế 9 tháng là mức tăng của giai đoạn, không phải tốc độ riêng tháng 9.</div></article>
        </div>
      </section>

      <section id="retail-fdi" class="section page">
        <div class="section-head"><h2>Bán lẻ & đầu tư trực tiếp nước ngoài</h2><div class="controls"><span class="badge">Tách số năm và lũy kế 9 tháng 2026</span><button id="download-retail" class="select export-btn" type="button">Tải bán lẻ</button><button id="download-fdi" class="select export-btn" type="button">Tải FDI</button></div></div>
        <div class="grid-equal"><article class="panel"><div class="panel-title">Tổng mức bán lẻ theo năm</div><div class="panel-sub">Nghìn tỷ VND hiện hành · 1990–2025</div><div class="chart-wrap"><canvas id="retail-annual-chart" role="img" aria-label="Tổng mức bán lẻ tiêu dùng theo năm"></canvas></div></article><article class="panel"><div class="panel-title">FDI đăng ký và thực hiện theo năm</div><div class="panel-sub">Tỷ USD · định nghĩa vốn đăng ký cấp phép theo chuỗi năm</div><div class="chart-wrap"><canvas id="fdi-annual-chart" role="img" aria-label="FDI đăng ký và thực hiện theo năm"></canvas></div></article></div>
        <div class="grid-equal" style="margin-top:14px"><article class="panel"><div class="panel-title">Bán lẻ tháng năm 2026</div><div class="panel-sub">Tỷ VND hiện hành · tăng trưởng thực là lũy kế đến kỳ báo cáo, không phải tốc độ riêng từng tháng</div><div class="chart-wrap small"><canvas id="retail-month-chart" role="img" aria-label="Tổng mức bán lẻ hàng tháng năm 2026"></canvas></div><div id="retail-month-table" class="table-wrap"></div></article><article class="panel"><div class="panel-title">FDI lũy kế 9 tháng 2026</div><div class="panel-sub">Định nghĩa nguồn NSO · tách riêng khỏi chuỗi vốn đăng ký dự án cấp phép năm</div><div class="data-footer"><div class="data-box"><b id="fdi-registered">—</b><span>Vốn đăng ký tổng hợp</span></div><div class="data-box"><b id="fdi-implemented">—</b><span>Vốn thực hiện lũy kế</span></div><div class="data-box"><b id="fdi-growth">—</b><span>Tăng so cùng kỳ</span></div></div><div class="footnote" id="fdi-note">—</div></article></div>
      </section>

      <section id="regional" class="section page">
        <div class="section-head"><h2>So sánh GRDP địa phương</h2><div class="controls"><span class="sub">63 tỉnh truyền thống · 6 vùng thống kê</span><div class="controls"><select id="grdp-year" class="select" aria-label="Chọn năm GRDP"></select><button id="download-grdp" class="select export-btn" type="button">Tải GRDP</button></div></div></div>
        <div class="grid-main">
          <article class="panel"><div class="panel-title">Tỷ trọng GRDP theo 6 vùng thống kê</div><div class="panel-sub" id="region-sub">% tổng GRDP sáu vùng · không cộng cùng tỉnh thành phần</div><div id="region-bars" class="region-list"></div></article>
          <article class="panel"><div class="section-head"><div><div class="panel-title">Xếp hạng tỉnh/thành</div><div class="panel-sub" id="province-sub">Chọn thước đo để so sánh</div></div><div class="controls"><select id="province-metric" class="select" aria-label="Chọn chỉ tiêu xếp hạng"><option value="grdp">Quy mô GRDP</option><option value="perCapita">GRDP/người</option><option value="growth">Tăng trưởng GRDP nguồn</option></select><select id="province-direction" class="select" aria-label="Chọn nhóm xếp hạng"><option value="top">Top 10</option><option value="bottom">Bottom 10</option></select></div></div><div id="province-table" class="table-wrap"></div><div class="footnote">GRDP ước tính từ GRDP/người × dân số bình quân. Tăng trưởng nguồn là chỉ số giá so sánh, khác tăng trưởng danh nghĩa. Phạm vi là 63 tỉnh/thành truyền thống, không chuẩn hóa sang địa giới mới.</div></article>
        </div>
      </section>

      <section id="models" class="section page">
        <div class="section-head"><h2>Training Lab · So sánh mô hình</h2><div class="controls"><span class="sub">Rolling origin · expanding window</span><select id="backtest-horizon" class="select" aria-label="Chọn chân trời backtest"><option value="1">1 năm</option><option value="2">2 năm</option><option value="3">3 năm</option><option value="4">4 năm</option><option value="5">5 năm</option></select><button id="download-backtest" class="select export-btn" type="button">Tải backtest</button></div></div>
        <article class="panel"><div class="model-layout"><div><div class="section-head"><div><div id="metric-title" class="panel-title">Sai số MAPE theo mô hình</div><div id="backtest-sub" class="panel-sub">Dữ liệu GDP thực quan sát</div></div><div class="controls"><select id="model-metric" class="select" aria-label="Chọn chỉ số so sánh"><option value="mape">MAPE (%)</option><option value="smape">sMAPE (%)</option><option value="mae">MAE (tỷ USD 2015)</option><option value="rmse">RMSE (tỷ USD 2015)</option><option value="mase">MASE</option></select></div></div><div class="chart-wrap small"><canvas id="model-chart" role="img" aria-label="So sánh sai số dự báo của các mô hình"></canvas></div></div><div class="model-callout"><strong>Mô hình tốt nhất theo backtest</strong><span id="model-summary">—</span><br><br>GRU/LSTM hiện kém hơn baseline trên mẫu này. Chỉ 41 quan sát GDP năm; kết quả neural chỉ nên xem là thăm dò.</div></div><div class="footnote">Chuẩn hóa chỉ fit trên tập huấn luyện từng fold; không xáo trộn thời gian và không dùng chuỗi spline tháng làm dữ liệu thực.</div><div class="panel-title" style="margin-top:13px">Leaderboard đầy đủ</div><div id="model-leaderboard" class="table-wrap"></div></article>
        <article class="panel" style="margin-top:14px"><div class="section-head"><div><div class="panel-title">Backtest GDP thực theo quý · giá 2010</div><div class="panel-sub" id="quarterly-backtest-sub">Rolling-origin · 32 quý đầu để huấn luyện · kết quả theo chân trời</div></div><div class="controls"><select id="quarterly-backtest-horizon" class="select" aria-label="Chọn chân trời backtest GDP quý"><option value="1">1 quý</option><option value="4">4 quý</option><option value="8">8 quý</option><option value="12">12 quý</option><option value="20">20 quý</option></select><select id="quarterly-model-metric" class="select" aria-label="Chọn chỉ số backtest GDP quý"><option value="mape">MAPE (%)</option><option value="rmse">RMSE (nghìn tỷ VND)</option><option value="mase">MASE mùa vụ</option></select><button id="download-quarterly-backtest" class="select export-btn" type="button">Tải backtest quý</button></div></div><div class="chart-wrap small"><canvas id="quarterly-model-chart" role="img" aria-label="So sánh mô hình backtest GDP thực theo quý"></canvas></div><div id="quarterly-model-leaderboard" class="table-wrap"></div><div class="footnote">So sánh Seasonal Naive, Seasonal Drift, xu hướng log với biến giả quý và ETS. Các cửa sổ kiểm thử chồng lấp nên sai số phụ thuộc nhau; kết quả không thay thế dự báo GDP năm đến 2030.</div></article>
        <article class="panel" style="margin-top:14px"><div class="section-head"><div><div class="panel-title">GDP thực: dự báo ngoài mẫu đến 2030</div><div class="panel-sub">Số liệu quan sát đến 2025 · tỷ USD cố định 2015 · dải P80 kinh nghiệm từ backtest</div></div><div class="controls"><select id="forecast-model" class="select" aria-label="Chọn mô hình dự báo GDP"></select><button id="download-projection" class="select export-btn" type="button">Tải dự báo</button></div></div><div class="chart-wrap"><canvas id="forecast-chart" role="img" aria-label="GDP thực quan sát, dự báo kiểm thử và dự báo đến năm 2030"></canvas></div><div class="legend"><span><i class="dot" style="background:#3288e8"></i>GDP quan sát</span><span><i class="dot" style="background:#f4a62a"></i><span id="backtest-legend">Backtest rolling-origin</span></span><span><i class="dot" style="background:#7856d8"></i>Dự báo 2026–2030</span><span><i class="dot" style="background:#b7aaf0"></i>Dải sai số P80 kinh nghiệm</span></div><div id="forecast-table" class="table-wrap"></div><div class="footnote">Dải P80 được hiệu chuẩn từ sai số log tuyệt đối backtest cùng chân trời; do sai số chuỗi thời gian có phụ thuộc và mẫu nhỏ, dải này không bảo đảm coverage 80%. Dự báo là kịch bản, không phải số liệu chính thức. GRU/LSTM còn mang tính thăm dò.</div></article>
        __ARENA_SECTION__
      </section>

      <section id="data-status" class="section page">
        <div class="section-head"><h2>Quản lý dữ liệu</h2><div class="controls"><span class="sub">Nguồn, phiên bản và chất lượng dữ liệu</span><button id="download-catalog" class="select export-btn" type="button">Tải danh mục</button><button id="download-version" class="select export-btn" type="button">Tải manifest</button></div></div>
        <div class="grid-equal">
          <article class="panel"><div class="status-row"><span>GDP quốc gia</span><span>World Bank · năm 2025</span><span class="status-tag">Cập nhật</span></div><div class="status-row"><span>GDP thực quý</span><span>NSDP · 2010-Q1–2025-Q4 · giá 2010</span><span class="status-tag">64 quan sát</span></div><div class="status-row"><span>GDP thực quý mới</span><span>NSDP · 2026-Q1–Q3 · giá 2020</span><span class="status-tag warn">Chuỗi riêng</span></div><div class="status-row"><span>CPI tháng</span><span>NSO · 2026-09</span><span class="status-tag warn">Tái tạo mức</span></div><div class="status-row"><span>Tỷ giá VND/USD</span><span>IMF · 2026-07</span><span class="status-tag">Quan sát</span></div><div class="status-row"><span>Xuất nhập khẩu</span><span>NSO · 2026-09</span><span class="status-tag warn">Sơ bộ</span></div><div class="status-row"><span>IIP tháng</span><span>NSO · 2026-09</span><span class="status-tag warn">Ước tính</span></div><div class="status-row"><span>GRDP địa phương</span><span>NSO · 2018–2025</span><span class="status-tag warn">2025 ước tính</span></div><div class="status-row"><span>Phiên bản dữ liệu</span><span id="data-version-id">—</span><button id="version-download-inline" class="select export-btn" type="button">Manifest</button><a id="version-archive-link" class="select export-btn" href="#" download>Snapshot ZIP</a></div></article>
          <article class="panel"><div class="panel-title">Tỷ giá và lạm phát mới nhất</div><div class="panel-sub">Hai trục phân tích độc lập; không diễn giải nhân quả</div><div class="data-footer"><div class="data-box"><b id="fx-value">—</b><span>VND/USD bình quân tháng<br>kỳ gần nhất</span></div><div class="data-box"><b id="cpi-period">—</b><span>Tháng CPI có dữ liệu<br>trong bộ cập nhật</span></div><div class="data-box"><b>41 năm</b><span>Chuỗi GDP thực<br>1985–2025</span></div></div><div class="footnote">Chỉ số CPI 2026 được tái tạo từ tỷ lệ lũy kế chính thức làm tròn. GDP tháng spline chỉ để minh họa/giữ tương thích, không dùng huấn luyện hay backtest.</div></article>
        </div>
        <article class="panel" style="margin-top:14px"><div class="section-head"><div><div class="panel-title">Danh mục cấu trúc và nguồn dữ liệu</div><div class="panel-sub">Tệp đang cấp dữ liệu cho dashboard, tần suất, kỳ bao phủ, trường chính và lưu ý khi phân tích</div></div><button id="download-quality" class="select export-btn" type="button">Tải kiểm tra</button></div><div id="data-quality-summary" class="footnote">—</div><div id="data-catalog" class="table-wrap"></div><div class="footnote">Nhấn tên nguồn để mở trang dữ liệu gốc. Các giá trị được gắn chú thích sơ bộ/tái tạo được giữ đúng trạng thái; không xem tần suất nội suy là quan sát thực.</div><div id="data-quality" class="table-wrap" style="margin-top:14px"></div></article>
      </section>
      <section id="project-info" class="section page">
        <div class="section-head"><div><h2>Thông tin đề tài</h2><span class="sub">Thông tin sinh viên, hướng dẫn, dữ liệu và phương pháp nghiên cứu</span></div></div>
        <div class="grid-equal">
          <article class="panel"><div class="panel-title">Thông tin sinh viên và đề tài</div>
            <div class="status-row"><span>Họ tên</span><strong>Bùi Nhĩ Ân</strong></div>
            <div class="status-row"><span>MSSV</span><strong>2311553345</strong></div>
            <div class="status-row"><span>Giảng viên hướng dẫn</span><strong>ThS. Vương Xuân Chí</strong></div>
            <div class="panel-title" style="margin-top:14px">Tên đề tài</div>
            <p>Xây dựng hệ thống xử lý và phân tích dự báo GDP toàn diện (End-to-End) tại Việt Nam</p>
          </article>
          <article class="panel"><div class="panel-title">Quy mô dữ liệu</div>
            <div class="data-footer">
              <div class="data-box"><b id="project-file-count">—</b><span>Tệp dữ liệu<br>trong catalog</span></div>
              <div class="data-box"><b id="project-url-count">—</b><span>Địa chỉ nguồn<br>được ghi trong manifest</span></div>
              <div class="data-box"><b id="project-source-count">—</b><span>Nhóm nguồn<br>bên ngoài</span></div>
            </div>
            <div id="project-source-groups" class="footnote" style="margin-top:12px"></div>
          </article>
        </div>
        <article class="panel" style="margin-top:14px"><div class="panel-title">Thuật toán và mô hình dự báo</div>
          <div class="panel-sub">5 mô hình GDP thực năm (USD cố định 2015), dự báo đến 2030</div>
          <ol id="project-models" class="table" style="padding-left:24px"></ol>
          <div class="panel-sub">4 mô hình backtest GDP quý (mức giá 2010), là nhánh đánh giá riêng</div><ol id="project-quarterly-models" class="table" style="padding-left:24px"></ol>
          <div class="footnote">Kỹ thuật phân tích bổ sung: Cubic Spline chỉ để tương thích/hiển thị; kiểm định ADF; bộ lọc HP; tương quan Pearson và Spearman; backtest expanding-window rolling-origin. MAPE, sMAPE, MAE, RMSE và MASE là chỉ số đánh giá, không phải thuật toán.</div>
        </article>
        <details class="panel" style="margin-top:14px"><summary class="panel-title" style="cursor:pointer">Danh sách địa chỉ nguồn dữ liệu</summary>
          <div class="panel-sub" style="margin:6px 0 10px">Các URL được ghi trong refresh manifest. Chọn một địa chỉ để mở nguồn gốc.</div>
          <ol id="project-source-links" style="padding-left:24px;overflow-wrap:anywhere"></ol>
        </details>
      </section>
      <footer id="page-footer" class="footnote page-footer" style="display:none"></footer>
    </div>
  </main>
</div>
<div id="tooltip" class="tooltip"></div>
<script>
const D=__DATA__;
const $=id=>document.getElementById(id);
const fmt=(v,d=1)=>Number(v).toLocaleString('vi-VN',{minimumFractionDigits:d,maximumFractionDigits:d});
const css=(name)=>getComputedStyle(document.body).getPropertyValue(name).trim();
const colors={blue:'#3288e8',green:'#25b886',orange:'#f4a62a',red:'#e45a65',purple:'#7856d8',muted:'#6b7c91',grid:'#e6edf4',text:'#18324f'};
function setupCanvas(canvas){const r=canvas.getBoundingClientRect(),dpr=window.devicePixelRatio||1;canvas.width=Math.max(1,Math.round(r.width*dpr));canvas.height=Math.max(1,Math.round(r.height*dpr));const c=canvas.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);return {c,w:r.width,h:r.height}}
function lineChart(id,labels,series,opts={}){const {c,w,h}=setupCanvas($(id)),p={l:48,r:12,t:12,b:30};let vals=series.flatMap(s=>s.values.filter(v=>v!==null&&Number.isFinite(v)));if(!vals.length)return;let min=opts.min!==undefined?opts.min:Math.min(...vals),max=opts.max!==undefined?opts.max:Math.max(...vals);if(max===min)max=min+1;let span=max-min;if(opts.zero){min=Math.min(0,min);max=Math.max(0,max);span=max-min}const x=i=>p.l+(w-p.l-p.r)*(labels.length===1?.5:i/(labels.length-1)),y=v=>p.t+(h-p.t-p.b)*(1-(v-min)/span);c.font='10px Segoe UI,Arial';c.fillStyle=css('--muted');c.strokeStyle=css('--line');c.lineWidth=1;for(let k=0;k<4;k++){let v=min+(max-min)*k/3,yy=y(v);c.beginPath();c.moveTo(p.l,yy);c.lineTo(w-p.r,yy);c.stroke();c.fillText(opts.tick?opts.tick(v):fmt(v,0),3,yy+3)}let step=Math.max(1,Math.ceil(labels.length/6));labels.forEach((l,i)=>{if(i%step===0||i===labels.length-1){c.fillStyle=css('--muted');c.fillText(l,p.l+(w-p.l-p.r)*i/Math.max(1,labels.length-1)-13,h-8)}});if(opts.band){const valid=labels.map((_,i)=>i).filter(i=>Number.isFinite(opts.band.lower[i])&&Number.isFinite(opts.band.upper[i]));if(valid.length){c.beginPath();valid.forEach((i,j)=>j?c.lineTo(x(i),y(opts.band.lower[i])):c.moveTo(x(i),y(opts.band.lower[i])));valid.slice().reverse().forEach(i=>c.lineTo(x(i),y(opts.band.upper[i])));c.closePath();c.globalAlpha=.15;c.fillStyle=opts.band.color||colors.purple;c.fill();c.globalAlpha=1}}series.forEach(s=>{c.beginPath();let active=false;s.values.forEach((v,i)=>{if(v===null||!Number.isFinite(v)){active=false;return}if(!active){c.moveTo(x(i),y(v));active=true}else c.lineTo(x(i),y(v))});c.strokeStyle=s.color;c.lineWidth=s.lineWidth||2.4;c.setLineDash(s.dash||[]);c.stroke();c.setLineDash([]);if(!s.noPoints)s.values.forEach((v,i)=>{if(v===null||!Number.isFinite(v))return;c.beginPath();c.arc(x(i),y(v),2.5,0,Math.PI*2);c.fillStyle=s.color;c.fill()})});canvasHover($(id),labels,series,x,y)}
function barChart(id,labels,values,opts={}){const {c,w,h}=setupCanvas($(id)),p={l:48,r:12,t:12,b:34};let min=opts.min!==undefined?opts.min:Math.min(0,...values),max=opts.max!==undefined?opts.max:Math.max(...values);if(max===min)max=min+1;let span=max-min;const y=v=>p.t+(h-p.t-p.b)*(1-(v-min)/span),step=(w-p.l-p.r)/values.length,bw=Math.max(8,step*.48);c.font='10px Segoe UI,Arial';c.fillStyle=css('--muted');c.strokeStyle=css('--line');for(let k=0;k<4;k++){let v=min+(max-min)*k/3,yy=y(v);c.beginPath();c.moveTo(p.l,yy);c.lineTo(w-p.r,yy);c.stroke();c.fillText(opts.tick?opts.tick(v):fmt(v,0),3,yy+3)}values.forEach((v,i)=>{let xx=p.l+step*i+(step-bw)/2,yy=y(Math.max(v,0)),base=y(Math.min(v,0));c.fillStyle=opts.colors?opts.colors[i]:v<0?colors.red:colors.blue;c.fillRect(xx,yy,bw,Math.max(1,base-yy));c.fillStyle=css('--muted');let lab=labels[i];c.fillText(lab,xx+bw/2-c.measureText(lab).width/2,h-9);if(opts.labels){c.fillStyle=css('--text');let val=opts.labels[i];c.fillText(val,xx+bw/2-c.measureText(val).width/2, v<0?base+12:yy-5)}});canvasHover($(id),labels,[{name:opts.series||'Giá trị',values,color:colors.blue}],i=>p.l+step*i+step/2,y)}
function showChartEmpty(id,message='Không có dữ liệu phù hợp với lựa chọn này.'){const canvas=$(id),wrap=canvas?.closest('.chart-wrap');if(!wrap)return;canvas.hidden=true;let empty=wrap.querySelector('.chart-empty');if(!empty){empty=document.createElement('div');empty.className='chart-empty';empty.setAttribute('role','status');empty.setAttribute('aria-live','polite');wrap.appendChild(empty)}empty.textContent=message;empty.hidden=false}
function clearChartEmpty(id){const canvas=$(id),wrap=canvas?.closest('.chart-wrap');if(!canvas||!wrap)return;canvas.hidden=false;const empty=wrap.querySelector('.chart-empty');if(empty)empty.hidden=true}
const drawLineChart=lineChart,drawBarChart=barChart;
lineChart=function(id,labels,series,opts={}){const valid=(labels||[]).length>0&&(series||[]).some(s=>(s.values||[]).some(v=>v!==null&&v!==undefined&&Number.isFinite(v)));if(!valid){showChartEmpty(id);return}clearChartEmpty(id);return drawLineChart(id,labels,series,opts)};
barChart=function(id,labels,values,opts={}){const valid=(labels||[]).length>0&&(values||[]).some(v=>v!==null&&v!==undefined&&Number.isFinite(v));if(!valid){showChartEmpty(id);return}clearChartEmpty(id);return drawBarChart(id,labels,values,opts)};
function canvasHover(canvas,labels,series,x,y){canvas.onmousemove=e=>{const r=canvas.getBoundingClientRect(),px=e.clientX-r.left;let best=0,dist=1e9;labels.forEach((_,i)=>{const xx=x(i),d=Math.abs(px-xx);if(d<dist){dist=d;best=i}});if(dist>45){$('tooltip').style.opacity=0;return}let items=series.map(s=>s.values[best]===null?'':`${s.name||''}: ${fmt(s.values[best],2)}`).filter(Boolean).join(' · ');$('tooltip').textContent=`${labels[best]} · ${items}`;$('tooltip').style.left=`${e.clientX}px`;$('tooltip').style.top=`${e.clientY}px`;$('tooltip').style.opacity=1};canvas.onmouseleave=()=>$('tooltip').style.opacity=0}
function renderOverview(){const rows=D.quarterly.filter(x=>Number.isFinite(x.growth)),values=rows.map(x=>x.growth),labels=rows.map(x=>x.period.replace(/^\d{4}-/,'').replace('Q','Quý '));barChart('quarter-chart',labels,values,{min:0,max:Math.max(1,Math.ceil(Math.max(...values)/2)*2),tick:v=>fmt(v,0)+'%',labels:values.map(v=>fmt(v,2)+'%'),series:'Tăng trưởng GDP cùng kỳ (%)'})}
function renderQuarterlyGDP(){const q10=D.quarterlyGDP2010,q20=D.quarterlyGDP2020,q20Chart=[...q20.filter(x=>x.period<='2025-Q3'),{period:'2025-Q4',value:null},...q20.filter(x=>x.period>='2026-Q1')];lineChart('quarterly-gdp-2010-chart',q10.map(x=>x.period),[{name:'GDP thực (nghìn tỷ VND, giá 2010)',values:q10.map(x=>x.value),color:colors.blue}],{min:0,tick:v=>fmt(v,0)});lineChart('quarterly-gdp-2020-chart',q20Chart.map(x=>x.period),[{name:'GDP thực (nghìn tỷ VND, giá 2020)',values:q20Chart.map(x=>x.value),color:colors.green}],{min:0,tick:v=>fmt(v,0)});$('quarterly-reconciliation-table').innerHTML=`<table class="table"><thead><tr><th>Năm</th><th>GDP năm (nghìn tỷ VND)</th><th>Tổng bốn quý</th><th>Chênh lệch</th><th>Kiểm tra</th></tr></thead><tbody>${D.quarterlyReconciliation.map(x=>`<tr><td>${x.year}</td><td>${fmt(x.annual,2)}</td><td>${fmt(x.quarterSum,2)}</td><td>${x.differencePct>0?'+':''}${fmt(x.differencePct,4)}%</td><td>${x.status}</td></tr>`).join('')}</tbody></table>`}
function renderGdp(){const start=Number($('start-year').value),metric=$('gdp-metric').value,rows=D.gdp.filter(x=>x.year>=start),labels=rows.map(x=>String(x.year)),growth=metric==='growth';$('gdp-subtitle').textContent=growth?'Tăng trưởng GDP thực so với năm trước · %':'USD cố định 2015 · tỷ USD · World Bank';$('gdp-legend').textContent=growth?'Tăng trưởng GDP thực':'GDP thực';const values=rows.map(x=>x[metric]);lineChart('gdp-chart',labels,[{name:growth?'Tăng trưởng GDP thực (%)':'GDP thực (tỷ USD)',values,color:colors.blue}],growth?{tick:v=>fmt(v,0)+'%'}:{min:0,max:Math.ceil(Math.max(...values)/50)*50,tick:v=>fmt(v,0)});}
function renderSectors(){const year=Number($('sector-year').value),record=D.sectors.find(x=>x.year===year)||D.sectors[D.sectors.length-1],items=record.shares.filter(x=>Number.isFinite(x.value)),max=Math.max(1,...items.map(x=>x.value));$('sector-bars').innerHTML=items.map(x=>`<div class="region-row"><span class="region-name">${x.label}</span><div class="track"><div class="fill" style="width:${x.value/max*100}%;background:${x.color}"></div></div><span class="region-value">${fmt(x.value,2)}%</span></div>`).join('');renderSectorTrend();renderSectorCompare()}
function renderSectorTrend(){const rows=D.sectors,labels=rows.map(x=>String(x.year)),names=[...new Set(rows.flatMap(x=>x.shares.map(s=>s.label)))],palette=[colors.green,colors.blue,colors.purple,colors.orange];const series=names.map((name,i)=>({name,values:rows.map(row=>row.shares.find(s=>s.label===name)?.value??null),color:palette[i%palette.length]}));lineChart('sector-trend-chart',labels,series,{min:0,max:60,tick:v=>fmt(v,0)+'%'})}
function renderSectorCompare(){const names={nong_lam_thuy_san:'Nông, lâm, thủy sản',cong_nghiep_xay_dung:'Công nghiệp, xây dựng',dich_vu:'Dịch vụ',thue_san_pham:'Thuế sản phẩm trừ trợ cấp'};$('sector-compare-table').innerHTML=`<table class="table"><thead><tr><th>Khu vực</th><th>Giá trị 2025 (nghìn tỷ VND)</th><th>Tỷ trọng 2025</th><th>Tăng danh nghĩa</th><th>Đổi tỷ trọng</th></tr></thead><tbody>${D.sectorCompare.map(x=>`<tr><td>${names[x.name]||x.name}</td><td>${fmt(x.value,1)}</td><td>${fmt(x.share,2)}%</td><td>${fmt(x.growth,2)}%</td><td>${x.shareChange>0?'+':''}${fmt(x.shareChange,2)} điểm %</td></tr>`).join('')}</tbody></table>`}
function renderRegions(){const year=Number($('grdp-year').value),record=D.regions.find(x=>x.year===year),items=record?record.items:[];const max=Math.max(1,...items.map(x=>x.share));$('region-sub').textContent=`${year} · % tổng GRDP sáu vùng · không cộng cùng tỉnh thành phần`;$('region-bars').innerHTML=items.map(x=>`<div class="region-row"><span class="region-name">${x.name}</span><div class="track"><div class="fill" style="width:${x.share/max*100}%"></div></div><span class="region-value">${fmt(x.share,2)}%</span></div>`).join('')}
function renderProvinces(){const year=Number($('grdp-year').value),metric=$('province-metric').value,direction=$('province-direction').value,record=D.provinces.find(x=>x.year===year),items=record?record.items:[],sorted=[...items].filter(x=>Number.isFinite(x[metric])).sort((a,b)=>direction==='top'?b[metric]-a[metric]:a[metric]-b[metric]),rows=sorted.slice(0,10),labels={grdp:`GRDP ${year} (nghìn tỷ VND)`,perCapita:'GRDP/người (triệu VND)',growth:'Tăng trưởng nguồn (%)'},unit=metric==='grdp'?1000:1;$('province-sub').textContent=`${direction==='top'?'Top':'Bottom'} 10 năm ${year} · ${labels[metric]}`;$('province-table').innerHTML=`<table class="table"><thead><tr><th>Hạng</th><th>Tỉnh/thành</th><th>${labels[metric]}</th></tr></thead><tbody>${rows.map((x,i)=>`<tr><td>${i+1}</td><td>${x.name}</td><td>${fmt(x[metric]/unit,metric==='grdp'?2:1)}${metric==='growth'?'%':''}</td></tr>`).join('')}</tbody></table>`}
function renderTrade(){const labels=D.trade.map(x=>x.month.slice(5));lineChart('trade-flow-chart',labels,[{name:'Xuất khẩu (tỷ USD)',values:D.trade.map(x=>x.export),color:colors.blue},{name:'Nhập khẩu (tỷ USD)',values:D.trade.map(x=>x.import),color:colors.orange}],{min:0,tick:v=>fmt(v,0)});barChart('trade-chart',labels,D.trade.map(x=>x.balance),{min:-Math.ceil(Math.abs(Math.min(...D.trade.map(x=>x.balance))))-1,max:Math.ceil(Math.max(...D.trade.map(x=>x.balance)))+1,tick:v=>fmt(v,0),series:'Cán cân (tỷ USD)'});const e=D.trade.reduce((a,x)=>a+x.export,0),im=D.trade.reduce((a,x)=>a+x.import,0);$('export-total').textContent=fmt(e,2)+' tỷ USD';$('import-total').textContent=fmt(im,2)+' tỷ USD';$('trade-total').textContent=fmt(e-im,2)+' tỷ USD'}
function renderIip(){lineChart('iip-chart',D.iip.map(x=>x.month.slice(5)),[{name:'IIP (2015=100)',values:D.iip.map(x=>x.index),color:colors.purple}],{min:0,max:240,tick:v=>fmt(v,0)})}
function renderRetail(){lineChart('retail-annual-chart',D.retailAnnual.map(x=>String(x.year)),[{name:'Tổng mức bán lẻ (nghìn tỷ VND)',values:D.retailAnnual.map(x=>x.totalT),color:colors.blue}],{min:0,tick:v=>fmt(v,0)});lineChart('fdi-annual-chart',D.fdiAnnual.map(x=>String(x.year)),[{name:'Vốn đăng ký dự án (tỷ USD)',values:D.fdiAnnual.map(x=>x.registeredB),color:colors.blue},{name:'Vốn thực hiện (tỷ USD)',values:D.fdiAnnual.map(x=>x.implementedB),color:colors.green}],{min:0,tick:v=>fmt(v,0)});lineChart('retail-month-chart',D.retailMonthly.map(x=>x.month.slice(5)),[{name:'Bán lẻ danh nghĩa (nghìn tỷ VND)',values:D.retailMonthly.map(x=>x.totalT),color:colors.orange}],{min:0,tick:v=>fmt(v,0)});$('retail-month-table').innerHTML=`<table class="table"><thead><tr><th>Kỳ</th><th>Tăng danh nghĩa YoY</th><th>Tăng thực lũy kế</th></tr></thead><tbody>${D.retailMonthly.map(x=>`<tr><td>${x.month}</td><td>${fmt(x.nominalGrowth,1)}%</td><td>${fmt(x.realCumulative,1)}%</td></tr>`).join('')}</tbody></table>`;const f=D.fdiLatest;$('fdi-registered').textContent=fmt(f.registeredB,2)+' tỷ USD';$('fdi-implemented').textContent=fmt(f.implementedB,2)+' tỷ USD';$('fdi-growth').textContent=`Đăng ký +${fmt(f.registeredGrowth,1)}% · thực hiện +${fmt(f.implementedGrowth,1)}%`;$('fdi-note').textContent=`Kỳ ${f.periodLabel} đến ${f.period}; số đăng ký 2026 bao gồm vốn cấp mới, điều chỉnh và góp vốn/mua cổ phần, không đồng nhất với vốn dự án cấp phép trong chuỗi năm.`}
function scatterChart(id,pair){const canvas=$(id),{c,w,h}=setupCanvas(canvas),p={l:48,r:14,t:12,b:30},pts=pair?.points||[];if(!pts.length){c.fillStyle=css('--muted');c.fillText('Không đủ dữ liệu cho cặp biến này',p.l,30);return}let xmin=Math.min(...pts.map(x=>x.x)),xmax=Math.max(...pts.map(x=>x.x)),ymin=Math.min(...pts.map(x=>x.y)),ymax=Math.max(...pts.map(x=>x.y));if(xmin===xmax){xmin-=1;xmax+=1}if(ymin===ymax){ymin-=1;ymax+=1}const dx=(xmax-xmin)*.08,dy=(ymax-ymin)*.08;xmin-=dx;xmax+=dx;ymin-=dy;ymax+=dy;const sx=v=>p.l+(w-p.l-p.r)*(v-xmin)/(xmax-xmin),sy=v=>p.t+(h-p.t-p.b)*(1-(v-ymin)/(ymax-ymin));c.font='10px Segoe UI,Arial';for(let k=0;k<4;k++){const xv=xmin+(xmax-xmin)*k/3,yv=ymin+(ymax-ymin)*k/3;c.strokeStyle=css('--line');c.beginPath();c.moveTo(sx(xv),p.t);c.lineTo(sx(xv),h-p.b);c.stroke();c.beginPath();c.moveTo(p.l,sy(yv));c.lineTo(w-p.r,sy(yv));c.stroke();c.fillStyle=css('--muted');c.fillText(fmt(xv,1),sx(xv)-10,h-8);c.fillText(fmt(yv,1),3,sy(yv)+3)}pts.forEach(pt=>{c.beginPath();c.arc(sx(pt.x),sy(pt.y),4,0,Math.PI*2);c.fillStyle=colors.blue;c.globalAlpha=.75;c.fill();c.globalAlpha=1});canvas.onmousemove=e=>{const r=canvas.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;let best=null,dist=16;pts.forEach(pt=>{const d=Math.hypot(sx(pt.x)-mx,sy(pt.y)-my);if(d<dist){dist=d;best=pt}});if(best){$('tooltip').textContent=`${best.year} · X ${fmt(best.x,2)} · Y ${fmt(best.y,2)}`;$('tooltip').style.left=`${e.clientX}px`;$('tooltip').style.top=`${e.clientY}px`;$('tooltip').style.opacity=1}else $('tooltip').style.opacity=0};canvas.onmouseleave=()=>$('tooltip').style.opacity=0}
function renderScatter(){const pair=D.scatterComparisons[Number($('scatter-select').value)]||D.scatterComparisons[0];scatterChart('macro-scatter-chart',pair);$('scatter-summary').textContent=`${pair.title} · Pearson ${fmt(pair.pearson,2)} · Spearman ${fmt(pair.spearman,2)} · n=${pair.n}; chỉ mô tả, không suy luận nhân quả.`}
function renderMacro(){lineChart('macro-monthly-chart',D.monthlyMacro.map(x=>x.month),[{name:'CPI (01/2020=100)',values:D.monthlyMacro.map(x=>x.cpi100),color:colors.blue},{name:'Tỷ giá VND/USD (01/2020=100)',values:D.monthlyMacro.map(x=>x.fx100),color:colors.green}],{min:90,tick:v=>fmt(v,0)});renderScatter();const rows=[...D.scatterComparisons];$('correlation-table').innerHTML=`<table class="table"><thead><tr><th>Cặp biến</th><th>Pearson</th><th>Spearman</th><th>n</th></tr></thead><tbody>${rows.map(x=>`<tr><td>${x.title}</td><td>${fmt(x.pearson,3)}</td><td>${fmt(x.spearman,3)}</td><td>${x.n}</td></tr>`).join('')}</tbody></table>`;renderAnnualMacro()}
function renderAnnualMacro(){const raw=$('macro-years').value,count=raw==='all'?D.macroAnnual.length:Number(raw),rows=D.macroAnnual.slice(-count).reverse(),cell=v=>v===null?'—':fmt(v,2)+'%';$('macro-annual-table').innerHTML=`<table class="table"><thead><tr><th>Năm</th><th>Tăng GDP thực</th><th>CPI YoY</th><th>Trade/GDP</th><th>Cán cân/GDP</th><th>FDI thực hiện/GDP</th><th>Bán lẻ thực ước tính</th></tr></thead><tbody>${rows.map(x=>`<tr><td>${x.year}</td><td>${cell(x.realGrowth)}</td><td>${cell(x.inflation)}</td><td>${cell(x.tradeToGdp)}</td><td>${cell(x.balanceToGdp)}</td><td>${cell(x.fdiToGdp)}</td><td>${cell(x.retailRealGrowth)}</td></tr>`).join('')}</tbody></table>`}
const DRIVER_COLORS=['#3288e8','#25b886','#f4a62a','#e45a65','#7856d8','#16a6a1','#b66ad0'];
const driverPct=(x,d=2)=>x===null||x===undefined||!Number.isFinite(Number(x))?'—':fmt(x,d);
function renderGrowthDrivers(){
  const G=D.growthDrivers, selectedYear=Number($('driver-year').value), contribution=G.contributions.find(x=>Number(x.nam)===selectedYear);
  const contributionDefs=[['Vốn cố định','dong_gop_von_co_dinh_diem_pct'],['Tồn kho','dong_gop_ton_kho_diem_pct'],['Tiêu dùng nhà nước','dong_gop_tieu_dung_nha_nuoc_diem_pct'],['Tiêu dùng hộ gia đình','dong_gop_tieu_dung_ho_gia_dinh_diem_pct'],['Cán cân hàng hóa & dịch vụ','dong_gop_can_can_hang_hoa_dich_vu_diem_pct'],['Sai số thống kê','dong_gop_chenh_lech_thong_ke_diem_pct']];
  const validContributions=contributionDefs.filter(([,key])=>Number.isFinite(contribution?.[key]));
  $('contribution-sub').textContent=contribution?`Năm ${selectedYear} · GDP tăng ${driverPct(contribution.tang_truong_gdp_thuc_chi_tieu_pct)}% · đóng góp điểm phần trăm · ${contribution.trang_thai==='uoc_tinh'?'ước tính':contribution.trang_thai==='so_bo'?'sơ bộ':'theo bảng NSO'}`:`Năm ${selectedYear} · chuỗi đổi năm gốc, không phân rã`;
  barChart('driver-contribution-chart',validContributions.map(x=>x[0]),validContributions.map(([,key])=>contribution[key]),{tick:v=>fmt(v,1),labels:validContributions.map(([,key])=>fmt(contribution[key],2)),series:'Đóng góp (điểm %)'});
  $('contribution-table').innerHTML=contribution?`<table class="table"><tbody><tr><th>Tăng GDP thực</th><td>${driverPct(contribution.tang_truong_gdp_thuc_chi_tieu_pct)}%</td><th>Tổng đóng góp tính lại</th><td>${driverPct(contribution.tong_dong_gop_phan_ra_diem_pct)} điểm %</td><th>Sai lệch</th><td>${driverPct(contribution.sai_lech_phan_ra_diem_pct,3)} điểm %</td></tr></tbody></table>`:'Không có quan sát';

  const sectorYears=[...new Set(G.sectorGrowth.map(x=>Number(x.nam)))].sort((a,b)=>a-b), sectorNames=['Nông, lâm, thủy sản','Công nghiệp và xây dựng','Dịch vụ'];
  lineChart('sector-real-growth-chart',sectorYears.map(String),sectorNames.map((name,i)=>({name,values:sectorYears.map(y=>G.sectorGrowth.find(x=>Number(x.nam)===y&&x.nganh===name)?.tang_truong_yoy_pct??null),color:DRIVER_COLORS[i]})),{zero:true,tick:v=>fmt(v,1)});
  const laborYears=[...new Set(G.employment.map(x=>Number(x.nam)))].sort((a,b)=>a-b), laborNames=['Nông, lâm, thủy sản','Công nghiệp và xây dựng','Dịch vụ'];
  lineChart('employment-share-chart',laborYears.map(String),laborNames.map((name,i)=>({name,values:laborYears.map(y=>G.employment.find(x=>Number(x.nam)===y&&x.khu_vuc===name)?.ty_trong_lao_dong_pct??null),color:DRIVER_COLORS[i]})),{min:0,max:70,tick:v=>fmt(v,0)});
  const productivityYears=[...new Set(G.productivity.map(x=>Number(x.nam)))].sort((a,b)=>a-b);
  lineChart('productivity-proxy-chart',productivityYears.map(String),laborNames.map((name,i)=>({name,values:productivityYears.map(y=>G.productivity.find(x=>Number(x.nam)===y&&x.khu_vuc===name)?.nang_suat_thuc_proxy_trieu_vnd_2010_nguoi??null),color:DRIVER_COLORS[i]})),{min:0,tick:v=>fmt(v,0)});
  const investmentYears=[...new Set(G.investment.map(x=>Number(x.nam)))].sort((a,b)=>a-b), ownerNames=['Nhà nước','Ngoài nhà nước','Khu vực FDI'];
  lineChart('investment-ownership-chart',investmentYears.map(String),ownerNames.map((name,i)=>({name,values:investmentYears.map(y=>G.investment.find(x=>Number(x.nam)===y&&x.loai_hinh_so_huu===name)?.gia_tri_nghin_ty_vnd??null),color:DRIVER_COLORS[i]})),{min:0,tick:v=>fmt(v,0)});
  const latestInvestmentYear=Math.max(...G.investmentShares.map(x=>Number(x.nam))), ownerRows=G.investmentShares.filter(x=>Number(x.nam)===latestInvestmentYear);
  $('investment-share-table').innerHTML=`<table class="table"><thead><tr><th>Cơ cấu sở hữu ${latestInvestmentYear}</th><th>Tỷ trọng giá hiện hành</th><th>Trạng thái</th></tr></thead><tbody>${ownerRows.map(x=>`<tr><td>${x.loai_hinh_so_huu}</td><td>${driverPct(x.ty_trong_pct)}%</td><td>${x.trang_thai==='so_bo'?'Sơ bộ':'Nguồn'}</td></tr>`).join('')}</tbody></table>`;

  const panel=G.panel, panelYears=panel.map(x=>Number(x.nam));
  const fiscalYears=panel.filter(x=>Number.isFinite(x.dau_tu_phat_trien_chi_ngan_sach_tren_gdp_pct)).map(x=>Number(x.nam));
  lineChart('fiscal-investment-chart',fiscalYears.map(String),[
    {name:'Chi đầu tư phát triển/GDP (%)',values:fiscalYears.map(y=>panel.find(x=>Number(x.nam)===y)?.dau_tu_phat_trien_chi_ngan_sach_tren_gdp_pct??null),color:colors.blue},
    {name:'Chi đầu tư phát triển/tổng chi (%)',values:fiscalYears.map(y=>panel.find(x=>Number(x.nam)===y)?.ty_trong_dau_tu_phat_trien_trong_chi_pct??null),color:colors.orange},
  ],{min:0,tick:v=>fmt(v,0)});
  const financial=panel.filter(x=>Number.isFinite(x.du_no_tin_dung_tren_gdp_pct)||Number.isFinite(x.can_can_vang_lai_tren_gdp_pct)), financialYears=financial.map(x=>Number(x.nam));
  lineChart('credit-current-chart',financialYears.map(String),[
    {name:'Dư nợ tín dụng/GDP (%)',values:financial.map(x=>x.du_no_tin_dung_tren_gdp_pct??null),color:colors.blue},
    {name:'Tài khoản vãng lai/GDP (%)',values:financial.map(x=>x.can_can_vang_lai_tren_gdp_pct??null),color:colors.green},
  ],{zero:true,tick:v=>fmt(v,0)});
  const rateYears=[...new Set(G.rates.map(x=>Number(x.nam)))].sort((a,b)=>a-b), rateNames=[...new Set(G.rates.map(x=>x.nhan))];
  lineChart('interest-rates-chart',rateYears.map(String),rateNames.map((name,i)=>({name,values:rateYears.map(y=>G.rates.find(x=>Number(x.nam)===y&&x.nhan===name)?.gia_tri_pct??null),color:DRIVER_COLORS[i]})),{min:0,tick:v=>fmt(v,1)});
  const unemploymentRows=G.unemployment.filter(x=>x.khu_vuc_cu_tru==='WHOLE COUNTRY'&&x.vung_kinh_te!=='Total'), unemploymentYears=[...new Set(unemploymentRows.map(x=>Number(x.nam)))].sort((a,b)=>a-b), regionNames=[...new Set(unemploymentRows.map(x=>x.vung_kinh_te))];
  const regionLabels={'Red River Delta':'Đồng bằng sông Hồng','Northern midlands and mountain areas':'Trung du và miền núi phía Bắc','North Central and Central coastal areas':'Bắc Trung Bộ & duyên hải miền Trung','Central Highlands':'Tây Nguyên','South East':'Đông Nam Bộ','Mekong River Delta':'Đồng bằng sông Cửu Long'};
  lineChart('unemployment-region-chart',unemploymentYears.map(String),regionNames.map((name,i)=>({name:regionLabels[name]||name,values:unemploymentYears.map(y=>unemploymentRows.find(x=>Number(x.nam)===y&&x.vung_kinh_te===name)?.ty_le_that_nghiep_luc_luong_lao_dong_trong_do_tuoi_pct??null),color:DRIVER_COLORS[i]})),{min:0,tick:v=>fmt(v,1)});

  const tfp=G.tfp;
  barChart('tfp-chart',tfp.map(x=>x.giai_doan),tfp.map(x=>x.dong_gop_tfp_pct),{min:0,max:100,labels:tfp.map(x=>fmt(x.dong_gop_tfp_pct,1)+'%'),tick:v=>fmt(v,0),series:'Đóng góp TFP (%)',colors:tfp.map((x,i)=>DRIVER_COLORS[i+1])});
  $('tfp-table').innerHTML=`<table class="table"><thead><tr><th>Kỳ</th><th>Vốn</th><th>Lao động</th><th>TFP</th><th>Tăng trưởng TFP</th></tr></thead><tbody>${tfp.map(x=>`<tr><td>${x.giai_doan}</td><td>${driverPct(x.dong_gop_von_pct)}%</td><td>${driverPct(x.dong_gop_lao_dong_pct)}%</td><td>${driverPct(x.dong_gop_tfp_pct)}%</td><td>${driverPct(x.tang_truong_tfp_pct)}%</td></tr>`).join('')}</tbody></table>`;

  const commodityRows=G.commodities, commodityYears=[...new Set(commodityRows.map(x=>x.thoi_gian))].sort(), commodityNames=[...new Set(commodityRows.map(x=>x.hang_hoa))];
  lineChart('commodity-index-chart',commodityYears,commodityNames.map((name,i)=>({name,values:commodityYears.map(m=>commodityRows.find(x=>x.thoi_gian===m&&x.hang_hoa===name)?.chi_so_2015_100??null),color:DRIVER_COLORS[i]})),{min:0,tick:v=>fmt(v,0)});

  const correlations=[...G.correlations].sort((a,b)=>Math.abs(b.pearson??0)-Math.abs(a.pearson??0));
  $('driver-correlation-table').innerHTML=`<table class="table"><thead><tr><th>Cặp so sánh</th><th>Pearson</th><th>Spearman</th><th>n</th><th>Giai đoạn</th></tr></thead><tbody>${correlations.map(x=>`<tr><td>${x.bien_y}</td><td>${driverPct(x.pearson,3)}</td><td>${driverPct(x.spearman,3)}</td><td>${x.so_quan_sat}</td><td>${x.giai_doan}</td></tr>`).join('')}</tbody></table>`;
  const rawCount=$('driver-table-years').value,count=rawCount==='all'?panel.length:Number(rawCount),annualRows=panel.slice(-count).reverse();
  $('driver-annual-table').innerHTML=`<table class="table"><thead><tr><th>Năm</th><th>GDP thực tăng</th><th>Nông nghiệp</th><th>Công nghiệp</th><th>Dịch vụ</th><th>Vốn cố định đóng góp</th><th>Tiêu dùng hộ đóng góp</th><th>Đầu tư thực tăng</th><th>CPI</th><th>Tín dụng/GDP</th><th>Chi đầu tư/GDP</th><th>Vãng lai/GDP</th><th>Thất nghiệp</th><th>Trạng thái</th></tr></thead><tbody>${annualRows.map(x=>`<tr><td>${x.nam}</td><td>${driverPct(x.tang_truong_gdp_thuc_pct)}%</td><td>${driverPct(x.tang_truong_nganh_nong_nghiep_pct)}%</td><td>${driverPct(x.tang_truong_nganh_cong_nghiep_xay_dung_pct)}%</td><td>${driverPct(x.tang_truong_nganh_dich_vu_pct)}%</td><td>${driverPct(x.dong_gop_von_co_dinh_diem_pct)} đ.%</td><td>${driverPct(x.dong_gop_tieu_dung_ho_gia_dinh_diem_pct)} đ.%</td><td>${driverPct(x.tang_truong_dau_tu_thuc_tong_yoy_pct)}%</td><td>${driverPct(x.lam_phat_cpi_yoy_pct)}%</td><td>${driverPct(x.du_no_tin_dung_tren_gdp_pct)}%</td><td>${driverPct(x.dau_tu_phat_trien_chi_ngan_sach_tren_gdp_pct)}%</td><td>${driverPct(x.can_can_vang_lai_tren_gdp_pct)}%</td><td>${driverPct(x.that_nghiep_do_tuoi_lao_dong_pct)}%</td><td>${x.trang_thai==='uoc_tinh'?'Ước tính':x.trang_thai==='so_bo'?'Sơ bộ':'—'}</td></tr>`).join('')}</tbody></table>`;
}
const ACTIVITY_COLORS=['#3288e8','#25b886','#f4a62a','#e45a65','#7856d8','#16a6a1','#b66ad0','#7c98b3','#d88441','#4b78bf','#4caa80','#9a72cc','#bc637b','#63a8bb'];
const ACTIVITY_SECTORS={agriculture:'Nông, lâm, thủy sản',industry:'Công nghiệp và xây dựng',services:'Dịch vụ'};
function renderDetailedSector(key){
  const prefix=`activity-${key}`,all=D.activityDetails.filter(x=>x.sectorKey===key),years=[...new Set(all.map(x=>Number(x.year)))].sort((a,b)=>a-b),latestYear=Math.max(...years),latest=all.filter(x=>Number(x.year)===latestYear).sort((a,b)=>(b.share??0)-(a.share??0)),nominal=latest.reduce((s,x)=>s+(x.nominal||0),0),share=latest.reduce((s,x)=>s+(x.share||0),0),sectorName=ACTIVITY_SECTORS[key];
  const broadGrowth=D.growthDrivers.sectorGrowth.find(x=>x.nganh===sectorName&&Number(x.nam)===latestYear),nineMonth=D.activityUpdates.find(x=>x.sectorKey===key&&x.period==='2026-9M'&&x.analysisLevel==='9m_broad');
  $(`${prefix}-nominal`).textContent=fmt(nominal/1000,1)+' nghìn tỷ';$(`${prefix}-share`).textContent=fmt(share,2)+'%';$(`${prefix}-growth`).textContent=broadGrowth&&broadGrowth.tang_truong_yoy_pct!==null?fmt(broadGrowth.tang_truong_yoy_pct,2)+'%':'—';$(`${prefix}-growth-2026`).textContent=nineMonth?fmt(nineMonth.realGrowth,2)+'%':'—';
  const maxShare=Math.max(1,...latest.map(x=>x.share||0));$(`${prefix}-composition`).innerHTML=latest.map(x=>`<div class="region-row"><span class="region-name" title="${x.activity}">${x.activity}</span><div class="track"><div class="fill" style="width:${(x.share||0)/maxShare*100}%;background:${ACTIVITY_COLORS[latest.indexOf(x)%ACTIVITY_COLORS.length]}"></div></div><span class="region-value">${fmt(x.share,2)}%</span></div>`).join('');
  const select=$(`${prefix}-select`),selected=select.value||'top5';select.innerHTML=`<option value="top5">5 hoạt động có tỷ trọng lớn nhất</option><option value="all">Tất cả hoạt động</option>${latest.map(x=>`<option value="${x.sourceActivity}">${x.activity}</option>`).join('')}`;select.value=[...latest.map(x=>x.sourceActivity),'top5','all'].includes(selected)?selected:'top5';
  const chartRows=select.value==='all'?latest:select.value==='top5'?latest.slice(0,5):latest.filter(x=>x.sourceActivity===select.value);const activityByYear=new Map(all.map(x=>[`${x.sourceActivity}|${x.year}`,x]));
  lineChart(`${prefix}-growth-chart`,years.map(String),chartRows.map((x,i)=>({name:x.activity,values:years.map(y=>activityByYear.get(`${x.sourceActivity}|${y}`)?.realGrowth??null),color:ACTIVITY_COLORS[i%ACTIVITY_COLORS.length]})),{zero:true,tick:v=>fmt(v,1)});
  $(`${prefix}-chart-note`).textContent=`Đang hiển thị ${chartRows.length}/${latest.length} hoạt động. Tăng trưởng thực lấy trực tiếp từ chỉ số năm trước = 100 của NSO.`;
  $(`${prefix}-annual-table`).innerHTML=`<table class="table"><thead><tr><th>Hoạt động kinh tế</th><th>GDP hiện hành (nghìn tỷ)</th><th>Tỷ trọng GDP</th><th>Tăng GDP thực</th><th>Đóng góp tăng GDP</th><th>Đổi tỷ trọng 5 năm</th></tr></thead><tbody>${latest.map(x=>`<tr><td>${x.activity}</td><td>${fmt(x.nominal/1000,2)}</td><td>${fmt(x.share,2)}%</td><td>${x.realGrowth===null?'—':fmt(x.realGrowth,2)+'%'}</td><td>${x.contribution===null?'—':fmt(x.contribution,2)+' điểm %'}</td><td>${x.shareChange5===null?'—':(x.shareChange5>0?'+':'')+fmt(x.shareChange5,2)+' điểm %'}</td></tr>`).join('')}</tbody></table>`;
  const updates=D.activityUpdates.filter(x=>x.sectorKey===key).sort((a,b)=>(a.period==='2026-Q3'?0:1)-(b.period==='2026-Q3'?0:1)||((a.analysisLevel==='9m_broad'?0:1)-(b.analysisLevel==='9m_broad'?0:1)));
  $(`${prefix}-update-table`).innerHTML=`<table class="table"><thead><tr><th>Kỳ</th><th>Hoạt động</th><th>Tăng GDP thực</th><th>Tỷ trọng đóng góp</th><th>Cơ cấu GDP 9T</th></tr></thead><tbody>${updates.map(x=>`<tr><td>${x.periodLabel}</td><td>${x.activity}</td><td>${fmt(x.realGrowth,2)}%</td><td>${fmt(x.contributionShare,2)}%</td><td>${x.gdpShare===null?'—':fmt(x.gdpShare,2)+'%'}</td></tr>`).join('')}</tbody></table>`;
}
function renderDetailedSectorByPage(page){const key=page.replace('sector-','');if(ACTIVITY_SECTORS[key])renderDetailedSector(key)}
const MODEL_LABELS={Naive_last_value:'Naive (giữ mức cuối)',Drift_mean_log_change:'Drift (tăng trưởng log TB)',Linear_log_trend:'Xu hướng log tuyến tính',GRU_logGDP:'GRU',LSTM_logGDP:'LSTM'};
const modelLabel=name=>MODEL_LABELS[name]||name;
const QUARTERLY_MODEL_LABELS={SeasonalNaive:'Seasonal Naive',SeasonalDrift:'Seasonal Drift',LogTrendQuarterDummies:'Log trend + biến giả quý',ETS_DampedAdditive:'ETS xu hướng giảm tốc'};
const quarterlyModelLabel=name=>QUARTERLY_MODEL_LABELS[name]||name;
function renderModels(){const key=$('model-metric').value,horizon=Number($('backtest-horizon').value),rows=D.metricsByHorizon.filter(x=>x.horizon===horizon).sort((a,b)=>(a[key]??Infinity)-(b[key]??Infinity)),value=x=>x[key],vals=rows.map(value),best=rows[0],colorsBy=rows.map((x,i)=>i===0?colors.green:colors.blue),metricNames={mape:'MAPE (%)',smape:'sMAPE (%)',mae:'MAE (tỷ USD 2015)',rmse:'RMSE (tỷ USD 2015)',mase:'MASE'},metricName=metricNames[key];$('metric-title').textContent=`${metricName} theo mô hình` ;barChart('model-chart',rows.map(x=>modelLabel(x.model)),vals,{min:0,max:Math.ceil(Math.max(...vals)/5)*5||1,colors:colorsBy,tick:v=>fmt(v,key==='mase'?1:0),labels:vals.map(v=>fmt(v,2)),series:metricName});$('backtest-sub').textContent=`Chân trời ${horizon} năm · ${best?.n||0} điểm kiểm thử cho mỗi mô hình`;$('model-summary').textContent=best?`${modelLabel(best.model)} đứng đầu theo ${metricName} ở chân trời ${horizon} năm; MAPE ${fmt(best.mape,2)}%, sMAPE ${fmt(best.smape,2)}%, RMSE ${fmt(best.rmse,2)} tỷ USD.`:'Chưa có kết quả cho lựa chọn này.';$('model-leaderboard').innerHTML=`<table class="table"><thead><tr><th>Mô hình</th><th>n</th><th>MAE (tỷ USD)</th><th>RMSE (tỷ USD)</th><th>MAPE</th><th>sMAPE</th><th>MASE</th></tr></thead><tbody>${rows.map((x,i)=>`<tr${i===0?' style="background:#eef8f3"':''}><td>${modelLabel(x.model)}</td><td>${x.n}</td><td>${fmt(x.mae,2)}</td><td>${fmt(x.rmse,2)}</td><td>${fmt(x.mape,2)}%</td><td>${fmt(x.smape,2)}%</td><td>${fmt(x.mase,2)}</td></tr>`).join('')}</tbody></table>`}
function renderQuarterlyModels(){const horizon=Number($('quarterly-backtest-horizon').value),metric=$('quarterly-model-metric').value,field={mape:'mape',rmse:'rmseT',mase:'mase'}[metric],rows=D.quarterlyMetrics.filter(x=>x.horizon===horizon).sort((a,b)=>a[field]-b[field]),values=rows.map(x=>x[field]),best=rows[0],metricName={mape:'MAPE (%)',rmse:'RMSE (nghìn tỷ VND)',mase:'MASE mùa vụ'}[metric];$('quarterly-backtest-sub').textContent=`Chân trời ${horizon} quý · ${best?.n||0} origin kiểm thử/mô hình · dữ liệu giá 2010`;barChart('quarterly-model-chart',rows.map(x=>quarterlyModelLabel(x.model)),values,{min:0,max:Math.max(...values)*1.15||1,colors:rows.map((x,i)=>i===0?colors.green:colors.blue),tick:v=>fmt(v,metric==='mape'?0:1),labels:values.map(v=>fmt(v,2)),series:metricName});$('quarterly-model-leaderboard').innerHTML=`<table class="table"><thead><tr><th>Mô hình</th><th>Origin n</th><th>MAPE</th><th>MAE (nghìn tỷ VND)</th><th>RMSE (nghìn tỷ VND)</th><th>MASE mùa vụ</th></tr></thead><tbody>${rows.map((x,i)=>`<tr${i===0?' style="background:#eef8f3"':''}><td>${quarterlyModelLabel(x.model)}</td><td>${x.n}</td><td>${fmt(x.mape,2)}%</td><td>${fmt(x.maeT,2)}</td><td>${fmt(x.rmseT,2)}</td><td>${fmt(x.mase,2)}</td></tr>`).join('')}</tbody></table>`}
function renderForecast(){const model=$('forecast-model').value,horizon=Number($('backtest-horizon').value),years=Array.from({length:46},(_,i)=>1985+i),actualMap=new Map(D.gdp.map(x=>[x.year,x.realB])),backtestMap=new Map(D.rollingHorizons.filter(x=>x.model===model&&x.horizon===horizon).map(x=>[x.year,x.forecastB])),futureRows=D.forecast2030.filter(x=>x.model===model),futureMap=new Map(futureRows.map(x=>[x.year,x.valueB])),lowerMap=new Map(futureRows.map(x=>[x.year,x.lower80B])),upperMap=new Map(futureRows.map(x=>[x.year,x.upper80B]));const actual=years.map(y=>actualMap.has(y)?actualMap.get(y):null),rolling=years.map(y=>backtestMap.has(y)?backtestMap.get(y):null),future=years.map(y=>futureMap.has(y)?futureMap.get(y):null),lower=years.map(y=>lowerMap.has(y)?lowerMap.get(y):null),upper=years.map(y=>upperMap.has(y)?upperMap.get(y):null);$('backtest-legend').textContent=`Backtest ${horizon} năm`;lineChart('forecast-chart',years.map(String),[{name:'GDP thực quan sát',values:actual,color:colors.blue},{name:`Dự báo backtest ${horizon} năm`,values:rolling,color:colors.orange},{name:'Dự báo 2026–2030',values:future,color:colors.purple},{name:'Cận dưới P80 kinh nghiệm',values:lower,color:'#9a8be0',lineWidth:1.2,dash:[4,3],noPoints:true},{name:'Cận trên P80 kinh nghiệm',values:upper,color:'#9a8be0',lineWidth:1.2,dash:[4,3],noPoints:true}],{min:0,tick:v=>fmt(v,0),band:{lower,upper,color:colors.purple}});const models=[...new Set(D.forecast2030.map(x=>x.model))],fyears=[...new Set(D.forecast2030.map(x=>x.year))].sort((a,b)=>a-b);$('forecast-table').innerHTML=`<table class="table"><thead><tr><th>Mô hình</th>${fyears.map(y=>`<th>${y}</th>`).join('')}</tr></thead><tbody>${models.map(name=>`<tr${name===model?' style="background:#eef6ff"':''}><td>${modelLabel(name)}</td>${fyears.map(y=>{const row=D.forecast2030.find(x=>x.model===name&&x.year===y);return `<td class="interval-cell">${row?`<b>${fmt(row.valueB,1)}</b><small>P80 ${fmt(row.lower80B,1)}–${fmt(row.upper80B,1)}</small>`:'—'}</td>`}).join('')}</tr>`).join('')}</tbody></table>`}
function renderQuality(){const passed=D.quality.filter(x=>x.status==='dat').length,failed=D.quality.length-passed;$('data-quality-summary').textContent=`${passed}/${D.quality.length} kiểm tra đạt · ${failed} mục cần xem lại · báo cáo gồm khóa trùng/thiếu, số dòng và các điều kiện miền dữ liệu.`;$('data-quality').innerHTML=`<table class="table"><thead><tr><th>Tệp/kiểm tra</th><th>Số dòng</th><th>Trùng khóa</th><th>Ô khóa thiếu</th><th>Tổng ô thiếu</th><th>Trạng thái</th><th>Ghi chú</th></tr></thead><tbody>${D.quality.map(x=>`<tr><td>${x.file}</td><td>${x.rows}</td><td>${x.duplicates}</td><td>${x.missingKey}</td><td>${x.missing}</td><td><span class="status-tag${x.status==='dat'?'':' warn'}">${x.status==='dat'?'Đạt':'Xem lại'}</span></td><td>${x.note}</td></tr>`).join('')}</tbody></table>`}
function renderCatalog(){$('data-catalog').innerHTML=`<table class="table"><thead><tr><th>Bộ dữ liệu</th><th>Tệp</th><th>Nguồn</th><th>Tần suất</th><th>Giai đoạn</th><th>Trường dữ liệu chính</th><th>Lưu ý</th></tr></thead><tbody>${D.catalog.map(x=>`<tr><td>${x.dataset}</td><td>${x.file}</td><td><a href="${x.url}" target="_blank" rel="noopener">${x.source} ↗</a></td><td>${x.frequency}</td><td>${x.coverage}</td><td>${x.fields}</td><td>${x.note}</td></tr>`).join('')}</tbody></table>`;renderQuality();$('data-version-id').textContent=D.version.id;$('version-pill').textContent=`Version ${D.version.id}`;$('version-archive-link').href=D.version.archive||'#'}
function renderProjectInfo(){const p=D.projectInfo;$('project-file-count').textContent=Number(p.dataFileCount).toLocaleString('vi-VN');$('project-url-count').textContent=Number(p.sourceUrls.length).toLocaleString('vi-VN');$('project-source-count').textContent=Number(p.sourceGroups.length).toLocaleString('vi-VN');$('project-source-groups').textContent=`Nguồn ngoài: ${p.sourceGroups.join(' · ')}`;const models=$('project-models');models.replaceChildren();for(const [i,item] of p.models.entries()){const li=document.createElement('li');li.textContent=item.label;models.appendChild(li)}const quarterlyModels=$('project-quarterly-models');quarterlyModels.replaceChildren();for(const item of p.quarterlyModels){const li=document.createElement('li');li.textContent=item.label;quarterlyModels.appendChild(li)}const links=$('project-source-links');links.replaceChildren();for(const url of p.sourceUrls){const li=document.createElement('li');const a=document.createElement('a');a.href=url;a.target='_blank';a.rel='noopener noreferrer';a.textContent=url;li.appendChild(a);links.appendChild(li)}}
function renderCurrentPage(){const page=document.querySelector('.page.active')?.id;if(page==='overview'){renderOverview()}else if(page==='macro'){renderGdp();renderSectors();renderQuarterlyGDP()}else if(page==='macro-compare'){renderMacro()}else if(page==='growth-drivers'){renderGrowthDrivers()}else if(page.startsWith('sector-')){renderDetailedSectorByPage(page)}else if(page==='trade'){renderTrade();renderIip()}else if(page==='retail-fdi'){renderRetail()}else if(page==='regional'){renderRegions();renderProvinces()}else if(page==='models'){renderModels();renderQuarterlyModels();renderForecast()}else if(page==='data-status'){renderCatalog()}else if(page==='project-info'){renderProjectInfo()}}
function showPage(page){document.querySelectorAll('.page').forEach(x=>x.classList.toggle('active',x.id===page));document.querySelectorAll('.nav-link').forEach(x=>x.classList.toggle('active',x.dataset.page===page));$('page-footer').classList.toggle('active',page==='overview');const meta={overview:['Tổng quan GDP Việt Nam','Vietnam · End-to-End Macro Analytics'],macro:['EDA & Phân tích','GDP thực, tăng trưởng và cơ cấu ngành'],'macro-compare':['So sánh vĩ mô','CPI, tỷ giá, thương mại và tăng trưởng · tương quan mô tả'],'growth-drivers':['Động lực GDP','Chi tiêu · ngành · lao động · đầu tư · tài khóa · đối ngoại'],'sector-agriculture':['Nông, lâm, thủy sản','GDP danh nghĩa · tăng trưởng thực · cơ cấu · 9 tháng 2026'],'sector-industry':['Công nghiệp, xây dựng','So sánh các hoạt động và tăng trưởng GDP thực'],'sector-services':['Dịch vụ','So sánh 14 hoạt động dịch vụ bằng GDP và tăng trưởng thực'],trade:['Thương mại & sản xuất','Ngoại thương và IIP · giữ nguyên tần suất tháng'],'retail-fdi':['Bán lẻ & FDI','Tiêu dùng trong nước, vốn đăng ký và vốn thực hiện'],regional:['GRDP địa phương','So sánh sáu vùng và 63 tỉnh truyền thống'],models:['Training Lab','Backtest cuốn chiếu và dự báo GDP thực đến 2030'],'data-status':['Quản lý dữ liệu','Danh mục cấu trúc, nguồn và chất lượng dữ liệu'],'project-info':['Thông tin đề tài','Sinh viên · giảng viên hướng dẫn · dữ liệu · thuật toán']}[page];$('top-title').textContent=meta[0];$('top-subtitle').textContent=meta[1];window.scrollTo({top:0,behavior:'smooth'});renderCurrentPage()}
const q3=D.quarterly.find(x=>x.period==='2026-Q3');$('nominal-kpi').textContent=fmt(D.latest.nominalUsdB,2)+' tỷ USD';$('real-kpi').textContent=fmt(D.latest.realGrowth,2)+'%';$('q3-kpi').textContent=fmt(q3.growth,2)+'%';$('cpi-kpi').textContent=fmt(D.latest.cpiNineMonth,2)+'%';$('fx-value').textContent=fmt(D.latest.fxValue,0)+' VND';$('overview-fx').textContent=fmt(D.latest.fxValue,0)+' VND · '+D.latest.fxDate;$('cpi-period').textContent=D.latest.cpiDate+' · CPI tái tạo';
function csvCell(value){const raw=value===null||value===undefined?'':String(value);return `"${raw.replaceAll('"','""')}"`}
const localApiHost=location.port==='8000'&&['http:','https:'].includes(location.protocol);
const exportEndpoint=location.hostname==='vietnam-gdp-insight-api.onrender.com'||localApiHost?'/api/v1/exports':'https://vietnam-gdp-insight-api.onrender.com/api/v1/exports';
function submitExport(fileName,contentType,content){const form=document.createElement('form');form.method='POST';form.action=exportEndpoint;form.enctype='application/x-www-form-urlencoded';form.acceptCharset='UTF-8';form.style.display='none';for(const [name,value] of Object.entries({file_name:fileName,content_type:contentType,content})){const field=document.createElement('textarea');field.name=name;field.value=value;form.appendChild(field)}document.body.appendChild(form);form.submit();window.setTimeout(()=>form.remove(),1000)}
function downloadCsv(fileName,headers,rows){const csv='\ufeff'+[headers.map(csvCell).join(','),...rows.map(row=>headers.map(key=>csvCell(row[key])).join(','))].join('\r\n');submitExport(fileName,'text/csv; charset=utf-8',csv)}
function downloadJson(fileName,value){submitExport(fileName,'application/json; charset=utf-8',JSON.stringify(value,null,2))}
function bindDownloads(){
$('download-gdp').addEventListener('click',()=>downloadCsv('gdp_viet_nam_quan_sat_1985_2025.csv',['nam','gdp_thuc_ty_usd_2015','tang_truong_thuc_pct','gdp_danh_nghia_ty_usd_hien_hanh'],D.gdp.map(x=>({nam:x.year,gdp_thuc_ty_usd_2015:x.realB,tang_truong_thuc_pct:x.growth,gdp_danh_nghia_ty_usd_hien_hanh:x.nominalUsdB}))));
$('download-quarterly-gdp-2010').addEventListener('click',()=>downloadCsv('gdp_thuc_quy_gia_2010_2010Q1_2025Q4.csv',['thoi_gian','nam','quy','gdp_thuc_nghin_ty_vnd_gia_2010'],D.quarterlyGDP2010.map(x=>({thoi_gian:x.period,nam:x.year,quy:x.quarter,gdp_thuc_nghin_ty_vnd_gia_2010:x.value}))));
$('download-quarterly-gdp-2020').addEventListener('click',()=>downloadCsv('gdp_thuc_quy_gia_2020_2025Q1_2026Q3.csv',['thoi_gian','nam','quy','gdp_thuc_nghin_ty_vnd_gia_2020'],D.quarterlyGDP2020.map(x=>({thoi_gian:x.period,nam:x.year,quy:x.quarter,gdp_thuc_nghin_ty_vnd_gia_2020:x.value}))));
$('download-quarterly-backtest').addEventListener('click',()=>downloadCsv('backtest_mo_hinh_gdp_thuc_quy_gia_2010.csv',['ky_du_bao','ky_goc_du_bao','chan_troi_quy','mo_hinh','gdp_thuc_thuc_te_nghin_ty_vnd_gia_2010','gdp_thuc_du_bao_nghin_ty_vnd_gia_2010'],D.quarterlyBacktest.map(x=>({ky_du_bao:x.target,ky_goc_du_bao:x.origin,chan_troi_quy:x.horizon,mo_hinh:x.model,gdp_thuc_thuc_te_nghin_ty_vnd_gia_2010:x.actualT,gdp_thuc_du_bao_nghin_ty_vnd_gia_2010:x.forecastT}))));
$('download-sectors').addEventListener('click',()=>downloadCsv('co_cau_gdp_nganh_1986_2025.csv',['year','sector','share_pct'],D.sectors.flatMap(x=>x.shares.map(y=>({year:x.year,sector:y.label,share_pct:y.value})))));
$('download-trade').addEventListener('click',()=>downloadCsv('ngoai_thuong_thang_2026.csv',['month','export_usd_billion','import_usd_billion','balance_usd_billion'],D.trade));
$('download-iip').addEventListener('click',()=>downloadCsv('iip_thang_2026.csv',['month','iip_2015_100'],D.iip.map(x=>({month:x.month,iip_2015_100:x.index}))));
$('download-retail').addEventListener('click',()=>downloadCsv('ban_le_tieu_dung_1990_2026.csv',['tan_suat','ky','tong_muc_ban_le_nghin_ty_vnd','tang_truong_danh_nghia_yoy_pct','tang_truong_thuc_yoy_luy_ke_pct'],[...D.retailAnnual.map(x=>({tan_suat:'nam',ky:x.year,tong_muc_ban_le_nghin_ty_vnd:x.totalT,tang_truong_danh_nghia_yoy_pct:x.nominalGrowth,tang_truong_thuc_yoy_luy_ke_pct:x.realGrowth})),...D.retailMonthly.map(x=>({tan_suat:'thang',ky:x.month,tong_muc_ban_le_nghin_ty_vnd:x.totalT,tang_truong_danh_nghia_yoy_pct:x.nominalGrowth,tang_truong_thuc_yoy_luy_ke_pct:x.realCumulative}))]));
$('download-fdi').addEventListener('click',()=>downloadCsv('fdi_dau_tu_1991_2026.csv',['ky','tan_suat','von_dang_ky_ty_usd','von_thuc_hien_ty_usd','ghi_chu_dinh_nghia'],[...D.fdiAnnual.map(x=>({ky:x.year,tan_suat:'nam',von_dang_ky_ty_usd:x.registeredB,von_thuc_hien_ty_usd:x.implementedB,ghi_chu_dinh_nghia:'Vốn đăng ký dự án cấp phép và vốn thực hiện năm'})),{ky:D.fdiLatest.periodLabel,tan_suat:'luy_ke',von_dang_ky_ty_usd:D.fdiLatest.registeredB,von_thuc_hien_ty_usd:D.fdiLatest.implementedB,ghi_chu_dinh_nghia:'2026 lũy kế; đăng ký gồm cấp mới, điều chỉnh và góp vốn/mua cổ phần'}]));
$('download-grdp').addEventListener('click',()=>{const rows=[];D.regions.forEach(y=>y.items.forEach(x=>rows.push({year:y.year,area_type:'region',name:x.name,grdp_vnd_billion:'',share_pct:x.share,per_capita_million_vnd:x.perCapita,growth_pct:x.growth})));D.provinces.forEach(y=>y.items.forEach(x=>rows.push({year:y.year,area_type:'province',name:x.name,grdp_vnd_billion:x.grdp,share_pct:'',per_capita_million_vnd:x.perCapita,growth_pct:x.growth})));downloadCsv('grdp_tinh_vung_2018_2025.csv',['year','area_type','name','grdp_vnd_billion','share_pct','per_capita_million_vnd','growth_pct'],rows)});
$('download-backtest').addEventListener('click',()=>downloadCsv('backtest_gdp_nhieu_chan_troi.csv',['nam_du_bao','nam_goc','chan_troi_nam','mo_hinh','gdp_thuc_thuc_te_ty_usd_2015','gdp_thuc_du_bao_ty_usd_2015'],D.rollingHorizons.map(x=>({nam_du_bao:x.year,nam_goc:x.originYear,chan_troi_nam:x.horizon,mo_hinh:x.model,gdp_thuc_thuc_te_ty_usd_2015:x.actualB,gdp_thuc_du_bao_ty_usd_2015:x.forecastB}))));
$('download-projection').addEventListener('click',()=>downloadCsv('du_bao_gdp_thuc_2026_2030.csv',['nam_du_bao','mo_hinh','chan_troi_nam','gdp_thuc_du_bao_ty_usd_2015','can_duoi_P80_ty_usd_2015','can_tren_P80_ty_usd_2015','so_mau_hieu_chuan'],D.forecast2030.map(x=>({nam_du_bao:x.year,mo_hinh:x.model,chan_troi_nam:x.horizon,gdp_thuc_du_bao_ty_usd_2015:x.valueB,can_duoi_P80_ty_usd_2015:x.lower80B,can_tren_P80_ty_usd_2015:x.upper80B,so_mau_hieu_chuan:x.calibrationN}))));
$('download-catalog').addEventListener('click',()=>downloadCsv('danh_muc_nguon_du_lieu.csv',['dataset','file','source','frequency','coverage','fields','note'],D.catalog));
$('download-quality').addEventListener('click',()=>downloadCsv('kiem_tra_chat_luong_du_lieu.csv',['tep','so_dong_du_lieu','so_dong_trung_khoa','so_o_thieu_tren_khoa','so_o_thieu','ket_qua','ghi_chu'],D.quality.map(x=>({tep:x.file,so_dong_du_lieu:x.rows,so_dong_trung_khoa:x.duplicates,so_o_thieu_tren_khoa:x.missingKey,so_o_thieu:x.missing,ket_qua:x.status,ghi_chu:x.note}))));
 $('download-driver-panel').addEventListener('click',()=>downloadCsv('du_lieu_so_sanh_dong_luc_gdp.csv',Object.keys(D.growthDrivers.panel[0]||{}),D.growthDrivers.panel));
 $('download-driver-data').addEventListener('click',()=>downloadJson('bo_chi_bao_dong_luc_gdp.json',D.growthDrivers));
for(const key of Object.keys(ACTIVITY_SECTORS)){
  const annualRows=D.activityDetails.filter(x=>x.sectorKey===key),updateRows=D.activityUpdates.filter(x=>x.sectorKey===key);
  $(`download-activity-${key}`).addEventListener('click',()=>downloadCsv(`du_lieu_gdp_chi_tiet_${key}_nam.csv`,Object.keys(annualRows[0]||{}),annualRows));
  $(`download-activity-updates-${key}`).addEventListener('click',()=>downloadCsv(`du_lieu_gdp_chi_tiet_${key}_2026.csv`,Object.keys(updateRows[0]||{}),updateRows));
  $(`activity-${key}-select`).addEventListener('change',()=>renderDetailedSector(key));
}
const saveManifest=()=>downloadJson('data_version_manifest.json',D.versionManifest);$('download-version').addEventListener('click',saveManifest);$('version-download-inline').addEventListener('click',saveManifest);
}
function fillOptions(id,values,selected){$(id).innerHTML=values.map(v=>`<option value="${v}"${Number(v)===Number(selected)?' selected':''}>${v}</option>`).join('')}
fillOptions('sector-year',D.sectors.map(x=>x.year),2025);fillOptions('grdp-year',D.grdpYears,D.grdpYears[D.grdpYears.length-1]);fillOptions('driver-year',D.growthDrivers.contributions.filter(x=>Number.isFinite(x.tong_dong_gop_phan_ra_diem_pct)).map(x=>x.nam),2025);$('scatter-select').innerHTML=D.scatterComparisons.map((x,i)=>`<option value="${i}">${x.title}</option>`).join('');$('forecast-model').innerHTML=[...new Set(D.forecast2030.map(x=>x.model))].map(name=>`<option value="${name}"${name==='Drift_mean_log_change'?' selected':''}>${modelLabel(name)}</option>`).join('');$('version-pill').textContent=`Version ${D.version.id}`;$('data-version-id').textContent=D.version.id;$('version-archive-link').href=D.version.archive||'#';
bindDownloads();$('quarterly-backtest-horizon').addEventListener('change',renderQuarterlyModels);$('quarterly-model-metric').addEventListener('change',renderQuarterlyModels);$('backtest-horizon').addEventListener('change',()=>{renderModels();renderForecast()});$('start-year').addEventListener('change',renderGdp);$('gdp-metric').addEventListener('change',renderGdp);$('sector-year').addEventListener('change',renderSectors);$('grdp-year').addEventListener('change',()=>{renderRegions();renderProvinces()});$('province-metric').addEventListener('change',renderProvinces);$('province-direction').addEventListener('change',renderProvinces);$('model-metric').addEventListener('change',renderModels);$('forecast-model').addEventListener('change',renderForecast);$('scatter-select').addEventListener('change',renderScatter);$('macro-years').addEventListener('change',renderAnnualMacro);$('driver-year').addEventListener('change',renderGrowthDrivers);$('driver-table-years').addEventListener('change',renderGrowthDrivers);$('theme').addEventListener('click',()=>{document.body.classList.toggle('dark');renderCurrentPage()});window.addEventListener('resize',renderCurrentPage);document.querySelectorAll('.nav-link').forEach(button=>button.addEventListener('click',()=>showPage(button.dataset.page)));
renderCurrentPage();
</script>
<script src="assets/backtest-arena.js" defer></script>
</body>
</html>'''

rendered = html.replace("__DATA__", json.dumps(data, ensure_ascii=False, separators=(",", ":"))).replace("__SECTOR_PAGES__", sector_pages_html).replace("__ARENA_SECTION__", arena_fragment)
(ROOT / "dashboard.html").write_text(rendered, encoding="utf-8")
print(f"Wrote offline dashboard: {ROOT / 'dashboard.html'} ({len(rendered):,} characters)")

