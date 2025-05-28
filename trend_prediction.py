# stock_data/trend_prediction.py
def predict_trends(stock_data, sentiment_analysis):
    if "positive" in sentiment_analysis.lower():
        prediction = "The stock is likely to rise in the short term."
    elif "negative" in sentiment_analysis.lower():
        prediction = "The stock is likely to fall in the short term."
    else:
        prediction = "The stock is likely to remain stable."
    
    return prediction
