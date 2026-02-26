# StockPulse — Complete Data Requirements Specification

**Version:** 3.0  
**Platform:** StockPulse — Indian Stock Analysis Platform  
**Scope:** Core 160 fields + Extended parameters for ML, strategies, analysis & prediction  
**Last Updated:** February 2026  

---

## 1. System Objectives and Methodology

The **StockPulse** system is designed to **maximize prediction capabilities** and **stock-picking efficiency** through a multi-layered analysis approach:

| Layer | Component | Description |
|-------|-----------|-------------|
| **Data Layer** | Multi-Source Ingestion | Real-time and historical data from NSE/BSE, Screener, News, and Alternative sources. |
| **Analysis Layer** | Quantitative & Qualitative | Combining **200+ financial ratios** with NLP-driven sentiment and management quality scores. |
| **AI Layer** | Machine Learning Models | Utilizing LSTM, XGBoost, and Transformers for trend prediction and anomaly detection. |
| **Strategy Layer** | Portfolio Optimization | Implementing **Hierarchical Risk Parity (HRP)** and **Factor-based ranking** for best returns. |

This document specifies all data parameters required to feed each layer.

---

## Executive Summary

This document is the **definitive reference** for all data parameters required by StockPulse: core analysis, screening, **strategies**, **ML models**, **backtesting**, **AI analysis**, and **prediction**. Parameters are organised by **extraction frequency** (for pipeline scheduling) and by **category** (for implementation and validation).

| Priority            | Count  | Description                                  | Implementation      |
|---------------------|--------|----------------------------------------------|---------------------|
| **Critical**        | **58** | System cannot function without these         | Phase 1 — Before Go-Live |
| **Important**       | **52** | Significantly improves analysis quality      | Phase 2 — First month   |
| **Standard**        | **35** | Enhances features, ML & strategies           | Phase 3 — Within 3 months |
| **Optional**        | **7**  | Future advanced features                     | Phase 4 — Future        |
| **Metadata**        | **3**  | System tracking for confidence scoring       | Phase 2                 |
| **Qualitative**     | **5**  | Manual or LLM-generated assessment            | Phase 3                 |
| **Extended (ML/AI)**| **55** | ML features, strategies, prediction, AI      | Phase 3–4               |
| **TOTAL (Core)**    | **160**| Complete platform base requirements           | —                      |
| **TOTAL (Incl. Extended)** | **215** | Maximum parameters for best return & prediction | —                |

---

## Part 1 — Extraction Frequency Guide

Use this to schedule extraction jobs and feed the system at the right cadence.

| Frequency      | Description                    | Typical Schedule           | Use Case                          |
|----------------|--------------------------------|----------------------------|-----------------------------------|
| **CONTINUOUS** | Updated on every write/event   | On every pipeline run      | Metadata, confidence, system state |
| **REAL_TIME**  | As soon as data is available   | Every 1–5 min (market hrs) | News, sentiment, live LTP/depth   |
| **HOURLY**     | Once per hour                  | 0 * * * * (cron)           | Optional: intraday aggregates     |
| **DAILY**      | After market close (EOD)       | 18:00 IST                  | OHLCV, technicals, valuations    |
| **WEEKLY**     | Once per week                  | Sunday 00:00               | Sector/industry peer averages     |
| **MONTHLY**     | Once per month                 | 1st of month               | Optional macro, monthly rolls     |
| **QUARTERLY**  | After results season           | 45 days after quarter end  | Income, ratios, shareholding      |
| **ANNUAL**     | After annual reports           | 90 days after FY end       | Balance sheet, cash flow          |
| **ON_EVENT**   | When event occurs              | Trigger-based / polling    | Corporate actions, earnings, SEBI |
| **ONCE / NEVER** | One-time or rare change      | On listing / manual        | Listing date, company static info |

---

## Part 2 — Parameters by Extraction Frequency

### 2.1 CONTINUOUS (3 parameters)

System-generated; updated whenever related data is written.

| #   | Field Name             | Type   | Used For                    | Priority   |
|-----|------------------------|--------|-----------------------------|------------|
| 158 | field_availability     | Dict   | Confidence: data completeness (40%) | Metadata |
| 159 | field_last_updated     | Dict   | Confidence: data freshness (30%)    | Metadata |
| 160 | multi_source_values   | Dict   | Confidence: source agreement (15%) | Metadata |

---

### 2.2 CONTINUOUS / REAL-TIME (Intraday)

*Required for high-frequency monitoring and intraday sentiment analysis.*

**Live market data (NSE/BSE or broker feed)**

| #    | Field Name               | Type   | Used For              | Source      | Priority   |
|------|--------------------------|--------|------------------------|-------------|------------|
| 161  | last_traded_price        | Decimal| Live LTP               | NSE/BSE / DHAN/Broker | Important  |
| 162  | market_depth_bid_ask     | Object | Order book depth, bid-ask spread | DHAN/Broker | Standard   |
| 216  | bid_ask_spread           | Decimal| Liquidity / cost       | NSE/BSE Feed | Standard   |
| 217  | tick_volume              | Integer| Tick-by-tick volume   | NSE/BSE Feed | Optional   |

