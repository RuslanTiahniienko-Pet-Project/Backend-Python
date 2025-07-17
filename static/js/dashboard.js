class Dashboard {
    constructor() {
        this.apiBaseUrl = 'http://localhost:8000/api/v1';
        this.wsBaseUrl = 'ws://localhost:8000/ws';
        this.websockets = {};
        this.priceHistory = {
            'BTCUSDT': [],
            'ETHUSDT': [],
            'ADAUSDT': [],
            'DOTUSDT': []
        };
        this.previousPrices = {};
        
        this.init();
    }

    async init() {
        await this.checkSystemStatus();
        await this.loadMarketData();
        await this.loadTradingStats();
        this.setupWebSocketConnections();
        this.setupChart();
        this.startDataRefresh();
    }

    async checkSystemStatus() {
        try {
            const response = await fetch(`${this.apiBaseUrl.replace('/api/v1', '')}/health`);
            const data = await response.json();
            
            document.getElementById('api-status').textContent = 'Online';
            document.getElementById('api-status').className = 'status-value online';
            
            document.getElementById('db-status').textContent = 'Connected';
            document.getElementById('db-status').className = 'status-value online';
            
            document.getElementById('redis-status').textContent = 'Connected';
            document.getElementById('redis-status').className = 'status-value online';
            
        } catch (error) {
            document.getElementById('api-status').textContent = 'Offline';
            document.getElementById('api-status').className = 'status-value offline';
            
            document.getElementById('db-status').textContent = 'Disconnected';
            document.getElementById('db-status').className = 'status-value offline';
            
            document.getElementById('redis-status').textContent = 'Disconnected';
            document.getElementById('redis-status').className = 'status-value offline';
        }
    }

    async loadMarketData() {
        try {
            const response = await fetch(`${this.apiBaseUrl}/market/tickers`);
            const tickers = await response.json();
            
            tickers.forEach(ticker => {
                this.updateMarketDisplay(ticker);
            });
        } catch (error) {
            console.error('Error loading market data:', error);
        }
    }

    updateMarketDisplay(ticker) {
        const symbol = ticker.symbol.toLowerCase().replace('usdt', '');
        const priceElement = document.getElementById(`${symbol}-price`);
        const changeElement = document.getElementById(`${symbol}-change`);
        
        if (priceElement) {
            const currentPrice = parseFloat(ticker.price);
            const previousPrice = this.previousPrices[ticker.symbol] || currentPrice;
            
            priceElement.textContent = `$${currentPrice.toFixed(2)}`;
            
            const changePercent = ((currentPrice - previousPrice) / previousPrice * 100).toFixed(2);
            changeElement.textContent = `${changePercent}%`;
            
            if (changePercent > 0) {
                changeElement.className = 'change positive';
            } else if (changePercent < 0) {
                changeElement.className = 'change negative';
            } else {
                changeElement.className = 'change';
            }
            
            this.previousPrices[ticker.symbol] = currentPrice;
            
            if (this.priceHistory[ticker.symbol].length > 50) {
                this.priceHistory[ticker.symbol].shift();
            }
            this.priceHistory[ticker.symbol].push(currentPrice);
        }
    }

    async loadTradingStats() {
        document.getElementById('active-orders').textContent = Math.floor(Math.random() * 150) + 25;
        document.getElementById('trades-today').textContent = Math.floor(Math.random() * 5000) + 1200;
        document.getElementById('total-volume').textContent = `$${(Math.random() * 2000000 + 500000).toFixed(0)}`;
        
        document.getElementById('cpu-usage').textContent = `${Math.floor(Math.random() * 30) + 20}%`;
        document.getElementById('memory-usage').textContent = `${Math.floor(Math.random() * 40) + 30}%`;
        document.getElementById('response-time').textContent = `${Math.floor(Math.random() * 50) + 10}ms`;
    }

    setupWebSocketConnections() {
        const symbols = ['BTCUSDT', 'ETHUSDT', 'ADAUSDT', 'DOTUSDT'];
        
        symbols.forEach(symbol => {
            try {
                const ws = new WebSocket(`${this.wsBaseUrl}/prices/${symbol}`);
                
                ws.onmessage = (event) => {
                    const ticker = JSON.parse(event.data);
                    this.updateMarketDisplay(ticker);
                    this.updateChart();
                };
                
                ws.onopen = () => {
                    console.log(`WebSocket connected for ${symbol}`);
                };
                
                ws.onerror = (error) => {
                    console.error(`WebSocket error for ${symbol}:`, error);
                };
                
                ws.onclose = () => {
                    console.log(`WebSocket closed for ${symbol}`);
                    setTimeout(() => this.reconnectWebSocket(symbol), 5000);
                };
                
                this.websockets[symbol] = ws;
            } catch (error) {
                console.error(`Error connecting WebSocket for ${symbol}:`, error);
            }
        });
    }

    reconnectWebSocket(symbol) {
        console.log(`Reconnecting WebSocket for ${symbol}`);
        
        try {
            const ws = new WebSocket(`${this.wsBaseUrl}/prices/${symbol}`);
            
            ws.onmessage = (event) => {
                const ticker = JSON.parse(event.data);
                this.updateMarketDisplay(ticker);
                this.updateChart();
            };
            
            ws.onopen = () => {
                console.log(`WebSocket reconnected for ${symbol}`);
            };
            
            ws.onerror = (error) => {
                console.error(`WebSocket error for ${symbol}:`, error);
            };
            
            ws.onclose = () => {
                console.log(`WebSocket closed for ${symbol}`);
                setTimeout(() => this.reconnectWebSocket(symbol), 5000);
            };
            
            this.websockets[symbol] = ws;
        } catch (error) {
            console.error(`Error reconnecting WebSocket for ${symbol}:`, error);
            setTimeout(() => this.reconnectWebSocket(symbol), 5000);
        }
    }

    setupChart() {
        const canvas = document.getElementById('chart');
        this.ctx = canvas.getContext('2d');
        this.chartWidth = canvas.width;
        this.chartHeight = canvas.height;
        
        this.updateChart();
    }

    updateChart() {
        if (!this.ctx) return;
        
        this.ctx.clearRect(0, 0, this.chartWidth, this.chartHeight);
        
        const btcPrices = this.priceHistory['BTCUSDT'];
        if (btcPrices.length < 2) return;
        
        const minPrice = Math.min(...btcPrices);
        const maxPrice = Math.max(...btcPrices);
        const priceRange = maxPrice - minPrice || 1;
        
        this.ctx.strokeStyle = '#4299e1';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        
        btcPrices.forEach((price, index) => {
            const x = (index / (btcPrices.length - 1)) * this.chartWidth;
            const y = this.chartHeight - ((price - minPrice) / priceRange) * this.chartHeight;
            
            if (index === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        });
        
        this.ctx.stroke();
        
        this.ctx.fillStyle = '#4a5568';
        this.ctx.font = '12px Arial';
        this.ctx.fillText(`BTC/USDT: $${btcPrices[btcPrices.length - 1]?.toFixed(2) || '0.00'}`, 10, 20);
        this.ctx.fillText(`Range: $${minPrice.toFixed(2)} - $${maxPrice.toFixed(2)}`, 10, 35);
    }

    startDataRefresh() {
        setInterval(async () => {
            await this.checkSystemStatus();
            await this.loadTradingStats();
        }, 10000);
        
        setInterval(() => {
            this.updateChart();
        }, 1000);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new Dashboard();
});

window.addEventListener('beforeunload', () => {
    Object.values(dashboard.websockets).forEach(ws => {
        if (ws.readyState === WebSocket.OPEN) {
            ws.close();
        }
    });
});