import random
import yfinance as yf
import matplotlib.pyplot as plt
import os
import re
import pandas as pd
from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime, timedelta
import mplfinance as mpf
import matplotlib
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch

# Use Agg backend for Matplotlib (non-GUI backend)
matplotlib.use('Agg')

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super_secret_key_123")  # Use env variable for security

# Clean up old static files (older than 1 hour)
def cleanup_static_folder():
    static_dir = "static"
    now = datetime.now()
    for filename in os.listdir(static_dir):
        filepath = os.path.join(static_dir, filename)
        if os.path.isfile(filepath):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if now - file_mtime > timedelta(hours=1):
                os.remove(filepath)

@app.route("/", methods=["GET", "POST"])
def home():
    if "chat_history" not in session:
        session["chat_history"] = []

    chat_history = session["chat_history"]

    if request.method == "POST":
        user_input = request.form.get("user_input", "").strip()
        if user_input:
            try:
                symbol, is_indian = extract_stock_symbol(user_input)
                wants_graph = any(k in user_input.lower() for k in ["graph", "chart", "plot"])
                wants_bar = "bar" in user_input.lower()
                wants_candlestick = "candlestick" in user_input.lower()
                wants_report = "report" in user_input.lower()
                wants_suggestion = any(k in user_input.lower() for k in ["suggestion", "advice", "should i", "good investment"])
                wants_dividend = "dividend" in user_input.lower()
                wants_volatility = "volatility" in user_input.lower()
                wants_52week = "52 week" in user_input.lower()

                bot_message = ""

                if symbol:
                    data = get_stock_data(symbol, period="1mo" if not wants_report else "1y")
                    if data.empty:
                        bot_message = f"Sorry, I couldn't fetch data for **{symbol}**. Please check the symbol and try again."
                    else:
                        stock_info = yf.Ticker(symbol).info
                        latest_price = data["Close"].iloc[-1]

                        if wants_report:
                            report_file = generate_stock_report(symbol, data, stock_info, is_indian)
                            bot_message = f"Here's the detailed report for **{symbol}**:<br><a href='/static/{report_file}' target='_blank'>Download Report (PDF)</a>"
                        elif wants_graph:
                            chart_type = "candlestick" if wants_candlestick else "bar" if wants_bar else "line"
                            image = plot_stock_chart(symbol, data, chart_type)
                            bot_message = f"Here's the {chart_type} chart for **{symbol}**:<br><img src='/static/{image}' width='100%'><br>Latest price: **{'₹' if is_indian else '$'}{latest_price:.2f}**"
                        elif wants_dividend:
                            dividend = stock_info.get("dividendRate", 0)
                            bot_message = f"The dividend yield for **{symbol}** is **{dividend:.2f}%** per annum." if dividend else f"**{symbol}** does not currently pay dividends."
                        elif wants_volatility:
                            volatility = data["Close"].pct_change().std() * (252 ** 0.5) * 100
                            bot_message = f"The annualized volatility for **{symbol}** is **{volatility:.2f}%**."
                        elif wants_52week:
                            high_52week = stock_info.get("fiftyTwoWeekHigh", "N/A")
                            low_52week = stock_info.get("fiftyTwoWeekLow", "N/A")
                            bot_message = f"**{symbol}** 52-week range: **{'₹' if is_indian else '$'}{low_52week} - {'₹' if is_indian else '$'}{high_52week}**."
                        elif wants_suggestion:
                            bot_message = generate_dynamic_suggestion(symbol, user_input, data, is_indian)
                        else:
                            bot_message = f"The latest price of **{symbol}** is **{'₹' if is_indian else '$'}{latest_price:.2f}**."
                else:
                    bot_message = handle_general_questions(user_input)

                chat_history.append({"type": "user", "message": user_input})
                chat_history.append({"type": "bot", "message": bot_message})
                session["chat_history"] = chat_history
                session.modified = True  # Ensure session updates

            except Exception as e:
                bot_message = f"Oops, something went wrong: {str(e)}"
                chat_history.append({"type": "bot", "message": bot_message})
                session["chat_history"] = chat_history
                session.modified = True

        # Clean up static files after each request
        cleanup_static_folder()
        return redirect(url_for("home"))

    return render_template("index.html", chat=chat_history)

