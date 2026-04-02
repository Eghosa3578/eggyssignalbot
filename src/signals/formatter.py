from typing import Optional
from .detector import Signal


class SignalFormatter:
    def format_signal(self, signal: Signal) -> str:
        parts = []
        
        parts.append("🚀 <b>NEW GEM DETECTED!</b>")
        parts.append("")
        parts.append(f"📛 <b>Name:</b> {signal.token_name}")
        parts.append(f"💰 <b>Symbol:</b> ${signal.token_symbol}")
        parts.append(f"🔗 <b>CA:</b> <code>{signal.token_address}</code>")
        parts.append("")
        
        parts.append("📊 <b>Metrics:</b>")
        parts.append(f"├ 💧 <b>Liquidity:</b> ${signal.liquidity_usd:,.0f}")
        parts.append(f"├ 📊 <b>Market Cap:</b> ${signal.market_cap:,.0f}")
        parts.append(f"├ 📈 <b>Volume 1h:</b> ${signal.volume_1h:,.0f}")
        parts.append(f"├ 📊 <b>Volume 24h:</b> ${signal.volume_24h:,.0f}")
        parts.append(f"├ 🔄 <b>Txns 1h:</b> {signal.buys_1h + signal.sells_1h} ({signal.buys_1h}B/{signal.sells_1h}S)")
        parts.append(f"├ 📉 <b>Change 1h:</b> {self._format_change(signal.price_change_1h)}")
        parts.append(f"└ 📉 <b>Change 24h:</b> {self._format_change(signal.price_change_24h)}")
        parts.append("")
        
        if signal.security:
            parts.append("🛡️ <b>Security:</b>")
            
            score = signal.security.overall_score
            if score >= 80:
                score_emoji = "✅"
                score_color = "Safe"
            elif score >= 50:
                score_emoji = "⚠️"
                score_color = "Medium"
            else:
                score_emoji = "❌"
                score_color = "Risky"
            
            parts.append(f"├ ⭐ <b>RugCheck:</b> {score}/100 ({score_emoji} {score_color})")
            
            lp_status = "✅ Burned" if signal.security.lp_burned else "❌ Not Burned"
            parts.append(f"├ 🔒 <b>LP:</b> {lp_status}")
            
            mint_status = "✅ Revoked" if signal.security.mint_authority == "revoked" else "⚠️ Active"
            parts.append(f"├ 🔑 <b>Mint Auth:</b> {mint_status}")
            
            freeze_status = "✅ Revoked" if signal.security.freeze_authority == "revoked" else "⚠️ Active"
            parts.append(f"├ 🥶 <b>Freeze:</b> {freeze_status}")
            
            parts.append(f"└ 👥 <b>Top 10 Holders:</b> {signal.security.top_holders_pct:.1f}%")
            
            if signal.security.warnings:
                parts.append("")
                for warning in signal.security.warnings[:2]:
                    parts.append(f"⚠️ {warning}")
        else:
            parts.append("🛡️ <b>Security:</b> ⏳ Check pending")
        
        parts.append("")
        parts.append("🔗 <b>Links:</b>")
        parts.append(f"├ DEX: https://dexscreener.com/solana/{signal.token_address}")
        parts.append(f"└ Chart: https://dexscreener.com/solana/{signal.token_address}")
        parts.append("")
        
        parts.append(f"🎯 <b>Signal Score:</b> {signal.signal_score}/100 ({signal.signal_strength})")
        parts.append("")
        
        parts.append("📝 <b>Why This Gem:</b>")
        for reason in signal.reasons[:4]:
            parts.append(f"• {reason}")
        
        parts.append("")
        parts.append("⚠️ <b>DYOR</b> - Not financial advice!")
        
        return "\n".join(parts)
    
    def format_signal_compact(self, signal: Signal) -> str:
        parts = []
        
        parts.append("🚀 <b>${}</b> | 💧 ${} | 📈 {}% 1h | ⭐ {}/100".format(
            signal.token_symbol,
            self._format_k(signal.liquidity_usd),
            signal.price_change_1h,
            signal.security.overall_score if signal.security else "?"
        ))
        
        parts.append(f"🔗 https://dexscreener.com/solana/{signal.token_address}")
        
        return "\n".join(parts)
    
    def _truncate_address(self, address: str) -> str:
        if not address or len(address) < 16:
            return address
        return f"{address[:6]}...{address[-4:]}"
    
    def _format_change(self, value: float) -> str:
        emoji = "🔴" if value < 0 else "🟢"
        return f"{emoji} {value:+.1f}%"
    
    def _format_k(self, value: float) -> str:
        if value >= 1_000_000:
            return f"{value/1_000_000:.1f}M"
        elif value >= 1_000:
            return f"{value/1_000:.1f}K"
        return str(int(value))
