import streamlit as st
import yfinance as yf
import pandas as pd
import json
import os
import plotly.express as px

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from newsapi import NewsApiClient
from sqlalchemy import create_engine
import pandas as pd

engine = create_engine("sqlite:///portfolio.db")

def save_to_db(portfolio):
    df = pd.DataFrame(portfolio, columns=["Stock","Buy","Qty"])
    df.to_sql("portfolio", engine, if_exists="replace", index=False)

def load_from_db():
    try:
        return pd.read_sql("SELECT * FROM portfolio", engine).values.tolist()
    except:
        return []

# ---------- USER LOGIN SYSTEM ----------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.title("🔐 SmAI Finance Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username == "admin" and password == "1234":     # CHANGE LATER
            st.session_state.logged_in = True
            st.session_state.user = username
            st.success("Login Successful 🎯")
            st.experimental_rerun()
        else:
            st.error("❌ Wrong Username or Password")

    st.stop()

# ---------- STREAMLIT CONFIG ----------
st.set_page_config(page_title="AI Finance System", page_icon="💼", layout="wide")
st.title("AI Finance System - Portfolio Manager 💼")
st.write("Track Stocks | Check Profit | Live Market | AI Insights")

st.info("📌 Enter NSE symbols like RELIANCE, TCS, INFY (without .NS)")

# ---------- PORTFOLIO FILE ----------
FILE_NAME = "portfolio.json"

def save_portfolio(data):
    with open(FILE_NAME, "w") as f:
        json.dump(data, f)

def load_portfolio():
    if os.path.exists(FILE_NAME):
        with open(FILE_NAME, "r") as f:
            return json.load(f)
    return []

portfolio = load_portfolio()

# ---------- LIVE PRICE ----------
@st.cache_data(ttl=10)
def get_price(stock):
    try:
        t = yf.Ticker(stock + ".NS")
        data = t.history(period="1d")
        if not data.empty:
            return float(data["Close"].iloc[-1])
        return 0
    except:
        return 0

# ---------- ADD STOCK ----------
st.sidebar.title("📌 Add Stock")
stock = st.sidebar.text_input("Stock Symbol (e.g. RELIANCE)")
buy_price = st.sidebar.number_input("Buy Price", value=0.0)
qty = st.sidebar.number_input("Quantity", value=0)

if st.sidebar.button("Add to Portfolio"):
    if stock != "" and buy_price > 0 and qty > 0:
        portfolio.append([stock.upper(), buy_price, qty])
        save_to_db(portfolio)

        save_portfolio(portfolio)
        st.sidebar.success("Added Successfully ✔️")
    else:
        st.sidebar.error("Enter valid data ❗")

# ---------- DELETE ----------
if len(portfolio) > 0:
    delete = st.selectbox("Remove Stock", [p[0] for p in portfolio])
    if st.button("Remove"):
        portfolio = [p for p in portfolio if p[0] != delete]
        save_portfolio(portfolio)
        st.success("Removed Successfully ❌")

# ---------- PORTFOLIO TABLE ----------
st.subheader("📊 Current Portfolio")
portfolio = load_from_db()

table = []
total_inv = 0
total_curr = 0

for s, b, q in portfolio:
    price = get_price(s)
    invest = b * q
    cur = price * q
    profit = cur - invest
    pcent = (profit / invest * 100) if invest > 0 else 0

    total_inv += invest
    total_curr += cur

    table.append([s, b, round(price, 2), q, round(profit, 2), round(pcent, 2)])

if len(table) > 0:
    df = pd.DataFrame(table, columns=["Stock","Buy","Current","Qty","P/L","P%"])
    st.dataframe(df)
else:
    st.info("No stocks added yet")
st.subheader("🧨 Clear Portfolio")

if st.button("Clear Entire Portfolio"):
    portfolio = []
    save_to_db(portfolio)
    st.success("Portfolio Cleared Successfully 🗑️")

# ---------- AI SUGGESTION ----------
st.subheader("🤖 AI Buy / Sell Suggestion")

