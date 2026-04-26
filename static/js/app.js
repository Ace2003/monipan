class StockTradingApp {
    constructor() {
        this.currentPage = 'market';
        this.selectedStock = null;
        this.tradeType = 'buy';
        this.chart = null;
        this.hotStocks = [];
        this.currentNews = null;
        this.init();
    }

    init() {
        this.bindEvents();
        this.navigateTo('market');
        this.updateTime();
    }

    bindEvents() {
        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = btn.dataset.page;
                this.navigateTo(page);
            });
        });

        document.querySelectorAll('.trade-tab').forEach(btn => {
            btn.addEventListener('click', () => {
                this.setTradeType(btn.dataset.type);
            });
        });

        const searchInput = document.getElementById('stock-search');
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce((e) => {
                this.handleSearch(e.target.value, 'market');
            }, 300));
            searchInput.addEventListener('focus', () => {
                if (searchInput.value) {
                    this.handleSearch(searchInput.value, 'market');
                }
            });
        }

        const tradeSearchInput = document.getElementById('trade-stock-input');
        if (tradeSearchInput) {
            tradeSearchInput.addEventListener('input', this.debounce((e) => {
                this.handleSearch(e.target.value, 'trade');
            }, 300));
            tradeSearchInput.addEventListener('focus', () => {
                if (tradeSearchInput.value) {
                    this.handleSearch(tradeSearchInput.value, 'trade');
                }
            });
        }

        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-container') && !e.target.closest('.stock-input-wrapper')) {
                this.hideSearchResults();
            }
        });

        const chartStockSelect = document.getElementById('chart-stock-select');
        const chartPeriodSelect = document.getElementById('chart-period-select');
        if (chartStockSelect) {
            chartStockSelect.addEventListener('change', () => {
                this.loadStockChart(chartStockSelect.value, chartPeriodSelect.value);
            });
        }
        if (chartPeriodSelect) {
            chartPeriodSelect.addEventListener('change', () => {
                this.loadStockChart(chartStockSelect.value, chartPeriodSelect.value);
            });
        }

        const tradePrice = document.getElementById('trade-price');
        const tradeQuantity = document.getElementById('trade-quantity');
        if (tradePrice) {
            tradePrice.addEventListener('input', () => this.updateTradeSummary());
        }
        if (tradeQuantity) {
            tradeQuantity.addEventListener('input', () => this.updateTradeSummary());
        }

        document.querySelectorAll('.price-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                if (this.selectedStock) {
                    document.getElementById('trade-price').value = this.selectedStock.current;
                    this.updateTradeSummary();
                }
            });
        });

        document.querySelectorAll('.quantity-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const percent = parseInt(btn.dataset.percent);
                this.setQuantityByPercent(percent);
            });
        });

        const tradeSubmitBtn = document.getElementById('trade-submit-btn');
        if (tradeSubmitBtn) {
            tradeSubmitBtn.addEventListener('click', () => this.submitTrade());
        }

        const refreshBtn = document.getElementById('refresh-btn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshAllData());
        }
    }

    navigateTo(page) {
        this.currentPage = page;

        document.querySelectorAll('.nav-item').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.page === page);
        });

        document.querySelectorAll('.page').forEach(p => {
            p.classList.toggle('active', p.id === `page-${page}`);
        });

        if (page === 'market') {
            this.loadMarketData();
        } else if (page === 'trade') {
            this.loadTradePageData();
        } else if (page === 'portfolio') {
            this.loadPortfolio();
        } else if (page === 'account') {
            this.loadAccountInfo();
        }
    }

    setTradeType(type) {
        this.tradeType = type;

        document.querySelectorAll('.trade-tab').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.type === type);
        });

        const submitBtn = document.getElementById('trade-submit-btn');
        if (submitBtn) {
            submitBtn.textContent = type === 'buy' ? '确认买入' : '确认卖出';
            submitBtn.className = `trade-submit-btn ${type}`;
        }

        this.updateTradeSummary();
    }

    async refreshAllData() {
        this.showLoading();
        try {
            await Promise.all([
                this.loadMarketData(),
                this.loadAccountInfo(),
                this.loadPortfolio()
            ]);
            this.updateTime();
            this.showToast('数据已刷新', 'success');
        } catch (error) {
            this.showToast('刷新失败', 'error');
        } finally {
            this.hideLoading();
        }
    }

    updateTime() {
        const now = new Date();
        const timeStr = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        const updateTimeEl = document.getElementById('update-time');
        if (updateTimeEl) {
            updateTimeEl.textContent = timeStr;
        }
    }

    async loadMarketData() {
        try {
            const response = await fetch('/api/market');
            const data = await response.json();
            
            if (data.success) {
                this.renderIndices(data.data.indices);
            }
        } catch (error) {
            console.error('加载市场数据失败:', error);
        }

        setTimeout(() => {
            this.loadNews();
        }, 100);

        setTimeout(() => {
            const chartStockSelect = document.getElementById('chart-stock-select');
            const chartPeriodSelect = document.getElementById('chart-period-select');
            if (chartStockSelect) {
                this.loadStockChart(chartStockSelect.value, chartPeriodSelect?.value || '1month');
            }
        }, 300);
    }

    async loadNews() {
        try {
            const response = await fetch('/api/news');
            const data = await response.json();
            
            if (data.success) {
                this.renderNews(data.data);
            }
        } catch (error) {
            console.error('加载新闻失败:', error);
        }
    }

    async loadTradePageData() {
        this.loadTransactionHistory();
        
        if (this.hotStocks.length === 0) {
            await this.loadHotStocks();
        } else {
            this.renderHotStocks(this.hotStocks);
        }
    }

    async loadHotStocks() {
        try {
            const response = await fetch('/api/search?keyword=');
            const data = await response.json();
            
            if (data.success && data.data && data.data.length > 0) {
                this.hotStocks = data.data.slice(0, 6);
                this.renderHotStocks(this.hotStocks);
            }
        } catch (error) {
            console.error('加载热门股票失败:', error);
        }
    }

    renderHotStocks(stocks) {
        const container = document.getElementById('hot-stocks-container');
        if (!container) return;

        container.innerHTML = stocks.map(stock => {
            const isUp = stock.change >= 0;
            const priceClass = isUp ? 'up' : 'down';
            const changePrefix = isUp ? '+' : '';

            return `
                <div class="hot-stock-item" data-symbol="${stock.symbol}" data-name="${this.escapeHtml(stock.name)}">
                    <div class="hot-stock-header">
                        <div>
                            <span class="hot-stock-name">${this.escapeHtml(stock.name)}</span>
                            <span class="hot-stock-code">${stock.symbol}</span>
                        </div>
                        <div>
                            <span class="hot-stock-price ${priceClass}">${stock.current.toFixed(2)}</span>
                        </div>
                    </div>
                    <div class="hot-stock-change ${priceClass}">
                        ${changePrefix}${stock.change.toFixed(2)}%
                    </div>
                </div>
            `;
        }).join('');

        container.querySelectorAll('.hot-stock-item').forEach(item => {
            item.addEventListener('click', () => {
                const symbol = item.dataset.symbol;
                this.selectHotStock(symbol, item);
            });
        });
    }

    selectHotStock(symbol, element) {
        document.querySelectorAll('.hot-stock-item').forEach(item => {
            item.classList.remove('selected');
        });
        if (element) {
            element.classList.add('selected');
        }

        this.selectStock(symbol, 'trade');
    }

    renderIndices(indices) {
        const container = document.getElementById('indices-container');
        if (!container) return;

        container.innerHTML = indices.map(index => {
            const isUp = index.change >= 0;
            const isFlat = index.change === 0;
            const priceClass = isUp ? 'up' : (isFlat ? 'flat' : 'down');
            const changeClass = isUp ? 'up' : (isFlat ? 'flat' : 'down');
            const changePrefix = isUp ? '+' : '';

            return `
                <div class="index-card">
                    <div class="index-name">${index.name}</div>
                    <div class="index-price ${priceClass}">${index.current.toFixed(2)}</div>
                    <div class="index-change ${changeClass}">
                        <span>${changePrefix}${index.change_point.toFixed(2)}</span>
                        <span>${changePrefix}${index.change.toFixed(2)}%</span>
                    </div>
                </div>
            `;
        }).join('');
    }

    renderNews(news) {
        const container = document.getElementById('news-container');
        if (!container) return;

        if (!news || news.length === 0) {
            container.innerHTML = '<div class="empty-state"><span class="empty-icon">📰</span><p>暂无新闻</p></div>';
            return;
        }

        container.innerHTML = news.map((item, index) => {
            return `
                <div class="news-item" data-index="${index}">
                    <div class="news-title">${this.escapeHtml(item.title)}</div>
                    <div class="news-meta">
                        <span>${this.escapeHtml(item.source || '未知来源')}</span>
                        <span>${this.escapeHtml(item.time || '')}</span>
                    </div>
                </div>
            `;
        }).join('');

        container.querySelectorAll('.news-item').forEach(item => {
            item.addEventListener('click', () => {
                const index = parseInt(item.dataset.index);
                if (news[index]) {
                    this.showNewsDetail(news[index]);
                }
            });
        });
    }

    showNewsDetail(news) {
        this.currentNews = news;

        const titleEl = document.getElementById('news-modal-title');
        const sourceEl = document.getElementById('news-modal-source');
        const timeEl = document.getElementById('news-modal-time');
        const contentEl = document.getElementById('news-modal-content');

        if (titleEl) {
            titleEl.textContent = news.title || '新闻详情';
        }
        if (sourceEl) {
            sourceEl.textContent = `来源：${news.source || '未知'}`;
        }
        if (timeEl) {
            timeEl.textContent = `时间：${news.time || '未知'}`;
        }
        if (contentEl) {
            let content = '';
            if (news.content && news.content.trim()) {
                content = `<p>${news.content}</p>`;
            } else if (news.url && news.url.startsWith('http')) {
                content = '<p style="color: var(--text-secondary); text-align: center;">该新闻未获取到详细内容</p>';
            } else {
                content = '<p style="color: var(--text-secondary); text-align: center;">暂无详细内容</p>';
            }
            
            if (news.url && news.url.startsWith('http')) {
                content += `<p style="text-align: center; margin-top: 24px;">
                    <a href="${news.url}" target="_blank" 
                       style="display: inline-block; padding: 10px 24px; background: var(--primary-color); color: white; text-decoration: none; border-radius: 8px; font-weight: 500;">
                        🔗 查看原文
                    </a>
                </p>`;
            }
            contentEl.innerHTML = content;
        }

        const modal = document.getElementById('news-modal');
        if (modal) {
            modal.classList.remove('hidden');
        }
    }

    closeNewsModal() {
        const modal = document.getElementById('news-modal');
        if (modal) {
            modal.classList.add('hidden');
        }
        this.currentNews = null;
    }

    async loadStockChart(symbol, period) {
        try {
            const infoResponse = await fetch(`/api/stock/${symbol}`);
            const infoData = await infoResponse.json();
            
            if (infoData.success) {
                this.renderStockDetail(infoData.data);
            }

            const historyResponse = await fetch(`/api/stock/${symbol}/history?period=${period}`);
            const historyData = await historyResponse.json();
            
            if (historyData.success) {
                this.renderStockChart(historyData.data);
            }
        } catch (error) {
            console.error('加载股票数据失败:', error);
        }
    }

    renderStockDetail(stock) {
        const isUp = stock.change >= 0;
        const changePrefix = isUp ? '+' : '';

        const elements = {
            'detail-stock-name': stock.name,
            'detail-stock-code': stock.symbol,
            'detail-current-price': stock.current.toFixed(2),
            'detail-change-info': `${changePrefix}${stock.change_point.toFixed(2)} (${changePrefix}${stock.change.toFixed(2)}%)`,
            'detail-open': stock.open.toFixed(2),
            'detail-high': stock.high.toFixed(2),
            'detail-low': stock.low.toFixed(2),
            'detail-prev-close': stock.prev_close.toFixed(2),
            'detail-volume': this.formatNumber(stock.volume),
            'detail-amount': this.formatAmount(stock.amount),
            'detail-turnover': `${stock.turnover_rate.toFixed(2)}%`,
            'detail-pe': stock.pe_ratio.toFixed(2)
        };

        Object.entries(elements).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = value;
            }
        });

        const currentPriceEl = document.getElementById('detail-current-price');
        const changeInfoEl = document.getElementById('detail-change-info');
        
        if (currentPriceEl) {
            currentPriceEl.className = `current-price ${isUp ? 'up' : 'down'}`;
        }
        if (changeInfoEl) {
            changeInfoEl.className = `change-info ${isUp ? 'up' : 'down'}`;
        }
    }

    renderStockChart(historyData) {
        const ctx = document.getElementById('stock-chart');
        if (!ctx) return;

        const data = historyData.data || [];
        if (data.length === 0) return;

        const labels = data.map(d => this.formatDateLabel(d.date, historyData.period));
        const closePrices = data.map(d => d.close);
        const volumes = data.map(d => d.volume);

        const isUp = closePrices[closePrices.length - 1] >= closePrices[0];
        const lineColor = isUp ? '#ff4d4f' : '#52c41a';
        const bgColor = isUp ? 'rgba(255, 77, 79, 0.1)' : 'rgba(82, 196, 26, 0.1)';

        if (this.chart) {
            this.chart.destroy();
        }

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: '收盘价',
                    data: closePrices,
                    borderColor: lineColor,
                    backgroundColor: bgColor,
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        mode: 'index',
                        intersect: false
                    }
                },
                scales: {
                    x: {
                        display: true,
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxTicksLimit: 6,
                            maxRotation: 0
                        }
                    },
                    y: {
                        display: true,
                        position: 'right',
                        grid: {
                            color: 'rgba(0, 0, 0, 0.05)'
                        }
                    }
                },
                interaction: {
                    mode: 'nearest',
                    axis: 'x',
                    intersect: false
                }
            }
        });
    }

    formatDateLabel(dateStr, period) {
        if (period === 'intraday') {
            return dateStr;
        }
        
        const date = new Date(dateStr);
        if (isNaN(date.getTime())) {
            return dateStr;
        }
        
        return `${date.getMonth() + 1}/${date.getDate()}`;
    }

    async handleSearch(keyword, context) {
        if (!keyword || keyword.trim() === '') {
            this.hideSearchResults();
            return;
        }

        try {
            const response = await fetch(`/api/search?keyword=${encodeURIComponent(keyword)}`);
            const data = await response.json();
            
            if (data.success) {
                this.renderSearchResults(data.data, context);
            }
        } catch (error) {
            console.error('搜索失败:', error);
        }
    }

    renderSearchResults(results, context) {
        const containerId = context === 'trade' ? 'trade-search-results' : 'search-results';
        const container = document.getElementById(containerId);
        
        if (!container || !results || results.length === 0) {
            this.hideSearchResults();
            return;
        }

        container.innerHTML = results.map(stock => {
            const isUp = stock.change >= 0;
            const priceClass = isUp ? 'up' : 'down';
            const changePrefix = isUp ? '+' : '';

            return `
                <div class="search-item" data-symbol="${stock.symbol}" data-context="${context}">
                    <div>
                        <span class="search-item-name">${this.escapeHtml(stock.name)}</span>
                        <span class="search-item-code">${stock.symbol}</span>
                    </div>
                    <div>
                        <span class="search-item-price ${priceClass}">${stock.current.toFixed(2)}</span>
                        <span class="search-item-price ${priceClass}">${changePrefix}${stock.change.toFixed(2)}%</span>
                    </div>
                </div>
            `;
        }).join('');

        container.classList.add('active');

        container.querySelectorAll('.search-item').forEach(item => {
            item.addEventListener('click', () => {
                const symbol = item.dataset.symbol;
                const itemContext = item.dataset.context;
                this.selectStock(symbol, itemContext);
            });
        });
    }

    hideSearchResults() {
        document.querySelectorAll('.search-results, .search-dropdown').forEach(el => {
            el.classList.remove('active');
        });
    }

    async selectStock(symbol, context) {
        this.hideSearchResults();

        try {
            const response = await fetch(`/api/stock/${symbol}`);
            const data = await response.json();
            
            if (data.success) {
                this.selectedStock = data.data;
                
                if (context === 'trade') {
                    this.renderSelectedStockForTrade();
                } else {
                    const chartStockSelect = document.getElementById('chart-stock-select');
                    if (chartStockSelect) {
                        let optionExists = false;
                        for (let option of chartStockSelect.options) {
                            if (option.value === symbol) {
                                optionExists = true;
                                option.selected = true;
                                break;
                            }
                        }
                        if (!optionExists) {
                            const newOption = new Option(data.data.name, symbol, true, true);
                            chartStockSelect.add(newOption);
                        }
                    }
                    const chartPeriodSelect = document.getElementById('chart-period-select');
                    this.loadStockChart(symbol, chartPeriodSelect?.value || '1month');
                    
                    const searchInput = document.getElementById('stock-search');
                    if (searchInput) {
                        searchInput.value = data.data.name;
                    }
                }
            }
        } catch (error) {
            console.error('获取股票信息失败:', error);
            this.showToast('获取股票信息失败', 'error');
        }
    }

    renderSelectedStockForTrade() {
        if (!this.selectedStock) return;

        const stock = this.selectedStock;
        const isUp = stock.change >= 0;

        const infoContainer = document.getElementById('selected-stock-info');
        if (infoContainer) {
            infoContainer.innerHTML = `
                <div class="selected-stock-header">
                    <div>
                        <span class="selected-name">${this.escapeHtml(stock.name)}</span>
                        <span class="selected-code">${stock.symbol}</span>
                    </div>
                    <div class="selected-price ${isUp ? 'up' : 'down'}">
                        ${stock.current.toFixed(2)}
                    </div>
                </div>
            `;
            infoContainer.classList.add('active');
        }

        const tradePriceInput = document.getElementById('trade-price');
        if (tradePriceInput) {
            tradePriceInput.value = stock.current.toFixed(2);
        }

        const tradeSearchInput = document.getElementById('trade-stock-input');
        if (tradeSearchInput) {
            tradeSearchInput.value = stock.name;
        }

        this.updateTradeSummary();
    }

    updateTradeSummary() {
        const price = parseFloat(document.getElementById('trade-price')?.value) || 0;
        const quantity = parseInt(document.getElementById('trade-quantity')?.value) || 0;

        const amount = price * quantity;
        const fee = Math.max(amount * 0.0003, 5);
        const stampDuty = this.tradeType === 'sell' ? amount * 0.001 : 0;
        const transferFee = Math.max(amount * 0.00002, 1);
        const totalFees = fee + stampDuty + transferFee;

        const total = this.tradeType === 'buy' ? amount + totalFees : amount - totalFees;

        const elements = {
            'summary-amount': `¥${amount.toFixed(2)}`,
            'summary-fee': `¥${fee.toFixed(2)}`,
            'summary-stamp': `¥${stampDuty.toFixed(2)}`,
            'summary-total': `¥${total.toFixed(2)}`
        };

        Object.entries(elements).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = value;
            }
        });
    }

    async setQuantityByPercent(percent) {
        if (!this.selectedStock) {
            this.showToast('请先选择股票', 'warning');
            return;
        }

        const price = parseFloat(document.getElementById('trade-price')?.value) || this.selectedStock.current;
        
        if (this.tradeType === 'buy') {
            try {
                const response = await fetch('/api/account');
                const data = await response.json();
                
                if (data.success) {
                    const availableCash = data.data.available_cash;
                    const estimatedTotal = availableCash * (percent / 100);
                    const shares = Math.floor(estimatedTotal / (price * 1.00132)) / 100;
                    const quantity = Math.floor(shares) * 100;
                    
                    if (quantity > 0) {
                        document.getElementById('trade-quantity').value = quantity;
                        this.updateTradeSummary();
                    } else {
                        this.showToast('可用资金不足', 'warning');
                    }
                }
            } catch (error) {
                console.error('获取账户信息失败:', error);
            }
        } else {
            try {
                const response = await fetch('/api/portfolio');
                const data = await response.json();
                
                if (data.success) {
                    const holding = data.data.find(h => h.stock_symbol === this.selectedStock.symbol);
                    if (holding) {
                        const quantity = Math.floor(holding.quantity * (percent / 100) / 100) * 100;
                        if (quantity > 0) {
                            document.getElementById('trade-quantity').value = quantity;
                            this.updateTradeSummary();
                        }
                    } else {
                        this.showToast('未持有该股票', 'warning');
                    }
                }
            } catch (error) {
                console.error('获取持仓失败:', error);
            }
        }
    }

    async submitTrade() {
        if (!this.selectedStock) {
            this.showToast('请先选择股票', 'warning');
            return;
        }

        const price = parseFloat(document.getElementById('trade-price')?.value);
        const quantity = parseInt(document.getElementById('trade-quantity')?.value);

        if (!price || price <= 0) {
            this.showToast('请输入有效价格', 'warning');
            return;
        }

        if (!quantity || quantity <= 0 || quantity % 100 !== 0) {
            this.showToast('数量必须是100的整数倍', 'warning');
            return;
        }

        this.showLoading();

        try {
            const endpoint = this.tradeType === 'buy' ? '/api/trade/buy' : '/api/trade/sell';
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    symbol: this.selectedStock.symbol,
                    quantity: quantity,
                    price: price
                })
            });

            const data = await response.json();

            if (data.success) {
                const action = this.tradeType === 'buy' ? '买入' : '卖出';
                this.showToast(`${action}成功！`, 'success');
                
                document.getElementById('trade-quantity').value = '';
                this.updateTradeSummary();
                
                this.loadTransactionHistory();
                this.loadAccountInfo();
                this.loadPortfolio();
            } else {
                this.showToast(data.message || '交易失败', 'error');
            }
        } catch (error) {
            console.error('交易失败:', error);
            this.showToast('交易失败，请重试', 'error');
        } finally {
            this.hideLoading();
        }
    }

    async loadTransactionHistory() {
        try {
            const response = await fetch('/api/transactions?limit=20');
            const data = await response.json();
            
            if (data.success) {
                this.renderTransactionHistory(data.data);
            }
        } catch (error) {
            console.error('加载交易记录失败:', error);
        }
    }

    renderTransactionHistory(transactions) {
        const container = document.getElementById('transaction-list');
        if (!container) return;

        if (!transactions || transactions.length === 0) {
            container.innerHTML = '<div class="empty-state"><span class="empty-icon">📋</span><p>暂无交易记录</p></div>';
            return;
        }

        container.innerHTML = transactions.map(tx => {
            const isBuy = tx.transaction_type === 'buy';
            const totalFees = tx.fee + tx.stamp_duty + tx.transfer_fee;

            return `
                <div class="transaction-item">
                    <div class="transaction-header">
                        <span class="transaction-type ${tx.transaction_type}">${isBuy ? '买入' : '卖出'}</span>
                        <span class="transaction-time">${tx.transaction_time}</span>
                    </div>
                    <div class="transaction-info">
                        <div class="transaction-stock">
                            <span class="transaction-stock-name">${this.escapeHtml(tx.stock_name)}</span>
                            <span class="transaction-stock-detail">${tx.stock_symbol} | ${tx.quantity}股 × ¥${tx.price.toFixed(2)}</span>
                        </div>
                        <div class="transaction-amount">
                            <span class="transaction-total">¥${tx.total_amount.toFixed(2)}</span>
                            <span class="transaction-fee">手续费: ¥${totalFees.toFixed(2)}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    async loadPortfolio() {
        try {
            const response = await fetch('/api/portfolio');
            const data = await response.json();
            
            if (data.success) {
                this.renderPortfolio(data.data);
            }
        } catch (error) {
            console.error('加载持仓失败:', error);
        }
    }

    renderPortfolio(portfolio) {
        let totalMarketValue = 0;
        let totalProfitLoss = 0;

        portfolio.forEach(item => {
            totalMarketValue += item.market_value;
            totalProfitLoss += item.profit_loss;
        });

        const totalProfitRate = totalMarketValue > 0 ? 
            (totalProfitLoss / (totalMarketValue - totalProfitLoss) * 100) : 0;

        const elements = {
            'portfolio-market-value': `¥${this.formatAmount(totalMarketValue)}`,
            'portfolio-profit-loss': `¥${totalProfitLoss >= 0 ? '+' : ''}${this.formatAmount(totalProfitLoss)}`,
            'portfolio-profit-rate': `${totalProfitLoss >= 0 ? '+' : ''}${totalProfitRate.toFixed(2)}%`
        };

        Object.entries(elements).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = value;
                el.style.color = totalProfitLoss >= 0 ? '#ff4d4f' : '#52c41a';
            }
        });

        const container = document.getElementById('portfolio-items');
        if (!container) return;

        if (!portfolio || portfolio.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <span class="empty-icon">📭</span>
                    <p>暂无持仓</p>
                    <p class="empty-hint">去交易页面买入股票吧</p>
                </div>
            `;
            return;
        }

        container.innerHTML = portfolio.map(item => {
            const isUp = item.profit_loss >= 0;
            const profitPrefix = isUp ? '+' : '';

            return `
                <div class="portfolio-item" onclick="app.selectStock('${item.stock_symbol}', 'trade')">
                    <div class="portfolio-header">
                        <div class="portfolio-stock-info">
                            <span class="portfolio-stock-name">${this.escapeHtml(item.stock_name)}</span>
                            <span class="portfolio-stock-code">${item.stock_symbol}</span>
                        </div>
                        <div class="portfolio-profit">
                            <span class="portfolio-profit-value ${isUp ? 'up' : 'down'}">
                                ${profitPrefix}¥${this.formatAmount(item.profit_loss)}
                            </span>
                            <span class="portfolio-profit-rate ${isUp ? 'up' : 'down'}">
                                ${profitPrefix}${item.profit_loss_rate.toFixed(2)}%
                            </span>
                        </div>
                    </div>
                    <div class="portfolio-stats">
                        <div class="portfolio-stat">
                            <span class="portfolio-stat-label">持仓</span>
                            <span class="portfolio-stat-value">${item.quantity}股</span>
                        </div>
                        <div class="portfolio-stat">
                            <span class="portfolio-stat-label">成本</span>
                            <span class="portfolio-stat-value">¥${item.avg_cost_price.toFixed(2)}</span>
                        </div>
                        <div class="portfolio-stat">
                            <span class="portfolio-stat-label">现价</span>
                            <span class="portfolio-stat-value ${isUp ? 'up' : 'down'}">¥${item.current_price.toFixed(2)}</span>
                        </div>
                        <div class="portfolio-stat">
                            <span class="portfolio-stat-label">市值</span>
                            <span class="portfolio-stat-value">¥${this.formatAmount(item.market_value)}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    async loadAccountInfo() {
        try {
            const response = await fetch('/api/account');
            const data = await response.json();
            
            if (data.success) {
                this.renderAccountInfo(data.data);
            }
        } catch (error) {
            console.error('加载账户信息失败:', error);
        }

        try {
            const txResponse = await fetch('/api/transactions?limit=1000');
            const txData = await txResponse.json();
            
            if (txData.success) {
                this.renderAccountStats(txData.data);
            }
        } catch (error) {
            console.error('加载交易统计失败:', error);
        }
    }

    renderAccountInfo(account) {
        const isProfit = account.total_profit >= 0;
        const profitPrefix = isProfit ? '+' : '';

        const elements = {
            'asset-total': `¥${this.formatAmount(account.total_assets)}`,
            'asset-available': `¥${this.formatAmount(account.available_cash)}`,
            'asset-market': `¥${this.formatAmount(account.market_value)}`,
            'asset-profit': `${profitPrefix}¥${this.formatAmount(account.total_profit)}`,
            'asset-profit-rate': `${profitPrefix}${account.profit_rate.toFixed(2)}%`
        };

        Object.entries(elements).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = value;
                if (id === 'asset-profit' || id === 'asset-profit-rate') {
                    el.style.color = isProfit ? '#ff4d4f' : '#52c41a';
                }
            }
        });
    }

    renderAccountStats(transactions) {
        const totalTrades = transactions.length;
        let totalAmount = 0;

        transactions.forEach(tx => {
            totalAmount += tx.total_amount;
        });

        const elements = {
            'stat-total-trades': totalTrades.toString(),
            'stat-total-amount': `¥${this.formatAmount(totalAmount)}`,
            'stat-win-rate': '--'
        };

        Object.entries(elements).forEach(([id, value]) => {
            const el = document.getElementById(id);
            if (el) {
                el.textContent = value;
            }
        });
    }

    formatNumber(num) {
        if (num >= 100000000) {
            return (num / 100000000).toFixed(2) + '亿';
        } else if (num >= 10000) {
            return (num / 10000).toFixed(2) + '万';
        }
        return num.toLocaleString();
    }

    formatAmount(amount) {
        if (Math.abs(amount) >= 100000000) {
            return (Math.abs(amount) / 100000000).toFixed(2) + '亿';
        } else if (Math.abs(amount) >= 10000) {
            return (Math.abs(amount) / 10000).toFixed(2) + '万';
        }
        return Math.abs(amount).toFixed(2);
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    showLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.remove('hidden');
        }
    }

    hideLoading() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.classList.add('hidden');
        }
    }

    showToast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        if (!container) return;

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;

        container.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideIn 0.3s ease reverse';
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 2500);
    }
}

const app = new StockTradingApp();
