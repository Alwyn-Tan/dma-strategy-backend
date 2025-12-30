from django.contrib import admin

from .models import Stock, StockPrice, StrategySignal

admin.site.register(Stock)
admin.site.register(StockPrice)
admin.site.register(StrategySignal)

