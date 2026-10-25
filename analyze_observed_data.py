"""Create dashboard-ready comparisons and careful macroeconomic diagnostics.

All model evaluation uses observed annual real GDP, never the spline-derived
monthly series. Annual / quarterly / monthly data are kept at their native grain.
Requires pandas, numpy, statsmodels, scipy, torch.
"""
from __future__ import annotations

import csv
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from statsmodels.tsa.filters.hp_filter import hpfilter
from statsmodels.tsa.stattools import adfuller
from torch import nn
from data_paths import data_path

ROOT = Path(__file__).resolve().parent
OUT = ROOT
SEED = 20261023


def read_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(data_path(name), encoding="utf-8-sig")


def write_csv(name: str, frame: pd.DataFrame) -> None:
    frame.to_csv(data_path(name, for_write=True), index=False, encoding="utf-8-sig", float_format="%.8f")


def numcol(df: pd.DataFrame, col: str) -> pd.Series:
    return pd.to_numeric(df[col], errors="coerce")


def correlate(frame: pd.DataFrame, left: str, right: str, label: str,
              method: str, caveat: str) -> dict:
    pair = frame[[left, right]].apply(pd.to_numeric, errors="coerce").dropna()
    corr = pair[left].corr(pair[right], method=method) if len(pair) >= 3 else np.nan
    return {
        "so_sanh": label, "bien_x": left, "bien_y": right,
        "phuong_phap": method, "he_so_tuong_quan": corr,
        "so_quan_sat": len(pair), "ghi_chu": caveat,
    }


# Annual macro panel, joining only variables that genuinely share annual periods.
gdp = read_csv("du_lieu_gdp_tong_hop.csv")
gdp["nam"] = numcol(gdp, "nam").astype("Int64")
gdp = gdp.dropna(subset=["nam"]).drop_duplicates("nam").copy()
for c in ["gdp_danh_nghia_usd", "gdp_danh_nghia_vnd_ty", "gdp_thuc_usd_2015", "tang_truong_gdp_thuc_pct"]:
    gdp[c] = numcol(gdp, c)
gdp = gdp.sort_values("nam")
gdp["tang_truong_gdp_danh_nghia_usd_yoy_pct"] = gdp["gdp_danh_nghia_usd"].pct_change() * 100
gdp["tang_truong_gdp_danh_nghia_vnd_yoy_pct"] = gdp["gdp_danh_nghia_vnd_ty"].pct_change() * 100

fx = read_csv("du_lieu_ty_gia_usd_vnd.csv")
fx["thoi_gian"] = pd.to_datetime(fx["thoi_gian"], errors="coerce")
fx["ty_gia_usd_vnd"] = numcol(fx, "ty_gia_usd_vnd")
fx = fx.dropna(subset=["thoi_gian", "ty_gia_usd_vnd"]).sort_values("thoi_gian")
fx["loi_suat_log_thang_pct"] = np.log(fx["ty_gia_usd_vnd"]).diff() * 100
fx["thay_doi_ty_gia_mom_pct"] = fx["ty_gia_usd_vnd"].pct_change() * 100
fx["thay_doi_ty_gia_yoy_pct"] = fx["ty_gia_usd_vnd"].pct_change(12) * 100
fx["bien_dong_12_thang_annualized_pct"] = fx["loi_suat_log_thang_pct"].rolling(12, min_periods=12).std(ddof=1) * math.sqrt(12)
fx["nam"] = fx["thoi_gian"].dt.year
fx_annual = fx.groupby("nam", as_index=False).agg(
    ty_gia_usd_vnd_binh_quan_nam=("ty_gia_usd_vnd", "mean"),
    so_thang_ty_gia=("ty_gia_usd_vnd", "count"),
)
fx_annual["trang_thai_ty_gia_nam"] = np.where(fx_annual["so_thang_ty_gia"].eq(12), "du_12_thang", "nam_chua_du_12_thang")
write_csv("du_lieu_fx_bien_dong_thang.csv", fx[[
    "thoi_gian", "ty_gia_usd_vnd", "thay_doi_ty_gia_mom_pct", "thay_doi_ty_gia_yoy_pct",
    "loi_suat_log_thang_pct", "bien_dong_12_thang_annualized_pct", "trang_thai",
]])

cpi = read_csv("du_lieu_lam_phat_cpi.csv")
cpi["thoi_gian"] = pd.to_datetime(cpi["thoi_gian"], errors="coerce")
cpi["chi_so_cpi"] = numcol(cpi, "chi_so_cpi")
cpi = cpi.dropna(subset=["thoi_gian", "chi_so_cpi"]).sort_values("thoi_gian")
cpi["tang_cpi_mom_pct"] = cpi["chi_so_cpi"].pct_change() * 100
cpi["tang_cpi_yoy_pct"] = cpi["chi_so_cpi"].pct_change(12) * 100
cpi["trang_thai_chi_so"] = np.where(cpi["thoi_gian"].dt.year.le(2025), "quan_sat_nso", "tai_tao_tu_ty_le_luy_ke_da_lam_tron")
cpi["trang_thai_bien_dong"] = np.where(cpi["thoi_gian"].dt.year.le(2025), "tinh_tu_chi_so_quan_sat", "tinh_tu_chi_so_tai_tao_co_sai_so_lam_tron")
write_csv("du_lieu_cpi_phan_tich_thang.csv", cpi)

trade = read_csv("du_lieu_xuat_nhap_khau.csv")
trade["nam"] = numcol(trade, "nam").astype("Int64")
retail = read_csv("du_lieu_ban_le_tieu_dung.csv")
retail["nam"] = numcol(retail, "nam").astype("Int64")
fdi = read_csv("du_lieu_fdi_dau_tu.csv")
fdi["nam"] = numcol(fdi, "nam").astype("Int64")
cpi_annual = read_csv("du_lieu_lam_phat_cpi_nam_lich_su.csv")
cpi_annual["nam"] = numcol(cpi_annual, "nam").astype("Int64")

