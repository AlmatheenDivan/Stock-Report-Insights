import requests

# Function to get financial news using NewsAPI
def get_financial_news():
    url = "https://newsapi.org/v2/everything?q=stock+market&apiKey=YOUR_NEWSAPI_KEY"  # Replace with your API key
    response = requests.get(url)
    news_data = response.json()
    return news_data['articles'][:5]  # Get top 5 news articles
