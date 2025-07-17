from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import asyncio
import json
import jwt
from decimal import Decimal
import random
import hashlib

app = FastAPI(title="SecureTradeAPI Enhanced Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

security = HTTPBearer()

SECRET_KEY = "demo-secret-key-12345"
ALGORITHM = "HS256"

users_db = {}
user_wallets = {}
user_orders = {}
order_id_counter = 1000

symbols = {
    "BTCUSDT": {"price": Decimal("45000.00"), "volume": Decimal("1000.0")},
    "ETHUSDT": {"price": Decimal("3200.00"), "volume": Decimal("2000.0")},
    "ADAUSDT": {"price": Decimal("1.25"), "volume": Decimal("50000.0")},
    "DOTUSDT": {"price": Decimal("25.50"), "volume": Decimal("5000.0")}
}

class UserCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class OrderCreate(BaseModel):
    symbol: str
    side: str
    type: str
    quantity: float
    price: Optional[float] = None

class BalanceUpdate(BaseModel):
    currency: str
    amount: float
    action: str

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hashlib.sha256(password.encode()).hexdigest() == hashed

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=30)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user_id
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    user_id = verify_token(credentials.credentials)
    if user_id not in users_db:
        raise HTTPException(status_code=401, detail="User not found")
    return users_db[user_id]

def simulate_price_change():
    for symbol in symbols:
        current_price = symbols[symbol]["price"]
        change_percent = Decimal(str(random.uniform(-0.02, 0.02)))
        new_price = current_price * (1 + change_percent)
        symbols[symbol]["price"] = new_price
        symbols[symbol]["volume"] = Decimal(str(random.uniform(100, 3000)))