if len(portfolio) > 0:
    suggestions = []
    for s,_,_ in portfolio:
        t = yf.Ticker(s + ".NS")
        hist = t.history(period="3mo")

        if len(hist) > 0:
            hist["MA50"] = hist["Close"].rolling(50).mean()
            cur = hist["Close"].iloc[-1]
            ma50 = hist["MA50"].iloc[-1]

            if cur > ma50:
                sig = "BUY 🔥"
            elif cur < ma50:
                sig = "SELL ⚠️"
            else:
                sig = "HOLD 🙂"

            suggestions.append([s, round(cur,2), round(ma50,2), sig])

    st.table(pd.DataFrame(suggestions, columns=["Stock","Price","50 Avg","Signal"]))
# ---------- AI PORTFOLIO DOCTOR ----------
st.subheader("🧠 AI Portfolio Doctor")

if len(portfolio) == 0:
    st.info("Add some stocks to analyze your portfolio.")
else:
    risky_stocks = []
    suggestions = []

    total_value = 0
    stock_values = []

    for stock, buy, qty in portfolio:
        try:
            ticker = yf.Ticker(stock + ".NS")
            price = ticker.history(period="1d")["Close"].iloc[-1]

            value = price * qty
            total_value += value
            stock_values.append(value)

            profit_percent = ((price - buy) / buy) * 100

            if profit_percent < -10:
                risky_stocks.append(stock)

            if profit_percent < -20:
                decision = "❌ Replace"
            elif profit_percent < -10:
                decision = "⚠ Reduce"
            elif profit_percent > 20:
                decision = "👍 Hold"
            else:
                decision = "➕ Add More"

            suggestions.append({
                "Stock": stock,
                "Profit %": round(profit_percent, 2),
                "AI Suggestion": decision
            })

        except:
            continue

    st.write("### 🧮 Portfolio Health Report")

    if len(portfolio) < 3:
        st.warning("⚠ Low Diversification — Risk High!")
    else:
        st.success("✅ Diversification Looks Good")

    if len(risky_stocks) > 0:
        st.error(f"🚨 High Risk Stocks: {', '.join(risky_stocks)}")
    else:
        st.success("🛡 Portfolio Risk Under Control")

    st.write("### 🧾 AI Stock Suggestions")
    st.table(pd.DataFrame(suggestions))
# ---------- AI TREND PREDICTION PRO ----------
st.subheader("📈 AI Trend Prediction (Golden Cross / Death Cross)")

if len(portfolio) == 0:
    st.info("Add some stocks to analyze trend.")
else:
    trend_data = []

    for stock, buy, qty in portfolio:
        try:
            ticker = yf.Ticker(stock + ".NS")
            hist = ticker.history(period="6mo")

            if len(hist) > 0:
                hist["SMA50"] = hist["Close"].rolling(50).mean()
                hist["SMA200"] = hist["Close"].rolling(200).mean()

                latest_price = hist["Close"].iloc[-1]
                sma50 = hist["SMA50"].iloc[-1]
                sma200 = hist["SMA200"].iloc[-1]

                if sma50 > sma200:
                    signal = "BUY 👍 (Golden Cross – Uptrend)"
                elif sma50 < sma200:
                    signal = "SELL ❌ (Death Cross – Downtrend)"
                else:
                    signal = "HOLD 🙂 (Sideways)"

                trend_data.append([
                    stock,
                    round(latest_price, 2),
                    round(sma50, 2),
                    round(sma200, 2),
                    signal
                ])

        except:
            continue

    trend_df = pd.DataFrame(
        trend_data,
        columns=["Stock", "Current Price", "SMA 50", "SMA 200", "AI Trend Signal"]
    )

    st.table(trend_df)
# ---------- SMART AUTO ALERT SYSTEM ----------
st.subheader("🔔 Smart Auto Alerts & Warnings")

if len(portfolio) == 0:
    st.info("Add stocks to get alerts.")