panel = gdp.merge(fx_annual, on="nam", how="left")
panel = panel.merge(trade, on="nam", how="left", suffixes=("", "_trade"))
panel = panel.merge(retail, on="nam", how="left", suffixes=("", "_retail"))
panel = panel.merge(fdi, on="nam", how="left", suffixes=("", "_fdi"))
panel = panel.merge(cpi_annual[["nam", "lam_phat_cpi_yoy_pct", "trang_thai"]].rename(columns={"trang_thai": "trang_thai_cpi_nam"}), on="nam", how="left")
panel["trade_to_gdp_pct"] = numcol(panel, "tong_kim_ngach_xuat_nhap_khau_usd") / numcol(panel, "gdp_danh_nghia_usd") * 100
panel["can_can_thuong_mai_tren_gdp_pct"] = numcol(panel, "can_can_thuong_mai_usd") / numcol(panel, "gdp_danh_nghia_usd") * 100
panel["xuat_khau_tren_gdp_pct"] = numcol(panel, "kim_ngach_xuat_khau_usd") / numcol(panel, "gdp_danh_nghia_usd") * 100
panel["nhap_khau_tren_gdp_pct"] = numcol(panel, "kim_ngach_nhap_khau_usd") / numcol(panel, "gdp_danh_nghia_usd") * 100
panel["ban_le_tren_gdp_pct"] = numcol(panel, "tong_muc_ban_le_vnd") / (numcol(panel, "gdp_danh_nghia_vnd_ty") * 1e9) * 100
panel["von_fdi_thuc_hien_tren_gdp_pct"] = numcol(panel, "von_fdi_thuc_hien_usd") / numcol(panel, "gdp_danh_nghia_usd") * 100
panel["von_fdi_dang_ky_tren_gdp_pct"] = numcol(panel, "von_dang_ky_du_an_fdi_usd") / numcol(panel, "gdp_danh_nghia_usd") * 100
panel["tang_truong_ban_le_danh_nghia_yoy_pct"] = numcol(panel, "tong_muc_ban_le_vnd").pct_change() * 100
panel["tang_truong_ban_le_thuc_uoc_tinh_yoy_pct"] = ((1 + panel["tang_truong_ban_le_danh_nghia_yoy_pct"] / 100) / (1 + numcol(panel, "lam_phat_cpi_yoy_pct") / 100) - 1) * 100
panel["ghi_chu_ban_le_thuc"] = "Ước tính gần đúng: tăng bán lẻ danh nghĩa đã giảm CPI chung; không thay thế chỉ số khối lượng bán lẻ chính thức."
write_csv("du_lieu_chi_so_kinh_te_hang_nam.csv", panel)

# Month-level comparisons: keep CPI and FX as observed/reconstructed in their own series.
monthly_compare = cpi.merge(fx[["thoi_gian", "ty_gia_usd_vnd", "thay_doi_ty_gia_mom_pct", "bien_dong_12_thang_annualized_pct"]], on="thoi_gian", how="outer")
monthly_compare = monthly_compare.sort_values("thoi_gian")
monthly_compare["ghi_chu_ghep"] = "CPI và FX là hai chuỗi độc lập; chỉ ghép theo tháng lịch để đối chiếu, không hàm ý quan hệ nhân quả."
write_csv("du_lieu_so_sanh_cpi_ty_gia_thang.csv", monthly_compare)

# Sector composition and shifts, using NSO current-price VND values.
sector = read_csv("du_lieu_gdp_co_cau_3_nganh.csv")
sector["nam"] = numcol(sector, "nam").astype("Int64")
sector = sector.sort_values("nam").copy()
sector_cols = [
    ("gdp_nong_lam_thuy_san_vnd_ty", "nong_lam_thuy_san"),
    ("gdp_cong_nghiep_xay_dung_vnd_ty", "cong_nghiep_xay_dung"),
    ("gdp_dich_vu_vnd_ty", "dich_vu"),
    ("thue_san_pham_tru_tro_cap_vnd_ty", "thue_san_pham"),
]
sector_comparison = []
for value_col, label in sector_cols:
    if value_col not in sector:
        continue
    share_col = {
        "nong_lam_thuy_san": "ty_trong_nong_lam_thuy_san_pct",
        "cong_nghiep_xay_dung": "ty_trong_cong_nghiep_xay_dung_pct",
        "dich_vu": "ty_trong_dich_vu_pct",
        "thue_san_pham": "ty_trong_thue_san_pham_pct",
    }[label]
    if share_col not in sector:
        continue
    item = pd.DataFrame({
        "nam": sector["nam"], "nhom_nganh": label,
        "gia_tri_them_danh_nghia_vnd_ty": numcol(sector, value_col),
        "ty_trong_trong_gdp_pct": numcol(sector, share_col),
        "trang_thai": sector["trang_thai"],
    })
    item["tang_truong_gia_tri_danh_nghia_yoy_pct"] = item["gia_tri_them_danh_nghia_vnd_ty"].pct_change() * 100
    item["thay_doi_ty_trong_so_voi_nam_truoc_diem_pct"] = item["ty_trong_trong_gdp_pct"].diff()
    sector_comparison.append(item)
sector_long = pd.concat(sector_comparison, ignore_index=True)
write_csv("du_lieu_so_sanh_co_cau_nganh.csv", sector_long)
sector_2025 = sector_long[sector_long["nam"].eq(2025)].copy()
sector_2025["so_sanh_nam"] = 2024
sector_2025 = sector_2025.rename(columns={
    "gia_tri_them_danh_nghia_vnd_ty": "gia_tri_danh_nghia_2025_vnd_ty",
    "ty_trong_trong_gdp_pct": "ty_trong_gdp_2025_pct",
    "tang_truong_gia_tri_danh_nghia_yoy_pct": "tang_truong_danh_nghia_2025_yoy_pct",
    "thay_doi_ty_trong_so_voi_nam_truoc_diem_pct": "thay_doi_ty_trong_2025_so_voi_2024_diem_pct",
})
write_csv("du_lieu_so_sanh_nganh_2025.csv", sector_2025)

