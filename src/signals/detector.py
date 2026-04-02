from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from ..security.analyzer import SecurityResult


@dataclass
class Signal:
    token_address: str
    token_name: str
    token_symbol: str
    liquidity_usd: float
    market_cap: float
    volume_1h: float
    volume_24h: float
    price_usd: float
    price_change_1h: float
    price_change_24h: float
    buys_1h: int
    sells_1h: int
    dex_url: str
    security: Optional[SecurityResult]
    signal_score: int
    signal_strength: str
    reasons: list
    timestamp: str


class SignalDetector:
    def __init__(
        self,
        min_liquidity: float = 25000,
        min_volume_1h: float = 10000,
        min_rugcheck_score: int = 60,
        max_top_holder_pct: int = 15,
        min_buys_1h: int = 5,
    ):
        self.min_liquidity = min_liquidity
        self.min_volume_1h = min_volume_1h
        self.min_rugcheck_score = min_rugcheck_score
        self.max_top_holder_pct = max_top_holder_pct
        self.min_buys_1h = min_buys_1h
    
    def evaluate(self, token_data: Dict[str, Any], security: Optional[SecurityResult] = None) -> Optional[Signal]:
        try:
            reasons = []
            score = 0
            max_score = 100
            
            liquidity = token_data.get("liquidity_usd", 0) or 0
            volume_1h = token_data.get("volume_1h", 0) or 0
            buys_1h = token_data.get("buys_1h", 0) or 0
            sells_1h = token_data.get("sells_1h", 0) or 0
            price_change_1h = token_data.get("price_change_1h", 0) or 0
            price_change_24h = token_data.get("price_change_24h", 0) or 0
            
            if liquidity >= 100000:
                score += 25
                reasons.append("High liquidity (>$100K)")
            elif liquidity >= self.min_liquidity:
                score += 15
                reasons.append(f"Liquidity: ${liquidity:,.0f}")
            
            if volume_1h >= 50000:
                score += 20
                reasons.append("Very high volume (>$50K/h)")
            elif volume_1h >= self.min_volume_1h:
                score += 10
                reasons.append(f"Volume 1h: ${volume_1h:,.0f}")
            
            if buys_1h >= 50:
                score += 15
                reasons.append(f"Strong buy pressure ({buys_1h} buys/h)")
            elif buys_1h >= self.min_buys_1h:
                score += 8
                reasons.append(f"Buy pressure: {buys_1h} buys/h")
            
            if sells_1h > 0 and buys_1h > sells_1h * 2:
                score += 10
                reasons.append("Buy/sell ratio > 2:1")
            
            if abs(price_change_1h) < 30 and price_change_1h > -10:
                score += 10
                reasons.append("Stable price action")
            elif price_change_1h > 20:
                score += 15
                reasons.append(f"Momentum: +{price_change_1h:.1f}% 1h")
            
            if security:
                if security.overall_score >= 80:
                    score += 20
                    reasons.append(f"RugCheck: {security.overall_score}/100 (Safe)")
                elif security.overall_score >= self.min_rugcheck_score:
                    score += 10
                    reasons.append(f"RugCheck: {security.overall_score}/100")
                else:
                    max_score -= 30
                
                if security.lp_burned:
                    score += 10
                    reasons.append("LP Burned")
                
                if security.top_holders_pct <= 10:
                    score += 10
                    reasons.append(f"Healthy distribution ({security.top_holders_pct:.1f}%)")
                elif security.top_holders_pct > self.max_top_holder_pct * 5:
                    max_score -= 20
                    reasons.append(f"Warning: {security.top_holders_pct:.1f}% held by top 10")
                
                if security.mint_authority == "revoked":
                    score += 5
                    reasons.append("Mint authority revoked")
                
                if security.errors:
                    return None
            else:
                score += 5
                reasons.append("Security check pending")
            
            signal_pct = (score / max_score) * 100
            
            if signal_pct >= 75:
                strength = "STRONG"
            elif signal_pct >= 55:
                strength = "MODERATE"
            else:
                strength = "WEAK"
            
            if score < 40:
                return None
            
            return Signal(
                token_address=token_data.get("token_address", ""),
                token_name=token_data.get("token_name", "Unknown"),
                token_symbol=token_data.get("token_symbol", "???"),
                liquidity_usd=liquidity,
                market_cap=token_data.get("market_cap", 0) or 0,
                volume_1h=volume_1h,
                volume_24h=token_data.get("volume_24h", 0) or 0,
                price_usd=token_data.get("price_usd", 0) or 0,
                price_change_1h=price_change_1h,
                price_change_24h=price_change_24h,
                buys_1h=buys_1h,
                sells_1h=sells_1h,
                dex_url=token_data.get("url", ""),
                security=security,
                signal_score=int(signal_pct),
                signal_strength=strength,
                reasons=reasons,
                timestamp=token_data.get("created_at", ""),
            )
        
        except Exception as e:
            logger.error(f"Error evaluating signal: {e}")
            return None
