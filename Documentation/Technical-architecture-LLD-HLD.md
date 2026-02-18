# StockPulse - Technical Architecture Document
 
> **Version**: 1.0
> **Last Updated**: February 18, 2026
> **Document Type**: High-Level Design (HLD) + Low-Level Design (LLD)
> **Project**: StockPulse - Indian Stock Market Analysis Platform
 
---
 
## Table of Contents
 
1. [Architecture Vision](#1-architecture-vision)
2. [High-Level Design (HLD)](#2-high-level-design-hld)
3. [Low-Level Design (LLD)](#3-low-level-design-lld)
4. [Database Design](#4-database-design)
5. [Data Pipeline Design](#5-data-pipeline-design)
6. [ML Pipeline Design](#6-ml-pipeline-design)
7. [LLM Integration](#7-llm-integration)
8. [Infrastructure & Deployment](#8-infrastructure--deployment)
9. [Monitoring & Logging](#9-monitoring--logging)
10. [Technology Stack Recommendations](#10-technology-stack-recommendations)
11. [Implementation Plan](#11-implementation-plan)
 
---
 
## 1. Architecture Vision
 
### 1.1 Design Principles
 
| Principle | Application |
|-----------|-------------|
| **Modularity** | Each service is independently deployable and testable |
| **Data-First** | All decisions flow from reliable, fresh, validated data |
| **Graceful Degradation** | System works with partial data (mock fallback) |
| **Async-First** | Non-blocking I/O for all external calls |
| **Single Source of Truth** | MongoDB as canonical data store |
| **Observability** | Every component emits structured logs and metrics |
 
### 1.2 System Context
 
```
                    ┌──────────────┐
                    │   User       │
                    │  (Browser)   │
                    └──────┬───────┘
                           │ HTTPS
                           ▼
                    ┌──────────────┐
                    │   Nginx      │
                    │  (Reverse    │
                    │   Proxy)     │
                    └──────┬───────┘
                     ┌─────┴─────┐
                     ▼           ▼
              ┌────────────┐  ┌────────────┐
              │  Frontend   │  │  Backend    │
              │  React SPA  │  │  FastAPI    │
              │  (Static)   │  │  (API)      │
              └────────────┘  └──────┬───────┘
                                     │
                    ┌────────────────┼────────────────┐
                    ▼                ▼                ▼
             ┌────────────┐  ┌────────────┐  ┌────────────┐
             │  MongoDB    │  │  Redis      │  │  External   │
             │  (Data)     │  │  (Cache)    │  │  APIs       │
             └────────────┘  └────────────┘  └────────────┘
```
 
---
 
## 2. High-Level Design (HLD)
 
### 2.1 Complete System Architecture
 
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CLIENT LAYER                                      │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    React 19 SPA (Port 3000)                           │  │
│  │                                                                       │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │  │
│  │  │Dashboard │ │Analyzer  │ │Screener  │ │Watchlist │ │Portfolio │  │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐              │  │
│  │  │News Hub  │ │Reports   │ │Backtest  │ │Alerts    │              │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘              │  │
│  │                                                                       │  │
│  │  Transport: Axios (REST) + WebSocket (Real-time)                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
                          ┌────────▼────────┐
                          │  Nginx / Caddy   │
                          │  (Reverse Proxy)  │
                          │  TLS Termination  │
                          └────────┬─────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                           API GATEWAY LAYER                                 │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                  FastAPI Application (Port 8000)                      │  │
│  │                                                                       │  │
│  │  Middleware: CORS │ Auth (JWT) │ Rate Limit │ Logging │ Compression  │  │
│  │                                                                       │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐     │  │
│  │  │ REST Router      │  │ WebSocket       │  │ Background      │     │  │
│  │  │ /api/v1/*        │  │ /ws/prices      │  │ Tasks           │     │  │
│  │  │ 20+ endpoints    │  │ Real-time feed  │  │ APScheduler     │     │  │
│  │  └────────┬─────────┘  └────────┬────────┘  └────────┬────────┘     │  │
│  └───────────┼─────────────────────┼─────────────────────┼──────────────┘  │
└──────────────┼─────────────────────┼─────────────────────┼──────────────────┘
               │                     │                     │
┌──────────────▼─────────────────────▼─────────────────────▼──────────────────┐
│                           SERVICE LAYER                                     │
│                                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                  │
│  │ Scoring       │  │ Market Data   │  │ Alert         │                  │
│  │ Engine        │  │ Service       │  │ Service       │                  │
│  │               │  │               │  │               │                  │
│  │ D1-D10        │  │ Real-time     │  │ 5 conditions  │                  │
│  │ R1-R10        │  │ Historical    │  │ Background    │                  │
│  │ Q1-Q9         │  │ Fundamentals  │  │ checker       │                  │
│  │ ML Adjust     │  │               │  │               │                  │
│  └───────────────┘  └───────────────┘  └───────────────┘                  │
│                                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                  │
│  │ LLM           │  │ Backtesting   │  │ PDF           │                  │
│  │ Service       │  │ Service       │  │ Service       │                  │
│  │               │  │               │  │               │                  │
│  │ GPT-4o        │  │ 5 strategies  │  │ ReportLab     │                  │
│  │ 4 insight     │  │ Trade sim     │  │ 3 report      │                  │
│  │ types         │  │ Metrics       │  │ types         │                  │
│  └───────────────┘  └───────────────┘  └───────────────┘                  │
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                    Data Extraction Pipeline                           │  │
│  │                                                                       │  │
│  │  Extractors ──> Processors ──> Validators ──> Storage                │  │
│  │  (yfinance,     (cleaner,      (quality,      (MongoDB)             │  │
│  │   NSE Bhavcopy,  calculator,    confidence)                          │  │
│  │   BSE API)       technical)                                          │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────────┐
│                           DATA LAYER                                        │
│                                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐                  │
│  │ MongoDB       │  │ Redis         │  │ External      │                  │
│  │               │  │               │  │ APIs          │                  │
│  │ - stocks      │  │ - price cache │  │               │                  │
│  │ - watchlists  │  │ - session     │  │ - yfinance    │                  │
│  │ - portfolios  │  │ - rate limits │  │ - NSE/BSE     │                  │
│  │ - alerts      │  │ - job queue   │  │ - Upstox      │                  │
│  │ - extractions │  │               │  │ - Emergent    │                  │
│  │ - time_series │  │               │  │ - NewsAPI     │                  │
│  └───────────────┘  └───────────────┘  └───────────────┘                  │
└─────────────────────────────────────────────────────────────────────────────┘
```
 
### 2.2 Data Flow Diagram
 
```
                    ┌──────────────────────────────┐
                    │     External Data Sources     │
                    │                              │
                    │  NSE  BSE  yfinance  News    │
                    └──────────┬───────────────────┘
                               │
                    ┌──────────▼───────────────────┐
                    │     Data Extraction Layer     │
                    │                              │
                    │  Extractors → Processors     │
                    │  → Validators → Storage      │
                    └──────────┬───────────────────┘
                               │
                    ┌──────────▼───────────────────┐
                    │     MongoDB (Raw Store)       │
                    │                              │
                    │  stocks_raw, prices_daily,   │
                    │  fundamentals, shareholding   │
                    └──────────┬───────────────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
    ┌─────────▼──────┐ ┌──────▼──────┐ ┌───────▼─────┐
    │  Scoring       │ │  ML Pipeline │ │  LLM        │
    │  Engine        │ │             │ │  Service     │
    │                │ │  Features   │ │             │
    │  D/R/Q Rules   │ │  Training   │ │  GPT-4o     │
    │  Confidence    │ │  Inference  │ │  Insights   │
    └─────────┬──────┘ └──────┬──────┘ └───────┬─────┘
              │                │                │
              └────────────────┼────────────────┘
                               │
                    ┌──────────▼───────────────────┐
                    │     Analysis Results Store    │
                    │                              │
                    │  scores, verdicts, insights  │
                    │  predictions, checklists     │
                    └──────────┬───────────────────┘
                               │
                    ┌──────────▼───────────────────┐
                    │     API Layer (FastAPI)       │
                    │                              │
                    │  REST + WebSocket endpoints  │
                    └──────────┬───────────────────┘
                               │
                    ┌──────────▼───────────────────┐
                    │     Frontend (React)          │
                    │                              │
                    │  Dashboard, Analyzer, etc.   │
                    └──────────────────────────────┘
```
 
### 2.3 Component Interaction Matrix
 
| Producer \ Consumer | Scoring Engine | Alert Service | LLM Service | Backtest | Frontend |
|---------------------|---------------|---------------|-------------|----------|----------|
| **Market Data** | Provides fundamentals + technicals | Provides current prices | Provides context data | Provides price history | Provides real-time prices |
| **Scoring Engine** | - | Score-based alerts | Score for explanation | - | Displays scores |
| **Data Extraction** | Raw data for scoring | - | - | Historical data | Pipeline status |
| **MongoDB** | Reads/writes analysis | Reads/writes alerts | - | Reads historical | Reads all data |
| **WebSocket** | - | Triggers alerts | - | - | Real-time updates |
 
---
 
## 3. Low-Level Design (LLD)
 
### 3.1 Backend Module Architecture
 
```
backend/
├── server.py                          # Application entry point
│   ├── create_app()                   # FastAPI factory
│   ├── register_middleware()          # CORS, auth, logging
│   ├── register_routes()             # Router mounting
│   └── lifespan()                    # Startup/shutdown events
│
├── routers/                           # [RECOMMENDED: Split from server.py]
│   ├── market.py                      # /api/v1/market/*
│   ├── stocks.py                      # /api/v1/stocks/*
│   ├── screener.py                    # /api/v1/screener/*
│   ├── watchlist.py                   # /api/v1/watchlist/*
│   ├── portfolio.py                   # /api/v1/portfolio/*
│   ├── news.py                        # /api/v1/news/*
│   ├── reports.py                     # /api/v1/reports/*
│   ├── backtest.py                    # /api/v1/backtest/*
│   ├── alerts.py                      # /api/v1/alerts/*
│   └── extraction.py                  # /api/v1/extraction/*
│
├── services/                          # Business logic
│   ├── scoring_engine.py             # Score calculation
│   ├── market_data_service.py        # External data fetching
│   ├── alerts_service.py             # Alert management
│   ├── llm_service.py                # LLM integration
│   ├── backtesting_service.py        # Strategy backtesting
│   ├── websocket_manager.py          # WebSocket connections
│   ├── pdf_service.py                # Report generation
│   ├── mock_data.py                  # Mock data generation
│   ├── notification_service.py       # [NEW: Email/SMS/Push]
│   ├── auth_service.py               # [NEW: Authentication]
│   └── cache_service.py              # [NEW: Redis cache]
│
├── data_extraction/                   # Data pipeline
│   ├── config/
│   ├── extractors/
│   ├── processors/
│   ├── pipeline/
│   ├── quality/
│   ├── storage/
│   └── models/
│
├── models/                            # Pydantic schemas
│   ├── stock_models.py
│   ├── alert_models.py
│   ├── backtest_models.py
│   ├── user_models.py                # [NEW: User/Auth]
│   └── common.py                     # [NEW: Shared types]
│
├── middleware/                         # [NEW: Custom middleware]
│   ├── auth.py                        # JWT validation
│   ├── rate_limit.py                  # Request throttling
│   └── logging.py                     # Request/response logging
│
├── config/                            # [NEW: Configuration]
│   ├── settings.py                    # Pydantic Settings
│   └── constants.py                   # Application constants
│
└── tests/                             # Test suite
    ├── unit/
    ├── integration/
    └── conftest.py
```
 
### 3.2 Scoring Engine - Detailed Flow
 
```
Input: stock_symbol (str)
                │
                ▼
┌──────────────────────────────┐
│  1. Fetch Stock Data          │
│                              │
│  fundamentals = get_fund()   │
│  technicals = get_tech()     │
│  valuation = get_val()       │
│  shareholding = get_share()  │
│  price_data = get_prices()   │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  2. Calculate Base Scores     │
│                              │
│  fundamental_score (0-100)   │  Weight: 35% LT, 20% ST
│  valuation_score (0-100)     │  Weight: 25% LT, 15% ST
│  technical_score (0-100)     │  Weight: 10% LT, 35% ST
│  quality_score (0-100)       │  Weight: 20% LT, 10% ST
│  risk_score (0-100)          │  Weight: 10% LT, 20% ST
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  3. Weighted Composite        │
│                              │
│  LT = 0.35F + 0.25V + 0.10T │
│       + 0.20Q + 0.10R       │
│                              │
│  ST = 0.20F + 0.15V + 0.35T │
│       + 0.10Q + 0.20R       │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  4. Apply Deal-Breakers       │
│     (D1-D10)                 │
│                              │
│  for each D in D1..D10:      │
│    if D.triggered:           │
│      has_deal_breaker = true │
│                              │
│  if has_deal_breaker:        │
│    score = min(score, 35)    │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  5. Apply Risk Penalties      │
│     (R1-R10)                 │
│                              │
│  for each R in R1..R10:      │
│    if R.triggered:           │
│      score -= R.penalty      │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  6. Apply Quality Boosters    │
│     (Q1-Q9)                 │
│                              │
│  total_boost = 0             │
│  for each Q in Q1..Q9:      │
│    if Q.triggered:           │
│      total_boost += Q.boost  │
│  score += min(total_boost,30)│
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  7. ML Adjustment (±10)      │
│                              │
│  ml_prediction = model(data) │
│  score += ml_adjustment      │
│  score = clamp(score, 0, 100)│
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  8. Confidence Scoring        │
│                              │
│  C = 0.40 × completeness    │
│    + 0.30 × freshness       │
│    + 0.15 × source_agreement │
│    + 0.15 × ml_confidence   │
└──────────┬───────────────────┘
           │
           ▼
┌──────────────────────────────┐
│  9. Generate Output           │
│                              │
│  verdict = map_score()       │
│  checklists = gen_checklists()│
│  scenarios = gen_scenarios() │
│                              │
│  Output:                     │
│    short_term_score: 0-100   │
│    long_term_score: 0-100    │
│    verdict: STRONG BUY..AVOID│
│    confidence_score: 0-100   │
│    deal_breakers: [10]       │
│    risk_penalties: [10]      │
│    quality_boosters: [9]     │
│    checklists: {ST:10,LT:13}│
│    scenarios: {bull,bear,base}│
└──────────────────────────────┘
```
 
### 3.3 Alert Processing Flow
 
```
┌─────────────────────────────────────────────────┐
│               Alert Lifecycle                    │
│                                                  │
│  CREATE                                          │
│    │  User sets: symbol, condition, threshold    │
│    │  System assigns: id, status=ACTIVE          │
│    ▼                                             │
│  MONITOR (Background, every 30 seconds)          │
│    │  For each ACTIVE alert:                     │
│    │    current_price = get_price(symbol)        │
│    │    if condition_met(price, threshold):      │
│    │      trigger_alert()                        │
│    │      if repeat: keep ACTIVE                 │
│    │      else: set TRIGGERED                    │
│    │    if expired: set EXPIRED                  │
│    ▼                                             │
│  TRIGGER                                         │
│    │  Record: triggered_at, triggered_price      │
│    │  Create: AlertNotification                  │
│    │  Future: Send email/SMS/push                │
│    ▼                                             │
│  NOTIFY (display in-app, future: external)       │
└─────────────────────────────────────────────────┘
```
 
### 3.4 WebSocket Real-Time Flow
 
```
Client                    Server                    Data Source
  │                         │                           │
  │──── WS Connect ────────>│                           │
  │                         │                           │
  │──── Subscribe ─────────>│                           │
  │     {symbols: [RELIANCE │                           │
  │      TCS, INFY]}        │                           │
  │                         │                           │
  │                         │──── Fetch Prices ────────>│
  │                         │<─── Price Data ──────────│
  │                         │                           │
  │<─── Price Update ───────│                           │
  │     {RELIANCE: 2500.50, │                           │
  │      TCS: 4200.75,      │     (every 5 seconds)    │
  │      INFY: 1850.20}     │                           │
  │                         │                           │
  │──── Unsubscribe ───────>│                           │
  │     {symbols: [INFY]}   │                           │
  │                         │                           │
  │<─── Price Update ───────│                           │
  │     {RELIANCE: 2501.00, │                           │
  │      TCS: 4201.50}      │                           │
  │                         │                           │
  │──── WS Disconnect ─────>│                           │
  │                         │  cleanup subscriptions    │
```
 
### 3.5 API Endpoint Specification
 
#### Stock Analysis Endpoint (Core)
 
```
GET /api/v1/stocks/{symbol}
 
Request:
  Path: symbol (str) - e.g., "RELIANCE"
  Query: use_real_data (bool, default=true)
 
Response (200):
{
  "symbol": "RELIANCE",
  "company_name": "Reliance Industries Ltd",
  "sector": "Oil & Gas",
  "market_cap_category": "Large Cap",
 
  "price": {
    "current": 2500.50,
    "change": 25.30,
    "change_percent": 1.02,
    "open": 2480.00,
    "high": 2510.00,
    "low": 2475.00,
    "volume": 12500000,
    "fifty_two_week_high": 2800.00,
    "fifty_two_week_low": 2100.00
  },
 
  "fundamentals": {
    "revenue": 850000000000,
    "revenue_growth": 12.5,
    "net_profit_margin": 10.2,
    "operating_margin": 15.8,
    "roe": 18.5,
    "debt_to_equity": 0.45,
    "interest_coverage": 8.5,
    "eps": 95.50,
    "book_value": 1250.00
  },
 
  "valuation": {
    "pe_ratio": 26.2,
    "pb_ratio": 2.0,
    "peg_ratio": 1.8,
    "ev_ebitda": 14.5,
    "dividend_yield": 0.8
  },
 
  "technicals": {
    "sma_20": 2450.00,
    "sma_50": 2400.00,
    "sma_200": 2350.00,
    "rsi": 58.5,
    "macd": 15.2,
    "macd_signal": 10.8,
    "bollinger_upper": 2550.00,
    "bollinger_lower": 2350.00
  },
 
  "shareholding": {
    "promoter": 50.3,
    "fii": 23.5,
    "dii": 12.8,
    "public": 13.4
  },
 
  "analysis": {
    "short_term_score": 72,
    "long_term_score": 78,
    "verdict": "BUY",
    "confidence_level": "HIGH",
    "confidence_score": 82,
    "deal_breakers": [...],
    "risk_penalties": {...},
    "quality_boosters": {...},
    "investment_checklists": {...},
    "bull_case": {...},
    "bear_case": {...},
    "base_case": {...}
  },
 
  "ml_prediction": {
    "direction": "BULLISH",
    "confidence": 0.75,
    "target_price": 2650.00,
    "time_horizon": "30d"
  }
}
```
 
---
 
## 4. Database Design
 
### 4.1 Database Selection: MongoDB
 
**Justification**:
 
| Criteria | MongoDB | PostgreSQL | InfluxDB |
|----------|---------|------------|----------|
| Schema flexibility | Excellent (schemaless) | Rigid (requires migrations) | Limited (time-series only) |
| Document structure | Native JSON | Requires JSON columns | Not applicable |
| Time-series support | Native (5.0+) | Extension (TimescaleDB) | Native |
| Async driver | Motor (mature) | asyncpg (mature) | Limited |
| Aggregation pipeline | Powerful | SQL-based | InfluxQL |
| Horizontal scaling | Built-in sharding | Requires Citus | Built-in |
| Already integrated | Yes (Motor in codebase) | No | No |
| Best for this use case | **Winner** | Good alternative | Supplement only |
 
**Recommendation**: **MongoDB as primary database** (already in use). Add Redis for caching and session management. Consider InfluxDB or MongoDB time-series collections for high-frequency price data if needed at scale.
 
### 4.2 MongoDB Collection Schema
 
```javascript
// ========================================
// Collection: stocks
// Purpose: Master stock data + latest snapshot
// ========================================
{
  _id: ObjectId,
  symbol: "RELIANCE",                    // Index: unique
  company_name: "Reliance Industries Ltd",
  isin: "INE002A01018",
  sector: "Oil & Gas",                   // Index
  industry: "Refineries",
  market_cap_category: "Large Cap",       // Index
  exchange: "NSE",
  listing_date: ISODate("1977-01-01"),
 
  // Latest price snapshot
  latest_price: {
    current: 2500.50,
    change: 25.30,
    change_percent: 1.02,
    volume: 12500000,
    updated_at: ISODate("2026-02-18T10:30:00Z")
  },
 
  // Latest fundamentals
  fundamentals: {
    revenue: 850000000000,
    revenue_growth: 12.5,
    net_profit_margin: 10.2,
    // ... all 160 fields
    updated_at: ISODate("2026-02-18T00:00:00Z")
  },
 
  // Latest analysis
  analysis: {
    short_term_score: 72,
    long_term_score: 78,
    verdict: "BUY",
    confidence_score: 82,
    deal_breakers: [...],
    updated_at: ISODate("2026-02-18T10:00:00Z")
  },
 
  metadata: {
    created_at: ISODate,
    updated_at: ISODate,
    data_quality: {
      completeness: 0.85,
      freshness: 0.95,
      last_extraction: ISODate
    }
  }
}
 
// Indexes:
// { symbol: 1 } - unique
// { sector: 1 }
// { market_cap_category: 1 }
// { "analysis.long_term_score": -1 }
// { "analysis.verdict": 1 }
 
// ========================================
// Collection: prices_daily (time-series)
// Purpose: Historical OHLCV data
// ========================================
{
  _id: ObjectId,
  symbol: "RELIANCE",                    // Index
  date: ISODate("2026-02-18"),           // Index
  open: 2480.00,
  high: 2510.00,
  low: 2475.00,
  close: 2500.50,
  volume: 12500000,
  adjusted_close: 2500.50,
  delivery_percent: 45.2,
  turnover: 31256000000,
 
  // Technical indicators (computed)
  indicators: {
    sma_20: 2450.00,
    sma_50: 2400.00,
    sma_200: 2350.00,
    ema_12: 2460.00,
    ema_26: 2430.00,
    rsi_14: 58.5,
    macd: 15.2,
    macd_signal: 10.8,
    bollinger_upper: 2550.00,
    bollinger_lower: 2350.00
  }
}
 
// Indexes:
// { symbol: 1, date: -1 } - compound
// { date: -1 } - for range queries
// Consider MongoDB time-series collection for this
 
// ========================================
// Collection: watchlists
// ========================================
{
  _id: ObjectId,
  user_id: "default",                    // For future multi-user
  name: "My Watchlist",
  items: [
    {
      symbol: "RELIANCE",
      added_at: ISODate,
      target_price: 2800.00,
      stop_loss: 2200.00,
      notes: "Good fundamentals"
    }
  ],
  created_at: ISODate,
  updated_at: ISODate
}
 
// ========================================
// Collection: portfolios
// ========================================
{
  _id: ObjectId,
  user_id: "default",
  name: "My Portfolio",
  holdings: [
    {
      symbol: "RELIANCE",
      shares: 10,
      avg_buy_price: 2300.00,
      purchase_date: ISODate("2025-06-15"),
      current_price: 2500.50,
      pnl: 2005.00,
      pnl_percent: 8.72
    }
  ],
  total_invested: 230000,
  current_value: 253050,
  total_pnl: 23050,
  xirr: 15.5,
  sector_allocation: {
    "Oil & Gas": 40,
    "IT": 35,
    "Banking": 25
  },
  created_at: ISODate,
  updated_at: ISODate
}
 
// ========================================
// Collection: alerts
// ========================================
{
  _id: ObjectId,
  user_id: "default",
  symbol: "RELIANCE",
  condition: "PRICE_ABOVE",              // Enum
  threshold: 2600.00,
  status: "ACTIVE",                      // Enum
  priority: "HIGH",                      // Enum
  repeat: false,
  expires_at: ISODate,
  created_at: ISODate,
  triggered_at: null,
  triggered_price: null,
  notifications: []
}
 
// ========================================
// Collection: extractions
// Purpose: Data pipeline run history
// ========================================
{
  _id: ObjectId,
  job_id: "ext_20260218_001",
  symbols: ["RELIANCE", "TCS"],
  status: "COMPLETED",                   // PENDING, RUNNING, COMPLETED, FAILED
  started_at: ISODate,
  completed_at: ISODate,
  results: {
    total_symbols: 2,
    successful: 2,
    failed: 0,
    fields_extracted: 320,
    data_quality_avg: 0.87
  },
  errors: []
}
 
// ========================================
// Collection: users (Future)
// ========================================
{
  _id: ObjectId,
  email: "user@example.com",
  hashed_password: "bcrypt_hash",
  name: "Investor",
  created_at: ISODate,
  preferences: {
    default_watchlist: ObjectId,
    default_portfolio: ObjectId,
    notification_channels: ["email", "push"],
    theme: "dark"
  }
}
```
 
### 4.3 Redis Cache Schema
 
```
# Price cache (TTL: 60 seconds)
cache:price:{symbol}                    -> JSON price data
 
# Analysis cache (TTL: 300 seconds)
cache:analysis:{symbol}                 -> JSON analysis data
 
# Market overview cache (TTL: 60 seconds)
cache:market:overview                   -> JSON market data
 
# Rate limiting (TTL: 60 seconds)
ratelimit:{ip}:{endpoint}              -> request count
 
# Session storage (TTL: 24 hours) [Future]
session:{session_id}                    -> JSON session data
 
# WebSocket subscriptions (no TTL)
ws:subscriptions:{client_id}           -> SET of symbols
 
# Background job locks (TTL: 300 seconds)
lock:extraction:{symbol}               -> job_id
```
 
---
 
## 5. Data Pipeline Design
 
### 5.1 Pipeline Architecture
 
```
┌─────────────────────────────────────────────────────────────────┐
│                    DATA PIPELINE OVERVIEW                        │
│                                                                  │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │ Schedule  │───>│ Extract  │───>│ Transform │───>│  Load    │ │
│  │ (Trigger) │    │ (Fetch)  │    │ (Process) │    │ (Store)  │ │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│       │               │               │               │        │
│       ▼               ▼               ▼               ▼        │
│  APScheduler    yfinance API    Cleaner          MongoDB       │
│  Cron jobs      NSE Bhavcopy    Calculator       Redis cache   │
│  Manual trigger BSE API         Validator                      │
│  Webhook        RSS Feeds       Technical calc                 │
└─────────────────────────────────────────────────────────────────┘
```
 
### 5.2 Extraction Schedule
 
| Job | Frequency | Trigger | Source | Data |
|-----|-----------|---------|--------|------|
| Intraday Prices | Every 5s (market hours) | WebSocket/Polling | Upstox/yfinance | OHLCV |
| EOD Prices | Daily 4:00 PM IST | Cron | NSE Bhavcopy | OHLCV + delivery |
| Fundamentals | Weekly (Saturday) | Cron | yfinance + scraping | Financial statements |
| Shareholding | Quarterly | Manual + Cron | NSE filings | Promoter/FII/DII |
| Corporate Actions | Daily 6:00 PM IST | Cron | BSE API | Dividends/splits |
| FII/DII Activity | Daily 6:30 PM IST | Cron | NSE reports | Buy/sell data |
| News | Every 15 min | Cron | RSS + NewsAPI | Headlines + sentiment |
| Index Data | Every 5 min (market hours) | Cron | NSE/yfinance | Index values + breadth |
| Scores Recalculation | Daily 7:00 PM IST | Cron | Internal | All tracked stocks |
 
### 5.3 Orchestrator Design
 
```python
# Pseudo-code for Pipeline Orchestrator
 
class PipelineOrchestrator:
    """
    Coordinates data extraction, processing, and storage.
    Runs as background service within FastAPI lifecycle.
    """
 
    def __init__(self):
        self.scheduler = APScheduler()
        self.extractors = {
            'yfinance': YFinanceExtractor(),
            'nse_bhavcopy': NSEBhavcopyExtractor(),
            'bse_api': BSEApiExtractor(),       # NEW
            'news_rss': NewsRSSExtractor(),     # NEW
        }
        self.processors = {
            'cleaner': DataCleaner(),
            'calculator': CalculationEngine(),
            'technical': TechnicalCalculator(),
            'validator': ValidationEngine(),
        }
        self.storage = MongoDBStore()
        self.cache = RedisCache()
 
    async def run_extraction(self, symbols, job_type='full'):
        """
        Full extraction pipeline for given symbols.
 
        Steps:
        1. Create extraction job record
        2. Extract raw data from all sources
        3. Clean and normalize data
        4. Calculate derived metrics
        5. Validate data quality
        6. Store in MongoDB
        7. Invalidate cache
        8. Trigger score recalculation
        """
        job = await self.create_job(symbols, job_type)
 
        for symbol in symbols:
            try:
                # Extract from all sources
                raw_data = {}
                for name, extractor in self.extractors.items():
                    raw_data[name] = await extractor.extract(symbol)
 
                # Merge and clean
                merged = self.processors['cleaner'].merge(raw_data)
                cleaned = self.processors['cleaner'].clean(merged)
 
                # Calculate derived fields
                enriched = self.processors['calculator'].calculate(cleaned)
                enriched = self.processors['technical'].calculate(enriched)
 
                # Validate
                quality = self.processors['validator'].validate(enriched)
 
                # Store
                await self.storage.upsert_stock(symbol, enriched, quality)
 
                # Invalidate cache
                await self.cache.delete(f"cache:analysis:{symbol}")
 
                job.mark_success(symbol)
 
            except Exception as e:
                job.mark_failure(symbol, str(e))
 
        await self.storage.save_job(job)
        return job
 
    def register_schedules(self):
        """Register all cron jobs."""
        # Market hours: 9:15 AM - 3:30 PM IST (Mon-Fri)
        self.scheduler.add_job(
            self.intraday_update,
            trigger='interval', seconds=60,
            id='intraday_prices'
        )
        self.scheduler.add_job(
            self.eod_extraction,
            trigger='cron', hour=16, minute=0,
            day_of_week='mon-fri',
            id='eod_prices'
        )
        self.scheduler.add_job(
            self.weekly_fundamentals,
            trigger='cron', day_of_week='sat', hour=6,
            id='weekly_fundamentals'
        )
        self.scheduler.add_job(
            self.daily_score_recalc,
            trigger='cron', hour=19, minute=0,
            day_of_week='mon-fri',
            id='daily_scores'
        )
```
 
### 5.4 Data Quality Framework
 
```
┌─────────────────────────────────────────────────┐
│              Data Quality Pipeline                │
│                                                  │
│  Raw Data ──> Completeness Check (40%)           │
│           │   How many of 160 fields present?    │
│           │                                      │
│           ├── Freshness Check (30%)              │
│           │   How old is the data?               │
│           │   < 1 day = 100%, 1-7 days = 80%,   │
│           │   7-30 days = 50%, > 30 days = 20%   │
│           │                                      │
│           ├── Source Agreement (15%)              │
│           │   Do multiple sources agree?          │
│           │   Price variance < 1% = good         │
│           │                                      │
│           └── Anomaly Detection (15%)            │
│               Are values within expected range?  │
│               Z-score > 3 = flag for review      │
│                                                  │
│  Output: confidence_score (0-100)                │
│          data_quality_report {}                  │
└─────────────────────────────────────────────────┘
```
 
---
 
## 6. ML Pipeline Design
 
### 6.1 ML Architecture Overview
 
```
┌─────────────────────────────────────────────────────────────────┐
│                      ML PIPELINE                                │
│                                                                  │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐            │
│  │ Feature    │    │ Model      │    │ Inference  │            │
│  │ Store      │───>│ Training   │───>│ Service    │            │
│  │            │    │            │    │            │            │
│  │ 160+ feats │    │ Offline    │    │ Online     │            │
│  │ Historical │    │ Weekly     │    │ Real-time  │            │
│  │ Rolling    │    │ Versioned  │    │ Cached     │            │
│  └────────────┘    └────────────┘    └────────────┘            │
│                                                                  │
│  Models:                                                         │
│  ├── Price Direction (LSTM/Transformer)                         │
│  ├── Sentiment Classifier (Fine-tuned BERT)                    │
│  ├── Anomaly Detector (Isolation Forest)                       │
│  └── Score Adjuster (Gradient Boosting)                        │
└─────────────────────────────────────────────────────────────────┘
```
 
### 6.2 Feature Engineering
 
```
Feature Categories for ML Models:
 
1. Price Features (rolling windows: 5d, 10d, 20d, 50d, 200d)
   - Returns (daily, weekly, monthly)
   - Volatility (realized, implied proxy)
   - Price relative to moving averages
   - Distance from 52-week high/low
   - Volume ratio (current/average)
 
2. Fundamental Features
   - Revenue growth rate
   - Margin trends (expanding/contracting)
   - ROE, ROCE trends
   - Debt trajectory
   - EPS growth
 
3. Technical Features
   - RSI (14-day)
   - MACD histogram
   - Bollinger Band position
   - ADX (trend strength)
   - Stochastic oscillator
 
4. Sentiment Features
   - News sentiment score (rolling 7d)
   - FII/DII flow direction
   - Sector momentum
   - Market breadth indicators
 
5. Cross-Sectional Features
   - Relative strength vs NIFTY50
   - Sector rank
   - Market cap percentile
```
 
### 6.3 Model Specifications
 
| Model | Algorithm | Input | Output | Training | Serving |
|-------|-----------|-------|--------|----------|---------|
| Price Direction | LSTM / Temporal Fusion Transformer | 50-day feature window | Up/Down/Flat + confidence | Weekly (Saturday) | Batch daily 7 PM |
| Sentiment | DistilBERT fine-tuned | News headline + content | Positive/Negative/Neutral + score | Monthly | Real-time per article |
| Anomaly | Isolation Forest | Price + Volume features | Normal/Anomaly + score | Monthly | Batch daily |
| Score Adjuster | XGBoost | Scoring features + market context | Score adjustment (-10 to +10) | Weekly | Batch daily |
 
### 6.4 ML Tech Stack Recommendation
 
| Component | Tool | Justification |
|-----------|------|---------------|
| Feature Store | Feast (open-source) or custom MongoDB | Feast is production-ready; MongoDB works for small scale |
| Training Framework | PyTorch + PyTorch Lightning | Best for LSTM/Transformer models |
| Experiment Tracking | MLflow | Open-source, tracks params/metrics/artifacts |
| Model Registry | MLflow Model Registry | Version control for models, staging/production |
| Serving | FastAPI endpoint (inline) | Already have FastAPI; simple for single-server |
| Batch Inference | APScheduler job | Runs after daily data extraction |
| Monitoring | MLflow + custom metrics | Track prediction accuracy, data drift |
 
---
 
## 7. LLM Integration
 
### 7.1 Current Implementation
 
```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│  FastAPI      │─────>│  LLM Service │─────>│  Emergent    │
│  Endpoint     │      │              │      │  (GPT-4o)    │
│              │      │  Prompt      │      │              │
│  /llm-insight│      │  Engineering │      │  OpenAI API  │
└──────────────┘      └──────────────┘      └──────────────┘
```
 
### 7.2 Enhanced LLM Architecture (Recommended)
 
```
┌─────────────────────────────────────────────────────────────────┐
│                    LLM INTEGRATION LAYER                        │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    LLM Router                              │ │
│  │                                                            │ │
│  │  Route by task type:                                       │ │
│  │  ├── Stock Analysis ──> GPT-4o (high quality)             │ │
│  │  ├── News Summary ──> GPT-4o-mini (cost-effective)        │ │
│  │  ├── Quick Query ──> GPT-4o-mini (low latency)            │ │
│  │  └── Batch Insight ──> GPT-4o (quality, batch API)        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Prompt       │  │ Response     │  │ Cache        │         │
│  │ Templates    │  │ Parser       │  │ Layer        │         │
│  │              │  │              │  │              │         │
│  │ Structured   │  │ JSON extract │  │ Redis        │         │
│  │ Few-shot     │  │ Validation   │  │ TTL: 1hr     │         │
│  │ Context-rich │  │ Fallback     │  │ Per-symbol   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                                                                  │
│  Features:                                                       │
│  ├── Structured output (JSON mode)                              │
│  ├── Token usage tracking per request                           │
│  ├── Cost monitoring (per model)                                │
│  ├── Response caching (identical prompts)                       │
│  ├── Rate limiting (tokens per minute)                          │
│  └── Fallback chain (GPT-4o -> GPT-4o-mini -> cached)          │
└─────────────────────────────────────────────────────────────────┘
```
 
### 7.3 LLM Use Cases
 
| Use Case | Model | Prompt Type | Cache TTL | Cost/Call |
|----------|-------|-------------|-----------|-----------|
| Full stock analysis | GPT-4o | Detailed with all data | 1 hour | ~$0.05 |
| Score explanation | GPT-4o | Focused on scoring data | 1 hour | ~$0.03 |
| Risk assessment | GPT-4o | Risk-focused data subset | 1 hour | ~$0.03 |
| News summary | GPT-4o-mini | Headlines + sentiment | 15 min | ~$0.005 |
| Quarterly results | GPT-4o | Financial statements | 24 hours | ~$0.05 |
| Quick question | GPT-4o-mini | Short context | No cache | ~$0.003 |
 
---
 
## 8. Infrastructure & Deployment
 
### 8.1 Deployment Architecture
 
```
┌─────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT TOPOLOGY                           │
│                                                                  │
│  Option A: Single Server (Current / MVP)                        │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Ubuntu 22.04 LTS                                         │  │
│  │                                                           │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐    │  │
│  │  │ Nginx   │  │ FastAPI │  │ React   │  │ MongoDB │    │  │
│  │  │ :80/443 │  │ :8000   │  │ :3000   │  │ :27017  │    │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘    │  │
│  │                                         ┌─────────┐      │  │
│  │                                         │ Redis   │      │  │
│  │                                         │ :6379   │      │  │
│  │                                         └─────────┘      │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Option B: Containerized (Recommended Next Step)                │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  Docker Compose                                           │  │
│  │                                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │  │
│  │  │ nginx       │  │ backend     │  │ frontend    │     │  │
│  │  │ (reverse    │  │ (FastAPI +  │  │ (React      │     │  │
│  │  │  proxy)     │  │  Uvicorn)   │  │  build)     │     │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘     │  │
│  │                                                           │  │
│  │  ┌─────────────┐  ┌─────────────┐                       │  │
│  │  │ mongodb     │  │ redis       │                       │  │
│  │  │ (data vol)  │  │ (cache)     │                       │  │
│  │  └─────────────┘  └─────────────┘                       │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                  │
│  Option C: Cloud-Native (Future Scale)                          │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  AWS / GCP / Azure                                        │  │
│  │                                                           │  │
│  │  CDN (CloudFront) ──> S3 (React build)                   │  │
│  │  ALB ──> ECS Fargate (FastAPI containers)                │  │
│  │  MongoDB Atlas (managed cluster)                         │  │
│  │  ElastiCache Redis (managed)                             │  │
│  │  CloudWatch / Prometheus (monitoring)                    │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```
 
### 8.2 Docker Configuration (Recommended)
 
```yaml
# docker-compose.yml (Recommended structure)
 
version: '3.8'
 
services:
  # Reverse Proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./frontend/build:/usr/share/nginx/html
    depends_on:
      - backend
 
  # Backend API
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - MONGO_URL=mongodb://mongodb:27017
      - MONGO_DB_NAME=stockpulse
      - REDIS_URL=redis://redis:6379
      - EMERGENT_LLM_KEY=${EMERGENT_LLM_KEY}
      - ENVIRONMENT=production
    ports:
      - "8000:8000"
    depends_on:
      - mongodb
      - redis
    restart: unless-stopped
 
  # Frontend (build stage only, served by Nginx)
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    volumes:
      - frontend_build:/app/build
 
  # Database
  mongodb:
    image: mongo:7.0
    volumes:
      - mongodb_data:/data/db
    ports:
      - "27017:27017"
    restart: unless-stopped
 
  # Cache
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    restart: unless-stopped
 
volumes:
  mongodb_data:
  redis_data:
  frontend_build:
```
 
### 8.3 Backend Dockerfile
 
```dockerfile
# backend/Dockerfile (Recommended)
FROM python:3.11-slim
 
WORKDIR /app
 
# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && rm -rf /var/lib/apt/lists/*
 
# Copy requirements first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
# Copy application code
COPY . .
 
# Create non-root user
RUN useradd --create-home appuser
USER appuser
 
EXPOSE 8000
 
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```
 
### 8.4 CI/CD Pipeline (Recommended)
 
```yaml
# .github/workflows/ci.yml (Recommended structure)
 
name: StockPulse CI/CD
 
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]
 
jobs:
  # Backend tests
  backend-test:
    runs-on: ubuntu-latest
    services:
      mongodb:
        image: mongo:7.0
        ports: [27017:27017]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt
      - run: cd backend && python -m pytest tests/ -v --cov=.
      - run: cd backend && black --check .
      - run: cd backend && flake8 .
      - run: cd backend && mypy .
 
  # Frontend tests
  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - run: cd frontend && npm ci
      - run: cd frontend && npm test -- --watchAll=false
      - run: cd frontend && npm run build
 
  # Docker build
  docker-build:
    needs: [backend-test, frontend-test]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose build
      - run: docker compose up -d
      - run: sleep 10 && curl -f http://localhost:8000/api/ || exit 1
      - run: docker compose down
 
  # Deploy (on main merge)
  deploy:
    needs: docker-build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Deploy to production"
      # Add deployment steps based on hosting choice
```
 
---
 
## 9. Monitoring & Logging
 
### 9.1 Observability Stack
 
```
┌─────────────────────────────────────────────────────────────────┐
│                    OBSERVABILITY STACK                           │
│                                                                  │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐      │
│  │   Logging     │  │   Metrics     │  │   Tracing     │      │
│  │               │  │               │  │               │      │
│  │  structlog    │  │  Prometheus   │  │  OpenTelemetry│      │
│  │  → stdout     │  │  client      │  │  (optional)   │      │
│  │  → file       │  │  /metrics    │  │               │      │
│  │  → Loki       │  │  endpoint    │  │  Spans for    │      │
│  │               │  │               │  │  API calls    │      │
│  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘      │
│          │                  │                  │               │
│          ▼                  ▼                  ▼               │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                     Grafana Dashboard                      │ │
│  │                                                            │ │
│  │  Panels:                                                   │ │
│  │  ├── API Request Rate (per endpoint)                      │ │
│  │  ├── Response Latency (p50, p95, p99)                    │ │
│  │  ├── Error Rate (4xx, 5xx)                               │ │
│  │  ├── Data Extraction Success Rate                        │ │
│  │  ├── WebSocket Active Connections                        │ │
│  │  ├── MongoDB Query Performance                           │ │
│  │  ├── Cache Hit/Miss Ratio                                │ │
│  │  ├── LLM Token Usage & Cost                              │ │
│  │  ├── ML Model Prediction Accuracy                        │ │
│  │  └── Alert Trigger Frequency                             │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```
 
### 9.2 Logging Strategy
 
```python
# Recommended logging configuration
 
import structlog
 
# Configure structlog for structured JSON logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
)
 
# Log levels by component:
#
# API Requests:        INFO  (method, path, status, duration_ms)
# Data Extraction:     INFO  (symbol, source, fields_count, quality)
# Scoring Calculation: INFO  (symbol, score, verdict, confidence)
# Alert Triggers:      WARN  (symbol, condition, price, threshold)
# LLM Calls:          INFO  (model, tokens_in, tokens_out, cost)
# Errors:             ERROR (exception, context, stack_trace)
# WebSocket Events:   DEBUG (connect, disconnect, subscribe)
# Cache Operations:   DEBUG (hit/miss, key, ttl)
```
 
### 9.3 Key Metrics to Track
 
| Metric | Type | Alert Threshold |
|--------|------|-----------------|
| `api_request_duration_seconds` | Histogram | p99 > 5s |
| `api_request_total` | Counter | - |
| `api_errors_total` | Counter | > 10/min on 5xx |
| `extraction_success_rate` | Gauge | < 80% |
| `extraction_duration_seconds` | Histogram | > 300s |
| `websocket_connections_active` | Gauge | > 1000 |
| `mongodb_query_duration_seconds` | Histogram | p95 > 1s |
| `cache_hit_ratio` | Gauge | < 50% |
| `llm_tokens_total` | Counter | - |
| `llm_cost_total_usd` | Counter | > $50/day |
| `alert_triggers_total` | Counter | - |
| `scoring_calculation_duration` | Histogram | > 10s |
| `data_quality_score` | Gauge | < 60 avg |
 
### 9.4 Health Check Endpoints
 
```
GET /health/live          # Is the process running?
  Response: {"status": "ok"}
 
GET /health/ready         # Is the service ready to serve?
  Response: {
    "status": "ok",
    "checks": {
      "mongodb": "connected",
      "redis": "connected",
      "yfinance": "reachable",
      "llm_api": "reachable"
    }
  }
 
GET /health/metrics       # Prometheus metrics endpoint
  Response: prometheus text format
```
 
---
 
## 10. Technology Stack Recommendations
 
### 10.1 Complete Stack with Justification
 
| Layer | Technology | Version | Justification | Alternatives Considered |
|-------|-----------|---------|---------------|------------------------|
| **Frontend Framework** | React | 19.0 | Already in use, mature ecosystem, large community | Next.js (SSR not needed), Vue (smaller ecosystem) |
| **UI Components** | shadcn/ui + Radix | Latest | Already in use, accessible, customizable | Ant Design (heavier), MUI (opinionated) |
| **Styling** | Tailwind CSS | 3.4 | Already in use, utility-first, rapid development | CSS Modules (more boilerplate) |
| **Charts** | Recharts | 3.6 | Already in use, React-native, declarative | D3 (lower level), Highcharts (license cost) |
| **Backend Framework** | FastAPI | 0.110 | Already in use, async, auto-docs, type-safe | Django REST (heavier), Express (less type safety) |
| **ASGI Server** | Uvicorn | 0.25 | Standard for FastAPI, performant | Hypercorn (similar), Gunicorn+Uvicorn workers |
| **Database** | MongoDB | 7.0 | Already in use, flexible schema, time-series support | PostgreSQL (rigid schema), DynamoDB (vendor lock) |
| **DB Driver** | Motor | 3.3 | Async MongoDB driver, already in use | PyMongo (sync only) |
| **Cache** | Redis | 7.x | Fast, versatile (cache, queues, sessions, rate limiting) | Memcached (less features) |
| **Task Scheduling** | APScheduler | 3.x | In-process, simple, sufficient for single-server | Celery (overkill for single server), Airflow (too heavy) |
| **Data Library** | Pandas + NumPy | 3.0 / 2.4 | Already in use, standard for financial data | Polars (faster but less ecosystem) |
| **Market Data** | yfinance + Upstox API | Latest | yfinance free, Upstox for Indian market real-time | Zerodha Kite (similar), Angel One (similar) |
| **LLM** | GPT-4o via Emergent | Latest | Already integrated, high quality | Claude (good alternative), Gemini (cost-effective) |
| **PDF Generation** | ReportLab | 4.2 | Already in use, professional output | WeasyPrint (CSS-based), FPDF (simpler) |
| **ML Training** | PyTorch + scikit-learn | Latest | Industry standard, flexible | TensorFlow (heavier) |
| **ML Serving** | FastAPI inline | - | Already have FastAPI, simple deployment | TFServing (overkill), Triton (GPU-focused) |
| **Experiment Tracking** | MLflow | Latest | Open-source, comprehensive | Weights & Biases (SaaS cost) |
| **Reverse Proxy** | Nginx / Caddy | Latest | Nginx: proven; Caddy: auto-HTTPS | Traefik (more complex) |
| **Containerization** | Docker + Compose | Latest | Standard, portable, reproducible | Podman (similar), bare metal (less portable) |
| **CI/CD** | GitHub Actions | - | Integrated with GitHub, generous free tier | Jenkins (self-hosted), GitLab CI (if using GitLab) |
| **Monitoring** | Prometheus + Grafana | Latest | Open-source standard, extensive dashboards | Datadog (SaaS cost), New Relic (SaaS cost) |
| **Logging** | structlog + Loki | Latest | Structured JSON, Grafana integration | ELK Stack (heavier), CloudWatch (vendor lock) |
| **Testing** | pytest + Jest | Latest | Standard for Python/JS, rich plugin ecosystem | unittest (less features), Vitest (newer) |
 
### 10.2 Indian Market Data API Comparison
 
| API | Real-time | Historical | Fundamentals | Cost | Recommendation |
|-----|-----------|------------|--------------|------|----------------|
| **yfinance** | Delayed (15 min) | Yes (free) | Basic | Free | Keep as fallback |
| **Upstox API** | WebSocket (live) | Yes | Limited | Free tier available | Primary for real-time |
| **Zerodha Kite** | WebSocket (live) | Yes | Limited | Paid (Rs 2000/mo) | Alternative to Upstox |
| **Angel One SmartAPI** | WebSocket (live) | Yes | Limited | Free | Good free alternative |
| **NSE Bhavcopy** | EOD only | Yes | No | Free | Daily OHLCV + delivery |
| **BSE API** | Limited | Yes | Corporate actions | Free | Corporate actions source |
| **Screener.in** | No | Limited | Excellent | Scraping | Fundamentals deep-dive |
| **TrueData** | Tick-by-tick | Yes | No | Paid | High-frequency needs |
 
**Recommended API Strategy**:
1. **Primary real-time**: Upstox API or Angel One SmartAPI (free WebSocket)
2. **EOD data**: NSE Bhavcopy (official, free, reliable)
3. **Fundamentals**: yfinance + Screener.in scraping
4. **Corporate actions**: BSE API
5. **Fallback**: yfinance for everything
 
---
 
## 11. Implementation Plan
 
### 11.1 Where Each Component Fits
 
```
┌─────────────────────────────────────────────────────────────────┐
│                    COMPONENT PLACEMENT MAP                       │
│                                                                  │
│  FRONTEND (React SPA)                                           │
│  └── /frontend/src/                                             │
│      ├── pages/          → User-facing screens                  │
│      ├── components/     → Reusable UI widgets                  │
│      ├── hooks/          → Data fetching, WebSocket             │
│      ├── lib/            → API client, utilities                │
│      └── store/          → State management (if needed)         │
│                                                                  │
│  BACKEND (FastAPI)                                              │
│  └── /backend/                                                  │
│      ├── server.py       → App entry, middleware, lifespan      │
│      ├── routers/        → API endpoint handlers (split from    │
│      │                     server.py)                           │
│      ├── services/       → Business logic (scoring, alerts,     │
│      │                     market data, LLM, backtesting)       │
│      ├── data_extraction/ → ETL pipeline (extractors,           │
│      │                     processors, validators, storage)     │
│      ├── models/         → Pydantic schemas for all entities    │
│      ├── middleware/     → Auth, rate limit, logging            │
│      ├── config/         → Settings, constants                  │
│      └── tests/          → Unit + integration tests             │
│                                                                  │
│  ML PIPELINE (Future)                                           │
│  └── /ml/                                                       │
│      ├── features/       → Feature engineering                  │
│      ├── models/         → Model definitions                    │
│      ├── training/       → Training scripts                     │
│      ├── inference/      → Prediction service                   │
│      └── experiments/    → MLflow experiment configs             │
│                                                                  │
│  INFRASTRUCTURE                                                  │
│  └── /                                                          │
│      ├── docker-compose.yml  → Container orchestration          │
│      ├── nginx.conf          → Reverse proxy config             │
│      ├── .github/workflows/  → CI/CD pipelines                  │
│      ├── monitoring/         → Prometheus, Grafana configs       │
│      └── scripts/            → Setup, migration, backup scripts │
└─────────────────────────────────────────────────────────────────┘
```
 
### 11.2 Implementation Sequence
 
```
Phase 1: Data Foundation [CURRENT]
├── 1.1 Evaluate Indian market APIs
├── 1.2 Implement primary data connector (Upstox/Angel One)
├── 1.3 Wire data extraction pipeline to server
├── 1.4 Implement scheduled extraction jobs
├── 1.5 MongoDB persistence for all data
└── 1.6 End-to-end testing with real data
 
Phase 2: Production Hardening
├── 2.1 Docker containerization
├── 2.2 Nginx reverse proxy + HTTPS
├── 2.3 Redis cache integration
├── 2.4 JWT authentication
├── 2.5 API rate limiting
├── 2.6 Structured logging
├── 2.7 Error handling standardization
├── 2.8 Database indexing
├── 2.9 Unit + integration test suite
└── 2.10 CI/CD pipeline
 
Phase 3: Enhancement
├── 3.1 Email/SMS alert notifications
├── 3.2 Advanced technical indicators
├── 3.3 Peer comparison tool
├── 3.4 Earnings calendar
├── 3.5 Multiple portfolio support
├── 3.6 Custom dashboard
├── 3.7 Report scheduling
└── 3.8 Broker integration
 
Phase 4: ML Pipeline
├── 4.1 Feature store setup
├── 4.2 Price direction model (LSTM)
├── 4.3 Sentiment model (BERT)
├── 4.4 Anomaly detection
├── 4.5 Model registry (MLflow)
├── 4.6 Batch inference pipeline
└── 4.7 A/B testing framework
 
Phase 5: Scale
├── 5.1 Multi-user support
├── 5.2 Subscription tiers
├── 5.3 Cloud deployment
├── 5.4 CDN + edge caching
├── 5.5 Message queue
├── 5.6 Horizontal scaling
└── 5.7 Mobile app / PWA
```
 
---
 
## Appendix: Decision Log
 
| # | Decision | Rationale | Date |
|---|----------|-----------|------|
| 1 | MongoDB over PostgreSQL | Flexible schema for 160+ fields, time-series support, async driver already integrated | Feb 2026 |
| 2 | FastAPI over Django | Async-first, auto-docs, lighter weight, already in use | Feb 2026 |
| 3 | React over Next.js | SPA sufficient (no SEO needed), simpler deployment, already in use | Feb 2026 |
| 4 | yfinance as fallback | Free, reliable for historical data, but delayed for real-time | Feb 2026 |
| 5 | GPT-4o for analysis | Highest quality for financial analysis, cost acceptable for single-user | Feb 2026 |
| 6 | APScheduler over Celery | In-process scheduling sufficient for single-server deployment | Feb 2026 |
| 7 | Redis for caching | Versatile (cache + sessions + rate limiting + queues), lightweight | Feb 2026 |
| 8 | Docker for deployment | Portable, reproducible, standard practice | Feb 2026 |
| 9 | Prometheus + Grafana | Open-source, comprehensive, no vendor lock-in | Feb 2026 |
| 10 | Upstox/Angel One for real-time | Free tier available, Indian market native, WebSocket support | Feb 2026 |
 
---
 
*This document serves as the complete technical blueprint for StockPulse. All implementation decisions should reference this document. Update when significant architectural changes are made.*