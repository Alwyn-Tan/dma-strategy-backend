from datetime import date, timedelta

import pandas as pd
import pytest

from market_data.services import StockDataService
from strategy_engine.services import StrategyService


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
def test_calculate_atr_constant_range_converges():
    df = pd.DataFrame(
        {
            "date": [date(2025, 1, d) for d in range(1, 31)],
            "open": [9.0] * 30,
            "high": [10.0] * 30,
            "low": [8.0] * 30,
            "close": [9.0] * 30,
            "volume": [100] * 30,
        }
    )
    atr = StrategyService.calculate_atr(df, window=14)
    assert len(atr) == len(df)
    assert atr.isna().sum() >= 13
    assert float(atr.dropna().iloc[-1]) == pytest.approx(2.0, abs=1e-6)


@pytest.mark.django_db
def test_calculate_adx_returns_0_to_100():
    df = pd.DataFrame(
        {
            "date": [date(2025, 1, 1) + timedelta(days=i) for i in range(40)],
            "open": [float(d) for d in range(1, 41)],
            "high": [float(d) + 1 for d in range(1, 41)],
            "low": [float(d) for d in range(1, 41)],
            "close": [float(d) + 0.5 for d in range(1, 41)],
            "volume": [100] * 40,
        }
    )
    adx = StrategyService.calculate_adx(df, window=14)
    assert len(adx) == len(df)
    tail = adx.dropna()
    assert not tail.empty
    assert (tail >= 0).all()
    assert (tail <= 100).all()


@pytest.mark.django_db
def test_calculate_performance_advanced_returns_series():
    df = pd.DataFrame(
        {
            "date": [date(2025, 1, d) for d in range(1, 21)],
            "open": [float(10 + d) for d in range(20)],
            "high": [float(10 + d) + 1 for d in range(20)],
            "low": [float(10 + d) - 1 for d in range(20)],
            "close": [float(10 + d) for d in range(20)],
            "volume": [100] * 20,
        }
    )
    out = StrategyService.calculate_performance(
        df,
        strategy_mode="advanced",
        regime_ma_window=3,
        use_adx_filter=False,
        ensemble_pairs=[(2, 3)],
        ensemble_ma_type="sma",
        target_vol=0.02,
        vol_window=2,
        max_leverage=1.0,
        min_vol_floor=1e-6,
    )
    assert "strategy" in out and "benchmark" in out
    assert len(out["strategy"]) == len(df)
    assert out["strategy"][0]["value"] == pytest.approx(1.0)


@pytest.mark.django_db
def test_advanced_ensemble_produces_partial_exposure():
    df = pd.DataFrame(
        {
            "date": [date(2025, 1, d) for d in range(1, 7)],
            "open": [10, 9, 8, 7, 6, 7],
            "high": [10, 9, 8, 7, 6, 7],
            "low": [10, 9, 8, 7, 6, 7],
            "close": [10, 9, 8, 7, 6, 7],
            "volume": [100] * 6,
        }
    )
    exposure = StrategyService._advanced_target_exposure(
        df,
        regime_ma_window=2,
        use_adx_filter=False,
        adx_window=14,
        adx_threshold=20.0,
        ensemble_pairs=[(1, 2), (3, 5)],
        ensemble_ma_type="sma",
        target_vol=0.0,
        vol_window=14,
        max_leverage=1.0,
        min_vol_floor=1e-6,
    )
    assert float(exposure.iloc[-1]) == pytest.approx(0.5)


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


@pytest.mark.django_db
def test_should_refresh_only_when_range_missing(settings):
    settings.AUTO_REFRESH_ON_REQUEST = True
    settings.AUTO_REFRESH_COOLDOWN_SECONDS = 0

    should, reason = StockDataService._should_refresh(
        "AAPL",
        start_date=date(2025, 1, 2),
        end_date=date(2025, 1, 5),
        min_date=date(2025, 1, 1),
        max_date=date(2025, 1, 10),
        force_refresh=False,
    )
    assert should is False
    assert reason == "covered_by_local"

    should, reason = StockDataService._should_refresh(
        "AAPL",
        start_date=date(2025, 1, 2),
        end_date=date(2025, 1, 12),
        min_date=date(2025, 1, 1),
        max_date=date(2025, 1, 10),
        force_refresh=False,
    )
    assert should is True
    assert reason == "end_date_after_max_date"

    should, reason = StockDataService._should_refresh(
        "AAPL",
        start_date=date(2024, 12, 20),
        end_date=date(2025, 1, 5),
        min_date=date(2025, 1, 1),
        max_date=date(2025, 1, 10),
        force_refresh=False,
    )
    assert should is True
    assert reason == "start_date_before_min_date"
