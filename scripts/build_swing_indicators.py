#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "data" / "reports" / "swing"

DEFAULT_LIQUIDITY = 1_000_000_000
DEFAULT_VOLUME_RATIO = 1.5
DEFAULT_HIGH_DISTANCE = 0.97
DEFAULT_MIN_SCORE = 6


def latest_raw_file() -> Path:
    files = sorted(RAW_DIR.glob("ihsg_prices_*_daily.csv"), key=lambda path: path.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No raw OHLCV files found in {RAW_DIR}")
    return files[-1]


def add_indicators(
    prices: pd.DataFrame,
    min_liquidity: float,
    min_volume_ratio: float,
    high_distance: float,
    min_score: int,
    require_liquidity: bool,
    require_volume: bool,
) -> pd.DataFrame:
    required_columns = {"date", "symbol", "open", "high", "low", "close", "adj_close", "volume"}
    missing = required_columns.difference(prices.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    data = prices.copy()
    data["date"] = pd.to_datetime(data["date"])
    numeric_columns = ["open", "high", "low", "close", "adj_close", "volume"]
    for column in numeric_columns:
        data[column] = pd.to_numeric(data[column], errors="coerce")

    data = data.dropna(subset=["date", "symbol", "close", "volume"])
    data = data.sort_values(["symbol", "date"]).reset_index(drop=True)
    grouped = data.groupby("symbol", sort=False)

    data["ma_20"] = grouped["close"].transform(lambda series: series.rolling(20, min_periods=20).mean())
    data["ma_50"] = grouped["close"].transform(lambda series: series.rolling(50, min_periods=50).mean())
    data["return_5d"] = grouped["close"].pct_change(5)
    data["return_20d"] = grouped["close"].pct_change(20)
    data["volume_ma_20"] = grouped["volume"].transform(lambda series: series.rolling(20, min_periods=20).mean())
    data["volume_ratio"] = data["volume"] / data["volume_ma_20"]
    data["rolling_high_20"] = grouped["high"].transform(lambda series: series.rolling(20, min_periods=20).max())
    data["distance_from_high_20"] = data["close"] / data["rolling_high_20"] - 1
    data["traded_value"] = data["close"] * data["volume"]
    data["avg_value_20d"] = grouped["traded_value"].transform(lambda series: series.rolling(20, min_periods=20).mean())

    data["close_above_ma20"] = data["close"] > data["ma_20"]
    data["ma20_above_ma50"] = data["ma_20"] > data["ma_50"]
    data["return_5d_positive"] = data["return_5d"] > 0
    data["return_20d_positive"] = data["return_20d"] > 0
    data["volume_ok"] = data["volume_ratio"] >= min_volume_ratio
    data["breakout_ok"] = data["close"] >= data["rolling_high_20"] * high_distance
    data["liquidity_ok"] = data["avg_value_20d"] >= min_liquidity

    score_columns = [
        "close_above_ma20",
        "ma20_above_ma50",
        "return_5d_positive",
        "return_20d_positive",
        "volume_ok",
        "breakout_ok",
        "liquidity_ok",
    ]
    data["score"] = data[score_columns].sum(axis=1)
    data["trend_ok"] = data["close_above_ma20"] & data["ma20_above_ma50"]
    data["momentum_ok"] = data["return_5d_positive"] & data["return_20d_positive"]
    data["swing_candidate"] = data["score"] >= min_score
    if require_liquidity:
        data["swing_candidate"] = data["swing_candidate"] & data["liquidity_ok"]
    if require_volume:
        data["swing_candidate"] = data["swing_candidate"] & data["volume_ok"]

    ordered_columns = [
        "date",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "adj_close",
        "volume",
        "ma_20",
        "ma_50",
        "return_5d",
        "return_20d",
        "volume_ma_20",
        "volume_ratio",
        "rolling_high_20",
        "distance_from_high_20",
        "traded_value",
        "avg_value_20d",
        "score",
        "trend_ok",
        "momentum_ok",
        "volume_ok",
        "breakout_ok",
        "liquidity_ok",
        "swing_candidate",
        "close_above_ma20",
        "ma20_above_ma50",
        "return_5d_positive",
        "return_20d_positive",
    ]
    return data[ordered_columns]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build one-week swing trading indicators from raw IHSG OHLCV data.")
    parser.add_argument("--input", type=Path, default=None, help="raw OHLCV CSV; default: latest file in data/raw")
    parser.add_argument("--min-liquidity", type=float, default=DEFAULT_LIQUIDITY)
    parser.add_argument("--min-volume-ratio", type=float, default=DEFAULT_VOLUME_RATIO)
    parser.add_argument("--high-distance", type=float, default=DEFAULT_HIGH_DISTANCE)
    parser.add_argument("--min-score", type=int, default=DEFAULT_MIN_SCORE)
    parser.add_argument("--allow-illiquid", action="store_true", help="do not require avg_value_20d liquidity filter")
    parser.add_argument("--allow-low-volume", action="store_true", help="do not require volume_ratio filter")
    args = parser.parse_args()

    raw_path = args.input or latest_raw_file()
    prices = pd.read_csv(raw_path)
    indicators = add_indicators(
        prices,
        min_liquidity=args.min_liquidity,
        min_volume_ratio=args.min_volume_ratio,
        high_distance=args.high_distance,
        min_score=args.min_score,
        require_liquidity=not args.allow_illiquid,
        require_volume=not args.allow_low_volume,
    )

    latest_date = indicators["date"].max()
    latest_date_text = latest_date.strftime("%Y-%m-%d")
    full_output = PROCESSED_DIR / f"ihsg_swing_indicators_{latest_date_text}.csv"
    candidates_output = REPORTS_DIR / f"candidates_{latest_date_text}.csv"
    latest_all_output = REPORTS_DIR / f"screener_all_{latest_date_text}.csv"

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    indicators_out = indicators.copy()
    indicators_out["date"] = indicators_out["date"].dt.strftime("%Y-%m-%d")
    indicators_out.to_csv(full_output, index=False)

    latest_rows = indicators[indicators["date"].eq(latest_date)].copy()
    latest_rows = latest_rows.sort_values(
        ["score", "return_5d", "volume_ratio", "avg_value_20d"],
        ascending=[False, False, False, False],
    )
    latest_rows["date"] = latest_rows["date"].dt.strftime("%Y-%m-%d")
    latest_rows.to_csv(latest_all_output, index=False)

    candidates = latest_rows[latest_rows["swing_candidate"]].copy()
    candidates.to_csv(candidates_output, index=False)

    print(f"Read raw prices: {raw_path}")
    print(f"Wrote indicators: {full_output} ({len(indicators_out)} rows)")
    print(f"Wrote latest screener: {latest_all_output} ({len(latest_rows)} rows)")
    print(f"Wrote candidates: {candidates_output} ({len(candidates)} rows)")


if __name__ == "__main__":
    main()