@app.route("/clear", methods=["POST"])
def clear_chat():
    session.pop("chat_history", None)
    return redirect(url_for("home"))

# General user input handler with stock suggestions
def handle_general_questions(user_input):
    user_input_lower = user_input.lower()
    if any(k in user_input_lower for k in ["hi", "hello", "hey"]):
        return "Hi! I'm your one-stop stock market assistant. Ask me about prices, charts, dividends, or suggestions."
    elif "stock market" in user_input_lower:
        return "The stock market is where shares are bought and sold. Want to know about a stock like AAPL or RELIANCE?"
    elif "ipo" in user_input_lower:
        return "An IPO is when a company offers its stock to the public for the first time. Want details?"
    elif "etf" in user_input_lower:
        return "ETFs are like mutual funds that trade on exchanges. Ask about NIFTYBEES or SPY."
    elif "dividend" in user_input_lower:
        return "Dividends are payouts from a company's profits. Want to check dividend for a specific stock?"
    elif "volatility" in user_input_lower:
        return "Volatility is how much a stock price moves. Ask about volatility of TSLA or HDFCBANK."
    elif "how to invest" in user_input_lower:
        return "To start investing, open a brokerage account, research stocks/funds, and diversify."
    elif any(k in user_input_lower for k in ["suggest", "suggestion", "recommend", "good investment"]):
        us_stocks = ["AAPL", "TSLA", "GOOG", "AMZN", "MSFT"]
        indian_stocks = ["RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS"]
        suggestions = random.sample(us_stocks + indian_stocks, 3)
        suggestion_text = "Here are some stocks you might consider researching:<br>"
        for sym in suggestions:
            is_indian = sym.endswith(".NS")
            data = get_stock_data(sym, period="1mo")
            if not data.empty:
                latest_price = data["Close"].iloc[-1]
                suggestion_text += f"- **{sym}**: Latest price {'₹' if is_indian else '$'}{latest_price:.2f}<br>"
        suggestion_text += "Always research fundamentals before investing!"
        return suggestion_text
    else:
        return "Ask about a stock’s price, chart, report, dividend, volatility, or investment advice."

# Stock symbol extraction
def extract_stock_symbol(text):
    known_us_symbols = ["AAPL", "TSLA", "GOOG", "AMZN", "MSFT", "META", "NVDA", "NFLX"]
    known_indian_symbols = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL", "HINDUNILVR"]

    words = re.findall(r'\b[A-Z]{2,10}(?:\.NS)?\b', text.upper())
    symbol = None
    is_indian = False

    for word in words:
        if word.endswith(".NS"):
            symbol = word
            is_indian = True
            break
        elif word in known_us_symbols:
            symbol = word
            break
        elif word in known_indian_symbols:
            symbol = f"{word}.NS"
            is_indian = True
            break

    if not symbol:
        for sym in known_us_symbols:
            if sym.lower() in text.lower():
                symbol = sym
                break
        for sym in known_indian_symbols:
            if sym.lower() in text.lower():
                symbol = f"{sym}.NS"
                is_indian = True
                break

    return symbol, is_indian

# Fetch stock data from Yahoo Finance
def get_stock_data(symbol, period="1mo"):
    try:
        stock = yf.Ticker(symbol)
        return stock.history(period=period)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

# Generate dynamic suggestion based on trends
def generate_dynamic_suggestion(symbol, user_input, data, is_indian):
    trend = "positive" if data["Close"].iloc[-1] > data["Close"].iloc[0] else "negative"
    currency = "₹" if is_indian else "$"
    if "should i" in user_input.lower():
        return f"{symbol} is showing a {trend} trend. Latest price: {currency}{data['Close'].iloc[-1]:.2f}. Research fundamentals before investing."
    return f"{symbol} trend: {trend}. Always do your research."

