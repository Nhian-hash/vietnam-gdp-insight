"""Precompute annual GDP cutoff backtests for the V-MEST Model Arena.

All transforms are fitted on each cutoff's training window only. The script is
intended for local/offline execution; Render serves the resulting JSON artifact
and never imports PyTorch or retrains models during an HTTP request.
"""
from __future__ import annotations

import json
import math
import random
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from statsmodels.tsa.statespace.sarimax import SARIMAX
from torch import nn

ROOT = Path(__file__).resolve().parents[1]
SOURCE_FILE = ROOT / "data" / "world_bank" / "processed" / "du_lieu_gdp_thuc_va_tang_truong.csv"
OUTPUT_FILE = ROOT / "data" / "derived" / "forecast" / "backtest_arena.json"
SEED = 20261122
MIN_TRAIN_YEARS = 20
WINDOW = 5
HIDDEN_SIZE = 8
EPOCHS = 200
MAX_HORIZON = 5

CUTOFFS = [
    {"key": "2008", "event": "Khủng hoảng tài chính toàn cầu"},
    {"key": "2019", "event": "Trước cú sốc COVID-19"},
    {"key": "2021", "event": "Giai đoạn phục hồi sau đại dịch"},
    {"key": "LATEST", "event": "Dự báo tương lai trên toàn bộ dữ liệu hiện có"},
]


class RecurrentForecaster(nn.Module):
    """Small, fixed-size one-step network; GRU/LSTM are assessed cautiously."""

    def __init__(self, kind: str) -> None:
        super().__init__()
        recurrent = nn.GRU if kind == "GRU" else nn.LSTM
        self.rnn = recurrent(input_size=1, hidden_size=HIDDEN_SIZE, batch_first=True)
        self.head = nn.Linear(HIDDEN_SIZE, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        output, _ = self.rnn(x)
        return self.head(output[:, -1, :])


def neural_path(kind: str, train_log: np.ndarray, steps: int, seed: int) -> np.ndarray:
    """Fit scaling on this cutoff only, then recursively forecast log GDP."""
    mean = float(train_log.mean())
    std = float(train_log.std(ddof=0))
    if not np.isfinite(std) or std < 1e-8:
        std = 1.0
    scaled = (train_log - mean) / std
    x_rows, y_rows = [], []
    for index in range(len(scaled) - WINDOW):
        x_rows.append(scaled[index:index + WINDOW])
        y_rows.append(scaled[index + WINDOW])
    if not x_rows:
        raise ValueError(f"{kind}: insufficient history for a {WINDOW}-year input window")

    # Fix random states per model and cutoff so the offline artifact is reproducible.
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    x = torch.tensor(np.asarray(x_rows), dtype=torch.float32).unsqueeze(-1)
    y = torch.tensor(np.asarray(y_rows), dtype=torch.float32).unsqueeze(-1)
    model = RecurrentForecaster(kind)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=0.01)
    loss_fn = nn.MSELoss()
    model.train()
    for _ in range(EPOCHS):
        optimizer.zero_grad(set_to_none=True)
        loss = loss_fn(model(x), y)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

    model.eval()
    history = list(scaled[-WINDOW:])
    output: list[float] = []
    with torch.no_grad():
        for _ in range(steps):
            sample = torch.tensor(history[-WINDOW:], dtype=torch.float32)[None, :, None]
            predicted_scaled = float(model(sample).item())
            predicted_log = predicted_scaled * std + mean
            output.append(predicted_log)
            history.append(predicted_scaled)
    return np.asarray(output, dtype=float)


def fit_forecasts(train_log: np.ndarray, cutoff_year: int) -> dict[str, dict[str, np.ndarray]]:
    """Fit all requested models once at a cutoff and forecast up to five years."""
    steps = MAX_HORIZON
    last = float(train_log[-1])
    drift = float(np.diff(train_log).mean()) if len(train_log) > 1 else 0.0
    forecasts: dict[str, dict[str, np.ndarray]] = {
        "Naive": {"point_log": np.repeat(last, steps)},
        "Drift": {"point_log": last + drift * np.arange(1, steps + 1)},
    }

    # A predeclared ARIMA order avoids selecting parameters using the holdout.
    sarimax_fit = SARIMAX(
        train_log,
        order=(1, 1, 0),
        trend="t",
        enforce_stationarity=False,
        enforce_invertibility=False,
    ).fit(disp=False, maxiter=300)
    sarimax_prediction = sarimax_fit.get_forecast(steps=steps)
    interval_log = np.asarray(sarimax_prediction.conf_int(alpha=0.05), dtype=float)
    forecasts["SARIMAX"] = {
        "point_log": np.asarray(sarimax_prediction.predicted_mean, dtype=float),
        "lower_log": interval_log[:, 0],
        "upper_log": interval_log[:, 1],
    }
    forecasts["GRU"] = {"point_log": neural_path("GRU", train_log, steps, SEED + cutoff_year)}
    forecasts["LSTM"] = {"point_log": neural_path("LSTM", train_log, steps, SEED + 1000 + cutoff_year)}
    return forecasts


