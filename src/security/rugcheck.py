import httpx
from typing import Dict, Any, Optional, List
from loguru import logger


class GoPlusClient:
    BASE_URL = "https://api.gopluslabs.io/api/v1"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        await self.client.aclose()
    
    async def get_token_security(self, chain: str, token_address: str) -> Optional[Dict[str, Any]]:
        try:
            url = f"{self.BASE_URL}/token_security/{chain}"
            params = {"contract_addresses": token_address}
            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if data.get("code") == 1 and data.get("data"):
                return data["data"].get(token_address.lower())
            return None
        except Exception as e:
            logger.error(f"Error fetching GoPlus security for {token_address}: {e}")
            return None
    
    async def get_solana_token_security(self, token_address: str) -> Optional[Dict[str, Any]]:
        return await self.get_token_security("solana", token_address)


class RugCheckClient:
    BASE_URL = "https://api.rugcheck.xyz"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)
        self.goplus = GoPlusClient()
    
    async def close(self):
        await self.client.aclose()
        await self.goplus.close()
    
    async def get_token_report(self, token_address: str) -> Optional[Dict[str, Any]]:
        try:
            if self.api_key:
                url = f"{self.BASE_URL}/v1/tokens/{token_address}/report"
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = await self.client.get(url, headers=headers)
                
                if response.status_code == 404:
                    return await self._fallback_to_goplus(token_address)
                
                response.raise_for_status()
                return response.json()
            else:
                return await self._fallback_to_goplus(token_address)
        except Exception as e:
            logger.warning(f"RugCheck failed, trying GoPlus: {e}")
            return await self._fallback_to_goplus(token_address)
    
    async def _fallback_to_goplus(self, token_address: str) -> Optional[Dict[str, Any]]:
        goplus_data = await self.goplus.get_solana_token_security(token_address)
        if goplus_data:
            return self._convert_goplus_to_rugcheck_format(goplus_data)
        return None
    
    def _convert_goplus_to_rugcheck_format(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "token": {
                "address": data.get("contract_address", ""),
                "name": data.get("token_name", ""),
                "symbol": data.get("token_symbol", ""),
            },
            "tags": [],
            "topHolders": [
                {"pct": float(data.get("holder_percent", 0))}
            ],
            "is_mintable": data.get("is_mintable", False),
            "is_proxy": data.get("is_proxy", False),
            "lp_total_supply": data.get("lp_total_supply", "0"),
            "goplus_data": data,
        }
    
    async def get_token_score(self, token_address: str) -> Optional[Dict[str, Any]]:
        report = await self.get_token_report(token_address)
        if not report:
            return {"score": 50, "totalScore": 50}
        
        goplus = report.get("goplus_data", {})
        
        score = 100
        
        if goplus.get("is_mintable", False):
            score -= 30
        if goplus.get("is_proxy", False):
            score -= 25
        if goplus.get("is_blacklisted", False):
            score -= 50
        if goplus.get("transfer_pausable", False):
            score -= 20
            
        lp_burned = goplus.get("lp_burned", True)
        if not lp_burned:
            score -= 20
            
        holder_pct = float(goplus.get("holder_percent", 0) or 0)
        if holder_pct > 50:
            score -= int(holder_pct * 0.3)
        
        return {
            "score": max(0, score),
            "totalScore": max(0, score),
            "source": "goplus" if "goplus_data" in report else "rugcheck"
        }
    
    async def get_token_top_holders(self, token_address: str) -> Optional[List[Dict[str, Any]]]:
        return None
