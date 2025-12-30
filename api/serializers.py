from datetime import date

from rest_framework import serializers


class StockQuerySerializer(serializers.Serializer):
    code = serializers.CharField(required=False, default="AAPL")
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False, default=date.today)
    short_window = serializers.IntegerField(required=False, default=5, min_value=1, max_value=500)
    long_window = serializers.IntegerField(required=False, default=20, min_value=1, max_value=500)
    include_meta = serializers.BooleanField(required=False, default=False)
    force_refresh = serializers.BooleanField(required=False, default=False)
    include_performance = serializers.BooleanField(required=False, default=False)
    gen_confirm_bars = serializers.IntegerField(required=False, default=0, min_value=0, max_value=50)
    gen_min_cross_gap = serializers.IntegerField(required=False, default=0, min_value=0, max_value=365)

    strategy_mode = serializers.ChoiceField(required=False, default="basic", choices=["basic", "advanced"])

    regime_ma_window = serializers.IntegerField(required=False, default=200, min_value=2, max_value=1000)
    use_adx_filter = serializers.BooleanField(required=False, default=False)
    adx_window = serializers.IntegerField(required=False, default=14, min_value=2, max_value=200)
    adx_threshold = serializers.FloatField(required=False, default=20.0, min_value=0.0, max_value=100.0)

    ensemble_pairs = serializers.CharField(required=False, default="5:20,10:50,20:100,50:200", allow_blank=True)
    ensemble_ma_type = serializers.ChoiceField(required=False, default="sma", choices=["sma", "ema"])

    target_vol = serializers.FloatField(required=False, default=0.02, min_value=0.0, max_value=1.0)
    vol_window = serializers.IntegerField(required=False, default=14, min_value=2, max_value=200)
    max_leverage = serializers.FloatField(required=False, default=1.0, min_value=0.0, max_value=10.0)
    min_vol_floor = serializers.FloatField(required=False, default=1e-6, min_value=1e-12, max_value=1.0)

    use_chandelier_stop = serializers.BooleanField(required=False, default=False)
    chandelier_k = serializers.FloatField(required=False, default=3.0, min_value=0.1, max_value=10.0)
    use_vol_stop = serializers.BooleanField(required=False, default=False)
    vol_stop_atr_mult = serializers.FloatField(required=False, default=2.0, min_value=0.1, max_value=20.0)

    @staticmethod
    def _parse_ensemble_pairs(value: str) -> list[tuple[int, int]]:
        raw = (value or "").strip()
        if not raw:
            return []
        pairs: list[tuple[int, int]] = []
        for part in raw.split(","):
            token = part.strip()
            if not token:
                continue
            if ":" not in token:
                raise serializers.ValidationError("ensemble_pairs must be like '5:20,10:50'")
            left, right = token.split(":", 1)
            try:
                short_w = int(left)
                long_w = int(right)
            except ValueError as e:
                raise serializers.ValidationError("ensemble_pairs must contain integer windows") from e
            if short_w < 1 or long_w < 1:
                raise serializers.ValidationError("ensemble_pairs windows must be >= 1")
            if short_w >= long_w:
                raise serializers.ValidationError("ensemble_pairs requires short < long for each pair")
            if short_w > 2000 or long_w > 2000:
                raise serializers.ValidationError("ensemble_pairs windows must be <= 2000")
            pairs.append((short_w, long_w))

        if not pairs:
            return []
        if len(pairs) > 12:
            raise serializers.ValidationError("ensemble_pairs supports up to 12 pairs")

        out: list[tuple[int, int]] = []
        seen = set()
        for pair in pairs:
            if pair in seen:
                continue
            seen.add(pair)
            out.append(pair)
        return out

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("start_date must be <= end_date")

        short_window = attrs.get("short_window", 5)
        long_window = attrs.get("long_window", 20)
        if short_window >= long_window:
            raise serializers.ValidationError("short_window must be < long_window")

        if attrs.get("strategy_mode") == "advanced" and attrs.get("include_performance"):
            attrs["ensemble_pairs"] = self._parse_ensemble_pairs(attrs.get("ensemble_pairs", ""))
            if not attrs["ensemble_pairs"]:
                raise serializers.ValidationError("ensemble_pairs is required when strategy_mode=advanced")
        return attrs


class SignalsQuerySerializer(StockQuerySerializer):
    strategy_mode = serializers.ChoiceField(required=False, default="basic", choices=["basic"])
    filter_signal_type = serializers.ChoiceField(required=False, default="all", choices=["all", "BUY", "SELL"])
    filter_limit = serializers.IntegerField(required=False, allow_null=True, min_value=1, max_value=5000)
    filter_sort = serializers.ChoiceField(required=False, default="desc", choices=["asc", "desc"])

