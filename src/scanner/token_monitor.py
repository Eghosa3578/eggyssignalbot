import asyncio
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime
from loguru import logger

from .dexscreener import DexScreenerClient
from ..utils.database import Database


class TokenMonitor:
    def __init__(
        self,
        dex_client: DexScreenerClient,
        database: Database,
        scanning_interval: int = 30,
        min_liquidity: float = 25000,
        min_volume_1h: float = 10000,
    ):
        self.dex_client = dex_client
        self.database = database
        self.scanning_interval = scanning_interval
        self.min_liquidity = min_liquidity
        self.min_volume_1h = min_volume_1h
        
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._callbacks: List[Callable] = []
        self._seen_tokens: set = set()
    
    def add_callback(self, callback: Callable):
        self._callbacks.append(callback)
    
    async def start(self):
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        logger.info("Token monitor started")
    
    async def stop(self):
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("Token monitor stopped")
    
    async def _monitor_loop(self):
        while self._running:
            try:
                await self._scan()
            except Exception as e:
                logger.error(f"Error in monitor loop: {e}")
            await asyncio.sleep(self.scanning_interval)
    
    async def _scan(self):
        logger.debug("Scanning for new tokens...")
        
        tokens = await self.dex_client.get_new_solana_tokens(
            min_liquidity=self.min_liquidity,
            limit=100
        )
        
        logger.debug(f"Found {len(tokens)} tokens with liquidity > ${self.min_liquidity}")
        
        filtered_tokens = []
        for token in tokens:
            if not self._filter_token(token):
                continue
            
            token_addr = token.get("token_address")
            if token_addr in self._seen_tokens:
                continue
            
            self._seen_tokens.add(token_addr)
            filtered_tokens.append(token)
        
        for token in filtered_tokens:
            for callback in self._callbacks:
                try:
                    await callback(token)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")
    
    def _filter_token(self, token: Dict[str, Any]) -> bool:
        liquidity = token.get("liquidity_usd", 0)
        volume_1h = token.get("volume_1h", 0)
        
        if liquidity < self.min_liquidity:
            return False
        
        if volume_1h < self.min_volume_1h:
            return False
        
        if not token.get("token_address"):
            return False
        
        if not token.get("token_name"):
            return False
        
        return True
    
    async def scan_specific_token(self, token_address: str) -> Optional[Dict[str, Any]]:
        pairs = await self.dex_client.get_token_pairs("solana", token_address)
        
        if not pairs:
            return None
        
        main_pair = max(pairs, key=lambda x: x.get("liquidity_usd", 0))
        return main_pair
    
    async def get_trending_tokens(self, limit: int = 20) -> List[Dict[str, Any]]:
        boosted = await self.dex_client.get_boosted_tokens()
        
        trending = []
        for token in boosted[:limit]:
            if token.get("chainId") == "solana":
                trending.append(token)
        
        return trending
