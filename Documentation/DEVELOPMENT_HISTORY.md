# StockPulse - Development History & Technical Documentation

> **Document Version**: 2.0  
> **Last Updated**: February 2026  
> **Platform**: Indian Stock Market Analysis Platform (NSE/BSE)

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture Overview](#architecture-overview)
3. [Development Timeline](#development-timeline)
4. [File Structure & Purpose](#file-structure--purpose)
5. [Feature Implementation Details](#feature-implementation-details)
6. [API Endpoints Reference](#api-endpoints-reference)
7. [Scoring System Documentation](#scoring-system-documentation)
8. [Data Extraction Pipeline](#data-extraction-pipeline)
9. [Testing & Quality Assurance](#testing--quality-assurance)

---

## 🎯 Project Overview

### What is StockPulse?
StockPulse is a comprehensive personal stock analysis platform designed for Indian markets (NSE/BSE). It features:
- **Rule-based scoring system** (0-100 scale)
- **Deal-breaker detection** (automatic stock disqualification)
- **ML predictions** for price direction
- **LLM-powered insights** via GPT-4o
- **Investment checklists** for both short-term and long-term strategies

### Key Capabilities
| Feature | Description |
|---------|-------------|
| 160 Data Fields | Comprehensive data across 13 categories |
| 10 Deal-Breakers | D1-D10 automatic stock rejection rules |
| 10 Risk Penalties | R1-R10 score deduction rules |
| 9 Quality Boosters | Q1-Q9 score enhancement rules |
| Investment Checklists | 10 short-term + 13 long-term criteria |

---

## 🏗️ Architecture Overview

### Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND                              │
│  React 18 + Tailwind CSS + shadcn/ui + Recharts             │
│  Port: 3000                                                  │
├─────────────────────────────────────────────────────────────┤
│                        BACKEND                               │
│  FastAPI + Python 3.11 + Motor (async MongoDB)              │
│  Port: 8001                                                  │
├─────────────────────────────────────────────────────────────┤
│                       DATABASE                               │
│  MongoDB (Motor async driver)                                │
├─────────────────────────────────────────────────────────────┤
│                    INTEGRATIONS                              │
│  OpenAI GPT-4o (via Emergent LLM Key)                       │
│  Groww Trading API (Live Indian Market Data)                │
│  Yahoo Finance (yfinance) for historical data               │
└─────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
/app/
├── backend/                    # FastAPI Backend
│   ├── server.py              # Main API server with all endpoints
│   ├── models/                # Pydantic models
│   │   ├── stock_models.py    # Data models for stocks, portfolios, etc.
│   │   └── pipeline_models.py # Data pipeline models (NEW)
│   ├── services/              # Business logic
│   │   ├── scoring_engine.py  # 4-tier scoring system
│   │   ├── mock_data.py       # Mock data generation
│   │   ├── llm_service.py     # GPT-4o integration
│   │   ├── alerts_service.py  # Price alerts functionality
│   │   └── pipeline_service.py # Data pipeline management (NEW)
│   └── data_extraction/       # Data extraction pipeline
│       ├── config/            # Field definitions (160 fields)
│       ├── extractors/        # Data source extractors
│       │   ├── yfinance_extractor.py  # Yahoo Finance
│       │   ├── nse_extractor.py       # NSE bhavcopy
│       │   └── grow_extractor.py      # Groww API (NEW)
│       ├── pipeline/          # Orchestration logic
│       ├── processors/        # Data cleaning & normalization
│       └── quality/           # Data quality validation
├── frontend/                   # React Frontend
│   └── src/
│       ├── pages/             # Main application pages
│       │   ├── Dashboard.jsx  # Market overview
│       │   ├── StockAnalyzer.jsx # Stock analysis with tabs
│       │   ├── Screener.jsx   # Stock screening
│       │   ├── Watchlist.jsx  # Watchlist management
│       │   ├── Portfolio.jsx  # Portfolio tracking
│       │   ├── NewsHub.jsx    # News aggregation
│       │   ├── Reports.jsx    # Report generation
│       │   └── DataPipeline.jsx # Pipeline monitoring (NEW)
│       ├── components/        # Reusable UI components
│       └── lib/               # Utilities and API client
├── Documentation/             # Project documentation
└── memory/                    # PRD and project context
```

---

## 📅 Development Timeline

### Phase 1: Foundation (Initial Build)
- ✅ Setup FastAPI backend with MongoDB
- ✅ Create React frontend with Tailwind CSS
- ✅ Implement 7 core modules (Dashboard, Analyzer, Screener, etc.)
- ✅ Add mock data for 40 Indian stocks
- ✅ Integrate GPT-4o for AI insights

### Phase 2: Data Extraction Pipeline
- ✅ Design 160 data fields across 13 categories
- ✅ Build extraction framework with yfinance
- ✅ Implement NSE bhavcopy parser
- ✅ Add data quality validation

### Phase 3: Scoring System Enhancement (Current Session)

#### Step 1: Deal-Breakers (D1-D10) ✅
**File Modified**: `backend/services/scoring_engine.py`

Implemented all 10 deal-breakers that automatically reject a stock:
| Code | Rule | Threshold | Description |
|------|------|-----------|-------------|
| D1 | Interest Coverage | < 2.0x | Cannot service debt |
| D2 | SEBI Investigation | = true | Regulatory risk |
| D3 | Revenue Declining | ≥ 3 years | Business failing |
| D4 | Negative OCF | ≥ 2 years | Cash burn issue |
| D5 | Negative FCF | ≥ 3 years | Unsustainable business |
| D6 | Stock Status | ≠ ACTIVE | Halted/Suspended |
| D7 | Promoter Pledging | > 80% | High promoter stress |
| D8 | Debt-to-Equity | > 5.0 | Excessive leverage |
| D9 | Credit Rating | D/Withdrawn | Default risk |
| D10 | Avg Volume | < 50,000 | Illiquid (short-term only) |

#### Step 2: Risk Penalties (R1-R10) ✅
**File Modified**: `backend/services/scoring_engine.py`

Implemented cumulative score deductions:
| Code | Rule | Threshold | LT Penalty | ST Penalty |
|------|------|-----------|------------|------------|
| R1 | D/E Moderate | 2.0-5.0 | -15 | -10 |
| R2 | Interest Coverage | 2.0-3.0x | -10 | -5 |
| R3 | ROE Weak | < 10% | -12 | -5 |
| R4 | Promoter Decreased | > 5% drop | -8 | -12 |
| R5 | Promoter Pledging | 30-80% | -10 | -15 |
| R6 | Price Below 52W High | > 30% | -5 | -15 |
| R7 | Operating Margin | Declining 2+ yrs | -10 | -5 |
| R8 | P/E Expensive | > 2x sector | -10 | -5 |
| R9 | Delivery % Low | < 30% | -5 | -10 |
| R10 | Contingent Liabilities | > 10% | -8 | -3 |

#### Step 3: Quality Boosters (Q1-Q9) ✅
**File Modified**: `backend/services/scoring_engine.py`

Implemented positive score additions (capped at +30):
| Code | Rule | Threshold | LT Boost | ST Boost |
|------|------|-----------|----------|----------|
| Q1 | ROE Excellent | > 20% | +15 | +5 |
| Q2 | Revenue Growth | > 15% CAGR | +12 | +5 |
| Q3 | Zero Debt | D/E < 0.1 | +10 | +5 |
| Q4 | Dividend History | 10+ years | +8 | +3 |
| Q5 | Operating Margin | > 25% | +10 | +5 |
| Q6 | Promoter Holding | > 50% | +8 | +10 |
| Q7 | FII Interest | > 20% | +5 | +8 |
| Q8 | 52W Breakout | With 2x volume | +3 | +12 |
| Q9 | FCF Yield | > 5% | +8 | +4 |

#### Step 4: Confidence Score Formula ✅
**File Modified**: `backend/services/scoring_engine.py`

Implemented documented formula:
```
Confidence = DataCompleteness(40%) + DataFreshness(30%) + SourceAgreement(15%) + MLConfidence(15%)
```

#### Step 5: Investment Checklists ✅
**Files Modified**: 
- `backend/services/scoring_engine.py`
- `frontend/src/pages/StockAnalyzer.jsx`

**Short-Term Checklist (10 items)**:
| ID | Criterion | Deal-Breaker |
|----|-----------|--------------|
| ST1 | Price above 50-day SMA | No |
| ST2 | RSI between 30-70 | No |
| ST3 | Volume confirms trend | No |
| ST4 | No earnings in 2 weeks | No |
| ST5 | Sector showing strength | No |
| ST6 | No negative catalysts | No |
| ST7 | Stock not halted/investigation | **YES** |
| ST8 | Volume > 100,000 | **YES** |
| ST9 | Clear support level | No |
| ST10 | Risk/reward ≥ 2:1 | No |

**Long-Term Checklist (13 items)**:
| ID | Criterion | Deal-Breaker |
|----|-----------|--------------|
| LT1 | Revenue grown 3+ years | No |
| LT2 | Profitable | No |
| LT3 | ROE > 15% | No |
| LT4 | FCF positive & growing | No |
| LT5 | D/E < 1.5 | No |
| LT6 | Competitive moat exists | No |
| LT7 | Good management track record | No |
| LT8 | Industry tailwinds | No |
| LT9 | PEG < 2 | No |
| LT10 | No fraud history | **YES** |
| LT11 | No disruption threat | **YES** |
| LT12 | Interest coverage > 3x | **YES** |
| LT13 | Business understandable | No |

#### Step 6: Data Extraction Pipeline API ✅
**File Modified**: `backend/server.py`

Added new endpoints:
- `GET /api/extraction/status` - Pipeline availability
- `GET /api/extraction/fields` - 160 field definitions
- `POST /api/extraction/run` - Trigger extraction

---

## 📁 File Structure & Purpose

### Backend Files

| File | Purpose | Key Functions |
|------|---------|---------------|
| `server.py` | Main API server | All REST endpoints, WebSocket support |
| `scoring_engine.py` | 4-tier scoring system | `generate_analysis()`, `check_deal_breakers()`, `apply_risk_penalties()`, `apply_quality_boosters()`, `generate_investment_checklists()` |
| `mock_data.py` | Mock data generation | `generate_stock_data()`, `generate_fundamentals()`, `generate_technicals()` |
| `llm_service.py` | GPT-4o integration | `generate_stock_insight()`, `summarize_news()` |
| `alerts_service.py` | Price alerts | Alert creation, checking, notifications |

### Data Extraction Files

| File | Purpose |
|------|---------|
| `config/field_definitions.py` | 160 field definitions with metadata |
| `extractors/yfinance_extractor.py` | Yahoo Finance data extraction |
| `extractors/nse_extractor.py` | NSE bhavcopy parsing |
| `pipeline/orchestrator.py` | Pipeline coordination |
| `processors/data_cleaner.py` | Data cleaning & normalization |
| `quality/validator.py` | Data quality checks |

### Frontend Files

| File | Purpose |
|------|---------|
| `pages/Dashboard.jsx` | Market overview, indices, FII/DII |
| `pages/StockAnalyzer.jsx` | Stock analysis with tabs (Fundamentals, Technicals, Valuation, Checklist, Scenarios) |
| `pages/Screener.jsx` | Custom stock screening |
| `pages/Watchlist.jsx` | Watchlist management |
| `pages/Portfolio.jsx` | Portfolio tracking with P&L |
| `pages/NewsHub.jsx` | News aggregation |
| `pages/Reports.jsx` | Report generation |
| `components/Charts.jsx` | Price and volume charts |
| `components/ScoreCard.jsx` | Score visualization |

---

## 🔌 API Endpoints Reference

### Stock Analysis
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/stocks` | GET | List all stocks with filters |
| `/api/stocks/{symbol}` | GET | Full stock analysis with scoring |
| `/api/stocks/{symbol}/llm-insight` | POST | AI-powered insights |

### Market Data
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/market/overview` | GET | Indices, breadth, FII/DII |

### User Features
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/watchlist` | GET/POST/DELETE | Watchlist CRUD |
| `/api/portfolio` | GET/POST/PUT/DELETE | Portfolio CRUD |
| `/api/screener` | POST | Custom screening |

### Data Extraction
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/extraction/status` | GET | Pipeline status |
| `/api/extraction/fields` | GET | 160 field definitions |
| `/api/extraction/run` | POST | Trigger extraction |

### Data Pipeline (Groww API) - NEW
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/pipeline/status` | GET | Pipeline status & metrics |
| `/api/pipeline/test-api` | POST | Test Groww API connection |
| `/api/pipeline/run` | POST | Trigger extraction job |
| `/api/pipeline/scheduler/start` | POST | Start auto-scheduler |
| `/api/pipeline/scheduler/stop` | POST | Stop scheduler |
| `/api/pipeline/scheduler/config` | PUT | Update scheduler settings |
| `/api/pipeline/jobs` | GET | List extraction jobs |
| `/api/pipeline/jobs/{job_id}` | GET | Get job details |
| `/api/pipeline/history` | GET | Job history |
| `/api/pipeline/logs` | GET | Pipeline event logs |
| `/api/pipeline/metrics` | GET | Detailed API metrics |
| `/api/pipeline/data-summary` | GET | Extracted data summary |
| `/api/pipeline/default-symbols` | GET | Tracked symbols |
| `/api/pipeline/symbol-categories` | GET | Symbols by category |
| `/api/pipeline/symbols/add` | POST | Add new symbols |
| `/api/pipeline/symbols/remove` | POST | Remove symbols |

---

## 📊 Scoring System Documentation

### 4-Tier Rule Hierarchy

```
┌─────────────────────────────────────────────────────────────┐
│ TIER 1: DEAL-BREAKERS (D1-D10)                              │
│ If ANY triggered → Score capped at 35, verdict = AVOID      │
├─────────────────────────────────────────────────────────────┤
│ TIER 2: RISK PENALTIES (R1-R10)                             │
│ Cumulative deductions from base score                        │
├─────────────────────────────────────────────────────────────┤
│ TIER 3: QUALITY BOOSTERS (Q1-Q9)                            │
│ Cumulative additions, capped at +30 total                   │
├─────────────────────────────────────────────────────────────┤
│ TIER 4: ML ADJUSTMENT                                        │
│ ±10 points based on ML model confidence                     │
└─────────────────────────────────────────────────────────────┘
```

### Score Interpretation

| Score Range | Verdict | Interpretation |
|-------------|---------|----------------|
| 80-100 | STRONG BUY | Excellent opportunity |
| 65-79 | BUY | Good candidate |
| 50-64 | HOLD | Neutral, wait for clarity |
| 35-49 | AVOID | Below average, risks exist |
| 0-34 | STRONG AVOID | Poor quality or deal-breaker |

---

## 🔄 Data Extraction Pipeline

### Live Data Pipeline (Groww API) - NEW

The platform now supports live market data extraction via the official Groww Trading API.

#### Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    GROWW API PIPELINE                        │
├─────────────────────────────────────────────────────────────┤
│  GrowwAPIExtractor                                           │
│  ├── JWT Authentication with X-API-VERSION header           │
│  ├── Rate Limiting (10/sec, 300/min)                        │
│  ├── Retry Mechanism (5 retries, exponential backoff)       │
│  └── Metrics Tracking (latency, success rate, errors)       │
├─────────────────────────────────────────────────────────────┤
│  DataPipelineService                                         │
│  ├── Scheduler (auto-start, configurable interval)          │
│  ├── Job Management (create, track, history)                │
│  ├── Symbol Management (143 symbols, 3 categories)          │
│  └── Logging & Audit Trail                                   │
├─────────────────────────────────────────────────────────────┤
│  Monitoring Dashboard                                        │
│  ├── Real-time Status Display                               │
│  ├── API Metrics Visualization                              │
│  ├── Job History & Logs                                     │
│  └── Data Quality Alerts                                    │
└─────────────────────────────────────────────────────────────┘
```

#### Symbol Categories (143 Total)
| Category | Count | Color Code | Examples |
|----------|-------|------------|----------|
| NIFTY 50 | 50 | Blue | RELIANCE, TCS, HDFCBANK, INFY |
| NIFTY Next 50 | 50 | Purple | ADANIGREEN, AMBUJACEM, DMART |
| Mid & Small Caps | 43 | Green | AUROPHARMA, PERSISTENT, MRF |

#### Pipeline Performance Metrics
| Metric | Value |
|--------|-------|
| API Success Rate | ~95%+ |
| Average Latency | 300-350ms |
| Scheduler Interval | 15 minutes (configurable) |
| Max Retries | 5 with exponential backoff |
| Rate Limit | 10 req/sec, 300 req/min |

### 160 Fields Across 13 Categories

| Category | Field Count | Examples |
|----------|-------------|----------|
| Stock Master | 14 | symbol, company_name, isin, sector |
| Price & Volume | 13 | open, high, low, close, volume |
| Derived Metrics | 11 | daily_return, 52w_high, volume_ratio |
| Income Statement | 18 | revenue, net_profit, eps, margins |
| Balance Sheet | 17 | assets, liabilities, equity, debt |
| Cash Flow | 8 | OCF, FCF, capex, dividends |
| Financial Ratios | 11 | ROE, ROA, D/E, interest coverage |
| Valuation | 17 | P/E, P/B, EV/EBITDA, market cap |
| Shareholding | 10 | promoter, FII, DII, pledging |
| Corporate Actions | 10 | dividends, splits, buybacks |
| News & Sentiment | 8 | headlines, sentiment scores |
| Technical | 15 | SMA, RSI, MACD, Bollinger |
| Qualitative | 8 | moat, management, risks |

### Extraction Sources

| Source | Data Type |
|--------|-----------|
| Yahoo Finance (yfinance) | Price, fundamentals, institutional |
| NSE Bhavcopy | Daily OHLCV, delivery data |
| Screener.in | Fundamentals (scrape) |
| RSS Feeds | News headlines |
| Calculated | Derived metrics, technical indicators |

---

## 🧪 Testing & Quality Assurance

### Backend Testing
- All API endpoints tested with curl/pytest
- Scoring engine validation for all 29 rules
- Investment checklists structure validation
- Data extraction pipeline verification

### Test Results Summary
| Component | Tests | Passed | Status |
|-----------|-------|--------|--------|
| Deal-Breakers D1-D10 | 10 | 10 | ✅ |
| Risk Penalties R1-R10 | 10 | 10 | ✅ |
| Quality Boosters Q1-Q9 | 9 | 9 | ✅ |
| Confidence Scoring | 4 | 4 | ✅ |
| Investment Checklists | 23 | 23 | ✅ |
| Extraction Pipeline | 3 | 3 | ✅ |

---

## 📝 Changelog

### Version 2.1 (February 2026 - Latest Session)
- ✅ **Groww API Integration** - Live Indian stock market data pipeline
  - Connected to official Groww Trading API with JWT authentication
  - Implemented retry mechanism with exponential backoff (5 max retries)
  - Rate limiting (10 req/sec, 300 req/min) with automatic throttling
  - API validation and health checks on startup
  
- ✅ **Expanded Stock Symbol Tracking (30 → 143 symbols)**
  - NIFTY 50 (50 stocks): RELIANCE, TCS, HDFCBANK, INFY, etc.
  - NIFTY Next 50 (50 stocks): ADANIGREEN, AMBUJACEM, BANKBARODA, etc.
  - Mid & Small Caps (43 stocks): AUROPHARMA, BANDHANBNK, etc.

- ✅ **Automated Data Collection Scheduler**
  - Auto-starts on server boot (15-minute interval default)
  - Configurable interval via API endpoint
  - Background execution with full monitoring

- ✅ **Data Pipeline Monitoring Dashboard** (New Page: `/data-pipeline`)
  - Real-time pipeline status display
  - API metrics: requests, success rate, latency, retries
  - Categorized symbol display (color-coded by index)
  - Job history and event logs
  - Data quality alerts for missing/delayed data

- ✅ **New API Endpoints Added**:
  | Endpoint | Method | Description |
  |----------|--------|-------------|
  | `/api/pipeline/status` | GET | Pipeline status & metrics |
  | `/api/pipeline/test-api` | POST | Test Groww API connection |
  | `/api/pipeline/run` | POST | Trigger extraction job |
  | `/api/pipeline/scheduler/start` | POST | Start auto-scheduler |
  | `/api/pipeline/scheduler/stop` | POST | Stop scheduler |
  | `/api/pipeline/jobs` | GET | List extraction jobs |
  | `/api/pipeline/logs` | GET | Pipeline event logs |
  | `/api/pipeline/metrics` | GET | Detailed metrics |
  | `/api/pipeline/symbol-categories` | GET | Symbols by category |
  | `/api/pipeline/symbols/add` | POST | Add new symbols |
  | `/api/pipeline/symbols/remove` | POST | Remove symbols |
  | `/api/pipeline/scheduler/config` | PUT | Update scheduler config |

- ✅ **Files Added/Modified**:
  - `backend/data_extraction/extractors/grow_extractor.py` - Groww API extractor
  - `backend/services/pipeline_service.py` - Pipeline management service
  - `backend/models/pipeline_models.py` - Pydantic models for pipeline
  - `frontend/src/pages/DataPipeline.jsx` - Monitoring dashboard
  - `backend/server.py` - Added 12 new pipeline endpoints
  - `frontend/src/lib/api.js` - Added pipeline API functions

### Version 2.0 (February 2026 - Previous Session)
- ✅ Completed D1-D10 Deal-Breakers implementation
- ✅ Completed R1-R10 Risk Penalties implementation
- ✅ Completed Q1-Q9 Quality Boosters implementation
- ✅ Implemented proper Confidence Score formula
- ✅ Added Investment Checklists (Short-Term: 10, Long-Term: 13)
- ✅ Added Data Extraction Pipeline API endpoints
- ✅ Enhanced frontend Checklist tab UI

### Version 1.0 (Initial Build)
- ✅ Core 7 modules implemented
- ✅ Basic scoring system
- ✅ Mock data for 40 stocks
- ✅ GPT-4o integration
- ✅ Data extraction framework (160 fields)

---

## 🔗 Related Documentation

- `/app/Documentation/MD folder/Stock_Analysis_Framework.md` - Detailed scoring rules
- `/app/Documentation/MD folder/Stock_Analysis_Platform_Architecture.md` - Architecture details
- `/app/Documentation/MD folder/Stock_Platform_Tech_Stack.md` - Technology stack
- `/app/memory/PRD.md` - Product Requirements Document
- `/app/test_result.md` - Testing protocol and results

---

*Document maintained as part of StockPulse development history.*
