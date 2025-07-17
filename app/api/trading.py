from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional
from app.core.database import get_db
from app.api.auth import get_current_user
from app.models.user import User
from app.models.trading import Order, Trade, OrderType, OrderSide, OrderStatus
from app.services.trading_engine import trading_engine

router = APIRouter(prefix="/trading", tags=["trading"])


class OrderCreate(BaseModel):
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: Decimal
    price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None


class OrderResponse(BaseModel):
    id: int
    symbol: str
    order_type: str
    side: str
    status: str
    quantity: Decimal
    price: Optional[Decimal]
    filled_quantity: Decimal
    remaining_quantity: Decimal
    created_at: str


class TradeResponse(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    fee: Decimal
    executed_at: str


class OrderBookResponse(BaseModel):
    symbol: str
    bids: List[dict]
    asks: List[dict]
    best_bid: float
    best_ask: float


@router.post("/orders", response_model=OrderResponse)
async def place_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if order_data.order_type in [OrderType.LIMIT, OrderType.STOP_LOSS, OrderType.TAKE_PROFIT]:
        if order_data.price is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Price is required for limit orders"
            )
    
    order = Order(
        user_id=current_user.id,
        symbol=order_data.symbol,
        order_type=order_data.order_type,
        side=order_data.side,
        quantity=order_data.quantity,
        price=order_data.price,
        stop_price=order_data.stop_price,
        remaining_quantity=order_data.quantity
    )
    
    db.add(order)
    await db.commit()
    await db.refresh(order)
    
    try:
        trades = await trading_engine.place_order(order, db)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Order processing failed: {str(e)}"
        )
    
    return OrderResponse(
        id=order.id,
        symbol=order.symbol,
        order_type=order.order_type.value,
        side=order.side.value,
        status=order.status.value,
        quantity=order.quantity,
        price=order.price,
        filled_quantity=order.filled_quantity,
        remaining_quantity=order.remaining_quantity,
        created_at=order.created_at.isoformat()
    )


@router.get("/orders", response_model=List[OrderResponse])
async def get_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(desc(Order.created_at))
        .limit(100)
    )
    orders = result.scalars().all()
    
    return [
        OrderResponse(
            id=order.id,
            symbol=order.symbol,
            order_type=order.order_type.value,
            side=order.side.value,
            status=order.status.value,
            quantity=order.quantity,
            price=order.price,
            filled_quantity=order.filled_quantity,
            remaining_quantity=order.remaining_quantity,
            created_at=order.created_at.isoformat()
        )
        for order in orders
    ]


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Order).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel this order"
        )
    
    success = await trading_engine.cancel_order(order_id, db)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to cancel order"
        )
    
    return {"message": "Order cancelled successfully"}


@router.get("/trades", response_model=List[TradeResponse])
async def get_trades(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Trade)
        .where(Trade.user_id == current_user.id)
        .order_by(desc(Trade.executed_at))
        .limit(100)
    )
    trades = result.scalars().all()
    
    return [
        TradeResponse(
            id=trade.id,
            symbol=trade.symbol,
            side=trade.side.value,
            quantity=trade.quantity,
            price=trade.price,
            fee=trade.fee,
            executed_at=trade.executed_at.isoformat()
        )
        for trade in trades
    ]


@router.get("/orderbook/{symbol}", response_model=OrderBookResponse)
async def get_orderbook(symbol: str):
    orderbook = trading_engine.get_order_book_snapshot(symbol)
    
    return OrderBookResponse(
        symbol=orderbook["symbol"],
        bids=orderbook["bids"],
        asks=orderbook["asks"],
        best_bid=orderbook["best_bid"],
        best_ask=orderbook["best_ask"]
    )