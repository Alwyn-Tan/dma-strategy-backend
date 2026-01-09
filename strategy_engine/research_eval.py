from __future__ import annotations

import math
from datetime import date
from typing import Optional

import pandas as pd


def slice_daily_records(daily: list[dict], *, start: date, end: Optional[date]) -> pd.DataFrame:
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
    cagr = compute_cagr(values, trading_days_per_year=trading_days_per_year)
    mdd = compute_max_drawdown(values)
    if cagr != cagr or mdd != mdd:
        return float("nan")
    if mdd <= 0:
        return float("nan")
    return float(cagr / mdd)


def compute_turnover(fills: list[dict], equity: pd.Series) -> float:
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
