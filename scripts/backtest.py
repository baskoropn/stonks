#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
REPORTS_ROOT = ROOT / "data" / "reports"


def latest_indicator_file(pattern: str = "ihsg_swing_indicators_*.csv") -> Path:
    files = sorted(PROCESSED_DIR.glob(pattern), key=lambda path: path.stat().st_mtime)
    if not files:
        raise FileNotFoundError(f"No indicator files found in {PROCESSED_DIR}")
    return files[-1]


def profit_factor(returns: pd.Series) -> float:
    wins = returns[returns > 0].sum()
    losses = returns[returns < 0].sum()
    if losses == 0:
        return float("inf") if wins > 0 else 0.0
    return float(wins / abs(losses))


def max_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    equity = (1 + returns).cumprod()
    drawdown = equity / equity.cummax() - 1
    return float(drawdown.min())


def build_trades(indicators: pd.DataFrame, hold_days: int, allow_overlap: bool, signal_column: str) -> pd.DataFrame:
    required_columns = {
        "date",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "score",
        signal_column,
        "return_5d",
        "return_20d",
        "volume_ratio",
        "avg_value_20d",
    }
    missing = required_columns.difference(indicators.columns)
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(sorted(missing))}")

    data = indicators.copy()
    data["date"] = pd.to_datetime(data["date"])
    for column in ["open", "high", "low", "close", "score", "return_5d", "return_20d", "volume_ratio", "avg_value_20d"]:
        data[column] = pd.to_numeric(data[column], errors="coerce")
    if data[signal_column].dtype != bool:
        data[signal_column] = data[signal_column].astype(str).str.lower().eq("true")

    data = data.dropna(subset=["date", "symbol", "open", "close"])
    data = data.sort_values(["symbol", "date"]).reset_index(drop=True)

    trades: list[dict[str, object]] = []
    for symbol, symbol_data in data.groupby("symbol", sort=False):
        symbol_data = symbol_data.reset_index(drop=True)
        next_allowed_signal_index = 0

        for signal_index, signal_row in symbol_data[symbol_data[signal_column]].iterrows():
            if not allow_overlap and signal_index < next_allowed_signal_index:
                continue

            entry_index = signal_index + 1
            exit_index = signal_index + hold_days
            if exit_index >= len(symbol_data) or entry_index >= len(symbol_data):
                continue

            entry_row = symbol_data.iloc[entry_index]
            exit_window = symbol_data.iloc[entry_index : exit_index + 1]
            exit_row = symbol_data.iloc[exit_index]

            entry_price = float(entry_row["open"])
            exit_price = float(exit_row["close"])
            if entry_price <= 0:
                continue

            trade_return = exit_price / entry_price - 1
            max_gain = float(exit_window["high"].max() / entry_price - 1)
            max_loss = float(exit_window["low"].min() / entry_price - 1)

            trades.append(
                {
                    "symbol": symbol,
                    "signal_date": signal_row["date"].strftime("%Y-%m-%d"),
                    "entry_date": entry_row["date"].strftime("%Y-%m-%d"),
                    "exit_date": exit_row["date"].strftime("%Y-%m-%d"),
                    "holding_days": hold_days,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "return": trade_return,
                    "return_pct": trade_return * 100,
                    "max_gain_pct": max_gain * 100,
                    "max_loss_pct": max_loss * 100,
                    "win": trade_return > 0,
                    "signal_column": signal_column,
                    "signal_score": int(signal_row["score"]),
                    "signal_return_5d": signal_row["return_5d"],
                    "signal_return_20d": signal_row["return_20d"],
                    "signal_volume_ratio": signal_row["volume_ratio"],
                    "signal_avg_value_20d": signal_row["avg_value_20d"],
                }
            )

            if not allow_overlap:
                next_allowed_signal_index = exit_index + 1

    return pd.DataFrame(trades)


