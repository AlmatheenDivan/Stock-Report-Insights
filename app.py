import random
import yfinance as yf
import matplotlib.pyplot as plt
import os
import re
from collections import Counter
import pandas as pd
from flask import Flask, render_template, request, session, redirect, url_for
from datetime import datetime, timedelta
import mplfinance as mpf
import matplotlib
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from langchain_community.llms import OpenAI
from llm_utils import llm
matplotlib.use('Agg')

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "super_secret_key_123")

def cleanup_static_folder():
    static_dir = "static"
    now = datetime.now()
    for filename in os.listdir(static_dir):
        filepath = os.path.join(static_dir, filename)
        if os.path.isfile(filepath):
            file_mtime = datetime.fromtimestamp(os.path.getmtime(filepath))
            if now - file_mtime > timedelta(hours=2):
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
                    data = get_stock_data(symbol, period="1y" if wants_report else "1mo")
                    if data.empty:
                        bot_message = f"Sorry, I couldn't fetch data for **{symbol}**. Please check the symbol and try again."
                    else:
                        stock_info = yf.Ticker(symbol).info
                        latest_price = data["Close"].iloc[-1]

                        # Generate investment suggestion
                        suggestion = generate_investment_suggestion(data)

                        if wants_report:
                            report_file = generate_stock_report(symbol, data, stock_info, is_indian, suggestion)
                            bot_message = (
                                f"Here's the detailed 3-page report for **{symbol}**:<br>"
                                f"<a href='/static/{report_file}' target='_blank'>Download Report (PDF)</a><br><br>"
                                f"Investment Suggestion: <b>{suggestion}</b>"
                            )
                        elif wants_graph:
                            chart_type = "candlestick" if wants_candlestick else "bar" if wants_bar else "line"
                            image = plot_stock_chart(symbol, data, chart_type)
                            bot_message = (
                                f"Here's the {chart_type} chart for **{symbol}**:<br>"
                                f"<img src='/static/{image}' width='100%'><br>"
                                f"Latest price: **{'₹' if is_indian else '$'}{latest_price:.2f}**<br>"
                                f"Investment Suggestion: <b>{suggestion}</b>"
                            )
                        elif wants_dividend:
                            dividend = stock_info.get("dividendRate", 0)
                            bot_message = (
                                f"The dividend yield for **{symbol}** is **{dividend:.2f}%** per annum."
                                if dividend else f"**{symbol}** does not currently pay dividends."
                            )
                        elif wants_volatility:
                            volatility = data["Close"].pct_change().std() * (252 ** 0.5) * 100
                            bot_message = f"The annualized volatility for **{symbol}** is **{volatility:.2f}%**."
                        elif wants_52week:
                            high_52week = stock_info.get("fiftyTwoWeekHigh", "N/A")
                            low_52week = stock_info.get("fiftyTwoWeekLow", "N/A")
                            bot_message = f"**{symbol}** 52-week range: **{'₹' if is_indian else '$'}{low_52week} - {'₹' if is_indian else '$'}{high_52week}**."
                        elif wants_suggestion:
                            bot_message = f"Investment Suggestion for **{symbol}**: <b>{suggestion}</b>"
                        else:
                            bot_message = f"The latest price of **{symbol}** is **{'₹' if is_indian else '$'}{latest_price:.2f}**.<br>Investment Suggestion: <b>{suggestion}</b>"
                else:
                    bot_message = handle_general_questions(user_input)

                chat_history.append({"type": "user", "message": user_input})
                chat_history.append({"type": "bot", "message": bot_message})
                session["chat_history"] = chat_history
                session.modified = True

            except Exception as e:
                bot_message = f"Oops, something went wrong: {str(e)}"
                chat_history.append({"type": "bot", "message": bot_message})
                session["chat_history"] = chat_history
                session.modified = True

        cleanup_static_folder()
        return redirect(url_for("home"))

    return render_template("index.html", chat=chat_history)

@app.route("/clear", methods=["POST"])
def clear_chat():
    session.pop("chat_history", None)
    return redirect(url_for("home"))

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
    elif "thank you" in user_input_lower:
        return "you are always welcome!!!!, can i help you in any other way?"
    elif "bye" in user_input_lower:
        return "take care and you are always welcome!!!!."
    elif "yes" in user_input_lower:
        return "Ask me about any stock related questions ."
    elif "no" in user_input_lower:
        return "OK take care and you are always welcome!!!!."
    elif "volatility" in user_input_lower:
        return "Volatility is how much a stock price moves. Ask about volatility of TSLA or HDFCBANK."
    elif "how to invest" in user_input_lower:
        return "To start investing, first set clear financial goals and build an emergency fund covering 3–6 months of expenses. Open a brokerage account—use platforms like Zerodha or Groww in India, or Fidelity and Robinhood in the U.S. Begin with low-risk, diversified options like index funds or ETFs (e.g., NIFTYBEES or SPY), and invest regularly using SIPs or auto-invest features. Learn basics like diversification and compounding through sites like Investopedia or Zerodha Varsity, and read beginner books like *The Intelligent Investor*. Stay consistent, think long-term, and avoid emotional decisions."
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
        suggestion_text += "Always conduct thorough research on a company's fundamentals before investing—analyzing factors like revenue, profit growth, debt levels, valuation ratios (such as P/E and P/B), dividend history, and industry position helps you make informed, confident decisions and avoid costly mistakes."
        return suggestion_text
    else:
        return "Ask about a stock’s price, chart, report, dividend, volatility, or investment advice."

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