**News & sentiment (RSS, Social APIs)**

| #    | Field Name               | Type   | Used For              | Source      | Priority   |
|------|--------------------------|--------|------------------------|-------------|------------|
| 130  | news_headline            | String | Breaking news display  | RSS Feeds   | Important  |
| 131  | news_body_text           | String | Full sentiment (NLP)   | RSS Feeds   | Important  |
| 132  | news_source              | String | Source credibility     | RSS Feeds   | Standard   |
| 133  | news_timestamp           | DateTime | Recency weight       | RSS Feeds   | Important  |
| 134  | news_sentiment_score     | Decimal | Sentiment polarity score | Calculated/NLP | Important |
| 135  | stock_tickers_mentioned | List   | Stock tagging          | NLP         | Standard   |
| 163  | social_mentions_7d       | Integer | Social media (Twitter/Reddit) | Social APIs | Optional   |
| 164  | forum_sentiment_avg      | Decimal | Forums / Valuepickr   | Scrape      | Optional   |

**Credit & system health**

| #    | Field Name               | Type   | Used For              | Source      | Priority   |
|------|--------------------------|--------|------------------------|-------------|------------|
| 136  | credit_rating            | String | D9 deal-breaker        | Rating Agencies | Important |
| 137  | credit_outlook           | Enum   | Credit trend           | Rating Agencies | Standard   |
| 218  | api_latency_ms           | Integer| System health          | Internal Logs | Optional   |
| 219  | data_ingestion_rate      | Decimal| System health          | Internal Logs | Optional   |
| 220  | model_inference_time_ms  | Integer| System health          | Internal Logs | Optional   |

---

### 2.3 HOURLY / PERIODIC (Intraday)

*Used for mid-day trend adjustments and momentum tracking.*

| Parameter Category | Data Fields | Primary Source |
|--------------------|-------------|----------------|
| **Intraday technicals** | Hourly RSI, MACD crossovers (hourly), VWAP (intraday) | Calculated from tick/1-min data |
| **Market breadth** | Advance-Decline ratio (hourly), Sectoral heatmap, VIX / India VIX fluctuations | NSE / Calculated |

| #   | Field Name                | Used For              | Source     |
|-----|---------------------------|------------------------|------------|
| 221 | rsi_hourly                | Intraday momentum      | Calculated |
| 222 | macd_crossover_hourly    | Intraday signal        | Calculated |
| 223 | vwap_intraday             | Hourly VWAP            | NSE / Calculated |
| 224 | advance_decline_ratio     | Market breadth         | NSE / Calculated |
| 225 | sectoral_heatmap          | Sector strength intraday | NSE / Calculated |
| 226 | india_vix                 | Volatility index       | NSE        |

---

### 2.4 DAILY (End of Day)

EOD price, derived metrics, valuation, technicals, and daily ML/strategy features. **Extract after market close (e.g. 18:00 IST).**

**Price & volume (13)**  
| #   | Field Name           | Type   | Used For              | Source        |
|-----|----------------------|--------|------------------------|---------------|
| 15  | date                 | Date   | Time series key         | NSE Bhavcopy  |
| 16  | open                 | Decimal| Candlestick, gap        | NSE Bhavcopy  |
| 17  | high                 | Decimal| Range, resistance        | NSE Bhavcopy  |
| 18  | low                  | Decimal| Range, support          | NSE Bhavcopy  |
| 19  | close                | Decimal| All calculations        | NSE Bhavcopy  |
| 20  | adjusted_close       | Decimal| Accurate returns        | yfinance     |
| 21  | volume               | Integer| Liquidity, D10          | NSE Bhavcopy  |
| 22  | delivery_volume      | Integer| Genuine buying         | NSE Bhavcopy  |
| 23  | delivery_percentage  | Decimal| Buyer conviction        | NSE Bhavcopy  |
| 24  | turnover             | Decimal| Value traded            | NSE Bhavcopy  |
| 25  | trades_count         | Integer| Participation breadth   | NSE Bhavcopy  |
| 26  | prev_close           | Decimal| Daily change            | NSE Bhavcopy  |
| 27  | vwap                 | Decimal| Institutional benchmark | NSE          |

**Derived price metrics (11)**  
| #   | Field Name               | Formula / Logic              | Used For              |
|-----|---------------------------|------------------------------|------------------------|
| 28  | daily_return_pct          | (close − prev_close) / prev_close × 100 | Return, volatility, ML |
| 29  | return_5d_pct             | (close − close_5d_ago) / close_5d_ago × 100 | 5d momentum      |
| 30  | return_20d_pct            | (close − close_20d_ago) / close_20d_ago × 100 | 20d momentum   |
| 31  | return_60d_pct            | (close − close_60d_ago) / close_60d_ago × 100 | 60d momentum   |
| 32  | day_range_pct             | (high − low) / low × 100     | Intraday volatility   |
| 33  | gap_percentage            | (open − prev_close) / prev_close × 100 | Gap detection   |
| 34  | week_52_high              | MAX(high) over 252 days      | Technical, Q8         |
| 35  | week_52_low               | MIN(low) over 252 days       | Support               |
| 36  | distance_from_52w_high    | (52w_high − close) / 52w_high × 100 | R6 penalty    |
| 37  | volume_ratio              | volume / avg_volume_20d      | Volume spike, ML      |
| 38  | avg_volume_20d            | AVG(volume) over 20 days     | D10 deal-breaker      |

