from __future__ import annotations

"""Metric utilities for research evaluation (IS/OOS segmentation).

This module is intentionally framework-agnostic: it operates on plain Python
records (lists of dicts) produced by the strategy engine and computes common
performance metrics for a specified date window.
"""

import math
from datetime import date
from typing import Optional

import pandas as pd


def slice_daily_records(daily: list[dict], *, start: date, end: Optional[date]) -> pd.DataFrame:
    """Slice daily records into a date-bounded DataFrame.

    Args:
        daily: Daily records (typically `details["daily"]`) containing a `date` field.
        start: Inclusive start date for the slice.
        end: Inclusive end date for the slice; if `None`, uses all dates >= start.
    Returns:
        A DataFrame sorted by date and limited to the requested window. Returns an
        empty DataFrame if input is empty or dates cannot be parsed.
    Notes:
        - Date parsing is tolerant: invalid dates are dropped.
        - Boundaries are inclusive (`start <= date <= end`).
    """
    if not daily:
        return pd.DataFrame()
    df = pd.DataFrame(daily).copy()
    if "date" not in df.columns:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"], errors="coerce", format="mixed").dt.date
    df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    df = df[df["date"] >= start]
    if end is not None:
        df = df[df["date"] <= end]
    return df.reset_index(drop=True)


def compute_max_drawdown(values: pd.Series) -> float:
    """Compute max drawdown (peak-to-trough) from a value series.

    Args:
        values: Portfolio value series (e.g. equity curve normalized to 1.0).
    Returns:
        Max drawdown as a non-negative fraction (e.g. 0.2 means -20% from peak).
        Returns NaN if input has no valid numeric values.
    """
    series = pd.to_numeric(values, errors="coerce").dropna()
    if series.empty:
        return float("nan")
    running_max = series.cummax()
    drawdown = (series / running_max) - 1.0
    worst = float(drawdown.min())
    if worst != worst:
        return float("nan")
    return float(max(0.0, -worst))


def compute_cagr(values: pd.Series, *, trading_days_per_year: int) -> float:
    """Compute CAGR from a value series using trading-day year approximation.

    Args:
        values: Portfolio value series (must have at least 2 numeric values).
        trading_days_per_year: Annualization basis (e.g. 252).
    Returns:
        CAGR as a decimal (e.g. 0.15 for +15% annualized). Returns NaN when the
        series is too short, contains non-positive endpoints, or when the
        annualization basis is invalid.
    Notes:
        Uses `(len(values) - 1) / trading_days_per_year` as the year fraction.
    """
    series = pd.to_numeric(values, errors="coerce").dropna()
    if len(series) < 2:
        return float("nan")
    if trading_days_per_year <= 0:
        return float("nan")
    start = float(series.iloc[0])
    end = float(series.iloc[-1])
    if start <= 0 or end <= 0:
        return float("nan")
    years = float(len(series) - 1) / float(trading_days_per_year)
    if years <= 0:
        return float("nan")
    return float((end / start) ** (1.0 / years) - 1.0)


def compute_sharpe(returns: pd.Series, *, trading_days_per_year: int) -> float:
    """Compute annualized Sharpe ratio from periodic returns.

    Args:
        returns: Periodic return series (e.g. daily pct changes).
        trading_days_per_year: Annualization basis (e.g. 252).
    Returns:
        Annualized Sharpe ratio. Returns NaN for too-short series or invalid
        annualization basis. Returns 0.0 when standard deviation is 0.
    """
    series = pd.to_numeric(returns, errors="coerce").dropna()
    if len(series) < 2:
        return float("nan")
    if trading_days_per_year <= 0:
        return float("nan")
    mean = float(series.mean())
    std = float(series.std(ddof=1))
    if std <= 0:
        return 0.0
    return float(mean / std * math.sqrt(float(trading_days_per_year)))


def compute_calmar(values: pd.Series, *, trading_days_per_year: int) -> float:
    """Compute Calmar ratio (CAGR / MDD).

    Args:
        values: Portfolio value series.
        trading_days_per_year: Annualization basis (e.g. 252).
    Returns:
        Calmar ratio as a float. Returns NaN if CAGR or MDD is NaN, or if MDD is
        non-positive.
    """
    cagr = compute_cagr(values, trading_days_per_year=trading_days_per_year)
    mdd = compute_max_drawdown(values)
    if cagr != cagr or mdd != mdd:
        return float("nan")
    if mdd <= 0:
        return float("nan")
    return float(cagr / mdd)


def compute_turnover(fills: list[dict], equity: pd.Series) -> float:
    """Compute a simple turnover proxy from fill notionals.

    Args:
        fills: Fill records, each optionally containing a `notional` field.
        equity: Equity series used to normalize turnover (uses mean equity).
    Returns:
        Turnover as `sum(abs(notional)) / mean(equity)`. Returns 0.0 if there are
        no fills. Returns NaN if equity cannot be normalized (e.g. empty/<=0).
    Notes:
        This is a proxy (not a standardized turnover definition).
    """
    if not fills:
        return 0.0
    eq = pd.to_numeric(equity, errors="coerce").dropna()
    if eq.empty:
        return float("nan")
    denom = float(eq.mean())
    if denom <= 0:
        return float("nan")
    traded = 0.0
    for fill in fills:
        try:
            traded += abs(float(fill.get("notional") or 0.0))
        except Exception:
            continue
    return float(traded / denom)


