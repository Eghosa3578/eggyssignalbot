from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from loguru import logger

from .rugcheck import RugCheckClient


@dataclass
class SecurityResult:
    token_address: str
    overall_score: int
    risk_level: str
    is_safe: bool
    checks: Dict[str, Any]
    top_holders_pct: float
    mint_authority: str
    freeze_authority: str
    lp_burned: bool
    lp_burn_address: Optional[str]
    warnings: List[str]
    errors: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "token_address": self.token_address,
            "overall_score": self.overall_score,
            "risk_level": self.risk_level,
            "is_safe": self.is_safe,
            "checks": self.checks,
            "top_holders_pct": self.top_holders_pct,
            "mint_authority": self.mint_authority,
            "freeze_authority": self.freeze_authority,
            "lp_burned": self.lp_burned,
            "lp_burn_address": self.lp_burn_address,
            "warnings": self.warnings,
            "errors": self.errors,
        }


class SecurityAnalyzer:
    BURN_ADDRESSES = [
        "11111111111111111111111111111111",
        "Burn0000000000000000000000000000000000000000000",
        "ExHLDwnVNBtDmNsLHDmDTVS66MqMbhKQ5P3BYJ2UQUpf",
        "DANGER1200000000000000000000000000000000000000",
        "SPECIAL1200000000000000000000000000000000000000",
    ]
    
    def __init__(self, rugcheck_client: RugCheckClient, min_score: int = 60):
        self.rugcheck = rugcheck_client
        self.min_score = min_score
    
    async def analyze_token(self, token_address: str) -> Optional[SecurityResult]:
        try:
            report = await self.rugcheck.get_token_report(token_address)
            score_data = await self.rugcheck.get_token_score(token_address)
            
            if not report and not score_data:
                logger.warning(f"No RugCheck data for {token_address}")
                return self._create_unknown_result(token_address)
            
            return self._parse_analysis(token_address, report, score_data)
        
        except Exception as e:
            logger.error(f"Error analyzing token {token_address}: {e}")
            return None
    
    def _parse_analysis(
        self, 
        token_address: str, 
        report: Optional[Dict[str, Any]], 
        score_data: Optional[Dict[str, Any]]
    ) -> SecurityResult:
        checks = {}
        warnings = []
        errors = []
        
        mint_authority = "unknown"
        freeze_authority = "unknown"
        lp_burned = False
        lp_burn_address = None
        top_holders_pct = 100
        
        overall_score = 50
        risk_level = "MEDIUM"
        is_safe = False
        
        if report:
            token_data = report.get("token", {})
            tags = report.get("tags", [])
            
            if "mintable" in tags or "unverified mint" in str(tags).lower():
                mint_authority = "active"
                errors.append("Mint authority is active")
            else:
                mint_authority = "revoked"
                checks["mint_authority"] = {"status": "passed", "detail": "Revoked"}
            
            if "unverified freeze" in str(tags).lower():
                freeze_authority = "active"
                warnings.append("Freeze authority may be active")
            else:
                freeze_authority = "revoked"
                checks["freeze_authority"] = {"status": "passed", "detail": "Revoked"}
            
            lp_token = token_data.get("lpToken", {})
            if lp_token:
                lp_holder = lp_token.get("holder", "") or lp_token.get("address", "")
                lp_burn_address = lp_holder
                if any(burn in lp_holder for burn in self.BURN_ADDRESSES):
                    lp_burned = True
                    checks["lp_burned"] = {"status": "passed", "detail": "LP burned"}
                else:
                    lp_burned = False
                    warnings.append("LP not burned - liquidity not locked")
                    checks["lp_burned"] = {"status": "warning", "detail": f"LP holder: {lp_holder[:8]}..."}
            
            top_holders = report.get("topHolders", [])
            if top_holders:
                total_pct = sum(h.get("pct", 0) for h in top_holders[:10])
                top_holders_pct = total_pct
                
                if total_pct > 80:
                    errors.append(f"Top 10 holders own {total_pct:.1f}% - HIGH CONCENTRATION")
                    checks["holder_distribution"] = {"status": "danger", "detail": f"{total_pct:.1f}%"}
                elif total_pct > 50:
                    warnings.append(f"Top 10 holders own {total_pct:.1f}% - Moderate concentration")
                    checks["holder_distribution"] = {"status": "warning", "detail": f"{total_pct:.1f}%"}
                else:
                    checks["holder_distribution"] = {"status": "passed", "detail": f"{total_pct:.1f}%"}
            
            if "honeypot" in tags or "honeypot" in str(report).lower():
                errors.append("HONEYPOT DETECTED - Cannot sell tokens")
                checks["honeypot"] = {"status": "danger", "detail": "Honeypot detected"}
            
            if "钓鱼" in str(report) or "phishing" in str(report).lower():
                errors.append("PHISHING TOKEN DETECTED")
            
            if "danger" in tags or "scam" in tags:
                errors.append("Flagged as dangerous/scam")
        
        if score_data:
            score = score_data.get("score", 0) or score_data.get("totalScore", 50)
            overall_score = int(score)
        
        if overall_score >= 80:
            risk_level = "LOW"
            is_safe = True
        elif overall_score >= 50:
            risk_level = "MEDIUM"
            is_safe = overall_score >= self.min_score
        else:
            risk_level = "HIGH"
            is_safe = False
        
        if not checks.get("mint_authority"):
            checks["mint_authority"] = {"status": "unknown", "detail": "Could not verify"}
        if not checks.get("lp_burned"):
            checks["lp_burned"] = {"status": "unknown", "detail": "Could not verify"}
        if not checks.get("holder_distribution"):
            checks["holder_distribution"] = {"status": "unknown", "detail": "Could not verify"}
        
        return SecurityResult(
            token_address=token_address,
            overall_score=overall_score,
            risk_level=risk_level,
            is_safe=is_safe,
            checks=checks,
            top_holders_pct=top_holders_pct,
            mint_authority=mint_authority,
            freeze_authority=freeze_authority,
            lp_burned=lp_burned,
            lp_burn_address=lp_burn_address,
            warnings=warnings,
            errors=errors,
        )
    
    def _create_unknown_result(self, token_address: str) -> SecurityResult:
        return SecurityResult(
            token_address=token_address,
            overall_score=50,
            risk_level="MEDIUM",
            is_safe=False,
            checks={
                "mint_authority": {"status": "unknown", "detail": "Not verified"},
                "freeze_authority": {"status": "unknown", "detail": "Not verified"},
                "lp_burned": {"status": "unknown", "detail": "Not verified"},
                "holder_distribution": {"status": "unknown", "detail": "Not verified"},
            },
            top_holders_pct=100,
            mint_authority="unknown",
            freeze_authority="unknown",
            lp_burned=False,
            lp_burn_address=None,
            warnings=["Could not verify token security - manual check required"],
            errors=[],
        )
