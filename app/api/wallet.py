from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from decimal import Decimal
from typing import Dict, List
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.services.wallet_service import wallet_service

router = APIRouter(prefix="/wallet", tags=["wallet"])


class DepositRequest(BaseModel):
    currency: str
    amount: Decimal


class WithdrawalRequest(BaseModel):
    currency: str
    amount: Decimal


class BalanceResponse(BaseModel):
    balances: Dict[str, Dict]


class TransactionResponse(BaseModel):
    id: int
    type: str
    amount: str
    currency: str
    status: str
    created_at: str


@router.get("/balances", response_model=BalanceResponse)
async def get_balances(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    balances = await wallet_service.get_user_balances(current_user.id, db)
    return BalanceResponse(balances=balances)


@router.post("/deposit")
async def deposit(
    deposit_request: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        success = await wallet_service.simulate_deposit(
            current_user.id,
            deposit_request.currency,
            deposit_request.amount,
            db
        )
        
        if success:
            return {"message": "Deposit successful"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Deposit failed"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/withdraw")
async def withdraw(
    withdrawal_request: WithdrawalRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    try:
        success = await wallet_service.simulate_withdrawal(
            current_user.id,
            withdrawal_request.currency,
            withdrawal_request.amount,
            db
        )
        
        if success:
            return {"message": "Withdrawal successful"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Withdrawal failed"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transaction_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    transactions = await wallet_service.get_transaction_history(current_user.id, db)
    
    return [
        TransactionResponse(
            id=tx["id"],
            type=tx["type"],
            amount=tx["amount"],
            currency=tx["currency"],
            status=tx["status"],
            created_at=tx["created_at"]
        )
        for tx in transactions
    ]