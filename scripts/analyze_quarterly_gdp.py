"""Backtest simple seasonal models on observed quarterly real GDP levels.

The target is the NSDP series at constant 2010 prices (2010-Q1–2025-Q4).
No monthly spline values or constant-2020-price observations are mixed into it.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from statsmodels.tsa.holtwinters import ExponentialSmoothing

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_paths import data_path

MIN_TRAIN_QUARTERS = 32
EVALUATION_HORIZONS = (1, 4, 8, 12, 20)
MODEL_NOTES = {
    "SeasonalNaive": "Lặp lại mức của cùng quý năm trước.",
    "SeasonalDrift": "Seasonal naive cộng mức tăng log cùng quý bình quân 5 năm gần nhất.",
    "LogTrendQuarterDummies": "OLS log GDP theo xu hướng tuyến tính và biến giả quý; fit lại từng origin.",
    "ETS_DampedAdditive": "ETS trên log GDP; xu hướng cộng có giảm tốc, mùa vụ cộng chu kỳ 4 quý.",
}


def seasonal_naive_path(log_train: np.ndarray, steps: int) -> np.ndarray:
    return np.asarray([log_train[-4 + ((h - 1) % 4)] for h in range(1, steps + 1)])


def seasonal_drift_path(log_train: np.ndarray, steps: int) -> np.ndarray:
    year_changes = log_train[4:] - log_train[:-4]
    growth = float(np.mean(year_changes[-min(20, len(year_changes)):]))
    return np.asarray([
        log_train[-4 + ((h - 1) % 4)] + growth * ((h + 3) // 4)
        for h in range(1, steps + 1)
    ])


def trend_seasonal_path(log_train: np.ndarray, last_period: pd.Period,
                        steps: int) -> np.ndarray:
    n = len(log_train)
    t = (np.arange(n, dtype=float) - (n - 1) / 2) / 4
    quarters = np.asarray([((last_period - (n - 1 - i)).quarter) for i in range(n)])
    # The source period is regular quarterly data. Build quarter dummies for Q2–Q4;
    # Q1 is the reference season to avoid a rank-deficient design matrix.
    design = np.column_stack([np.ones(n), t, *(quarters == q for q in (2, 3, 4))]).astype(float)
    coefficients, *_ = np.linalg.lstsq(design, log_train, rcond=None)
    future_periods = [last_period + h for h in range(1, steps + 1)]
    t_future = (np.arange(n, n + steps, dtype=float) - (n - 1) / 2) / 4
    future_quarters = np.asarray([period.quarter for period in future_periods])
    future_design = np.column_stack([np.ones(steps), t_future,
                                     *(future_quarters == q for q in (2, 3, 4))]).astype(float)
    return future_design @ coefficients


def ets_path(log_train: np.ndarray, steps: int) -> np.ndarray:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fit = ExponentialSmoothing(
            log_train,
            trend="add",
            damped_trend=True,
            seasonal="add",
            seasonal_periods=4,
            initialization_method="estimated",
        ).fit(optimized=True, use_brute=False)
    return np.asarray(fit.forecast(steps), dtype=float)


def forecast_path(log_train: np.ndarray, last_period: pd.Period, steps: int) -> dict[str, np.ndarray]:
    predictions = {
        "SeasonalNaive": seasonal_naive_path(log_train, steps),
        "SeasonalDrift": seasonal_drift_path(log_train, steps),
        "LogTrendQuarterDummies": trend_seasonal_path(log_train, last_period, steps),
    }
    predictions["ETS_DampedAdditive"] = ets_path(log_train, steps)
    return predictions


def main() -> None:
    frame = pd.read_csv(data_path("du_lieu_gdp_quy_muc_thuc_gia_2010.csv"), encoding="utf-8-sig")
    frame["gdp_thuc_ty_vnd_gia_2010"] = pd.to_numeric(frame["gdp_thuc_ty_vnd_gia_2010"], errors="coerce")
    periods = pd.PeriodIndex([f"{int(y)}Q{int(q)}" for y, q in zip(frame["nam"], frame["quy"])], freq="Q")
    values = frame["gdp_thuc_ty_vnd_gia_2010"].to_numpy(dtype=float)
    if len(frame) <= MIN_TRAIN_QUARTERS or np.any(~np.isfinite(values)) or np.any(values <= 0):
        raise RuntimeError("Chuỗi GDP quý không đủ độ dài hoặc có mức GDP không hợp lệ")
    expected_periods = pd.period_range(periods[0], periods[-1], freq="Q")
    if not periods.equals(expected_periods):
        raise RuntimeError("Chuỗi GDP quý có kỳ bị thiếu hoặc không liên tục")

    log_values = np.log(values)
    rows = []
    for origin_index in range(MIN_TRAIN_QUARTERS, len(frame)):
        train = log_values[:origin_index]
        origin_period = periods[origin_index - 1]
        max_horizon = min(20, len(frame) - origin_index)
        predictions = forecast_path(train, origin_period, max_horizon)
        seasonal_scale = float(np.mean(np.abs(np.exp(train[4:]) - np.exp(train[:-4]))))
        for horizon in EVALUATION_HORIZONS:
            if horizon > max_horizon:
                continue
            target_index = origin_index + horizon - 1
            target_period = periods[target_index]
            actual = values[target_index]
            for model, path in predictions.items():
                predicted = float(np.exp(path[horizon - 1]))
                rows.append({
                    "ky_du_bao": str(target_period),
                    "ky_goc_du_bao": str(origin_period),
                    "chan_troi_quy": horizon,
                    "chan_troi_nam": horizon / 4,
                    "mo_hinh": model,
                    "gdp_thuc_thuc_te_ty_vnd_gia_2010": actual,
                    "gdp_thuc_du_bao_ty_vnd_gia_2010": predicted,
                    "sai_so_ty_vnd": predicted - actual,
                    "sai_so_pct": (predicted / actual - 1) * 100,
                    "so_quy_huan_luyen": origin_index,
                    "mase_chia_cho_sai_so_mua_vu_train_ty_vnd": seasonal_scale,
                    "phuong_phap": MODEL_NOTES[model],
                    "ghi_chu": "Backtest rolling-origin mở rộng; chỉ dùng dữ liệu đến quý gốc. GDP quý nguồn giá 2010, không ghép chuỗi giá 2020.",
                })

    backtest = pd.DataFrame(rows).sort_values(["chan_troi_quy", "ky_goc_du_bao", "mo_hinh"])
    if backtest.empty:
        raise RuntimeError("Không tạo được dự báo kiểm thử GDP quý")
    backtest_path = data_path("du_lieu_du_bao_gdp_quy_backtest.csv", for_write=True)
    backtest.to_csv(backtest_path, index=False, encoding="utf-8-sig", float_format="%.8f")

    metric_rows = []
    for (horizon, model), group in backtest.groupby(["chan_troi_quy", "mo_hinh"], sort=True):
        actual = group["gdp_thuc_thuc_te_ty_vnd_gia_2010"].to_numpy(dtype=float)
        predicted = group["gdp_thuc_du_bao_ty_vnd_gia_2010"].to_numpy(dtype=float)
        errors = predicted - actual
        metric_rows.append({
            "chan_troi_quy": int(horizon),
            "chan_troi_nam": float(horizon) / 4,
            "mo_hinh": model,
            "so_diem_kiem_thu": int(len(group)),
            "ky_dau": str(group["ky_du_bao"].min()),
            "ky_cuoi": str(group["ky_du_bao"].max()),
            "MAE_ty_vnd": float(np.mean(np.abs(errors))),
            "RMSE_ty_vnd": float(np.sqrt(np.mean(errors ** 2))),
            "MAPE_pct": float(np.mean(np.abs(errors / actual)) * 100),
            "MASE_mua_vu": float(np.mean(np.abs(errors) / group["mase_chia_cho_sai_so_mua_vu_train_ty_vnd"].to_numpy(dtype=float))),
            "ghi_chu": "Các origin có cửa sổ kiểm thử chồng lấp; điểm kiểm thử không độc lập. Không suy rộng thành bảo đảm xác suất.",
        })
    metrics = pd.DataFrame(metric_rows).sort_values(["chan_troi_quy", "MAPE_pct"])
    metrics_path = data_path("so_sanh_hieu_qua_mo_hinh_gdp_quy.csv", for_write=True)
    metrics.to_csv(metrics_path, index=False, encoding="utf-8-sig", float_format="%.8f")

    reconciliation = pd.read_csv(data_path("doi_chieu_gdp_thuc_quy_va_nam.csv"), encoding="utf-8-sig")
    quality_path = data_path("kiem_tra_chat_luong_du_lieu.csv")
    quality = pd.read_csv(quality_path, encoding="utf-8-sig")

    def quality_record(name: str, dataset: pd.DataFrame, keys: list[str], expected: int,
                       note: str, domain_ok: bool = True) -> dict:
        duplicates = int(dataset.duplicated(keys).sum())
        missing_key = int(dataset[keys].isna().sum().sum())
        missing = int(dataset.isna().sum().sum())
        passed = len(dataset) == expected and duplicates == 0 and missing_key == 0 and domain_ok
        return {
            "tep": name,
            "so_dong_du_lieu": int(len(dataset)),
            "so_dong_trung_khoa": duplicates,
            "so_o_thieu_tren_khoa": missing_key,
            "so_o_thieu": missing,
            "so_dong_ky_vong": expected,
            "ket_qua": "dat" if passed else "can_xem_xet",
            "ghi_chu": note,
        }

    quarterly_raw = pd.read_csv(data_path("du_lieu_gdp_quy_muc_thuc_gia_2010.csv"), encoding="utf-8-sig")
    quarterly_new_base = pd.read_csv(data_path("du_lieu_gdp_quy_muc_thuc_gia_2020.csv"), encoding="utf-8-sig")
    checks = [
        quality_record("du_lieu_gdp_quy_muc_thuc_gia_2010.csv", quarterly_raw, ["thoi_gian"], 64,
                       "GDP thực quan sát theo quý, 2010-Q1–2025-Q4, giá so sánh 2010."),
        quality_record("du_lieu_gdp_quy_muc_thuc_gia_2020.csv", quarterly_new_base, ["thoi_gian"], 6,
                       "Chuỗi mới giá 2020 riêng: 2025-Q1–Q3 và 2026-Q1–Q3; không ghép giá 2010."),
        quality_record("doi_chieu_gdp_thuc_quy_va_nam.csv", reconciliation, ["nam"], 16,
                       "Tổng bốn quý so với GDP năm cùng nguồn; sai số tuyệt đối tối đa dưới 0,01%.",
                       bool(pd.to_numeric(reconciliation["chenh_lech_pct"], errors="coerce").abs().le(0.01).all())),
        quality_record("du_lieu_du_bao_gdp_quy_backtest.csv", backtest,
                       ["ky_goc_du_bao", "chan_troi_quy", "mo_hinh"], 480,
                       "Expanding-window rolling-origin; có 4 mô hình ở 5 chân trời, origin chồng lấp."),
        quality_record("so_sanh_hieu_qua_mo_hinh_gdp_quy.csv", metrics,
                       ["chan_troi_quy", "mo_hinh"], 20,
                       "MAPE/RMSE/MASE mùa vụ tính riêng từng chân trời và mô hình."),
    ]
    quality = quality[~quality["tep"].isin([row["tep"] for row in checks])]
    quality = pd.concat([quality, pd.DataFrame(checks)], ignore_index=True)
    quality.to_csv(quality_path, index=False, encoding="utf-8-sig")

    manifest = {
        "target": "Observed quarterly real GDP level, constant 2010 prices, billion VND",
        "source_file": "data/nso/processed/du_lieu_gdp_quy_muc_thuc_gia_2010.csv",
        "period": {"start": str(periods[0]), "end": str(periods[-1]), "observations": int(len(periods))},
        "minimum_training_quarters": MIN_TRAIN_QUARTERS,
        "horizons_quarters": list(EVALUATION_HORIZONS),
        "models": [
            {"name": model, "description": description}
            for model, description in MODEL_NOTES.items()
        ],
        "evaluation": "Expanding-window rolling-origin; each model is refit at each origin; no random split; all transformations use only each fold's training history.",
        "caveats": [
            "Quarterly level series is available at constant 2010 prices through 2025-Q4. The newer 2020-price series is kept separate.",
            "The sample is larger than the annual series but the origins overlap, so forecast errors are dependent.",
            "This quarterly branch supplements but does not replace the annual GDP USD 2015 forecast to 2030.",
            "Seasonal naive and ETS are exploratory forecasting baselines; model selection must use the displayed out-of-sample metrics.",
        ],
        "outputs": [
            "data/derived/forecast/du_lieu_du_bao_gdp_quy_backtest.csv",
            "data/derived/forecast/so_sanh_hieu_qua_mo_hinh_gdp_quy.csv",
        ],
    }
    data_path("manifest_phan_tich_gdp_quy.json", for_write=True).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    analysis_manifest_path = ROOT / "analysis_manifest.json"
    analysis_manifest = json.loads(analysis_manifest_path.read_text(encoding="utf-8")) if analysis_manifest_path.exists() else {}
    analysis_manifest["analysis_date"] = datetime.now(timezone.utc).date().isoformat()
    analysis_manifest["quarterly_real_gdp_evaluation"] = {
        "source": "NSDP / National Summary Data Page of Vietnam Statistics Office",
        "source_file": "data/nso/processed/du_lieu_gdp_quy_muc_thuc_gia_2010.csv",
        "target": "Quarterly observed real GDP level, constant 2010 prices, billion VND",
        "period": f"{periods[0]}–{periods[-1]}",
        "observations": int(len(periods)),
        "minimum_training_quarters": MIN_TRAIN_QUARTERS,
        "horizons_quarters": list(EVALUATION_HORIZONS),
        "sample_counts_per_model": {
            str(int(row.chan_troi_quy)): int(row.so_diem_kiem_thu)
            for row in metrics.drop_duplicates("chan_troi_quy").itertuples(index=False)
        },
        "models": list(MODEL_NOTES),
        "method": "Expanding-window rolling-origin; each model is refit at each origin. Origins overlap and errors are dependent.",
        "separate_price_base_series": "2025-Q1–2025-Q3 and 2026-Q1–2026-Q3 at constant 2020 prices; stored separately and not spliced into the constant-2010 series.",
        "outputs": [
            "data/derived/forecast/du_lieu_du_bao_gdp_quy_backtest.csv",
            "data/derived/forecast/so_sanh_hieu_qua_mo_hinh_gdp_quy.csv",
        ],
    }
    analysis_manifest_path.write_text(json.dumps(analysis_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Quarterly GDP backtest: {len(backtest)} rows; {len(metrics)} model/horizon results")
    print(metrics[["chan_troi_quy", "mo_hinh", "so_diem_kiem_thu", "MAPE_pct", "RMSE_ty_vnd"]].to_string(index=False))


if __name__ == "__main__":
    main()
