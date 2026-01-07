from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from market_data.services import StockDataService


class Command(BaseCommand):
    help = "Batch download daily OHLCV from yfinance (adjusted) and write normalized CSVs to DATA_DIR."

    @staticmethod
    def _parse_ymd(value: Optional[str], *, field_name: str) -> Optional[date]:
        raw = (value or "").strip()
        if not raw:
            return None
        parsed = parse_date(raw)
        if parsed is None:
            raise CommandError(f"{field_name} must be YYYY-MM-DD")
        return parsed

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbols",
            nargs="+",
            required=True,
            help="One or more symbols (e.g., AAPL MSFT 00700.HK).",
        )
        parser.add_argument(
            "--period",
            default="3y",
            help="Used only when neither --start-date nor --end-date is provided (default: 3y).",
        )
        parser.add_argument("--start-date", default=None, help="YYYY-MM-DD (optional).")
        parser.add_argument("--end-date", default=None, help="YYYY-MM-DD (optional).")
        parser.add_argument(
            "--output-dir",
            default=None,
            help="Output directory (default: settings.DATA_DIR).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing files (atomic replace).",
        )

    def handle(self, *args, **options):
        symbols: list[str] = list(options["symbols"] or [])
        period: str = str(options.get("period") or "3y")
        start_date = self._parse_ymd(options.get("start_date"), field_name="start_date")
        end_date = self._parse_ymd(options.get("end_date"), field_name="end_date")
        force: bool = bool(options.get("force", False))

        output_dir_raw = options.get("output_dir")
        output_dir = Path(output_dir_raw) if output_dir_raw else Path(settings.DATA_DIR)
        output_dir.mkdir(parents=True, exist_ok=True)

        failures: list[tuple[str, str]] = []
        written = 0
        skipped = 0

        mode = "date-range" if (start_date or end_date) else "period"
        self.stdout.write(
            f"Downloading {len(symbols)} symbol(s) from yfinance (mode={mode}, auto_adjust=true) -> {output_dir}"
        )

        for raw_symbol in symbols:
            symbol = (raw_symbol or "").strip()
            if not symbol:
                continue

            try:
                code = StockDataService._validate_code(symbol).upper()
                filename = StockDataService.build_batch_csv_filename(
                    code,
                    start_date=start_date,
                    end_date=end_date,
                    period=period,
                )
                out_path = output_dir / filename

                if out_path.exists() and not force:
                    skipped += 1
                    self.stdout.write(f"[SKIP] {code} -> {out_path.name} (exists; use --force to overwrite)")
                    continue

                df = StockDataService.fetch_yfinance_ohlcv(
                    code,
                    start_date=start_date,
                    end_date=end_date,
                    period=period,
                    auto_adjust=True,
                )
                if df.empty:
                    raise ValueError("yfinance returned no rows after filtering")

                StockDataService.atomic_write_price_csv(out_path, df)
                written += 1

                min_date = df["date"].min()
                max_date = df["date"].max()
                self.stdout.write(
                    f"[OK] {code} -> {out_path.name} rows={len(df)} range={min_date}..{max_date}"
                )
            except Exception as exc:
                failures.append((symbol, str(exc)))
                self.stderr.write(f"[FAIL] {symbol}: {exc}")
                continue

        self.stdout.write(f"Done. written={written} skipped={skipped} failed={len(failures)}")
        if failures:
            summary = ", ".join([f"{sym}({msg})" for sym, msg in failures[:5]])
            more = "" if len(failures) <= 5 else f" (+{len(failures) - 5} more)"
            raise CommandError(f"Some symbols failed: {summary}{more}")

