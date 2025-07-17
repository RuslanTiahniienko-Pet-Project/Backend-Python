from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.api import auth, trading, market, wallet, websocket
from app.services.market_data import market_data_service
from app.core.config import settings
import asyncio
import json
from typing import Dict, List

app = FastAPI(title=settings.app_name, version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(trading.router, prefix="/api/v1")
app.include_router(market.router, prefix="/api/v1")
app.include_router(wallet.router, prefix="/api/v1")
app.include_router(websocket.router)

app.mount("/static", StaticFiles(directory="static"), name="static")


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, symbol: str):
        await websocket.accept()
        if symbol not in self.active_connections:
            self.active_connections[symbol] = []
        self.active_connections[symbol].append(websocket)
    
    def disconnect(self, websocket: WebSocket, symbol: str):
        if symbol in self.active_connections:
            self.active_connections[symbol].remove(websocket)
    
    async def broadcast(self, message: str, symbol: str):
        if symbol in self.active_connections:
            for connection in self.active_connections[symbol]:
                try:
                    await connection.send_text(message)
                except:
                    self.active_connections[symbol].remove(connection)


manager = ConnectionManager()


@app.websocket("/ws/prices/{symbol}")
async def websocket_endpoint(websocket: WebSocket, symbol: str):
    await manager.connect(websocket, symbol)
    try:
        while True:
            ticker = await market_data_service.get_ticker(symbol)
            if ticker:
                await websocket.send_text(json.dumps(ticker))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket, symbol)


@app.on_event("startup")
async def startup_event():
    await market_data_service.initialize()


@app.on_event("shutdown")
async def shutdown_event():
    await market_data_service.stop()


@app.get("/")
async def root():
    return {"message": "SecureTradeAPI is running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "SecureTradeAPI"}