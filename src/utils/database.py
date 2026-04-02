import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


class Database:
    def __init__(self, db_path: str = "data/signals.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    async def init(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS signals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    token_address TEXT UNIQUE NOT NULL,
                    token_name TEXT,
                    token_symbol TEXT,
                    liquidity REAL,
                    volume_1h REAL,
                    rugcheck_score INTEGER,
                    safety_status TEXT,
                    detected_at TEXT,
                    sent_at TEXT,
                    message_id INTEGER
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS token_cache (
                    token_address TEXT PRIMARY KEY,
                    data TEXT,
                    fetched_at TEXT
                )
            """)
            await db.commit()
    
    async def save_signal(self, signal_data: Dict[str, Any], message_id: int = None) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            try:
                await db.execute("""
                    INSERT OR REPLACE INTO signals 
                    (token_address, token_name, token_symbol, liquidity, volume_1h, 
                     rugcheck_score, safety_status, detected_at, sent_at, message_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    signal_data.get("token_address"),
                    signal_data.get("token_name"),
                    signal_data.get("token_symbol"),
                    signal_data.get("liquidity"),
                    signal_data.get("volume_1h"),
                    signal_data.get("rugcheck_score"),
                    signal_data.get("safety_status"),
                    signal_data.get("detected_at"),
                    datetime.utcnow().isoformat(),
                    message_id
                ))
                await db.commit()
                return True
            except Exception as e:
                return False
    
    async def was_signal_sent(self, token_address: str, cooldown_seconds: int = 300) -> bool:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT sent_at FROM signals 
                WHERE token_address = ? AND sent_at IS NOT NULL
                ORDER BY rowid DESC LIMIT 1
            """, (token_address,))
            row = await cursor.fetchone()
            if row:
                last_sent = datetime.fromisoformat(row[0])
                elapsed = (datetime.utcnow() - last_sent).total_seconds()
                return elapsed < cooldown_seconds
            return False
    
    async def cache_token(self, token_address: str, data: Dict[str, Any]):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO token_cache (token_address, data, fetched_at)
                VALUES (?, ?, ?)
            """, (token_address, json.dumps(data), datetime.utcnow().isoformat()))
            await db.commit()
    
    async def get_cached_token(self, token_address: str) -> Optional[Dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT data, fetched_at FROM token_cache WHERE token_address = ?
            """, (token_address,))
            row = await cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
    
    async def get_stats(self) -> Dict[str, Any]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM signals")
            total = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT COUNT(*) FROM signals WHERE sent_at IS NOT NULL")
            sent = (await cursor.fetchone())[0]
            
            return {"total_detected": total, "signals_sent": sent}