**Valuation (17)** — depend on daily close + fundamentals  
| #   | Field Name             | Used For           | #   | Field Name                | Used For            |
|-----|------------------------|--------------------|-----|---------------------------|---------------------|
| 93  | market_cap             | Size, EV           | 102 | dividend_yield            | Income investing    |
| 94  | enterprise_value        | EV/EBITDA          | 103 | fcf_yield                 | Q9 booster          |
| 95  | pe_ratio               | Valuation, R8      | 104 | earnings_yield            | Bond comparison     |
| 96  | pe_ratio_forward        | Forward valuation  | 105 | sector_avg_pe             | R8 (P/E vs sector)  |
| 97  | peg_ratio              | Growth-adjusted    | 106 | sector_avg_roe             | Sector benchmark    |
| 98  | pb_ratio               | Asset-based val    | 107 | industry_avg_pe           | Industry comparison |
| 99  | ps_ratio               | Revenue-based val  | 108 | historical_pe_median      | Historical val      |
| 100 | ev_to_ebitda           | Valuation scoring  | 109 | sector_performance        | Sector strength     |
| 101 | ev_to_sales             | Revenue-based EV   |     |                           |                     |

**Technical indicators (15 + Ichimoku)** — calculated from OHLCV (pandas-ta)  
| #   | Field Name         | #   | Field Name         | #   | Field Name          |
|-----|--------------------|-----|--------------------|-----|---------------------|
| 138 | sma_20             | 143 | rsi_14             | 148 | atr_14              |
| 139 | sma_50             | 144 | macd               | 149 | adx_14              |
| 140 | sma_200            | 145 | macd_signal        | 150 | obv                 |
| 141 | ema_12             | 146 | bollinger_upper    | 151 | support_level       |
| 142 | ema_26             | 147 | bollinger_lower    | 152 | resistance_level    |
| 227 | ichimoku_tenkan     | 228 | ichimoku_kijun     | 229 | ichimoku_senkou_a_b | Trend (Ichimoku Cloud) |

**Extended — daily ML / strategy (22)**  
| #   | Field Name               | Used For                          | Source/Method     |
|-----|--------------------------|------------------------------------|-------------------|
| 165 | realized_volatility_10d  | Volatility forecast, GARCH, risk   | Calculated        |
| 166 | realized_volatility_20d  | ML feature, risk                   | Calculated        |
| 167 | return_1d_pct            | Same as daily_return_pct           | Calculated        |
| 168 | return_3d_pct            | Short momentum                     | Calculated        |
| 169 | return_10d_pct           | Momentum (XGBoost/LSTM)            | Calculated        |
| 170 | momentum_rank_sector     | Relative strength vs sector        | Calculated        |
| 171 | price_vs_sma20_pct       | Distance from SMA20                | Calculated        |
| 172 | price_vs_sma50_pct       | Distance from SMA50                | Calculated        |
| 173 | volume_zscore            | Unusual volume (anomaly)           | Calculated        |
| 174 | volatility_percentile_1y  | Vol regime                         | Calculated        |
| 175 | stoch_k                  | Stochastic %K (strategies)         | pandas-ta         |
| 176 | stoch_d                  | Stochastic %D (strategies)         | pandas-ta         |
| 177 | cci_20                   | Commodity Channel Index            | pandas-ta         |
| 178 | williams_r                | Williams %R                       | pandas-ta         |
| 179 | cmf                      | Chaikin Money Flow                 | pandas-ta         |
| 180 | macd_histogram           | MACD − Signal (backtest)           | Calculated        |
| 181 | turnover_20d_avg         | Liquidity feature                  | Calculated        |
| 182 | free_float_market_cap    | Float size (ML)                    | Calculated        |
| 183 | days_since_earnings      | Event feature (ML)                 | Calculated        |
| 184 | days_to_earnings         | Event feature (ML)                 | Calculated        |
| 185 | trading_day_of_week      | Calendar feature (optional)        | System            |
| 186 | nifty_50_return_1m       | Index momentum (optional)          | NSE Indices       |
| 230 | fii_net_activity_daily   | FII buy/sell (₹ Cr)                | NSE / BSE         |
| 231 | dii_net_activity_daily   | DII buy/sell (₹ Cr)                | NSE / BSE         |
| 232 | sp500_return_1d          | Global market (S&P 500)            | Yahoo Finance     |
| 233 | nasdaq_return_1d         | Global market (Nasdaq)             | Yahoo Finance     |

