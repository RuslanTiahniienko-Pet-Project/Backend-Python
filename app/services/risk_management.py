from decimal import Decimal
from typing import Dict, Optional
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.trading import Order, Trade, OrderSide
from app.models.user import User
from app.models.wallet import Wallet
from app.services.wallet_service import wallet_service
import asyncio
from datetime import datetime, timedelta


@dataclass
class RiskResult:
    approved: bool
    reason: str = ""
    risk_score: float = 0.0


class RiskManagementService:
    def __init__(self):
        self.position_limits = {
            "BTCUSDT": {"max_position": Decimal("10"), "max_order_size": Decimal("1")},
            "ETHUSDT": {"max_position": Decimal("100"), "max_order_size": Decimal("10")},
            "ADAUSDT": {"max_position": Decimal("10000"), "max_order_size": Decimal("1000")},
            "DOTUSDT": {"max_position": Decimal("1000"), "max_order_size": Decimal("100")}
        }
        
        self.daily_limits = {
            "max_daily_volume": Decimal("100000"),
            "max_daily_orders": 1000
        }
    
    async def validate_order(self, order: Order, user: User, db: AsyncSession) -> RiskResult:
        risk_checks = [
            self.check_position_limits(order, user, db),
            self.check_balance_requirements(order, user, db),
            self.check_daily_limits(order, user, db),
            self.check_order_size_limits(order, user, db),
            self.check_price_deviation(order, db)
        ]
        
        for check in risk_checks:
            result = await check
            if not result.approved:
                return result
        
        return RiskResult(approved=True, reason="All checks passed")
    
    async def check_position_limits(self, order: Order, user: User, db: AsyncSession) -> RiskResult:
        if order.symbol not in self.position_limits:
            return RiskResult(approved=False, reason="Symbol not supported")
        
        limits = self.position_limits[order.symbol]
        
        result = await db.execute(
            select(func.sum(Trade.quantity * 
                          func.case(
                              (Trade.side == OrderSide.BUY, 1),
                              (Trade.side == OrderSide.SELL, -1)
                          )))
            .where(Trade.user_id == user.id, Trade.symbol == order.symbol)
        )
        
        current_position = result.scalar() or Decimal("0")
        
        if order.side == OrderSide.BUY:
            new_position = current_position + order.quantity
        else:
            new_position = current_position - order.quantity
        
        if abs(new_position) > limits["max_position"]:
            return RiskResult(
                approved=False,
                reason=f"Position limit exceeded. Max: {limits['max_position']}"
            )
        
        return RiskResult(approved=True)
    
    async def check_balance_requirements(self, order: Order, user: User, db: AsyncSession) -> RiskResult:
        if order.side == OrderSide.BUY:
            quote_currency = order.symbol[3:]
            required_balance = order.quantity * (order.price or Decimal("0"))
            
            wallet = await wallet_service.get_wallet(user.id, quote_currency, db)
            
            if not wallet or wallet.available_balance < required_balance:
                return RiskResult(
                    approved=False,
                    reason=f"Insufficient {quote_currency} balance"
                )
        else:
            base_currency = order.symbol[:3]
            
            wallet = await wallet_service.get_wallet(user.id, base_currency, db)
            
            if not wallet or wallet.available_balance < order.quantity:
                return RiskResult(
                    approved=False,
                    reason=f"Insufficient {base_currency} balance"
                )
        
        return RiskResult(approved=True)
    
    async def check_daily_limits(self, order: Order, user: User, db: AsyncSession) -> RiskResult:
        today = datetime.utcnow().date()
        
        result = await db.execute(
            select(func.count(Order.id))
            .where(
                Order.user_id == user.id,
                func.date(Order.created_at) == today
            )
        )
        
        daily_orders = result.scalar() or 0
        
        if daily_orders >= self.daily_limits["max_daily_orders"]:
            return RiskResult(
                approved=False,
                reason="Daily order limit exceeded"
            )
        
        result = await db.execute(
            select(func.sum(Trade.quantity * Trade.price))
            .where(
                Trade.user_id == user.id,
                func.date(Trade.executed_at) == today
            )
        )
        
        daily_volume = result.scalar() or Decimal("0")
        
        estimated_trade_volume = order.quantity * (order.price or Decimal("50000"))
        
        if daily_volume + estimated_trade_volume > self.daily_limits["max_daily_volume"]:
            return RiskResult(
                approved=False,
                reason="Daily volume limit exceeded"
            )
        
        return RiskResult(approved=True)
    
    async def check_order_size_limits(self, order: Order, user: User, db: AsyncSession) -> RiskResult:
        if order.symbol not in self.position_limits:
            return RiskResult(approved=False, reason="Symbol not supported")
        
        limits = self.position_limits[order.symbol]
        
        if order.quantity > limits["max_order_size"]:
            return RiskResult(
                approved=False,
                reason=f"Order size exceeds limit. Max: {limits['max_order_size']}"
            )
        
        return RiskResult(approved=True)
    
    async def check_price_deviation(self, order: Order, db: AsyncSession) -> RiskResult:
        from app.services.market_data import market_data_service
        
        if order.order_type.value == "market":
            return RiskResult(approved=True)
        
        ticker = await market_data_service.get_ticker(order.symbol)
        
        if not ticker:
            return RiskResult(approved=False, reason="Unable to get market price")
        
        market_price = Decimal(ticker["price"])
        
        if order.price:
            deviation = abs(order.price - market_price) / market_price
            
            if deviation > Decimal("0.1"):
                return RiskResult(
                    approved=False,
                    reason="Price deviates too much from market price"
                )
        
        return RiskResult(approved=True)
    
    async def calculate_risk_score(self, user: User, db: AsyncSession) -> float:
        score = 0.0
        
        result = await db.execute(
            select(func.count(Trade.id))
            .where(
                Trade.user_id == user.id,
                Trade.executed_at >= datetime.utcnow() - timedelta(days=30)
            )
        )
        
        monthly_trades = result.scalar() or 0
        
        if monthly_trades > 1000:
            score += 0.3
        elif monthly_trades > 500:
            score += 0.2
        elif monthly_trades > 100:
            score += 0.1
        
        balances = await wallet_service.get_user_balances(user.id, db)
        total_value = sum(
            Decimal(balance["total"]) for balance in balances.values()
        )
        
        if total_value > Decimal("100000"):
            score += 0.1
        elif total_value > Decimal("10000"):
            score += 0.05
        
        if user.kyc_status.value != "approved":
            score += 0.4
        
        if not user.is_2fa_enabled:
            score += 0.2
        
        return min(score, 1.0)
    
    async def get_user_risk_profile(self, user: User, db: AsyncSession) -> Dict:
        risk_score = await self.calculate_risk_score(user, db)
        
        if risk_score < 0.3:
            risk_level = "LOW"
        elif risk_score < 0.6:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"
        
        return {
            "user_id": user.id,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "kyc_status": user.kyc_status.value,
            "two_fa_enabled": user.is_2fa_enabled,
            "account_age_days": (datetime.utcnow() - user.created_at).days
        }


risk_management_service = RiskManagementService()