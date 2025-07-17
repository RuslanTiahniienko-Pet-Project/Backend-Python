from decimal import Decimal
from typing import Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.wallet import Wallet, Transaction
from app.models.user import User
from fastapi import HTTPException, status
import asyncio


class WalletService:
    def __init__(self):
        self.balance_locks = {}
    
    async def get_user_balances(self, user_id: int, db: AsyncSession) -> Dict[str, Dict]:
        result = await db.execute(
            select(Wallet).where(Wallet.user_id == user_id)
        )
        wallets = result.scalars().all()
        
        balances = {}
        for wallet in wallets:
            balances[wallet.currency] = {
                "available": str(wallet.available_balance),
                "locked": str(wallet.locked_balance),
                "total": str(wallet.total_balance)
            }
        
        return balances
    
    async def create_wallet(self, user_id: int, currency: str, db: AsyncSession) -> Wallet:
        result = await db.execute(
            select(Wallet).where(
                Wallet.user_id == user_id,
                Wallet.currency == currency
            )
        )
        
        existing_wallet = result.scalar_one_or_none()
        if existing_wallet:
            return existing_wallet
        
        wallet = Wallet(
            user_id=user_id,
            currency=currency,
            available_balance=Decimal("0"),
            locked_balance=Decimal("0")
        )
        
        db.add(wallet)
        await db.commit()
        await db.refresh(wallet)
        
        return wallet
    
    async def get_wallet(self, user_id: int, currency: str, db: AsyncSession) -> Optional[Wallet]:
        result = await db.execute(
            select(Wallet).where(
                Wallet.user_id == user_id,
                Wallet.currency == currency
            )
        )
        return result.scalar_one_or_none()
    
    async def update_balance(self, user_id: int, currency: str, amount: Decimal, 
                           transaction_type: str, db: AsyncSession) -> bool:
        wallet_key = f"{user_id}_{currency}"
        
        if wallet_key not in self.balance_locks:
            self.balance_locks[wallet_key] = asyncio.Lock()
        
        async with self.balance_locks[wallet_key]:
            wallet = await self.get_wallet(user_id, currency, db)
            
            if not wallet:
                wallet = await self.create_wallet(user_id, currency, db)
            
            if transaction_type == "deposit":
                wallet.available_balance += amount
            elif transaction_type == "withdrawal":
                if wallet.available_balance < amount:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Insufficient balance"
                    )
                wallet.available_balance -= amount
            elif transaction_type == "lock":
                if wallet.available_balance < amount:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Insufficient balance to lock"
                    )
                wallet.available_balance -= amount
                wallet.locked_balance += amount
            elif transaction_type == "unlock":
                if wallet.locked_balance < amount:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Insufficient locked balance"
                    )
                wallet.locked_balance -= amount
                wallet.available_balance += amount
            
            await db.commit()
            await db.refresh(wallet)
            
            transaction = Transaction(
                user_id=user_id,
                wallet_id=wallet.id,
                type=transaction_type,
                amount=amount,
                currency=currency,
                status="completed"
            )
            
            db.add(transaction)
            await db.commit()
            
            return True
    
    async def lock_balance(self, user_id: int, currency: str, amount: Decimal, db: AsyncSession) -> bool:
        return await self.update_balance(user_id, currency, amount, "lock", db)
    
    async def unlock_balance(self, user_id: int, currency: str, amount: Decimal, db: AsyncSession) -> bool:
        return await self.update_balance(user_id, currency, amount, "unlock", db)
    
    async def process_trade_settlement(self, user_id: int, symbol: str, side: str, 
                                     quantity: Decimal, price: Decimal, fee: Decimal, 
                                     db: AsyncSession) -> bool:
        base_currency = symbol[:3]
        quote_currency = symbol[3:]
        
        if side == "buy":
            total_cost = quantity * price + fee
            
            await self.update_balance(user_id, quote_currency, total_cost, "withdrawal", db)
            await self.update_balance(user_id, base_currency, quantity, "deposit", db)
            
        else:
            
            await self.update_balance(user_id, base_currency, quantity, "withdrawal", db)
            
            proceeds = quantity * price - fee
            await self.update_balance(user_id, quote_currency, proceeds, "deposit", db)
        
        return True
    
    async def get_transaction_history(self, user_id: int, db: AsyncSession, 
                                    limit: int = 100) -> list:
        result = await db.execute(
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .order_by(Transaction.created_at.desc())
            .limit(limit)
        )
        
        transactions = result.scalars().all()
        
        return [
            {
                "id": tx.id,
                "type": tx.type,
                "amount": str(tx.amount),
                "currency": tx.currency,
                "status": tx.status,
                "created_at": tx.created_at.isoformat()
            }
            for tx in transactions
        ]
    
    async def simulate_deposit(self, user_id: int, currency: str, amount: Decimal, db: AsyncSession) -> bool:
        return await self.update_balance(user_id, currency, amount, "deposit", db)
    
    async def simulate_withdrawal(self, user_id: int, currency: str, amount: Decimal, db: AsyncSession) -> bool:
        return await self.update_balance(user_id, currency, amount, "withdrawal", db)


wallet_service = WalletService()