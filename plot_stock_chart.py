# stock_data/plot_stock_chart.py
import matplotlib.pyplot as plt
import os
from datetime import datetime

def plot_stock_chart(symbol, stock_data):
    plt.figure(figsize=(10, 4))
    stock_data["Close"].plot(title=f"{symbol} - Last 5 Days Closing Price")
    plt.xlabel("Date")
    plt.ylabel("Price (USD)")
    filename = f"{symbol}_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
    filepath = os.path.join("static/images", filename)
    plt.tight_layout()
    plt.savefig(filepath)
    plt.close()
    return filename