def get_stock_data(symbol, period="1mo"):
    try:
        stock = yf.Ticker(symbol)
        return stock.history(period=period)
    except Exception as e:
        print(f"Error fetching data: {e}")
        return pd.DataFrame()

def generate_investment_suggestion(data):
    # Simple moving average crossover for suggestion:
    # If 20-day SMA > 50-day SMA => "Yes, you can invest"
    # Else "No, better wait"
    try:
        data = data.copy()
        data["SMA20"] = data["Close"].rolling(window=20).mean()
        data["SMA50"] = data["Close"].rolling(window=50).mean()
        if data["SMA20"].iloc[-1] > data["SMA50"].iloc[-1]:
            return "Yes, you can consider investing based on current trends, GOOD LUCK!."
        else:
            return "No, it might be better to wait before investing."
    except Exception:
        return "No clear suggestion available at the moment."

def plot_stock_chart(symbol, data, chart_type="line"):
    color = "#{:06x}".format(random.randint(0, 0xFFFFFF))
    timestamp = int(datetime.now().timestamp())
    filename = f"{symbol}_{chart_type}_{timestamp}.png"
    filepath = os.path.join("static", filename)

    plt.figure(figsize=(8, 5))
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

def plot_pie_chart(symbol, stock_info):
    sectors = {
        "Technology": 0,
        "Other": 0,
    }
    sector = stock_info.get("sector", "Other")
    if sector not in sectors:
        sector = "Other"
    sectors[sector] = 48  # Pie chart with single sector for demo

    timestamp = int(datetime.now().timestamp())
    filename = f"{symbol}_pie_{timestamp}.png"
    filepath = os.path.join("static", filename)

    plt.figure(figsize=(5, 5))
    plt.pie(sectors.values(), labels=sectors.keys(), autopct='%1.1f%%', startangle=140)
    plt.title("Sector Allocation (Demo)")
    plt.savefig(filepath)
    plt.close()
    return filename

def plot_volatility_chart(symbol, data):
    returns = data["Close"].pct_change()
    volatility = returns.rolling(window=20).std() * (252**0.5) * 100  # annualized volatility %

    timestamp = int(datetime.now().timestamp())
    filename = f"{symbol}_volatility_{timestamp}.png"
    filepath = os.path.join("static", filename)

    plt.figure(figsize=(8, 5))
    plt.plot(volatility.index, volatility, color='red', linewidth=2)
    plt.title("20-Day Rolling Volatility (%)")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(filepath)
    plt.close()
    return filename

def generate_stock_report(symbol, data, stock_info, is_indian, suggestion):
    filename = f"{symbol}_report_{int(datetime.now().timestamp())}.pdf"
    filepath = os.path.join("static", filename)
    doc = SimpleDocTemplate(filepath, pagesize=letter)
    styles = getSampleStyleSheet()
    elements = []

    # Page 1: Title and Stock Metrics
    title = f"Stock Report for {symbol}"
    elements.append(Paragraph(title, styles["Title"]))
    elements.append(Spacer(1, 12))

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
        ["Sector", f"{stock_info.get('sector', 'N/A')}"],
    ]
    table = Table(table_data)
    elements.append(Paragraph("Stock Metrics", styles["Heading2"]))
    elements.append(table)
    elements.append(Spacer(1, 24))

    # Investment Suggestion
    elements.append(Paragraph("Investment Suggestion", styles["Heading2"]))
    elements.append(Paragraph(suggestion, styles["Heading1"]))
    elements.append(PageBreak())

    # Page 2: Charts (line, bar, candlestick)
    elements.append(Paragraph("Price Charts", styles["Heading3"]))
    # Line chart
    line_chart = plot_stock_chart(symbol, data, "line")
    elements.append(Image(os.path.join("static", line_chart), width=7*inch, height=5*inch))
    elements.append(Spacer(1, 12))

    # Bar chart
    bar_chart = plot_stock_chart(symbol, data, "bar")
    elements.append(Image(os.path.join("static", bar_chart), width=7*inch, height=5*inch))
    elements.append(Spacer(1, 12))

    # Candlestick chart
    candle_chart = plot_stock_chart(symbol, data, "candlestick")
    elements.append(Image(os.path.join("static", candle_chart), width=7*inch, height=5*inch))
    elements.append(PageBreak())

    # Page 3: Pie chart and Volatility chart
    elements.append(Paragraph("Sector Allocation and Volatility", styles["Heading2"]))

    # Pie chart
    pie_chart = plot_pie_chart(symbol, stock_info)
    elements.append(Image(os.path.join("static", pie_chart), width=4*inch, height=4*inch))

    # Volatility chart
    volatility_chart = plot_volatility_chart(symbol, data)
    elements.append(Image(os.path.join("static", volatility_chart), width=7*inch, height=5*inch))

    doc.build(elements)
    return filename

if __name__ == "__main__":
    if not os.path.exists("static"):
        os.makedirs("static")
    app.run(debug=True, host="0.0.0.0", port=5000)