**Risk & performance metrics — per-stock (rolling, optional advanced)**  
*These are calculated from historical daily returns and index benchmarks to support risk-adjusted ranking and portfolio construction. They are **additional** to the original 215-parameter set.*

| #   | Field Name               | Window / Logic                                            | Used For                           |
|-----|--------------------------|-----------------------------------------------------------|------------------------------------|
| 249 | beta_1y                  | Cov(stock, index) / Var(index), 1Y daily returns         | Systematic risk vs Nifty/sector   |
| 250 | beta_3y                  | Same as beta_1y over 3Y (if history available)           | Long-term risk profile            |
| 251 | max_drawdown_1y          | Max peak-to-trough fall on 1Y equity curve               | Drawdown risk                     |
| 252 | sharpe_ratio_1y          | Annualised excess return / volatility, 1Y daily returns  | Risk-adjusted return (overall)    |
| 253 | sortino_ratio_1y         | Excess return / downside deviation, 1Y daily returns     | Downside-risk-adjusted return     |
| 254 | information_ratio_1y     | Active return vs index / tracking error, 1Y              | Alpha quality vs benchmark        |
| 255 | rolling_volatility_30d   | Std dev of daily returns over last 30 trading days       | Short-term risk regime            |
| 256 | downside_deviation_1y    | Std dev of negative returns only, 1Y                     | Tail risk                         |

---

### 2.5 WEEKLY

*Medium-term trends and broader market shifts.*

| Parameter Category | Data Fields | Primary Source |
|--------------------|-------------|----------------|
| **Trend analysis** | Weekly MA crossovers, Support/Resistance (weekly) | Calculated |
| **Sector/peer** | Sector avg P/E, Sector avg ROE, Industry avg P/E | Screener.in |
| **Alternative data** | Google Trends (stock-specific keywords), Job postings growth | Google Trends / LinkedIn |

| #   | Field Name       | Used For              | Source     |
|-----|------------------|------------------------|------------|
| 105 | sector_avg_pe    | R8 (P/E vs sector)     | Screener.in |
| 106 | sector_avg_roe   | Sector benchmark       | Screener.in |
| 107 | industry_avg_pe  | Industry comparison    | Screener.in |
| 234 | sma_weekly_crossover  | Weekly trend signal   | Calculated |
| 235 | support_resistance_weekly | Weekly S/R levels  | Calculated |
| 236 | google_trends_score    | Search interest (stock keywords) | Google Trends |
| 237 | job_postings_growth   | Hiring trend (sector/company) | LinkedIn / Scrape |

---

### 2.6 MONTHLY

*Macroeconomic and sectoral health indicators.*

| Parameter Category | Data Fields | Primary Source |
|--------------------|-------------|----------------|
| **Macro indicators** | CPI inflation, IIP (Industrial Production), RBI Repo Rate, USD/INR | RBI / MOSPI |
| **Commodity prices** | Crude (Brent), Gold, Steel, Copper | MCX / Bloomberg / Yahoo |

| #   | Field Name           | Used For        | Source     |
|-----|----------------------|-----------------|------------|
| 238 | cpi_inflation        | Macro context   | RBI / MOSPI |
| 239 | iip_growth           | Industrial production | MOSPI  |
| 240 | rbi_repo_rate        | Rate environment| RBI        |
| 241 | usdinr_rate          | FX / FII context| RBI / Yahoo |
| 242 | crude_brent_price    | Commodity       | MCX / Yahoo |
| 243 | gold_price           | Safe-haven      | MCX / Yahoo |
| 244 | steel_price          | Commodity       | MCX / Bloomberg |
| 245 | copper_price         | Commodity       | MCX / Bloomberg |

---

### 2.7 QUARTERLY (18 + 11 + 10 + 4 = 43 parameters)

Income statement, financial ratios, shareholding, and quarterly valuation/earnings. **Extract within 45 days of quarter end.**

**Income statement (18)**  
| #   | Field Name             | #   | Field Name           | #   | Field Name          |
|-----|------------------------|-----|----------------------|-----|---------------------|
| 39  | revenue                | 46  | net_profit           | 53  | ebit                |
| 40  | revenue_growth_yoy      | 47  | net_profit_margin    | 54  | other_income        |
| 41  | revenue_growth_qoq      | 48  | eps                  | 55  | tax_expense         |
| 42  | operating_profit       | 49  | eps_growth_yoy        | 56  | effective_tax_rate  |
| 43  | operating_margin        | 50  | interest_expense     |     |                     |
| 44  | gross_profit           | 51  | depreciation         |     |                     |
| 45  | gross_margin           | 52  | ebitda               |     |                     |

**Financial ratios (11)**  
| #   | Field Name           | #   | Field Name            | #   | Field Name             |
|-----|----------------------|-----|------------------------|-----|-------------------------|
| 82  | roe                  | 86  | interest_coverage      | 90  | inventory_turnover     |
| 83  | roa                  | 87  | current_ratio          | 91  | receivables_turnover    |
| 84  | roic                 | 88  | quick_ratio            | 92  | dividend_payout_ratio   |
| 85  | debt_to_equity       | 89  | asset_turnover         |     |                         |

