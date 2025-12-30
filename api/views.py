from pathlib import Path

import pandas as pd
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from market_data.services import StockDataService
from strategy_engine.services import StrategyService

from .serializers import SignalsQuerySerializer, StockQuerySerializer


class StockDataView(APIView):
    def get(self, request):
        params = StockQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        stock_code = params.validated_data["code"]
        start_date = params.validated_data.get("start_date")
        end_date = params.validated_data.get("end_date")
        short_window = params.validated_data["short_window"]
        long_window = params.validated_data["long_window"]
        include_meta = params.validated_data.get("include_meta", False)
        force_refresh = params.validated_data.get("force_refresh", False)
        include_performance = params.validated_data.get("include_performance", False)
        gen_confirm_bars = params.validated_data.get("gen_confirm_bars", 0)
        gen_min_cross_gap = params.validated_data.get("gen_min_cross_gap", 0)
        strategy_mode = params.validated_data.get("strategy_mode", "basic")

        try:
            df, meta = StockDataService.get_stock_data(
                stock_code,
                start_date,
                end_date,
                with_meta=True,
                force_refresh=force_refresh,
            )
        except FileNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        if df.empty:
            return Response({"error": "No data found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            df = StrategyService.calculate_moving_averages(df, short_window, long_window)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        performance = None
        if include_performance:
            try:
                perf_kwargs = {
                    "initial_capital": 100,
                    "fee_rate": 0.001,
                    "slippage_rate": 0.0005,
                    "allow_fractional": True,
                    "confirm_bars": gen_confirm_bars,
                    "min_cross_gap": gen_min_cross_gap,
                    "strategy_mode": strategy_mode,
                }
                if strategy_mode == "advanced":
                    perf_kwargs.update(
                        {
                            "regime_ma_window": params.validated_data.get("regime_ma_window", 200),
                            "use_adx_filter": params.validated_data.get("use_adx_filter", False),
                            "adx_window": params.validated_data.get("adx_window", 14),
                            "adx_threshold": params.validated_data.get("adx_threshold", 20.0),
                            "ensemble_pairs": params.validated_data.get("ensemble_pairs", []),
                            "ensemble_ma_type": params.validated_data.get("ensemble_ma_type", "sma"),
                            "target_vol": params.validated_data.get("target_vol", 0.02),
                            "vol_window": params.validated_data.get("vol_window", 14),
                            "max_leverage": params.validated_data.get("max_leverage", 1.0),
                            "min_vol_floor": params.validated_data.get("min_vol_floor", 1e-6),
                            "use_chandelier_stop": params.validated_data.get("use_chandelier_stop", False),
                            "chandelier_k": params.validated_data.get("chandelier_k", 3.0),
                            "use_vol_stop": params.validated_data.get("use_vol_stop", False),
                            "vol_stop_atr_mult": params.validated_data.get("vol_stop_atr_mult", 2.0),
                        }
                    )
                performance = StrategyService.calculate_performance(df, **perf_kwargs)
            except ValueError as e:
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        df = df.astype(object).where(pd.notnull(df), None)
        data = df.to_dict("records")
        if meta is not None:
            meta["returned_count"] = len(data)
            if include_performance:
                meta["assumptions"] = {
                    "mode": "research",
                    "fill": "next_open",
                    "initial_capital": 100,
                    "fee_rate": 0.001,
                    "slippage_rate": 0.0005,
                    "allow_fractional": True,
                    "price_adjusted": False,
                    "signal_rules": {
                        "confirm_bars": gen_confirm_bars,
                        "min_cross_gap": gen_min_cross_gap,
                    },
                }
                if strategy_mode == "advanced":
                    meta["assumptions"]["strategy"] = {
                        "strategy_mode": strategy_mode,
                        "regime": {
                            "ma_window": params.validated_data.get("regime_ma_window", 200),
                            "use_adx_filter": params.validated_data.get("use_adx_filter", False),
                            "adx_window": params.validated_data.get("adx_window", 14),
                            "adx_threshold": params.validated_data.get("adx_threshold", 20.0),
                        },
                        "ensemble": {
                            "pairs": params.validated_data.get("ensemble_pairs", []),
                            "ma_type": params.validated_data.get("ensemble_ma_type", "sma"),
                        },
                        "vol_targeting": {
                            "target_vol": params.validated_data.get("target_vol", 0.02),
                            "vol_window": params.validated_data.get("vol_window", 14),
                            "max_leverage": params.validated_data.get("max_leverage", 1.0),
                            "min_vol_floor": params.validated_data.get("min_vol_floor", 1e-6),
                        },
                        "exits": {
                            "use_chandelier_stop": params.validated_data.get("use_chandelier_stop", False),
                            "chandelier_k": params.validated_data.get("chandelier_k", 3.0),
                            "use_vol_stop": params.validated_data.get("use_vol_stop", False),
                            "vol_stop_atr_mult": params.validated_data.get("vol_stop_atr_mult", 2.0),
                        },
                    }

        if include_meta or include_performance:
            payload = {"data": data, "meta": meta}
            if include_performance:
                payload["performance"] = performance
        else:
            payload = data
        resp = Response(payload)
        if meta is not None:
            resp["X-Data-Status"] = meta.get("data_status", "")
            data_range = meta.get("data_range", {})
            resp["X-Data-Range"] = f"{data_range.get('min_date') or ''},{data_range.get('max_date') or ''}"
            resp["X-Data-Last-Updated"] = meta.get("last_modified") or ""
            refresh = meta.get("refresh", {})
            resp["X-Data-Refresh"] = refresh.get("status", "")
            resp["X-Data-Refresh-Reason"] = refresh.get("reason", "")
        return resp


class SignalView(APIView):
    def get(self, request):
        params = SignalsQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        stock_code = params.validated_data["code"]
        start_date = params.validated_data.get("start_date")
        end_date = params.validated_data.get("end_date")
        short_window = params.validated_data["short_window"]
        long_window = params.validated_data["long_window"]
        gen_confirm_bars = params.validated_data["gen_confirm_bars"]
        gen_min_cross_gap = params.validated_data["gen_min_cross_gap"]
        include_meta = params.validated_data.get("include_meta", False)
        force_refresh = params.validated_data.get("force_refresh", False)

        filter_signal_type = params.validated_data["filter_signal_type"]
        filter_limit = params.validated_data.get("filter_limit")
        filter_sort = params.validated_data["filter_sort"]

        try:
            if include_meta:
                df, data_meta = StockDataService.get_stock_data(
                    stock_code,
                    start_date,
                    end_date,
                    with_meta=True,
                    force_refresh=force_refresh,
                )
            else:
                data_meta = None
                df = StockDataService.get_stock_data(
                    stock_code,
                    start_date,
                    end_date,
                    with_meta=False,
                    force_refresh=force_refresh,
                )
        except FileNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        if df.empty:
            return Response({"error": "No data found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            df = StrategyService.calculate_moving_averages(df, short_window, long_window)
            signals = StrategyService.generate_signals(
                df,
                confirm_bars=gen_confirm_bars,
                min_cross_gap=gen_min_cross_gap,
            )
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        generated_count = len(signals)

        if filter_signal_type != "all":
            signals = [s for s in signals if s["signal_type"] == filter_signal_type]

        signals = sorted(signals, key=lambda s: s["date"], reverse=(filter_sort == "desc"))
        if filter_limit:
            signals = signals[:filter_limit]

        meta = {
            "generated_count": generated_count,
            "returned_count": len(signals),
            "params": {
                "code": stock_code,
                "start_date": start_date.isoformat() if start_date else None,
                "end_date": end_date.isoformat() if end_date else None,
                "short_window": short_window,
                "long_window": long_window,
                "gen_confirm_bars": gen_confirm_bars,
                "gen_min_cross_gap": gen_min_cross_gap,
                "filter_signal_type": filter_signal_type,
                "filter_limit": filter_limit,
                "filter_sort": filter_sort,
            },
        }
        if data_meta is not None:
            meta["data_meta"] = data_meta

        payload = {"data": signals, "meta": meta}
        return Response(payload)


class CodesView(APIView):
    def get(self, request):
        data_dir = getattr(settings, "DATA_DIR", None)
        if not data_dir:
            return Response({"error": "DATA_DIR is not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        data_dir = Path(data_dir)
        if not data_dir.exists():
            return Response(
                {"error": f"DATA_DIR does not exist: {data_dir}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        items: list[dict] = []
        for csv_path in sorted(data_dir.glob("*.csv")):
            stem = csv_path.stem
            code = stem[:-3] if stem.lower().endswith("_3y") else stem
            try:
                code = StockDataService._validate_code(code)
            except ValueError:
                continue
            items.append({"code": code, "label": code, "file": csv_path.name})

        return Response(items)
