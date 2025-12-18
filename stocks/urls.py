from django.urls import path

from .views import SignalView, StockDataView

urlpatterns = [
    path('stock-data/', StockDataView.as_view(), name='stock_data'),
    path('signals/', SignalView.as_view(), name='signals'),
]

