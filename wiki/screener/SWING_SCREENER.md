# Swing Screener

This repo currently implements a one-week swing trading screener for IHSG / IDX stocks.

The goal is not to find one magic indicator. The goal is to combine trend, momentum, volume confirmation, breakout behavior, and liquidity into a simple candidate-generation rule.

## Objective

Target holding period:

```text
around 5 trading days
```

Trading style:

```text
short-term swing continuation
```

The screener tries to find stocks that are:

- Already trending upward.
- Showing positive short-term momentum.
- Trading near recent highs.
- Experiencing stronger-than-normal volume.
- Liquid enough to enter and exit.

## Source Data

The screener uses daily OHLCV data:

```text
date
symbol
open
high
low
close
adj_close
volume
```

Indicators are calculated per `symbol`, ordered by `date`. We do not calculate rolling indicators across mixed tickers.

## Indicators

### Moving Averages

```text
ma_20 = 20-day simple moving average of close
ma_50 = 50-day simple moving average of close
```

Purpose:

- `ma_20` captures short-term trend.
- `ma_50` captures medium-term trend.
- `close > ma_20` means price is above short-term average.
- `ma_20 > ma_50` means short-term trend is stronger than medium-term trend.

### Momentum

```text
return_5d = close / close 5 trading days ago - 1
return_20d = close / close 20 trading days ago - 1
```

Purpose:

- `return_5d` checks one-week price strength.
- `return_20d` checks one-month price strength.
- Requiring both to be positive avoids stocks that only bounced for one day but remain weak on a slightly longer window.

### Volume Confirmation

```text
volume_ma_20 = 20-day average volume
volume_ratio = today volume / volume_ma_20
volume_ok = volume_ratio >= 1.5
```

Purpose:

For swing trading, price movement is stronger when volume confirms it. A stock moving upward on weak volume can be easier to reverse or manipulate, especially in smaller IDX names.

The default requires today volume to be at least 1.5x the 20-day average.

### Breakout / Near High

```text
rolling_high_20 = highest high over the last 20 trading days
distance_from_high_20 = close / rolling_high_20 - 1
breakout_ok = close >= rolling_high_20 * 0.97
```

Purpose:

The stock should be near its recent 20-day high. This supports a continuation-style swing trade rather than trying to catch falling stocks.

The default allows the close to be within 3% of the 20-day high.

### Liquidity

```text
traded_value = close * volume
avg_value_20d = 20-day average of traded_value
liquidity_ok = avg_value_20d >= 1,000,000,000
```

Purpose:

Liquidity matters because a stock can look good on a chart but still be difficult to trade. Thin stocks can have wider spreads, worse fills, and higher slippage.

The default requires average traded value of at least 1 billion IDR.

## Score

Each row receives one point for each condition:

```text
+1 close > ma_20
+1 ma_20 > ma_50
+1 return_5d > 0
+1 return_20d > 0
+1 volume_ratio >= 1.5
+1 close >= rolling_high_20 * 0.97
+1 avg_value_20d >= 1,000,000,000
```

Maximum score:

```text
7
```

Default candidate rule:

```text
swing_candidate = score >= 6
                  and liquidity_ok
                  and volume_ok
```

Liquidity and volume are mandatory by default because this screener is designed for practical swing trading, not just chart pattern discovery.

## Output Files

Full indicator dataset:

```text
data/processed/ihsg_swing_indicators_<latest-date>.csv
```

Latest date screener for all stocks:

```text
data/reports/swing/screener_all_<latest-date>.csv
```

Latest candidate watchlist:

```text
data/reports/swing/candidates_<latest-date>.csv
```

## Ranking

The latest screener output is sorted by:

```text
score descending
return_5d descending
volume_ratio descending
avg_value_20d descending
```

Reason:

- Higher score means more conditions are satisfied.
- Higher `return_5d` favors stronger one-week momentum.
- Higher `volume_ratio` favors stronger participation.
- Higher `avg_value_20d` favors more liquid stocks.

## Why This Screener

For one-week swing trading, a pure indicator like RSI or MACD alone is usually too weak. This screener combines several dimensions:

```text
trend      -> close above MA20 and MA20 above MA50
momentum   -> positive 5-day and 20-day returns
volume     -> current volume above normal volume
breakout   -> close near 20-day high
liquidity  -> enough traded value to enter and exit
```

This is more robust than relying on a single signal.

## Caveats

This screener is not a guarantee. It is a candidate generator.

It does not include:

- Stop loss logic.
- Take profit logic.
- Transaction costs.
- Slippage.
- Position sizing.
- Portfolio constraints.
