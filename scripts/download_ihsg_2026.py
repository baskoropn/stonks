#!/usr/bin/env python3
from __future__ import annotations

import csv
import re
import warnings
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from time import sleep
from typing import Iterable
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import pandas as pd
import yfinance as yf

from paths import RAW_DIR, ROOT, UNIVERSE_DIR, reports_dir

DEFAULT_EXCEL = ROOT / "Daftar Saham  - 20260707.xlsx"
DEFAULT_START = "2026-01-01"
DEFAULT_END = (date.today() + timedelta(days=1)).isoformat()
DEFAULT_CHUNK_SIZE = 75
DEFAULT_THREADS = 8
DEFAULT_SLEEP = 1.0
DEFAULT_REPAIR = False

XLSX_NS = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


@dataclass(frozen=True)
class ListedStock:
    code: str
    yahoo_symbol: str
    name: str
    listing_date: str
    shares: str
    board: str


def column_name(cell_ref: str) -> str:
    return "".join(ch for ch in cell_ref if ch.isalpha())


def cell_value(cell: ET.Element) -> str:
    if cell.attrib.get("t") == "inlineStr":
        return "".join(cell.itertext()).strip()

    value = cell.find("x:v", XLSX_NS)
    return "" if value is None or value.text is None else value.text.strip()


def read_idx_excel(path: Path) -> list[ListedStock]:
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))

    rows: list[dict[str, str]] = []
    for row in root.findall(".//x:sheetData/x:row", XLSX_NS):
        values = {
            column_name(cell.attrib["r"]): cell_value(cell)
            for cell in row.findall("x:c", XLSX_NS)
        }
        if values:
            rows.append(values)

    stocks: list[ListedStock] = []
    for row in rows[1:]:
        code = row.get("B", "").strip().upper()
        if not re.fullmatch(r"[A-Z0-9]{2,8}", code):
            continue

        stocks.append(
            ListedStock(
                code=code,
                yahoo_symbol=f"{code}.JK",
                name=row.get("C", "").strip(),
                listing_date=row.get("D", "").strip(),
                shares=row.get("E", "").strip(),
                board=row.get("F", "").strip(),
            )
        )

    return stocks


def chunks(items: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(items), size):
        yield items[index : index + size]


def flatten_prices(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()

    long = (
        frame.stack(level=0, future_stack=True)
        .rename_axis(index=["date", "symbol"])
        .reset_index()
    )
    long.columns = [str(column).lower().replace(" ", "_") for column in long.columns]
    price_columns = [column for column in ["open", "high", "low", "close", "adj_close", "volume"] if column in long]
    if price_columns:
        long = long.dropna(subset=price_columns, how="all")
    return long.sort_values(["symbol", "date"]).reset_index(drop=True)


def write_universe(stocks: list[ListedStock], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "code",
                "yahoo_symbol",
                "name",
                "listing_date",
                "shares",
                "board",
            ],
        )
        writer.writeheader()
        for stock in stocks:
            writer.writerow(stock.__dict__)


def main() -> None:
    warnings.filterwarnings("ignore", category=FutureWarning)
    warnings.filterwarnings("ignore", message=".*Timestamp.utcnow.*")

    stocks = read_idx_excel(DEFAULT_EXCEL)
    symbols = [stock.yahoo_symbol for stock in stocks]
    print(f"Loaded {len(symbols)} stock symbols from {DEFAULT_EXCEL.name}")

    universe_path = UNIVERSE_DIR / "idx_equities_20260707.csv"
    write_universe(stocks, universe_path)

    downloaded: list[pd.DataFrame] = []
    for batch_no, batch in enumerate(chunks(symbols, DEFAULT_CHUNK_SIZE), start=1):
        print(f"Downloading batch {batch_no}: {len(batch)} symbols")
        frame = yf.download(
            batch,
            start=DEFAULT_START,
            end=DEFAULT_END,
            interval="1d",
            group_by="ticker",
            auto_adjust=False,
            actions=True,
            repair=DEFAULT_REPAIR,
            threads=DEFAULT_THREADS,
            progress=False,
            timeout=30,
        )
        flat = flatten_prices(frame)
        if not flat.empty:
            downloaded.append(flat)
        sleep(DEFAULT_SLEEP)

    prices = pd.concat(downloaded, ignore_index=True) if downloaded else pd.DataFrame()
    prices_path = RAW_DIR / f"ihsg_prices_{DEFAULT_START}_{DEFAULT_END}_daily.csv"
    prices_path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(prices_path, index=False)

    counts = prices.groupby("symbol").size() if not prices.empty else pd.Series(dtype=int)
    status = pd.DataFrame(
        {
            "symbol": symbols,
            "price_rows": [int(counts.get(symbol, 0)) for symbol in symbols],
        }
    )
    status["downloaded"] = status["price_rows"] > 0
    status_path = reports_dir("download") / f"ihsg_download_status_{DEFAULT_START}_{DEFAULT_END}.csv"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status.to_csv(status_path, index=False)

    print(f"Wrote universe: {universe_path}")
    print(f"Wrote prices: {prices_path} ({len(prices)} rows)")
    print(f"Wrote status: {status_path}")
    print(f"Downloaded symbols: {status['downloaded'].sum()} / {len(status)}")


if __name__ == "__main__":
    main()
