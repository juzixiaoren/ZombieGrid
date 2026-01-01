const BASE_URL = "http://127.0.0.1:8000/zombieGrid/api";

async function apiGet(path) {
  const res = await fetch(BASE_URL + path);
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}`);
  return await res.json();
}

async function apiPost(path, body) {
  const res = await fetch(BASE_URL + path, {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body)
  });
  if (!res.ok) {
    const txt = await res.text();
    throw new Error(`${res.status} ${res.statusText} ${txt}`);
  }
  return await res.json();
}

/* 辅助方法封装（页面直接调用） */
async function getHotStocks() {
  // 返回 [{code,name,latest,change_pct}, ...]
  return await apiGet("/stocks/hot");
}

async function searchStock(q) {
  // q 可以是 code 或 name，返回最匹配的单只股票基本信息
  return await apiGet("/stocks/search?q=" + encodeURIComponent(q));
}

async function getStockOHLC(code, period = "day") {
  // 返回 {meta:{code,name}, data: [{date,open,high,low,close,volume}, ...]}
  return await apiGet(`/stocks/${encodeURIComponent(code)}/ohlc?period=${period}`);
}

async function generateStrategy(params) {
  // params = {name,a,b,first_trigger_price,total_rows,buy_amount}
  return await apiPost("/strategy/generate", params);
}

async function saveStrategy(resultObj) {
  // resultObj: 返回的策略结构（和generate返回结构一致）
  return await apiPost("/strategy/save", resultObj);
}

async function listStrategies() {
  // 返回 [{id,name,last_modified,a,b,total_rows,buy_amount}, ...]
  return await apiGet("/strategy/list");
}

async function getStrategyRows(config_id) {
  // 返回该策略的 rows []
  return await apiGet(`/strategy/${config_id}/rows`);
}

async function runBacktest(payload) {
  // payload: {strategy_id, code, start_date, end_date}
  // 返回 {backtest_id, metrics:{...}, df_daily:[{date,total_value,...}], df_trades:[...]}
  return await apiPost("/backtest/run", payload);
}

async function getBacktestResult(backtest_id) {
  return await apiGet(`/backtest/${backtest_id}`);
}
