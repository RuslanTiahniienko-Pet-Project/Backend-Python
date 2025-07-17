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
from enum import Enum

app = FastAPI(title="SecureTradeAPI Advanced Demo")

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

class UserRole(str, Enum):
    USER = "user"
    ADMIN = "admin"
    TRADER = "trader"

class KYCStatus(str, Enum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

users_db = {}
user_wallets = {}
user_orders = {}
user_trades = {}
user_notifications = {}
trading_bots = {}
kyc_documents = {}
notification_settings = {}
alert_rules = {}
user_kyc_status = {}
user_personal_info = {}
user_payment_methods = {}
user_transactions = {}
order_id_counter = 1000

symbols = {
    "BTCUSDT": {"price": Decimal("45000.00"), "volume": Decimal("1000.0"), "change_24h": 0.0},
    "ETHUSDT": {"price": Decimal("3200.00"), "volume": Decimal("2000.0"), "change_24h": 0.0},
    "ADAUSDT": {"price": Decimal("1.25"), "volume": Decimal("50000.0"), "change_24h": 0.0},
    "DOTUSDT": {"price": Decimal("25.50"), "volume": Decimal("5000.0"), "change_24h": 0.0}
}

class UserCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str

class UserLogin(BaseModel):
    email: str
    password: str
    totp_code: Optional[str] = None

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

class TwoFactorSetup(BaseModel):
    totp_code: str

class KYCDocument(BaseModel):
    document_type: str
    document_data: str
    
class TradingBot(BaseModel):
    name: str
    strategy: str
    symbol: str
    parameters: Dict
    
class BotStrategy(str, Enum):
    GRID = "grid"
    MOMENTUM = "momentum"
    MEAN_REVERSION = "mean_reversion"
    ARBITRAGE = "arbitrage"
    SCALPING = "scalping"
    
class BotStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    
class BotCreate(BaseModel):
    name: str
    strategy: str
    symbol: str
    parameters: Dict
    
class BotUpdate(BaseModel):
    status: Optional[str] = None
    parameters: Optional[Dict] = None

class NotificationType(str, Enum):
    PRICE_ALERT = "price_alert"
    ORDER_FILLED = "order_filled"
    TRADE_EXECUTED = "trade_executed"
    RISK_WARNING = "risk_warning"
    SYSTEM_UPDATE = "system_update"
    BOT_STATUS = "bot_status"
    PORTFOLIO_UPDATE = "portfolio_update"
    
class NotificationPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class NotificationChannel(str, Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    TELEGRAM = "telegram"
    SLACK = "slack"
    WEBHOOK = "webhook"

class NotificationCreate(BaseModel):
    type: str
    title: str
    message: str
    priority: Optional[str] = "medium"
    channels: Optional[List[str]] = []
    
class NotificationSettings(BaseModel):
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    telegram_enabled: bool = False
    slack_enabled: bool = False
    webhook_enabled: bool = False
    webhook_url: Optional[str] = None
    telegram_token: Optional[str] = None
    slack_webhook: Optional[str] = None
    
class AlertRule(BaseModel):
    name: str
    symbol: str
    condition: str
    value: float
    enabled: bool = True

class KYCDocumentType(str, Enum):
    PASSPORT = "passport"
    DRIVERS_LICENSE = "drivers_license"
    NATIONAL_ID = "national_id"
    PROOF_OF_ADDRESS = "proof_of_address"
    BANK_STATEMENT = "bank_statement"
    UTILITY_BILL = "utility_bill"
    SELFIE = "selfie"

class KYCDocumentCreate(BaseModel):
    document_type: str
    document_number: Optional[str] = None
    document_data: str
    country: Optional[str] = None
    expiry_date: Optional[str] = None
    
class KYCUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None
    
class PersonalInfo(BaseModel):
    first_name: str
    last_name: str
    date_of_birth: str
    nationality: str
    address: str
    city: str
    postal_code: str
    country: str
    phone: str

class PaymentMethod(str, Enum):
    CARD = "card"
    BANK_TRANSFER = "bank_transfer"
    CRYPTO = "crypto"
    PAYPAL = "paypal"
    APPLE_PAY = "apple_pay"
    GOOGLE_PAY = "google_pay"

class TransactionType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    
class TransactionStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class DepositRequest(BaseModel):
    amount: float
    currency: str
    payment_method: str
    
class WithdrawalRequest(BaseModel):
    amount: float
    currency: str
    payment_method: str
    destination: str
    
class PaymentMethodCreate(BaseModel):
    type: str
    name: str
    details: Dict
    
class TransactionCreate(BaseModel):
    type: str
    amount: float
    currency: str
    payment_method: str
    destination: Optional[str] = None

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

async def get_admin_user(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def simulate_price_change():
    for symbol in symbols:
        current_price = symbols[symbol]["price"]
        old_price = current_price
        
        change_percent = Decimal(str(random.uniform(-0.02, 0.02)))
        new_price = current_price * (1 + change_percent)
        symbols[symbol]["price"] = new_price
        symbols[symbol]["volume"] = Decimal(str(random.uniform(100, 3000)))
        symbols[symbol]["change_24h"] = float((new_price - old_price) / old_price * 100)

def init_user_data(user_id: str):
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
    if user_id not in user_trades:
        user_trades[user_id] = []
    if user_id not in user_notifications:
        user_notifications[user_id] = []
    if user_id not in notification_settings:
        notification_settings[user_id] = {
            "email_enabled": True,
            "sms_enabled": False,
            "push_enabled": True,
            "telegram_enabled": False,
            "slack_enabled": False,
            "webhook_enabled": False,
            "webhook_url": None,
            "telegram_token": None,
            "slack_webhook": None
        }
    if user_id not in alert_rules:
        alert_rules[user_id] = []
    if user_id not in trading_bots:
        trading_bots[user_id] = []
    if user_id not in user_kyc_status:
        user_kyc_status[user_id] = "not_started"
    if user_id not in user_personal_info:
        user_personal_info[user_id] = {}
    if user_id not in kyc_documents:
        kyc_documents[user_id] = []
    if user_id not in user_payment_methods:
        user_payment_methods[user_id] = []
    if user_id not in user_transactions:
        user_transactions[user_id] = []

@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SecureTradeAPI Advanced Demo</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 15px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); }
            h1 { color: #333; text-align: center; margin-bottom: 30px; }
            .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; margin: 30px 0; }
            .feature-card { background: #f8f9fa; padding: 20px; border-radius: 10px; border-left: 4px solid #007bff; }
            .feature-card h3 { color: #007bff; margin-top: 0; }
            .feature-card.new { border-left-color: #28a745; }
            .feature-card.new h3 { color: #28a745; }
            .api-section { margin: 20px 0; padding: 20px; border: 1px solid #ddd; border-radius: 10px; background: #f8f9fa; }
            .endpoint { background: white; padding: 15px; margin: 10px 0; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            .method { display: inline-block; padding: 4px 12px; border-radius: 20px; color: white; font-size: 12px; font-weight: bold; margin-right: 10px; }
            .get { background: #28a745; }
            .post { background: #007bff; }
            .delete { background: #dc3545; }
            .put { background: #ffc107; color: #212529; }
            code { background: #f8f9fa; padding: 3px 6px; border-radius: 3px; font-family: monospace; }
            .link { color: #007bff; text-decoration: none; font-weight: 500; }
            .link:hover { text-decoration: underline; }
            .status-badge { display: inline-block; padding: 4px 8px; border-radius: 12px; font-size: 11px; font-weight: bold; }
            .success { background: #d4edda; color: #155724; }
            .new { background: #d1ecf1; color: #0c5460; }
            .dashboard-links { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 30px 0; }
            .dashboard-link { background: #007bff; color: white; padding: 15px; text-align: center; border-radius: 8px; text-decoration: none; font-weight: 500; }
            .dashboard-link:hover { background: #0056b3; color: white; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 SecureTradeAPI - Advanced Trading Platform</h1>
            
            <div class="features">
                <div class="feature-card new">
                    <h3>🔐 2FA Authentication</h3>
                    <p>Google Authenticator integration with backup codes</p>
                    <span class="status-badge new">✨ NEW</span>
                </div>
                <div class="feature-card new">
                    <h3>👑 Admin Panel</h3>
                    <p>Complete user management and platform administration</p>
                    <span class="status-badge new">✨ NEW</span>
                </div>
                <div class="feature-card new">
                    <h3>📊 Order Book Visualization</h3>
                    <p>Real-time order book with depth charts</p>
                    <span class="status-badge new">✨ NEW</span>
                </div>
                <div class="feature-card new">
                    <h3>📈 Advanced Charts</h3>
                    <p>TradingView integration with technical indicators</p>
                    <span class="status-badge new">✨ NEW</span>
                </div>
                <div class="feature-card new">
                    <h3>🤖 Trading Bots</h3>
                    <p>Automated trading strategies and backtesting</p>
                    <span class="status-badge new">✨ NEW</span>
                </div>
                <div class="feature-card new">
                    <h3>🎯 Risk Management</h3>
                    <p>Advanced risk controls and position management</p>
                    <span class="status-badge new">✨ NEW</span>
                </div>
            </div>
            
            <div class="dashboard-links">
                <a href="/static/auth.html" class="dashboard-link">🔐 Login / Register</a>
                <a href="/static/admin.html" class="dashboard-link">👑 Admin Panel</a>
                <a href="/static/trading.html" class="dashboard-link">📊 Trading Dashboard</a>
                <a href="/static/analytics.html" class="dashboard-link">📈 Analytics</a>
                <a href="/static/bots.html" class="dashboard-link">🤖 Trading Bots</a>
                <a href="/static/kyc.html" class="dashboard-link">🆔 KYC Verification</a>
            </div>
            
            <div class="api-section">
                <h2>🔐 2FA Authentication</h2>
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <code>/api/v1/auth/2fa/setup</code> - Setup 2FA
                </div>
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <code>/api/v1/auth/2fa/verify</code> - Verify 2FA code
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <code>/api/v1/auth/2fa/qr</code> - Get QR code
                </div>
            </div>
            
            <div class="api-section">
                <h2>👑 Admin Panel</h2>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <code>/api/v1/admin/users</code> - Get all users
                </div>
                <div class="endpoint">
                    <span class="method put">PUT</span>
                    <code>/api/v1/admin/users/{user_id}</code> - Update user
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <code>/api/v1/admin/stats</code> - Platform statistics
                </div>
            </div>
            
            <div class="api-section">
                <h2>🤖 Trading Bots</h2>
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <code>/api/v1/bots</code> - Create trading bot
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <code>/api/v1/bots</code> - Get user bots
                </div>
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <code>/api/v1/bots/{bot_id}/start</code> - Start bot
                </div>
            </div>
            
            <div class="api-section">
                <h2>🆔 KYC Verification</h2>
                <div class="endpoint">
                    <span class="method post">POST</span>
                    <code>/api/v1/kyc/upload</code> - Upload KYC document
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <code>/api/v1/kyc/status</code> - Get KYC status
                </div>
            </div>
            
            <div class="api-section">
                <h2>📊 Analytics & Risk</h2>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <code>/api/v1/analytics/portfolio</code> - Portfolio analytics
                </div>
                <div class="endpoint">
                    <span class="method get">GET</span>
                    <code>/api/v1/risk/assessment</code> - Risk assessment
                </div>
            </div>
        </div>
    </body>
    </html>
    """

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
        "role": UserRole.USER,
        "kyc_status": KYCStatus.NOT_STARTED,
        "is_2fa_enabled": False,
        "two_factor_secret": None,
        "backup_codes": [],
        "created_at": datetime.utcnow().isoformat(),
        "last_login": None
    }
    
    init_user_data(user_id)
    
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
    
    if user["is_2fa_enabled"]:
        if not user_data.totp_code:
            raise HTTPException(status_code=401, detail="2FA code required")
        
        from app.services.two_factor_auth import two_factor_service
        if not two_factor_service.verify_token(user["two_factor_secret"], user_data.totp_code):
            raise HTTPException(status_code=401, detail="Invalid 2FA code")
    
    user["last_login"] = datetime.utcnow().isoformat()
    access_token = create_access_token(data={"sub": user_id})
    
    return Token(access_token=access_token, token_type="bearer")

@app.get("/api/v1/auth/2fa/setup")
async def setup_2fa(current_user: dict = Depends(get_current_user)):
    if current_user["is_2fa_enabled"]:
        raise HTTPException(status_code=400, detail="2FA already enabled")
    
    from app.services.two_factor_auth import two_factor_service
    
    secret = two_factor_service.generate_secret()
    qr_code = two_factor_service.generate_qr_code(current_user["email"], secret)
    backup_codes = two_factor_service.generate_backup_codes()
    
    current_user["two_factor_secret"] = secret
    current_user["backup_codes"] = backup_codes
    
    return {
        "secret": secret,
        "qr_code": qr_code,
        "backup_codes": backup_codes
    }

@app.post("/api/v1/auth/2fa/verify")
async def verify_2fa(
    setup_data: TwoFactorSetup,
    current_user: dict = Depends(get_current_user)
):
    if not current_user["two_factor_secret"]:
        raise HTTPException(status_code=400, detail="2FA not set up")
    
    from app.services.two_factor_auth import two_factor_service
    
    if not two_factor_service.verify_token(current_user["two_factor_secret"], setup_data.totp_code):
        raise HTTPException(status_code=400, detail="Invalid 2FA code")
    
    current_user["is_2fa_enabled"] = True
    
    return {"message": "2FA enabled successfully"}

@app.get("/api/v1/auth/profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    return {
        "id": current_user["id"],
        "email": current_user["email"],
        "first_name": current_user["first_name"],
        "last_name": current_user["last_name"],
        "role": current_user["role"],
        "kyc_status": current_user["kyc_status"],
        "is_2fa_enabled": current_user["is_2fa_enabled"],
        "created_at": current_user["created_at"],
        "last_login": current_user["last_login"]
    }

@app.on_event("startup")
async def startup_event():
    users_db["admin"] = {
        "id": "admin",
        "email": "admin@example.com",
        "password": hash_password("admin123"),
        "first_name": "Admin",
        "last_name": "User",
        "role": UserRole.ADMIN,
        "kyc_status": KYCStatus.APPROVED,
        "is_2fa_enabled": False,
        "two_factor_secret": None,
        "backup_codes": [],
        "created_at": datetime.utcnow().isoformat(),
        "last_login": None
    }
    init_user_data("admin")
    
    users_db["demo"] = {
        "id": "demo",
        "email": "demo@example.com",
        "password": hash_password("demo123"),
        "first_name": "Demo",
        "last_name": "User",
        "role": UserRole.USER,
        "kyc_status": KYCStatus.PENDING,
        "is_2fa_enabled": False,
        "two_factor_secret": None,
        "backup_codes": [],
        "created_at": datetime.utcnow().isoformat(),
        "last_login": None
    }
    init_user_data("demo")

@app.get("/api/v1/admin/users")
async def get_all_users(admin_user: dict = Depends(get_admin_user)):
    users = []
    for user_id, user in users_db.items():
        users.append({
            "id": user["id"],
            "email": user["email"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "role": user["role"],
            "kyc_status": user["kyc_status"],
            "is_2fa_enabled": user["is_2fa_enabled"],
            "created_at": user["created_at"],
            "last_login": user["last_login"]
        })
    return {"users": users}

@app.put("/api/v1/admin/users/{user_id}")
async def update_user(
    user_id: str,
    update_data: dict,
    admin_user: dict = Depends(get_admin_user)
):
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    user = users_db[user_id]
    
    if "role" in update_data:
        user["role"] = update_data["role"]
    if "kyc_status" in update_data:
        user["kyc_status"] = update_data["kyc_status"]
    if "is_active" in update_data:
        user["is_active"] = update_data["is_active"]
    
    return {"message": "User updated successfully", "user": user}

@app.get("/api/v1/admin/stats")
async def get_platform_stats(admin_user: dict = Depends(get_admin_user)):
    total_users = len(users_db)
    active_users = len([u for u in users_db.values() if u.get("last_login")])
    
    total_trades = sum(len(trades) for trades in user_trades.values())
    total_volume = sum(
        sum(trade.get("volume", 0) for trade in trades) 
        for trades in user_trades.values()
    )
    
    kyc_stats = {
        "not_started": len([u for u in users_db.values() if u["kyc_status"] == KYCStatus.NOT_STARTED]),
        "pending": len([u for u in users_db.values() if u["kyc_status"] == KYCStatus.PENDING]),
        "approved": len([u for u in users_db.values() if u["kyc_status"] == KYCStatus.APPROVED]),
        "rejected": len([u for u in users_db.values() if u["kyc_status"] == KYCStatus.REJECTED])
    }
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "total_trades": total_trades,
        "total_volume": total_volume,
        "kyc_stats": kyc_stats,
        "total_bots": sum(len(bots) for bots in trading_bots.values())
    }

@app.post("/api/v1/admin/users/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    admin_user: dict = Depends(get_admin_user)
):
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    users_db[user_id]["is_active"] = False
    return {"message": "User suspended successfully"}

@app.post("/api/v1/admin/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    admin_user: dict = Depends(get_admin_user)
):
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")
    
    users_db[user_id]["is_active"] = True
    return {"message": "User activated successfully"}

@app.get("/api/v1/admin/trades")
async def get_all_trades(admin_user: dict = Depends(get_admin_user)):
    all_trades = []
    for user_id, trades in user_trades.items():
        for trade in trades:
            trade_data = trade.copy()
            trade_data["user_id"] = user_id
            trade_data["user_email"] = users_db[user_id]["email"]
            all_trades.append(trade_data)
    
    return {"trades": all_trades[-100:]}

@app.get("/api/v1/wallet/balances")
async def get_balances(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
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
    init_user_data(user_id)
    
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
    init_user_data(user_id)
    
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
    
    if order_data.type == "market":
        trade = {
            "id": order_id,
            "symbol": order_data.symbol,
            "side": order_data.side,
            "quantity": order_data.quantity,
            "price": current_price,
            "volume": order_data.quantity * current_price,
            "executed_at": datetime.utcnow().isoformat()
        }
        user_trades[user_id].append(trade)
    
    return {
        "message": "Order placed successfully",
        "order": order
    }

@app.get("/api/v1/trading/orders")
async def get_user_orders(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    return {"orders": user_orders[user_id]}

@app.get("/api/v1/market/tickers")
async def get_all_tickers():
    simulate_price_change()
    return [
        {
            "symbol": symbol,
            "price": str(data["price"]),
            "volume": str(data["volume"]),
            "change_24h": f"{data['change_24h']:.2f}%",
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
        "change_24h": f"{data['change_24h']:.2f}%",
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
    
    for i in range(20):
        bid_price = price * (1 - Decimal("0.001") * (i + 1))
        ask_price = price * (1 + Decimal("0.001") * (i + 1))
        
        bid_quantity = random.uniform(0.1, 10.0) * (1 - i * 0.05)
        ask_quantity = random.uniform(0.1, 10.0) * (1 - i * 0.05)
        
        bids.append({
            "price": round(float(bid_price), 2),
            "quantity": round(bid_quantity, 4),
            "total": round(bid_quantity * float(bid_price), 2)
        })
        asks.append({
            "price": round(float(ask_price), 2),
            "quantity": round(ask_quantity, 4),
            "total": round(ask_quantity * float(ask_price), 2)
        })
    
    return {
        "symbol": symbol,
        "bids": bids,
        "asks": asks,
        "spread": round(float(asks[0]["price"] - bids[0]["price"]), 2),
        "spread_percent": round((asks[0]["price"] - bids[0]["price"]) / bids[0]["price"] * 100, 4),
        "timestamp": datetime.utcnow().isoformat()
    }

@app.websocket("/ws/orderbook/{symbol}")
async def websocket_orderbook(websocket: WebSocket, symbol: str):
    await websocket.accept()
    try:
        while True:
            orderbook = await get_orderbook(symbol)
            await websocket.send_text(json.dumps(orderbook))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

@app.websocket("/ws/prices/{symbol}")
async def websocket_prices(websocket: WebSocket, symbol: str):
    await websocket.accept()
    try:
        while True:
            ticker = await get_ticker(symbol)
            await websocket.send_text(json.dumps(ticker))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass

@app.get("/api/v1/analytics/portfolio")
async def get_portfolio_analytics(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
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
            "percentage": 0,
            "change_24h": random.uniform(-5, 5),
            "pnl": random.uniform(-1000, 2000)
        }
    
    for currency in portfolio:
        portfolio[currency]["percentage"] = round((portfolio[currency]["value"] / total_value) * 100, 2) if total_value > 0 else 0
    
    trades = user_trades.get(user_id, [])
    total_trades = len(trades)
    winning_trades = len([t for t in trades if random.random() > 0.4])
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    return {
        "total_portfolio_value": round(total_value, 2),
        "portfolio_breakdown": portfolio,
        "performance": {
            "daily_change": f"{random.uniform(-5, 5):.2f}%",
            "weekly_change": f"{random.uniform(-10, 15):.2f}%",
            "monthly_change": f"{random.uniform(-20, 30):.2f}%",
            "yearly_change": f"{random.uniform(-40, 80):.2f}%",
            "total_pnl": round(sum(p["pnl"] for p in portfolio.values()), 2)
        },
        "statistics": {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": total_trades - winning_trades,
            "win_rate": round(win_rate, 2),
            "avg_profit": round(random.uniform(50, 200), 2),
            "avg_loss": round(random.uniform(-150, -30), 2),
            "profit_factor": round(random.uniform(1.2, 2.5), 2),
            "sharpe_ratio": round(random.uniform(0.5, 2.0), 2)
        },
        "risk_metrics": {
            "var_95": round(random.uniform(500, 2000), 2),
            "max_drawdown": round(random.uniform(5, 25), 2),
            "volatility": round(random.uniform(15, 45), 2),
            "beta": round(random.uniform(0.8, 1.5), 2),
            "correlation_btc": round(random.uniform(0.3, 0.9), 2)
        },
        "top_performer": max(portfolio.keys(), key=lambda x: portfolio[x]["value"]) if portfolio else None,
        "worst_performer": min(portfolio.keys(), key=lambda x: portfolio[x]["change_24h"]) if portfolio else None
    }

@app.get("/api/v1/analytics/performance")
async def get_performance_analytics(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    # Generate performance history
    performance_data = []
    base_value = 10000
    
    for i in range(30):
        change = random.uniform(-0.05, 0.08)
        base_value *= (1 + change)
        
        performance_data.append({
            "date": (datetime.utcnow() - timedelta(days=29-i)).strftime("%Y-%m-%d"),
            "portfolio_value": round(base_value, 2),
            "daily_return": round(change * 100, 2),
            "cumulative_return": round(((base_value - 10000) / 10000) * 100, 2)
        })
    
    return {
        "performance_history": performance_data,
        "monthly_returns": [
            {"month": "Jan", "return": round(random.uniform(-10, 15), 2)},
            {"month": "Feb", "return": round(random.uniform(-8, 12), 2)},
            {"month": "Mar", "return": round(random.uniform(-5, 20), 2)},
            {"month": "Apr", "return": round(random.uniform(-12, 8), 2)},
            {"month": "May", "return": round(random.uniform(-3, 25), 2)},
            {"month": "Jun", "return": round(random.uniform(-15, 10), 2)},
        ],
        "sector_allocation": {
            "DeFi": round(random.uniform(20, 40), 2),
            "Layer1": round(random.uniform(25, 45), 2),
            "Layer2": round(random.uniform(10, 25), 2),
            "NFT": round(random.uniform(5, 15), 2),
            "Gaming": round(random.uniform(3, 12), 2),
            "Stablecoins": round(random.uniform(15, 30), 2)
        }
    }

@app.get("/api/v1/risk/assessment")
async def get_risk_assessment(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    # Calculate risk metrics
    balances = user_wallets[user_id]
    total_value = sum(balance["available"] for balance in balances.values())
    
    # Position concentration risk
    largest_position = max(balances.values(), key=lambda x: x["available"])["available"]
    concentration_risk = (largest_position / total_value * 100) if total_value > 0 else 0
    
    # Leverage simulation
    leverage_ratio = random.uniform(1.0, 3.0)
    
    # Calculate risk score
    risk_score = min(100, (concentration_risk * 0.4) + (leverage_ratio * 15) + random.uniform(10, 30))
    
    return {
        "risk_score": round(risk_score, 2),
        "risk_level": "LOW" if risk_score < 30 else "MEDIUM" if risk_score < 60 else "HIGH",
        "concentration_risk": round(concentration_risk, 2),
        "leverage_ratio": round(leverage_ratio, 2),
        "daily_var": round(random.uniform(500, 2000), 2),
        "max_drawdown": round(random.uniform(5, 25), 2),
        "position_limits": {
            "max_position_size": 50000,
            "max_leverage": 5.0,
            "max_daily_loss": 5000,
            "max_open_positions": 10
        },
        "current_positions": len(user_orders.get(user_id, [])),
        "margin_usage": round(random.uniform(20, 70), 2),
        "available_margin": round(random.uniform(5000, 15000), 2),
        "alerts": [
            {
                "type": "warning",
                "message": "High concentration in BTC position",
                "severity": "medium"
            },
            {
                "type": "info", 
                "message": "Daily loss limit approaching",
                "severity": "low"
            }
        ]
    }

@app.get("/api/v1/bots")
async def get_trading_bots(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    if user_id not in trading_bots:
        trading_bots[user_id] = []
    
    return {"bots": trading_bots[user_id]}

@app.post("/api/v1/bots")
async def create_trading_bot(bot: BotCreate, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    if user_id not in trading_bots:
        trading_bots[user_id] = []
    
    bot_id = len(trading_bots[user_id]) + 1
    new_bot = {
        "id": bot_id,
        "name": bot.name,
        "strategy": bot.strategy,
        "symbol": bot.symbol,
        "parameters": bot.parameters,
        "status": "active",
        "created_at": datetime.utcnow().isoformat(),
        "profit_loss": 0.0,
        "total_trades": 0,
        "win_rate": 0.0,
        "last_trade": None,
        "performance": {
            "daily_return": 0.0,
            "total_return": 0.0,
            "max_drawdown": 0.0,
            "sharpe_ratio": 0.0
        }
    }
    
    trading_bots[user_id].append(new_bot)
    
    return {"bot": new_bot, "message": "Trading bot created successfully"}

@app.put("/api/v1/bots/{bot_id}")
async def update_trading_bot(bot_id: int, bot_update: BotUpdate, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    if user_id not in trading_bots:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot = next((b for b in trading_bots[user_id] if b["id"] == bot_id), None)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    if bot_update.status:
        bot["status"] = bot_update.status
    
    if bot_update.parameters:
        bot["parameters"].update(bot_update.parameters)
    
    return {"bot": bot, "message": "Trading bot updated successfully"}

@app.delete("/api/v1/bots/{bot_id}")
async def delete_trading_bot(bot_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    if user_id not in trading_bots:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot_index = next((i for i, b in enumerate(trading_bots[user_id]) if b["id"] == bot_id), None)
    if bot_index is None:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    deleted_bot = trading_bots[user_id].pop(bot_index)
    
    return {"message": f"Trading bot '{deleted_bot['name']}' deleted successfully"}

@app.post("/api/v1/bots/{bot_id}/start")
async def start_trading_bot(bot_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    if user_id not in trading_bots:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot = next((b for b in trading_bots[user_id] if b["id"] == bot_id), None)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot["status"] = "active"
    bot["last_trade"] = datetime.utcnow().isoformat()
    
    return {"message": f"Trading bot '{bot['name']}' started successfully"}

@app.post("/api/v1/bots/{bot_id}/stop")
async def stop_trading_bot(bot_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    if user_id not in trading_bots:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot = next((b for b in trading_bots[user_id] if b["id"] == bot_id), None)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot["status"] = "stopped"
    
    return {"message": f"Trading bot '{bot['name']}' stopped successfully"}

@app.get("/api/v1/bots/{bot_id}/performance")
async def get_bot_performance(bot_id: int, current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    if user_id not in trading_bots:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    bot = next((b for b in trading_bots[user_id] if b["id"] == bot_id), None)
    if not bot:
        raise HTTPException(status_code=404, detail="Bot not found")
    
    # Generate performance history
    performance_data = []
    base_value = 1000
    
    for i in range(30):
        change = random.uniform(-0.03, 0.05)
        base_value *= (1 + change)
        
        performance_data.append({
            "date": (datetime.utcnow() - timedelta(days=29-i)).strftime("%Y-%m-%d"),
            "portfolio_value": round(base_value, 2),
            "daily_return": round(change * 100, 2),
            "cumulative_return": round(((base_value - 1000) / 1000) * 100, 2)
        })
    
    bot["performance"] = {
        "daily_return": round(random.uniform(-2, 3), 2),
        "total_return": round(random.uniform(-10, 25), 2),
        "max_drawdown": round(random.uniform(2, 15), 2),
        "sharpe_ratio": round(random.uniform(0.8, 2.5), 2),
        "profit_loss": round(random.uniform(-500, 1200), 2),
        "total_trades": random.randint(50, 500),
        "win_rate": round(random.uniform(45, 75), 2)
    }
    
    return {
        "bot": bot,
        "performance_history": performance_data,
        "trades_today": random.randint(5, 25),
        "avg_trade_duration": f"{random.randint(2, 30)} minutes"
    }

@app.get("/api/v1/bots/strategies")
async def get_bot_strategies(current_user: dict = Depends(get_current_user)):
    return {
        "strategies": [
            {
                "name": "Grid Trading",
                "key": "grid",
                "description": "Places buy and sell orders at regular intervals around current price",
                "parameters": ["grid_size", "grid_spacing", "investment_amount"],
                "risk_level": "medium",
                "best_markets": ["sideways", "volatile"]
            },
            {
                "name": "Momentum Trading",
                "key": "momentum", 
                "description": "Follows price trends and momentum indicators",
                "parameters": ["momentum_period", "entry_threshold", "exit_threshold"],
                "risk_level": "high",
                "best_markets": ["trending", "bull market"]
            },
            {
                "name": "Mean Reversion",
                "key": "mean_reversion",
                "description": "Buys when price is below average, sells when above",
                "parameters": ["ma_period", "deviation_threshold", "position_size"],
                "risk_level": "medium",
                "best_markets": ["ranging", "stable"]
            },
            {
                "name": "Arbitrage",
                "key": "arbitrage",
                "description": "Exploits price differences between markets or exchanges",
                "parameters": ["min_spread", "max_position", "execution_delay"],
                "risk_level": "low",
                "best_markets": ["any", "high volume"]
            },
            {
                "name": "Scalping",
                "key": "scalping",
                "description": "Makes many small profits from minor price changes",
                "parameters": ["tick_size", "profit_target", "stop_loss"],
                "risk_level": "high",
                "best_markets": ["liquid", "high frequency"]
            }
        ]
    }

@app.get("/api/v1/bots/backtest")
async def backtest_strategy(
    strategy: str,
    symbol: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    # Simulate backtest results
    initial_balance = 10000
    final_balance = initial_balance * random.uniform(0.8, 1.5)
    
    trades = []
    balance = initial_balance
    
    for i in range(random.randint(20, 100)):
        trade_return = random.uniform(-0.05, 0.08)
        trade_amount = balance * 0.1
        profit = trade_amount * trade_return
        balance += profit
        
        trades.append({
            "date": (datetime.utcnow() - timedelta(days=random.randint(1, 90))).strftime("%Y-%m-%d"),
            "symbol": symbol,
            "side": random.choice(["buy", "sell"]),
            "quantity": round(trade_amount / 45000, 4),
            "price": round(45000 * random.uniform(0.95, 1.05), 2),
            "profit": round(profit, 2)
        })
    
    return {
        "strategy": strategy,
        "symbol": symbol,
        "period": f"{start_date or '2024-01-01'} to {end_date or '2024-12-31'}",
        "initial_balance": initial_balance,
        "final_balance": round(final_balance, 2),
        "total_return": round(((final_balance - initial_balance) / initial_balance) * 100, 2),
        "total_trades": len(trades),
        "winning_trades": len([t for t in trades if t["profit"] > 0]),
        "win_rate": round(len([t for t in trades if t["profit"] > 0]) / len(trades) * 100, 2),
        "max_drawdown": round(random.uniform(5, 25), 2),
        "sharpe_ratio": round(random.uniform(0.5, 2.0), 2),
        "trades": trades[-10:]  # Return last 10 trades
    }

@app.post("/api/v1/risk/limits")
async def update_risk_limits(
    limits: dict,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    
    # Store user risk limits (in real app, save to database)
    user_risk_limits = {
        "max_position_size": limits.get("max_position_size", 50000),
        "max_leverage": limits.get("max_leverage", 5.0),
        "max_daily_loss": limits.get("max_daily_loss", 5000),
        "stop_loss_percentage": limits.get("stop_loss_percentage", 5.0),
        "take_profit_percentage": limits.get("take_profit_percentage", 10.0)
    }
    
    return {
        "message": "Risk limits updated successfully",
        "limits": user_risk_limits
    }

@app.get("/api/v1/notifications")
async def get_notifications(
    limit: int = 50,
    offset: int = 0,
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    # Generate sample notifications if none exist
    if not user_notifications[user_id]:
        await generate_sample_notifications(user_id)
    
    notifications = user_notifications[user_id]
    
    if unread_only:
        notifications = [n for n in notifications if not n.get("read", False)]
    
    # Sort by timestamp (newest first)
    notifications = sorted(notifications, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    # Apply pagination
    paginated_notifications = notifications[offset:offset + limit]
    
    return {
        "notifications": paginated_notifications,
        "total": len(notifications),
        "unread_count": len([n for n in user_notifications[user_id] if not n.get("read", False)])
    }

@app.post("/api/v1/notifications")
async def create_notification(
    notification: NotificationCreate,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    new_notification = {
        "id": len(user_notifications[user_id]) + 1,
        "type": notification.type,
        "title": notification.title,
        "message": notification.message,
        "priority": notification.priority,
        "channels": notification.channels,
        "timestamp": datetime.utcnow().isoformat(),
        "read": False,
        "delivered": False
    }
    
    user_notifications[user_id].append(new_notification)
    
    # Simulate notification delivery
    await deliver_notification(user_id, new_notification)
    
    return {"notification": new_notification, "message": "Notification created successfully"}

@app.patch("/api/v1/notifications/{notification_id}")
async def update_notification(
    notification_id: int,
    read: Optional[bool] = None,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    notification = next((n for n in user_notifications[user_id] if n["id"] == notification_id), None)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    if read is not None:
        notification["read"] = read
    
    return {"notification": notification, "message": "Notification updated successfully"}

@app.delete("/api/v1/notifications/{notification_id}")
async def delete_notification(
    notification_id: int,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    notification_index = next((i for i, n in enumerate(user_notifications[user_id]) if n["id"] == notification_id), None)
    if notification_index is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    
    deleted_notification = user_notifications[user_id].pop(notification_index)
    
    return {"message": f"Notification deleted successfully"}

@app.post("/api/v1/notifications/mark-all-read")
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    for notification in user_notifications[user_id]:
        notification["read"] = True
    
    return {"message": "All notifications marked as read"}

@app.get("/api/v1/notifications/settings")
async def get_notification_settings(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    return {"settings": notification_settings[user_id]}

@app.put("/api/v1/notifications/settings")
async def update_notification_settings(
    settings: NotificationSettings,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    notification_settings[user_id].update(settings.dict())
    
    return {"settings": notification_settings[user_id], "message": "Notification settings updated successfully"}

@app.get("/api/v1/notifications/alerts")
async def get_alert_rules(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    return {"alerts": alert_rules[user_id]}

@app.post("/api/v1/notifications/alerts")
async def create_alert_rule(
    alert: AlertRule,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    new_alert = {
        "id": len(alert_rules[user_id]) + 1,
        "name": alert.name,
        "symbol": alert.symbol,
        "condition": alert.condition,
        "value": alert.value,
        "enabled": alert.enabled,
        "created_at": datetime.utcnow().isoformat(),
        "triggered_count": 0,
        "last_triggered": None
    }
    
    alert_rules[user_id].append(new_alert)
    
    return {"alert": new_alert, "message": "Alert rule created successfully"}

@app.put("/api/v1/notifications/alerts/{alert_id}")
async def update_alert_rule(
    alert_id: int,
    alert: AlertRule,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    alert_rule = next((a for a in alert_rules[user_id] if a["id"] == alert_id), None)
    if not alert_rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    alert_rule.update({
        "name": alert.name,
        "symbol": alert.symbol,
        "condition": alert.condition,
        "value": alert.value,
        "enabled": alert.enabled
    })
    
    return {"alert": alert_rule, "message": "Alert rule updated successfully"}

@app.delete("/api/v1/notifications/alerts/{alert_id}")
async def delete_alert_rule(
    alert_id: int,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    alert_index = next((i for i, a in enumerate(alert_rules[user_id]) if a["id"] == alert_id), None)
    if alert_index is None:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    deleted_alert = alert_rules[user_id].pop(alert_index)
    
    return {"message": f"Alert rule '{deleted_alert['name']}' deleted successfully"}

@app.post("/api/v1/notifications/test")
async def test_notification_delivery(
    channels: List[str],
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    test_notification = {
        "id": 9999,
        "type": "system_update",
        "title": "Test Notification",
        "message": "This is a test notification to verify your notification settings.",
        "priority": "medium",
        "channels": channels,
        "timestamp": datetime.utcnow().isoformat(),
        "read": False,
        "delivered": False
    }
    
    delivery_results = await deliver_notification(user_id, test_notification)
    
    return {
        "message": "Test notification sent",
        "delivery_results": delivery_results,
        "channels_tested": channels
    }

async def deliver_notification(user_id: str, notification: dict):
    user_settings = notification_settings[user_id]
    delivery_results = {}
    
    for channel in notification["channels"]:
        if channel == "email" and user_settings["email_enabled"]:
            delivery_results["email"] = await send_email_notification(user_id, notification)
        elif channel == "sms" and user_settings["sms_enabled"]:
            delivery_results["sms"] = await send_sms_notification(user_id, notification)
        elif channel == "push" and user_settings["push_enabled"]:
            delivery_results["push"] = await send_push_notification(user_id, notification)
        elif channel == "telegram" and user_settings["telegram_enabled"]:
            delivery_results["telegram"] = await send_telegram_notification(user_id, notification)
        elif channel == "slack" and user_settings["slack_enabled"]:
            delivery_results["slack"] = await send_slack_notification(user_id, notification)
        elif channel == "webhook" and user_settings["webhook_enabled"]:
            delivery_results["webhook"] = await send_webhook_notification(user_id, notification)
    
    notification["delivered"] = True
    notification["delivery_results"] = delivery_results
    
    return delivery_results

async def send_email_notification(user_id: str, notification: dict):
    await asyncio.sleep(0.1)
    return {"status": "sent", "timestamp": datetime.utcnow().isoformat()}

async def send_sms_notification(user_id: str, notification: dict):
    await asyncio.sleep(0.1)
    return {"status": "sent", "timestamp": datetime.utcnow().isoformat()}

async def send_push_notification(user_id: str, notification: dict):
    await asyncio.sleep(0.1)
    return {"status": "sent", "timestamp": datetime.utcnow().isoformat()}

async def send_telegram_notification(user_id: str, notification: dict):
    await asyncio.sleep(0.1)
    return {"status": "sent", "timestamp": datetime.utcnow().isoformat()}

async def send_slack_notification(user_id: str, notification: dict):
    await asyncio.sleep(0.1)
    return {"status": "sent", "timestamp": datetime.utcnow().isoformat()}

async def send_webhook_notification(user_id: str, notification: dict):
    await asyncio.sleep(0.1)
    return {"status": "sent", "timestamp": datetime.utcnow().isoformat()}

async def generate_sample_notifications(user_id: str):
    sample_notifications = [
        {
            "type": "price_alert",
            "title": "BTC Price Alert",
            "message": "Bitcoin has reached $45,000 - your target price!",
            "priority": "high",
            "channels": ["email", "push"]
        },
        {
            "type": "order_filled",
            "title": "Order Executed",
            "message": "Your buy order for 0.5 BTC at $44,500 has been filled.",
            "priority": "medium",
            "channels": ["push"]
        },
        {
            "type": "risk_warning",
            "title": "Risk Alert",
            "message": "Your portfolio risk level is approaching HIGH. Consider reducing position sizes.",
            "priority": "urgent",
            "channels": ["email", "push", "sms"]
        },
        {
            "type": "bot_status",
            "title": "Trading Bot Update",
            "message": "Your Grid Trading bot has been paused due to market volatility.",
            "priority": "medium",
            "channels": ["push"]
        },
        {
            "type": "system_update",
            "title": "System Maintenance",
            "message": "Scheduled maintenance will occur tonight from 2-4 AM UTC.",
            "priority": "low",
            "channels": ["email"]
        }
    ]
    
    for i, sample in enumerate(sample_notifications):
        notification = {
            "id": i + 1,
            "type": sample["type"],
            "title": sample["title"],
            "message": sample["message"],
            "priority": sample["priority"],
            "channels": sample["channels"],
            "timestamp": (datetime.utcnow() - timedelta(hours=random.randint(1, 24))).isoformat(),
            "read": random.choice([True, False]),
            "delivered": True
        }
        
        if len(user_notifications[user_id]) < 5:
            user_notifications[user_id].append(notification)

@app.get("/api/v1/risk/alerts")
async def get_risk_alerts(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    
    # Generate sample alerts
    alerts = [
        {
            "id": 1,
            "type": "position_limit",
            "severity": "high",
            "message": "BTC position exceeds 40% of portfolio",
            "timestamp": datetime.utcnow().isoformat(),
            "resolved": False
        },
        {
            "id": 2,
            "type": "daily_loss",
            "severity": "medium", 
            "message": "Daily loss limit reached 80%",
            "timestamp": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            "resolved": False
        },
        {
            "id": 3,
            "type": "margin_call",
            "severity": "high",
            "message": "Margin requirement increased",
            "timestamp": (datetime.utcnow() - timedelta(hours=5)).isoformat(),
            "resolved": True
        }
    ]
    
    return {"alerts": alerts}

@app.get("/api/v1/kyc/status")
async def get_kyc_status(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    return {
        "status": user_kyc_status[user_id],
        "personal_info": user_personal_info[user_id],
        "documents": kyc_documents[user_id],
        "progress": calculate_kyc_progress(user_id)
    }

@app.post("/api/v1/kyc/personal-info")
async def update_personal_info(
    personal_info: PersonalInfo,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    user_personal_info[user_id] = personal_info.dict()
    
    # Update KYC status if not started
    if user_kyc_status[user_id] == "not_started":
        user_kyc_status[user_id] = "pending"
    
    return {
        "message": "Personal information updated successfully",
        "personal_info": user_personal_info[user_id]
    }

@app.post("/api/v1/kyc/documents")
async def upload_kyc_document(
    document: KYCDocumentCreate,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    # Check if document type already exists
    existing_doc = next((d for d in kyc_documents[user_id] if d["document_type"] == document.document_type), None)
    
    if existing_doc:
        # Update existing document
        existing_doc.update({
            "document_number": document.document_number,
            "document_data": document.document_data,
            "country": document.country,
            "expiry_date": document.expiry_date,
            "uploaded_at": datetime.utcnow().isoformat(),
            "status": "pending"
        })
        updated_doc = existing_doc
    else:
        # Create new document
        new_document = {
            "id": len(kyc_documents[user_id]) + 1,
            "document_type": document.document_type,
            "document_number": document.document_number,
            "document_data": document.document_data,
            "country": document.country,
            "expiry_date": document.expiry_date,
            "uploaded_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "notes": None
        }
        kyc_documents[user_id].append(new_document)
        updated_doc = new_document
    
    # Update KYC status
    if user_kyc_status[user_id] == "not_started":
        user_kyc_status[user_id] = "pending"
    
    return {
        "message": "Document uploaded successfully",
        "document": updated_doc
    }

@app.get("/api/v1/kyc/documents")
async def get_kyc_documents(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    return {"documents": kyc_documents[user_id]}

@app.delete("/api/v1/kyc/documents/{document_id}")
async def delete_kyc_document(
    document_id: int,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    document_index = next((i for i, d in enumerate(kyc_documents[user_id]) if d["id"] == document_id), None)
    if document_index is None:
        raise HTTPException(status_code=404, detail="Document not found")
    
    deleted_document = kyc_documents[user_id].pop(document_index)
    
    return {"message": f"Document deleted successfully"}

@app.post("/api/v1/kyc/submit")
async def submit_kyc_application(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    # Check if personal info is complete
    if not user_personal_info[user_id]:
        raise HTTPException(status_code=400, detail="Personal information is required")
    
    # Check if required documents are uploaded
    required_docs = ["passport", "proof_of_address", "selfie"]
    uploaded_doc_types = [d["document_type"] for d in kyc_documents[user_id]]
    
    missing_docs = [doc for doc in required_docs if doc not in uploaded_doc_types]
    if missing_docs:
        raise HTTPException(
            status_code=400, 
            detail=f"Missing required documents: {', '.join(missing_docs)}"
        )
    
    # Update KYC status to pending review
    user_kyc_status[user_id] = "pending"
    
    # In real application, this would trigger a review process
    # For demo, we'll simulate automatic approval after a delay
    
    return {
        "message": "KYC application submitted successfully",
        "status": "pending",
        "estimated_review_time": "2-3 business days"
    }

@app.get("/api/v1/kyc/requirements")
async def get_kyc_requirements(current_user: dict = Depends(get_current_user)):
    return {
        "required_documents": [
            {
                "type": "passport",
                "name": "Passport",
                "description": "Government-issued passport",
                "required": True
            },
            {
                "type": "drivers_license",
                "name": "Driver's License",
                "description": "Valid driver's license",
                "required": False
            },
            {
                "type": "national_id",
                "name": "National ID",
                "description": "Government-issued national ID card",
                "required": False
            },
            {
                "type": "proof_of_address",
                "name": "Proof of Address",
                "description": "Utility bill, bank statement, or government document",
                "required": True
            },
            {
                "type": "selfie",
                "name": "Selfie Verification",
                "description": "Photo of yourself holding your ID document",
                "required": True
            }
        ],
        "personal_info_fields": [
            "first_name", "last_name", "date_of_birth", "nationality",
            "address", "city", "postal_code", "country", "phone"
        ],
        "supported_countries": [
            "US", "UK", "DE", "FR", "CA", "AU", "JP", "SG", "NL", "CH"
        ]
    }

# Admin KYC endpoints
@app.get("/api/v1/admin/kyc/applications")
async def get_kyc_applications(current_user: dict = Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    applications = []
    for user_id in user_kyc_status:
        if user_kyc_status[user_id] != "not_started":
            applications.append({
                "user_id": user_id,
                "status": user_kyc_status[user_id],
                "personal_info": user_personal_info.get(user_id, {}),
                "documents_count": len(kyc_documents.get(user_id, [])),
                "submitted_at": datetime.utcnow().isoformat(),
                "progress": calculate_kyc_progress(user_id)
            })
    
    return {"applications": applications}

@app.put("/api/v1/admin/kyc/{user_id}")
async def update_kyc_status(
    user_id: str,
    kyc_update: KYCUpdate,
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if user_id not in user_kyc_status:
        raise HTTPException(status_code=404, detail="User not found")
    
    if kyc_update.status:
        user_kyc_status[user_id] = kyc_update.status
    
    return {
        "message": "KYC status updated successfully",
        "user_id": user_id,
        "status": user_kyc_status[user_id]
    }

@app.put("/api/v1/admin/kyc/{user_id}/documents/{document_id}")
async def update_document_status(
    user_id: str,
    document_id: int,
    status: str,
    notes: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    if user_id not in kyc_documents:
        raise HTTPException(status_code=404, detail="User not found")
    
    document = next((d for d in kyc_documents[user_id] if d["id"] == document_id), None)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    document["status"] = status
    if notes:
        document["notes"] = notes
    document["reviewed_at"] = datetime.utcnow().isoformat()
    
    return {
        "message": "Document status updated successfully",
        "document": document
    }

def calculate_kyc_progress(user_id: str) -> dict:
    progress = 0
    steps = []
    
    # Personal info step
    if user_personal_info.get(user_id):
        progress += 25
        steps.append({"name": "Personal Information", "completed": True})
    else:
        steps.append({"name": "Personal Information", "completed": False})
    
    # Document upload steps
    required_docs = ["passport", "proof_of_address", "selfie"]
    uploaded_doc_types = [d["document_type"] for d in kyc_documents.get(user_id, [])]
    
    for doc_type in required_docs:
        if doc_type in uploaded_doc_types:
            progress += 25
            steps.append({"name": f"{doc_type.replace('_', ' ').title()}", "completed": True})
        else:
            steps.append({"name": f"{doc_type.replace('_', ' ').title()}", "completed": False})
    
    return {
        "percentage": progress,
        "steps": steps,
        "completed": progress == 100
    }

@app.post("/api/v1/risk/alerts/{alert_id}/resolve")
async def resolve_alert(
    alert_id: int,
    current_user: dict = Depends(get_current_user)
):
    return {
        "message": f"Alert {alert_id} resolved successfully"
    }

@app.get("/api/v1/payments/methods")
async def get_payment_methods(current_user: dict = Depends(get_current_user)):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    # Generate sample payment methods if none exist
    if not user_payment_methods[user_id]:
        sample_methods = [
            {
                "id": 1,
                "type": "card",
                "name": "Visa ending in 1234",
                "details": {
                    "last_four": "1234",
                    "brand": "visa",
                    "expiry_month": 12,
                    "expiry_year": 2025
                },
                "is_default": True,
                "created_at": datetime.utcnow().isoformat()
            },
            {
                "id": 2,
                "type": "bank_transfer",
                "name": "Bank of America",
                "details": {
                    "account_number": "****1234",
                    "routing_number": "026009593",
                    "account_type": "checking"
                },
                "is_default": False,
                "created_at": datetime.utcnow().isoformat()
            }
        ]
        user_payment_methods[user_id] = sample_methods
    
    return {"payment_methods": user_payment_methods[user_id]}

@app.post("/api/v1/payments/methods")
async def add_payment_method(
    method: PaymentMethodCreate,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    new_method = {
        "id": len(user_payment_methods[user_id]) + 1,
        "type": method.type,
        "name": method.name,
        "details": method.details,
        "is_default": len(user_payment_methods[user_id]) == 0,
        "created_at": datetime.utcnow().isoformat()
    }
    
    user_payment_methods[user_id].append(new_method)
    
    return {"method": new_method, "message": "Payment method added successfully"}

@app.delete("/api/v1/payments/methods/{method_id}")
async def delete_payment_method(
    method_id: int,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    method_index = next((i for i, m in enumerate(user_payment_methods[user_id]) if m["id"] == method_id), None)
    if method_index is None:
        raise HTTPException(status_code=404, detail="Payment method not found")
    
    deleted_method = user_payment_methods[user_id].pop(method_index)
    
    return {"message": "Payment method deleted successfully"}

@app.post("/api/v1/payments/deposit")
async def create_deposit(
    deposit: DepositRequest,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    # Validate payment method exists
    payment_method = next((m for m in user_payment_methods[user_id] if m["type"] == deposit.payment_method), None)
    if not payment_method:
        raise HTTPException(status_code=400, detail="Payment method not found")
    
    # Create transaction
    transaction = {
        "id": len(user_transactions[user_id]) + 1,
        "type": "deposit",
        "amount": deposit.amount,
        "currency": deposit.currency,
        "payment_method": deposit.payment_method,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "transaction_id": f"DEP_{random.randint(100000, 999999)}",
        "fees": round(deposit.amount * 0.025, 2),  # 2.5% fee
        "net_amount": round(deposit.amount * 0.975, 2)
    }
    
    user_transactions[user_id].append(transaction)
    
    # Simulate processing
    await asyncio.sleep(0.1)
    
    # Update wallet balance
    if user_id in user_wallets:
        if deposit.currency in user_wallets[user_id]:
            user_wallets[user_id][deposit.currency]["available"] += transaction["net_amount"]
        else:
            user_wallets[user_id][deposit.currency] = {
                "available": transaction["net_amount"],
                "locked": 0.0
            }
    
    # Update transaction status
    transaction["status"] = "completed"
    transaction["completed_at"] = datetime.utcnow().isoformat()
    
    return {
        "transaction": transaction,
        "message": "Deposit completed successfully"
    }

@app.post("/api/v1/payments/withdraw")
async def create_withdrawal(
    withdrawal: WithdrawalRequest,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    # Check if user has sufficient balance
    if user_id not in user_wallets or withdrawal.currency not in user_wallets[user_id]:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    available_balance = user_wallets[user_id][withdrawal.currency]["available"]
    withdrawal_fee = round(withdrawal.amount * 0.01, 2)  # 1% fee
    total_amount = withdrawal.amount + withdrawal_fee
    
    if available_balance < total_amount:
        raise HTTPException(status_code=400, detail="Insufficient balance for withdrawal and fees")
    
    # Create transaction
    transaction = {
        "id": len(user_transactions[user_id]) + 1,
        "type": "withdrawal",
        "amount": withdrawal.amount,
        "currency": withdrawal.currency,
        "payment_method": withdrawal.payment_method,
        "destination": withdrawal.destination,
        "status": "processing",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "transaction_id": f"WTH_{random.randint(100000, 999999)}",
        "fees": withdrawal_fee,
        "net_amount": withdrawal.amount
    }
    
    user_transactions[user_id].append(transaction)
    
    # Update wallet balance
    user_wallets[user_id][withdrawal.currency]["available"] -= total_amount
    
    # Simulate processing delay
    await asyncio.sleep(0.2)
    
    # Update transaction status
    transaction["status"] = "completed"
    transaction["completed_at"] = datetime.utcnow().isoformat()
    
    return {
        "transaction": transaction,
        "message": "Withdrawal completed successfully"
    }

@app.get("/api/v1/payments/transactions")
async def get_transactions(
    limit: int = 50,
    offset: int = 0,
    transaction_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    # Generate sample transactions if none exist
    if not user_transactions[user_id]:
        sample_transactions = [
            {
                "id": 1,
                "type": "deposit",
                "amount": 1000.0,
                "currency": "USDT",
                "payment_method": "card",
                "status": "completed",
                "created_at": (datetime.utcnow() - timedelta(days=1)).isoformat(),
                "transaction_id": "DEP_123456",
                "fees": 25.0,
                "net_amount": 975.0
            },
            {
                "id": 2,
                "type": "withdrawal",
                "amount": 500.0,
                "currency": "USDT",
                "payment_method": "bank_transfer",
                "destination": "Bank of America ****1234",
                "status": "completed",
                "created_at": (datetime.utcnow() - timedelta(hours=12)).isoformat(),
                "transaction_id": "WTH_789012",
                "fees": 5.0,
                "net_amount": 500.0
            },
            {
                "id": 3,
                "type": "deposit",
                "amount": 2000.0,
                "currency": "USDT",
                "payment_method": "crypto",
                "status": "processing",
                "created_at": (datetime.utcnow() - timedelta(hours=2)).isoformat(),
                "transaction_id": "DEP_345678",
                "fees": 50.0,
                "net_amount": 1950.0
            }
        ]
        user_transactions[user_id] = sample_transactions
    
    transactions = user_transactions[user_id]
    
    # Filter by type if specified
    if transaction_type:
        transactions = [t for t in transactions if t["type"] == transaction_type]
    
    # Sort by created_at (newest first)
    transactions = sorted(transactions, key=lambda x: x["created_at"], reverse=True)
    
    # Apply pagination
    paginated_transactions = transactions[offset:offset + limit]
    
    return {
        "transactions": paginated_transactions,
        "total": len(transactions),
        "has_more": offset + limit < len(transactions)
    }

@app.get("/api/v1/payments/fees")
async def get_payment_fees(current_user: dict = Depends(get_current_user)):
    return {
        "deposit_fees": {
            "card": {"percentage": 2.5, "minimum": 1.0, "maximum": 50.0},
            "bank_transfer": {"percentage": 0.5, "minimum": 0.0, "maximum": 10.0},
            "crypto": {"percentage": 1.0, "minimum": 0.0, "maximum": 25.0},
            "paypal": {"percentage": 3.0, "minimum": 1.0, "maximum": 100.0}
        },
        "withdrawal_fees": {
            "card": {"percentage": 1.0, "minimum": 2.0, "maximum": 25.0},
            "bank_transfer": {"percentage": 0.5, "minimum": 5.0, "maximum": 15.0},
            "crypto": {"percentage": 0.5, "minimum": 0.0, "maximum": 10.0},
            "paypal": {"percentage": 2.0, "minimum": 2.0, "maximum": 50.0}
        }
    }

@app.get("/api/v1/payments/supported-currencies")
async def get_supported_currencies(current_user: dict = Depends(get_current_user)):
    return {
        "fiat": [
            {"code": "USD", "name": "US Dollar", "symbol": "$", "decimals": 2},
            {"code": "EUR", "name": "Euro", "symbol": "€", "decimals": 2},
            {"code": "GBP", "name": "British Pound", "symbol": "£", "decimals": 2},
            {"code": "CAD", "name": "Canadian Dollar", "symbol": "C$", "decimals": 2},
            {"code": "AUD", "name": "Australian Dollar", "symbol": "A$", "decimals": 2},
            {"code": "JPY", "name": "Japanese Yen", "symbol": "¥", "decimals": 0}
        ],
        "crypto": [
            {"code": "BTC", "name": "Bitcoin", "symbol": "₿", "decimals": 8},
            {"code": "ETH", "name": "Ethereum", "symbol": "Ξ", "decimals": 18},
            {"code": "USDT", "name": "Tether", "symbol": "₮", "decimals": 6},
            {"code": "USDC", "name": "USD Coin", "symbol": "USDC", "decimals": 6},
            {"code": "BNB", "name": "Binance Coin", "symbol": "BNB", "decimals": 18},
            {"code": "ADA", "name": "Cardano", "symbol": "ADA", "decimals": 6}
        ]
    }

@app.post("/api/v1/payments/verify")
async def verify_payment(
    transaction_id: str,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    # Find transaction
    transaction = next((t for t in user_transactions[user_id] if t["transaction_id"] == transaction_id), None)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
    
    # Simulate verification process
    await asyncio.sleep(0.5)
    
    verification_result = {
        "transaction_id": transaction_id,
        "status": transaction["status"],
        "verified": True,
        "verification_time": datetime.utcnow().isoformat(),
        "details": {
            "amount": transaction["amount"],
            "currency": transaction["currency"],
            "fees": transaction["fees"],
            "net_amount": transaction["net_amount"]
        }
    }
    
    return verification_result

@app.get("/api/v1/payments/history")
async def get_payment_history(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    init_user_data(user_id)
    
    # Generate summary statistics
    transactions = user_transactions[user_id]
    
    deposits = [t for t in transactions if t["type"] == "deposit" and t["status"] == "completed"]
    withdrawals = [t for t in transactions if t["type"] == "withdrawal" and t["status"] == "completed"]
    
    total_deposited = sum(t["net_amount"] for t in deposits)
    total_withdrawn = sum(t["net_amount"] for t in withdrawals)
    total_fees = sum(t["fees"] for t in transactions if t["status"] == "completed")
    
    return {
        "summary": {
            "total_deposited": round(total_deposited, 2),
            "total_withdrawn": round(total_withdrawn, 2),
            "net_flow": round(total_deposited - total_withdrawn, 2),
            "total_fees": round(total_fees, 2),
            "transaction_count": len(transactions)
        },
        "monthly_stats": [
            {
                "month": "2024-01",
                "deposits": round(random.uniform(1000, 5000), 2),
                "withdrawals": round(random.uniform(500, 2000), 2),
                "fees": round(random.uniform(10, 100), 2)
            },
            {
                "month": "2024-02",
                "deposits": round(random.uniform(1500, 6000), 2),
                "withdrawals": round(random.uniform(800, 3000), 2),
                "fees": round(random.uniform(15, 150), 2)
            },
            {
                "month": "2024-03",
                "deposits": round(random.uniform(2000, 7000), 2),
                "withdrawals": round(random.uniform(1000, 4000), 2),
                "fees": round(random.uniform(20, 200), 2)
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)