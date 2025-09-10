import os
import pandas as pd
import logging
from .models import Stock, StockPrice, StrategySignal
from alpha_vantage.timeseries import TimeSeries

logger = logging.getLogger(__name__)
ALPHAVANTAGE_API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")

class StockDataService:

class StrategyService:


