from django.db import models

class Stock(models.Model):
    code = models.CharField("Stock Code", max_length=20, unique=True,
                           help_text="E.g., 00700.HK (Tencent), AAPL (Apple)")
    name = models.CharField("Stock Name", max_length=100, blank=True, null=True)
    market = models.CharField("Market", max_length=10, blank=True, null=True,
                             help_text="E.g., HK (Hong Kong), US (United States)")
    is_active = models.BooleanField("Is Active", default=True)
    created_at = models.DateTimeField("Created At", auto_now_add=True)
    updated_at = models.DateTimeField("Updated At", auto_now=True)

    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"
        ordering = ['code']
        indexes = [
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return f"{self.code} {self.name or ''}"


class StockPrice(models.Model):
    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="prices",
        verbose_name="Stock"
    )
    date = models.DateField("Date")
    open = models.FloatField("Open Price")
    high = models.FloatField("High Price")
    low = models.FloatField("Low Price")
    close = models.FloatField("Close Price")
    volume = models.BigIntegerField("Volume", help_text="Unit: shares")
    adjusted_close = models.FloatField("Adjusted Close Price", blank=True, null=True)
    created_at = models.DateTimeField("Created At", auto_now_add=True)

    class Meta:
        verbose_name = "Stock Price"
        verbose_name_plural = "Stock Prices"
        unique_together = ('stock', 'date')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['stock', 'date']),
        ]

    def __str__(self):
        return f"{self.stock.code} {self.date} Close: {self.close}"


class StrategySignal(models.Model):
    class SignalType(models.TextChoices):
        BUY = 'BUY', 'Buy'
        SELL = 'SELL', 'Sell'

    stock = models.ForeignKey(
        Stock,
        on_delete=models.CASCADE,
        related_name="signals",
        verbose_name="Stock"
    )
    date = models.DateField("Signal Date")
    signal_type = models.CharField(
        "Signal Type",
        max_length=10,
        choices=SignalType.choices,
        default=SignalType.BUY
    )
    price = models.FloatField("Signal Price", help_text="Close price when signal generated")
    ma_short = models.FloatField("Short-term MA Value")
    ma_long = models.FloatField("Long-term MA Value")
    short_window = models.PositiveIntegerField("Short Window", default=5)
    long_window = models.PositiveIntegerField("Long Window", default=20)
    created_at = models.DateTimeField("Created At", auto_now_add=True)

    class Meta:
        verbose_name = "Strategy Signal"
        verbose_name_plural = "Strategy Signals"
        # Ensure unique signal for same stock, date and MA parameters
        unique_together = ('stock', 'date', 'short_window', 'long_window')
        ordering = ['-date']
        indexes = [
            models.Index(fields=['stock', 'date']),
        ]

    def __str__(self):
        return f"{self.stock.code} {self.date} {self.get_signal_type_display()}"