else:
    alert_messages = []

    for stock, buy, qty in portfolio:
        current_price = get_price(stock)
        if buy == 0:
            continue
        
        profit_percent = ((current_price - buy) / buy) * 100

        # Profit Alert
        if profit_percent >= 10:
            alert_messages.append(f"🟢 {stock} is in strong profit (+{round(profit_percent,2)}%). Consider booking profit!")

        # Minor Loss Alert
        elif -10 < profit_percent < 0:
            alert_messages.append(f"🟡 {stock} is slightly losing ({round(profit_percent,2)}%). Monitor closely!")

        # Heavy Loss Alert
        elif profit_percent <= -10:
            alert_messages.append(f"🔴 {stock} is in heavy loss ({round(profit_percent,2)}%). Consider exit or rethink position!")

    if len(alert_messages) > 0:
        for msg in alert_messages:
            st.warning(msg)
    else:
        st.success("✅ No Alerts — Portfolio Stable")
# ---------- ADVANCED RISK SCORE ENGINE ----------
st.subheader("⚠️ Advanced Portfolio Risk Engine")

if len(portfolio) == 0:
    st.info("Add some stocks to calculate risk.")
else:
    risk_table = []
    total_risk = 0
    counted = 0

    for stock, buy, qty in portfolio:
        try:
            ticker = yf.Ticker(stock + ".NS")
            data = ticker.history(period="3mo")

            if len(data) < 10:
                continue

            # Daily returns
            data["Returns"] = data["Close"].pct_change()

            # Volatility (Risk Base)
            volatility = data["Returns"].std() * 100

            # Current Price
            current_price = data["Close"].iloc[-1]

            # Profit %
            profit_percent = ((current_price - buy) / buy) * 100
            
            # ---------- Risk Score Formula ----------
            risk_score = min(100, abs(volatility) * 2)

            if profit_percent < -10:
                risk_score += 10
            if profit_percent < -20:
                risk_score += 20

            if risk_score < 30:
                risk_level = "Low 🟢"
            elif risk_score < 60:
                risk_level = "Medium 🟡"
            else:
                risk_level = "High 🔴"

            total_risk += risk_score
            counted += 1

            risk_table.append([
                stock,
                round(volatility, 2),
                round(profit_percent, 2),
                round(risk_score, 2),
                risk_level
            ])

        except:
            continue

    if counted > 0:
        avg_risk = total_risk / counted
    else:
        avg_risk = 0

    df_risk = pd.DataFrame(
        risk_table,
        columns=["Stock", "Volatility %", "Profit %", "Risk Score", "Risk Level"]
    )

    st.table(df_risk)

    st.subheader("🛡 Portfolio Risk Summary")

    if avg_risk < 30:
        st.success(f"🟢 Portfolio Risk: LOW ({round(avg_risk,2)}) — Safe & Stable")
    elif avg_risk < 60:
        st.warning(f"🟡 Portfolio Risk: MEDIUM ({round(avg_risk,2)}) — Manage Carefully")
    else:
        st.error(f"🔴 Portfolio Risk: HIGH ({round(avg_risk,2)}) — Very Risky!")
# ---------- AI NEWS SENTIMENT ENGINE ----------
st.subheader("📰 Live Market News & AI Sentiment")

NEWS_API = "YOUR_NEWS_API_KEY"   # <---- yahan apni NewsAPI key daalna
newsapi = NewsApiClient(api_key=NEWS_API)
analyzer = SentimentIntensityAnalyzer()

try:
    news = newsapi.get_top_headlines(
        category="business",
        language="en",
        country="us",
        page_size=5
    )

    if len(news["articles"]) == 0:
        st.info("No news available right now")
    else:
        positive = negative = neutral = 0

        for article in news["articles"]:
            title = article["title"]
            desc = article["description"] if article["description"] else ""

            st.write("### 🔹", title)
            st.write(desc)
            st.write("---")

            score = analyzer.polarity_scores(title + desc)["compound"]

            if score >= 0.05:
                positive += 1
            elif score <= -0.05:
                negative += 1
            else:
                neutral += 1

        st.subheader("📊 Market Sentiment Summary")
        st.write(f"🟢 Positive News:", positive)
        st.write(f"🔴 Negative News:", negative)
        st.write(f"🟡 Neutral News:", neutral)

        st.subheader("🤖 AI Market Outlook")

        if positive > negative:
            st.success("📈 Market Looks Bullish — Good Time to Hold / Consider Buying")
        elif negative > positive:
            st.error("📉 Market Looks Bearish — Stay Cautious")
        else:
            st.warning("😐 Market Neutral — Observe & Wait")

