# TraderTony Project Manifest

## Project Overview

TraderTony is a Telegram-based trading bot for Solana tokens, built with Python. The bot provides a simple interface for viewing token information and executing trades on the Raydium DEX.

## Project Structure

```
trader-tony/
├── docs/                    # Documentation
├── src/                     # Source code
│   ├── bot/                # Telegram bot components
│   ├── trading/           # Trading functionality
│   └── utils/             # Utility modules
├── tests/                  # Test files
├── .env                    # Environment configuration
└── requirements.txt        # Project dependencies
```

## Core Modules

### Bot Module (src/bot/)
- `handler.py`: Telegram command handlers
- `__init__.py`: Bot module initialization

### Trading Module (src/trading/)
- `sniper.py`: Token info and trading logic
- `raydium.py`: Raydium DEX integration
- `__init__.py`: Trading module initialization

### Utils Module (src/utils/)
- `wallet.py`: Wallet management
- `config.py`: Configuration handling
- `__init__.py`: Utils module initialization

## Dependencies

### Core Dependencies
```
pyTelegramBotAPI==4.14.0    # Telegram bot framework
solana==0.30.2              # Solana blockchain interaction
solders==0.18.1             # Solana transaction handling
python-dotenv==1.0.0        # Environment configuration
```

## Environment Variables

Required environment variables in `.env`:
```
# Telegram Configuration
TELEGRAM_BOT_TOKEN=your_bot_token

# Solana Configuration
SOLANA_RPC_URL=your_rpc_url
WALLET_SEED_PHRASE=optional_admin_wallet_seed

# Trading Configuration
MAX_SLIPPAGE=1.0
MIN_SOL_BALANCE=0.05
```

## Testing

Test files are organized to match the source structure:
```
tests/
├── test_sniper.py          # Trading tests
├── test_wallet.py          # Wallet tests
└── test_raydium.py         # DEX integration tests
```

## Documentation

Key documentation files:
- `trading_bot_architecture.md`: System architecture
- `project_manifest.md`: Project structure (this file)
- `IMPLEMENTATION_GUIDE.md`: Implementation details

## Development Setup

1. Clone repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure environment variables
4. Run bot:
   ```bash
   python main.py
   ```

## Testing

Run tests with:
```bash
pytest tests/
```

## Contributing

1. Fork repository
2. Create feature branch
3. Implement changes
4. Add tests
5. Submit pull request

## License

MIT License - See LICENSE file for details
