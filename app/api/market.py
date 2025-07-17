from fastapi import APIRouter
from typing import List, Dict, Optional
from app.services.market_data import market_data_service

router = APIRouter(prefix="/market", tags=["market"])


@router.get("/ticker/{symbol}")
async def get_ticker(symbol: str) -> Optional[Dict]:
    return await market_data_service.get_ticker(symbol)


@router.get("/tickers")
async def get_all_tickers() -> List[Dict]:
    return await market_data_service.get_all_tickers()


@router.get("/history/{symbol}")
async def get_historical_data(symbol: str, limit: int = 100) -> List[Dict]:
    return await market_data_service.get_historical_data(symbol, limit)


@router.get("/symbols")
async def get_symbols() -> List[str]:
    return ["BTCUSDT", "ETHUSDT", "ADAUSDT", "DOTUSDT"]