def compute_win_rate(closed_trades: list[dict]) -> float:
    """Compute trade-level win rate from closed trades.

    Args:
        closed_trades: Closed trade records, each optionally containing `pnl`.
    Returns:
        Win rate in [0, 1]. Returns NaN if no valid PnL values exist.
    """
    if not closed_trades:
        return float("nan")
    pnls: list[float] = []
    for t in closed_trades:
        try:
            pnls.append(float(t.get("pnl")))
        except Exception:
            continue
    if not pnls:
        return float("nan")
    wins = sum(1 for p in pnls if p > 0)
    return float(wins / len(pnls))


def compute_pl_ratio(closed_trades: list[dict]) -> float:
    """Compute profit/loss ratio (avg win / avg loss) from closed trades.

    Args:
        closed_trades: Closed trade records, each optionally containing `pnl`.
    Returns:
        Profit/loss ratio. Returns NaN if there are no wins or no losses, or if
        PnL values cannot be parsed.
    """
    if not closed_trades:
        return float("nan")
    wins: list[float] = []
    losses: list[float] = []
    for t in closed_trades:
        try:
            pnl = float(t.get("pnl"))
        except Exception:
            continue
        if pnl > 0:
            wins.append(pnl)
        elif pnl < 0:
            losses.append(pnl)
    if not wins or not losses:
        return float("nan")
    avg_win = float(sum(wins) / len(wins))
    avg_loss = float(abs(sum(losses) / len(losses)))
    if avg_loss <= 0:
        return float("nan")
    return float(avg_win / avg_loss)


def summarize_segment(
    *,
    daily: list[dict],
    fills: list[dict],
    closed_trades: list[dict],
    start: date,
    end: Optional[date],
    trading_days_per_year: int,
) -> dict:
    """Summarize performance metrics for a date-bounded segment.

    Args:
        daily: Daily records for the full backtest (will be sliced by date).
        fills: Fill records for the full backtest (filtered by date).
        closed_trades: Closed trade records for the full backtest (filtered by date).
        start: Inclusive segment start date.
        end: Inclusive segment end date; if `None`, uses all dates >= start.
        trading_days_per_year: Annualization basis for CAGR/Sharpe/Calmar.
    Returns:
        A dict with keys:
        - `bars`: Number of daily bars in the segment.
        - `cagr`, `mdd`, `sharpe`, `calmar`
        - `turnover`, `avg_exposure`
        - `trades`, `win_rate`, `pl_ratio`
    Notes:
        Empty segments return `bars=0`, `trades=0`, and NaN for most metrics.
    """
    daily_df = slice_daily_records(daily, start=start, end=end)
    if daily_df.empty:
        return {
            "bars": 0,
            "cagr": float("nan"),
            "mdd": float("nan"),
            "sharpe": float("nan"),
            "calmar": float("nan"),
            "turnover": float("nan"),
            "avg_exposure": float("nan"),
            "trades": 0,
            "win_rate": float("nan"),
            "pl_ratio": float("nan"),
        }

    values = pd.to_numeric(daily_df.get("value"), errors="coerce")
    returns = values.pct_change().fillna(0.0)

    fills_in_range: list[dict] = []
    for f in fills:
        try:
            d = pd.to_datetime(f.get("date"), errors="coerce", format="mixed").date()
        except Exception:
            continue
        if d is None:
            continue
        if d < start:
            continue
        if end is not None and d > end:
            continue
        fills_in_range.append(f)

    closed_in_range: list[dict] = []
    for t in closed_trades:
        try:
            d = pd.to_datetime(t.get("exit_date"), errors="coerce", format="mixed").date()
        except Exception:
            continue
        if d is None:
            continue
        if d < start:
            continue
        if end is not None and d > end:
            continue
        closed_in_range.append(t)

    exposure_series = (
        pd.to_numeric(daily_df["exposure"], errors="coerce") if "exposure" in daily_df.columns else pd.Series(dtype=float)
    )
    equity = pd.to_numeric(daily_df["equity"], errors="coerce") if "equity" in daily_df.columns else pd.Series(dtype=float)
    avg_exposure = float(exposure_series.mean()) if not exposure_series.empty else float("nan")

    return {
        "bars": int(len(daily_df)),
        "cagr": compute_cagr(values, trading_days_per_year=trading_days_per_year),
        "mdd": compute_max_drawdown(values),
        "sharpe": compute_sharpe(returns, trading_days_per_year=trading_days_per_year),
        "calmar": compute_calmar(values, trading_days_per_year=trading_days_per_year),
        "turnover": compute_turnover(fills_in_range, equity),
        "avg_exposure": avg_exposure,
        "trades": int(len(closed_in_range)),
        "win_rate": compute_win_rate(closed_in_range),
        "pl_ratio": compute_pl_ratio(closed_in_range),
    }
