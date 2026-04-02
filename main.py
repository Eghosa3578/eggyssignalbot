import asyncio
import signal
from pathlib import Path

from config.settings import settings
from src.utils.logger import setup_logger, get_logger
from src.utils.database import Database
from src.scanner.dexscreener import DexScreenerClient
from src.scanner.token_monitor import TokenMonitor
from src.security.rugcheck import RugCheckClient
from src.security.analyzer import SecurityAnalyzer
from src.signals.detector import SignalDetector
from src.signals.formatter import SignalFormatter
from src.bot import TelegramBot


class SolanaSignalBot:
    def __init__(self):
        self.logger = setup_logger(settings.log_level)
        self.db = Database()
        
        self.dex_client = DexScreenerClient()
        self.rugcheck_client = RugCheckClient(settings.rugcheck_api_key)
        
        self.monitor = TokenMonitor(
            dex_client=self.dex_client,
            database=self.db,
            scanning_interval=settings.scanning_interval,
            min_liquidity=settings.min_liquidity,
            min_volume_1h=settings.min_volume_1h,
        )
        
        self.security_analyzer = SecurityAnalyzer(
            rugcheck_client=self.rugcheck_client,
            min_score=settings.min_rugcheck_score,
        )
        
        self.signal_detector = SignalDetector(
            min_liquidity=settings.min_liquidity,
            min_volume_1h=settings.min_volume_1h,
            min_rugcheck_score=settings.min_rugcheck_score,
            max_top_holder_pct=settings.max_top_holder_pct,
        )
        
        self.formatter = SignalFormatter()
        self.telegram_bot = TelegramBot(
            token=settings.telegram_bot_token,
            channel_id=settings.telegram_channel_id,
            database=self.db,
        )
        
        self._running = False
    
    async def start(self):
        self.logger.info("=" * 50)
        self.logger.info("Starting Solana Signal Bot")
        self.logger.info("=" * 50)
        
        Path("logs").mkdir(exist_ok=True)
        Path("data").mkdir(exist_ok=True)
        
        await self.db.init()
        self.logger.info("Database initialized")
        
        self.monitor.add_callback(self._on_new_token)
        await self.monitor.start()
        
        await self.telegram_bot.start()
        
        self._running = True
        self.logger.info("Bot is now running!")
        
        while self._running:
            await asyncio.sleep(1)
    
    async def stop(self):
        self.logger.info("Shutting down bot...")
        self._running = False
        
        await self.monitor.stop()
        await self.dex_client.close()
        await self.rugcheck_client.close()
        await self.telegram_bot.stop()
        
        self.logger.info("Bot shutdown complete")
    
    async def _on_new_token(self, token_data: dict):
        token_address = token_data.get("token_address")
        token_name = token_data.get("token_name", "Unknown")
        
        self.logger.info(f"New token detected: {token_name} ({token_address[:10]}...)")
        
        was_sent = await self.db.was_signal_sent(
            token_address, 
            cooldown_seconds=settings.signal_cooldown
        )
        
        if was_sent:
            self.logger.debug(f"Signal already sent for {token_address[:10]}... within cooldown period")
            return
        
        self.logger.info(f"Analyzing {token_name} security...")
        security = await self.security_analyzer.analyze_token(token_address)
        
        if not security:
            self.logger.warning(f"Could not get security analysis for {token_name}")
            return
        
        if not security.is_safe:
            self.logger.info(f"{token_name} failed security check (score: {security.overall_score})")
            return
        
        self.logger.info(f"Security passed for {token_name} (score: {security.overall_score})")
        
        signal = self.signal_detector.evaluate(token_data, security)
        
        if not signal:
            self.logger.debug(f"{token_name} did not meet signal criteria")
            return
        
        self.logger.info(f"🎉 GEM FOUND: {token_name} - Score: {signal.signal_score}/100 ({signal.signal_strength})")
        
        message = self.formatter.format_signal(signal)
        
        message_id = await self.telegram_bot.send_signal(message)
        
        if message_id:
            await self.db.save_signal(
                {
                    "token_address": token_address,
                    "token_name": token_name,
                    "token_symbol": token_data.get("token_symbol"),
                    "liquidity": token_data.get("liquidity_usd"),
                    "volume_1h": token_data.get("volume_1h"),
                    "rugcheck_score": security.overall_score,
                    "safety_status": security.risk_level,
                    "detected_at": token_data.get("created_at"),
                },
                message_id=message_id,
            )
            self.logger.info(f"Signal saved to database, message_id: {message_id}")


async def main():
    bot = SolanaSignalBot()
    
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        bot.logger.info("Received shutdown signal")
        asyncio.create_task(bot.stop())
    
    try:
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)
    except NotImplementedError:
        pass
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        await bot.stop()
    except Exception as e:
        bot.logger.error(f"Fatal error: {e}")
        await bot.stop()
        raise


if __name__ == "__main__":
    asyncio.run(main())
