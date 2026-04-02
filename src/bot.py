import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.constants import ParseMode
from loguru import logger

from .utils.database import Database


class TelegramBot:
    def __init__(self, token: str, channel_id: str, database: Database):
        self.token = token
        self.channel_id = channel_id
        self.database = database
        self.app = None
        self._subscribers = set()
    
    async def start(self):
        self.app = Application.builder().token(self.token).build()
        
        self.app.add_handler(CommandHandler("start", self._start_cmd))
        self.app.add_handler(CommandHandler("help", self._help_cmd))
        self.app.add_handler(CommandHandler("stats", self._stats_cmd))
        self.app.add_handler(CommandHandler("ping", self._ping_cmd))
        
        logger.info(f"Starting Telegram bot with token: {self.token[:10]}...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling()
        logger.info("Telegram bot started successfully")
    
    async def stop(self):
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        logger.info("Telegram bot stopped")
    
    async def send_signal(self, message: str, parse_mode: str = ParseMode.HTML) -> int:
        if not self.app:
            logger.error("Telegram bot not initialized")
            return None
        
        try:
            chat_id = self.channel_id
            if not chat_id.startswith("@"):
                chat_id = int(chat_id) if chat_id.lstrip("-").isdigit() else chat_id
            
            sent_message = await self.app.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode=parse_mode,
                disable_web_page_preview=True,
            )
            logger.info(f"Signal sent to {self.channel_id}, message_id: {sent_message.message_id}")
            return sent_message.message_id
        except Exception as e:
            logger.error(f"Error sending signal: {e}")
            return None
    
    async def _start_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        welcome = """
👋 <b>Welcome to Solana Signal Bot!</b>

I monitor Solana DEX pairs and send you alerts for promising tokens with good security.

<b>Commands:</b>
/start - Show this welcome message
/stats - View bot statistics  
/help - Help information
/ping - Check bot status

<b>Note:</b> You'll receive signals automatically when I find gems!
"""
        await update.message.reply_text(welcome, parse_mode=ParseMode.HTML)
    
    async def _help_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        help_text = """
<b>How It Works:</b>

🔍 I scan DexScreener for new Solana pairs
🛡️ Security checks via RugCheck API
📊 Analyze volume, liquidity, holders
🚀 Alert you when a gem is found!

<b>Tips:</b>
• Always DYOR (Do Your Own Research)
• Signals are not financial advice
• Check multiple sources before investing
"""
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    async def _stats_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        stats = await self.database.get_stats()
        
        stats_text = f"""
📊 <b>Bot Statistics</b>

🔎 Tokens Detected: {stats['total_detected']}
📨 Signals Sent: {stats['signals_sent']}

Monitoring is active 24/7!
"""
        await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)
    
    async def _ping_cmd(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("✅ Bot is online and monitoring!")
