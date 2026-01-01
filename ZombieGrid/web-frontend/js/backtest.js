(async function(){
  // 加载策略下拉
  try {
    const strategies = await listStrategies();
    const sel = document.getElementById('selectStrategy');
    sel.innerHTML = '<option value="">请选择</option>';
    strategies.forEach(s => {
      const o = document.createElement('option');
      o.value = s.id;
      o.text = `${s.id} | ${s.name || '无名'} | rows:${s.total_rows}`;
      sel.appendChild(o);
    });
  } catch (e) {
    console.warn('list strategies failed', e);
  }

  document.getElementById('btnRunBacktest').addEventListener('click', async ()=>{
    const strategy_id = document.getElementById('selectStrategy').value;
    const code = document.getElementById('btStockCode').value.trim();
    const start_date = document.getElementById('btStart').value;
    const end_date = document.getElementById('btEnd').value;
    if (!strategy_id || !code) return alert('请选择策略并填写股票代码');

    const payload = {strategy_id: parseInt(strategy_id), code, start_date: start_date || null, end_date: end_date || null};
    try {
      const res = await runBacktest(payload);
      // res should include df_daily and df_trades and metrics
      document.getElementById('btMetrics').innerText = JSON.stringify(res.metrics || {}, null, 2);
      if (res.df_daily && res.df_daily.length) {
        const x = res.df_daily.map(r=>r.date);
        const y = res.df_daily.map(r=>r.total_value);
        renderLineChart('btChart', x, y, '账户净值');
      }
      // trades table
      if (res.df_trades && res.df_trades.length) {
        const t = document.getElementById('btTrades');
        let html = '<h4>交易流水</h4><table><thead><tr><th>date</th><th>action</th><th>executed_price</th><th>shares</th><th>amount</th></tr></thead><tbody>';
        res.df_trades.forEach(row => {
          html += `<tr><td>${row.date}</td><td>${row.action}</td><td>${row.executed_price}</td><td>${row.shares}</td><td>${row.amount}</td></tr>`;
        });
        html += '</tbody></table>';
        t.innerHTML = html;
      }
    } catch (err) {
      alert('回测失败: ' + err.message);
    }
  });
})();
