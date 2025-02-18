# Project Structure

```
trader-tony/
├── src/
│   ├── bot/
│   │   ├── index.js              # Bot entry point
│   │   ├── commands.js           # Command handlers
│   │   └── keyboard.js           # Telegram keyboard layouts
│   │
│   ├── sniper/
│   │   ├── index.js              # Sniper module
│   │   ├── transaction.js        # Transaction builder
│   │   └── gas.js               # Gas optimization
│   │
│   ├── shorter/
│   │   ├── index.js              # Shorting module
│   │   ├── platforms/           # Platform connectors
│   │   │   ├── gmx.js
│   │   │   ├── dydx.js
│   │   │   └── gains.js
│   │   └── position.js          # Position management
│   │
│   ├── analysis/
│   │   ├── index.js              # Analysis entry point
│   │   ├── contract.js           # Contract analysis
│   │   ├── risk.js              # Risk assessment
│   │   └── patterns.js          # Pattern detection
│   │
│   ├── utils/
│   │   ├── network.js            # Network utilities
│   │   ├── logger.js            # Logging setup
│   │   └── config.js            # Configuration
│   │
│   └── database/
│       ├── index.js              # Database connection
│       └── models/              # Data models
│
├── config/
│   ├── default.json             # Default configuration
│   └── production.json          # Production settings
│
├── tests/
│   ├── sniper.test.js
│   ├── shorter.test.js
│   └── analysis.test.js
│
├── scripts/
│   ├── setup.js                 # Setup script
│   └── deploy.js                # Deployment script
│
├── docs/
│   ├── API.md                   # API documentation
│   └── DEPLOYMENT.md            # Deployment guide
│
├── .env.example                 # Example environment variables
├── package.json                 # Project manifest
├── README.md                    # Project documentation
└── LICENSE                      # License information
```

## Key Components

### Bot Module
Handles Telegram interactions and command processing

### Sniper Module
Manages token sniping operations and transaction execution

### Shorter Module
Handles shorting operations across different platforms

### Analysis Module
Performs risk analysis and pattern detection

### Utils
Common utilities and helper functions

### Database
Data persistence and state management

## Configuration Files

### Environment Variables (.env)
```env
TELEGRAM_BOT_TOKEN=your_bot_token
ETH_RPC_URL=ethereum_rpc_url
SOL_RPC_URL=solana_rpc_url
PRIVATE_KEY=wallet_private_key
MONGODB_URI=mongodb_connection_string
```

### Default Configuration (config/default.json)
```json
{
    "network": {
        "ethereum": {
            "chainId": 1,
            "confirmations": 1
        },
        "solana": {
            "commitment": "confirmed"
        }
    },
    "trading": {
        "maxGasPrice": 5000,
        "maxSlippage": 15,
        "maxLeverage": 5
    },
    "monitoring": {
        "interval": 1000,
        "timeout": 300000
    }
}
```