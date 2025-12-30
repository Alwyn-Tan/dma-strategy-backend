from django.urls import path

from .views import CodesView, SignalView, StockDataView

urlpatterns = [
    path("codes/", CodesView.as_view(), name="codes"),
    path("stock-data/", StockDataView.as_view(), name="stock_data"),
    path("signals/", SignalView.as_view(), name="signals"),
]

