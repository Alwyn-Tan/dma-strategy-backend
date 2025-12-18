from datetime import date

import pandas as pd
import pytest

from stocks.services import StockDataService, StrategyService


@pytest.mark.django_db
def test_calculate_moving_averages_basic():
    df = pd.DataFrame(
        {
            "date": [date(2025, 1, d) for d in range(1, 8)],
            "open": [1, 2, 3, 4, 5, 6, 7],
            "high": [1, 2, 3, 4, 5, 6, 7],
            "low": [1, 2, 3, 4, 5, 6, 7],
            "close": [1, 2, 3, 4, 5, 6, 7],
            "volume": [100] * 7,
        }
    )

    out = StrategyService.calculate_moving_averages(df, short_window=3, long_window=5)
    assert "ma_short" in out.columns
    assert "ma_long" in out.columns
    assert out["ma_short"].isna().sum() == 2
    assert out["ma_long"].isna().sum() == 4


@pytest.mark.django_db
def test_generate_signals_cross_over():
    df = pd.DataFrame(
        {
            "date": [date(2025, 1, d) for d in range(1, 7)],
            "open": [1, 1, 1, 1, 1, 1],
            "high": [1, 1, 1, 1, 1, 1],
            "low": [1, 1, 1, 1, 1, 1],
            "close": [1, 1, 1, 10, 10, 10],
            "volume": [100] * 6,
        }
    )
    df = StrategyService.calculate_moving_averages(df, short_window=2, long_window=3)
    signals = StrategyService.generate_signals(df)
    assert signals
    assert all("signal_type" in s for s in signals)


@pytest.mark.django_db
def test_generate_signals_confirm_bars_delays_signal():
    df = pd.DataFrame(
        {
            "date": [date(2025, 1, d) for d in range(1, 8)],
            "open": [1, 1, 1, 1, 1, 1, 1],
            "high": [1, 1, 1, 1, 1, 1, 1],
            "low": [1, 1, 1, 1, 1, 1, 1],
            "close": [1, 1, 1, 10, 10, 10, 10],
            "volume": [100] * 7,
        }
    )
    df = StrategyService.calculate_moving_averages(df, short_window=2, long_window=3)
    base = StrategyService.generate_signals(df, confirm_bars=0)
    delayed = StrategyService.generate_signals(df, confirm_bars=1)
    assert base
    assert delayed
    assert delayed[0]["date"] >= base[0]["date"]


@pytest.mark.django_db
def test_generate_signals_min_cross_gap_same_type():
    # Construct a series that oscillates to create multiple crossings.
    df = pd.DataFrame(
        {
            "date": [date(2025, 1, d) for d in range(1, 13)],
            "open": [1] * 12,
            "high": [1] * 12,
            "low": [1] * 12,
            "close": [1, 2, 1, 2, 1, 2, 1, 10, 1, 10, 1, 10],
            "volume": [100] * 12,
        }
    )
    df = StrategyService.calculate_moving_averages(df, short_window=2, long_window=3)
    signals = StrategyService.generate_signals(df, confirm_bars=0, min_cross_gap=0)
    signals_gap = StrategyService.generate_signals(df, confirm_bars=0, min_cross_gap=2)
    assert len(signals_gap) <= len(signals)


@pytest.mark.django_db
def test_read_price_csv_repo_format(tmp_path):
    # Matches the repo's "Price/Ticker/Date" header style.
    csv = (
        "Price,open,high,low,close,volume\n"
        "Ticker,TEST,TEST,TEST,TEST,TEST\n"
        "Date,,,,,\n"
        "2025-01-01,1,2,0.5,1.5,100\n"
        "2025-01-02,2,3,1.5,2.5,200\n"
    )
    p = tmp_path / "TEST_3y.csv"
    p.write_text(csv)

    df = StockDataService.read_price_csv(p)
    assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]
    assert df.iloc[0]["date"] == date(2025, 1, 1)
