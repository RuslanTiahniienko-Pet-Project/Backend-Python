from decimal import Decimal
from typing import List, Optional, Dict
from dataclasses import dataclass
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.trading import Order, Trade, OrderStatus, OrderSide
from app.models.wallet import Wallet
from app.models.user import User
import asyncio
import heapq
from collections import defaultdict


@dataclass
class OrderMatch:
    buy_order: Order
    sell_order: Order
    quantity: Decimal
    price: Decimal


@dataclass
class TradeResult:
    trade_id: int
    order_id: int
    symbol: str
    side: OrderSide
    quantity: Decimal
    price: Decimal
    fee: Decimal


class OrderBook:
    def __init__(self):
        self.buy_orders = []
        self.sell_orders = []
        self.order_map: Dict[int, Order] = {}
    
    def add_order(self, order: Order):
        self.order_map[order.id] = order
        
        if order.side == OrderSide.BUY:
            heapq.heappush(self.buy_orders, (-order.price, order.created_at, order))
        else:
            heapq.heappush(self.sell_orders, (order.price, order.created_at, order))
    
    def remove_order(self, order_id: int):
        if order_id in self.order_map:
            del self.order_map[order_id]
    
    def get_best_bid(self) -> Optional[Decimal]:
        if self.buy_orders:
            return -self.buy_orders[0][0]
        return None
    
    def get_best_ask(self) -> Optional[Decimal]:
        if self.sell_orders:
            return self.sell_orders[0][0]
        return None


