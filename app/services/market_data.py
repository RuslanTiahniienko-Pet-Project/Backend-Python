import asyncio
import json
import websockets
from decimal import Decimal
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.trading import MarketData
from app.core.database import AsyncSessionLocal
import aioredis
from app.core.config import settings
from dataclasses import dataclass
from datetime import datetime


@dataclass
class PriceUpdate:
    symbol: str
    price: Decimal
    volume: Decimal
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    source: str = "internal"


class MarketDataService:
    def __init__(self):
        self.redis = None
        self.subscribers: Dict[str, List] = {}
        self.price_cache: Dict[str, PriceUpdate] = {}
        self.running = False
    
    async def initialize(self):
        self.redis = await aioredis.from_url(settings.redis_url)
        await self.start_price_simulation()
    
    async def start_price_simulation(self):
        self.running = True
        symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"]
        
        initial_prices = {
            "BTCUSDT": Decimal("45000.00"),
            "ETHUSDT": Decimal("3200.00"),
            "ADAUSDT": Decimal("1.25"),
            "DOTUSDT": Decimal("25.50")
        }
        
        for symbol in symbols:
            self.price_cache[symbol] = PriceUpdate(
                symbol=symbol,
                price=initial_prices[symbol],
                volume=Decimal("1000.0"),
                bid_price=initial_prices[symbol] * Decimal("0.999"),
                ask_price=initial_prices[symbol] * Decimal("1.001")
            )
        
        asyncio.create_task(self.simulate_price_updates())
    
    async def simulate_price_updates(self):
        import random
        
        while self.running:
            for symbol in self.price_cache:
                current_price = self.price_cache[symbol].price
                
                change_percent = Decimal(str(random.uniform(-0.02, 0.02)))
                new_price = current_price * (1 + change_percent)
                
                volume = Decimal(str(random.uniform(100, 2000)))
                
                price_update = PriceUpdate(
                    symbol=symbol,
                    price=new_price,
                    volume=volume,
                    bid_price=new_price * Decimal("0.999"),
                    ask_price=new_price * Decimal("1.001")
                )
                
                await self.update_price(price_update)
            
            await asyncio.sleep(1)
    
    async def update_price(self, price_update: PriceUpdate):
        self.price_cache[price_update.symbol] = price_update
        
        await self.redis.hset(
            f"price:{price_update.symbol}",
            mapping={
                "price": str(price_update.price),
                "volume": str(price_update.volume),
                "bid_price": str(price_update.bid_price),
                "ask_price": str(price_update.ask_price),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
        
        await self.redis.publish(
            f"price_updates:{price_update.symbol}",
            json.dumps({
                "symbol": price_update.symbol,
                "price": str(price_update.price),
                "volume": str(price_update.volume),
                "bid_price": str(price_update.bid_price),
                "ask_price": str(price_update.ask_price),
                "timestamp": datetime.utcnow().isoformat()
            })
        )
        
        await self.store_market_data(price_update)
    
    async def store_market_data(self, price_update: PriceUpdate):
        async with AsyncSessionLocal() as db:
            market_data = MarketData(
                symbol=price_update.symbol,
                price=price_update.price,
                volume=price_update.volume,
                bid_price=price_update.bid_price,
                ask_price=price_update.ask_price
            )
            
            db.add(market_data)
            await db.commit()
    
    async def get_ticker(self, symbol: str) -> Optional[Dict]:
        if symbol in self.price_cache:
            price_update = self.price_cache[symbol]
            return {
                "symbol": symbol,
                "price": str(price_update.price),
                "volume": str(price_update.volume),
                "bid_price": str(price_update.bid_price),
                "ask_price": str(price_update.ask_price),
                "timestamp": datetime.utcnow().isoformat()
            }
        return None
    
    async def get_all_tickers(self) -> List[Dict]:
        tickers = []
        for symbol in self.price_cache:
            ticker = await self.get_ticker(symbol)
            if ticker:
                tickers.append(ticker)
        return tickers
    
    async def get_historical_data(self, symbol: str, limit: int = 100) -> List[Dict]:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select, desc
            
            result = await db.execute(
                select(MarketData)
                .where(MarketData.symbol == symbol)
                .order_by(desc(MarketData.timestamp))
                .limit(limit)
            )
            
            market_data = result.scalars().all()
            
            return [
                {
                    "symbol": data.symbol,
                    "price": str(data.price),
                    "volume": str(data.volume),
                    "bid_price": str(data.bid_price),
                    "ask_price": str(data.ask_price),
                    "timestamp": data.timestamp.isoformat()
                }
                for data in market_data
            ]
    
    async def subscribe_to_price_updates(self, symbol: str, callback):
        if symbol not in self.subscribers:
            self.subscribers[symbol] = []
        self.subscribers[symbol].append(callback)
    
    async def unsubscribe_from_price_updates(self, symbol: str, callback):
        if symbol in self.subscribers:
            self.subscribers[symbol].remove(callback)
    
    async def stop(self):
        self.running = False
        if self.redis:
            await self.redis.close()


market_data_service = MarketDataService()