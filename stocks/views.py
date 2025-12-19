from datetime import date
from pathlib import Path

from django.conf import settings
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

import pandas as pd

from .services import StockDataService, StrategyService


class StockQuerySerializer(serializers.Serializer):
    code = serializers.CharField(required=False, default="AAPL")
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False, default=date.today)
    short_window = serializers.IntegerField(required=False, default=5, min_value=1, max_value=500)
    long_window = serializers.IntegerField(required=False, default=20, min_value=1, max_value=500)
    include_meta = serializers.BooleanField(required=False, default=False)
    force_refresh = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date must be <= end_date")

        short_window = attrs.get("short_window", 5)
        long_window = attrs.get("long_window", 20)
        if short_window >= long_window:
            raise serializers.ValidationError("short_window must be < long_window")
        return attrs


class SignalsQuerySerializer(StockQuerySerializer):
    gen_confirm_bars = serializers.IntegerField(required=False, default=0, min_value=0, max_value=50)
    gen_min_cross_gap = serializers.IntegerField(required=False, default=0, min_value=0, max_value=365)

    filter_signal_type = serializers.ChoiceField(required=False, default="all", choices=["all", "BUY", "SELL"])
    filter_limit = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=5000)
    filter_sort = serializers.ChoiceField(required=False, default="desc", choices=["asc", "desc"])


class StockDataView(APIView):
    """获取股票数据及均线"""

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

        # 获取股票数据
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

        # 计算均线
        try:
            df = StrategyService.calculate_moving_averages(df, short_window, long_window)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        # 转换为前端可用的格式
        # DRF 的 JSONRenderer 默认不允许 NaN/Infinity；pandas 的 rolling 会产生 NaN，
        # 需要先把 DataFrame 转为 object 再将 NaN 转为 None（输出为 JSON null）。
        df = df.astype(object).where(pd.notnull(df), None)
        data = df.to_dict("records")
        if meta is not None:
            meta["returned_count"] = len(data)

        payload = {"data": data, "meta": meta} if include_meta else data
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
    """获取交易信号"""

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

        # 获取数据并生成信号
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
    """
    List available stock codes from CSV files under DATA_DIR.

    Returns: [{ "code": "AAPL", "label": "AAPL", "file": "AAPL_3y.csv" }, ...]
    """

    def get(self, request):
        data_dir = getattr(settings, "DATA_DIR", None)
        if not data_dir:
            return Response({"error": "DATA_DIR is not configured"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        data_dir = Path(data_dir)
        if not data_dir.exists():
            return Response({"error": f"DATA_DIR does not exist: {data_dir}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
