// 简化：chart lib helper for K-line + indicator overlay
function renderKLine(elementId, ohlcData) {
  // ohlcData: [{date,open,high,low,close,volume}, ...]
  const el = document.getElementById(elementId);
  if (!el) return;
  const dates = ohlcData.map(d => d.date);
  const values = ohlcData.map(d => [d.open, d.close, d.low, d.high]);
  const volumes = ohlcData.map(d => d.volume || 0);

  const chart = echarts.init(el);
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' }
    },
    xAxis: {
      type: 'category',
      data: dates,
      boundaryGap: false
    },
    yAxis: [{ scale: true }, { type: 'value', gridIndex: 0 }],
    grid: [{ left: '10%', right: '8%', height: '60%' },{left:'10%', right:'8%', top:'75%', height:'15%'}],
    series: [
      {
        name: 'K',
        type: 'candlestick',
        data: values,
        itemStyle: {
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a'
        },
      },
      {
        name: 'Volume',
        type: 'bar',
        xAxisIndex: 0,
        yAxisIndex: 1,
        data: volumes,
        barMaxWidth:12
      }
    ]
  };
  chart.setOption(option);
  window.onresize = ()=>chart.resize();
  return chart;
}

function renderLineChart(elementId, xData, yData, name="收益") {
  const el = document.getElementById(elementId);
  if (!el) return;
  const chart = echarts.init(el);
  const option = {
    tooltip:{trigger:'axis'},
    xAxis:{type:'category',data:xData},
    yAxis:{type:'value'},
    series:[{type:'line',data:yData,name:name,smooth:true,areaStyle:{}}]
  };
  chart.setOption(option);
  window.onresize = ()=>chart.resize();
  return chart;
}