# Province and region comparisons use the 63-province legacy geography in the source.
grdp = read_csv("du_lieu_grdp_63_tinh_thanh.csv")
grdp["nam"] = numcol(grdp, "nam").astype("Int64")
grdp["quy_mo_grdp_vnd"] = numcol(grdp, "quy_mo_grdp_vnd")
grdp["grdp_binh_quan_dau_nguoi_trieu_vnd"] = numcol(grdp, "grdp_binh_quan_dau_nguoi_trieu_vnd")
province = grdp[grdp["loai_dia_ban"].eq("tinh_thanh_63_truyen_thong")].copy()
prev = province[province["nam"].eq(2024)][["ten_tinh", "quy_mo_grdp_vnd"]].rename(columns={"quy_mo_grdp_vnd": "grdp_2024_vnd_ty"})
prov25 = province[province["nam"].eq(2025)].merge(prev, on="ten_tinh", how="left")
prov25["grdp_2025_vnd_ty"] = prov25["quy_mo_grdp_vnd"]
prov25["tang_truong_grdp_danh_nghia_tu_muc_grdp_pct"] = (prov25["grdp_2025_vnd_ty"] / prov25["grdp_2024_vnd_ty"] - 1) * 100
prov25["hang_grdp_2025"] = prov25["grdp_2025_vnd_ty"].rank(method="min", ascending=False).astype("Int64")
prov25["hang_grdp_binh_quan_dau_nguoi_2025"] = prov25["grdp_binh_quan_dau_nguoi_trieu_vnd"].rank(method="min", ascending=False).astype("Int64")
prov_total = prov25["grdp_2025_vnd_ty"].sum()
prov25["ty_trong_tong_grdp_63_tinh_pct"] = prov25["grdp_2025_vnd_ty"] / prov_total * 100
prov25["ghi_chu_so_sanh"] = "GRDP 2025 ước tính; tăng trưởng từ mức GRDP danh nghĩa 2024-2025 khác với chỉ số tăng trưởng GRDP nguồn (giá so sánh)."
prov25_out = prov25[[
    "ma_tinh", "ten_tinh", "ma_vung_kinh_te", "ten_vung_kinh_te", "grdp_2024_vnd_ty", "grdp_2025_vnd_ty",
    "tang_truong_grdp_danh_nghia_tu_muc_grdp_pct", "tang_truong_grdp_yoy_pct", "grdp_binh_quan_dau_nguoi_trieu_vnd",
    "hang_grdp_2025", "hang_grdp_binh_quan_dau_nguoi_2025", "ty_trong_tong_grdp_63_tinh_pct", "trang_thai", "ghi_chu_so_sanh",
]]
write_csv("du_lieu_so_sanh_grdp_63_tinh_2025.csv", prov25_out.sort_values("hang_grdp_2025"))
regions25 = grdp[(grdp["loai_dia_ban"].eq("vung_thong_ke")) & grdp["nam"].eq(2025)].copy()
regions_total = regions25["quy_mo_grdp_vnd"].sum()
regions25["ty_trong_tong_grdp_6_vung_pct"] = regions25["quy_mo_grdp_vnd"] / regions_total * 100
regions25["hang_grdp_2025"] = regions25["quy_mo_grdp_vnd"].rank(method="min", ascending=False).astype("Int64")
regions25["ghi_chu"] = "Sáu vùng thống kê; không cộng đồng thời với các tỉnh thành phần."
write_csv("du_lieu_so_sanh_grdp_6_vung_2025.csv", regions25[[
    "ma_vung_kinh_te", "ten_vung_kinh_te", "quy_mo_grdp_vnd", "grdp_binh_quan_dau_nguoi_trieu_vnd",
    "tang_truong_grdp_yoy_pct", "ty_trong_tong_grdp_6_vung_pct", "hang_grdp_2025", "trang_thai", "ghi_chu",
]].sort_values("hang_grdp_2025"))

# IIP against GDP: annual grain only; monthly GDP is not observed and cannot support monthly lead tests.
iip = read_csv("du_lieu_san_xuat_iip_nam.csv")
iip["nam"] = numcol(iip, "nam").astype("Int64")
iip["tang_truong_iip_yoy_pct"] = numcol(iip, "tang_truong_iip_yoy_pct")
iip_total = iip[iip["ten_nganh"].astype(str).str.strip().str.lower().isin(["total", "whole industry"])].drop_duplicates("nam")
iip_comp = gdp[["nam", "tang_truong_gdp_thuc_pct"]].merge(iip_total[["nam", "tang_truong_iip_yoy_pct"]], on="nam", how="inner").sort_values("nam")
for lag in range(0, 4):
    iip_comp[f"tang_truong_iip_t_minus_{lag}_pct"] = iip_comp["tang_truong_iip_yoy_pct"].shift(lag)
write_csv("du_lieu_so_sanh_iip_gdp_hang_nam.csv", iip_comp)

# Statistical comparisons on growth rates, not trending levels.
annual_cmp = panel.copy()
annual_cmp["tang_truong_ty_gia_binh_quan_nam_yoy_pct"] = numcol(annual_cmp, "ty_gia_usd_vnd_binh_quan_nam").pct_change() * 100
annual_cmp["tang_truong_xuat_khau_yoy_pct"] = numcol(annual_cmp, "kim_ngach_xuat_khau_usd").pct_change() * 100
annual_cmp["tang_truong_nhap_khau_yoy_pct"] = numcol(annual_cmp, "kim_ngach_nhap_khau_usd").pct_change() * 100
annual_cmp["tang_truong_fdi_thuc_hien_yoy_pct"] = numcol(annual_cmp, "von_fdi_thuc_hien_usd").pct_change() * 100
if not iip_total.empty:
    annual_cmp = annual_cmp.merge(iip_total[["nam", "tang_truong_iip_yoy_pct"]], on="nam", how="left")
    annual_cmp["tang_truong_iip_t_minus_1_pct"] = annual_cmp["tang_truong_iip_yoy_pct"].shift(1)
