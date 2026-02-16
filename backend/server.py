from fastapi import FastAPI, APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import asyncio

# Configure logging early
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from models.stock_models import (
    Stock, WatchlistItem, PortfolioHolding, Portfolio,
    NewsItem, ScreenerRequest, ScreenerFilter, LLMInsightRequest
)
from services.mock_data import (
    get_all_stocks, generate_news_items, generate_market_overview as mock_market_overview, INDIAN_STOCKS
)
from services.scoring_engine import generate_analysis, generate_ml_prediction
from services.llm_service import generate_stock_insight, summarize_news

# Import real market data service
try:
    from services.market_data_service import (
        get_stock_quote, get_historical_data, get_market_indices,
        get_bulk_quotes, get_stock_fundamentals, is_real_data_available,
        get_available_symbols, STOCK_SYMBOL_MAP
    )
    REAL_DATA_AVAILABLE = is_real_data_available()
except ImportError:
    REAL_DATA_AVAILABLE = False

# Import WebSocket manager
try:
    from services.websocket_manager import (
        connection_manager, price_broadcaster, handle_websocket_message
    )
    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
db_name = os.environ.get('MONGO_DB_NAME', os.environ.get('DB_NAME', 'stockpulse'))
client = AsyncIOMotorClient(mongo_url)
db = client[db_name]

# Initialize Alerts Service
try:
    from services.alerts_service import init_alerts_service, get_alerts_service
    from models.alert_models import AlertCreate, AlertUpdate, AlertCondition, AlertStatus
    alerts_service = init_alerts_service(db)
    ALERTS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Alerts service not available: {e}")
    ALERTS_AVAILABLE = False
    alerts_service = None

# Import Data Extraction Pipeline
try:
    from data_extraction.pipeline.orchestrator import PipelineOrchestrator
    from data_extraction.models.extraction_models import ExtractionStatus
    EXTRACTION_PIPELINE_AVAILABLE = True
    _pipeline_orchestrator = None  # Lazy initialization
except ImportError as e:
    logger.warning(f"Data extraction pipeline not available: {e}")
    EXTRACTION_PIPELINE_AVAILABLE = False
    _pipeline_orchestrator = None

# Configuration
USE_REAL_DATA = os.environ.get('USE_REAL_DATA', 'true').lower() == 'true'

# Create the main app
app = FastAPI(title="Stock Analysis Platform API", version="1.0.0")

# Create router with /api prefix
api_router = APIRouter(prefix="/api")

# Log data source status
logger.info(f"Real data available: {REAL_DATA_AVAILABLE}")
logger.info(f"Use real data: {USE_REAL_DATA}")
logger.info(f"Data source: {'Real (Yahoo Finance)' if REAL_DATA_AVAILABLE and USE_REAL_DATA else 'Mock Data'}")

# Cache for stock data
_stock_cache = {}
_cache_timestamp = None
_real_data_cache = {}
_real_cache_timestamp = None
CACHE_TTL = 300  # 5 minutes for mock data
REAL_CACHE_TTL = 60  # 1 minute for real data


def _get_cap_category(market_cap: float) -> str:
    """Determine market cap category based on Indian market standards"""
    if market_cap >= 200000000000:  # 20,000 Cr+
        return "Large"
    elif market_cap >= 50000000000:  # 5,000 Cr+
        return "Mid"
    else:
        return "Small"


def _calculate_technicals(history: list, quote: dict) -> dict:
    """Calculate technical indicators from historical price data"""
    if not history or len(history) < 20:
        return {
            "sma_50": quote.get("current_price", 0),
            "sma_200": quote.get("current_price", 0),
            "rsi_14": 50,
            "high_52_week": quote.get("fifty_two_week_high", 0),
            "low_52_week": quote.get("fifty_two_week_low", 0),
            "volume_avg_20": quote.get("avg_volume", 0),
        }
    
    closes = [h["close"] for h in history]
    
    # Calculate SMAs
    sma_50 = sum(closes[-50:]) / min(50, len(closes)) if len(closes) >= 20 else closes[-1]
    sma_200 = sum(closes[-200:]) / min(200, len(closes)) if len(closes) >= 50 else closes[-1]
    
    # Calculate RSI (simplified)
    gains = []
    losses = []
    for i in range(1, min(15, len(closes))):
        diff = closes[-i] - closes[-i-1]
        if diff > 0:
            gains.append(diff)
        else:
            losses.append(abs(diff))
    
    avg_gain = sum(gains) / 14 if gains else 0
    avg_loss = sum(losses) / 14 if losses else 0.001
    rs = avg_gain / avg_loss if avg_loss > 0 else 100
    rsi = 100 - (100 / (1 + rs))
    
    return {
        "sma_50": round(sma_50, 2),
        "sma_200": round(sma_200, 2),
        "rsi_14": round(rsi, 2),
        "high_52_week": quote.get("fifty_two_week_high", max(closes) if closes else 0),
        "low_52_week": quote.get("fifty_two_week_low", min(closes) if closes else 0),
        "volume_avg_20": quote.get("avg_volume", 0),
        "support_level": round(min(closes[-20:]) * 0.98, 2) if len(closes) >= 20 else 0,
        "resistance_level": round(max(closes[-20:]) * 1.02, 2) if len(closes) >= 20 else 0,
    }

