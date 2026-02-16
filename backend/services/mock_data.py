import random
from datetime import datetime, timedelta
from typing import List, Dict
import math

# Indian Stock Market Mock Data
INDIAN_STOCKS = [
    {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "sector": "Energy", "industry": "Oil & Gas Refining", "cap": "Large"},
    {"symbol": "TCS", "name": "Tata Consultancy Services", "sector": "IT", "industry": "IT Services", "cap": "Large"},
    {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "sector": "Financial", "industry": "Private Banks", "cap": "Large"},
    {"symbol": "INFY", "name": "Infosys Ltd", "sector": "IT", "industry": "IT Services", "cap": "Large"},
    {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "sector": "Financial", "industry": "Private Banks", "cap": "Large"},
    {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Ltd", "sector": "FMCG", "industry": "Personal Products", "cap": "Large"},
    {"symbol": "SBIN", "name": "State Bank of India", "sector": "Financial", "industry": "Public Banks", "cap": "Large"},
    {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "sector": "Telecom", "industry": "Telecom Services", "cap": "Large"},
    {"symbol": "ITC", "name": "ITC Ltd", "sector": "FMCG", "industry": "Cigarettes & Tobacco", "cap": "Large"},
    {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank", "sector": "Financial", "industry": "Private Banks", "cap": "Large"},
    {"symbol": "LT", "name": "Larsen & Toubro Ltd", "sector": "Infrastructure", "industry": "Construction", "cap": "Large"},
    {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "sector": "Financial", "industry": "Private Banks", "cap": "Large"},
    {"symbol": "ASIANPAINT", "name": "Asian Paints Ltd", "sector": "Consumer", "industry": "Paints", "cap": "Large"},
    {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd", "sector": "Auto", "industry": "Passenger Vehicles", "cap": "Large"},
    {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical", "sector": "Pharma", "industry": "Pharmaceuticals", "cap": "Large"},
    {"symbol": "TITAN", "name": "Titan Company Ltd", "sector": "Consumer", "industry": "Jewellery", "cap": "Large"},
    {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd", "sector": "Financial", "industry": "NBFC", "cap": "Large"},
    {"symbol": "WIPRO", "name": "Wipro Ltd", "sector": "IT", "industry": "IT Services", "cap": "Large"},
    {"symbol": "HCLTECH", "name": "HCL Technologies Ltd", "sector": "IT", "industry": "IT Services", "cap": "Large"},
    {"symbol": "ULTRACEMCO", "name": "UltraTech Cement Ltd", "sector": "Materials", "industry": "Cement", "cap": "Large"},
    {"symbol": "POWERGRID", "name": "Power Grid Corp", "sector": "Utilities", "industry": "Power Transmission", "cap": "Large"},
    {"symbol": "NTPC", "name": "NTPC Ltd", "sector": "Utilities", "industry": "Power Generation", "cap": "Large"},
    {"symbol": "TATASTEEL", "name": "Tata Steel Ltd", "sector": "Materials", "industry": "Steel", "cap": "Large"},
    {"symbol": "ONGC", "name": "Oil & Natural Gas Corp", "sector": "Energy", "industry": "Oil Exploration", "cap": "Large"},
    {"symbol": "JSWSTEEL", "name": "JSW Steel Ltd", "sector": "Materials", "industry": "Steel", "cap": "Large"},
    {"symbol": "TECHM", "name": "Tech Mahindra Ltd", "sector": "IT", "industry": "IT Services", "cap": "Large"},
    {"symbol": "ADANIENT", "name": "Adani Enterprises Ltd", "sector": "Conglomerate", "industry": "Diversified", "cap": "Large"},
    {"symbol": "ADANIPORTS", "name": "Adani Ports & SEZ", "sector": "Infrastructure", "industry": "Ports", "cap": "Large"},
    {"symbol": "COALINDIA", "name": "Coal India Ltd", "sector": "Energy", "industry": "Coal Mining", "cap": "Large"},
    {"symbol": "HINDALCO", "name": "Hindalco Industries", "sector": "Materials", "industry": "Aluminium", "cap": "Large"},
    {"symbol": "PIDILITIND", "name": "Pidilite Industries", "sector": "Materials", "industry": "Specialty Chemicals", "cap": "Mid"},
    {"symbol": "DABUR", "name": "Dabur India Ltd", "sector": "FMCG", "industry": "Personal Products", "cap": "Mid"},
    {"symbol": "GODREJCP", "name": "Godrej Consumer Products", "sector": "FMCG", "industry": "Personal Products", "cap": "Mid"},
    {"symbol": "HAVELLS", "name": "Havells India Ltd", "sector": "Consumer", "industry": "Electrical Equipment", "cap": "Mid"},
    {"symbol": "VOLTAS", "name": "Voltas Ltd", "sector": "Consumer", "industry": "Air Conditioners", "cap": "Mid"},
    {"symbol": "TRENT", "name": "Trent Ltd", "sector": "Consumer", "industry": "Retail", "cap": "Mid"},
    {"symbol": "POLYCAB", "name": "Polycab India Ltd", "sector": "Consumer", "industry": "Cables", "cap": "Mid"},
    {"symbol": "ZOMATO", "name": "Zomato Ltd", "sector": "Technology", "industry": "Food Delivery", "cap": "Mid"},
    {"symbol": "PAYTM", "name": "One97 Communications", "sector": "Technology", "industry": "Fintech", "cap": "Mid"},
    {"symbol": "NYKAA", "name": "FSN E-Commerce", "sector": "Technology", "industry": "E-Commerce", "cap": "Mid"},
]


def generate_price_history(base_price: float, days: int = 365) -> List[Dict]:
    """Generate realistic price history"""
    prices = []
    current_price = base_price * random.uniform(0.7, 0.9)
    
    for i in range(days):
        date = (datetime.now() - timedelta(days=days-i)).strftime("%Y-%m-%d")
        daily_return = random.gauss(0.0005, 0.02)  # Mean 0.05% daily, 2% std dev
        current_price = current_price * (1 + daily_return)
        
        high = current_price * random.uniform(1.0, 1.03)
        low = current_price * random.uniform(0.97, 1.0)
        open_price = random.uniform(low, high)
        
        prices.append({
            "date": date,
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(current_price, 2),
            "volume": random.randint(100000, 50000000)
        })
    
    return prices


def generate_fundamentals(sector: str, cap: str) -> Dict:
    """Generate realistic fundamental data based on sector with history for deal-breaker checks"""
    sector_profiles = {
        "IT": {"margin": (15, 25), "roe": (18, 35), "growth": (10, 25), "de": (0, 0.3)},
        "Financial": {"margin": (15, 30), "roe": (12, 20), "growth": (12, 22), "de": (5, 10)},
        "FMCG": {"margin": (12, 22), "roe": (20, 40), "growth": (8, 15), "de": (0, 0.5)},
        "Energy": {"margin": (8, 18), "roe": (10, 20), "growth": (5, 15), "de": (0.5, 1.5)},
        "Pharma": {"margin": (15, 25), "roe": (12, 25), "growth": (8, 18), "de": (0.1, 0.6)},
        "Auto": {"margin": (8, 15), "roe": (12, 22), "growth": (8, 20), "de": (0.2, 0.8)},
        "Materials": {"margin": (10, 20), "roe": (10, 18), "growth": (5, 15), "de": (0.5, 1.2)},
        "Infrastructure": {"margin": (8, 15), "roe": (10, 18), "growth": (10, 20), "de": (0.8, 2.0)},
        "Consumer": {"margin": (12, 22), "roe": (15, 30), "growth": (10, 20), "de": (0.1, 0.5)},
        "Telecom": {"margin": (5, 15), "roe": (5, 15), "growth": (5, 15), "de": (1.0, 2.5)},
        "Utilities": {"margin": (10, 20), "roe": (10, 15), "growth": (5, 12), "de": (1.0, 2.0)},
        "Technology": {"margin": (-10, 15), "roe": (-5, 20), "growth": (15, 50), "de": (0, 0.5)},
        "Conglomerate": {"margin": (8, 18), "roe": (10, 20), "growth": (10, 25), "de": (0.5, 1.5)},
    }
    
    profile = sector_profiles.get(sector, {"margin": (10, 20), "roe": (12, 20), "growth": (8, 15), "de": (0.3, 1.0)})
    
    revenue_base = {"Large": 50000, "Mid": 10000, "Small": 2000}[cap]
    revenue = revenue_base * random.uniform(0.5, 3.0)
    
    operating_margin = random.uniform(*profile["margin"])
    net_margin = operating_margin * random.uniform(0.5, 0.8)
    
    current_ocf = revenue * random.uniform(0.08, 0.2)
    current_fcf = revenue * random.uniform(0.05, 0.15)
    
    # Generate historical data for D3, D4, D5 deal-breaker checks
    # Revenue history (5 years) - mostly growing for healthy companies
    revenue_growth_rate = random.uniform(0.03, 0.15)
    revenue_history = []
    base_rev = revenue
    for i in range(5):
        # 90% chance of growth in historical data
        if random.random() > 0.1:
            factor = 1 / (1 + revenue_growth_rate * (5 - i))
        else:
            factor = 1 / (1 - random.uniform(0.02, 0.08) * (5 - i))
        revenue_history.append(round(base_rev * factor, 2))
    revenue_history.append(round(revenue, 2))  # Current year
    
    # OCF history (5 years) - mostly positive for healthy companies
    ocf_history = []
    for i in range(5):
        if random.random() > 0.15:  # 85% chance of positive OCF
            ocf_history.append(round(revenue_history[i] * random.uniform(0.05, 0.2), 2))
        else:
            ocf_history.append(round(-revenue_history[i] * random.uniform(0.01, 0.05), 2))
    ocf_history.append(round(current_ocf, 2))
    
    # FCF history (5 years)
    fcf_history = []
    for i in range(5):
        if random.random() > 0.2:  # 80% chance of positive FCF
            fcf_history.append(round(revenue_history[i] * random.uniform(0.03, 0.12), 2))
        else:
            fcf_history.append(round(-revenue_history[i] * random.uniform(0.01, 0.05), 2))
    fcf_history.append(round(current_fcf, 2))
    
    # Operating margin history (for R7)
    om_history = []
    base_margin = operating_margin
    for i in range(5):
        variation = random.uniform(-2, 2)
        om_history.append(round(base_margin + variation, 2))
    om_history.append(round(operating_margin, 2))
    
    return {
        "revenue_ttm": round(revenue, 2),
        "revenue_growth_yoy": round(random.uniform(*profile["growth"]), 2),
        "net_profit": round(revenue * net_margin / 100, 2),
        "eps": round(random.uniform(5, 150), 2),
        "gross_margin": round(operating_margin + random.uniform(10, 20), 2),
        "operating_margin": round(operating_margin, 2),
        "net_profit_margin": round(net_margin, 2),
        "roe": round(random.uniform(*profile["roe"]), 2),
        "roa": round(random.uniform(5, 15), 2),
        "roic": round(random.uniform(10, 25), 2),
        "debt_to_equity": round(random.uniform(*profile["de"]), 2),
        "interest_coverage": round(random.uniform(3, 20), 2),
        "free_cash_flow": round(current_fcf, 2),
        "operating_cash_flow": round(current_ocf, 2),
        "current_ratio": round(random.uniform(1.0, 3.0), 2),
        "quick_ratio": round(random.uniform(0.8, 2.5), 2),
        # Historical data for D3, D4, D5 deal-breaker checks
        "revenue_history": revenue_history,
        "operating_cash_flow_history": ocf_history,
        "free_cash_flow_history": fcf_history,
        "operating_margin_history": om_history,
        # FCF yield calculation
        "fcf_yield": round((current_fcf / revenue) * 100, 2) if revenue > 0 else 0,
        # Delivery percentage (for R9)
        "delivery_percentage": round(random.uniform(25, 65), 2),
        # Contingent liabilities as % of net worth (for R10)
        "contingent_liabilities_pct": round(random.uniform(0, 15), 2),
    }


def generate_valuation(current_price: float, eps: float, sector: str) -> Dict:
    """Generate valuation metrics"""
    sector_pe = {
        "IT": (20, 40), "Financial": (12, 25), "FMCG": (40, 70),
        "Energy": (8, 18), "Pharma": (20, 40), "Auto": (15, 30),
        "Materials": (8, 20), "Infrastructure": (15, 30), "Consumer": (30, 60),
        "Telecom": (15, 40), "Utilities": (10, 20), "Technology": (30, 100),
        "Conglomerate": (15, 35),
    }
    
    pe_range = sector_pe.get(sector, (15, 30))
    pe_ratio = random.uniform(*pe_range)
    
    return {
        "pe_ratio": round(pe_ratio, 2),
        "peg_ratio": round(random.uniform(0.5, 2.5), 2),
        "pb_ratio": round(random.uniform(1, 10), 2),
        "ev_ebitda": round(random.uniform(8, 25), 2),
        "ps_ratio": round(random.uniform(1, 10), 2),
        "dividend_yield": round(random.uniform(0, 4), 2),
        "market_cap": round(current_price * random.uniform(100, 1000) * 10000000, 2),
    }


def generate_technicals(prices: List[Dict]) -> Dict:
    """Generate technical indicators from price history"""
    if len(prices) < 200:
        return {}
    
    closes = [p["close"] for p in prices]
    current = closes[-1]
    
    sma_50 = sum(closes[-50:]) / 50
    sma_200 = sum(closes[-200:]) / 200
    
    # RSI calculation (simplified)
    gains = []
    losses = []
    for i in range(1, 15):
        change = closes[-i] - closes[-i-1]
        if change > 0:
            gains.append(change)
        else:
            losses.append(abs(change))
    
    avg_gain = sum(gains) / 14 if gains else 0
    avg_loss = sum(losses) / 14 if losses else 0.001
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    # Bollinger Bands
    bb_period = closes[-20:]
    bb_mean = sum(bb_period) / 20
    bb_std = math.sqrt(sum((x - bb_mean)**2 for x in bb_period) / 20)
    
    # 52 week high/low
    year_prices = closes[-252:] if len(closes) >= 252 else closes
    
    return {
        "sma_50": round(sma_50, 2),
        "sma_200": round(sma_200, 2),
        "rsi_14": round(rsi, 2),
        "macd": round(random.uniform(-5, 5), 2),
        "macd_signal": round(random.uniform(-3, 3), 2),
        "macd_histogram": round(random.uniform(-2, 2), 2),
        "bollinger_upper": round(bb_mean + 2 * bb_std, 2),
        "bollinger_lower": round(bb_mean - 2 * bb_std, 2),
        "bollinger_middle": round(bb_mean, 2),
        "volume_avg_20": int(sum(p["volume"] for p in prices[-20:]) / 20),
        "high_52_week": round(max(year_prices), 2),
        "low_52_week": round(min(year_prices), 2),
        "support_level": round(current * 0.95, 2),
        "resistance_level": round(current * 1.05, 2),
    }


def generate_shareholding() -> Dict:
    """Generate shareholding pattern with all required fields"""
    promoter = random.uniform(30, 75)
    fii = random.uniform(5, 35)
    dii = random.uniform(5, 25)
    public = 100 - promoter - fii - dii
    
    # Generate promoter holding change (for R4)
    promoter_change = random.uniform(-3, 3)  # Usually small changes
    
    return {
        "promoter_holding": round(promoter, 2),
        "fii_holding": round(fii, 2),
        "dii_holding": round(dii, 2),
        "public_holding": round(max(0, public), 2),
        "promoter_pledging": round(random.uniform(0, 20), 2),
        "promoter_holding_change": round(promoter_change, 2),  # For R4 penalty
    }


def generate_stock_data(stock_info: Dict) -> Dict:
    """Generate complete stock data with all fields for deal-breaker checks"""
    base_prices = {
        "RELIANCE": 2450, "TCS": 3800, "HDFCBANK": 1650, "INFY": 1550,
        "ICICIBANK": 1050, "HINDUNILVR": 2350, "SBIN": 620, "BHARTIARTL": 1450,
        "ITC": 450, "KOTAKBANK": 1750, "LT": 3400, "AXISBANK": 1100,
        "ASIANPAINT": 2900, "MARUTI": 11500, "SUNPHARMA": 1650, "TITAN": 3200,
        "BAJFINANCE": 6800, "WIPRO": 450, "HCLTECH": 1650, "ULTRACEMCO": 10500,
        "POWERGRID": 280, "NTPC": 350, "TATASTEEL": 145, "ONGC": 260,
        "JSWSTEEL": 890, "TECHM": 1450, "ADANIENT": 2800, "ADANIPORTS": 1250,
        "COALINDIA": 420, "HINDALCO": 620, "PIDILITIND": 2900, "DABUR": 520,
        "GODREJCP": 1150, "HAVELLS": 1550, "VOLTAS": 1650, "TRENT": 5800,
        "POLYCAB": 6200, "ZOMATO": 245, "PAYTM": 680, "NYKAA": 165,
    }
    
    base_price = base_prices.get(stock_info["symbol"], random.uniform(100, 5000))
    price_history = generate_price_history(base_price)
    current_price = price_history[-1]["close"]
    prev_close = price_history[-2]["close"]
    price_change = current_price - prev_close
    
    fundamentals = generate_fundamentals(stock_info["sector"], stock_info["cap"])
    technicals = generate_technicals(price_history)
    
    # Credit ratings (most are investment grade, few are lower)
    credit_ratings = ["AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-"]
    # 95% chance of investment grade rating
    credit_rating = random.choice(credit_ratings) if random.random() > 0.05 else random.choice(["BB", "B", "CCC", "D"])
    
    return {
        "symbol": stock_info["symbol"],
        "name": stock_info["name"],
        "sector": stock_info["sector"],
        "industry": stock_info["industry"],
        "market_cap_category": stock_info["cap"],
        "current_price": round(current_price, 2),
        "price_change": round(price_change, 2),
        "price_change_percent": round((price_change / prev_close) * 100, 2),
        "fundamentals": fundamentals,
        "valuation": generate_valuation(current_price, fundamentals["eps"], stock_info["sector"]),
        "technicals": technicals,
        "shareholding": generate_shareholding(),
        "price_history": price_history[-90:],  # Last 90 days
        # Fields for deal-breaker checks (D2, D6, D9)
        "stock_status": "ACTIVE",  # D6: All stocks are active by default
        "sebi_investigation": False,  # D2: No SEBI investigation by default
        "credit_rating": credit_rating,  # D9: Credit rating
        # Corporate actions for additional context
        "corporate_actions": {
            "last_dividend": round(random.uniform(0, 50), 2),
            "ex_dividend_date": (datetime.now() - timedelta(days=random.randint(30, 180))).strftime("%Y-%m-%d"),
            "upcoming_events": [],
        },
    }


def get_all_stocks() -> List[Dict]:
    """Generate all stock data"""
    return [generate_stock_data(stock) for stock in INDIAN_STOCKS]


def generate_news_items() -> List[Dict]:
    """Generate mock news items"""
    news_templates = [
        {"title": "Q3 Results: {company} reports {change}% YoY growth in net profit", "sentiment": "POSITIVE", "score": 0.75},
        {"title": "{company} announces dividend of ₹{amount} per share", "sentiment": "POSITIVE", "score": 0.65},
        {"title": "FIIs increase stake in {company} by {change}% in Q3", "sentiment": "POSITIVE", "score": 0.60},
        {"title": "{company} bags ₹{amount} crore order from government", "sentiment": "POSITIVE", "score": 0.70},
        {"title": "Analysts upgrade {company} with target price of ₹{price}", "sentiment": "POSITIVE", "score": 0.68},
        {"title": "{company} to expand capacity by {change}% over next 2 years", "sentiment": "POSITIVE", "score": 0.55},
        {"title": "{company} faces margin pressure amid rising input costs", "sentiment": "NEGATIVE", "score": -0.45},
        {"title": "Promoters of {company} reduce stake by {change}%", "sentiment": "NEGATIVE", "score": -0.55},
        {"title": "{company} quarterly results miss street estimates", "sentiment": "NEGATIVE", "score": -0.60},
        {"title": "Global headwinds impact {company} exports business", "sentiment": "NEGATIVE", "score": -0.40},
        {"title": "{company} to maintain guidance despite market volatility", "sentiment": "NEUTRAL", "score": 0.10},
        {"title": "RBI policy decision: Impact on banking stocks including {company}", "sentiment": "NEUTRAL", "score": 0.05},
    ]
    
    sources = ["Economic Times", "Moneycontrol", "Business Standard", "CNBC TV18", "Mint", "Financial Express"]
    news_items = []
    
    for i in range(25):
        template = random.choice(news_templates)
        stock = random.choice(INDIAN_STOCKS)
        days_ago = random.randint(0, 7)
        
        news_items.append({
            "id": f"news_{i}",
            "title": template["title"].format(
                company=stock["name"],
                change=random.randint(5, 30),
                amount=random.randint(5, 500),
                price=random.randint(500, 5000)
            ),
            "summary": f"Detailed analysis and market reaction for {stock['name']} in the {stock['sector']} sector.",
            "source": random.choice(sources),
            "url": f"https://example.com/news/{i}",
            "published_date": (datetime.now() - timedelta(days=days_ago)).strftime("%Y-%m-%d %H:%M"),
            "sentiment": template["sentiment"],
            "sentiment_score": template["score"],
            "related_stocks": [stock["symbol"]],
        })
    
    return sorted(news_items, key=lambda x: x["published_date"], reverse=True)


def generate_market_overview() -> Dict:
    """Generate market overview data"""
    return {
        "nifty_50": {
            "value": round(random.uniform(22000, 23500), 2),
            "change": round(random.uniform(-200, 200), 2),
            "change_percent": round(random.uniform(-1, 1), 2),
        },
        "sensex": {
            "value": round(random.uniform(72000, 77000), 2),
            "change": round(random.uniform(-500, 500), 2),
            "change_percent": round(random.uniform(-1, 1), 2),
        },
        "nifty_bank": {
            "value": round(random.uniform(48000, 52000), 2),
            "change": round(random.uniform(-300, 300), 2),
            "change_percent": round(random.uniform(-1.5, 1.5), 2),
        },
        "india_vix": {
            "value": round(random.uniform(12, 20), 2),
            "change": round(random.uniform(-2, 2), 2),
            "change_percent": round(random.uniform(-10, 10), 2),
        },
        "market_breadth": {
            "advances": random.randint(800, 1500),
            "declines": random.randint(500, 1200),
            "unchanged": random.randint(50, 150),
        },
        "fii_dii": {
            "fii_buy": round(random.uniform(5000, 15000), 2),
            "fii_sell": round(random.uniform(5000, 15000), 2),
            "dii_buy": round(random.uniform(3000, 10000), 2),
            "dii_sell": round(random.uniform(3000, 10000), 2),
        },
        "sector_performance": [
            {"sector": "IT", "change_percent": round(random.uniform(-2, 3), 2)},
            {"sector": "Banking", "change_percent": round(random.uniform(-2, 3), 2)},
            {"sector": "Pharma", "change_percent": round(random.uniform(-2, 3), 2)},
            {"sector": "Auto", "change_percent": round(random.uniform(-2, 3), 2)},
            {"sector": "FMCG", "change_percent": round(random.uniform(-2, 3), 2)},
            {"sector": "Metal", "change_percent": round(random.uniform(-3, 4), 2)},
            {"sector": "Realty", "change_percent": round(random.uniform(-3, 4), 2)},
            {"sector": "Energy", "change_percent": round(random.uniform(-2, 3), 2)},
        ],
    }
