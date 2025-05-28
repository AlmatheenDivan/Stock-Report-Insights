import pandas as pd

# Function to preprocess stock and news data
def preprocess_data(stock_data, news_data):
    # For simplicity, summarize stock data to the last 3 rows
    stock_summary = stock_data.tail(3).to_string()  # Display last 3 rows as a summary
    
    # Collect titles from news articles (5 most recent)
    news_titles = "\n".join([article['title'] for article in news_data])
    
    return stock_summary, news_titles
