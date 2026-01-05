import math
from typing import Optional

import pandas as pd


class StrategyService:
    @staticmethod
    def _ema(series: pd.Series, *, window: int) -> pd.Series:
        if window < 1:
            raise ValueError("window must be >= 1")
        return series.ewm(span=window, adjust=False, min_periods=window).mean()

    @staticmethod
    def _rma(series: pd.Series, *, window: int) -> pd.Series:
        if window < 1:
            raise ValueError("window must be >= 1")
        alpha = 1.0 / float(window)
        return series.ewm(alpha=alpha, adjust=False, min_periods=window).mean()

    @staticmethod
    def calculate_atr(df: pd.DataFrame, *, window: int = 14) -> pd.Series:
        if df.empty:
            return pd.Series(dtype=float)
        for col in ["high", "low", "close"]:
            if col not in df.columns:
                raise ValueError(f"missing {col} column")
        if window < 1:
            raise ValueError("window must be >= 1")

        high = pd.to_numeric(df["high"], errors="coerce")
        low = pd.to_numeric(df["low"], errors="coerce")
        close = pd.to_numeric(df["close"], errors="coerce")
        prev_close = close.shift(1)

        tr = pd.concat(
            [
                (high - low).abs(),
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ],
            axis=1,
        ).max(axis=1)

        return StrategyService._rma(tr, window=window)

    @staticmethod
    def calculate_adx(df: pd.DataFrame, *, window: int = 14) -> pd.Series:
        if df.empty:
            return pd.Series(dtype=float)
        for col in ["high", "low", "close"]:
            if col not in df.columns:
                raise ValueError(f"missing {col} column")
        if window < 1:
            raise ValueError("window must be >= 1")

        high = pd.to_numeric(df["high"], errors="coerce")
        low = pd.to_numeric(df["low"], errors="coerce")

        up_move = high.diff()
        down_move = (-low.diff())

        plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
        minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

        atr = StrategyService.calculate_atr(df, window=window)
        plus_dm_sm = StrategyService._rma(plus_dm, window=window)
        minus_dm_sm = StrategyService._rma(minus_dm, window=window)

        atr_safe = atr.where(atr > 0)
        plus_di = 100.0 * (plus_dm_sm / atr_safe)
        minus_di = 100.0 * (minus_dm_sm / atr_safe)

        denom = (plus_di + minus_di).where((plus_di + minus_di) != 0)
        dx = 100.0 * ((plus_di - minus_di).abs() / denom)
        adx = StrategyService._rma(dx.fillna(0.0), window=window)
        return adx

    @staticmethod
    def _calculate_ma(series: pd.Series, *, window: int, ma_type: str) -> pd.Series:
        if ma_type == "sma":
            return series.rolling(window=window, min_periods=window).mean()
        if ma_type == "ema":
            return StrategyService._ema(series, window=window)
        raise ValueError("ma_type must be 'sma' or 'ema'")

    @staticmethod
    def _ensemble_exposure_close(
        df: pd.DataFrame,
        *,
        ensemble_pairs: list[tuple[int, int]],
        ensemble_ma_type: str,
    ) -> pd.Series:
        if df.empty:
            return pd.Series(dtype=float)
        if "close" not in df.columns:
            raise ValueError("missing close column")
        if not ensemble_pairs:
            raise ValueError("ensemble_pairs is required when use_ensemble=true")

        close = pd.to_numeric(df["close"], errors="coerce")

        pair_signals: list[pd.Series] = []
        for short_w, long_w in ensemble_pairs:
            ma_s = StrategyService._calculate_ma(close, window=short_w, ma_type=ensemble_ma_type)
            ma_l = StrategyService._calculate_ma(close, window=long_w, ma_type=ensemble_ma_type)
            pair_signals.append((ma_s > ma_l).astype(float))

        signal_df = pd.concat(pair_signals, axis=1)
        valid_counts = signal_df.notna().sum(axis=1).astype(float)
        trend_score = signal_df.sum(axis=1) / valid_counts.where(valid_counts > 0)
        return trend_score.clip(lower=0.0, upper=1.0).fillna(0.0)

    @staticmethod
    def _dma_exposure_close_from_signals(
        df: pd.DataFrame,
        *,
        confirm_bars: int,
        min_cross_gap: int,
    ) -> pd.Series:
        if df.empty:
            return pd.Series(dtype=float)
        if "ma_short" not in df.columns or "ma_long" not in df.columns:
            raise ValueError("missing ma_short/ma_long columns; call calculate_moving_averages first")

        work = df.copy().reset_index(drop=True)

        def to_iso(value) -> str:
            return value.isoformat() if hasattr(value, "isoformat") else str(value)

        index_by_date = {to_iso(row["date"]): idx for idx, row in work.iterrows()}
        signals = StrategyService.generate_signals(
            work,
            confirm_bars=confirm_bars,
            min_cross_gap=min_cross_gap,
        )

        state = pd.Series([float("nan")] * len(work))
        for signal in signals:
            idx = index_by_date.get(signal["date"])
            if idx is None:
                continue
            state.iloc[idx] = 1.0 if signal["signal_type"] == "BUY" else 0.0

        return state.ffill().fillna(0.0)

    @staticmethod
    def calculate_moving_averages(df: pd.DataFrame, short_window: int = 5, long_window: int = 20) -> pd.DataFrame:
        if short_window < 1 or long_window < 1:
            raise ValueError("short_window and long_window must be >= 1")
        if short_window >= long_window:
            raise ValueError("short_window must be < long_window")
        if "close" not in df.columns:
            raise ValueError("missing close column")

        df = df.copy()
        df["ma_short"] = df["close"].rolling(window=short_window, min_periods=short_window).mean()
        df["ma_long"] = df["close"].rolling(window=long_window, min_periods=long_window).mean()
        return df

    @staticmethod
    def generate_signals(
        df: pd.DataFrame,
        *,
        confirm_bars: int = 0,
        min_cross_gap: int = 0,
    ) -> list[dict]:
        if df.empty:
            return []
        if "ma_short" not in df.columns or "ma_long" not in df.columns:
            raise ValueError("missing ma_short/ma_long columns; call calculate_moving_averages first")
        if confirm_bars < 0:
            raise ValueError("confirm_bars must be >= 0")
        if min_cross_gap < 0:
            raise ValueError("min_cross_gap must be >= 0")

        work = df.copy()
        work = work.dropna(subset=["ma_short", "ma_long"]).reset_index(drop=True)
        if work.empty:
            return []

        diff = work["ma_short"] - work["ma_long"]
        prev_diff = diff.shift(1)

        buy_cross = (diff > 0) & (prev_diff <= 0)
        sell_cross = (diff < 0) & (prev_diff >= 0)

        def confirm_at(index: int, direction: str) -> Optional[int]:
            if confirm_bars == 0:
                return index

            end = index + confirm_bars
            if end >= len(work):
                return None

            segment = diff.iloc[index : end + 1]
            if direction == "BUY":
                return end if bool((segment > 0).all()) else None
            return end if bool((segment < 0).all()) else None

        out: list[dict] = []
        last_idx_by_type: dict[str, int] = {}

        for i in range(len(work)):
            if bool(buy_cross.iloc[i]):
                confirmed = confirm_at(i, "BUY")
                if confirmed is None:
                    continue
                if "BUY" in last_idx_by_type and confirmed - last_idx_by_type["BUY"] <= min_cross_gap:
                    continue
                last_idx_by_type["BUY"] = confirmed
                row = work.iloc[confirmed]
                out.append(
                    {
                        "date": row["date"].isoformat(),
                        "signal_type": "BUY",
                        "price": float(row["close"]),
                        "ma_short": float(row["ma_short"]),
                        "ma_long": float(row["ma_long"]),
                    }
                )
                continue

            if bool(sell_cross.iloc[i]):
                confirmed = confirm_at(i, "SELL")
                if confirmed is None:
                    continue
                if "SELL" in last_idx_by_type and confirmed - last_idx_by_type["SELL"] <= min_cross_gap:
                    continue
                last_idx_by_type["SELL"] = confirmed
                row = work.iloc[confirmed]
                out.append(
                    {
                        "date": row["date"].isoformat(),
                        "signal_type": "SELL",
                        "price": float(row["close"]),
                        "ma_short": float(row["ma_short"]),
                        "ma_long": float(row["ma_long"]),
                    }
                )

        return out

    @staticmethod
    def calculate_performance(
        df: pd.DataFrame,
        *,
        initial_capital: float = 100.0,
        fee_rate: float = 0.001,
        slippage_rate: float = 0.0005,
        allow_fractional: bool = True,
        confirm_bars: int = 0,
        min_cross_gap: int = 0,
        use_ensemble: bool = False,
        ensemble_pairs: Optional[list[tuple[int, int]]] = None,
        ensemble_ma_type: str = "sma",
        use_regime_filter: bool = False,
        regime_ma_window: int = 200,
        use_adx_filter: bool = False,
        adx_window: int = 14,
        adx_threshold: float = 20.0,
        use_vol_targeting: bool = False,
        target_vol_annual: float = 0.15,
        trading_days_per_year: int = 252,
        vol_window: int = 14,
        max_leverage: float = 1.0,
        min_vol_floor: float = 1e-6,
        use_chandelier_stop: bool = False,
        chandelier_k: float = 3.0,
        use_vol_stop: bool = False,
        vol_stop_atr_mult: float = 2.0,
    ) -> dict[str, list[dict]]:
        if df.empty:
            return {"strategy": [], "benchmark": []}
        for col in ["date", "open", "close"]:
            if col not in df.columns:
                raise ValueError(f"missing {col} column")
        if initial_capital <= 0:
            raise ValueError("initial_capital must be > 0")
        if fee_rate < 0 or slippage_rate < 0:
            raise ValueError("fee_rate and slippage_rate must be >= 0")
        if use_adx_filter and not use_regime_filter:
            raise ValueError("use_adx_filter requires use_regime_filter=true")
        if use_vol_targeting:
            if target_vol_annual <= 0:
                raise ValueError("target_vol_annual must be > 0 when use_vol_targeting=true")
            if trading_days_per_year <= 0:
                raise ValueError("trading_days_per_year must be > 0")
        if max_leverage < 0:
            raise ValueError("max_leverage must be >= 0")
        if min_vol_floor <= 0:
            raise ValueError("min_vol_floor must be > 0")

        work = df.copy().reset_index(drop=True)
        work = work.dropna(subset=["date", "open", "close"])
        if work.empty:
            return {"strategy": [], "benchmark": []}

        def to_iso(value) -> str:
            return value.isoformat() if hasattr(value, "isoformat") else str(value)

        cash = float(initial_capital)
        shares = 0.0
        first_close = float(work.loc[0, "close"])

        strategy_series: list[dict] = []
        benchmark_series: list[dict] = []

        all_features_disabled = not (
            use_ensemble
            or use_regime_filter
            or use_adx_filter
            or use_vol_targeting
            or use_chandelier_stop
            or use_vol_stop
        )

        if all_features_disabled:
            if "ma_short" not in df.columns or "ma_long" not in df.columns:
                raise ValueError("missing ma_short/ma_long columns; call calculate_moving_averages first")

            index_by_date = {to_iso(row["date"]): idx for idx, row in work.iterrows()}
            signals = StrategyService.generate_signals(
                work,
                confirm_bars=confirm_bars,
                min_cross_gap=min_cross_gap,
            )

            actions_by_index: dict[int, str] = {}
            for signal in signals:
                idx = index_by_date.get(signal["date"])
                if idx is None:
                    continue
                exec_idx = idx + 1
                if exec_idx >= len(work):
                    continue
                if exec_idx in actions_by_index:
                    continue
                actions_by_index[exec_idx] = signal["signal_type"]

            for i, row in work.iterrows():
                action = actions_by_index.get(i)
                open_price = float(row["open"])
                close_price = float(row["close"])

                if action == "BUY" and shares <= 0 and cash > 0 and open_price > 0:
                    effective_price = open_price * (1 + slippage_rate)
                    unit_cost = effective_price * (1 + fee_rate)
                    if unit_cost > 0:
                        if allow_fractional:
                            buy_shares = cash / unit_cost
                        else:
                            buy_shares = int(cash / unit_cost)
                        if buy_shares > 0:
                            cash -= buy_shares * unit_cost
                            shares += buy_shares

                elif action == "SELL" and shares > 0 and open_price > 0:
                    effective_price = open_price * (1 - slippage_rate)
                    unit_revenue = effective_price * (1 - fee_rate)
                    cash += shares * unit_revenue
                    shares = 0.0

                equity = cash + shares * close_price
                date_str = to_iso(row["date"])
                strategy_series.append({"date": date_str, "value": equity / initial_capital})
                benchmark_series.append(
                    {"date": date_str, "value": (close_price / first_close) if first_close else 0.0}
                )

            return {"strategy": strategy_series, "benchmark": benchmark_series}

        if use_ensemble:
            pairs = ensemble_pairs or []
            exposure_close = StrategyService._ensemble_exposure_close(
                work,
                ensemble_pairs=pairs,
                ensemble_ma_type=ensemble_ma_type,
            )
        else:
            exposure_close = StrategyService._dma_exposure_close_from_signals(
                work,
                confirm_bars=confirm_bars,
                min_cross_gap=min_cross_gap,
            )

        close = pd.to_numeric(work["close"], errors="coerce")

        if use_regime_filter:
            regime_ma = close.rolling(window=regime_ma_window, min_periods=regime_ma_window).mean()
            exposure_close = exposure_close.where(close > regime_ma, 0.0)

        if use_adx_filter:
            adx = StrategyService.calculate_adx(work, window=adx_window)
            exposure_close = exposure_close.where(adx > float(adx_threshold), 0.0)

        atr: Optional[pd.Series] = None
        if use_vol_targeting:
            atr = StrategyService.calculate_atr(work, window=vol_window)
            atr_pct = (atr / close).abs()
            target_vol_daily = float(target_vol_annual) / math.sqrt(float(trading_days_per_year))
            vol_safe = atr_pct.clip(lower=float(min_vol_floor))
            scale = (target_vol_daily / vol_safe).clip(upper=float(max_leverage))
            exposure_close = (exposure_close * scale).clip(lower=0.0)

        desired_exposure = exposure_close.shift(1).fillna(0.0)

        if atr is None and (use_chandelier_stop or use_vol_stop):
            atr = StrategyService.calculate_atr(work, window=vol_window)

        entry_price: Optional[float] = None
        high_max: Optional[float] = None

        for i, row in work.iterrows():
            open_price = float(row["open"])
            close_price = float(row["close"])
            high_price = float(row.get("high", close_price))
            low_price = float(row.get("low", close_price))

            target = float(desired_exposure.iloc[i]) if i < len(desired_exposure) else 0.0
            target = max(0.0, target)

            had_position_before_open = shares > 0
            stop_level: Optional[float] = None
            if had_position_before_open and (use_chandelier_stop or use_vol_stop) and atr is not None and i - 1 >= 0:
                prev_atr = float(atr.iloc[i - 1])
                if prev_atr == prev_atr and prev_atr > 0:
                    candidates: list[float] = []
                    if use_chandelier_stop and high_max is not None:
                        candidates.append(high_max - float(chandelier_k) * prev_atr)
                    if use_vol_stop and entry_price is not None:
                        candidates.append(entry_price - float(vol_stop_atr_mult) * prev_atr)
                    if candidates:
                        stop_level = max(candidates)

            if open_price > 0:
                equity_at_open = cash + shares * open_price
                desired_position_value = equity_at_open * target
                current_position_value = shares * open_price
                delta_value = desired_position_value - current_position_value

                if delta_value > 0 and cash > 0:
                    effective_price = open_price * (1 + slippage_rate)
                    unit_cost = effective_price * (1 + fee_rate)
                    if unit_cost > 0:
                        desired_buy_shares = delta_value / unit_cost
                        if not allow_fractional:
                            desired_buy_shares = int(desired_buy_shares)
                        max_affordable = cash / unit_cost
                        buy_shares = min(desired_buy_shares, max_affordable)
                        if buy_shares > 0:
                            cash -= buy_shares * unit_cost
                            shares += buy_shares
                            if entry_price is None and shares > 0:
                                entry_price = effective_price
                                high_max = high_price

                elif delta_value < 0 and shares > 0:
                    effective_price = open_price * (1 - slippage_rate)
                    unit_revenue = effective_price * (1 - fee_rate)
                    desired_sell_shares = (-delta_value) / open_price
                    if not allow_fractional:
                        desired_sell_shares = int(desired_sell_shares)
                    sell_shares = min(desired_sell_shares, shares)
                    if sell_shares > 0:
                        cash += sell_shares * unit_revenue
                        shares -= sell_shares
                        if shares <= 0:
                            shares = 0.0
                            entry_price = None
                            high_max = None

            if had_position_before_open and stop_level is not None and low_price <= stop_level and shares > 0:
                fill_price = min(open_price, stop_level) if open_price > 0 else stop_level
                effective_price = fill_price * (1 - slippage_rate)
                unit_revenue = effective_price * (1 - fee_rate)
                cash += shares * unit_revenue
                shares = 0.0
                entry_price = None
                high_max = None

            if shares > 0:
                high_max = max(high_max or high_price, high_price)

            equity = cash + shares * close_price
            date_str = to_iso(row["date"])
            strategy_series.append({"date": date_str, "value": equity / initial_capital})
            benchmark_series.append({"date": date_str, "value": (close_price / first_close) if first_close else 0.0})

        return {"strategy": strategy_series, "benchmark": benchmark_series}