def to_level(value_log: float) -> float:
    value = math.exp(float(value_log))
    if not math.isfinite(value):
        raise ValueError("Model produced a non-finite GDP forecast")
    return value


def model_metrics(model_name: str, path: dict[str, list[dict]], actual_by_year: dict[int, float]) -> dict:
    observed = [
        (item, actual_by_year[item["year"]])
        for item in path["points"]
        if item["year"] in actual_by_year
    ]
    if not observed:
        return {
            "model": model_name, "n": 0, "mae_usd_2015": None,
            "rmse_usd_2015": None, "mape_pct": None,
            "coverage_95_pct": None, "coverage_n": 0,
            "covered_n": 0, "status": "forecast_only",
        }

    errors = np.asarray([item["predicted_usd_2015"] - actual for item, actual in observed], dtype=float)
    actuals = np.asarray([actual for _, actual in observed], dtype=float)
    result = {
        "model": model_name,
        "n": len(observed),
        "mae_usd_2015": float(np.mean(np.abs(errors))),
        "rmse_usd_2015": float(np.sqrt(np.mean(errors ** 2))),
        "mape_pct": float(np.mean(np.abs(errors / actuals)) * 100) if np.all(actuals > 0) else None,
        "coverage_95_pct": None,
        "coverage_n": 0,
        "covered_n": 0,
        "status": "evaluated",
    }
    interval_rows = [
        (item, actual) for item, actual in observed
        if item.get("lower95_usd_2015") is not None and item.get("upper95_usd_2015") is not None
    ]
    if interval_rows:
        covered = sum(
            item["lower95_usd_2015"] <= actual <= item["upper95_usd_2015"]
            for item, actual in interval_rows
        )
        result.update({
            "coverage_95_pct": float(covered / len(interval_rows) * 100),
            "coverage_n": len(interval_rows),
            "covered_n": int(covered),
        })
    return result


