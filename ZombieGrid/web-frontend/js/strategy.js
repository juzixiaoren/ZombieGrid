document.getElementById('btnGenerate').addEventListener('click', async ()=>{
  const form = document.getElementById('strategyForm');
  const data = {};
  new FormData(form).forEach((v,k)=>{ if (v !== '') data[k] = isNaN(v)?v: (v.includes('.')?parseFloat(v):parseInt(v))});
  try {
    const res = await generateStrategy(data);
    // show rows table
    const box = document.getElementById('strategyResult');
    const rows = res.rows || [];
    let html = `<h4>配置</h4><pre>${JSON.stringify(res.config||{}, null, 2)}</pre>`;
    html += `<h4>网格行（共 ${rows.length} 行）</h4><table><thead><tr><th>#</th><th>buy_trigger</th><th>buy_price</th><th>buy_amount</th><th>shares</th><th>sell_price</th></tr></thead><tbody>`;
    rows.forEach((r,i)=>{
      html += `<tr><td>${i+1}</td><td>${r.buy_trigger_price.toFixed(4)}</td><td>${r.buy_price.toFixed(4)}</td><td>${r.buy_amount.toFixed(2)}</td><td>${(r.shares||0).toFixed(4)}</td><td>${r.sell_price.toFixed(4)}</td></tr>`;
    });
    html += `</tbody></table>`;
    box.innerHTML = html;
    // enable save
    const btnSave = document.getElementById('btnSave');
    btnSave.disabled = false;
    btnSave._payload = res;
  } catch (e) {
    alert('生成失败: ' + e.message);
  }
});

document.getElementById('btnSave').addEventListener('click', async (e)=>{
  const btn = e.target;
  if (!btn._payload) return alert('没有可保存的策略');
  try {
    await saveStrategy(btn._payload);
    alert('保存成功');
    btn.disabled = true;
  } catch (err) {
    alert('保存失败: ' + err.message);
  }
});