comparisons = []
specs = [
    ("tang_truong_gdp_thuc_pct", "lam_phat_cpi_yoy_pct", "Tăng trưởng GDP thực và lạm phát CPI năm", "quan_he_mo_ta; khong_suy_dien_nhan_qua"),
    ("tang_truong_gdp_thuc_pct", "tang_truong_ty_gia_binh_quan_nam_yoy_pct", "Tăng trưởng GDP thực và biến động tỷ giá bình quân năm", "Tỷ giá tăng nghĩa là VND/USD tăng; tương quan không hàm ý nhân quả."),
    ("tang_truong_gdp_thuc_pct", "tang_truong_iip_yoy_pct", "Tăng trưởng GDP thực và IIP cùng năm", "Mẫu IIP ngắn; chỉ mô tả, không khẳng định IIP dự báo GDP."),
    ("tang_truong_gdp_thuc_pct", "tang_truong_iip_t_minus_1_pct", "Tăng trưởng GDP thực và IIP năm trước", "Lag=1: IIP năm t-1 so với GDP thực năm t; mẫu rất nhỏ, mô tả."),
    ("tang_truong_gdp_thuc_pct", "tang_truong_ban_le_thuc_uoc_tinh_yoy_pct", "Tăng trưởng GDP thực và tăng trưởng bán lẻ thực ước tính", "Bán lẻ thực là proxy đã giảm CPI chung; không phải chỉ số khối lượng chính thức."),
    ("tang_truong_gdp_danh_nghia_usd_yoy_pct", "tang_truong_ty_gia_binh_quan_nam_yoy_pct", "Tăng trưởng GDP danh nghĩa USD và biến động tỷ giá", "GDP USD chịu ảnh hưởng quy đổi; chỉ quan hệ mô tả."),
]
for x, y, label, caution in specs:
    if x not in annual_cmp or y not in annual_cmp:
        continue
    for method in ["pearson", "spearman"]:
        comparisons.append(correlate(annual_cmp, x, y, label, method, caution))
write_csv("du_lieu_so_sanh_tuong_quan_vi_mo.csv", pd.DataFrame(comparisons))

# ADF: deterministic trend for log GDP level; intercept for log differences.
real = gdp.dropna(subset=["gdp_thuc_usd_2015"]).sort_values("nam")
log_real = np.log(real["gdp_thuc_usd_2015"].to_numpy(dtype=float))
adf_rows = []
for label, values, regression in [
    ("log_gdp_thuc_muc", log_real, "ct"),
    ("tang_truong_log_gdp_thuc_pct", np.diff(log_real) * 100, "c"),
]:
    result = adfuller(values, regression=regression, autolag="AIC", result_object=True)
    adf_rows.append({
        "chuoi": label, "bien_doi": "log-level" if regression == "ct" else "first-difference-of-log (approx growth %)" ,
        "n": len(values), "adf_statistic": result.statistic, "p_value": result.pvalue, "lag_chon_aic": result.lags,
        "so_quan_sat_huu_hieu": result.nobs, "regression": regression,
        "critical_1pct": result.critical_values["1%"], "critical_5pct": result.critical_values["5%"], "critical_10pct": result.critical_values["10%"],
        "ket_luan_muc_5pct": "bac_bo_unit_root" if result.pvalue < 0.05 else "khong_du_bang_chung_bac_bo_unit_root",
        "ghi_chu": "ADF nhạy với đặc tả và mẫu nhỏ; GDP spline tháng không được dùng.",
    })
write_csv("ket_qua_kiem_dinh_adf.csv", pd.DataFrame(adf_rows))

# Trend-cycle decomposition of annual log real GDP via HP filter, lambda=6.25.
# This is a detrending diagnostic, not an official measure of potential output.
cycle_log, trend_log = hpfilter(pd.Series(log_real), lamb=6.25)
decomp = pd.DataFrame({
    "nam": real["nam"].to_numpy(), "gdp_thuc_quan_sat_usd_2015": real["gdp_thuc_usd_2015"].to_numpy(),
    "log_gdp_thuc": log_real, "xu_huong_hp_log": np.asarray(trend_log),
    "gdp_xu_huong_hp_usd_2015": np.exp(np.asarray(trend_log)),
    "chu_ky_hp_pct_so_voi_xu_huong": (np.exp(np.asarray(cycle_log)) - 1) * 100,
})
decomp["ghi_chu"] = "HP filter lambda=6.25 cho chuỗi năm; chu kỳ nhạy với điểm đầu/cuối, không phải GDP tiềm năng chính thức."
write_csv("du_lieu_phan_ra_gdp_thuc_hang_nam.csv", decomp)

# Walk-forward one-step-ahead annual forecast comparison; scaler is fit per training fold.
torch.set_num_threads(1)
torch.use_deterministic_algorithms(True)
random.seed(SEED)
np.random.seed(SEED)
torch.manual_seed(SEED)


class RecurrentForecaster(nn.Module):
    def __init__(self, kind: str, hidden: int = 8):
        super().__init__()
        self.rnn = nn.GRU(1, hidden, batch_first=True) if kind == "GRU" else nn.LSTM(1, hidden, batch_first=True)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        output, _ = self.rnn(x)
        return self.head(output[:, -1, :])