def main() -> None:
    if not SOURCE_FILE.is_file():
        raise FileNotFoundError(f"Không tìm thấy chuỗi GDP thực: {SOURCE_FILE}")
    data = pd.read_csv(SOURCE_FILE, encoding="utf-8-sig")
    required = {"nam", "gdp_thuc_usd_2015"}
    if not required.issubset(data.columns):
        raise ValueError(f"Chuỗi GDP thiếu cột bắt buộc: {sorted(required - set(data.columns))}")
    data = data[["nam", "gdp_thuc_usd_2015"]].copy()
    data["nam"] = pd.to_numeric(data["nam"], errors="coerce")
    data["gdp_thuc_usd_2015"] = pd.to_numeric(data["gdp_thuc_usd_2015"], errors="coerce")
    data = data.dropna().sort_values("nam")
    if data["nam"].duplicated().any():
        raise ValueError("Chuỗi GDP có năm trùng; cần xử lý nguồn trước khi chạy backtest.")
    data["nam"] = data["nam"].astype(int)
    if (data["gdp_thuc_usd_2015"] <= 0).any():
        raise ValueError("GDP thực phải dương để dùng log và MAPE.")
    years = data["nam"].to_numpy(dtype=int)
    values = data["gdp_thuc_usd_2015"].to_numpy(dtype=float)
    if np.any(np.diff(years) != 1):
        raise ValueError("Chuỗi GDP năm có khoảng trống; không nội suy để tạo quan sát giả cho backtest.")
    actual_by_year = {int(year): float(value) for year, value in zip(years, values)}
    observed_latest = int(years[-1])
    all_scenarios: list[dict] = []

    # CPU thread count and seeds are fixed to keep model fitting reproducible.
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    for item in CUTOFFS:
        cutoff_key = item["key"]
        cutoff_year = observed_latest if cutoff_key == "LATEST" else int(cutoff_key)
        train_mask = years <= cutoff_year
        train_years = years[train_mask]
        train_values = values[train_mask]
        if len(train_values) < MIN_TRAIN_YEARS:
            raise ValueError(f"Chỉ có {len(train_values)} năm trước cutoff {cutoff_key}; cần tối thiểu {MIN_TRAIN_YEARS}.")
        train_log = np.log(train_values)

        with warnings.catch_warnings(record=True) as caught_warnings:
            warnings.simplefilter("always")
            fitted = fit_forecasts(train_log, cutoff_year)
        warning_text = sorted({str(w.message) for w in caught_warnings if str(w.message)})

        for horizon in range(1, MAX_HORIZON + 1):
            evaluation_years = list(range(cutoff_year + 1, cutoff_year + horizon + 1))
            actual_series = [
                {"year": year, "actual_usd_2015": actual_by_year.get(year)}
                for year in evaluation_years
            ]
            forecast_paths: dict[str, dict] = {}
            metrics: list[dict] = []
            for model_name, fitted_path in fitted.items():
                points = []
                for step, year in enumerate(evaluation_years):
                    point = {
                        "year": year,
                        "predicted_usd_2015": to_level(fitted_path["point_log"][step]),
                    }
                    if model_name == "SARIMAX":
                        point["lower95_usd_2015"] = to_level(fitted_path["lower_log"][step])
                        point["upper95_usd_2015"] = to_level(fitted_path["upper_log"][step])
                    points.append(point)
                model_path = {"model": model_name, "points": points}
                forecast_paths[model_name] = model_path
                metrics.append(model_metrics(model_name, model_path, actual_by_year))

            observed_eval_years = [year for year in evaluation_years if year in actual_by_year]
            if cutoff_key == "LATEST":
                status = "forecast_only"
                scenario_note = "Mốc hiện tại dùng toàn bộ chuỗi quan sát để dự báo; chưa có giá trị thực tế để tính sai số."
            else:
                status = "evaluated" if observed_eval_years else "no_holdout_observations"
                scenario_note = (
                    f"Có {len(observed_eval_years)}/{horizon} năm thực tế trong cửa sổ; các năm sau kỳ cuối nguồn chỉ là dự báo."
                    if len(observed_eval_years) < horizon else
                    "Đây là kiểm định ngoài mẫu tại một mốc cắt cố định; số điểm kiểm thử còn ít nên không đại diện mọi chế độ kinh tế."
                )
            all_scenarios.append({
                "cutoff_key": cutoff_key,
                "cutoff_year": cutoff_year,
                "event_label": item["event"],
                "horizon": horizon,
                "status": status,
                "history": [
                    {"year": int(year), "value_usd_2015": float(value)}
                    for year, value in zip(train_years, train_values)
                ],
                "actuals": actual_series,
                "forecasts": forecast_paths,
                "metrics": metrics,
                "notes": [scenario_note],
                "sarimax_coverage_note": (
                    "Khoảng 95% được lấy từ SARIMAX trên log GDP rồi biến đổi ngược. Tỷ lệ bao phủ thực nghiệm dùng riêng các điểm holdout có thực tế; n nhỏ nên chỉ mang tính mô tả."
                ),
                "warnings": warning_text,
            })

    artifact = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "target": {
            "name": "GDP thực Việt Nam",
            "source": "World Bank, World Development Indicators (WDI)",
            "source_url": "https://api.worldbank.org/v2/country/VNM/indicator/NY.GDP.MKTP.KD?date=1985:2025&format=json&per_page=1000",
            "indicator": "NY.GDP.MKTP.KD",
            "dataset_path": "data/world_bank/processed/du_lieu_gdp_thuc_va_tang_truong.csv",
            "frequency": "annual",
            "unit": "USD cố định năm 2015",
            "model_scale": "log(GDP thực USD cố định 2015)",
            "observed_from": int(years[0]),
            "observed_to": observed_latest,
            "observation_count": int(len(values)),
            "interpolation_used": False,
        },
        "methodology": {
            "evaluation": "Fixed-origin cutoff backtest; each model is refit using observations through the cutoff and forecasts the next 1–5 years.",
            "preprocessing": "Log transform; neural standardization is fit inside each cutoff using only its training observations. No interpolation or random split.",
            "minimum_training_years": MIN_TRAIN_YEARS,
            "models": {
                "Naive": "Giữ nguyên log GDP cuối cùng.",
                "Drift": "Ngoại suy mức thay đổi log GDP bình quân trong cửa sổ huấn luyện.",
                "SARIMAX": "SARIMAX(1,1,0), xu hướng tuyến tính trên log GDP; đặc tả cố định trước kiểm thử.",
                "GRU": f"GRU một biến, cửa sổ {WINDOW} năm, hidden={HIDDEN_SIZE}, {EPOCHS} epochs; dự báo đệ quy.",
                "LSTM": f"LSTM một biến, cửa sổ {WINDOW} năm, hidden={HIDDEN_SIZE}, {EPOCHS} epochs; dự báo đệ quy.",
            },
            "metrics": {
                "mae_rmse_unit": "USD cố định 2015",
                "mape": "Chỉ tính khi toàn bộ giá trị thực dương.",
                "sarimax_interval": "Khoảng dự báo 95% trên log-scale biến đổi ngược; empirical coverage được báo cùng n kiểm định.",
            },
            "limitations": [
                "Chuỗi năm chỉ có khoảng 41 quan sát; GRU/LSTM tại cutoff sớm có ít cửa sổ huấn luyện và dễ bất ổn.",
                "Các cutoff lịch sử là những phép thử tình huống, không phải bằng chứng mô hình luôn chịu được mọi cú sốc.",
                "Cutoff LATEST chưa có holdout thực tế nên không có bảng xếp hạng sai số.",
                "Empirical coverage từ 1–5 điểm không đủ để khẳng định khoảng dự báo đạt độ bao phủ 95% dài hạn.",
            ],
        },
        "supported_cutoffs": [item["key"] for item in CUTOFFS],
        "supported_horizons": list(range(1, MAX_HORIZON + 1)),
        "scenarios": all_scenarios,
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(json.dumps(artifact, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT_FILE.relative_to(ROOT)} ({len(all_scenarios)} scenarios)")
    print(f"Target: {years[0]}–{observed_latest}, {len(values)} annual observations, USD constant 2015")


if __name__ == "__main__":
    main()

