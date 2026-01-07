from __future__ import annotations

import sys
import types
from datetime import date

import pandas as pd
import pytest
from django.core.management import call_command

from market_data.services import StockDataService


@pytest.mark.django_db
def test_build_batch_csv_filename_period_mode():
    name = StockDataService.build_batch_csv_filename(
        "aapl",
        start_date=None,
        end_date=None,
        period="3y",
    )
    assert name == "AAPL_3y.csv"


@pytest.mark.django_db
def test_build_batch_csv_filename_date_range_mode():
    assert (
        StockDataService.build_batch_csv_filename(
            "AAPL",
            start_date=date(2015, 1, 1),
            end_date=date(2025, 12, 31),
            period="3y",
        )
        == "AAPL_2015-01-01_2025-12-31.csv"
    )
    assert (
        StockDataService.build_batch_csv_filename(
            "AAPL",
            start_date=date(2015, 1, 1),
            end_date=None,
            period="3y",
        )
        == "AAPL_2015-01-01_end.csv"
    )
    assert (
        StockDataService.build_batch_csv_filename(
            "AAPL",
            start_date=None,
            end_date=date(2025, 12, 31),
            period="3y",
        )
        == "AAPL_start_2025-12-31.csv"
    )


@pytest.mark.django_db
def test_normalize_yfinance_df_multiindex_columns():
    idx = pd.to_datetime(["2025-01-01", "2025-01-02"])
    cols = pd.MultiIndex.from_product([["Open", "High", "Low", "Close", "Volume"], ["AAPL"]])
    raw = pd.DataFrame(
        [
            [10.0, 11.0, 9.0, 10.5, 100],
            [11.0, 12.0, 10.0, 11.5, 200],
        ],
        index=idx,
        columns=cols,
    )
    raw.index.name = "Date"

    out = StockDataService._normalize_yfinance_df(raw)
    assert list(out.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert out.iloc[0]["date"] == date(2025, 1, 1)


@pytest.mark.django_db
def test_yfinance_batch_csv_command_writes_and_skips(tmp_path, settings, monkeypatch):
    settings.DATA_DIR = tmp_path

    def fake_download(*_args, **_kwargs):
        idx = pd.date_range("2025-01-01", periods=3, freq="D")
        df = pd.DataFrame(
            {
                "Open": [10.0, 11.0, 12.0],
                "High": [11.0, 12.0, 13.0],
                "Low": [9.0, 10.0, 11.0],
                "Close": [10.5, 11.5, 12.5],
                "Volume": [100, 200, 300],
            },
            index=idx,
        )
        df.index.name = "Date"
        return df

    fake_module = types.SimpleNamespace(download=fake_download)
    monkeypatch.setitem(sys.modules, "yfinance", fake_module)

    call_command("yfinance_batch_csv", "--symbols", "AAPL", "--output-dir", str(tmp_path))
    out_path = tmp_path / "AAPL_3y.csv"
    assert out_path.exists()
    first = out_path.read_text()
    assert first.splitlines()[0] == "date,open,high,low,close,volume"

    def fake_download_changed(*_args, **_kwargs):
        idx = pd.date_range("2025-01-01", periods=1, freq="D")
        df = pd.DataFrame(
            {
                "Open": [999.0],
                "High": [999.0],
                "Low": [999.0],
                "Close": [999.0],
                "Volume": [999],
            },
            index=idx,
        )
        df.index.name = "Date"
        return df

    fake_module_2 = types.SimpleNamespace(download=fake_download_changed)
    monkeypatch.setitem(sys.modules, "yfinance", fake_module_2)

    call_command("yfinance_batch_csv", "--symbols", "AAPL", "--output-dir", str(tmp_path))
    second = out_path.read_text()
    assert second == first

