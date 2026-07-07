# Stonks

Local IHSG / IDX stock data pipeline for downloading daily OHLCV data, building screeners, and backtesting candidate signals.

This project uses:

- `yfinance` to download Yahoo Finance market data.
- `pandas` to clean, transform, and calculate indicators.
- The IDX workbook `Daftar Saham  - 20260707.xlsx` as the stock universe source.

## Architecture

```text
Daftar Saham  - 20260707.xlsx
        |
        v
scripts/download_ihsg_2026.py
        |
        +--> data/universe/idx_equities_20260707.csv
        +--> data/raw/ihsg_prices_<start>_<end>_daily.csv
        +--> data/reports/download/ihsg_download_status_<start>_<end>.csv
        |
        v
scripts/build_swing_indicators.py
        |
        +--> data/processed/ihsg_swing_indicators_<latest-date>.csv
        +--> data/reports/swing/screener_all_<latest-date>.csv
        +--> data/reports/swing/candidates_<latest-date>.csv
        |
        v
scripts/build_macd_indicators.py
        |
        +--> data/processed/ihsg_macd_indicators_<latest-date>.csv
        +--> data/reports/macd/screener_all_<latest-date>.csv
        +--> data/reports/macd/candidates_<latest-date>.csv
        |
        v
scripts/backtest.py
        |
        +--> data/reports/<strategy>/backtest_trades_<strategy>_<latest-date>_5d.csv
        +--> data/reports/<strategy>/backtest_summary_<strategy>_<latest-date>_5d.csv
        +--> data/reports/<strategy>/backtest_by_symbol_<strategy>_<latest-date>_5d.csv
        +--> data/reports/<strategy>/backtest_by_score_<strategy>_<latest-date>_5d.csv
```

## Directory Layout

```text
.
├── Daftar Saham  - 20260707.xlsx
├── download_ohlcv.sh
├── requirements.txt
├── scripts/
│   ├── download_ihsg_2026.py
│   ├── build_swing_indicators.py
│   ├── build_macd_indicators.py
│   └── backtest.py
└── data/
    ├── universe/
    ├── raw/
    ├── processed/
    └── reports/
```

## Data Layers

`data/universe`

Contains the stock universe extracted from the IDX workbook. Stock codes are converted into Yahoo Finance symbols by adding `.JK`, for example `BBCA` becomes `BBCA.JK`.

`data/raw`

Contains raw daily OHLCV data from yfinance. This layer should be treated as source data and not edited manually.

Main columns:

```text
date,symbol,open,high,low,close,adj_close,volume,dividends,stock_splits,capital_gains
```

`data/processed`

Contains generated indicator datasets. These files are derived from `data/raw`.

`data/reports`

Contains operational reports and latest screener outputs:

```text
download/ihsg_download_status_<start>_<end>.csv
swing/screener_all_<latest-date>.csv
swing/candidates_<latest-date>.csv
swing/backtest_trades_swing_<latest-date>_5d.csv
swing/backtest_summary_swing_<latest-date>_5d.csv
swing/backtest_by_symbol_swing_<latest-date>_5d.csv
swing/backtest_by_score_swing_<latest-date>_5d.csv
macd/screener_all_<latest-date>.csv
macd/candidates_<latest-date>.csv
macd/backtest_trades_macd_<latest-date>_5d.csv
macd/backtest_summary_macd_<latest-date>_5d.csv
macd/backtest_by_symbol_macd_<latest-date>_5d.csv
macd/backtest_by_score_macd_<latest-date>_5d.csv
```

## Installation

Create and activate a virtual environment:

```bash
cd /Users/baskoro/Documents/kodingan/stonks
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

The current requirement is:

```text
yfinance==0.2.65
```

`pandas` is installed automatically as a dependency of `yfinance`.

## Main Commands

From zero, run these in order:

```bash
bash download_ohlcv.sh
bash indicators.sh --all
bash backtest.sh --all
```

`download_ohlcv.sh` downloads raw OHLCV and status only. With no parameters, this means:

```text
start = 2026-01-01
end   = tomorrow internally, so today's available Yahoo data is included
```

The scripts are intentionally split:

```text
download_ohlcv.sh -> data/raw + data/reports/download
indicators.sh     -> data/processed + screener candidate reports
backtest.sh       -> backtest reports
```

## Custom Date Range

`yfinance` treats `end` as exclusive. To include `2026-07-08`, pass `--end 2026-07-09`.

```bash
bash download_ohlcv.sh --start 2026-01-01 --end 2026-07-09
```

## Useful Parameters

Download smaller batches if Yahoo starts timing out:

```bash
bash download_ohlcv.sh --chunk-size 50
```

Use more or fewer download threads:

```bash
bash download_ohlcv.sh --threads 4
```

Build indicators:

```bash
bash indicators.sh --swing
bash indicators.sh --macd
bash indicators.sh --all
```

Build swing indicators with stricter liquidity:

```bash
bash indicators.sh --swing --min-liquidity 5000000000
```

Backtest:

```bash
bash backtest.sh --swing
bash backtest.sh --macd
bash backtest.sh --all
```

Run a different holding period:

```bash
bash backtest.sh --swing --hold-days 3
```

The shell scripts call the Python implementation under `scripts/`. You can still run the Python scripts directly for development:

```bash
./venv/bin/python scripts/build_swing_indicators.py
./venv/bin/python scripts/build_macd_indicators.py
./venv/bin/python scripts/backtest.py \
  --input-pattern "ihsg_swing_indicators_*.csv" \
  --signal-column swing_candidate \
  --strategy-name swing
```

## Current Defaults

Download defaults:

```text
start: 2026-01-01
end: tomorrow
chunk-size: 75
threads: 8
sleep between chunks: 1 second
repair: disabled
```

Screener defaults:

```text
min_score: 6
min_liquidity: 1,000,000,000 IDR average traded value
min_volume_ratio: 1.5
high_distance: 0.97
liquidity required: yes
volume confirmation required: yes
```

Backtest defaults:

```text
entry: next trading day open after signal
exit: close 5 trading days after signal
overlapping trades per symbol: disabled
transaction costs: not included
slippage: not included
```

## Documentation

Screener rules and indicator definitions:

```text
wiki/screener/SWING_SCREENER.md
```

MACD screener rules and indicator definitions:

```text
wiki/screener/MACD.md
```

Backtest mechanism:

```text
wiki/backtest/BACKTEST.md
```

Current backtest result and analysis:

```text
wiki/backtest/BACKTEST_ANALYSIS.md
```

## Notes

`repair=True` is disabled by default because `yfinance==0.2.65` with the current Python/Pandas stack produced `ValueError: output array is read-only` for many IDX symbols.

Yahoo Finance coverage is not perfect. Some IDX symbols may return no price data because they are suspended, delisted, newly listed, or unavailable on Yahoo.

This project is for research and screening. It is not financial advice.
