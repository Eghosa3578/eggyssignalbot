# Solana Signal Bot

A Telegram bot that monitors Solana DEX pairs via DexScreener API, performs security audits via RugCheck, and sends trading signals when promising tokens are found.

## Features

- Real-time monitoring of Solana DEX pairs
- Security analysis using RugCheck API
- Automatic signal generation for promising tokens
- Telegram channel notifications
- Configurable filters and thresholds

## Setup

### 1. Create a Telegram Bot

1. Open Telegram and chat with [@BotFather](https://t.me/BotFather)
2. Send `/newbot` and follow the instructions
3. Copy your bot token

### 2. Create a Telegram Channel

1. Create a new channel in Telegram
2. Add your bot as an admin with "Post Messages" permission
3. Get your channel ID (e.g., `@your_channel_name` or `-1001234567890`)

### 3. Install Dependencies

```bash
cd solana-signal-bot
pip install -r requirements.txt
```

### 4. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHANNEL_ID=@your_channel_name
RUGCHECK_API_KEY=your_rugcheck_api_key_here
```

### 5. Run the Bot

```bash
python main.py
```

## Deployment with Docker

```bash
docker build -t solana-signal-bot .
docker run -d --env-file .env solana-signal-bot
```

## Deployment with Railway

1. Connect your GitHub repository
2. Add environment variables from your `.env` file
3. Deploy

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | - | Your Telegram bot token |
| `TELEGRAM_CHANNEL_ID` | - | Target channel ID |
| `RUGCHECK_API_KEY` | - | RugCheck API key (optional) |
| `SCANNING_INTERVAL` | 30 | Seconds between scans |
| `MIN_LIQUIDITY` | 25000 | Minimum USD liquidity |
| `MIN_VOLUME_1H` | 10000 | Minimum 1h volume |
| `MIN_RUGCHECK_SCORE` | 60 | Minimum RugCheck score |
| `MAX_TOP_HOLDER_PCT` | 15 | Max % for top 10 holders |
| `SIGNAL_COOLDOWN` | 300 | Seconds before re-alerting |

## Bot Commands

- `/start` - Welcome message
- `/help` - Help information
- `/stats` - View statistics
- `/ping` - Check bot status

## Disclaimer

This bot is for educational purposes only. Signals are not financial advice. Always DYOR before investing in any token.