**Shareholding (10)**  
| #   | Field Name               | #   | Field Name             |
|-----|--------------------------|-----|-------------------------|
| 110 | promoter_holding         | 116 | fii_holding_change      |
| 111 | promoter_pledging        | 117 | num_shareholders        |
| 112 | fii_holding              | 118 | mf_holding              |
| 113 | dii_holding              | 119 | insurance_holding       |
| 114 | public_holding           |     |                         |
| 115 | promoter_holding_change  |     |                         |

**Extended — quarterly (4) + management (2)**  
| #   | Field Name             | Used For              | Source      |
|-----|------------------------|------------------------|-------------|
| 187 | earnings_surprise_pct   | Earnings beat/miss (ML)| Screener/BSE |
| 188 | analyst_rating_consensus| Consensus (AI/ML)      | Trendlyne/Broker |
| 189 | target_price_consensus | Target (AI/ML)         | Trendlyne/Broker |
| 190 | num_analysts           | Coverage               | Trendlyne/Broker |
| 246 | concall_transcript_available | Concall text for NLP | Manual / Filings |
| 247 | management_guidance_sentiment_score | Guidance tone (LLM) | Manual / LLM |

---

### 2.8 ANNUAL (17 + 8 + 4 = 29 parameters)

Balance sheet, cash flow, and annual-only ratios. **Extract within 90 days of FY end.**

**Balance sheet (17)**  
| #   | Field Name               | #   | Field Name             | #   | Field Name                |
|-----|--------------------------|-----|-------------------------|-----|----------------------------|
| 57  | total_assets             | 64  | current_assets          | 71  | reserves_and_surplus      |
| 58  | total_equity             | 65  | current_liabilities     | 72  | book_value_per_share      |
| 59  | total_debt               | 66  | inventory               | 73  | contingent_liabilities    |
| 60  | long_term_debt           | 67  | receivables             |     |                            |
| 61  | short_term_debt           | 68  | payables                |     |                            |
| 62  | cash_and_equivalents     | 69  | fixed_assets            |     |                            |
| 63  | net_debt                 | 70  | intangible_assets       |     |                            |

**Cash flow (8)**  
| #   | Field Name               | #   | Field Name             |
|-----|--------------------------|-----|-------------------------|
| 74  | operating_cash_flow      | 78  | free_cash_flow          |
| 75  | investing_cash_flow      | 79  | dividends_paid          |
| 76  | financing_cash_flow      | 80  | debt_repayment          |
| 77  | capital_expenditure       | 81  | equity_raised           |

**Extended — annual (4)**  
| #   | Field Name               | Used For           | Source      |
|-----|--------------------------|--------------------|-------------|
| 191 | revenue_5y_cagr          | Long-term growth   | Calculated  |
| 192 | eps_5y_cagr              | EPS growth trend   | Calculated  |
| 193 | roe_5y_avg               | Consistency        | Calculated  |
| 194 | fcf_3y_avg               | Cash stability     | Calculated  |

---

### 2.9 ON_EVENT (10 + 5 qualitative = 15 parameters)

Corporate actions, events, and qualitative assessments. **Extract when event occurs or on change.**

**Corporate actions & events (10)**  
| #   | Field Name           | #   | Field Name           |
|-----|----------------------|-----|----------------------|
| 120 | dividend_per_share    | 126 | next_earnings_date   |
| 121 | ex_dividend_date     | 127 | pending_events       |
| 122 | stock_split_ratio    | 128 | stock_status         |
| 123 | bonus_ratio          | 129 | sebi_investigation   |
| 124 | rights_issue_ratio   |     |                      |
| 125 | buyback_details      |     |                      |

**Qualitative & metadata (5 + 3 system)**  
| #   | Field Name                   | Input Method   | Used For           |
|-----|------------------------------|----------------|--------------------|
| 153 | moat_assessment               | Manual/LLM     | Competitive moat   |
| 154 | management_assessment         | Manual/LLM     | Management track   |
| 155 | industry_growth_assessment   | Manual/LLM     | Industry tailwinds |
| 156 | disruption_risk              | Manual/LLM     | Disruption risk    |
| 157 | fraud_history                | Manual/News    | No accounting fraud|

---

### 2.10 YEARLY / ONCE (Master & structural data)

*Structural data and long-term assessment. Extract on listing or when changed (rare).*

| Parameter Category | Data Fields | Primary Source |
|--------------------|-------------|----------------|
| **Master data** | Company Name, ISIN, Sector, Industry, Listing Date, Face Value | NSE/BSE |
| **Balance sheet (annual)** | Total Assets, Long-term Debt, Share Capital, Reserves | Annual Reports / Screener |
| **Qualitative moat** | Competitive advantage description, Regulatory risk assessment | Manual / Research / LLM |