except Exception as e:
    st.warning("⚠️ Unable to fetch news. Check Internet / API Key")
    # ---------- PORTFOLIO VISUALIZATION ----------
st.subheader("📊 Portfolio Performance Dashboard")

if len(portfolio) == 0:
    st.info("Add stocks to see charts.")
else:
    df_chart = pd.DataFrame(table, columns=["Stock","Buy","Current","Qty","P/L","P%"])

    df_chart["Investment"] = df_chart["Buy"] * df_chart["Qty"]

    # PIE CHART - Investment Distribution
    st.write("### 💰 Investment Distribution")
    fig1 = px.pie(df_chart, names="Stock", values="Investment")
    st.plotly_chart(fig1)

    # BAR CHART - Profit Loss
    st.write("### 📈 Profit / Loss Chart")
    fig2 = px.bar(df_chart, x="Stock", y="P/L", color="P/L")
    st.plotly_chart(fig2)

# ---------- FOREX DASHBOARD ----------
st.subheader("💱 Live Forex Market")

forex_pairs = ["USDINR=X", "EURUSD=X", "GBPUSD=X"]
forex_data = []

for pair in forex_pairs:
    try:
        ticker = yf.Ticker(pair)
        price = ticker.history(period="1d")["Close"].iloc[-1]
        forex_data.append([pair, round(price, 4)])
    except:
        continue

df_forex = pd.DataFrame(forex_data, columns=["Currency Pair", "Price"])
st.table(df_forex)
# ---------- CRYPTO DASHBOARD ----------
st.subheader("🪙 Live Crypto Market")

crypto_list = ["BTC-USD", "ETH-USD"]
crypto_data = []

for coin in crypto_list:
    try:
        ticker = yf.Ticker(coin)
        price = ticker.history(period="1d")["Close"].iloc[-1]
        crypto_data.append([coin, round(price, 2)])
    except:
        continue

df_crypto = pd.DataFrame(crypto_data, columns=["Crypto", "Price (USD)"])
st.table(df_crypto)
# ---------- AI AUTO DECISION ADVISOR ----------
st.subheader("🤖 AI Auto Investment Decision Advisor")

if len(portfolio) == 0:
    st.info("Add stocks to get AI advice.")
else:
    advisor_notes = []
    profit_portfolio = 0
    loss_portfolio = 0

    for stock, buy, qty in portfolio:
        try:
            price = get_price(stock)
            profit_percent = ((price - buy) / buy) * 100

            if profit_percent > 10:
                advisor_notes.append(f"🟢 {stock}: In good profit (+{round(profit_percent,2)}%). Consider partial profit booking.")
                profit_portfolio += 1

            elif 0 < profit_percent <= 10:
                advisor_notes.append(f"🟡 {stock}: Performing well. Hold for better returns.")
                profit_portfolio += 1

            elif -10 < profit_percent <= 0:
                advisor_notes.append(f"🟡 {stock}: Slight loss. HOLD & Monitor.")
                loss_portfolio += 1

            else:
                advisor_notes.append(f"🔴 {stock}: Heavy Loss ({round(profit_percent,2)}%). Review or Exit Strategy Needed!")
                loss_portfolio += 1

        except:
            continue

    st.write("### 🧾 AI Advice Summary")
    for note in advisor_notes:
        st.write(note)

    st.write("----")

    # Final Portfolio Level Decision
    st.write("### 🧠 Final AI Portfolio Decision")

    if profit_portfolio > loss_portfolio:
        st.success("📈 Portfolio Looks Strong — HOLD / Add More Selectively")
    elif loss_portfolio > profit_portfolio:
        st.error("📉 Portfolio Risky — Control Risk / Avoid New Investments")
    else:
        st.warning("😐 Balanced Portfolio — Observe Market Before Decision")
# ---------- AI GOAL PLANNER ----------
st.subheader("🎯 AI Financial Goal Planner")

goal_amount = st.number_input("Enter Your Financial Goal Amount (₹)", value=0)
monthly_invest = st.number_input("How much can you invest monthly? (₹)", value=0)
expected_return = st.slider("Expected Annual Return (%)", 5, 25, 12)

