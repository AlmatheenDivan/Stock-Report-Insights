# stock_data/data_collection.py
import yfinance as yf
import pandas as pd

def get_stock_data(symbol: str, period="1mo"):
    stock = yf.Ticker(symbol)
    return stock.history(period=period)