# Helper functions
def get_cached_stocks():
    global _stock_cache, _cache_timestamp
    now = datetime.now(timezone.utc)
    
    if _cache_timestamp is None or (now - _cache_timestamp).seconds > CACHE_TTL:
        stocks = get_all_stocks()
        _stock_cache = {s["symbol"]: s for s in stocks}
        _cache_timestamp = now
    
    return _stock_cache


# ==================== HEALTH CHECK ====================
@api_router.get("/")
async def root():
    return {"message": "Stock Analysis Platform API", "status": "healthy"}


@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


# ==================== MARKET OVERVIEW ====================
@api_router.get("/market/overview")
async def get_market_overview():
    """Get market overview including indices, breadth, and sector performance"""
    # Try real data first
    if REAL_DATA_AVAILABLE and USE_REAL_DATA:
        try:
            indices = await get_market_indices()
            if indices:
                # Merge with mock data for additional fields
                overview = mock_market_overview()
                overview.update(indices)
                return overview
        except Exception as e:
            logger.error(f"Real data failed, falling back to mock: {e}")
    
    return mock_market_overview()


# ==================== STOCKS ====================
@api_router.get("/stocks", response_model=List[Dict[str, Any]])
async def get_stocks(
    sector: Optional[str] = None,
    cap: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """Get list of stocks with optional filtering"""
    stocks = list(get_cached_stocks().values())
    
    if sector:
        stocks = [s for s in stocks if s["sector"].lower() == sector.lower()]
    if cap:
        stocks = [s for s in stocks if s["market_cap_category"].lower() == cap.lower()]
    
    # Sort by market cap
    stocks.sort(key=lambda x: x["valuation"]["market_cap"], reverse=True)
    
    return stocks[:limit]


@api_router.get("/stocks/{symbol}")
async def get_stock(symbol: str):
    """Get detailed stock data including analysis"""
    symbol = symbol.upper()
    
    # Try real data first
    if REAL_DATA_AVAILABLE and USE_REAL_DATA:
        try:
            quote = await get_stock_quote(symbol)
            history = await get_historical_data(symbol, period="3mo", interval="1d")
            fundamentals = await get_stock_fundamentals(symbol)
            
            if quote:
                # Build stock data from real quote
                stock_data = {
                    "symbol": symbol,
                    "name": quote.get("name", symbol),
                    "sector": quote.get("sector", "Unknown"),
                    "industry": quote.get("industry", "Unknown"),
                    "market_cap_category": _get_cap_category(quote.get("market_cap", 0)),
                    "current_price": quote.get("current_price", 0),
                    "price_change": quote.get("price_change", 0),
                    "price_change_percent": quote.get("price_change_percent", 0),
                    "fundamentals": fundamentals or {},
                    "valuation": {
                        "pe_ratio": quote.get("pe_ratio", 0),
                        "pb_ratio": quote.get("pb_ratio", 0),
                        "dividend_yield": quote.get("dividend_yield", 0),
                        "market_cap": quote.get("market_cap", 0),
                    },
                    "technicals": _calculate_technicals(history, quote),
                    "shareholding": {},  # Not available from Yahoo Finance
                    "price_history": history[-90:] if history else [],
                }
                
                # Generate analysis
                stock_data["analysis"] = generate_analysis(stock_data)
                stock_data["ml_prediction"] = generate_ml_prediction(stock_data)
                
                return stock_data
        except Exception as e:
            logger.error(f"Real data failed for {symbol}, falling back to mock: {e}")
    
    # Fallback to mock data
    stocks = get_cached_stocks()
    
    if symbol not in stocks:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    
    stock_data = stocks[symbol].copy()
    stock_data["analysis"] = generate_analysis(stock_data)
    stock_data["ml_prediction"] = generate_ml_prediction(stock_data)
    
    return stock_data


@api_router.get("/stocks/{symbol}/analysis")
async def get_stock_analysis(symbol: str):
    """Get detailed analysis for a stock"""
    stocks = get_cached_stocks()
    symbol = symbol.upper()
    
    if symbol not in stocks:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    
    stock_data = stocks[symbol]
    analysis = generate_analysis(stock_data)
    ml_prediction = generate_ml_prediction(stock_data)
    
    return {
        "symbol": symbol,
        "name": stock_data["name"],
        "current_price": stock_data["current_price"],
        "analysis": analysis,
        "ml_prediction": ml_prediction
    }


@api_router.post("/stocks/{symbol}/llm-insight")
async def get_llm_insight(symbol: str, request: LLMInsightRequest):
    """Get AI-powered insight for a stock"""
    stocks = get_cached_stocks()
    symbol = symbol.upper()
    
    if symbol not in stocks:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    
    stock_data = stocks[symbol].copy()
    stock_data["analysis"] = generate_analysis(stock_data)
    
    insight = await generate_stock_insight(stock_data, request.analysis_type)
    
    return {
        "symbol": symbol,
        "analysis_type": request.analysis_type,
        "insight": insight
    }


# ==================== SCREENER ====================
@api_router.post("/screener")
async def screen_stocks(request: ScreenerRequest):
    """Screen stocks based on multiple criteria"""
    stocks = list(get_cached_stocks().values())
    results = []
    
    for stock in stocks:
        passes_all = True
        fund = stock.get("fundamentals", {})
        val = stock.get("valuation", {})
        tech = stock.get("technicals", {})
        share = stock.get("shareholding", {})
        
        all_metrics = {
            **fund, **val, **tech, **share,
            "current_price": stock.get("current_price", 0),
            "price_change_percent": stock.get("price_change_percent", 0),
            "market_cap": val.get("market_cap", 0),
        }
        
        for f in request.filters:
            value = all_metrics.get(f.metric, 0)
            
            if f.operator == "gt" and not (value > f.value):
                passes_all = False
            elif f.operator == "lt" and not (value < f.value):
                passes_all = False
            elif f.operator == "gte" and not (value >= f.value):
                passes_all = False
            elif f.operator == "lte" and not (value <= f.value):
                passes_all = False
            elif f.operator == "eq" and not (value == f.value):
                passes_all = False
            elif f.operator == "between" and f.value2 is not None:
                if not (f.value <= value <= f.value2):
                    passes_all = False
            
            if not passes_all:
                break
        
        if passes_all:
            # Add analysis
            analysis = generate_analysis(stock)
            results.append({
                **stock,
                "analysis": analysis
            })
    
    # Sort results
    sort_key = request.sort_by
    reverse = request.sort_order == "desc"
    
    def get_sort_value(s):
        if sort_key == "market_cap":
            return s.get("valuation", {}).get("market_cap", 0)
        elif sort_key == "score":
            return s.get("analysis", {}).get("long_term_score", 0)
        elif sort_key in s.get("fundamentals", {}):
            return s["fundamentals"].get(sort_key, 0)
        elif sort_key in s.get("valuation", {}):
            return s["valuation"].get(sort_key, 0)
        return s.get(sort_key, 0)
    
    results.sort(key=get_sort_value, reverse=reverse)
    
    return {
        "count": len(results),
        "stocks": results[:request.limit]
    }


@api_router.get("/screener/presets")
async def get_screener_presets():
    """Get pre-built screener filters"""
    return [
        {
            "id": "quality_value",
            "name": "Quality + Value",
            "description": "High ROE, low debt, reasonable valuation",
            "filters": [
                {"metric": "roe", "operator": "gt", "value": 15},
                {"metric": "debt_to_equity", "operator": "lt", "value": 1},
                {"metric": "pe_ratio", "operator": "lt", "value": 30},
            ]
        },
        {
            "id": "high_growth",
            "name": "High Growth Momentum",
            "description": "Strong revenue growth with technical strength",
            "filters": [
                {"metric": "revenue_growth_yoy", "operator": "gt", "value": 15},
                {"metric": "rsi_14", "operator": "between", "value": 40, "value2": 70},
            ]
        },
        {
            "id": "dividend_champions",
            "name": "Dividend Champions",
            "description": "High dividend yield with sustainable payout",
            "filters": [
                {"metric": "dividend_yield", "operator": "gt", "value": 2},
                {"metric": "debt_to_equity", "operator": "lt", "value": 1.5},
            ]
        },
        {
            "id": "oversold_quality",
            "name": "Oversold Quality",
            "description": "Technically oversold but fundamentally strong",
            "filters": [
                {"metric": "rsi_14", "operator": "lt", "value": 40},
                {"metric": "roe", "operator": "gt", "value": 12},
            ]
        },
        {
            "id": "low_debt_leaders",
            "name": "Low Debt Leaders",
            "description": "Virtually debt-free companies",
            "filters": [
                {"metric": "debt_to_equity", "operator": "lt", "value": 0.3},
                {"metric": "interest_coverage", "operator": "gt", "value": 10},
            ]
        },
    ]


# ==================== WATCHLIST ====================
@api_router.get("/watchlist")
async def get_watchlist():
    """Get user's watchlist"""
    watchlist = await db.watchlist.find({}, {"_id": 0}).to_list(100)
    
    # Enrich with current data
    stocks = get_cached_stocks()
    enriched = []
    
    for item in watchlist:
        symbol = item.get("symbol", "")
        if symbol in stocks:
            stock = stocks[symbol]
            analysis = generate_analysis(stock)
            enriched.append({
                **item,
                "current_price": stock["current_price"],
                "price_change": stock["price_change"],
                "price_change_percent": stock["price_change_percent"],
                "score": analysis["long_term_score"],
                "verdict": analysis["verdict"],
            })
        else:
            enriched.append(item)
    
    return enriched


@api_router.post("/watchlist")
async def add_to_watchlist(item: WatchlistItem):
    """Add stock to watchlist"""
    # Check if already exists
    existing = await db.watchlist.find_one({"symbol": item.symbol})
    if existing:
        raise HTTPException(status_code=400, detail="Stock already in watchlist")
    
    doc = item.model_dump()
    doc["added_date"] = doc["added_date"].isoformat()
    
    # Create a copy for insertion (MongoDB modifies the original dict)
    insert_doc = {**doc}
    await db.watchlist.insert_one(insert_doc)
    
    # Return the original doc without _id
    return {"message": "Added to watchlist", "item": doc}


@api_router.delete("/watchlist/{symbol}")
async def remove_from_watchlist(symbol: str):
    """Remove stock from watchlist"""
    result = await db.watchlist.delete_one({"symbol": symbol.upper()})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Stock not in watchlist")
    return {"message": "Removed from watchlist"}


@api_router.put("/watchlist/{symbol}")
async def update_watchlist_item(symbol: str, updates: Dict[str, Any]):
    """Update watchlist item (target price, stop loss, notes)"""
    result = await db.watchlist.update_one(
        {"symbol": symbol.upper()},
        {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Stock not in watchlist")
    return {"message": "Updated successfully"}


# ==================== PORTFOLIO ====================
@api_router.get("/portfolio")
async def get_portfolio():
    """Get user's portfolio"""
    holdings = await db.portfolio.find({}, {"_id": 0}).to_list(100)
    
    if not holdings:
        return {
            "holdings": [],
            "total_invested": 0,
            "current_value": 0,
            "total_profit_loss": 0,
            "total_profit_loss_percent": 0,
            "xirr": 0,
            "sector_allocation": [],
        }
    
    stocks = get_cached_stocks()
    enriched_holdings = []
    total_invested = 0
    current_value = 0
    sector_allocation = {}
    
    for holding in holdings:
        symbol = holding.get("symbol", "")
        qty = holding.get("quantity", 0)
        avg_price = holding.get("avg_buy_price", 0)
        invested = qty * avg_price
        total_invested += invested
        
        if symbol in stocks:
            stock = stocks[symbol]
            curr_price = stock["current_price"]
            curr_val = qty * curr_price
            current_value += curr_val
            pl = curr_val - invested
            pl_pct = (pl / invested) * 100 if invested > 0 else 0
            
            sector = stock.get("sector", "Other")
            sector_allocation[sector] = sector_allocation.get(sector, 0) + curr_val
            
            enriched_holdings.append({
                **holding,
                "current_price": curr_price,
                "current_value": round(curr_val, 2),
                "profit_loss": round(pl, 2),
                "profit_loss_percent": round(pl_pct, 2),
                "sector": sector,
            })
        else:
            enriched_holdings.append(holding)
    
    total_pl = current_value - total_invested
    total_pl_pct = (total_pl / total_invested) * 100 if total_invested > 0 else 0
    
    # Convert sector allocation to list
    sector_list = [
        {"sector": k, "value": round(v, 2), "percent": round((v / current_value) * 100, 2) if current_value > 0 else 0}
        for k, v in sorted(sector_allocation.items(), key=lambda x: x[1], reverse=True)
    ]
    
    return {
        "holdings": enriched_holdings,
        "total_invested": round(total_invested, 2),
        "current_value": round(current_value, 2),
        "total_profit_loss": round(total_pl, 2),
        "total_profit_loss_percent": round(total_pl_pct, 2),
        "xirr": round(total_pl_pct * 1.2, 2),  # Simplified XIRR approximation
        "sector_allocation": sector_list,
    }


@api_router.post("/portfolio")
async def add_to_portfolio(holding: PortfolioHolding):
    """Add holding to portfolio"""
    doc = holding.model_dump()
    
    # Check if stock already exists, update quantity if so
    existing = await db.portfolio.find_one({"symbol": holding.symbol})
    if existing:
        # Average out the buy price
        total_qty = existing.get("quantity", 0) + holding.quantity
        total_value = (existing.get("quantity", 0) * existing.get("avg_buy_price", 0)) + (holding.quantity * holding.avg_buy_price)
        new_avg = total_value / total_qty if total_qty > 0 else 0
        
        await db.portfolio.update_one(
            {"symbol": holding.symbol},
            {"$set": {"quantity": total_qty, "avg_buy_price": round(new_avg, 2)}}
        )
        return {"message": "Updated existing holding"}
    
    # Create a copy for insertion (MongoDB modifies the original dict)
    insert_doc = {**doc}
    await db.portfolio.insert_one(insert_doc)
    
    # Return the original doc without _id
    return {"message": "Added to portfolio", "holding": doc}


@api_router.delete("/portfolio/{symbol}")
async def remove_from_portfolio(symbol: str):
    """Remove holding from portfolio"""
    result = await db.portfolio.delete_one({"symbol": symbol.upper()})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Holding not found")
    return {"message": "Removed from portfolio"}


@api_router.put("/portfolio/{symbol}")
async def update_portfolio_holding(symbol: str, updates: Dict[str, Any]):
    """Update portfolio holding"""
    result = await db.portfolio.update_one(
        {"symbol": symbol.upper()},
        {"$set": updates}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Holding not found")
    return {"message": "Updated successfully"}


# ==================== NEWS ====================
@api_router.get("/news")
async def get_news(
    symbol: Optional[str] = None,
    sentiment: Optional[str] = None,
    limit: int = Query(default=20, le=50)
):
    """Get market news with sentiment"""
    news = generate_news_items()
    
    if symbol:
        news = [n for n in news if symbol.upper() in n.get("related_stocks", [])]
    if sentiment:
        news = [n for n in news if n.get("sentiment", "").upper() == sentiment.upper()]
    
    return news[:limit]


@api_router.get("/news/summary")
async def get_news_summary():
    """Get AI-generated news summary"""
    news = generate_news_items()
    summary = await summarize_news(news[:10])
    
    return {
        "summary": summary,
        "news_count": len(news),
        "positive_count": len([n for n in news if n["sentiment"] == "POSITIVE"]),
        "negative_count": len([n for n in news if n["sentiment"] == "NEGATIVE"]),
        "neutral_count": len([n for n in news if n["sentiment"] == "NEUTRAL"]),
    }


# ==================== REPORTS ====================
class ReportRequest(BaseModel):
    report_type: str  # single_stock, comparison, portfolio_health
    symbols: List[str] = []


@api_router.post("/reports/generate")
async def generate_report(request: ReportRequest):
    """Generate analysis report"""
    stocks = get_cached_stocks()
    
    if request.report_type == "single_stock":
        if not request.symbols:
            raise HTTPException(status_code=400, detail="Symbol required")
        
        symbol = request.symbols[0].upper()
        if symbol not in stocks:
            raise HTTPException(status_code=404, detail="Stock not found")
        
        stock = stocks[symbol].copy()
        stock["analysis"] = generate_analysis(stock)
        stock["ml_prediction"] = generate_ml_prediction(stock)
        stock["llm_insight"] = await generate_stock_insight(stock, "full")
        
        return {
            "report_type": "single_stock",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data": stock
        }
    
    elif request.report_type == "comparison":
        if len(request.symbols) < 2:
            raise HTTPException(status_code=400, detail="At least 2 symbols required for comparison")
        
        comparison_data = []
        for sym in request.symbols[:5]:  # Max 5 stocks
            sym = sym.upper()
            if sym in stocks:
                stock = stocks[sym].copy()
                stock["analysis"] = generate_analysis(stock)
                comparison_data.append(stock)
        
        return {
            "report_type": "comparison",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data": comparison_data
        }
    
    elif request.report_type == "portfolio_health":
        portfolio = await get_portfolio()
        
        health_data = {
            "portfolio": portfolio,
            "diversification_score": len(set(h.get("sector", "") for h in portfolio.get("holdings", []))) * 10,
            "risk_assessment": "MODERATE" if portfolio.get("total_profit_loss_percent", 0) > 0 else "HIGH",
            "recommendations": [
                "Consider diversifying across more sectors",
                "Review holdings with negative returns",
                "Set stop-loss levels for high-risk positions"
            ]
        }
        
        return {
            "report_type": "portfolio_health",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "data": health_data
        }
    
    raise HTTPException(status_code=400, detail="Invalid report type")


# PDF Export endpoint
try:
    from services.pdf_service import (
        generate_single_stock_pdf, generate_comparison_pdf, 
        generate_portfolio_health_pdf, is_pdf_available
    )
    from fastapi.responses import Response
    PDF_EXPORT_AVAILABLE = is_pdf_available()
except ImportError:
    PDF_EXPORT_AVAILABLE = False


@api_router.post("/reports/generate-pdf")
async def generate_pdf_report(request: ReportRequest):
    """Generate PDF report for download"""
    if not PDF_EXPORT_AVAILABLE:
        raise HTTPException(status_code=503, detail="PDF generation not available. Install reportlab.")
    
    stocks = get_cached_stocks()
    
    try:
        if request.report_type == "single_stock":
            if not request.symbols:
                raise HTTPException(status_code=400, detail="Symbol required")
            
            symbol = request.symbols[0].upper()
            if symbol not in stocks:
                raise HTTPException(status_code=404, detail="Stock not found")
            
            stock = stocks[symbol].copy()
            stock["analysis"] = generate_analysis(stock)
            stock["ml_prediction"] = generate_ml_prediction(stock)
            stock["llm_insight"] = await generate_stock_insight(stock, "full")
            
            pdf_bytes = generate_single_stock_pdf(stock)
            filename = f"{symbol}_report_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        elif request.report_type == "comparison":
            if len(request.symbols) < 2:
                raise HTTPException(status_code=400, detail="At least 2 symbols required")
            
            comparison_data = []
            for sym in request.symbols[:5]:
                sym = sym.upper()
                if sym in stocks:
                    stock = stocks[sym].copy()
                    stock["analysis"] = generate_analysis(stock)
                    comparison_data.append(stock)
            
            pdf_bytes = generate_comparison_pdf(comparison_data)
            filename = f"comparison_{'_'.join(request.symbols[:3])}_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        elif request.report_type == "portfolio_health":
            portfolio = await get_portfolio()
            health_data = {
                "portfolio": portfolio,
                "diversification_score": len(set(h.get("sector", "") for h in portfolio.get("holdings", []))) * 10,
                "risk_assessment": "MODERATE" if portfolio.get("total_profit_loss_percent", 0) > 0 else "HIGH",
                "recommendations": [
                    "Consider diversifying across more sectors",
                    "Review holdings with negative returns",
                    "Set stop-loss levels for high-risk positions"
                ]
            }
            
            pdf_bytes = generate_portfolio_health_pdf(health_data)
            filename = f"portfolio_health_{datetime.now().strftime('%Y%m%d')}.pdf"
        
        else:
            raise HTTPException(status_code=400, detail="Invalid report type")
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except Exception as e:
        logger.error(f"PDF generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


# ==================== SECTORS ====================
@api_router.get("/sectors")
async def get_sectors():
    """Get list of sectors with stock counts"""
    stocks = list(get_cached_stocks().values())
    sectors = {}
    
    for stock in stocks:
        sector = stock.get("sector", "Other")
        if sector not in sectors:
            sectors[sector] = {"name": sector, "count": 0, "stocks": []}
        sectors[sector]["count"] += 1
        sectors[sector]["stocks"].append(stock["symbol"])
    
    return list(sectors.values())


# ==================== SEARCH ====================
@api_router.get("/search")
async def search_stocks(q: str = Query(..., min_length=1)):
    """Search stocks by symbol or name"""
    stocks = list(get_cached_stocks().values())
    q = q.upper()
    
    results = [
        {"symbol": s["symbol"], "name": s["name"], "sector": s["sector"]}
        for s in stocks
        if q in s["symbol"].upper() or q in s["name"].upper()
    ]
    
    return results[:10]


# ==================== BACKTESTING ====================
try:
    from services.backtesting_service import (
        run_backtest, get_available_strategies, get_strategy_info
    )
    from models.backtest_models import BacktestConfig, StrategyType
    BACKTEST_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Backtesting service not available: {e}")
    BACKTEST_AVAILABLE = False


@api_router.get("/backtest/strategies")
async def list_strategies():
    """Get list of available backtesting strategies"""
    if not BACKTEST_AVAILABLE:
        raise HTTPException(status_code=503, detail="Backtesting service not available")
    
    strategies = get_available_strategies()
    return [s.model_dump() for s in strategies]


@api_router.get("/backtest/strategies/{strategy_id}")
async def get_strategy(strategy_id: str):
    """Get details for a specific strategy"""
    if not BACKTEST_AVAILABLE:
        raise HTTPException(status_code=503, detail="Backtesting service not available")
    
    try:
        strategy_type = StrategyType(strategy_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    strategy = get_strategy_info(strategy_type)
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    
    return strategy.model_dump()


@api_router.post("/backtest/run")
async def run_backtest_endpoint(config: BacktestConfig):
    """Run a backtest with the specified configuration"""
    if not BACKTEST_AVAILABLE:
        raise HTTPException(status_code=503, detail="Backtesting service not available")
    
    symbol = config.symbol.upper()
    stocks = get_cached_stocks()
    
    if symbol not in stocks:
        raise HTTPException(status_code=404, detail="Stock not found")
    
    # Get price history
    try:
        if REAL_DATA_AVAILABLE and USE_REAL_DATA:
            from services.market_data_service import get_historical_data
            history = await get_historical_data(symbol, period="2y")
            if history:
                price_history = [
                    {
                        "date": h["date"].strftime("%Y-%m-%d") if hasattr(h["date"], "strftime") else h["date"],
                        "open": h.get("open", h.get("close", 0)),
                        "high": h.get("high", h.get("close", 0)),
                        "low": h.get("low", h.get("close", 0)),
                        "close": h.get("close", 0),
                        "volume": h.get("volume", 0)
                    }
                    for h in history
                ]
            else:
                price_history = None
        else:
            price_history = None
        
        # Fallback to mock data if needed
        if not price_history:
            from services.mock_data import generate_price_history
            price_history = generate_price_history(symbol, days=500)
        
        # Run the backtest
        result = await run_backtest(config, price_history)
        
        return result.model_dump()
    
    except Exception as e:
        logger.error(f"Backtest error: {e}")
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


# ==================== ALERTS ====================
@api_router.get("/alerts")
async def get_alerts(
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = Query(default=50, le=100)
):
    """Get all price alerts"""
    if not ALERTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Alerts service not available")
    
    status_enum = None
    if status:
        try:
            status_enum = AlertStatus(status)
        except ValueError:
            pass
    
    alerts = await alerts_service.get_all_alerts(status=status_enum, symbol=symbol, limit=limit)
    
    return {
        "alerts": [a.model_dump() for a in alerts],
        "total": len(alerts),
        "active": len([a for a in alerts if a.status == AlertStatus.ACTIVE]),
        "triggered": len([a for a in alerts if a.status == AlertStatus.TRIGGERED]),
    }


@api_router.post("/alerts")
async def create_alert(alert_data: AlertCreate):
    """Create a new price alert"""
    if not ALERTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Alerts service not available")
    
    # Get stock name if available
    stocks = get_cached_stocks()
    stock = stocks.get(alert_data.symbol.upper())
    stock_name = stock.get("name") if stock else None
    
    alert = await alerts_service.create_alert(alert_data, stock_name)
    
    return {"message": "Alert created", "alert": alert.model_dump()}


@api_router.get("/alerts/{alert_id}")
async def get_alert(alert_id: str):
    """Get a specific alert"""
    if not ALERTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Alerts service not available")
    
    alert = await alerts_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return alert.model_dump()


@api_router.put("/alerts/{alert_id}")
async def update_alert(alert_id: str, updates: AlertUpdate):
    """Update an existing alert"""
    if not ALERTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Alerts service not available")
    
    alert = await alerts_service.update_alert(alert_id, updates)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert updated", "alert": alert.model_dump()}


@api_router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete an alert"""
    if not ALERTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Alerts service not available")
    
    success = await alerts_service.delete_alert(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    return {"message": "Alert deleted"}


@api_router.get("/alerts/summary/stats")
async def get_alerts_summary():
    """Get alerts summary statistics"""
    if not ALERTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Alerts service not available")
    
    summary = await alerts_service.get_summary()
    return summary.model_dump()


@api_router.get("/alerts/notifications/recent")
async def get_recent_notifications(limit: int = Query(default=20, le=50)):
    """Get recent alert notifications"""
    if not ALERTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Alerts service not available")
    
    notifications = alerts_service.get_recent_notifications(limit)
    return [n.model_dump() for n in notifications]


@api_router.post("/alerts/check")
async def manually_check_alerts():
    """Manually trigger alert condition check (for testing)"""
    if not ALERTS_AVAILABLE:
        raise HTTPException(status_code=503, detail="Alerts service not available")
    
    # Get active alert symbols
    active_alerts = await alerts_service.get_all_alerts(status=AlertStatus.ACTIVE)
    symbols = list(set(a.symbol for a in active_alerts))
    
    if not symbols:
        return {"message": "No active alerts", "notifications": []}
    
    # Fetch current prices
    prices = {}
    if REAL_DATA_AVAILABLE and USE_REAL_DATA:
        try:
            quotes = await get_bulk_quotes(symbols)
            for symbol, quote in quotes.items():
                if quote:
                    prices[symbol] = {
                        "price": quote.get("current_price", 0),
                        "change_percent": quote.get("price_change_percent", 0),
                    }
        except Exception as e:
            logger.error(f"Error fetching prices for alert check: {e}")
    
    if not prices:
        # Fallback to cached stock data
        stocks = get_cached_stocks()
        for symbol in symbols:
            if symbol in stocks:
                prices[symbol] = {
                    "price": stocks[symbol].get("current_price", 0),
                    "change_percent": stocks[symbol].get("price_change_percent", 0),
                }
    
    notifications = await alerts_service.check_alert_conditions(prices)
    
    return {
        "message": f"Checked {len(active_alerts)} alerts",
        "triggered": len(notifications),
        "notifications": [n.model_dump() for n in notifications]
    }


# ==================== DATA EXTRACTION PIPELINE ====================

class ExtractionRequest(BaseModel):
    """Request model for data extraction"""
    symbols: List[str] = Field(..., description="List of stock symbols to extract")
    sources: Optional[List[str]] = Field(None, description="Data sources to use (default: all)")


class ExtractionResponse(BaseModel):
    """Response model for data extraction"""
    job_id: str
    status: str
    total_symbols: int
    processed_symbols: int
    failed_symbols: int
    progress_percent: float
    errors: List[str]
    duration_seconds: Optional[float]


@api_router.get("/extraction/status")
async def get_extraction_status():
    """Get status of data extraction pipeline and available features"""
    return {
        "pipeline_available": EXTRACTION_PIPELINE_AVAILABLE,
        "real_data_available": REAL_DATA_AVAILABLE,
        "use_real_data": USE_REAL_DATA,
        "current_data_source": "Real (Yahoo Finance)" if REAL_DATA_AVAILABLE and USE_REAL_DATA else "Mock Data",
        "available_extractors": ["yfinance", "nse_bhavcopy"] if EXTRACTION_PIPELINE_AVAILABLE else [],
        "features": {
            "field_definitions": 160,
            "deal_breakers": 10,
            "risk_penalties": 10,
            "quality_boosters": 9,
        }
    }


@api_router.post("/extraction/run", response_model=ExtractionResponse)
async def run_extraction(request: ExtractionRequest):
    """
    Run the data extraction pipeline for specified symbols.
    
    This endpoint triggers the full extraction pipeline:
    1. Raw data extraction from multiple sources
    2. Data cleaning and normalization
    3. Calculation of derived fields
    4. Technical indicator computation
    5. Validation against scoring rules
    6. Quality assessment
    """
    global _pipeline_orchestrator
    
    if not EXTRACTION_PIPELINE_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail="Data extraction pipeline not available"
        )
    
    try:
        # Initialize orchestrator if needed
        if _pipeline_orchestrator is None:
            _pipeline_orchestrator = PipelineOrchestrator(db=db)
        
        # Run the pipeline
        job = await _pipeline_orchestrator.run(
            symbols=request.symbols,
            sources=request.sources
        )
        
        # Return results
        duration = None
        if job.completed_at and job.started_at:
            duration = (job.completed_at - job.started_at).total_seconds()
        
        return ExtractionResponse(
            job_id=job.job_id,
            status=job.status.value,
            total_symbols=job.total_symbols,
            processed_symbols=job.processed_symbols,
            failed_symbols=job.failed_symbols,
            progress_percent=job.progress_pct,
            errors=job.errors[:10],  # Limit errors
            duration_seconds=duration
        )
        
    except Exception as e:
        logger.error(f"Extraction pipeline error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Extraction failed: {str(e)}"
        )


@api_router.get("/extraction/fields")
async def get_field_definitions():
    """Get all 160 field definitions with their metadata"""
    try:
        from data_extraction.config.field_definitions import FIELD_DEFINITIONS, FIELDS_BY_CATEGORY
        
        return {
            "total_fields": len(FIELD_DEFINITIONS),
            "categories": list(FIELDS_BY_CATEGORY.keys()),
            "fields_by_category": {
                cat: [
                    {
                        "name": f["name"],
                        "display_name": f["display_name"],
                        "data_type": f["data_type"],
                        "unit": f.get("unit"),
                        "is_derived": f.get("is_derived", False),
                        "priority": f.get("priority", "medium"),
                    }
                    for f in fields
                ]
                for cat, fields in FIELDS_BY_CATEGORY.items()
            }
        }
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Field definitions not available"
        )


# Include router
app.include_router(api_router)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== WEBSOCKET ====================
@app.websocket("/ws/prices")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time price updates"""
    if not WEBSOCKET_AVAILABLE:
        await websocket.close(code=1003, reason="WebSocket not available")
        return
    
    # Generate unique client ID
    client_id = f"client_{uuid.uuid4().hex[:8]}"
    
    await connection_manager.connect(websocket, client_id)
    
    try:
        while True:
            # Wait for messages from client
            data = await websocket.receive_text()
            await handle_websocket_message(websocket, client_id, data)
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        connection_manager.disconnect(client_id)


@app.websocket("/ws/prices/{client_id}")
async def websocket_with_id(websocket: WebSocket, client_id: str):
    """WebSocket endpoint with custom client ID"""
    if not WEBSOCKET_AVAILABLE:
        await websocket.close(code=1003, reason="WebSocket not available")
        return
    
    await connection_manager.connect(websocket, client_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            await handle_websocket_message(websocket, client_id, data)
    except WebSocketDisconnect:
        connection_manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        connection_manager.disconnect(client_id)


# ==================== LIFECYCLE EVENTS ====================
@app.on_event("startup")
async def startup_event():
    """Start background services on app startup"""
    logger.info("Starting StockPulse API...")
    
    if WEBSOCKET_AVAILABLE:
        await price_broadcaster.start()
        logger.info("Price broadcaster started")
    
    logger.info("StockPulse API ready!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on app shutdown"""
    logger.info("Shutting down StockPulse API...")
    
    if WEBSOCKET_AVAILABLE:
        await price_broadcaster.stop()
        logger.info("Price broadcaster stopped")
    
    client.close()
    logger.info("Database connection closed")
