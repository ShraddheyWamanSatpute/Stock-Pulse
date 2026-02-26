# DHAN API Test

## How many parameters do we get from DHAN?

From the official DHAN v2 API docs, the **data** APIs return the following.

### Summary

| Endpoint | Purpose | # of response parameters |
|----------|--------|---------------------------|
| `GET /profile` | Account & token validity | **7** |
| `POST /marketfeed/ltp` | Last traded price | **3** (incl. `last_price`) |
| `POST /marketfeed/ohlc` | OHLC + LTP | **7** (open, high, low, close, last_price) |
| `POST /marketfeed/quote` | Market depth, OHLC, OI, volume | **27** |
| `POST /charts/historical` | Daily candles | **7** (open, high, low, close, volume, timestamp, open_interest) |
| `POST /charts/intraday` | Minute candles (1/5/15/25/60 min) | **7** (same as historical) |

**Total unique parameter names across all data endpoints: 41**

### Parameter list by endpoint

- **Profile:** `dhanClientId`, `tokenValidity`, `activeSegment`, `ddpi`, `mtf`, `dataPlan`, `dataValidity`
- **LTP:** `data`, `status`, `last_price` (per instrument)
- **OHLC:** `data`, `status`, `last_price`, `ohlc.open`, `ohlc.high`, `ohlc.low`, `ohlc.close`
- **Quote:** `last_price`, `last_quantity`, `last_trade_time`, `average_price`, `buy_quantity`, `sell_quantity`, `volume`, `oi`, `oi_day_high`, `oi_day_low`, `net_change`, `lower_circuit_limit`, `upper_circuit_limit`, `ohlc` (open/high/low/close), `depth` (buy/sell: quantity, orders, price per level)
- **Historical / Intraday:** `open`, `high`, `low`, `close`, `volume`, `timestamp`, `open_interest` (arrays)

### Running the test script

1. **Docs-only (no API call):**
   ```bash
   DHAN_DOCS_ONLY=1 python scripts/dhan_api_test.py
   ```

2. **Live test with access token (from web.dhan.co):**
   - Log in at [web.dhan.co](https://web.dhan.co) → My Profile → Access DhanHQ APIs.
   - Generate an **Access Token** (24h) and note your **Client ID** (numeric).
   ```bash
   export DHAN_ACCESS_TOKEN="<your 24h token>"
   export DHAN_CLIENT_ID="<your numeric client id>"
   python scripts/dhan_api_test.py
   ```

3. **Live test with API key + secret (OAuth):**
   - Set **Redirect URL** in Dhan under API key settings.
   - You must know your **Dhan Client ID** (from profile).
   ```bash
   export DHAN_API_KEY="<your API key>"
   export DHAN_API_SECRET="<your API secret>"
   export DHAN_CLIENT_ID="<your dhan client id>"
   python scripts/dhan_api_test.py
   ```
   Open the printed URL in a browser, log in, then from the redirect URL copy `tokenId` and run:
   ```bash
   export DHAN_TOKEN_ID="<tokenId from redirect>"
   python scripts/dhan_api_test.py
   ```

**Note:** Data APIs may require an active **Data plan** on your Dhan account (see `dataPlan` and `dataValidity` in `/profile`).

---

## Screener.in Free vs Paid – How many more parameters?

Screener.in **paid** (Premium ~₹4,000/year) does **not** add a large set of new parameter types. The same **60+ fundamental fields** (P&L, balance sheet, cash flow, ratios, shareholding, sector/industry) are available on the site whether you use free or paid. The difference is **how** you get them.

| Aspect | Free (current) | Paid (Premium) |
|--------|-----------------|----------------|
| **Parameter types** | ~60+ (scrape company pages) | Same ~60+ (no new data types) |
| **Access method** | Web scraping, limited Excel export | **Unlimited CSV export** of screen results |
| **Bulk export** | Limited / per-company scrape | **Up to 50 columns** per CSV export (you choose columns) |
| **Extra in export** | — | **ISIN**, **Industry Group**, NSE/BSE codes (handy for VLOOKUP / integration) |

### What you gain with Screener.in paid

1. **Reliable bulk access** – Export screen results to CSV with up to **50 columns** per run (e.g. PE, ROE, ROCE, debt/equity, sales growth, profit growth, market cap, custom ratios). No need to scrape hundreds of company pages.
2. **Same ~60+ parameters, better coverage** – You don’t get “60 more” new parameters; you cover the **same 60+ fundamentals** in a structured way (CSV) and can run multiple exports with different column sets if you need more than 50 at a time.
3. **A few export-only columns** – e.g. **Industry Group**, **ISIN** in CSV (and any new columns Screener adds to exports). So in practice, **about 2–5 extra** easily usable parameters/identifiers.

### DHAN vs Screener.in (parameter overlap)

| Source | Focus | Approx. parameters | Overlap with the other? |
|--------|--------|---------------------|---------------------------|
| **DHAN** | Price, volume, market depth, OHLC (real-time & historical) | **41** unique names | Almost none – DHAN is price/volume/depth. |
| **Screener.in** | Fundamentals (P&L, BS, CF, ratios, shareholding) | **60+** | None – Screener is fundamentals. |

So:

- **DHAN** → price/volume/depth (41 params).
- **Screener.in free** → ~60+ fundamental params via scraping.
- **Screener.in paid** → Same ~60+ fundamental params via **bulk CSV export** (up to 50 columns per export) plus a few export-only fields (e.g. ISIN, Industry Group). You don’t get “X more” new parameter types; you get **better, scalable access** to the same set and **~2–5 extra** export-friendly columns.
