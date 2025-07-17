from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Boolean, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from enum import Enum as PyEnum


class OrderType(PyEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderSide(PyEnum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(PyEnum):
    PENDING = "pending"
    PARTIAL_FILLED = "partial_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    
    order_type = Column(Enum(OrderType), nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    
    quantity = Column(Numeric(18, 8), nullable=False)
    price = Column(Numeric(18, 8))
    stop_price = Column(Numeric(18, 8))
    
    filled_quantity = Column(Numeric(18, 8), default=0)
    remaining_quantity = Column(Numeric(18, 8))
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="orders")
    trades = relationship("Trade", back_populates="order")


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    symbol = Column(String(20), nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    
    quantity = Column(Numeric(18, 8), nullable=False)
    price = Column(Numeric(18, 8), nullable=False)
    
    fee = Column(Numeric(18, 8), default=0)
    fee_currency = Column(String(10))
    
    executed_at = Column(DateTime(timezone=True), server_default=func.now())
    
    order = relationship("Order", back_populates="trades")
    user = relationship("User", back_populates="trades")


class MarketData(Base):
    __tablename__ = "market_data"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    
    price = Column(Numeric(18, 8), nullable=False)
    volume = Column(Numeric(18, 8), nullable=False)
    
    bid_price = Column(Numeric(18, 8))
    ask_price = Column(Numeric(18, 8))
    
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)