from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

import pandas as pd

from .services import StockDataService, StrategyService


class StockQuerySerializer(serializers.Serializer):
    code = serializers.CharField(required=False, default="AAPL")
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    short_window = serializers.IntegerField(required=False, default=5, min_value=1, max_value=500)
    long_window = serializers.IntegerField(required=False, default=20, min_value=1, max_value=500)

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

        # 获取股票数据
        try:
            df = StockDataService.get_stock_data(stock_code, start_date, end_date)
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
        return Response(data)


class SignalView(APIView):
    """获取交易信号"""

    def get(self, request):
        params = StockQuerySerializer(data=request.query_params)
        params.is_valid(raise_exception=True)
        stock_code = params.validated_data["code"]
        start_date = params.validated_data.get("start_date")
        end_date = params.validated_data.get("end_date")
        short_window = params.validated_data["short_window"]
        long_window = params.validated_data["long_window"]

        # 获取数据并生成信号
        try:
            df = StockDataService.get_stock_data(stock_code, start_date, end_date)
        except FileNotFoundError as e:
            return Response({"error": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        if df.empty:
            return Response({"error": "No data found"}, status=status.HTTP_404_NOT_FOUND)

        try:
            df = StrategyService.calculate_moving_averages(df, short_window, long_window)
            signals = StrategyService.generate_signals(df)
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(signals)
