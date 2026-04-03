from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    telegram_channel_id: str = ""
    rugcheck_api_key: Optional[str] = None
    
    scanning_interval: int = 30
    min_liquidity: float = 25000
    min_volume_1h: float = 10000
    min_rugcheck_score: int = 60
    max_top_holder_pct: int = 15
    signal_cooldown: int = 300
    
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
