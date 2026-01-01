(async function(){
  try {
    const list = await listStrategies();
    const container = document.getElementById('historyList');
    if (!list || list.length === 0) {
      container.innerHTML = "<div>暂无策略</div>";
      return;
    }
    let html = '<table><thead><tr><th>ID</th><th>名称</th><th>修改时间</th><th>a</th><th>b</th><th>行数</th><th>操作</th></tr></thead><tbody>';
    list.forEach(it => {
      html += `<tr>
        <td>${it.id}</td>
        <td>${it.name||''}</td>
        <td>${it.last_modified||''}</td>
        <td>${it.a}</td>
        <td>${it.b}</td>
        <td>${it.total_rows}</td>
        <td>
          <button onclick="viewRows(${it.id})">查看行</button>
          <button onclick="gotoBacktest(${it.id})">回测</button>
        </td>
      </tr>`;
    });
    html += '</tbody></table>';
    container.innerHTML = html;
  } catch (e) {
    document.getElementById('historyList').innerHTML = '加载失败: ' + e.message;
  }
})();

window.viewRows = async function(id) {
  try {
    const rows = await getStrategyRows(id);
    let html = `<h4>策略 ${id} 行</h4><table><thead><tr><th>#</th><th>buy_trigger</th><th>buy_price</th><th>buy_amount</th><th>shares</th></tr></thead><tbody>`;
    rows.forEach((r,i)=> html += `<tr><td>${i+1}</td><td>${r.buy_trigger_price}</td><td>${r.buy_price}</td><td>${r.buy_amount}</td><td>${r.shares}</td></tr>`);
    html += '</tbody></table>';
    const w = window.open('', '_blank');
    w.document.body.innerHTML = html;
  } catch (e) { alert('失败: '+e.message); }
}
window.gotoBacktest = function(id){
  localStorage.setItem('last_strategy_id', id);
  window.location.href = 'backtest.html';
}
