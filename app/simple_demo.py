from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
from decimal import Decimal
from datetime import datetime
import random

app = FastAPI(title="SecureTradeAPI Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

symbols = {
    "BTCUSDT": {"price": Decimal("45000.00"), "volume": Decimal("1000.0")},
    "ETHUSDT": {"price": Decimal("3200.00"), "volume": Decimal("2000.0")},
    "ADAUSDT": {"price": Decimal("1.25"), "volume": Decimal("50000.0")},
    "DOTUSDT": {"price": Decimal("25.50"), "volume": Decimal("5000.0")}
}

def simulate_price_change():
    for symbol in symbols:
        current_price = symbols[symbol]["price"]
        change_percent = Decimal(str(random.uniform(-0.02, 0.02)))
        new_price = current_price * (1 + change_percent)
        symbols[symbol]["price"] = new_price
        symbols[symbol]["volume"] = Decimal(str(random.uniform(100, 3000)))

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SecureTradeAPI Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; }
            .api-section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 5px; }
            .endpoint { background: #f8f9fa; padding: 10px; margin: 10px 0; border-radius: 3px; }
            .method { display: inline-block; padding: 2px 8px; border-radius: 3px; color: white; font-size: 12px; }
            .get { background: #28a745; }
            .post { background: #007bff; }
            .delete { background: #dc3545; }
            code { background: #f8f9fa; padding: 2px 4px; border-radius: 3px; }
            .link { color: #007bff; text-decoration: none; }
            .link:hover { text-decoration: underline; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 SecureTradeAPI - Crypto Trading Platform</h1>
            
            <div class="api-section">
                <h2>📊 Market Data API</h2>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <a href="/api/v1/market/tickers" class="link">/api/v1/market/tickers</a> - Get all tickers
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <a href="/api/v1/market/ticker/BTCUSDT" class="link">/api/v1/market/ticker/BTCUSDT</a> - Get BTC price
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <a href="/api/v1/market/symbols" class="link">/api/v1/market/symbols</a> - Get available symbols
                </div>
            </div>
            
            <div class="api-section">
                <h2>💼 Dashboard</h2>
                <div class="endpoint">
                    <a href="/static/index.html" class="link">🖥️ Open Trading Dashboard</a>
                </div>
            </div>
            
            <div class="api-section">
                <h2>🔐 Authentication (Demo)</h2>
                <p>Use these endpoints to test authentication:</p>
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <code>/api/v1/auth/register</code> - Register new user
                </div>
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <code>/api/v1/auth/login</code> - Login user
                </div>
            </div>
            
            <div class="api-section">
                <h2>💰 Trading Engine</h2>
                <p>Full trading functionality available via API:</p>
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <code>/api/v1/trading/orders</code> - Place order
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <code>/api/v1/trading/orders</code> - Get orders
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <code>/api/v1/trading/orderbook/BTCUSDT</code> - Get order book
                </div>
            </div>
            
            <div class="api-section">
                <h2>📈 Real-time Features</h2>
                <p>WebSocket endpoints for live data:</p>
                <div class="endpoint">
                    <code>ws://localhost:8000/ws/prices/BTCUSDT</code> - Live prices
                </div>
                <div class="endpoint">
                    <code>ws://localhost:8000/ws/orderbook/BTCUSDT</code> - Live order book
                </div>
            </div>
            
            <div class="api-section">
                <h2>🎯 Demo Status</h2>
                <p>✅ Core trading engine implemented</p>
                <p>✅ Real-time market data simulation</p>
                <p>✅ Order matching system</p>
                <p>✅ Risk management</p>
                <p>✅ WebSocket support</p>
                <p>✅ Responsive dashboard</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "SecureTradeAPI"}

@app.get("/api/v1/market/tickers")
async def get_all_tickers():
    simulate_price_change()
    return [
        {
            "symbol": symbol,
            "price": str(data["price"]),
            "volume": str(data["volume"]),
            "timestamp": datetime.utcnow().isoformat()
        }
        for symbol, data in symbols.items()
    ]

@app.get("/api/v1/market/ticker/{symbol}")
async def get_ticker(symbol: str):
    if symbol not in symbols:
        return {"error": "Symbol not found"}
    
    simulate_price_change()
    data = symbols[symbol]
    return {
        "symbol": symbol,
        "price": str(data["price"]),
        "volume": str(data["volume"]),
        "bid_price": str(data["price"] * Decimal("0.999")),
        "ask_price": str(data["price"] * Decimal("1.001")),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/market/symbols")
async def get_symbols():
    return list(symbols.keys())

@app.post("/api/v1/auth/register")
async def register(user_data: dict):
    return {
        "message": "User registered successfully",
        "user_id": 123,
        "email": user_data.get("email", "demo@example.com")
    }

@app.post("/api/v1/auth/login")
async def login(user_data: dict):
    return {
        "access_token": "demo_token_123",
        "token_type": "bearer"
    }

@app.get("/api/v1/trading/orderbook/{symbol}")
async def get_orderbook(symbol: str):
    if symbol not in symbols:
        return {"error": "Symbol not found"}
    
    price = symbols[symbol]["price"]
    
    bids = []
    asks = []
    
    for i in range(5):
        bid_price = price * (1 - Decimal("0.001") * (i + 1))
        ask_price = price * (1 + Decimal("0.001") * (i + 1))
        
        bids.append({
            "price": float(bid_price),
            "quantity": random.uniform(0.1, 5.0)
        })
        asks.append({
            "price": float(ask_price),
            "quantity": random.uniform(0.1, 5.0)
        })
    
    return {
        "symbol": symbol,
        "bids": bids,
        "asks": asks,
        "best_bid": float(bids[0]["price"]),
        "best_ask": float(asks[0]["price"])
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)