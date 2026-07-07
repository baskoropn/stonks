#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from paths import PROCESSED_DIR, reports_dir


DEFAULT_HOLD_DAYS = 5
DEFAULT_ALLOW_OVERLAP = False
DEFAULT_TAKE_PROFIT_PCT = 0.08
DEFAULT_STOP_LOSS_PCT = 0.04
STRATEGIES = {
    "swing": {
        "input_pattern": "ihsg_swing_indicators_*.csv",
        "signal_column": "swing_candidate",
        "strategy_name": "swing",
    },
    "macd": {
        "input_pattern": "ihsg_macd_indicators_*.csv",
        "signal_column": "macd_candidate",
        "strategy_name": "macd",
    },
}


def resolve_exit(
    exit_window: pd.DataFrame,
    entry_price: float,
    take_profit_pct: float,
    stop_loss_pct: float,
) -> tuple[pd.Series, float, str, int]:
    take_profit_price = entry_price * (1 + take_profit_pct)
    stop_loss_price = entry_price * (1 - stop_loss_pct)

    for holding_days, (_, row) in enumerate(exit_window.iterrows(), start=1):
        open_price = float(row["open"])
        high_price = float(row["high"])
        low_price = float(row["low"])

        if open_price <= stop_loss_price:
            return row, open_price, "stop_loss_open", holding_days
        if open_price >= take_profit_price:
            return row, open_price, "take_profit_open", holding_days

        take_profit_hit = high_price >= take_profit_price
        stop_loss_hit = low_price <= stop_loss_price

        if take_profit_hit and stop_loss_hit:
            return row, stop_loss_price, "both_hit_stop_loss_first", holding_days
        if stop_loss_hit:
            return row, stop_loss_price, "stop_loss", holding_days
        if take_profit_hit:
            return row, take_profit_price, "take_profit", holding_days

    exit_row = exit_window.iloc[-1]
    return exit_row, float(exit_row["close"]), "time_exit", len(exit_window)


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


def build_trades(
    indicators: pd.DataFrame,
    hold_days: int,
    allow_overlap: bool,
    signal_column: str,
    take_profit_pct: float,
    stop_loss_pct: float,
) -> pd.DataFrame:
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

            entry_price = float(entry_row["open"])
            if entry_price <= 0:
                continue

            exit_row, exit_price, exit_reason, holding_days = resolve_exit(
                exit_window=exit_window,
                entry_price=entry_price,
                take_profit_pct=take_profit_pct,
                stop_loss_pct=stop_loss_pct,
            )
            trade_return = exit_price / entry_price - 1
            max_gain = float(exit_window["high"].max() / entry_price - 1)
            max_loss = float(exit_window["low"].min() / entry_price - 1)

            trades.append(
                {
                    "symbol": symbol,
                    "signal_date": signal_row["date"].strftime("%Y-%m-%d"),
                    "entry_date": entry_row["date"].strftime("%Y-%m-%d"),
                    "exit_date": exit_row["date"].strftime("%Y-%m-%d"),
                    "holding_days": holding_days,
                    "max_holding_days": hold_days,
                    "exit_reason": exit_reason,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "take_profit_price": entry_price * (1 + take_profit_pct),
                    "stop_loss_price": entry_price * (1 - stop_loss_pct),
                    "take_profit_pct": take_profit_pct * 100,
                    "stop_loss_pct": stop_loss_pct * 100,
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


def run_backtest(strategy_key: str) -> None:
    strategy = STRATEGIES[strategy_key]
    indicator_path = latest_indicator_file(strategy["input_pattern"])
    strategy_name = strategy["strategy_name"]
    signal_column = strategy["signal_column"]
    indicators = pd.read_csv(indicator_path)
    trades = build_trades(
        indicators,
        hold_days=DEFAULT_HOLD_DAYS,
        allow_overlap=DEFAULT_ALLOW_OVERLAP,
        signal_column=signal_column,
        take_profit_pct=DEFAULT_TAKE_PROFIT_PCT,
        stop_loss_pct=DEFAULT_STOP_LOSS_PCT,
    )
    summary = summarize(trades)
    by_symbol = summarize_by_symbol(trades)
    by_score = summarize_by_score(trades)

    latest_date = pd.to_datetime(indicators["date"]).max().strftime("%Y-%m-%d")
    suffix = f"{strategy_name}_{latest_date}_{DEFAULT_HOLD_DAYS}d"
    output_dir = reports_dir(strategy_name)
    trades_path = output_dir / f"backtest_trades_{suffix}.csv"
    summary_path = output_dir / f"backtest_summary_{suffix}.csv"
    by_symbol_path = output_dir / f"backtest_by_symbol_{suffix}.csv"
    by_score_path = output_dir / f"backtest_by_score_{suffix}.csv"

    output_dir.mkdir(parents=True, exist_ok=True)
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


def main() -> None:
    strategy_key = os.environ.get("STONKS_BACKTEST_STRATEGY", "swing")
    if strategy_key not in STRATEGIES:
        valid = ", ".join(sorted(STRATEGIES))
        raise ValueError(f"Unknown backtest strategy: {strategy_key}. Valid strategies: {valid}")
    run_backtest(strategy_key)


if __name__ == "__main__":
    main()