**Stock master (14)**  
| #   | Field Name             | Type   | When to Update   | Source        |
|-----|------------------------|--------|------------------|---------------|
| 1   | symbol                 | String | On listing        | NSE/BSE       |
| 2   | company_name           | String | On change         | NSE/BSE       |
| 3   | isin                   | String(12) | Never         | NSE/BSE       |
| 4   | nse_code               | String | On change         | NSE           |
| 5   | bse_code               | String | On change         | BSE           |
| 6   | sector                 | String | On change         | Screener.in   |
| 7   | industry               | String | On change         | Screener.in   |
| 9   | listing_date           | Date   | Never             | NSE/BSE       |
| 10  | face_value              | Decimal| On split          | NSE/BSE       |
| 13  | website                | URL    | Never             | Screener.in   |
| 14  | registered_office      | String | Never             | BSE           |

**Updated daily (but reference data):**  
| #   | Field Name             | Source     |
|-----|------------------------|------------|
| 8   | market_cap_category    | Calculated |
| 11  | shares_outstanding     | BSE Filings (quarterly) |
| 12  | free_float_shares      | BSE Filings (quarterly) |

**Qualitative (yearly/on event):**  
| #   | Field Name                   | Used For                        | Source      |
|-----|------------------------------|----------------------------------|-------------|
| 153 | moat_assessment               | Competitive advantage description | Manual/LLM |
| 248 | regulatory_risk_assessment   | Regulatory risk (SEBI, sector)  | Manual/LLM  |

---

### 2.11 DERIVATIVES (F&O) — Daily / Intraday (Optional but Recommended)

*Futures and options data to capture market positioning, sentiment, and implied volatility. These fields are recommended for advanced strategies and ML models and are **additional** to the original 215-parameter set.*

**Futures positioning (index and stock futures)**  
| #   | Field Name                | Frequency   | Used For                                   | Source            |
|-----|---------------------------|------------|--------------------------------------------|-------------------|
| 257 | futures_oi                | Daily EOD  | Overall positioning (long/short interest)  | NSE F&O           |
| 258 | futures_oi_change_pct     | Daily EOD  | OI build-up/unwinding classification       | Calculated (Δ OI) |
| 259 | futures_price_near        | Daily EOD  | Near-month futures price                   | NSE F&O           |
| 260 | futures_basis_pct         | Daily EOD  | (Futures − Spot) / Spot × 100              | Calculated        |
| 261 | fii_index_futures_long_oi | Daily EOD  | FII long index futures positioning         | NSE / SEBI data   |
| 262 | fii_index_futures_short_oi| Daily EOD  | FII short index futures positioning        | NSE / SEBI data   |

**Options sentiment & implied volatility**  
| #   | Field Name               | Frequency   | Used For                                   | Source            |
|-----|--------------------------|------------|--------------------------------------------|-------------------|
| 263 | options_call_oi_total    | Daily EOD  | Total call OI (nearest expiries)           | NSE Option Chain  |
| 264 | options_put_oi_total     | Daily EOD  | Total put OI (nearest expiries)            | NSE Option Chain  |
| 265 | put_call_ratio_oi        | Daily EOD  | Sentiment via OI (PCR OI)                  | Calculated        |
| 266 | put_call_ratio_volume    | Daily EOD  | Sentiment via traded volume (PCR Volume)   | Calculated        |
| 267 | options_max_pain_strike  | Daily EOD  | Max pain strike for nearest expiry         | Calculated        |
| 268 | iv_atm_pct               | Daily / RT | Implied vol of nearest ATM option          | NSE Option Chain  |
| 269 | iv_percentile_1y         | Daily EOD  | Percentile of current IV vs 1Y IV history  | Calculated        |
| 270 | pcr_index_level          | Daily EOD  | Index-level PCR (e.g., Nifty/BankNifty)    | NSE F&O           |

---

## Part 3 — Parameters by Category (Quick Reference)

| #   | Category                  | Field Count | Primary Source   | History  | Frequency      |
|-----|---------------------------|-------------|------------------|----------|----------------|
| 1   | Stock Master Data         | 14          | NSE/BSE, Screener| N/A      | On change / Once |
| 2   | Price & Volume (OHLCV)    | 13          | NSE Bhavcopy     | 10 yr    | Daily          |
| 3   | Derived Price Metrics     | 11          | Calculated       | 10 yr    | Daily          |
| 4   | Income Statement          | 18          | Screener.in      | 10 yr    | Quarterly      |
| 5   | Balance Sheet             | 17          | Screener.in      | 10 yr    | Annual         |
| 6   | Cash Flow Statement       | 8           | Screener.in      | 10 yr    | Annual         |
| 7   | Financial Ratios          | 11          | Calculated       | 10 yr    | Quarterly      |
| 8   | Valuation Metrics         | 17          | Calculated       | 10 yr    | Daily/Weekly   |
| 9   | Shareholding Pattern      | 10          | BSE Filings      | 5–7 yr   | Quarterly      |
| 10  | Corporate Actions & Events| 10          | BSE/NSE         | 10 yr    | On event       |
| 11  | News & Sentiment           | 8           | RSS Feeds        | 30 days  | Real-time      |
| 12  | Technical Indicators       | 15          | pandas-ta        | 10 yr    | Daily          |
| 13  | Qualitative & Metadata     | 8           | Manual/System   | Current  | On event / Continuous |
| 14  | Extended (ML/Strategies/AI)| 55          | Mixed            | Per field| Per frequency  |
|     | **TOTAL**                  | **215**     |                  |          |                |

