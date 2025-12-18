import logging
import re
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
from django.conf import settings

logger = logging.getLogger(__name__)


class StockDataService:
    _SAFE_CODE_RE = re.compile(r"^[A-Za-z0-9._-]+$")

    @classmethod
    def _validate_code(cls, stock_code: str) -> str:
        code = (stock_code or "").strip()
        if not code:
            raise ValueError("code is required")
        if not cls._SAFE_CODE_RE.fullmatch(code):
            raise ValueError("invalid code: only letters/numbers/._- are allowed")
        return code

    @staticmethod
    def _candidate_paths(data_dir: Path, code: str) -> list[Path]:
        candidates = [
            data_dir / f"{code}.csv",
            data_dir / f"{code.upper()}.csv",
            data_dir / f"{code}_3y.csv",
            data_dir / f"{code.upper()}_3y.csv",
        ]
        deduped: list[Path] = []
        seen = set()
        for path in candidates:
            if path not in seen:
                deduped.append(path)
                seen.add(path)
        return deduped

    @classmethod
    def resolve_csv_path(cls, stock_code: str, data_dir: Optional[Path] = None) -> Path:
        code = cls._validate_code(stock_code)
        data_dir = Path(data_dir) if data_dir else Path(settings.DATA_DIR)
        for candidate in cls._candidate_paths(data_dir, code):
            if candidate.exists() and candidate.is_file():
                return candidate
        raise FileNotFoundError(f"No CSV found for code={code} in {data_dir}")

    @staticmethod
    def read_price_csv(csv_path: Path) -> pd.DataFrame:
        """
        Reads CSV files in either:
        - simple format: date,open,high,low,close,volume
        - repo format: first column named 'Price' and extra rows (Ticker/Date) that need skipping.
        """
        csv_path = Path(csv_path)

        try:
            df = pd.read_csv(csv_path)
        except Exception:
            df = pd.read_csv(csv_path, skiprows=[1, 2])

        if not len(df.columns):
            raise ValueError(f"CSV has no columns: {csv_path}")

        first_col = df.columns[0]
        if first_col.lower() in {"price", "date"}:
            df = df.rename(columns={first_col: "date"})
        elif "date" not in {c.lower() for c in df.columns}:
            df = df.rename(columns={first_col: "date"})

        normalized = {c.lower(): c for c in df.columns}
        required = ["date", "open", "high", "low", "close", "volume"]
        missing = [k for k in required if k not in normalized]
        if missing:
            raise ValueError(f"CSV missing required columns {missing}: {csv_path}")

        df = df.rename(columns={normalized["date"]: "date"})
        for col in ["open", "high", "low", "close", "volume"]:
            df = df.rename(columns={normalized[col]: col})

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["date"] = df["date"].dt.date

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["open", "high", "low", "close"])
        df = df.sort_values("date").reset_index(drop=True)
        return df

    @classmethod
    def get_stock_data(
        cls,
        stock_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> pd.DataFrame:
        csv_path = cls.resolve_csv_path(stock_code)
        df = cls.read_price_csv(csv_path)

        if start_date:
            df = df[df["date"] >= start_date]
        if end_date:
            df = df[df["date"] <= end_date]

        return df.reset_index(drop=True)


class StrategyService:
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
            """
            Returns the confirmation index for a cross at `index`, or None if not confirmed.
            Confirmation rule: after a cross, for the next `confirm_bars` bars (inclusive),
            diff must stay on the same side (positive for BUY, negative for SELL).
            Signal time is the last confirmation bar (index + confirm_bars).
            """
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