if st.button("Calculate Goal Plan"):
    if goal_amount <= 0 or monthly_invest <= 0:
        st.error("Please enter valid goal and monthly investment.")
    else:
        r = expected_return / 100 / 12
        months = 0
        value = 0

        while value < goal_amount and months < 1000*12:
            value = value * (1 + r)
            value += monthly_invest
            months += 1

        years = months // 12
        rem_months = months % 12

        st.success(f"🎉 Your goal of ₹{goal_amount} can be achieved in:")
        st.info(f"⏳ {years} Years {rem_months} Months")

        st.write(f"📈 Estimated Future Value: ₹{round(value)}")

        if years <= 5:
            st.success("🔥 Aggressive but Achievable Plan")
        elif years <= 10:
            st.warning("🙂 Balanced & Realistic Plan")
        else:
            st.error("⌛ Long Duration — Increase Monthly Investment")
# ---------- AI PORTFOLIO OPTIMIZATION ----------
st.subheader("🧠 AI Portfolio Optimization & Improvement")

if len(portfolio) == 0:
    st.info("Add stocks to get optimization suggestions.")
else:
    high_risk = []
    low_return = []
    good_performers = []

    for stock, buy, qty in portfolio:
        try:
            current = get_price(stock)
            profit_percent = ((current - buy) / buy) * 100

            if profit_percent < -10:
                high_risk.append(stock)

            elif 0 <= profit_percent < 5:
                low_return.append(stock)

            elif profit_percent >= 10:
                good_performers.append(stock)

        except:
            continue

    st.write("### 📌 AI Suggestions")

    if len(high_risk) > 0:
        st.error(f"🔴 High Risk Stocks — Consider Reducing: {', '.join(high_risk)}")

    if len(low_return) > 0:
        st.warning(f"🟡 Weak Return Stocks — Review Performance: {', '.join(low_return)}")

    if len(good_performers) > 0:
        st.success(f"🟢 Strong Performing Stocks — Consider Adding More: {', '.join(good_performers)}")

    st.write("---")

    st.write("### 🤖 Final AI Optimization Strategy")

    if len(high_risk) > len(good_performers):
        st.error("📉 Portfolio Risk High — Reduce risky positions & diversify!")
    elif len(good_performers) > len(high_risk):
        st.success("📈 Portfolio looking strong — Hold good stocks and grow smartly!")
    else:
        st.warning("😐 Balanced portfolio — small adjustments recommended.")
# ---------- PORTFOLIO STRESS TEST (CRASH SIMULATOR) ----------
st.subheader("💥 Market Crash Stress Test")

if len(portfolio) == 0:
    st.info("Add stocks to perform stress test.")
else:
    crash_levels = [-5, -10, -20, -40]
    stress_result = []

    total_current = 0
    total_buy = 0

    for stock, buy, qty in portfolio:
        try:
            price = get_price(stock)
            total_current += price * qty
            total_buy += buy * qty
        except:
            continue

    for crash in crash_levels:
        drop_factor = (100 + crash) / 100
        crashed_value = total_current * drop_factor
        loss_amount = total_current - crashed_value
        loss_percent = (loss_amount / total_current) * 100

        stress_result.append([
            f"{crash}% Market Crash",
            round(crashed_value, 2),
            f"{round(loss_percent,2)} %"
        ])

    df_stress = pd.DataFrame(
        stress_result,
        columns=["Scenario", "Portfolio Value After Crash", "Loss %"]
    )

    st.table(df_stress)

    st.subheader("🧠 AI Survival Judgment")

    if total_current <= 0:
        st.error("Portfolio data invalid.")
    else:
        if total_current - (total_current * 0.40) > total_buy * 0.6:
            st.success("🟢 Strong Portfolio — Can survive even heavy crashes!")
        elif total_current - (total_current * 0.20) > total_buy * 0.5:
            st.warning("🟡 Medium Survive Chance — Risk Manage karo!")
        else:
            st.error("🔴 Very Risky Portfolio — Crash me bade losses ho sakte hain!")
# ---------- AUTO PORTFOLIO REBALANCING AI ----------
st.subheader("🧮 Auto Portfolio Rebalancing AI")

if len(portfolio) == 0:
    st.info("Add stocks to rebalance portfolio.")
