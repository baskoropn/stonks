#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "data" / "reports" / "macd"

DEFAULT_LIQUIDITY = 1_000_000_000
DEFAULT_VOLUME_RATIO = 1.5
DEFAULT_MIN_SCORE = 7
DEFAULT_RSI_MIN = 45
DEFAULT_RSI_MAX = 75


def latest_raw_file() -> Path:
    files = sorted(RAW_DIR.glob("ihsg_prices_*_daily.csv"), key=lambda path: path.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No raw OHLCV files found in {RAW_DIR}")
    return files[-1]


def rsi_wilder(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def add_macd_indicators(
    prices: pd.DataFrame,
    min_liquidity: float,
    min_volume_ratio: float,
    min_score: int,
    rsi_min: float,
    rsi_max: float,
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
    data["traded_value"] = data["close"] * data["volume"]
    data["avg_value_20d"] = grouped["traded_value"].transform(lambda series: series.rolling(20, min_periods=20).mean())

    data["ema_12"] = grouped["close"].transform(lambda series: series.ewm(span=12, adjust=False, min_periods=12).mean())
    data["ema_26"] = grouped["close"].transform(lambda series: series.ewm(span=26, adjust=False, min_periods=26).mean())
    data["macd_line"] = data["ema_12"] - data["ema_26"]
    data["macd_signal"] = grouped["macd_line"].transform(lambda series: series.ewm(span=9, adjust=False, min_periods=9).mean())
    data["macd_histogram"] = data["macd_line"] - data["macd_signal"]
    data["macd_line_prev"] = grouped["macd_line"].shift(1)
    data["macd_signal_prev"] = grouped["macd_signal"].shift(1)
    data["macd_histogram_prev"] = grouped["macd_histogram"].shift(1)
    data["rsi_14"] = grouped["close"].transform(rsi_wilder)

    data["macd_golden_cross"] = (data["macd_line"] > data["macd_signal"]) & (
        data["macd_line_prev"] <= data["macd_signal_prev"]
    )
    data["macd_histogram_positive"] = data["macd_histogram"] > 0
    data["macd_histogram_rising"] = data["macd_histogram"] > data["macd_histogram_prev"]
    data["close_above_ma20"] = data["close"] > data["ma_20"]
    data["ma20_above_ma50"] = data["ma_20"] > data["ma_50"]
    data["volume_ok"] = data["volume_ratio"] >= min_volume_ratio
    data["liquidity_ok"] = data["avg_value_20d"] >= min_liquidity
    data["rsi_ok"] = data["rsi_14"].between(rsi_min, rsi_max, inclusive="both")

    score_columns = [
        "macd_golden_cross",
        "macd_histogram_positive",
        "macd_histogram_rising",
        "close_above_ma20",
        "ma20_above_ma50",
        "volume_ok",
        "liquidity_ok",
        "rsi_ok",
    ]
    data["macd_score"] = data[score_columns].sum(axis=1)
    data["score"] = data["macd_score"]
    data["trend_ok"] = data["close_above_ma20"] & data["ma20_above_ma50"]
    data["momentum_ok"] = data["macd_histogram_positive"] & data["macd_histogram_rising"]
    data["macd_candidate"] = (
        (data["macd_score"] >= min_score)
        & data["macd_golden_cross"]
        & data["volume_ok"]
        & data["liquidity_ok"]
        & data["rsi_ok"]
    )

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
        "traded_value",
        "avg_value_20d",
        "ema_12",
        "ema_26",
        "macd_line",
        "macd_signal",
        "macd_histogram",
        "rsi_14",
        "score",
        "macd_score",
        "trend_ok",
        "momentum_ok",
        "volume_ok",
        "liquidity_ok",
        "rsi_ok",
        "macd_golden_cross",
        "macd_histogram_positive",
        "macd_histogram_rising",
        "close_above_ma20",
        "ma20_above_ma50",
        "macd_candidate",
    ]
    return data[ordered_columns]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build MACD golden-cross screener indicators from raw IHSG OHLCV data.")
    parser.add_argument("--input", type=Path, default=None, help="raw OHLCV CSV; default: latest file in data/raw")
    parser.add_argument("--min-liquidity", type=float, default=DEFAULT_LIQUIDITY)
    parser.add_argument("--min-volume-ratio", type=float, default=DEFAULT_VOLUME_RATIO)
    parser.add_argument("--min-score", type=int, default=DEFAULT_MIN_SCORE)
    parser.add_argument("--rsi-min", type=float, default=DEFAULT_RSI_MIN)
    parser.add_argument("--rsi-max", type=float, default=DEFAULT_RSI_MAX)
    args = parser.parse_args()

    raw_path = args.input or latest_raw_file()
    prices = pd.read_csv(raw_path)
    indicators = add_macd_indicators(
        prices,
        min_liquidity=args.min_liquidity,
        min_volume_ratio=args.min_volume_ratio,
        min_score=args.min_score,
        rsi_min=args.rsi_min,
        rsi_max=args.rsi_max,
    )

    latest_date = indicators["date"].max()
    latest_date_text = latest_date.strftime("%Y-%m-%d")
    full_output = PROCESSED_DIR / f"ihsg_macd_indicators_{latest_date_text}.csv"
    candidates_output = REPORTS_DIR / f"candidates_{latest_date_text}.csv"
    latest_all_output = REPORTS_DIR / f"screener_all_{latest_date_text}.csv"

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    indicators_out = indicators.copy()
    indicators_out["date"] = indicators_out["date"].dt.strftime("%Y-%m-%d")
    indicators_out.to_csv(full_output, index=False)

    latest_rows = indicators[indicators["date"].eq(latest_date)].copy()
    latest_rows = latest_rows.sort_values(
        ["macd_score", "volume_ratio", "avg_value_20d"],
        ascending=[False, False, False],
    )
    latest_rows["date"] = latest_rows["date"].dt.strftime("%Y-%m-%d")
    latest_rows.to_csv(latest_all_output, index=False)

    candidates = latest_rows[latest_rows["macd_candidate"]].copy()
    candidates.to_csv(candidates_output, index=False)

    print(f"Read raw prices: {raw_path}")
    print(f"Wrote MACD indicators: {full_output} ({len(indicators_out)} rows)")
    print(f"Wrote latest MACD screener: {latest_all_output} ({len(latest_rows)} rows)")
    print(f"Wrote MACD candidates: {candidates_output} ({len(candidates)} rows)")


if __name__ == "__main__":
    main()
