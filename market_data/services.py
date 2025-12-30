import logging
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import pandas as pd
from django.conf import settings
from django.core.cache import cache

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

    @staticmethod
    def _data_range(df: pd.DataFrame) -> tuple[Optional[date], Optional[date]]:
        if df.empty:
            return None, None
        return df["date"].min(), df["date"].max()

    @staticmethod
    def _file_last_modified_iso(csv_path: Path) -> Optional[str]:
        try:
            mtime = csv_path.stat().st_mtime
        except FileNotFoundError:
            return None
        return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()

    @classmethod
    def _should_refresh(
        cls,
        stock_code: str,
        start_date: Optional[date],
        end_date: Optional[date],
        min_date: Optional[date],
        max_date: Optional[date],
        *,
        force_refresh: bool,
    ) -> tuple[bool, str]:
        if not settings.AUTO_REFRESH_ON_REQUEST:
            return False, "disabled"
        if not start_date and not end_date:
            return False, "no_requested_range"

        coverage_start = True if not start_date or not min_date else start_date >= min_date
        coverage_end = True if not end_date or not max_date else end_date <= max_date
        if coverage_start and coverage_end and not force_refresh:
            return False, "covered_by_local"

        reason = "range_not_covered"
        if min_date is None and max_date is None:
            reason = "no_local_data"
        elif start_date and min_date and start_date < min_date:
            reason = "start_date_before_min_date"
        elif end_date and max_date and end_date > max_date:
            reason = "end_date_after_max_date"

        cooldown = max(settings.AUTO_REFRESH_COOLDOWN_SECONDS, 0)
        if cooldown and not force_refresh:
            key = f"stock_refresh:{stock_code}"
            last_refresh = cache.get(key)
            if last_refresh and (datetime.now(timezone.utc) - last_refresh).total_seconds() < cooldown:
                return False, "cooldown"

        return True, reason

    @staticmethod
    def _normalize_yfinance_df(df: pd.DataFrame) -> pd.DataFrame:
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = [col[0] for col in df.columns]

        df = df.reset_index()

        normalized = {c.lower(): c for c in df.columns}

        column_map: dict[str, str] = {}
        if "date" in normalized:
            column_map[normalized["date"]] = "date"
        elif "datetime" in normalized:
            column_map[normalized["datetime"]] = "date"
        else:
            column_map[df.columns[0]] = "date"

        for key, col in normalized.items():
            if key == "open":
                column_map[col] = "open"
            elif key == "high":
                column_map[col] = "high"
            elif key == "low":
                column_map[col] = "low"
            elif key == "close":
                column_map[col] = "close"
            elif key == "volume":
                column_map[col] = "volume"

        df = df.rename(columns=column_map)

        required = {"date", "open", "high", "low", "close", "volume"}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"yfinance missing columns: {sorted(missing)}")

        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["date"] = df["date"].dt.date

        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.dropna(subset=["open", "high", "low", "close"])
        return df[["date", "open", "high", "low", "close", "volume"]]

    @classmethod
    def _fetch_yfinance(
        cls,
        stock_code: str,
        *,
        start_date: Optional[date],
        end_date: Optional[date],
    ) -> pd.DataFrame:
        import yfinance as yf

        if start_date is None:
            data = yf.download(
                stock_code,
                period="max",
                interval="1d",
                auto_adjust=False,
                progress=False,
            )
        else:
            yf_end = end_date + timedelta(days=1) if end_date else None
            data = yf.download(
                stock_code,
                start=start_date,
                end=yf_end,
                interval="1d",
                auto_adjust=False,
                progress=False,
            )

        if data is None or data.empty:
            raise ValueError("yfinance returned no data")

        df = cls._normalize_yfinance_df(data)
        if start_date:
            df = df[df["date"] >= start_date]
        if end_date:
            df = df[df["date"] <= end_date]
        return df.reset_index(drop=True)

    @classmethod
    def _merge_and_write_csv(cls, csv_path: Path, existing: pd.DataFrame, incoming: pd.DataFrame) -> pd.DataFrame:
        combined = pd.concat([existing, incoming], ignore_index=True)
        combined = combined.drop_duplicates(subset=["date"], keep="last")
        combined = combined.sort_values("date").reset_index(drop=True)

        temp_path = csv_path.with_suffix(".tmp")
        combined.to_csv(temp_path, index=False)
        temp_path.replace(csv_path)
        return combined

    @classmethod
    def _get_stock_data_with_meta(
        cls,
        stock_code: str,
        start_date: Optional[date],
        end_date: Optional[date],
        *,
        force_refresh: bool,
    ) -> tuple[pd.DataFrame, dict]:
        csv_path = cls.resolve_csv_path(stock_code)
        df = cls.read_price_csv(csv_path)
        min_date, max_date = cls._data_range(df)

        meta: dict = {
            "code": stock_code,
            "file": csv_path.name,
            "source": "csv",
            "last_modified": cls._file_last_modified_iso(csv_path),
            "data_range": {
                "min_date": min_date.isoformat() if min_date else None,
                "max_date": max_date.isoformat() if max_date else None,
            },
            "requested_range": {
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
            },
            "refresh": {
                "attempted": False,
                "status": "skipped",
                "reason": "not_checked",
                "fetched_rows": 0,
            },
        }

        should_refresh, reason = cls._should_refresh(
            stock_code,
            start_date,
            end_date,
            min_date,
            max_date,
            force_refresh=force_refresh,
        )
        if should_refresh:
            meta["refresh"]["attempted"] = True
            meta["refresh"]["reason"] = reason
            try:
                if start_date and min_date and start_date < min_date:
                    fetch_start = start_date
                elif max_date:
                    fetch_start = max_date + timedelta(days=1)
                else:
                    fetch_start = start_date
                fetched = cls._fetch_yfinance(stock_code, start_date=fetch_start, end_date=end_date)
                if fetched.empty:
                    meta["refresh"]["status"] = "failed"
                    meta["refresh"]["reason"] = "no_new_rows"
                else:
                    df = cls._merge_and_write_csv(csv_path, df, fetched)
                    min_date, max_date = cls._data_range(df)
                    meta["source"] = "csv+yfinance"
                    meta["refresh"]["status"] = "updated"
                    meta["refresh"]["fetched_rows"] = len(fetched)
                    meta["data_range"] = {
                        "min_date": min_date.isoformat() if min_date else None,
                        "max_date": max_date.isoformat() if max_date else None,
                    }
                    meta["last_modified"] = cls._file_last_modified_iso(csv_path)
            except Exception as exc:
                logger.warning("auto refresh failed for %s: %s", stock_code, exc)
                meta["refresh"]["status"] = "failed"
                meta["refresh"]["reason"] = str(exc)
            finally:
                cooldown = max(settings.AUTO_REFRESH_COOLDOWN_SECONDS, 0)
                if cooldown:
                    cache.set(f"stock_refresh:{stock_code}", datetime.now(timezone.utc), timeout=cooldown)
        else:
            meta["refresh"]["reason"] = reason

        coverage_start = True if not start_date or not min_date else start_date >= min_date
        coverage_end = True if not end_date or not max_date else end_date <= max_date
        meta["coverage"] = {"start_ok": coverage_start, "end_ok": coverage_end}
        meta["data_status"] = "up_to_date" if coverage_start and coverage_end else "stale"

        return df, meta

    @classmethod
    def get_stock_data(
        cls,
        stock_code: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        *,
        with_meta: bool = False,
        force_refresh: bool = False,
    ) -> pd.DataFrame:
        df, meta = cls._get_stock_data_with_meta(
            stock_code,
            start_date,
            end_date,
            force_refresh=force_refresh,
        )

        if start_date:
            df = df[df["date"] >= start_date]
        if end_date:
            df = df[df["date"] <= end_date]

        df = df.reset_index(drop=True)

        if meta is not None:
            filtered_min, filtered_max = cls._data_range(df)
            meta["filtered_range"] = {
                "min_date": filtered_min.isoformat() if filtered_min else None,
                "max_date": filtered_max.isoformat() if filtered_max else None,
            }
            meta["returned_count"] = len(df)

        if with_meta:
            return df, meta
        return df

