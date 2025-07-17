# SecureTradeAPI

A comprehensive cryptocurrency trading platform built with FastAPI, featuring advanced trading capabilities, real-time market data, and institutional-grade security.

## Features

### Core Trading System
- Real-time order matching engine
- Multi-symbol trading support (BTC, ETH, ADA, DOT)
- Market and limit order types
- WebSocket-based real-time price feeds
- Order book visualization

### Authentication & Security
- JWT-based authentication
- Two-factor authentication (2FA) with TOTP
- Role-based access control
- Secure password hashing
- Session management

### Advanced Analytics
- Portfolio performance tracking
- Risk assessment and management
- Trading statistics and metrics
- Real-time P&L calculations
- Asset allocation analysis

### Trading Automation
- Multiple trading strategies (SMA, RSI, MACD, Bollinger Bands)
- Backtesting capabilities
- Automated trading bots
- Strategy performance monitoring

### Compliance & Verification
- Complete KYC workflow
- Document upload and verification
- Identity verification process
- Compliance monitoring

### Payment System
- Multiple payment methods (cards, bank transfers, crypto, PayPal)
- Deposit and withdrawal processing
- Transaction history
- Fee calculation and management

### Administrative Tools
- Admin dashboard with user management
- Platform statistics and analytics
- KYC approval workflow
- User role management

### Notification System
- Multi-channel notifications (email, SMS, push)
- Price alerts and trading notifications
- Customizable alert rules
- Real-time notification delivery

## Technical Stack

### Backend
- **Framework**: FastAPI (Python 3.8+)
- **Database**: PostgreSQL with SQLAlchemy 2.0
- **Cache**: Redis for session management and real-time data
- **Authentication**: JWT with 2FA support
- **WebSockets**: Real-time communication
- **Async Support**: Full async/await implementation

### Frontend
- **Technology**: Vanilla JavaScript with modern ES6+
- **Styling**: CSS3 with responsive design
- **Charts**: LightweightCharts for trading charts
- **Real-time**: WebSocket connections for live updates

## Installation

### Prerequisites
- Python 3.8 or higher
- PostgreSQL 12 or higher
- Redis 6 or higher

### Setup

1. Clone the repository:
```bash
git clone https://github.com/RuslanTiahniienko-Pet-Project/Backend-Python.git
cd Backend-Python
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
DATABASE_URL=postgresql://user:password@localhost/securetradeapi
REDIS_URL=redis://localhost:6379
JWT_SECRET_KEY=your-secret-key
```

4. Run the application:
```bash
python app/advanced_demo.py
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/2fa/setup` - Setup 2FA
- `POST /api/v1/auth/2fa/verify` - Verify 2FA token
- `GET /api/v1/auth/profile` - Get user profile

### Trading
- `POST /api/v1/trading/orders` - Place order
- `GET /api/v1/trading/orders` - Get user orders
- `DELETE /api/v1/trading/orders/{order_id}` - Cancel order
- `GET /api/v1/trading/positions` - Get positions
- `GET /api/v1/trading/history` - Get trading history

### Market Data
- `GET /api/v1/market/symbols` - Get available symbols
- `GET /api/v1/market/ticker/{symbol}` - Get symbol ticker
- `GET /api/v1/market/orderbook/{symbol}` - Get order book
- `GET /api/v1/market/history/{symbol}` - Get price history

### Portfolio
- `GET /api/v1/portfolio/summary` - Get portfolio summary
- `GET /api/v1/portfolio/performance` - Get performance metrics
- `GET /api/v1/portfolio/positions` - Get current positions
- `GET /api/v1/portfolio/history` - Get portfolio history

### Risk Management
- `GET /api/v1/risk/assessment` - Get risk assessment
- `POST /api/v1/risk/limits` - Set risk limits
- `GET /api/v1/risk/alerts` - Get risk alerts
- `POST /api/v1/risk/alerts` - Create risk alert

