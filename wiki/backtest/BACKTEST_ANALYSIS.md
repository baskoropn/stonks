# Backtest Analysis

This document summarizes the current backtest result and interpretation.

Backtest mechanism details are documented in `wiki/backtest/BACKTEST.md`.

## Dataset

Current swing analysis uses:

```text
data/processed/ihsg_swing_indicators_2026-07-07.csv
```

Signal sample:

```text
signal_date range: 2026-02-03 to 2026-06-30
latest data date: 2026-07-07
holding period: 5 trading days
overlapping trades per symbol: disabled
```

## Overall Result

From:

```text
data/reports/swing/backtest_summary_swing_2026-07-07_5d.csv
```

```text
trades: 666
win_rate: 30.03%
average_return: -3.51%
median_return: -3.05%
best_trade: 105.77%
worst_trade: -55.50%
profit_factor: 0.49
```

## By Score

From:

```text
data/reports/swing/backtest_by_score_swing_2026-07-07_5d.csv
```

```text
score 7:
trades: 120
win_rate: 33.33%
average_return: -3.54%
median_return: -2.58%
profit_factor: 0.48

score 6:
trades: 546
win_rate: 29.30%
average_return: -3.51%
median_return: -3.32%
profit_factor: 0.49
```

## Interpretation

The current swing screener is not profitable on the available 2026 sample.

Main reasons:

```text
win rate is low
average return is negative
median return is negative
profit factor is below 1
score 7 does not materially outperform score 6
```

The conclusion is not that the data pipeline is wrong. The useful conclusion is that the current screener rule is too loose or incomplete for a one-week swing strategy.

## MACD Screener Result

Current MACD analysis uses:

```text
data/processed/ihsg_macd_indicators_2026-07-07.csv
```

From:

```text
data/reports/macd/backtest_summary_macd_2026-07-07_5d.csv
```

```text
trades: 207
win_rate: 26.57%
average_return: -6.10%
median_return: -5.70%
best_trade: 54.05%
worst_trade: -55.50%
profit_factor: 0.31
```

By score:

```text
score 8:
trades: 68
win_rate: 29.41%
average_return: -5.43%
median_return: -5.76%
profit_factor: 0.36

score 7:
trades: 139
win_rate: 25.18%
average_return: -6.43%
median_return: -5.70%
profit_factor: 0.28
```

Current latest MACD candidates:

```text
NEST.JK
YOII.JK
```

Interpretation:

```text
The MACD screener is also not profitable on the available 2026 sample.
```

The MACD filter produced fewer historical trades than the swing screener, but the average return and profit factor were worse.

## What This Tells Us

The current rules find stocks with technical confirmation, but neither combination produced good 5-day forward returns in this sample.

Possible issues:

```text
entries may be too late after the move
volume spike may mark exhaustion instead of continuation
no stop loss or take profit is used
market-wide condition is ignored
all candidates are treated equally
low-priced volatile stocks may dominate signals
```

## Recommended Next Tests

Test stricter trend filters:

```text
close > ma_50
ma_20 > ma_50
ma_50 slope positive
```

Test different holding periods:

```text
3 trading days
5 trading days
10 trading days
```

Test stop loss / take profit:

```text
stop loss: -5%
take profit: +8%
```

Test liquidity thresholds:

```text
avg_value_20d >= 5,000,000,000
avg_value_20d >= 10,000,000,000
```

Test avoiding overextended names:

```text
return_5d <= 20%
distance_from_ma20 <= 10%
```

Test market regime:

```text
only trade when IHSG index is above MA20 or MA50
```
