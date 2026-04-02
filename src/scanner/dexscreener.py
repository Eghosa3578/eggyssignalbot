import httpx
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger


class DexScreenerClient:
    BASE_URL = "https://api.dexscreener.com"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def get_latest_pairs(self, chain: str = "solana", limit: int = 50) -> List[Dict[str, Any]]:
        try:
            url1 = f"{self.BASE_URL}/token-boosts/latest/v1"
            response1 = await self.client.get(url1)
            response1.raise_for_status()
            boosts = response1.json()
            
            addresses = [p["tokenAddress"] for p in boosts if p.get("chainId") == chain]
            addresses = list(dict.fromkeys(addresses))[:30]
            
            if not addresses:
                return []
                
            addr_str = ",".join(addresses)
            url2 = f"{self.BASE_URL}/latest/dex/tokens/{addr_str}"
            response2 = await self.client.get(url2)
            response2.raise_for_status()
            data = response2.json()
            
            if isinstance(data, dict) and "pairs" in data:
                pairs = [p for p in data["pairs"] if p.get("chainId") == chain]
                return [self._normalize_pair(p) for p in pairs[:limit]]
            elif isinstance(data, list):
                pairs = [p for p in data if p.get("chainId") == chain]
                return [self._normalize_pair(p) for p in pairs[:limit]]
            return []
        except Exception as e:
            logger.error(f"Error fetching latest pairs: {e}")
            return []
    
    async def search_pairs(self, query: str, chain: str = "solana") -> List[Dict[str, Any]]:
        try:
            url = f"{self.BASE_URL}/latest/dex/search"
            params = {"chainId": chain, "q": query}
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                return [self._normalize_pair(p) for p in data]
            elif isinstance(data, dict) and "pairs" in data:
                return [self._normalize_pair(p) for p in data["pairs"]]
            return []
        except Exception as e:
            logger.error(f"Error searching pairs: {e}")
            return []
    
    async def get_token_pairs(self, chain: str, token_address: str) -> List[Dict[str, Any]]:
        try:
            url = f"{self.BASE_URL}/token-pairs/v1/{chain}/{token_address}"
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                return [self._normalize_pair(p) for p in data]
            elif isinstance(data, dict) and "pairs" in data:
                return [self._normalize_pair(p) for p in data["pairs"]]
            return []
        except Exception as e:
            logger.error(f"Error fetching token pairs for {token_address}: {e}")
            return []
    
    async def get_boosted_tokens(self) -> List[Dict[str, Any]]:
        try:
            url = f"{self.BASE_URL}/token-boosts/latest/v1"
            response = await self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            if isinstance(data, list):
                return data
            return []
        except Exception as e:
            logger.error(f"Error fetching boosted tokens: {e}")
            return []
    
    async def get_new_solana_tokens(self, min_liquidity: float = 0, limit: int = 100) -> List[Dict[str, Any]]:
        try:
            pairs = await self.get_latest_pairs("solana", limit)
            
            new_tokens = []
            for pair in pairs:
                liquidity = pair.get("liquidity_usd", 0) or 0
                if liquidity >= min_liquidity:
                    if self._is_meme_token(pair):
                        new_tokens.append(pair)
            
            return new_tokens[:limit]
        except Exception as e:
            logger.error(f"Error fetching new Solana tokens: {e}")
            return []
    
    def _normalize_pair(self, pair: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "pair_address": pair.get("pairAddress") or pair.get("pair_address"),
            "chain_id": pair.get("chainId") or pair.get("chain_id", "solana"),
            "dex_id": pair.get("dexId"),
            "token_address": pair.get("baseToken", {}).get("address") if pair.get("baseToken") else pair.get("baseTokenAddress"),
            "token_name": pair.get("baseToken", {}).get("name") if pair.get("baseToken") else pair.get("baseTokenName"),
            "token_symbol": pair.get("baseToken", {}).get("symbol") if pair.get("baseToken") else pair.get("baseTokenSymbol"),
            "quote_token_symbol": pair.get("quoteToken", {}).get("symbol") if pair.get("quoteToken") else "SOL",
            "price_usd": float(pair.get("priceUsd", 0) or 0),
            "price_change_1h": float(pair.get("priceChange", {}).get("h1", 0) or 0) if isinstance(pair.get("priceChange"), dict) else float(pair.get("priceChange1h", 0) or 0),
            "price_change_6h": float(pair.get("priceChange", {}).get("h6", 0) or 0) if isinstance(pair.get("priceChange"), dict) else float(pair.get("priceChange6h", 0) or 0),
            "price_change_24h": float(pair.get("priceChange", {}).get("h24", 0) or 0) if isinstance(pair.get("priceChange"), dict) else float(pair.get("priceChange24h", 0) or 0),
            "market_cap": float(pair.get("marketCap", pair.get("fdv", 0)) or 0),
            "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0) or 0) if isinstance(pair.get("liquidity"), dict) else float(pair.get("liquidityUsd", 0) or 0),
            "liquidity_base": float(pair.get("liquidity", {}).get("base", 0) or 0) if isinstance(pair.get("liquidity"), dict) else 0,
            "volume_24h": float(pair.get("volume", {}).get("h24", 0) or 0) if isinstance(pair.get("volume"), dict) else float(pair.get("volume24h", 0) or 0),
            "volume_1h": float(pair.get("volume", {}).get("h1", 0) or 0) if isinstance(pair.get("volume"), dict) else float(pair.get("volume1h", 0) or 0),
            "txns_24h": pair.get("txns", {}).get("h24", {}) if isinstance(pair.get("txns"), dict) else {},
            "txns_1h": pair.get("txns", {}).get("h1", {}) if isinstance(pair.get("txns"), dict) else {},
            "buys_1h": (pair.get("txns", {}).get("h1", {}).get("buys", 0) or 0) if isinstance(pair.get("txns"), dict) else 0,
            "sells_1h": (pair.get("txns", {}).get("h1", {}).get("sells", 0) or 0) if isinstance(pair.get("txns"), dict) else 0,
            "buys_24h": (pair.get("txns", {}).get("h24", {}).get("buys", 0) or 0) if isinstance(pair.get("txns"), dict) else 0,
            "sells_24h": (pair.get("txns", {}).get("h24", {}).get("sells", 0) or 0) if isinstance(pair.get("txns"), dict) else 0,
            "url": pair.get("url") or f"https://dexscreener.com/solana/{pair.get('pairAddress') or pair.get('pair_address')}",
            "created_at": pair.get("pairCreatedAt") or pair.get("createdAt"),
        }
    
    def _is_meme_token(self, pair: Dict[str, Any]) -> bool:
        name = (pair.get("token_name", "") or "").lower()
        symbol = (pair.get("token_symbol", "") or "").lower()
        meme_keywords = ["dog", "cat", "frog", "pepe", "doge", "shib", "elon", "moon", "inu", 
                         "baby", "mini", "floki", "brett", "michi", "朋克", "doge", "wif", "maga",
                         "trump", "Biden", "based", "chad", "hawk", "bonk", "popcat", "moodeng"]
        
        for keyword in meme_keywords:
            if keyword in name or keyword in symbol:
                return True
        return False
