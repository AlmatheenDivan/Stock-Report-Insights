# stock_data/report_generation.py
def generate_report(symbol, stock_data, sentiment_analysis, prediction):
    report = f"""
    Stock Report for {symbol}:
    ----------------------------
    Stock Performance (Last 5 days):
    {stock_data.tail(5)}

    Sentiment Analysis:
    {sentiment_analysis}

    Predicted Trend:
    {prediction}
    """
    return report