### Trading Bots
- `GET /api/v1/bots` - Get user bots
- `POST /api/v1/bots` - Create new bot
- `PUT /api/v1/bots/{bot_id}` - Update bot
- `DELETE /api/v1/bots/{bot_id}` - Delete bot
- `POST /api/v1/bots/{bot_id}/start` - Start bot
- `POST /api/v1/bots/{bot_id}/stop` - Stop bot

### KYC
- `GET /api/v1/kyc/status` - Get KYC status
- `POST /api/v1/kyc/personal-info` - Submit personal information
- `POST /api/v1/kyc/documents` - Upload document
- `DELETE /api/v1/kyc/documents/{doc_id}` - Delete document
- `POST /api/v1/kyc/submit` - Submit KYC application

### Payments
- `GET /api/v1/payments/methods` - Get payment methods
- `POST /api/v1/payments/methods` - Add payment method
- `POST /api/v1/payments/deposit` - Process deposit
- `POST /api/v1/payments/withdraw` - Process withdrawal
- `GET /api/v1/payments/transactions` - Get transaction history

### Notifications
- `GET /api/v1/notifications` - Get notifications
- `POST /api/v1/notifications/mark-read` - Mark notifications as read
- `GET /api/v1/notifications/settings` - Get notification settings
- `PUT /api/v1/notifications/settings` - Update notification settings

### Admin
- `GET /api/v1/admin/stats` - Get platform statistics
- `GET /api/v1/admin/users` - Get users list
- `PUT /api/v1/admin/users/{user_id}` - Update user
- `POST /api/v1/admin/users/{user_id}/suspend` - Suspend user
- `GET /api/v1/admin/trades` - Get all trades

### Wallet
- `GET /api/v1/wallet/balances` - Get wallet balances
- `POST /api/v1/wallet/transfer` - Internal transfer
- `GET /api/v1/wallet/transactions` - Get wallet transactions

## WebSocket Endpoints

### Real-time Data
- `ws://localhost:8002/ws/prices/{symbol}` - Live price updates
- `ws://localhost:8002/ws/orderbook/{symbol}` - Order book updates
- `ws://localhost:8002/ws/trades/{symbol}` - Live trades
- `ws://localhost:8002/ws/notifications` - Real-time notifications

## Database Schema

### Users
- User authentication and profile information
- Role-based access control
- 2FA settings and backup codes

### Trading
- Orders, trades, and positions
- Symbol definitions and market data
- Order book and price history

### Portfolio
- Balance tracking and performance metrics
- Position management and P&L calculations

### Risk Management
- Risk assessments and limits
- Alert configurations and notifications

### KYC
- Personal information and document storage
- Verification status and compliance tracking

### Payments
- Payment methods and transaction history
- Deposit and withdrawal processing

### Notifications
- Notification queue and delivery status
- User preferences and settings

## Security Features

### Authentication
- JWT tokens with expiration
- Secure password hashing with bcrypt
- Two-factor authentication with TOTP
- Session management with Redis

### Data Protection
- Input validation and sanitization
- SQL injection prevention
- XSS protection
- CSRF protection

### API Security
- Rate limiting
- Request validation
- Error handling
- Audit logging

## Performance Optimizations

### Database
- Optimized queries with proper indexing
- Connection pooling
- Async database operations

### Caching
- Redis caching for frequently accessed data
- Session caching
- Real-time data caching

### Real-time Updates
- WebSocket connections for live data
- Efficient message broadcasting
- Connection management

## Development

### Running Tests
```bash
pytest tests/
```

### Code Quality
- Type hints throughout codebase
- Comprehensive error handling
- Structured logging
- API documentation with OpenAPI

### Development Server
```bash
uvicorn app.advanced_demo:app --reload --port 8002
```

## Production Deployment

### Docker Support
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.advanced_demo:app", "--host", "0.0.0.0", "--port", "8002"]
```

### Environment Configuration
- Database connection pooling
- Redis clustering support
- Load balancing configuration
- SSL/TLS termination

### Monitoring
- Health check endpoints
- Performance metrics
- Error tracking
- Audit logging

## License

This project is licensed under the MIT License.