def neural_predict(kind: str, train: np.ndarray, seed: int, window: int = 5) -> float:
    mean, std = float(train.mean()), float(train.std(ddof=0))
    if not np.isfinite(std) or std < 1e-8:
        std = 1.0
    z = (train - mean) / std
    xs, ys = [], []
    for i in range(len(z) - window):
        xs.append(z[i:i + window])
        ys.append(z[i + window])
    if not xs:
        raise ValueError("Insufficient history for recurrent model")
    x = torch.tensor(np.asarray(xs), dtype=torch.float32).unsqueeze(-1)
    y = torch.tensor(np.asarray(ys), dtype=torch.float32).unsqueeze(-1)
    torch.manual_seed(seed)
    model = RecurrentForecaster(kind)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=0.01)
    loss_fn = nn.MSELoss()
    model.train()
    for _ in range(200):
        optimizer.zero_grad(set_to_none=True)
        loss = loss_fn(model(x), y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
    model.eval()
    last = torch.tensor(((train[-window:] - mean) / std)[None, :, None], dtype=torch.float32)
    with torch.no_grad():
        pred_z = float(model(last).item())
    return pred_z * std + mean


forecast_rows = []
test_start_year = 2016
log_years = real["nam"].astype(int).to_numpy()
for target_idx, target_year in enumerate(log_years):
    if target_year < test_start_year:
        continue
    train = log_real[:target_idx]
    actual_log = float(log_real[target_idx])
    if len(train) < 10:
        continue
    predictions = {
        "Naive_last_value": float(train[-1]),
        "Drift_mean_log_change": float(train[-1] + np.diff(train).mean()),
        "Linear_log_trend": float(np.polyval(np.polyfit(np.arange(len(train)), train, deg=1), len(train))),
        "GRU_logGDP": neural_predict("GRU", train, SEED + int(target_year)),
        "LSTM_logGDP": neural_predict("LSTM", train, SEED + 1000 + int(target_year)),
    }
    train_real_levels = np.exp(train)
    mase_scale = float(np.abs(np.diff(train_real_levels)).mean())
    for model_name, pred_log in predictions.items():
        forecast_rows.append({
            "nam_du_bao": int(target_year), "mo_hinh": model_name,
            "gdp_thuc_thuc_te_usd_2015": float(np.exp(actual_log)),
            "gdp_thuc_du_bao_usd_2015": float(np.exp(pred_log)),
            "sai_so_usd": float(np.exp(pred_log) - np.exp(actual_log)),
            "sai_so_phan_tram_pct": float((np.exp(pred_log) / np.exp(actual_log) - 1) * 100),
            "so_nam_train": len(train), "cua_so_dau_vao_nam": 5,
            "mase_chia_cho_mae_naive_tren_train_usd_2015": mase_scale,
            "epochs": 200 if model_name.startswith(("GRU", "LSTM")) else "",
            "seed": SEED + int(target_year) + (1000 if model_name.startswith("LSTM") else 0) if model_name.startswith(("GRU", "LSTM")) else "",
            "ghi_chu": "Rolling origin; từng năm dự báo chỉ dùng các năm trước đó; scaler chỉ fit trên train." if model_name.startswith(("GRU", "LSTM")) else "Baseline rolling-origin; chỉ dùng dữ liệu train đến năm trước.",
        })
forecast_df = pd.DataFrame(forecast_rows)
write_csv("du_lieu_du_bao_rolling_origin.csv", forecast_df)
metric_rows = []
for model_name, group in forecast_df.groupby("mo_hinh", sort=False):
    errors = group["gdp_thuc_du_bao_usd_2015"].to_numpy() - group["gdp_thuc_thuc_te_usd_2015"].to_numpy()
    actuals = group["gdp_thuc_thuc_te_usd_2015"].to_numpy()
    mase_by_fold = np.abs(errors) / group["mase_chia_cho_mae_naive_tren_train_usd_2015"].to_numpy()
    metric_rows.append({
        "mo_hinh": model_name, "so_diem_kiem_thu": len(group), "nam_dau": int(group["nam_du_bao"].min()),
        "nam_cuoi": int(group["nam_du_bao"].max()), "MAE_usd_2015": np.abs(errors).mean(),
        "RMSE_usd_2015": np.sqrt(np.mean(errors ** 2)), "MAPE_pct": np.mean(np.abs(errors / actuals)) * 100,
        "sMAPE_pct": np.mean(2 * np.abs(errors) / (np.abs(group["gdp_thuc_du_bao_usd_2015"].to_numpy()) + np.abs(actuals))) * 100,
        "MASE_vs_naive_train": np.mean(mase_by_fold),
        "ghi_chu": "Chỉ 10 dự báo ngoài mẫu; kết quả nhạy với giai đoạn kiểm thử, không đủ mẫu để khẳng định mô hình thắng ổn định." if model_name.startswith(("GRU", "LSTM")) else "Mốc so sánh; dùng chung các năm kiểm thử với GRU/LSTM.",
    })
metrics = pd.DataFrame(metric_rows).sort_values("RMSE_usd_2015")
write_csv("so_sanh_hieu_qua_mo_hinh_du_bao.csv", metrics)

# Multi-step projections from the full observed annual series to 2030. These are
# model scenarios, not official GDP estimates or prediction intervals.
def neural_recursive_path(kind: str, observed: np.ndarray, seed: int,
                          steps: int = 5, window: int = 5) -> np.ndarray:
    mean, std = float(observed.mean()), float(observed.std(ddof=0))
    if not np.isfinite(std) or std < 1e-8:
        std = 1.0
    z = (observed - mean) / std
    xs, ys = [], []
    for i in range(len(z) - window):
        xs.append(z[i:i + window])
        ys.append(z[i + window])
    x = torch.tensor(np.asarray(xs), dtype=torch.float32).unsqueeze(-1)
    y = torch.tensor(np.asarray(ys), dtype=torch.float32).unsqueeze(-1)
    torch.manual_seed(seed)
    model = RecurrentForecaster(kind)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=0.01)
    loss_fn = nn.MSELoss()
    model.train()
    for _ in range(200):
        optimizer.zero_grad(set_to_none=True)
        loss = loss_fn(model(x), y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
    history_z = list(z)
    predictions = []
    model.eval()
    for _ in range(steps):
        last = torch.tensor(np.asarray(history_z[-window:])[None, :, None], dtype=torch.float32)
        with torch.no_grad():
            pred_z = float(model(last).item())
        history_z.append(pred_z)
        predictions.append(pred_z * std + mean)
    return np.asarray(predictions)


def forecast_metrics_by_horizon(backtest: pd.DataFrame) -> pd.DataFrame:
    metric_rows = []
    for (horizon, model_name), group in backtest.groupby(["chan_troi_nam", "mo_hinh"], sort=True):
        errors = group["gdp_thuc_du_bao_usd_2015"].to_numpy() - group["gdp_thuc_thuc_te_usd_2015"].to_numpy()
        actuals = group["gdp_thuc_thuc_te_usd_2015"].to_numpy()
        metric_rows.append({
            "chan_troi_nam": int(horizon), "mo_hinh": model_name, "so_diem_kiem_thu": len(group),
            "nam_dau": int(group["nam_du_bao"].min()), "nam_cuoi": int(group["nam_du_bao"].max()),
            "MAE_usd_2015": float(np.mean(np.abs(errors))), "RMSE_usd_2015": float(np.sqrt(np.mean(errors ** 2))),
            "MAPE_pct": float(np.mean(np.abs(errors / actuals)) * 100),
            "sMAPE_pct": float(np.mean(2 * np.abs(errors) / (np.abs(group["gdp_thuc_du_bao_usd_2015"].to_numpy()) + np.abs(actuals))) * 100),
            "MASE_vs_naive_train": float(np.mean(np.abs(errors) / group["mase_chia_cho_mae_naive_train_usd_2015"].to_numpy())),
            "ghi_chu": "Expanding-window; chỉ dùng lịch sử có trước năm gốc. Cỡ mẫu giảm khi chân trời dài hơn.",
        })
    return pd.DataFrame(metric_rows).sort_values(["chan_troi_nam", "RMSE_usd_2015"])


observed_log = np.log(real["gdp_thuc_usd_2015"].to_numpy(dtype=float))
log_years = real["nam"].astype(int).to_numpy()
test_start_idx = int(np.where(log_years >= test_start_year)[0][0])
multi_horizon_rows = []
# Reuse the established one-step rolling-origin forecasts for horizon 1.
for r in forecast_df.itertuples(index=False):
    multi_horizon_rows.append({
        "nam_du_bao": int(r.nam_du_bao), "nam_goc": int(r.nam_du_bao) - 1,
        "chan_troi_nam": 1, "mo_hinh": str(r.mo_hinh),
        "gdp_thuc_thuc_te_usd_2015": float(r.gdp_thuc_thuc_te_usd_2015),
        "gdp_thuc_du_bao_usd_2015": float(r.gdp_thuc_du_bao_usd_2015),
        "sai_so_usd": float(r.sai_so_usd), "sai_so_log": float(np.log(r.gdp_thuc_du_bao_usd_2015) - np.log(r.gdp_thuc_thuc_te_usd_2015)),
        "so_nam_train": int(r.so_nam_train),
        "mase_chia_cho_mae_naive_train_usd_2015": float(r.mase_chia_cho_mae_naive_tren_train_usd_2015),
    })

# Refit only once at each historical forecast origin, then recursively forecast
# horizons 2-5. Horizon samples are necessarily shorter for longer lead times.
for origin_idx in range(test_start_idx, len(log_years) - 1):
    train = log_real[:origin_idx]
    max_h = min(5, len(log_years) - origin_idx)
    if len(train) < 10 or max_h < 2:
        continue
    log_path = {
        "Naive_last_value": np.repeat(train[-1], max_h),
        "Drift_mean_log_change": train[-1] + np.diff(train).mean() * np.arange(1, max_h + 1),
        "Linear_log_trend": np.polyval(np.polyfit(np.arange(len(train)), train, deg=1), np.arange(len(train), len(train) + max_h)),
        "GRU_logGDP": neural_recursive_path("GRU", train, SEED + int(log_years[origin_idx]), max_h),
        "LSTM_logGDP": neural_recursive_path("LSTM", train, SEED + 1000 + int(log_years[origin_idx]), max_h),
    }
    scale = float(np.abs(np.diff(np.exp(train))).mean())
    for horizon in range(2, max_h + 1):
        target_idx = origin_idx + horizon - 1
        actual = float(np.exp(log_real[target_idx]))
        for model_name, path in log_path.items():
            prediction = float(np.exp(path[horizon - 1]))
            multi_horizon_rows.append({
                "nam_du_bao": int(log_years[target_idx]), "nam_goc": int(log_years[origin_idx] - 1),
                "chan_troi_nam": horizon, "mo_hinh": model_name,
                "gdp_thuc_thuc_te_usd_2015": actual, "gdp_thuc_du_bao_usd_2015": prediction,
                "sai_so_usd": prediction - actual, "sai_so_log": float(path[horizon - 1] - log_real[target_idx]),
                "so_nam_train": len(train), "mase_chia_cho_mae_naive_train_usd_2015": scale,
            })
multi_horizon = pd.DataFrame(multi_horizon_rows).sort_values(["chan_troi_nam", "nam_du_bao", "mo_hinh"])
write_csv("du_lieu_du_bao_nhieu_chan_troi.csv", multi_horizon)
horizon_metrics = forecast_metrics_by_horizon(multi_horizon)
write_csv("so_sanh_hieu_qua_mo_hinh_theo_chan_troi.csv", horizon_metrics)

forecast_horizon = 5
years_future = np.arange(int(real["nam"].max()) + 1, int(real["nam"].max()) + forecast_horizon + 1)
drift = float(np.diff(observed_log).mean())
trend_coef = np.polyfit(np.arange(len(observed_log)), observed_log, deg=1)
future_log = {
    "Naive_last_value": np.repeat(observed_log[-1], forecast_horizon),
    "Drift_mean_log_change": observed_log[-1] + drift * np.arange(1, forecast_horizon + 1),
    "Linear_log_trend": np.polyval(trend_coef, np.arange(len(observed_log), len(observed_log) + forecast_horizon)),
    "GRU_logGDP": neural_recursive_path("GRU", observed_log, SEED + 2030, forecast_horizon),
    "LSTM_logGDP": neural_recursive_path("LSTM", observed_log, SEED + 3030, forecast_horizon),
}
forecast_2030_rows = []
for model_name, values in future_log.items():
    for year, value in zip(years_future, values):
        horizon = int(year - int(real["nam"].max()))
        calibration = multi_horizon[(multi_horizon["chan_troi_nam"].eq(horizon)) & multi_horizon["mo_hinh"].eq(model_name)]
        abs_log_errors = np.sort(np.abs(calibration["sai_so_log"].to_numpy(dtype=float)))
        rank = min(len(abs_log_errors), int(np.ceil((len(abs_log_errors) + 1) * 0.80)))
        q80 = float(abs_log_errors[max(0, rank - 1)])
        forecast_2030_rows.append({
            "nam_du_bao": int(year), "mo_hinh": model_name,
            "gdp_thuc_du_bao_usd_2015": float(np.exp(value)),
            "can_duoi_80_kinh_nghiem_usd_2015": float(np.exp(value - q80)),
            "can_tren_80_kinh_nghiem_usd_2015": float(np.exp(value + q80)),
            "chan_troi_nam": horizon, "so_mau_hieu_chuan": int(len(abs_log_errors)),
            "phuong_phap_khoang": "P80 sai số tuyệt đối log GDP từ backtest rolling-origin cùng chân trời; dải thực nghiệm, không bảo đảm coverage.",
            "don_vi": "USD cố định 2015", "phan_loai": "du_bao_ngoai_mau",
            "ghi_chu": "Dự báo mô hình từ chuỗi GDP thực năm quan sát đến 2025; không phải số liệu chính thức. GRU/LSTM dùng dự báo đệ quy 5 bước, scaler fit trên toàn bộ chuỗi train.",
        })
forecast_2030 = pd.DataFrame(forecast_2030_rows)
write_csv("du_lieu_du_bao_gdp_thuc_den_2030.csv", forecast_2030)

# Comparison-ready retail 2026 and trade 2026 changes, with source-frequency labels.
retail26 = read_csv("du_lieu_ban_le_tieu_dung_thang_2026.csv")
retail26["thoi_gian"] = pd.to_datetime(retail26["thoi_gian"], errors="coerce")
retail26["tong_muc_ban_le_vnd"] = numcol(retail26, "tong_muc_ban_le_vnd")
retail26["tang_truong_danh_nghia_mom_tinh_tu_muc"] = retail26["tong_muc_ban_le_vnd"].pct_change() * 100
retail26["ghi_chu_so_sanh"] = "Tăng trưởng thực do NSO công bố là lũy kế theo kỳ, không phải tăng trưởng thực riêng tháng."
write_csv("du_lieu_so_sanh_ban_le_thang_2026.csv", retail26)
trade26 = read_csv("du_lieu_xuat_nhap_khau_thang_2026.csv")
trade26["thoi_gian"] = pd.to_datetime(trade26["thoi_gian"], errors="coerce")
for c in ["kim_ngach_xuat_khau_usd", "kim_ngach_nhap_khau_usd", "can_can_thuong_mai_usd"]:
    trade26[c] = numcol(trade26, c)
trade26["tang_truong_xuat_khau_mom_pct"] = trade26["kim_ngach_xuat_khau_usd"].pct_change() * 100
trade26["tang_truong_nhap_khau_mom_pct"] = trade26["kim_ngach_nhap_khau_usd"].pct_change() * 100
trade26["ghi_chu_so_sanh"] = "Số liệu tháng 2026 sơ bộ; chưa tính tăng trưởng cùng kỳ do tệp nguồn tải được chỉ cung cấp bảng 2026 này."
write_csv("du_lieu_so_sanh_ngoai_thuong_thang_2026.csv", trade26)

# Compact, reproducible quality checks for the refreshed files and analysis outputs.
quality_rows = []
def quality(file_name: str, frame: pd.DataFrame, key_cols: list[str], expected: int | None, note: str) -> None:
    duplicate_rows = int(frame.duplicated(key_cols).sum()) if key_cols else 0
    missing_key_values = int(frame[key_cols].isna().sum().sum()) if key_cols else 0
    quality_rows.append({
        "tep": file_name, "so_dong_du_lieu": len(frame), "so_dong_trung_khoa": duplicate_rows,
        "so_o_thieu_tren_khoa": missing_key_values,
        "so_o_thieu": int(frame.isna().sum().sum()), "so_dong_ky_vong": expected if expected is not None else "",
        "ket_qua": "dat" if duplicate_rows == 0 and missing_key_values == 0 and (expected is None or len(frame) == expected) else "can_xem_lai",
        "ghi_chu": note,
    })


def domain_check(name: str, passed: bool, observed: int, expected: int, note: str) -> None:
    quality_rows.append({
        "tep": name, "so_dong_du_lieu": int(observed), "so_dong_trung_khoa": 0,
        "so_o_thieu_tren_khoa": 0, "so_o_thieu": 0, "so_dong_ky_vong": int(expected),
        "ket_qua": "dat" if passed else "can_xem_lai", "ghi_chu": note,
    })

quality("du_lieu_gdp_tong_hop.csv", gdp, ["nam"], 41, "GDP năm 1985-2025; quan sát annual.")
quality("du_lieu_ty_gia_usd_vnd.csv", fx, ["thoi_gian"], 513, "Tỷ giá tháng IMF đến 2026-07; không nội suy các tháng sau.")
quality("du_lieu_cpi_phan_tich_thang.csv", cpi, ["thoi_gian"], 81, "CPI 2020-01..2026-09; 2026 được gắn cờ tái tạo từ tỷ lệ lũy kế đã làm tròn.")
quality("du_lieu_xuat_nhap_khau_thang_2026.csv", trade26, ["thoi_gian"], 9, "NSO sơ bộ Jan-Sep 2026; USD chuyển đổi từ 1000 USD.")
quality("du_lieu_san_xuat_iip_thang_2026.csv", read_csv("du_lieu_san_xuat_iip_thang_2026.csv"), ["thoi_gian"], 9, "IIP 2015=100; chỉ Sep có tỷ lệ MoM/YoY trong bảng nguồn.")
quality("du_lieu_grdp_63_tinh_thanh.csv", grdp, ["ten_tinh", "nam", "loai_dia_ban"], 552, "63 tỉnh cũ + 6 vùng thống kê, 2018-2025; vùng không cộng cùng tỉnh.")
quality("du_lieu_ban_le_tieu_dung.csv", retail, ["nam"], 36, "Chuỗi bán lẻ năm 1990-2025; giá trị danh nghĩa theo nguồn NSO.")
quality("du_lieu_ban_le_tieu_dung_thang_2026.csv", retail26, ["thoi_gian"], 9, "Bán lẻ tháng 2026-01..09; tăng trưởng thực được công bố theo lũy kế kỳ.")
quality("du_lieu_fdi_dau_tu.csv", fdi, ["nam"], 35, "Chuỗi năm bắt đầu 1991; số liệu 1988-1990 gộp riêng.")
quality("du_lieu_fdi_luy_ke_2026.csv", read_csv("du_lieu_fdi_luy_ke_2026.csv"), ["thoi_gian"], 1, "FDI lũy kế 9 tháng 2026; phạm vi đăng ký khác vốn dự án cấp phép năm.")
quality("du_lieu_chi_so_kinh_te_hang_nam.csv", read_csv("du_lieu_chi_so_kinh_te_hang_nam.csv"), ["nam"], 41, "Bảng năm hợp nhất GDP, thương mại, CPI, bán lẻ, FDI và các tỷ lệ vĩ mô.")
quality("du_lieu_so_sanh_nganh_2025.csv", read_csv("du_lieu_so_sanh_nganh_2025.csv"), ["nhom_nganh"], 4, "So sánh 2024-2025 gồm ba khu vực kinh tế và thuế sản phẩm ròng.")
quality("du_lieu_du_bao_rolling_origin.csv", forecast_df, ["nam_du_bao", "mo_hinh"], 50, "5 mô hình x 10 năm kiểm thử 2016-2025; expanding-window.")
quality("so_sanh_hieu_qua_mo_hinh_du_bao.csv", metrics, ["mo_hinh"], 5, "Cùng cửa sổ kiểm thử; bao gồm baseline Naive/Drift/linear và GRU/LSTM.")
quality("du_lieu_du_bao_gdp_thuc_den_2030.csv", forecast_2030, ["nam_du_bao", "mo_hinh"], 25, "5 mô hình x 5 năm dự báo ngoài mẫu 2026-2030; không phải số liệu chính thức.")
quality("du_lieu_du_bao_nhieu_chan_troi.csv", multi_horizon, ["nam_goc", "chan_troi_nam", "mo_hinh"], 200, "Expanding-window backtest 1-5 năm; cùng gốc dự báo dùng cho từng chân trời khả dụng.")
quality("so_sanh_hieu_qua_mo_hinh_theo_chan_troi.csv", horizon_metrics, ["chan_troi_nam", "mo_hinh"], 25, "5 mô hình được so sánh riêng cho từng chân trời 1-5 năm; mẫu kiểm thử nhỏ hơn ở chân trời dài.")
province_coverage = province.groupby("nam")["ten_tinh"].nunique()
region_coverage = grdp[grdp["loai_dia_ban"].eq("vung_thong_ke")].groupby("nam")["ten_vung_kinh_te"].nunique()
domain_check("CHECK_gdp_years_contiguous_positive", bool(np.array_equal(real["nam"].astype(int).to_numpy(), np.arange(1985, 2026)) and (real["gdp_thuc_usd_2015"] > 0).all()), len(real), 41, "GDP thực quan sát liên tục 1985–2025 và dương ở mọi năm.")
domain_check("CHECK_grdp_63_provinces_each_year", bool(len(province_coverage) == 8 and province_coverage.eq(63).all()), int(province_coverage.sum()), 504, "Mỗi năm 2018–2025 có đủ 63 tỉnh/thành theo phạm vi dữ liệu truyền thống.")
domain_check("CHECK_grdp_6_regions_each_year", bool(len(region_coverage) == 8 and region_coverage.eq(6).all()), int(region_coverage.sum()), 48, "Mỗi năm 2018–2025 có đủ sáu vùng thống kê.")
domain_check("CHECK_forecast_2030_positive_complete", bool(set(forecast_2030["nam_du_bao"].astype(int)) == set(range(2026, 2031)) and len(forecast_2030) == 25 and np.isfinite(forecast_2030["gdp_thuc_du_bao_usd_2015"]).all() and (forecast_2030["gdp_thuc_du_bao_usd_2015"] > 0).all()), len(forecast_2030), 25, "5 mô hình × 5 năm 2026–2030; dự báo mức GDP thực hữu hạn và dương.")
expected_horizon_rows = sum((10 - horizon + 1) * 5 for horizon in range(1, 6))
domain_check("CHECK_backtest_horizons_1_to_5", bool(set(multi_horizon["chan_troi_nam"].astype(int)) == set(range(1, 6)) and len(multi_horizon) == expected_horizon_rows), len(multi_horizon), expected_horizon_rows, "Mỗi chân trời 1–5 năm có đầy đủ 5 mô hình và số điểm giảm đúng theo chiều dài chân trời.")
write_csv("kiem_tra_chat_luong_du_lieu.csv", pd.DataFrame(quality_rows))
if any(row["ket_qua"] != "dat" for row in quality_rows):
    raise ValueError("At least one data quality check did not pass; inspect kiem_tra_chat_luong_du_lieu.csv")

analysis_manifest = {
    "analysis_date": "2026-10-23",
    "forecast_target": "World Bank annual real GDP, constant 2015 USD, 1985-2025",
    "forecast_evaluation": {
        "method": "expanding-window rolling-origin one-step-ahead",
        "test_years": "2016-2025", "scaler": "fit on each training fold only",
        "models": ["Naive_last_value", "Drift_mean_log_change", "Linear_log_trend", "GRU_logGDP", "LSTM_logGDP"],
        "gru_lstm": "sequence=5 years, hidden=8, epochs=200, fixed seed per origin; exploratory due short annual series",
    },
    "forecast_projection": {
        "file": "du_lieu_du_bao_gdp_thuc_den_2030.csv",
        "years": "2026-2030",
        "models": ["Naive_last_value", "Drift_mean_log_change", "Linear_log_trend", "GRU_logGDP", "LSTM_logGDP"],
        "target": "annual real GDP, constant 2015 USD",
        "interpretation": "Out-of-sample model projections based on observations through 2025; not official estimates. The displayed empirical P80 bands use absolute log errors from rolling-origin backtests at the matching horizon; time-series errors are dependent and small samples do not guarantee nominal coverage. Neural models use recursive five-step forecasts and are exploratory.",
    },
    "multi_horizon_backtest": {
        "file": "du_lieu_du_bao_nhieu_chan_troi.csv",
        "horizons_years": [1, 2, 3, 4, 5],
        "method": "expanding-window rolling-origin; baselines forecast in log GDP; GRU/LSTM use recursive multi-step forecasts",
        "metric_file": "so_sanh_hieu_qua_mo_hinh_theo_chan_troi.csv",
        "sample_counts_per_model": {"1": 10, "2": 9, "3": 8, "4": 7, "5": 6},
    },
    "time_series_methods": {
        "adf": "ADF with AIC lag selection; trend+constant for log level, constant for log difference",
        "decomposition": "HP filter on log annual real GDP, lambda=6.25; not an official potential GDP estimate",
        "fx_volatility": "12-month rolling sample standard deviation of monthly log returns, annualized by sqrt(12)",
    },
    "comparisons": [
        "annual macro indicators and ratios", "GDP sector composition", "province and region GRDP rankings",
        "CPI and FX monthly comparison", "annual IIP/GDP contemporaneous and lagged correlation",
        "annual and monthly trade comparisons", "rolling-origin forecast model comparison",
    ],
    "quality_check_file": "kiem_tra_chat_luong_du_lieu.csv",
}
with (ROOT / "analysis_manifest.json").open("w", encoding="utf-8") as f:
    import json
    json.dump(analysis_manifest, f, ensure_ascii=False, indent=2)

print(f"Annual panel={len(panel)} years, CPI={len(cpi)} months, FX={len(fx)} months, GRDP 2025 provinces={len(prov25)}, regions={len(regions25)}")
print("ADF:", [(r["chuoi"], round(r["p_value"], 6)) for r in adf_rows])
print("Forecast leaderboard:", metrics[["mo_hinh", "RMSE_usd_2015", "MAPE_pct"]].to_dict("records"))
print("Horizon backtest metrics written for horizons 1-5; see so_sanh_hieu_qua_mo_hinh_theo_chan_troi.csv")
from snapshot_data import main as create_data_snapshot
create_data_snapshot()
