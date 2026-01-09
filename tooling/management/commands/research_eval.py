from __future__ import annotations

import csv
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_date

from market_data.services import StockDataService
from strategy_engine.research_eval import summarize_segment
from strategy_engine.services import StrategyService


class Command(BaseCommand):
    help = "Run research evaluations (IS/OOS + ablations + optional grid search) and write artifacts to results/research/<run_id>/."

    DEFAULT_IS_START = date(2015, 1, 1)
    DEFAULT_IS_END = date(2020, 12, 31)
    DEFAULT_OOS_START = date(2021, 1, 1)

    DEFAULT_VARIANTS = [
        "dma_baseline",
        "advanced_full",
        "advanced_no_vol_targeting",
    ]

    @staticmethod
    def _parse_ymd(value: Optional[str], *, field_name: str) -> Optional[date]:
        raw = (value or "").strip()
        if not raw:
            return None
        parsed = parse_date(raw)
        if parsed is None:
            raise CommandError(f"{field_name} must be YYYY-MM-DD")
        return parsed

    @staticmethod
    def _parse_int_csv(value: str, *, field_name: str) -> list[int]:
        raw = (value or "").strip()
        if not raw:
            return []
        out: list[int] = []
        for part in raw.split(","):
            token = part.strip()
            if not token:
                continue
            try:
                out.append(int(token))
            except ValueError as exc:
                raise CommandError(f"{field_name} must be comma-separated integers") from exc
        return out

    @staticmethod
    def _parse_variants(value: Optional[str]) -> list[str]:
        raw = (value or "").strip()
        if not raw:
            return []
        return [v.strip() for v in raw.split(",") if v.strip()]

    @staticmethod
    def _write_rows_csv(path: Path, rows: list[dict]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not rows:
            path.write_text("")
            return
        fieldnames = list(rows[0].keys())
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)

    def add_arguments(self, parser):
        parser.add_argument(
            "--symbols",
            nargs="+",
            required=True,
            help="One or more symbols (e.g., AAPL MSFT 00700.HK).",
        )
        parser.add_argument("--run-id", default=None, help="Run identifier (default: UTC timestamp).")
        parser.add_argument(
            "--output-dir",
            default=None,
            help="Base output directory (default: results/research).",
        )
        parser.add_argument(
            "--data-dir",
            default=None,
            help="CSV data directory override (default: settings.DATA_DIR).",
        )

        parser.add_argument("--is-start", default=self.DEFAULT_IS_START.isoformat())
        parser.add_argument("--is-end", default=self.DEFAULT_IS_END.isoformat())
        parser.add_argument("--oos-start", default=self.DEFAULT_OOS_START.isoformat())
        parser.add_argument("--oos-end", default=None, help="Optional YYYY-MM-DD end for OOS.")

        parser.add_argument(
            "--variants",
            default=",".join(self.DEFAULT_VARIANTS),
            help="Comma-separated variant ids (default: dma_baseline,advanced_full,advanced_no_vol_targeting).",
        )

        parser.add_argument("--grid-search", action="store_true", help="Enable constrained grid search on IS.")
        parser.add_argument("--short-grid", default="5,10,20", help="Comma-separated short_window candidates.")
        parser.add_argument("--long-grid", default="20,50,100,200", help="Comma-separated long_window candidates.")
        parser.add_argument(
            "--search-metric",
            default="sharpe",
            choices=["sharpe", "calmar", "cagr"],
            help="Metric used to pick parameters on IS during grid search.",
        )

        parser.add_argument("--fee-rate", default=0.001, type=float)
        parser.add_argument("--slippage-rate", default=0.0005, type=float)
        parser.add_argument("--confirm-bars", default=0, type=int)
        parser.add_argument("--min-cross-gap", default=0, type=int)

        parser.add_argument("--use-exits", action="store_true", help="Enable exits in advanced variants.")
        parser.add_argument("--trading-days-per-year", default=252, type=int)
        parser.add_argument("--vol-window", default=14, type=int)
        parser.add_argument("--target-vol-annual", default=0.15, type=float)
        parser.add_argument("--target-vol", default=None, type=float, help="Legacy daily target volatility.")
        parser.add_argument("--max-leverage", default=1.0, type=float)
        parser.add_argument("--min-vol-floor", default=1e-6, type=float)
        parser.add_argument("--regime-ma-window", default=200, type=int)
        parser.add_argument("--adx-window", default=14, type=int)
        parser.add_argument("--adx-threshold", default=20.0, type=float)
        parser.add_argument("--ensemble-pairs", default="5:20,10:50,20:100,50:200")
        parser.add_argument("--ensemble-ma-type", default="sma", choices=["sma", "ema"])
        parser.add_argument("--chandelier-k", default=3.0, type=float)
        parser.add_argument("--vol-stop-atr-mult", default=2.0, type=float)

    def handle(self, *args, **options):
        symbols: list[str] = list(options["symbols"] or [])
        variants = self._parse_variants(options.get("variants")) or list(self.DEFAULT_VARIANTS)

        is_start = self._parse_ymd(options.get("is_start"), field_name="is_start") or self.DEFAULT_IS_START
        is_end = self._parse_ymd(options.get("is_end"), field_name="is_end") or self.DEFAULT_IS_END
        oos_start = self._parse_ymd(options.get("oos_start"), field_name="oos_start") or self.DEFAULT_OOS_START
        oos_end = self._parse_ymd(options.get("oos_end"), field_name="oos_end")

        if is_start > is_end:
            raise CommandError("is_start must be <= is_end")
        if oos_end is not None and oos_start > oos_end:
            raise CommandError("oos_start must be <= oos_end")
        if is_end >= oos_start:
            raise CommandError("IS and OOS must be disjoint (require is_end < oos_start)")

        run_id = (options.get("run_id") or "").strip()
        if not run_id:
            run_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%SZ")

        output_dir_raw = options.get("output_dir")
        base_output_dir = Path(output_dir_raw) if output_dir_raw else Path("results") / "research"
        run_dir = base_output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        series_dir = run_dir / "series"
        fills_dir = run_dir / "fills"
        trades_dir = run_dir / "trades"
        grid_dir = run_dir / "grid"

        short_grid = self._parse_int_csv(options.get("short_grid"), field_name="short_grid")
        long_grid = self._parse_int_csv(options.get("long_grid"), field_name="long_grid")
        grid_search: bool = bool(options.get("grid_search", False))
        search_metric: str = str(options.get("search_metric") or "sharpe")

        fee_rate = float(options.get("fee_rate") or 0.0)
        slippage_rate = float(options.get("slippage_rate") or 0.0)
        confirm_bars = int(options.get("confirm_bars") or 0)
        min_cross_gap = int(options.get("min_cross_gap") or 0)

        trading_days_per_year = int(options.get("trading_days_per_year") or 252)
        vol_window = int(options.get("vol_window") or 14)
        target_vol_annual = float(options.get("target_vol_annual") or 0.15)
        target_vol = options.get("target_vol")
        target_vol_daily = None if target_vol is None else float(target_vol)
        max_leverage = float(options.get("max_leverage") or 1.0)
        min_vol_floor = float(options.get("min_vol_floor") or 1e-6)

        regime_ma_window = int(options.get("regime_ma_window") or 200)
        adx_window = int(options.get("adx_window") or 14)
        adx_threshold = float(options.get("adx_threshold") or 20.0)

        ensemble_pairs_raw = str(options.get("ensemble_pairs") or "")
        ensemble_ma_type = str(options.get("ensemble_ma_type") or "sma")

        chandelier_k = float(options.get("chandelier_k") or 3.0)
        vol_stop_atr_mult = float(options.get("vol_stop_atr_mult") or 2.0)

        use_exits: bool = bool(options.get("use_exits", False))

        # Keep parsing logic consistent with StockQuerySerializer.
        parsed_pairs: list[tuple[int, int]] = []
        for part in ensemble_pairs_raw.split(","):
            token = part.strip()
            if not token:
                continue
            if ":" not in token:
                raise CommandError("ensemble_pairs must be like '5:20,10:50'")
            left, right = token.split(":", 1)
            try:
                s = int(left)
                l = int(right)
            except ValueError as exc:
                raise CommandError("ensemble_pairs must contain integer windows") from exc
            if s < 1 or l < 1 or s >= l:
                raise CommandError("ensemble_pairs requires short < long for each pair")
            parsed_pairs.append((s, l))

        variant_defs: dict[str, dict] = {
            "dma_baseline": {
                "use_ensemble": False,
                "use_regime_filter": False,
                "use_adx_filter": False,
                "use_vol_targeting": False,
                "use_chandelier_stop": False,
                "use_vol_stop": False,
            },
            "advanced_full": {
                "use_ensemble": True,
                "ensemble_pairs": parsed_pairs,
                "ensemble_ma_type": ensemble_ma_type,
                "use_regime_filter": True,
                "regime_ma_window": regime_ma_window,
                "use_adx_filter": True,
                "adx_window": adx_window,
                "adx_threshold": adx_threshold,
                "use_vol_targeting": True,
                "target_vol_annual": target_vol_annual,
                "target_vol_daily": target_vol_daily,
                "trading_days_per_year": trading_days_per_year,
                "vol_window": vol_window,
                "max_leverage": max_leverage,
                "min_vol_floor": min_vol_floor,
                "use_chandelier_stop": bool(use_exits),
                "chandelier_k": chandelier_k,
                "use_vol_stop": bool(use_exits),
                "vol_stop_atr_mult": vol_stop_atr_mult,
            },
            "advanced_no_vol_targeting": {
                "use_ensemble": True,
                "ensemble_pairs": parsed_pairs,
                "ensemble_ma_type": ensemble_ma_type,
                "use_regime_filter": True,
                "regime_ma_window": regime_ma_window,
                "use_adx_filter": True,
                "adx_window": adx_window,
                "adx_threshold": adx_threshold,
                "use_vol_targeting": False,
                "use_chandelier_stop": bool(use_exits),
                "chandelier_k": chandelier_k,
                "use_vol_stop": bool(use_exits),
                "vol_stop_atr_mult": vol_stop_atr_mult,
            },
        }

        unknown = [v for v in variants if v not in variant_defs]
        if unknown:
            raise CommandError(f"Unknown variants: {', '.join(unknown)}")

        config = {
            "run_id": run_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "symbols": symbols,
            "variants": variants,
            "split": {
                "is_start": is_start.isoformat(),
                "is_end": is_end.isoformat(),
                "oos_start": oos_start.isoformat(),
                "oos_end": oos_end.isoformat() if oos_end else None,
            },
            "grid_search": {
                "enabled": grid_search,
                "short_grid": short_grid,
                "long_grid": long_grid,
                "metric": search_metric,
            },
            "assumptions": {
                "fill": "next_open",
                "fee_rate": fee_rate,
                "slippage_rate": slippage_rate,
                "confirm_bars": confirm_bars,
                "min_cross_gap": min_cross_gap,
            },
        }
        (run_dir / "config.json").write_text(json.dumps(config, indent=2, sort_keys=True), encoding="utf-8")

        data_dir_override = options.get("data_dir")
        data_dir = Path(data_dir_override) if data_dir_override else Path(getattr(settings, "DATA_DIR", "data"))

        summary_rows: list[dict] = []
        failures: list[tuple[str, str]] = []

        self.stdout.write(f"Research eval run_id={run_id} symbols={len(symbols)} variants={variants} -> {run_dir}")

        for raw_symbol in symbols:
            symbol = (raw_symbol or "").strip()
            if not symbol:
                continue

            try:
                code = StockDataService._validate_code(symbol).upper()
                csv_path = StockDataService.resolve_csv_path(code, data_dir=data_dir)
                df = StockDataService.read_price_csv(csv_path)
                if df.empty:
                    raise ValueError("CSV contains no rows")
            except Exception as exc:
                failures.append((symbol, str(exc)))
                self.stderr.write(f"[FAIL] {symbol}: {exc}")
                continue

            df = df[(df["date"] >= is_start) & (df["date"] <= (oos_end or df["date"].max()))].reset_index(drop=True)
            if df.empty:
                failures.append((code, "no rows in requested IS/OOS range"))
                self.stderr.write(f"[FAIL] {code}: no rows in requested IS/OOS range")
                continue

            for variant in variants:
                variant_kwargs = dict(variant_defs[variant])

                def run_one(short_window: int, long_window: int) -> dict:
                    df_ma = StrategyService.calculate_moving_averages(df, short_window=short_window, long_window=long_window)
                    return StrategyService.calculate_performance(
                        df_ma,
                        initial_capital=100.0,
                        fee_rate=fee_rate,
                        slippage_rate=slippage_rate,
                        allow_fractional=True,
                        confirm_bars=confirm_bars,
                        min_cross_gap=min_cross_gap,
                        return_details=True,
                        **variant_kwargs,
                    )

                chosen_short = 5
                chosen_long = 20
                best_out: Optional[dict] = None
                grid_rows: list[dict] = []

                if grid_search:
                    best_score = float("-inf")
                    for s in short_grid:
                        for l in long_grid:
                            if s >= l:
                                continue
                            try:
                                out = run_one(s, l)
                                details = out.get("details") or {}
                                seg = summarize_segment(
                                    daily=details.get("daily", []),
                                    fills=details.get("fills", []),
                                    closed_trades=details.get("closed_trades", []),
                                    start=is_start,
                                    end=is_end,
                                    trading_days_per_year=trading_days_per_year,
                                )
                                score = float(seg.get(search_metric))
                                if score != score:
                                    score = float("-inf")
                                grid_rows.append(
                                    {
                                        "code": code,
                                        "variant": variant,
                                        "short_window": s,
                                        "long_window": l,
                                        "bars": seg.get("bars"),
                                        "cagr": seg.get("cagr"),
                                        "mdd": seg.get("mdd"),
                                        "sharpe": seg.get("sharpe"),
                                        "calmar": seg.get("calmar"),
                                    }
                                )
                                if score > best_score:
                                    best_score = score
                                    chosen_short = s
                                    chosen_long = l
                                    best_out = out
                            except Exception:
                                continue

                    self._write_rows_csv(grid_dir / f"{code}__{variant}__grid.csv", grid_rows)

                if best_out is None:
                    try:
                        best_out = run_one(chosen_short, chosen_long)
                    except Exception as exc:
                        failures.append((f"{code}:{variant}", str(exc)))
                        self.stderr.write(f"[FAIL] {code} {variant}: {exc}")
                        continue

                details = best_out.get("details") or {}
                daily = details.get("daily", [])
                fills = details.get("fills", [])
                closed_trades = details.get("closed_trades", [])

                is_metrics = summarize_segment(
                    daily=daily,
                    fills=fills,
                    closed_trades=closed_trades,
                    start=is_start,
                    end=is_end,
                    trading_days_per_year=trading_days_per_year,
                )
                oos_metrics = summarize_segment(
                    daily=daily,
                    fills=fills,
                    closed_trades=closed_trades,
                    start=oos_start,
                    end=oos_end,
                    trading_days_per_year=trading_days_per_year,
                )

                summary_rows.append(
                    {
                        "code": code,
                        "variant": variant,
                        "short_window": chosen_short,
                        "long_window": chosen_long,
                        "is_bars": is_metrics.get("bars"),
                        "is_cagr": is_metrics.get("cagr"),
                        "is_mdd": is_metrics.get("mdd"),
                        "is_sharpe": is_metrics.get("sharpe"),
                        "is_calmar": is_metrics.get("calmar"),
                        "is_turnover": is_metrics.get("turnover"),
                        "is_avg_exposure": is_metrics.get("avg_exposure"),
                        "is_trades": is_metrics.get("trades"),
                        "is_win_rate": is_metrics.get("win_rate"),
                        "is_pl_ratio": is_metrics.get("pl_ratio"),
                        "oos_bars": oos_metrics.get("bars"),
                        "oos_cagr": oos_metrics.get("cagr"),
                        "oos_mdd": oos_metrics.get("mdd"),
                        "oos_sharpe": oos_metrics.get("sharpe"),
                        "oos_calmar": oos_metrics.get("calmar"),
                        "oos_turnover": oos_metrics.get("turnover"),
                        "oos_avg_exposure": oos_metrics.get("avg_exposure"),
                        "oos_trades": oos_metrics.get("trades"),
                        "oos_win_rate": oos_metrics.get("win_rate"),
                        "oos_pl_ratio": oos_metrics.get("pl_ratio"),
                    }
                )

                self._write_rows_csv(series_dir / f"{code}__{variant}__daily.csv", list(daily))
                self._write_rows_csv(fills_dir / f"{code}__{variant}__fills.csv", list(fills))
                self._write_rows_csv(trades_dir / f"{code}__{variant}__trades.csv", list(closed_trades))

                self.stdout.write(
                    f"[OK] {code} {variant} short={chosen_short} long={chosen_long} "
                    f"IS(sharpe={is_metrics.get('sharpe')}) OOS(sharpe={oos_metrics.get('sharpe')})"
                )

        self._write_rows_csv(run_dir / "summary.csv", summary_rows)
        self.stdout.write(f"Done. rows={len(summary_rows)} failed={len(failures)}")

        if failures:
            summary = ", ".join([f"{sym}({msg})" for sym, msg in failures[:5]])
            more = "" if len(failures) <= 5 else f" (+{len(failures) - 5} more)"
            raise CommandError(f"Some items failed: {summary}{more}")