---

## Part 4 — Extended Parameters Summary (161–215)

These parameters support **strategies**, **ML models**, **backtesting**, **AI analysis**, and **prediction** to maximise stock-picking and return potential.

| ID Range | Group                    | Count | Frequency   | Used For                          |
|----------|---------------------------|-------|-------------|------------------------------------|
| 161–164  | Live / sentiment          | 4     | Real-time   | Broker LTP/depth, social/forum     |
| 165–186  | Daily ML & strategy       | 22    | Daily       | Volatility, momentum, technicals, events |
| 187–190  | Quarterly analyst/earnings| 4     | Quarterly   | Earnings surprise, consensus       |
| 191–194  | Annual growth/quality     | 4     | Annual      | 5y CAGRs, 5y ROE, 3y FCF          |
| 195–215  | Reserved / future         | 21    | TBD         | Additional ML, macro, alternative data |

**Full list — Extended parameters (161–215)**

| #   | Field Name                 | Frequency  | Used For                          |
|-----|----------------------------|------------|------------------------------------|
| 161 | last_traded_price          | Real-time  | Live LTP (broker API)              |
| 162 | market_depth_bid_ask       | Real-time  | Order book (broker API)            |
| 163 | social_mentions_7d         | Real-time  | Social buzz (optional)             |
| 164 | forum_sentiment_avg        | Real-time  | Forums (optional)                  |
| 165 | realized_volatility_10d    | Daily      | GARCH, risk, ML                     |
| 166 | realized_volatility_20d    | Daily      | ML, volatility forecast             |
| 167 | return_1d_pct              | Daily      | Same as daily_return_pct           |
| 168 | return_3d_pct              | Daily      | Short momentum, ML                  |
| 169 | return_10d_pct             | Daily      | Momentum, XGBoost/LSTM              |
| 170 | momentum_rank_sector       | Daily      | Relative strength                   |
| 171 | price_vs_sma20_pct         | Daily      | ML feature                         |
| 172 | price_vs_sma50_pct         | Daily      | ML feature                         |
| 173 | volume_zscore              | Daily      | Anomaly detection                   |
| 174 | volatility_percentile_1y   | Daily      | Vol regime                         |
| 175 | stoch_k                    | Daily      | Stochastic (strategies)             |
| 176 | stoch_d                    | Daily      | Stochastic (strategies)             |
| 177 | cci_20                     | Daily      | CCI (strategies)                    |
| 178 | williams_r                 | Daily      | Williams %R (strategies)             |
| 179 | cmf                        | Daily      | Chaikin Money Flow                  |
| 180 | macd_histogram             | Daily      | MACD − Signal (backtest)             |
| 181 | turnover_20d_avg           | Daily      | Liquidity feature                   |
| 182 | free_float_market_cap      | Daily      | Float size (ML)                     |
| 183 | days_since_earnings        | Daily      | Event feature (ML)                  |
| 184 | days_to_earnings           | Daily      | Event feature (ML)                  |
| 185 | trading_day_of_week        | Daily      | Calendar (optional)                |
| 186 | nifty_50_return_1m         | Daily      | Index momentum (optional)           |
| 187 | earnings_surprise_pct      | Quarterly  | Earnings beat/miss (ML)             |
| 188 | analyst_rating_consensus   | Quarterly  | Consensus (AI/ML)                   |
| 189 | target_price_consensus     | Quarterly  | Target (AI/ML)                      |
| 190 | num_analysts               | Quarterly  | Coverage                           |
| 191 | revenue_5y_cagr            | Annual     | Long-term growth                   |
| 192 | eps_5y_cagr                | Annual     | EPS growth trend                   |
| 193 | roe_5y_avg                 | Annual     | ROE consistency                    |
| 194 | fcf_3y_avg                 | Annual     | FCF stability                      |
| 195–215 | (Reserved)               | TBD        | Future ML, macro, alternative data  |

**Key uses:**

- **LSTM/GRU/Transformer:** 60-day OHLCV + technicals (existing) + realized_volatility, return_1d/3d/10d, volume_zscore, days_since_earnings.
- **XGBoost/LightGBM:** 100+ features from existing 160 + price_vs_sma, momentum_rank_sector, volatility_percentile, analyst_rating_consensus, earnings_surprise_pct.
- **Backtest strategies:** SMA crossover, RSI, MACD, Bollinger, Momentum use existing OHLCV + technicals; extended: stoch_k/d, cci_20, williams_r, cmf, macd_histogram.
- **AI/LLM analysis:** Fundamentals + news_sentiment + analyst_rating_consensus + target_price_consensus + qualitative (moat, management, disruption).
- **Risk (GARCH, VaR):** daily_return_pct, realized_volatility_10d/20d, volatility_percentile_1y.

