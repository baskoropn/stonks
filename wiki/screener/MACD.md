# MACD Screener

This document defines the MACD golden-cross screener.

The MACD screener is separate from `SWING_SCREENER.md`. It produces its own indicator file, candidate report, and backtest report.

## Objective

The objective is still one-week swing trading, but the primary trigger is:

```text
MACD line crosses above MACD signal line
```

This is often called a bullish MACD crossover or MACD golden cross.

## Script

```text
scripts/build_macd_indicators.py
```

Run with the latest raw OHLCV file:

```bash
./venv/bin/python scripts/build_macd_indicators.py
```

## MACD Formula

```text
ema_12 = 12-day exponential moving average of close
ema_26 = 26-day exponential moving average of close
macd_line = ema_12 - ema_26
macd_signal = 9-day exponential moving average of macd_line
macd_histogram = macd_line - macd_signal
```

Golden cross:

```text
macd_golden_cross = macd_line crosses above macd_signal
```

## Supporting Filters

MACD alone is not enough, so this screener adds filters.

Trend:

```text
close > ma_20
ma_20 > ma_50
```

Momentum:

```text
macd_histogram > 0
macd_histogram > previous macd_histogram
```

Volume:

```text
volume_ratio >= 1.5
```

Liquidity:

```text
avg_value_20d >= 1,000,000,000
```

RSI safety filter:

```text
45 <= rsi_14 <= 75
```

The RSI filter avoids very weak stocks and extremely overbought stocks.

## Score

Each row receives one point for each condition:

```text
+1 macd_golden_cross
+1 macd_histogram > 0
+1 macd_histogram rising
+1 close > ma_20
+1 ma_20 > ma_50
+1 volume_ratio >= 1.5
+1 avg_value_20d >= 1,000,000,000
+1 rsi_14 between 45 and 75
```

Maximum score:

```text
8
```

Default candidate rule:

```text
macd_candidate = macd_score >= 7
                 and macd_golden_cross
                 and volume_ok
                 and liquidity_ok
                 and rsi_ok
```

## Output Files

Full indicator dataset:

```text
data/processed/ihsg_macd_indicators_<latest-date>.csv
```

Latest date screener for all stocks:

```text
data/reports/macd/screener_all_<latest-date>.csv
```

Latest MACD candidate watchlist:

```text
data/reports/macd/candidates_<latest-date>.csv
```

## Backtest

The same reusable backtest script can test this screener:

```bash
bash backtest.sh --macd
```

Backtest mechanism details are documented in `wiki/backtest/BACKTEST.md`.
