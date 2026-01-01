// 在 web-frontend/js/stock.js 中，确保图表渲染代码正确
async function loadAndRender() {
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const q = urlParams.get('q');
        
        if (!q) {
            document.getElementById('stockInfo').innerHTML = '<div>请先搜索股票</div>';
            return;
        }

        // 搜索股票
        const stock = await searchStock(q);
        document.getElementById('stockInfo').innerHTML = `
            <h2>${stock.name} (${stock.code})</h2>
            <p>最新价: ${stock.latest} | 行业: ${stock.industry}</p>
        `;

        // 加载K线数据
        const ohlcData = await getStockOHLC(stock.code, 'day');
        renderChart(ohlcData);
        
    } catch (error) {
        console.error('加载股票数据失败:', error);
        document.getElementById('stockInfo').innerHTML = '<div>加载股票数据失败</div>';
    }
}

function renderChart(ohlcData) {
    if (!ohlcData || !ohlcData.data || ohlcData.data.length === 0) {
        console.error('没有K线数据');
        return;
    }
    
    const chart = echarts.init(document.getElementById('chart'));
    
    const dates = ohlcData.data.map(item => item.date);
    const values = ohlcData.data.map(item => [
        item.open,
        item.close,
        item.low,
        item.high
    ]);
    
    const option = {
        title: {
            text: `${ohlcData.meta.name} (${ohlcData.meta.code}) K线图`
        },
        tooltip: {
            trigger: 'axis',
            axisPointer: {
                type: 'cross'
            }
        },
        xAxis: {
            type: 'category',
            data: dates
        },
        yAxis: {
            type: 'value',
            scale: true
        },
        series: [{
            type: 'candlestick',
            data: values,
            itemStyle: {
                color: '#ec0000',
                color0: '#00da3c',
                borderColor: '#ec0000',
                borderColor0: '#00da3c'
            }
        }]
    };
    
    chart.setOption(option);
}