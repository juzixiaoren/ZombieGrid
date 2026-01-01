(async function(){
  try {
    const hotList = document.getElementById('hotList');
    hotList.innerHTML = "加载中...";
    const data = await getHotStocks();
    hotList.innerHTML = "";
    if (!data || data.length === 0) {
      hotList.innerHTML = "<div>无数据</div>";
      return;
    }
    data.slice(0,12).forEach(s => {
      const t = document.createElement('div');
      t.className = 'stock-tile';
      t.innerHTML = `<div style="display:flex;justify-content:space-between"><strong>${s.code} ${s.name}</strong><span>${(s.change_pct||0).toFixed(2)}%</span></div>
                     <div>最新: ${s.latest ?? '—'}</div>
                     <div style="margin-top:6px"><a href="stock.html?q=${encodeURIComponent(s.code)}">查看</a></div>`;
      hotList.appendChild(t);
    });

    // top gainers / losers - if provided by API
    const g = document.getElementById('topGainers');
    const l = document.getElementById('topLosers');
    if (data && data.length) {
      const sorted = data.slice().sort((a,b)=> (b.change_pct||0)-(a.change_pct||0));
      sorted.slice(0,5).forEach(it=> {
        const li = document.createElement('li'); li.innerHTML = `<a href="stock.html?q=${encodeURIComponent(it.code)}">${it.code} ${it.name} ${(it.change_pct||0).toFixed(2)}%</a>`;
        g.appendChild(li);
      });
      sorted.slice(-5).reverse().forEach(it=>{
        const li = document.createElement('li'); li.innerHTML = `<a href="stock.html?q=${encodeURIComponent(it.code)}">${it.code} ${it.name} ${(it.change_pct||0).toFixed(2)}%</a>`;
        l.appendChild(li);
      });
    }
  } catch (e) {
    console.error(e);
    document.getElementById('hotList').innerHTML = "获取失败：" + e.message;
  }
})();