else:
    try:
        rebalance_table = []
        portfolio_value = 0

        # Calculate total current value
        for stock, buy, qty in portfolio:
            price = get_price(stock)
            value = price * qty
            portfolio_value += value

        # Ideal equal allocation
        ideal_percent = 100 / len(portfolio)

        for stock, buy, qty in portfolio:
            price = get_price(stock)
            value = price * qty
            weight = (value / portfolio_value) * 100

            difference = round(weight - ideal_percent, 2)

            if difference > 5:
                action = "🔻 Reduce Exposure"
            elif difference < -5:
                action = "🔼 Increase Allocation"
            else:
                action = "🟢 Balanced"

            rebalance_table.append([
                stock,
                round(value, 2),
                f"{round(weight,2)} %",
                f"{ideal_percent:.2f} %",
                difference,
                action
            ])

        df_rebalance = pd.DataFrame(
            rebalance_table,
            columns=["Stock", "Current Value", "Current Weight", "Ideal Weight", "Difference %", "AI Suggestion"]
        )

        st.table(df_rebalance)

        st.subheader("🤖 Final Rebalancing Advice")
        st.info("📌 Goal: Risk kam karna + Stability badhana")

        st.success("🧠 Recommendation: Over-weight stocks ko reduce karo & under-weight stocks me thoda increase karo.")

    except:
        st.error("⚠️ Unable to calculate rebalancing. Check portfolio data.")
# ---------- DOWNLOADABLE PDF REPORT ----------
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

st.subheader("📥 Download AI Portfolio PDF Report")

def generate_pdf():
    file_path = "portfolio_report.pdf"
    c = canvas.Canvas(file_path, pagesize=letter)

    c.setFont("Helvetica-Bold", 18)
    c.drawString(160, 760, "AI Portfolio Performance Report")

    c.setFont("Helvetica", 12)
    c.drawString(50, 730, "📌 Generated by SmAI Finance System")
    c.drawString(50, 710, "----------------------------------------------")

    y = 680
    c.drawString(50, y, "Stock        Buy Price     Current Price     Qty     Status")
    y -= 20

    for stock, buy, qty in portfolio:
        try:
            price = get_price(stock)
            status = "Profit" if price > buy else "Loss"

            text = f"{stock}          {round(buy,2)}             {round(price,2)}            {qty}        {status}"
            c.drawString(50, y, text)
            y -= 20
        except:
            continue

    c.drawString(50, y-10, "----------------------------------------------")
    c.drawString(50, y-30, "🤖 AI Summary:")
    c.drawString(50, y-50, "✔ Portfolio Analysis Completed")
    c.drawString(50, y-70, "✔ Risk Reviewed")
    c.drawString(50, y-90, "✔ Smart Suggestions Generated")

    c.save()
    return file_path

if st.button("Generate PDF Report"):
    pdf_file = generate_pdf()
    with open(pdf_file, "rb") as f:
        st.download_button(
            label="Download Portfolio Report 📄",
            data=f,
            file_name="AI_Portfolio_Report.pdf",
            mime="application/pdf"
        )

# ---------- TOTAL RESULT ----------
if len(portfolio) > 0:
    st.subheader("📌 Summary")
    st.write("💰 Total Investment:", round(total_inv, 2))
    st.write("📈 Current Value:", round(total_curr, 2))
    st.write("🔥 Profit / Loss:", round(total_curr-total_inv, 2))

# ---------- NEWS + SENTIMENT ----------
st.subheader("📰 Market News & Sentiment")
NEWS_API = "YOUR_NEWS_API_KEY"
newsapi = NewsApiClient(api_key=NEWS_API)
analyzer = SentimentIntensityAnalyzer()

try:
    news = newsapi.get_top_headlines(category="business", language="en", country="us")
    pos = neg = neu = 0

    for article in news["articles"][:5]:
        st.write("###", article["title"])
        score = analyzer.polarity_scores(article["title"])["compound"]

        if score >= 0.05: pos += 1
        elif score <= -0.05: neg += 1
        else: neu += 1
        st.write("---")

    st.write(f"🟢 Positive: {pos}")
    st.write(f"🔴 Negative: {neg}")
    st.write(f"🟡 Neutral: {neu}")

except:
    st.warning("News unavailable")