def init_user_wallet(user_id: str):
    if user_id not in user_wallets:
        user_wallets[user_id] = {
            "BTC": {"available": 0.1, "locked": 0.0},
            "ETH": {"available": 2.0, "locked": 0.0},
            "USDT": {"available": 10000.0, "locked": 0.0},
            "ADA": {"available": 1000.0, "locked": 0.0},
            "DOT": {"available": 50.0, "locked": 0.0}
        }
    if user_id not in user_orders:
        user_orders[user_id] = []

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SecureTradeAPI Enhanced Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .container { max-width: 1000px; margin: 0 auto; background: white; padding: 30px; border-radius: 15px; box-shadow: 0 10px 30px rgba(0,0,0,0.3); }
            h1 { color: #333; text-align: center; margin-bottom: 30px; }
            .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }
            .feature-card { background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #007bff; }
            .feature-card h3 { color: #007bff; margin-top: 0; }
            .api-section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 10px; background: #f8f9fa; }
            .endpoint { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .method { display: inline-block; padding: 4px 12px; border-radius: 20px; color: white; font-size: 12px; font-weight: bold; margin-right: 10px; }
            .get { background: #28a745; }
            .post { background: #007bff; }
            .delete { background: #dc3545; }
            code { background: #f8f9fa; padding: 3px 6px; border-radius: 3px; font-family: monospace; }
            .link { color: #007bff; text-decoration: none; font-weight: 500; }
            .link:hover { text-decoration: underline; }
            .auth-demo { background: #e3f2fd; padding: 20px; border-radius: 10px; margin: 20px 0; }
            .demo-user { background: #fff3cd; padding: 15px; border-radius: 8px; margin: 10px 0; }
            .status-badge { display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }
            .success { background: #d4edda; color: #155724; }
            .info { background: #cce5ff; color: #004085; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 SecureTradeAPI - Enhanced Crypto Trading Platform</h1>
            
            <div class="features">
                <div class="feature-card">
                    <h3>🔐 Authentication System</h3>
                    <p>JWT-based authentication with registration, login, and protected endpoints</p>
                    <span class="status-badge success">✅ Active</span>
                </div>
                <div class="feature-card">
                    <h3>💰 Wallet Management</h3>
                    <p>Multi-currency wallets with balance tracking and transaction history</p>
                    <span class="status-badge success">✅ Active</span>
                </div>
                <div class="feature-card">
                    <h3>📊 Trading Engine</h3>
                    <p>Order placement, management, and real-time market data</p>
                    <span class="status-badge success">✅ Active</span>
                </div>
            </div>
            
            <div class="auth-demo">
                <h3>🔐 Authentication Demo</h3>
                <p>Use these test credentials or register a new account:</p>
                <div class="demo-user">
                    <strong>Demo User:</strong><br>
                    Email: demo@example.com<br>
                    Password: demo123
                </div>
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <code>/api/v1/auth/register</code> - Register new user
                </div>
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <code>/api/v1/auth/login</code> - Get access token
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <code>/api/v1/auth/profile</code> - Get user profile (requires token)
                </div>
            </div>
            
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
                    <a href="/api/v1/market/orderbook/BTCUSDT" class="link">/api/v1/market/orderbook/BTCUSDT</a> - Get order book
                </div>
            </div>
            
            <div class="api-section">
                <h2>💼 Protected Endpoints (Require Authentication)</h2>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <code>/api/v1/wallet/balances</code> - Get user balances
                </div>
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <code>/api/v1/wallet/deposit</code> - Deposit funds
                </div>
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <code>/api/v1/trading/orders</code> - Place order
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <code>/api/v1/trading/orders</code> - Get user orders
                </div>
            </div>
            
            <div class="api-section">
                <h2>🎯 Dashboard</h2>
                <div class="endpoint">
                    <a href="/static/index.html" class="link">🖥️ Open Trading Dashboard</a>
                </div>
            </div>
            
            <div class="api-section">
                <h2>📱 cURL Examples</h2>
                <div class="endpoint">
                    <strong>Register:</strong><br>
                    <code>curl -X POST http://localhost:8000/api/v1/auth/register -H "Content-Type: application/json" -d '{"email": "test@example.com", "password": "test123", "first_name": "John", "last_name": "Doe"}'</code>
                </div>
                <div class="endpoint">
                    <strong>Login:</strong><br>
                    <code>curl -X POST http://localhost:8000/api/v1/auth/login -H "Content-Type: application/json" -d '{"email": "test@example.com", "password": "test123"}'</code>
                </div>
                <div class="endpoint">
                    <strong>Get Balances:</strong><br>
                    <code>curl -X GET http://localhost:8000/api/v1/wallet/balances -H "Authorization: Bearer YOUR_TOKEN"</code>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "SecureTradeAPI Enhanced"}

@app.post("/api/v1/auth/register", response_model=dict)
async def register(user_data: UserCreate):
    if user_data.email in [u["email"] for u in users_db.values()]:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_id = str(len(users_db) + 1)
    users_db[user_id] = {
        "id": user_id,
        "email": user_data.email,
        "password": hash_password(user_data.password),
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "created_at": datetime.utcnow().isoformat()
    }
    
    init_user_wallet(user_id)
    
    return {
        "message": "User registered successfully",
        "user_id": user_id,
        "email": user_data.email
    }

@app.post("/api/v1/auth/login", response_model=Token)
async def login(user_data: UserLogin):
    user = None
    user_id = None
    
    for uid, u in users_db.items():
        if u["email"] == user_data.email:
            user = u
            user_id = uid
            break
    
    if not user or not verify_password(user_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": user_id})
    
    return Token(access_token=access_token, token_type="bearer")

@app.get("/api/v1/auth/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "first_name": current_user["first_name"],
        "last_name": current_user["last_name"],
        "created_at": current_user["created_at"]
    }

@app.get("/api/v1/wallet/balances")
async def get_balances(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_wallet(user_id)
    
    balances = {}
    for currency, balance in user_wallets[user_id].items():
        balances[currency] = {
            "available": balance["available"],
            "locked": balance["locked"],
            "total": balance["available"] + balance["locked"]
        }
    
    return {"balances": balances}

@app.post("/api/v1/wallet/deposit")
async def deposit_funds(
    balance_update: BalanceUpdate,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_wallet(user_id)
    
    if balance_update.currency not in user_wallets[user_id]:
        raise HTTPException(status_code=400, detail="Currency not supported")
    
    user_wallets[user_id][balance_update.currency]["available"] += balance_update.amount
    
    return {
        "message": "Deposit successful",
        "currency": balance_update.currency,
        "amount": balance_update.amount,
        "new_balance": user_wallets[user_id][balance_update.currency]["available"]
    }

@app.post("/api/v1/trading/orders")
async def place_order(
    order_data: OrderCreate,
    current_user: dict = Depends(get_current_user)
):
    global order_id_counter
    user_id = current_user["id"]
    init_user_wallet(user_id)
    
    if order_data.symbol not in symbols:
        raise HTTPException(status_code=400, detail="Symbol not supported")
    
    order_id = order_id_counter
    order_id_counter += 1
    
    current_price = float(symbols[order_data.symbol]["price"])
    
    order = {
        "id": order_id,
        "user_id": user_id,
        "symbol": order_data.symbol,
        "side": order_data.side,
        "type": order_data.type,
        "quantity": order_data.quantity,
        "price": order_data.price or current_price,
        "status": "filled" if order_data.type == "market" else "pending",
        "created_at": datetime.utcnow().isoformat(),
        "filled_at": datetime.utcnow().isoformat() if order_data.type == "market" else None
    }
    
    user_orders[user_id].append(order)
    
    return {
        "message": "Order placed successfully",
        "order": order
    }

@app.get("/api/v1/trading/orders")
async def get_user_orders(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_wallet(user_id)
    
    return {"orders": user_orders[user_id]}

@app.get("/api/v1/trading/history")
async def get_trading_history(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_wallet(user_id)
    
    filled_orders = [order for order in user_orders[user_id] if order["status"] == "filled"]
    
    total_volume = sum(order["quantity"] * order["price"] for order in filled_orders)
    total_trades = len(filled_orders)
    
    symbols_traded = list(set(order["symbol"] for order in filled_orders))
    
    profit_loss = random.uniform(-500, 1500)
    
    return {
        "summary": {
            "total_trades": total_trades,
            "total_volume": round(total_volume, 2),
            "symbols_traded": symbols_traded,
            "profit_loss": round(profit_loss, 2),
            "success_rate": f"{random.uniform(60, 85):.1f}%"
        },
        "recent_trades": filled_orders[-10:],
        "monthly_stats": {
            "trades_this_month": random.randint(15, 50),
            "volume_this_month": round(random.uniform(5000, 25000), 2),
            "best_performing_symbol": random.choice(["BTCUSDT", "ETHUSDT", "ADAUSDT"]),
            "avg_trade_size": round(random.uniform(100, 1000), 2)
        }
    }

@app.get("/api/v1/analytics/portfolio")
async def get_portfolio_analytics(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_wallet(user_id)
    
    portfolio = {}
    total_value = 0
    
    for currency, balance in user_wallets[user_id].items():
        if currency == "USDT":
            price = 1.0
        else:
            symbol = f"{currency}USDT"
            if symbol in symbols:
                price = float(symbols[symbol]["price"])
            else:
                price = 1.0
        
        value = balance["available"] * price
        total_value += value
        
        portfolio[currency] = {
            "balance": balance["available"],
            "price": price,
            "value": round(value, 2),
            "percentage": 0
        }
    
    for currency in portfolio:
        portfolio[currency]["percentage"] = round((portfolio[currency]["value"] / total_value) * 100, 2) if total_value > 0 else 0
    
    return {
        "total_portfolio_value": round(total_value, 2),
        "portfolio_breakdown": portfolio,
        "performance": {
            "daily_change": f"{random.uniform(-5, 5):.2f}%",
            "weekly_change": f"{random.uniform(-10, 15):.2f}%",
            "monthly_change": f"{random.uniform(-20, 30):.2f}%"
        },
        "top_performer": max(portfolio.keys(), key=lambda x: portfolio[x]["value"]) if portfolio else None
    }

@app.get("/api/v1/market/tickers")
async def get_all_tickers():
    simulate_price_change()
    return [
        {
            "symbol": symbol,
            "price": str(data["price"]),
            "volume": str(data["volume"]),
            "change_24h": f"{random.uniform(-5, 5):.2f}%",
            "timestamp": datetime.utcnow().isoformat()
        }
        for symbol, data in symbols.items()
    ]

@app.get("/api/v1/market/ticker/{symbol}")
async def get_ticker(symbol: str):
    if symbol not in symbols:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    simulate_price_change()
    data = symbols[symbol]
    return {
        "symbol": symbol,
        "price": str(data["price"]),
        "volume": str(data["volume"]),
        "bid_price": str(data["price"] * Decimal("0.999")),
        "ask_price": str(data["price"] * Decimal("1.001")),
        "change_24h": f"{random.uniform(-5, 5):.2f}%",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/api/v1/market/orderbook/{symbol}")
async def get_orderbook(symbol: str):
    if symbol not in symbols:
        raise HTTPException(status_code=404, detail="Symbol not found")
    
    simulate_price_change()
    price = symbols[symbol]["price"]
    
    bids = []
    asks = []
    
    for i in range(5):
        bid_price = price * (1 - Decimal("0.001") * (i + 1))
        ask_price = price * (1 + Decimal("0.001") * (i + 1))
        
        bids.append({
            "price": float(bid_price),
            "quantity": round(random.uniform(0.1, 5.0), 4)
        })
        asks.append({
            "price": float(ask_price),
            "quantity": round(random.uniform(0.1, 5.0), 4)
        })
    
    return {
        "symbol": symbol,
        "bids": bids,
        "asks": asks,
        "best_bid": float(bids[0]["price"]),
        "best_ask": float(asks[0]["price"])
    }

@app.on_event("startup")
async def startup_event():
    users_db["demo"] = {
        "id": "demo",
        "email": "demo@example.com",
        "password": hash_password("demo123"),
        "first_name": "Demo",
        "last_name": "User",
        "created_at": datetime.utcnow().isoformat()
    }
    init_user_wallet("demo")

class NotificationManager:
    def __init__(self):
        self.connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.connections:
            self.connections[user_id] = []
        self.connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, user_id: str):
        if user_id in self.connections:
            self.connections[user_id].remove(websocket)
    
    async def send_notification(self, user_id: str, message: dict):
        if user_id in self.connections:
            for connection in self.connections[user_id]:
                try:
                    await connection.send_text(json.dumps(message))
                except:
                    self.connections[user_id].remove(connection)

notification_manager = NotificationManager()

@app.websocket("/ws/notifications/{user_id}")
async def websocket_notifications(websocket: WebSocket, user_id: str):
    await notification_manager.connect(websocket, user_id)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_manager.disconnect(websocket, user_id)

@app.websocket("/ws/prices/{symbol}")
async def websocket_prices(websocket: WebSocket, symbol: str):
    await websocket.accept()
    try:
        while True:
            simulate_price_change()
            if symbol in symbols:
                data = symbols[symbol]
                price_update = {
                    "symbol": symbol,
                    "price": str(data["price"]),
                    "volume": str(data["volume"]),
                    "timestamp": datetime.utcnow().isoformat(),
                    "change": f"{random.uniform(-2, 2):.2f}%"
                }
                await websocket.send_text(json.dumps(price_update))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

async def send_order_notification(user_id: str, order: dict):
    notification = {
        "type": "order_update",
        "data": order,
        "timestamp": datetime.utcnow().isoformat(),
        "message": f"Order {order['id']} has been {order['status']}"
    }
    await notification_manager.send_notification(user_id, notification)

async def send_price_alert(user_id: str, symbol: str, price: float, threshold: float):
    notification = {
        "type": "price_alert",
        "data": {
            "symbol": symbol,
            "price": price,
            "threshold": threshold
        },
        "timestamp": datetime.utcnow().isoformat(),
        "message": f"{symbol} price reached ${price:.2f}"
    }
    await notification_manager.send_notification(user_id, notification)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)