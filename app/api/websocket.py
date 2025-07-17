from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.services.market_data import market_data_service
from app.services.trading_engine import trading_engine
from app.api.auth import get_current_user
from app.models.user import User
import json
import asyncio
from typing import Dict, List

router = APIRouter()


class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[int, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, channel: str, user_id: int = None):
        await websocket.accept()
        
        if channel not in self.active_connections:
            self.active_connections[channel] = []
        self.active_connections[channel].append(websocket)
        
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, channel: str, user_id: int = None):
        if channel in self.active_connections:
            if websocket in self.active_connections[channel]:
                self.active_connections[channel].remove(websocket)
        
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
    
    async def broadcast_to_channel(self, message: str, channel: str):
        if channel in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[channel]:
                try:
                    await connection.send_text(message)
                except:
                    dead_connections.append(connection)
            
            for dead_connection in dead_connections:
                self.active_connections[channel].remove(dead_connection)
    
    async def send_to_user(self, message: str, user_id: int):
        if user_id in self.user_connections:
            dead_connections = []
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_text(message)
                except:
                    dead_connections.append(connection)
            
            for dead_connection in dead_connections:
                self.user_connections[user_id].remove(dead_connection)


manager = WebSocketManager()


@router.websocket("/ws/prices/{symbol}")
async def websocket_prices(websocket: WebSocket, symbol: str):
    await manager.connect(websocket, f"prices:{symbol}")
    
    try:
        while True:
            ticker = await market_data_service.get_ticker(symbol)
            if ticker:
                await websocket.send_text(json.dumps(ticker))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"prices:{symbol}")


@router.websocket("/ws/orderbook/{symbol}")
async def websocket_orderbook(websocket: WebSocket, symbol: str):
    await manager.connect(websocket, f"orderbook:{symbol}")
    
    try:
        while True:
            orderbook = trading_engine.get_order_book_snapshot(symbol)
            await websocket.send_text(json.dumps(orderbook))
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"orderbook:{symbol}")


@router.websocket("/ws/trades/{symbol}")
async def websocket_trades(websocket: WebSocket, symbol: str):
    await manager.connect(websocket, f"trades:{symbol}")
    
    try:
        while True:
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"trades:{symbol}")


@router.websocket("/ws/account")
async def websocket_account(websocket: WebSocket, token: str):
    await manager.connect(websocket, "account")
    
    try:
        while True:
            account_update = {
                "type": "account_update",
                "timestamp": "2024-01-01T00:00:00Z",
                "data": {
                    "balances": {},
                    "orders": [],
                    "trades": []
                }
            }
            await websocket.send_text(json.dumps(account_update))
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(websocket, "account")


async def broadcast_price_update(symbol: str, price_data: dict):
    await manager.broadcast_to_channel(
        json.dumps(price_data), 
        f"prices:{symbol}"
    )


async def broadcast_trade_execution(symbol: str, trade_data: dict):
    await manager.broadcast_to_channel(
        json.dumps(trade_data), 
        f"trades:{symbol}"
    )


async def notify_user_order_update(user_id: int, order_data: dict):
    await manager.send_to_user(
        json.dumps(order_data), 
        user_id
    )