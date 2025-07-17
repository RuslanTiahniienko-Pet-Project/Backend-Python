from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, Numeric
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from enum import Enum as PyEnum


class UserStatus(PyEnum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"


class KYCStatus(PyEnum):
    NOT_STARTED = "not_started"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    
    status = Column(Enum(UserStatus), default=UserStatus.PENDING)
    kyc_status = Column(Enum(KYCStatus), default=KYCStatus.NOT_STARTED)
    
    is_active = Column(Boolean, default=True)
    is_2fa_enabled = Column(Boolean, default=False)
    
    daily_withdrawal_limit = Column(Numeric(18, 8), default=10000)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    wallets = relationship("Wallet", back_populates="user")
    orders = relationship("Order", back_populates="user")
    trades = relationship("Trade", back_populates="user")