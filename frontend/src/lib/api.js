import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = axios.create({
  baseURL: `${BACKEND_URL}/api`,
  timeout: 30000,
});

// Market
export const getMarketOverview = () => API.get("/market/overview");

// Stocks
export const getStocks = (params = {}) => API.get("/stocks", { params });
export const getStock = (symbol) => API.get(`/stocks/${symbol}`);
export const getStockAnalysis = (symbol) => API.get(`/stocks/${symbol}/analysis`);
export const getLLMInsight = (symbol, analysisType = "full") =>
  API.post(`/stocks/${symbol}/llm-insight`, { symbol, analysis_type: analysisType });

// Screener
export const screenStocks = (filters) => API.post("/screener", filters);
export const getScreenerPresets = () => API.get("/screener/presets");

// Watchlist
export const getWatchlist = () => API.get("/watchlist");
export const addToWatchlist = (item) => API.post("/watchlist", item);
export const removeFromWatchlist = (symbol) => API.delete(`/watchlist/${symbol}`);
export const updateWatchlistItem = (symbol, updates) => API.put(`/watchlist/${symbol}`, updates);

// Portfolio
export const getPortfolio = () => API.get("/portfolio");
export const addToPortfolio = (holding) => API.post("/portfolio", holding);
export const removeFromPortfolio = (symbol) => API.delete(`/portfolio/${symbol}`);
export const updatePortfolioHolding = (symbol, updates) => API.put(`/portfolio/${symbol}`, updates);

// News
export const getNews = (params = {}) => API.get("/news", { params });
export const getNewsSummary = () => API.get("/news/summary");

// Reports
export const generateReport = (request) => API.post("/reports/generate", request);

// PDF Export
export const downloadPdfReport = async (request) => {
  const response = await API.post("/reports/generate-pdf", request, {
    responseType: "blob",
  });

  // Create download link
  const blob = new Blob([response.data], { type: "application/pdf" });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement("a");

  // Get filename from content-disposition header or use default
  const contentDisposition = response.headers["content-disposition"];
  let filename = "report.pdf";
  if (contentDisposition) {
    const match = contentDisposition.match(/filename=(.+)/);
    if (match) filename = match[1];
  }

  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);

  return response;
};

// Alerts
export const getAlerts = (params = {}) => API.get("/alerts", { params });
export const createAlert = (alert) => API.post("/alerts", alert);
export const getAlert = (alertId) => API.get(`/alerts/${alertId}`);
export const updateAlert = (alertId, updates) => API.put(`/alerts/${alertId}`, updates);
export const deleteAlert = (alertId) => API.delete(`/alerts/${alertId}`);
export const getAlertsSummary = () => API.get("/alerts/summary/stats");
export const getRecentNotifications = () => API.get("/alerts/notifications/recent");
export const checkAlerts = () => API.post("/alerts/check");

// Backtesting
export const getStrategies = () => API.get("/backtest/strategies");
export const getStrategy = (strategyId) => API.get(`/backtest/strategies/${strategyId}`);
export const runBacktest = (config) => API.post("/backtest/run", config);

// Sectors
export const getSectors = () => API.get("/sectors");

// Search
export const searchStocks = (query) => API.get("/search", { params: { q: query } });

// Health
export const healthCheck = () => API.get("/health");

// Data Pipeline
export const getPipelineStatus = () => API.get("/pipeline/status");
export const runPipelineExtraction = (request = {}) => API.post("/pipeline/run", request);
export const startPipelineScheduler = (intervalMinutes = 30) => 
  API.post("/pipeline/scheduler/start", { interval_minutes: intervalMinutes });
export const stopPipelineScheduler = () => API.post("/pipeline/scheduler/stop");
export const getPipelineJobs = (limit = 20) => API.get("/pipeline/jobs", { params: { limit } });
export const getPipelineJob = (jobId) => API.get(`/pipeline/jobs/${jobId}`);
export const getPipelineHistory = (limit = 50) => API.get("/pipeline/history", { params: { limit } });
export const getPipelineLogs = (limit = 100, eventType = null) => 
  API.get("/pipeline/logs", { params: { limit, event_type: eventType } });
export const getPipelineMetrics = () => API.get("/pipeline/metrics");
export const getPipelineDataSummary = () => API.get("/pipeline/data-summary");
export const testGrowAPI = (symbol = "RELIANCE") => API.post("/pipeline/test-api", { symbol });
export const getDefaultSymbols = () => API.get("/pipeline/default-symbols");
export const getSymbolCategories = () => API.get("/pipeline/symbol-categories");
export const addPipelineSymbols = (symbols) => API.post("/pipeline/symbols/add", symbols);
export const removePipelineSymbols = (symbols) => API.post("/pipeline/symbols/remove", symbols);
export const updateSchedulerConfig = (intervalMinutes, autoStart) => 
  API.put("/pipeline/scheduler/config", null, { 
    params: { interval_minutes: intervalMinutes, auto_start: autoStart } 
  });

export default API;

