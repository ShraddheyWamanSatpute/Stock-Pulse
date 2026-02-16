#!/usr/bin/env python3

import requests
import sys
import json
from datetime import datetime
from typing import Dict, List, Any

class StockAnalysisPlatformTester:
    def __init__(self, base_url="https://smartdoc-review.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.failed_tests = []
        self.passed_tests = []

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int, data: Dict = None, params: Dict = None) -> tuple:
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ PASSED - Status: {response.status_code}")
                self.passed_tests.append(name)
                try:
                    return success, response.json()
                except:
                    return success, response.text
            else:
                print(f"❌ FAILED - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                self.failed_tests.append({
                    "test": name,
                    "expected": expected_status,
                    "actual": response.status_code,
                    "response": response.text[:500]
                })
                return False, {}

        except Exception as e:
            print(f"❌ FAILED - Error: {str(e)}")
            self.failed_tests.append({
                "test": name,
                "error": str(e)
            })
            return False, {}

    def test_health_endpoints(self):
        """Test basic health endpoints"""
        print("\n" + "="*50)
        print("TESTING HEALTH ENDPOINTS")
        print("="*50)
        
        self.run_test("API Root", "GET", "", 200)
        self.run_test("Health Check", "GET", "health", 200)

    def test_market_overview(self):
        """Test market overview endpoint"""
        print("\n" + "="*50)
        print("TESTING MARKET OVERVIEW")
        print("="*50)
        
        success, data = self.run_test("Market Overview", "GET", "market/overview", 200)
        if success and data:
            # Verify required fields
            required_fields = ['nifty_50', 'sensex', 'nifty_bank', 'india_vix', 'market_breadth', 'fii_dii']
            for field in required_fields:
                if field in data:
                    print(f"   ✓ Found {field}")
                else:
                    print(f"   ⚠️  Missing {field}")

    def test_stocks_endpoints(self):
        """Test stock-related endpoints"""
        print("\n" + "="*50)
        print("TESTING STOCKS ENDPOINTS")
        print("="*50)
        
        # Get all stocks
        success, stocks_data = self.run_test("Get All Stocks", "GET", "stocks", 200, params={"limit": 10})
        
        if success and stocks_data and len(stocks_data) > 0:
            # Test individual stock
            test_symbol = stocks_data[0]['symbol']
            print(f"   Using test symbol: {test_symbol}")
            
            self.run_test(f"Get Stock Details - {test_symbol}", "GET", f"stocks/{test_symbol}", 200)
            self.run_test(f"Get Stock Analysis - {test_symbol}", "GET", f"stocks/{test_symbol}/analysis", 200)
            
            # Test LLM insight
            llm_data = {"analysis_type": "full"}
            self.run_test(f"LLM Insight - {test_symbol}", "POST", f"stocks/{test_symbol}/llm-insight", 200, data=llm_data)
        
        # Test non-existent stock
        self.run_test("Non-existent Stock", "GET", "stocks/INVALID", 404)

    def test_screener_endpoints(self):
        """Test screener functionality"""
        print("\n" + "="*50)
        print("TESTING SCREENER ENDPOINTS")
        print("="*50)
        
        # Get presets
        self.run_test("Screener Presets", "GET", "screener/presets", 200)
        
        # Test screener with filters
        screener_data = {
            "filters": [
                {"metric": "roe", "operator": "gt", "value": 10}
            ],
            "sort_by": "market_cap",
            "sort_order": "desc",
            "limit": 10
        }
        success, results = self.run_test("Run Screener", "POST", "screener", 200, data=screener_data)
        if success and results:
            print(f"   Found {results.get('count', 0)} stocks matching criteria")

    def test_watchlist_endpoints(self):
        """Test watchlist functionality"""
        print("\n" + "="*50)
        print("TESTING WATCHLIST ENDPOINTS")
        print("="*50)
        
        # Get empty watchlist
        self.run_test("Get Watchlist", "GET", "watchlist", 200)
        
        # Add to watchlist
        watchlist_item = {
            "symbol": "RELIANCE",
            "name": "Reliance Industries Limited",
            "added_date": datetime.now().isoformat()
        }
        success, _ = self.run_test("Add to Watchlist", "POST", "watchlist", 200, data=watchlist_item)
        
        if success:
            # Get watchlist again
            self.run_test("Get Watchlist After Add", "GET", "watchlist", 200)
            
            # Update watchlist item
            update_data = {"target_price": 2500, "notes": "Test note"}
            self.run_test("Update Watchlist Item", "PUT", "watchlist/RELIANCE", 200, data=update_data)
            
            # Remove from watchlist
            self.run_test("Remove from Watchlist", "DELETE", "watchlist/RELIANCE", 200)

    def test_portfolio_endpoints(self):
        """Test portfolio functionality"""
        print("\n" + "="*50)
        print("TESTING PORTFOLIO ENDPOINTS")
        print("="*50)
        
        # Get empty portfolio
        self.run_test("Get Portfolio", "GET", "portfolio", 200)
        
        # Add holding
        holding_data = {
            "symbol": "TCS",
            "name": "Tata Consultancy Services",
            "quantity": 10,
            "avg_buy_price": 3500.0,
            "buy_date": "2024-01-01"
        }
        success, _ = self.run_test("Add Portfolio Holding", "POST", "portfolio", 200, data=holding_data)
        
        if success:
            # Get portfolio after add
            self.run_test("Get Portfolio After Add", "GET", "portfolio", 200)
            
            # Update holding
            update_data = {"quantity": 15}
            self.run_test("Update Portfolio Holding", "PUT", "portfolio/TCS", 200, data=update_data)
            
            # Remove holding
            self.run_test("Remove Portfolio Holding", "DELETE", "portfolio/TCS", 200)

    def test_news_endpoints(self):
        """Test news functionality"""
        print("\n" + "="*50)
        print("TESTING NEWS ENDPOINTS")
        print("="*50)
        
        # Get news
        success, news_data = self.run_test("Get News", "GET", "news", 200, params={"limit": 5})
        if success and news_data:
            print(f"   Found {len(news_data)} news items")
        
        # Get news summary
        self.run_test("Get News Summary", "GET", "news/summary", 200)
        
        # Filter by sentiment
        self.run_test("Filter News by Sentiment", "GET", "news", 200, params={"sentiment": "POSITIVE", "limit": 3})

    def test_reports_endpoints(self):
        """Test reports functionality"""
        print("\n" + "="*50)
        print("TESTING REPORTS ENDPOINTS")
        print("="*50)
        
        # Single stock report
        report_data = {
            "report_type": "single_stock",
            "symbols": ["RELIANCE"]
        }
        self.run_test("Single Stock Report", "POST", "reports/generate", 200, data=report_data)
        
        # Comparison report
        comparison_data = {
            "report_type": "comparison",
            "symbols": ["RELIANCE", "TCS"]
        }
        self.run_test("Comparison Report", "POST", "reports/generate", 200, data=comparison_data)
        
        # Portfolio health report
        portfolio_report_data = {
            "report_type": "portfolio_health",
            "symbols": []
        }
        self.run_test("Portfolio Health Report", "POST", "reports/generate", 200, data=portfolio_report_data)

    def test_search_endpoints(self):
        """Test search functionality"""
        print("\n" + "="*50)
        print("TESTING SEARCH ENDPOINTS")
        print("="*50)
        
        # Search stocks
        success, results = self.run_test("Search Stocks", "GET", "search", 200, params={"q": "REL"})
        if success and results:
            print(f"   Found {len(results)} search results")
        
        # Get sectors
        success, sectors = self.run_test("Get Sectors", "GET", "sectors", 200)
        if success and sectors:
            print(f"   Found {len(sectors)} sectors")

    def test_scoring_engine(self):
        """Test scoring engine implementation for StockPulse"""
        print("\n" + "="*60)
        print("TESTING SCORING ENGINE - STOCKPULSE ANALYSIS PLATFORM")
        print("="*60)
        
        # Test symbols as specified in the review request
        test_symbols = ["RELIANCE", "TCS", "HDFCBANK"]
        
        for symbol in test_symbols:
            print(f"\n🔍 Testing Scoring Engine for {symbol}")
            print("-" * 40)
            
            # Get stock analysis data
            success, stock_data = self.run_test(f"Get Stock Data - {symbol}", "GET", f"stocks/{symbol}", 200)
            
            if not success or not stock_data:
                print(f"❌ Failed to get stock data for {symbol}")
                continue
                
            # Verify analysis object exists
            analysis = stock_data.get("analysis")
            if not analysis:
                print(f"❌ No analysis object found for {symbol}")
                continue
                
            print(f"✅ Analysis object found for {symbol}")
            
            # =================================================================
            # TEST 1: DEAL-BREAKERS (D1-D10)
            # =================================================================
            print(f"\n📋 Testing Deal-Breakers (D1-D10) for {symbol}")
            
            deal_breakers = analysis.get("deal_breakers", [])
            if not deal_breakers:
                print(f"❌ No deal_breakers found for {symbol}")
                continue
                
            print(f"   Found {len(deal_breakers)} deal-breakers")
            
            # Check all D1-D10 codes are present
            expected_db_codes = [f"D{i}" for i in range(1, 11)]
            found_db_codes = [db.get("code") for db in deal_breakers]
            
            missing_codes = set(expected_db_codes) - set(found_db_codes)
            if missing_codes:
                print(f"❌ Missing deal-breaker codes: {missing_codes}")
            else:
                print(f"✅ All 10 deal-breaker codes (D1-D10) present")
            
            # Verify structure of each deal-breaker
            required_db_fields = ["code", "rule", "triggered", "value", "threshold", "description", "severity"]
            db_structure_valid = True
            
            for db in deal_breakers:
                for field in required_db_fields:
                    if field not in db:
                        print(f"❌ Deal-breaker {db.get('code', 'Unknown')} missing field: {field}")
                        db_structure_valid = False
                        
                # Verify triggered is boolean
                if not isinstance(db.get("triggered"), bool):
                    print(f"❌ Deal-breaker {db.get('code')} 'triggered' field is not boolean: {type(db.get('triggered'))}")
                    db_structure_valid = False
                    
                # Verify severity is CRITICAL
                if db.get("severity") != "CRITICAL":
                    print(f"⚠️  Deal-breaker {db.get('code')} severity is not CRITICAL: {db.get('severity')}")
            
            if db_structure_valid:
                print(f"✅ Deal-breaker structure validation passed")
            
            # Count triggered deal-breakers
            triggered_dbs = [db for db in deal_breakers if db.get("triggered")]
            print(f"   Triggered deal-breakers: {len(triggered_dbs)}")
            for tdb in triggered_dbs:
                print(f"     - {tdb.get('code')}: {tdb.get('description')}")
            
            # =================================================================
            # TEST 2: RISK PENALTIES (R1-R10)
            # =================================================================
            print(f"\n⚠️  Testing Risk Penalties (R1-R10) for {symbol}")
            
            risk_penalties = analysis.get("risk_penalties", {})
            if not risk_penalties:
                print(f"❌ No risk_penalties object found for {symbol}")
                continue
                
            # Check for long_term and short_term arrays
            lt_penalties = risk_penalties.get("long_term", [])
            st_penalties = risk_penalties.get("short_term", [])
            
            print(f"   Long-term penalties: {len(lt_penalties)}")
            print(f"   Short-term penalties: {len(st_penalties)}")
            
            # Verify structure of penalties
            required_penalty_fields = ["code", "rule", "description", "value", "threshold", "penalty"]
            penalty_structure_valid = True
            
            for penalty_list, penalty_type in [(lt_penalties, "long-term"), (st_penalties, "short-term")]:
                for penalty in penalty_list:
                    for field in required_penalty_fields:
                        if field not in penalty:
                            print(f"❌ {penalty_type} penalty {penalty.get('code', 'Unknown')} missing field: {field}")
                            penalty_structure_valid = False
                            
                    # Verify penalty is negative (it's a penalty)
                    penalty_value = penalty.get("penalty", 0)
                    if penalty_value > 0:
                        print(f"⚠️  {penalty_type} penalty {penalty.get('code')} has positive value: {penalty_value}")
            
            if penalty_structure_valid:
                print(f"✅ Risk penalty structure validation passed")
            
            # Check for expected R1-R10 codes in applied penalties
            expected_r_codes = [f"R{i}" for i in range(1, 11)]
            all_penalty_codes = [p.get("code") for p in lt_penalties + st_penalties]
            found_r_codes = set(all_penalty_codes) & set(expected_r_codes)
            print(f"   Applied penalty codes: {sorted(found_r_codes)}")
            
            # =================================================================
            # TEST 3: QUALITY BOOSTERS (Q1-Q9)
            # =================================================================
            print(f"\n⭐ Testing Quality Boosters (Q1-Q9) for {symbol}")
            
            quality_boosters = analysis.get("quality_boosters", {})
            if not quality_boosters:
                print(f"❌ No quality_boosters object found for {symbol}")
                continue
                
            # Check for long_term and short_term arrays
            lt_boosters = quality_boosters.get("long_term", [])
            st_boosters = quality_boosters.get("short_term", [])
            
            print(f"   Long-term boosters: {len(lt_boosters)}")
            print(f"   Short-term boosters: {len(st_boosters)}")
            
            # Verify structure of boosters
            required_booster_fields = ["code", "rule", "description", "value", "threshold", "boost"]
            booster_structure_valid = True
            
            for booster_list, booster_type in [(lt_boosters, "long-term"), (st_boosters, "short-term")]:
                for booster in booster_list:
                    for field in required_booster_fields:
                        if field not in booster:
                            print(f"❌ {booster_type} booster {booster.get('code', 'Unknown')} missing field: {field}")
                            booster_structure_valid = False
                            
                    # Verify boost is positive (it's a boost)
                    boost_value = booster.get("boost", 0)
                    if boost_value <= 0:
                        print(f"⚠️  {booster_type} booster {booster.get('code')} has non-positive value: {boost_value}")
            
            if booster_structure_valid:
                print(f"✅ Quality booster structure validation passed")
            
            # Check for expected Q1-Q9 codes in applied boosters
            expected_q_codes = [f"Q{i}" for i in range(1, 10)]
            all_booster_codes = [b.get("code") for b in lt_boosters + st_boosters]
            found_q_codes = set(all_booster_codes) & set(expected_q_codes)
            print(f"   Applied booster codes: {sorted(found_q_codes)}")
            
            # Verify boost cap at +30
            total_lt_boost = quality_boosters.get("lt_total_boost", 0)
            total_st_boost = quality_boosters.get("st_total_boost", 0)
            
            if total_lt_boost > 30:
                print(f"⚠️  Long-term boost exceeds cap: {total_lt_boost} > 30")
            if total_st_boost > 30:
                print(f"⚠️  Short-term boost exceeds cap: {total_st_boost} > 30")
            
            # =================================================================
            # TEST 4: CONFIDENCE SCORE
            # =================================================================
            print(f"\n🎯 Testing Confidence Score for {symbol}")
            
            # Check main confidence fields
            confidence_score = analysis.get("confidence_score")
            confidence_level = analysis.get("confidence_level")
            confidence_breakdown = analysis.get("confidence_breakdown", {})
            
            confidence_valid = True
            
            # Verify confidence_score is 0-100
            if confidence_score is None:
                print(f"❌ Missing confidence_score")
                confidence_valid = False
            elif not (0 <= confidence_score <= 100):
                print(f"❌ confidence_score out of range: {confidence_score}")
                confidence_valid = False
            else:
                print(f"✅ confidence_score: {confidence_score}")
            
            # Verify confidence_level is HIGH/MEDIUM/LOW
            valid_levels = ["HIGH", "MEDIUM", "LOW"]
            if confidence_level not in valid_levels:
                print(f"❌ Invalid confidence_level: {confidence_level}")
                confidence_valid = False
            else:
                print(f"✅ confidence_level: {confidence_level}")
            
            # Verify confidence_breakdown components
            required_breakdown_fields = ["data_completeness", "data_freshness", "source_agreement", "ml_confidence"]
            for field in required_breakdown_fields:
                value = confidence_breakdown.get(field)
                if value is None:
                    print(f"❌ Missing confidence breakdown field: {field}")
                    confidence_valid = False
                elif not (0 <= value <= 100):
                    print(f"❌ confidence breakdown {field} out of range: {value}")
                    confidence_valid = False
                else:
                    print(f"✅ {field}: {value}")
            
            if confidence_valid:
                print(f"✅ Confidence score validation passed")
            
            # =================================================================
            # TEST 5: OVERALL SCORING VALIDATION
            # =================================================================
            print(f"\n📊 Testing Overall Scoring for {symbol}")
            
            # Check main scores
            long_term_score = analysis.get("long_term_score")
            short_term_score = analysis.get("short_term_score")
            verdict = analysis.get("verdict")
            
            if long_term_score is None or not (0 <= long_term_score <= 100):
                print(f"❌ Invalid long_term_score: {long_term_score}")
            else:
                print(f"✅ long_term_score: {long_term_score}")
            
            if short_term_score is None or not (0 <= short_term_score <= 100):
                print(f"❌ Invalid short_term_score: {short_term_score}")
            else:
                print(f"✅ short_term_score: {short_term_score}")
            
            valid_verdicts = ["STRONG BUY", "BUY", "HOLD", "AVOID", "STRONG AVOID"]
            if verdict not in valid_verdicts:
                print(f"❌ Invalid verdict: {verdict}")
            else:
                print(f"✅ verdict: {verdict}")
            
            # Check if deal-breaker logic is working (scores should be capped at 35 if deal-breaker triggered)
            if triggered_dbs:
                if long_term_score > 35 or short_term_score > 35:
                    print(f"⚠️  Scores not capped at 35 despite triggered deal-breakers")
                    print(f"     LT: {long_term_score}, ST: {short_term_score}")
                else:
                    print(f"✅ Scores properly capped due to deal-breakers")
            
            print(f"\n✅ Scoring engine test completed for {symbol}")
            print("-" * 40)

    def run_all_tests(self):
        """Run all test suites"""
        print("🚀 Starting Stock Analysis Platform API Tests")
        print(f"Base URL: {self.base_url}")
        
        try:
            self.test_health_endpoints()
            self.test_market_overview()
            self.test_stocks_endpoints()
            self.test_screener_endpoints()
            self.test_watchlist_endpoints()
            self.test_portfolio_endpoints()
            self.test_news_endpoints()
            self.test_reports_endpoints()
            self.test_search_endpoints()
            
        except KeyboardInterrupt:
            print("\n⚠️  Tests interrupted by user")
        except Exception as e:
            print(f"\n💥 Unexpected error: {str(e)}")
        
        # Print final results
        self.print_results()
        
        return 0 if self.tests_passed == self.tests_run else 1

    def print_results(self):
        """Print test results summary"""
        print("\n" + "="*60)
        print("TEST RESULTS SUMMARY")
        print("="*60)
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"✅ Passed: {self.tests_passed}")
        print(f"❌ Failed: {len(self.failed_tests)}")
        print(f"📈 Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for i, test in enumerate(self.failed_tests, 1):
                print(f"   {i}. {test.get('test', 'Unknown')}")
                if 'error' in test:
                    print(f"      Error: {test['error']}")
                else:
                    print(f"      Expected: {test.get('expected')}, Got: {test.get('actual')}")
        
        if self.passed_tests:
            print(f"\n✅ PASSED TESTS:")
            for i, test in enumerate(self.passed_tests, 1):
                print(f"   {i}. {test}")

def main():
    tester = StockAnalysisPlatformTester()
    return tester.run_all_tests()

if __name__ == "__main__":
    sys.exit(main())