---

## Part 5 — Primary Data Sources Summary

| Source           | Data Provided                    | Approx. Fields | Cost          | Method        |
|------------------|----------------------------------|----------------|---------------|---------------|
| **Screener.in**  | Fundamentals, ratios, 10yr, peers| 60+            | Free / ₹4k/yr | Scrape / Export |
| **NSE Bhavcopy** | EOD OHLCV, delivery               | 15             | Free          | CSV Download   |
| **BSE Filings**  | Shareholding, corp actions       | 15             | Free          | Scrape / API   |
| **Trendlyne**    | FII/DII, pledging, forward PE     | 8              | Free (limited)| Scrape         |
| **yfinance**     | Adjusted close, backup prices    | 10             | Free          | API            |
| **DHAN/Broker**  | LTP, OHLC, quote, historical      | 41             | Free (data plan) | REST API    |
| **RSS Feeds**    | News (Moneycontrol, ET, BS)      | 4              | Free          | RSS            |
| **Rating Agencies** | Credit ratings (CRISIL etc.)   | 3              | Free          | Scrape         |
| **pandas-ta / Custom** | Technicals, derived, ML features | 15+ extended | Free       | Calculated     |

---

## Part 6 — Scheduling Checklist (Pipeline Manager)

- **CONTINUOUS:** field_availability, field_last_updated, multi_source_values (on every write).
- **REAL_TIME:** News/sentiment (every 1–5 min); LTP/depth if broker API (every 1 min during market).
- **DAILY (post market):** Bhavcopy → OHLCV; then derived metrics, technicals, valuations; then extended daily ML (volatility, momentum, extra technicals).
- **WEEKLY:** Sector/industry peer averages (Screener or internal rollup).
- **QUARTERLY:** Income statement, ratios, shareholding, earnings surprise, analyst consensus (after results).
- **ANNUAL:** Balance sheet, cash flow, annual ratios, 5y CAGRs, 5y ROE, 3y FCF.
- **ON_EVENT:** Corporate actions, next_earnings_date, pending_events, stock_status, SEBI; qualitative when updated.
- **ONCE/NEVER:** Stock master (symbol, isin, sector, industry, listing_date, etc.) on listing or change.

---

---

## Inclusion checklist (System objectives & data by frequency)

All parameters from the **System Objectives and Methodology** and **Data Parameters by Frequency** spec are included in this document:

| Your section | In this doc | Parameters covered |
|--------------|-------------|--------------------|
| **1. System objectives** (Data / Analysis / AI / Strategy) | § 1. System Objectives and Methodology | 4 layers: Multi-source ingestion, 200+ ratios + NLP, LSTM/XGBoost/Transformers, HRP & factor-based ranking |
| **2.1 Continuous / Real-time** (Live market, News & sentiment, System health) | § 2.2 CONTINUOUS / REAL-TIME | LTP, bid-ask, order book depth, tick volume; news, sentiment polarity, social/forum; API latency, ingestion rate, model inference time |
| **2.2 Hourly** (Intraday technicals, Market breadth) | § 2.3 HOURLY / PERIODIC | Hourly RSI, MACD crossovers, VWAP intraday; Advance-Decline ratio, Sectoral heatmap, India VIX |
| **2.3 Daily** (Price/volume, Technicals, Valuation, Market indicators) | § 2.4 DAILY | OHLCV, delivery, VWAP; SMA/EMA, Bollinger, ATR, ADX, **Ichimoku Cloud**; P/E, P/B, EV/EBITDA, market cap, div yield; Nifty 50, **FII/DII net activity**, **S&P 500, Nasdaq** |
| **2.4 Weekly** (Trend analysis, Alternative data) | § 2.5 WEEKLY | Weekly MA crossovers, Support/Resistance (weekly); **Google Trends**, **Job postings growth** |
| **2.5 Monthly** (Macro, Commodity) | § 2.6 MONTHLY | **CPI, IIP, RBI Repo Rate, USD/INR**; **Crude (Brent), Gold, Steel, Copper** |
| **2.6 Quarterly** (Income, Shareholding, Management) | § 2.7 QUARTERLY | Income statement, EBITDA, EPS, interest coverage; Promoter/FII/DII, pledging, shareholders; **Concall transcripts**, **Management guidance sentiment score** |
| **2.7 Yearly / Once** (Master, Balance sheet, Qualitative moat) | § 2.8 ANNUAL, § 2.10 YEARLY/ONCE | Company name, ISIN, sector, industry, listing date, face value; Total assets, debt, share capital, reserves; **Competitive advantage**, **Regulatory risk assessment** |

---

*This document specifies all 160 core + extended data parameters (including objectives and frequency-based layout) for StockPulse. Use it as the single reference for the offline loader and extraction pipeline, and for feeding strategies, ML models, analysis, and prediction.*
