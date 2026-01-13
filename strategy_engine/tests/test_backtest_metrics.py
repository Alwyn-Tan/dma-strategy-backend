from datetime import date

import pandas as pd
import pytest

from strategy_engine.backtest_metrics import (
    compute_max_drawdown,
    slice_daily_records,
    summarize_segment,
)
from strategy_engine.services import StrategyService


@pytest.mark.django_db
def test_resolve_target_vol_daily_prefers_annual():
    daily, info = StrategyService.resolve_target_vol_daily(
        target_vol_annual=0.2,
        target_vol_daily=0.02,
        trading_days_per_year=252,
    )
    assert info["source"] == "annual"
    assert daily == pytest.approx(0.2 / (252**0.5))


@pytest.mark.django_db
def test_resolve_target_vol_daily_uses_daily_when_annual_missing():
    daily, info = StrategyService.resolve_target_vol_daily(
        target_vol_annual=None,
        target_vol_daily=0.02,
        trading_days_per_year=252,
    )
    assert info["source"] == "daily"
    assert daily == pytest.approx(0.02)


@pytest.mark.django_db
def test_slice_daily_records_is_inclusive():
    daily = [
        {"date": "2020-12-31", "value": 1.0, "equity": 100.0, "exposure": 0.0},
        {"date": "2021-01-01", "value": 1.0, "equity": 100.0, "exposure": 0.0},
        {"date": "2021-01-02", "value": 1.0, "equity": 100.0, "exposure": 0.0},
    ]
    out = slice_daily_records(daily, start=date(2021, 1, 1), end=None)
    assert out.iloc[0]["date"] == date(2021, 1, 1)


@pytest.mark.django_db
def test_compute_max_drawdown_simple():
    values = pd.Series([1.0, 1.1, 0.99, 1.2])
    mdd = compute_max_drawdown(values)
    assert mdd == pytest.approx((1.1 - 0.99) / 1.1)


@pytest.mark.django_db
def test_trade_extraction_and_metrics_smoke():
    df = pd.DataFrame(
        {
            "date": [date(2025, 1, d) for d in range(1, 11)],
            "open": [1.0] * 10,
            "high": [1.0] * 10,
            "low": [1.0] * 10,
            "close": [1.0, 1.0, 1.0, 10.0, 10.0, 10.0, 1.0, 1.0, 1.0, 1.0],
            "volume": [100] * 10,
        }
    )
    df = StrategyService.calculate_moving_averages(df, short_window=2, long_window=3)
    out = StrategyService.calculate_performance(df, fee_rate=0.0, slippage_rate=0.0, return_details=True)
    details = out["details"]

    assert details["fills"]
    assert details["closed_trades"]

    metrics = summarize_segment(
        daily=details["daily"],
        fills=details["fills"],
        closed_trades=details["closed_trades"],
        start=date(2025, 1, 1),
        end=date(2025, 1, 10),
        trading_days_per_year=252,
    )
    assert metrics["trades"] >= 1
    assert 0.0 <= metrics["win_rate"] <= 1.0