class TradingEngine:
    def __init__(self):
        self.order_books: Dict[str, OrderBook] = defaultdict(OrderBook)
        self.trading_lock = asyncio.Lock()
    
    async def place_order(self, order: Order, db: AsyncSession) -> List[TradeResult]:
        async with self.trading_lock:
            order_book = self.order_books[order.symbol]
            
            if order.order_type.value == "market":
                return await self.process_market_order(order, order_book, db)
            else:
                return await self.process_limit_order(order, order_book, db)
    
    async def process_market_order(self, order: Order, order_book: OrderBook, db: AsyncSession) -> List[TradeResult]:
        trades = []
        remaining_quantity = order.quantity
        
        if order.side == OrderSide.BUY:
            while remaining_quantity > 0 and order_book.sell_orders:
                best_ask_price, _, matching_order = heapq.heappop(order_book.sell_orders)
                
                if matching_order.id not in order_book.order_map:
                    continue
                
                trade_quantity = min(remaining_quantity, matching_order.remaining_quantity)
                trade_price = best_ask_price
                
                trade = await self.execute_trade(order, matching_order, trade_quantity, trade_price, db)
                trades.append(trade)
                
                remaining_quantity -= trade_quantity
                
                if matching_order.remaining_quantity == 0:
                    await self.update_order_status(matching_order, OrderStatus.FILLED, db)
                    order_book.remove_order(matching_order.id)
        
        else:
            while remaining_quantity > 0 and order_book.buy_orders:
                neg_best_bid_price, _, matching_order = heapq.heappop(order_book.buy_orders)
                best_bid_price = -neg_best_bid_price
                
                if matching_order.id not in order_book.order_map:
                    continue
                
                trade_quantity = min(remaining_quantity, matching_order.remaining_quantity)
                trade_price = best_bid_price
                
                trade = await self.execute_trade(order, matching_order, trade_quantity, trade_price, db)
                trades.append(trade)
                
                remaining_quantity -= trade_quantity
                
                if matching_order.remaining_quantity == 0:
                    await self.update_order_status(matching_order, OrderStatus.FILLED, db)
                    order_book.remove_order(matching_order.id)
        
        if remaining_quantity == 0:
            await self.update_order_status(order, OrderStatus.FILLED, db)
        else:
            await self.update_order_status(order, OrderStatus.PARTIAL_FILLED, db)
        
        return trades
    
    async def process_limit_order(self, order: Order, order_book: OrderBook, db: AsyncSession) -> List[TradeResult]:
        trades = []
        remaining_quantity = order.quantity
        
        if order.side == OrderSide.BUY:
            while remaining_quantity > 0 and order_book.sell_orders:
                best_ask_price, _, matching_order = order_book.sell_orders[0]
                
                if best_ask_price > order.price:
                    break
                
                heapq.heappop(order_book.sell_orders)
                
                if matching_order.id not in order_book.order_map:
                    continue
                
                trade_quantity = min(remaining_quantity, matching_order.remaining_quantity)
                trade_price = best_ask_price
                
                trade = await self.execute_trade(order, matching_order, trade_quantity, trade_price, db)
                trades.append(trade)
                
                remaining_quantity -= trade_quantity
                
                if matching_order.remaining_quantity == 0:
                    await self.update_order_status(matching_order, OrderStatus.FILLED, db)
                    order_book.remove_order(matching_order.id)
        
        else:
            while remaining_quantity > 0 and order_book.buy_orders:
                neg_best_bid_price, _, matching_order = order_book.buy_orders[0]
                best_bid_price = -neg_best_bid_price
                
                if best_bid_price < order.price:
                    break
                
                heapq.heappop(order_book.buy_orders)
                
                if matching_order.id not in order_book.order_map:
                    continue
                
                trade_quantity = min(remaining_quantity, matching_order.remaining_quantity)
                trade_price = best_bid_price
                
                trade = await self.execute_trade(order, matching_order, trade_quantity, trade_price, db)
                trades.append(trade)
                
                remaining_quantity -= trade_quantity
                
                if matching_order.remaining_quantity == 0:
                    await self.update_order_status(matching_order, OrderStatus.FILLED, db)
                    order_book.remove_order(matching_order.id)
        
        if remaining_quantity > 0:
            order.remaining_quantity = remaining_quantity
            order_book.add_order(order)
            await self.update_order_status(order, OrderStatus.PENDING, db)
        
        if remaining_quantity == 0:
            await self.update_order_status(order, OrderStatus.FILLED, db)
        elif remaining_quantity < order.quantity:
            await self.update_order_status(order, OrderStatus.PARTIAL_FILLED, db)
        
        return trades
    
    async def execute_trade(self, order1: Order, order2: Order, quantity: Decimal, price: Decimal, db: AsyncSession) -> TradeResult:
        fee = quantity * price * Decimal("0.001")
        
        trade = Trade(
            order_id=order1.id,
            user_id=order1.user_id,
            symbol=order1.symbol,
            side=order1.side,
            quantity=quantity,
            price=price,
            fee=fee,
            fee_currency="USDT"
        )
        
        db.add(trade)
        await db.commit()
        await db.refresh(trade)
        
        order1.filled_quantity += quantity
        order1.remaining_quantity -= quantity
        
        order2.filled_quantity += quantity
        order2.remaining_quantity -= quantity
        
        await db.commit()
        
        return TradeResult(
            trade_id=trade.id,
            order_id=order1.id,
            symbol=order1.symbol,
            side=order1.side,
            quantity=quantity,
            price=price,
            fee=fee
        )
    
    async def update_order_status(self, order: Order, status: OrderStatus, db: AsyncSession):
        await db.execute(
            update(Order).where(Order.id == order.id).values(status=status)
        )
        await db.commit()
    
    async def cancel_order(self, order_id: int, db: AsyncSession) -> bool:
        result = await db.execute(select(Order).where(Order.id == order_id))
        order = result.scalar_one_or_none()
        
        if not order or order.status in [OrderStatus.FILLED, OrderStatus.CANCELLED]:
            return False
        
        order_book = self.order_books[order.symbol]
        order_book.remove_order(order_id)
        
        await self.update_order_status(order, OrderStatus.CANCELLED, db)
        return True
    
    def get_order_book_snapshot(self, symbol: str) -> Dict:
        order_book = self.order_books[symbol]
        
        bids = []
        asks = []
        
        for neg_price, _, order in sorted(order_book.buy_orders, reverse=True)[:10]:
            bids.append({"price": float(-neg_price), "quantity": float(order.remaining_quantity)})
        
        for price, _, order in sorted(order_book.sell_orders)[:10]:
            asks.append({"price": float(price), "quantity": float(order.remaining_quantity)})
        
        return {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "best_bid": float(order_book.get_best_bid() or 0),
            "best_ask": float(order_book.get_best_ask() or 0)
        }


trading_engine = TradingEngine()