# Plot stock chart with unique filename
def plot_stock_chart(symbol, data, chart_type="line"):
    color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    timestamp = int(datetime.now().timestamp())  # Unique timestamp
    filename = f"{symbol}_{chart_type}_{timestamp}.png"
    filepath = os.path.join("static", filename)

    plt.figure(figsize=(8, 5))  # Smaller figure for mobile
    if chart_type == "candlestick":
        mpf.plot(data, type='candle', style='yahoo', savefig=filepath, scale_width_adjustment=dict(candle=0.7))
    elif chart_type == "bar":
        plt.bar(data.index.strftime('%Y-%m-%d'), data["Close"], color=color)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(filepath)
        plt.close()
    else:
        plt.plot(data.index, data["Close"], color=color, linewidth=2)
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(filepath)
        plt.close()

    return filename

# Generate stock report in PDF format with news and chart
def generate_stock_report(symbol, data, stock_info, is_indian):
    filename = f"{symbol}_report_{int(datetime.now().timestamp())}.pdf"
    filepath = os.path.join("static", filename)
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Title
    title = f"Stock Report for {symbol}"
    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Spacer(1, 12))

    # Stock Metrics Table
    latest_price = data["Close"].iloc[-1]
    open_price = data["Open"].iloc[-1]
    change = latest_price - open_price
    change_percent = (change / open_price) * 100

    table_data = [
        ["Latest Price", f"{'₹' if is_indian else '$'}{latest_price:.2f}"],
        ["Opening Price", f"{'₹' if is_indian else '$'}{open_price:.2f}"],
        ["Day Change", f"{'₹' if is_indian else '$'}{change:.2f} ({change_percent:.2f}%)"],
        ["Volume", f"{stock_info.get('volume', 'N/A')}"],
        ["Market Cap", f"{stock_info.get('marketCap', 'N/A')}"],
        ["52 Week High", f"{stock_info.get('fiftyTwoWeekHigh', 'N/A')}"],
        ["52 Week Low", f"{stock_info.get('fiftyTwoWeekLow', 'N/A')}"],
    ]

    table = Table(table_data)
    elements.append(Paragraph("Stock Metrics", styles["Heading2"]))
    elements.append(table)
    elements.append(Spacer(1, 24))

    # News Section
    elements.append(Paragraph("Recent News", styles["Heading2"]))
    try:
        news_items = yf.Ticker(symbol).news[:5]
        for item in news_items:
            title = item.get("title", "N/A")
            publisher = item.get("publisher", "Unknown")
            pub_date = datetime.fromtimestamp(item.get("providerPublishTime", 0)).strftime("%Y-%m-%d")
            news_text = f"<b>{title}</b><br>Publisher: {publisher}<br>Date: {pub_date}"
            elements.append(Paragraph(news_text, styles["Normal"]))
            elements.append(Spacer(1, 12))
    except Exception as e:
        elements.append(Paragraph("Unable to fetch news at this time.", styles["Normal"]))
        elements.append(Spacer(1, 12))

    # Chart Section
    elements.append(Paragraph("Price Chart", styles["Heading2"]))
    chart_filename = plot_stock_chart(symbol, data, chart_type="candlestick")
    chart_filepath = os.path.join("static", chart_filename)
    try:
        chart_image = Image(chart_filepath, width=5*inch, height=3*inch)  # Smaller for mobile
        elements.append(chart_image)
    except Exception as e:
        elements.append(Paragraph("Unable to include chart at this time.", styles["Normal"]))

    # Build PDF
    doc.build(elements)
    return filename

# Run the Flask app
if __name__ == "__main__":
    if not os.path.exists("static"):
        os.makedirs("static")
    app.run(debug=True, host="0.0.0.0", port=5000)  # Accessible on local network