def summarize(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame(
            [
                {
                    "scope": "overall",
                    "trades": 0,
                    "win_rate": 0.0,
                    "average_return": 0.0,
                    "median_return": 0.0,
                    "best_trade": 0.0,
                    "worst_trade": 0.0,
                    "profit_factor": 0.0,
                    "sequential_max_drawdown": 0.0,
                }
            ]
        )

    returns = trades["return"]
    return pd.DataFrame(
        [
            {
                "scope": "overall",
                "trades": len(trades),
                "win_rate": float(trades["win"].mean()),
                "average_return": float(returns.mean()),
                "median_return": float(returns.median()),
                "best_trade": float(returns.max()),
                "worst_trade": float(returns.min()),
                "profit_factor": profit_factor(returns),
                "sequential_max_drawdown": max_drawdown(returns),
            }
        ]
    )


def summarize_by_symbol(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()

    rows = []
    for symbol, symbol_trades in trades.groupby("symbol"):
        returns = symbol_trades["return"]
        rows.append(
            {
                "symbol": symbol,
                "trades": len(symbol_trades),
                "win_rate": float(symbol_trades["win"].mean()),
                "average_return": float(returns.mean()),
                "median_return": float(returns.median()),
                "best_trade": float(returns.max()),
                "worst_trade": float(returns.min()),
                "profit_factor": profit_factor(returns),
                "sequential_max_drawdown": max_drawdown(returns),
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["average_return", "win_rate", "trades"],
        ascending=[False, False, False],
    )


def summarize_by_score(trades: pd.DataFrame) -> pd.DataFrame:
    if trades.empty:
        return pd.DataFrame()

    rows = []
    for score, score_trades in trades.groupby("signal_score"):
        returns = score_trades["return"]
        rows.append(
            {
                "signal_score": int(score),
                "trades": len(score_trades),
                "win_rate": float(score_trades["win"].mean()),
                "average_return": float(returns.mean()),
                "median_return": float(returns.median()),
                "best_trade": float(returns.max()),
                "worst_trade": float(returns.min()),
                "profit_factor": profit_factor(returns),
                "sequential_max_drawdown": max_drawdown(returns),
            }
        )

    return pd.DataFrame(rows).sort_values("signal_score", ascending=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backtest generated screener candidates.")
    parser.add_argument("--input", type=Path, default=None, help="indicator CSV; default: latest file in data/processed")
    parser.add_argument("--input-pattern", default="ihsg_swing_indicators_*.csv", help="glob pattern used when --input is omitted")
    parser.add_argument("--signal-column", default="swing_candidate", help="boolean signal column to backtest")
    parser.add_argument("--strategy-name", default=None, help="name used in output filenames; default: signal column without _candidate")
    parser.add_argument("--hold-days", type=int, default=5, help="exit at close N trading days after signal")
    parser.add_argument("--allow-overlap", action="store_true", help="allow overlapping trades for the same symbol")
    args = parser.parse_args()

    indicator_path = args.input or latest_indicator_file(args.input_pattern)
    strategy_name = args.strategy_name or args.signal_column.removesuffix("_candidate")
    indicators = pd.read_csv(indicator_path)
    trades = build_trades(
        indicators,
        hold_days=args.hold_days,
        allow_overlap=args.allow_overlap,
        signal_column=args.signal_column,
    )
    summary = summarize(trades)
    by_symbol = summarize_by_symbol(trades)
    by_score = summarize_by_score(trades)

    latest_date = pd.to_datetime(indicators["date"]).max().strftime("%Y-%m-%d")
    suffix = f"{strategy_name}_{latest_date}_{args.hold_days}d"
    reports_dir = REPORTS_ROOT / strategy_name
    trades_path = reports_dir / f"backtest_trades_{suffix}.csv"
    summary_path = reports_dir / f"backtest_summary_{suffix}.csv"
    by_symbol_path = reports_dir / f"backtest_by_symbol_{suffix}.csv"
    by_score_path = reports_dir / f"backtest_by_score_{suffix}.csv"

    reports_dir.mkdir(parents=True, exist_ok=True)
    trades.to_csv(trades_path, index=False)
    summary.to_csv(summary_path, index=False)
    by_symbol.to_csv(by_symbol_path, index=False)
    by_score.to_csv(by_score_path, index=False)

    print(f"Read indicators: {indicator_path}")
    print(f"Wrote trades: {trades_path} ({len(trades)} rows)")
    print(f"Wrote summary: {summary_path}")
    print(f"Wrote by-symbol summary: {by_symbol_path} ({len(by_symbol)} rows)")
    print(f"Wrote by-score summary: {by_score_path} ({len(by_score)} rows)")
    if not summary.empty:
        row = summary.iloc[0]
        print(
            "Overall: "
            f"trades={int(row['trades'])}, "
            f"win_rate={row['win_rate']:.2%}, "
            f"avg_return={row['average_return']:.2%}, "
            f"profit_factor={row['profit_factor']:.2f}"
        )


if __name__ == "__main__":
    main()
