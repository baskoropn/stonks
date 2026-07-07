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
take profit: 8%
stop loss: 4%
same-day TP/SL conflict: stop loss first
overlapping trades per symbol: disabled
```

## Overall Result

From:

```text
data/reports/swing/backtest_summary_swing_2026-07-07_5d.csv
```

```text
trades: 666
win_rate: 22.97%
average_return: -1.48%
median_return: -4.00%
best_trade: 25.93%
worst_trade: -15.19%
profit_factor: 0.51
```

Exit reasons:

```text
stop_loss: 352
time_exit: 106
take_profit: 97
both_hit_stop_loss_first: 73
stop_loss_open: 29
take_profit_open: 9
```

## By Score

From:

```text
data/reports/swing/backtest_by_score_swing_2026-07-07_5d.csv
```

```text
score 7:
trades: 120
win_rate: 25.83%
average_return: -1.13%
median_return: -4.00%
profit_factor: 0.62

score 6:
trades: 546
win_rate: 22.34%
average_return: -1.55%
median_return: -4.00%
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
many trades hit stop loss before take profit
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
win_rate: 14.98%
average_return: -2.23%
median_return: -4.00%
best_trade: 9.69%
worst_trade: -7.35%
profit_factor: 0.33
```

Exit reasons:

```text
stop_loss: 139
take_profit: 24
both_hit_stop_loss_first: 24
time_exit: 13
stop_loss_open: 4
take_profit_open: 3
```

By score:

```text
score 8:
trades: 68
win_rate: 16.18%
average_return: -1.99%
median_return: -4.00%
profit_factor: 0.38

score 7:
trades: 139
win_rate: 14.39%
average_return: -2.35%
median_return: -4.00%
profit_factor: 0.31
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
conservative stop loss is hit more often than take profit
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

Compare nearby stop loss / take profit assumptions in code:

```text
take profit 6%, stop loss 3%
take profit 8%, stop loss 4%
take profit 10%, stop loss 5%
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
