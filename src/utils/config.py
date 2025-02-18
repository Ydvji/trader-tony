"""
Configuration management for Trader Tony.
"""
import os
from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class TradingConfig:
    """Trading-specific configuration."""
    min_liquidity: float = 1000  # USD
    max_slippage: float = 1.0    # 1%
    take_profit: float = 50.0    # 50%
    stop_loss: float = 20.0      # 20%
    trailing_stop: Optional[float] = None
    anti_mev: bool = True
    priority_fee: float = 0.0001  # SOL
    max_buy_amount: float = 1.0  # SOL
    default_amount: float = 0.1  # SOL for quick snipes
    gas_limit: int = 1000000  # Compute units
    max_retries: int = 3  # Transaction retry attempts

@dataclass
class RiskConfig:
    """Risk management configuration."""
    min_holders: int = 10
    max_risk_score: int = 70
    min_verification_score: int = 80
    suspicious_pattern_threshold: float = 50.0  # 50% price change threshold
    max_buy_tax: float = 10.0  # Maximum acceptable buy tax
    max_sell_tax: float = 10.0  # Maximum acceptable sell tax
    min_liquidity_ratio: float = 0.1  # Min liquidity as % of market cap
    honeypot_check: bool = True  # Enable honeypot detection
    require_verified: bool = True  # Require verified contracts
    require_renounced: bool = True  # Require renounced ownership

from dataclasses import field

def default_trading_config() -> TradingConfig:
    return TradingConfig()

def default_risk_config() -> RiskConfig:
    return RiskConfig()

@dataclass
class MonitorConfig:
    """Monitoring configuration."""
    enabled: bool = True
    price_change_threshold: float = 5.0  # 5% price change alert
    liquidity_change_threshold: float = 10.0  # 10% liquidity change alert
    volume_spike_threshold: float = 100.0  # 100% volume increase alert
    alert_cooldown: int = 300  # 5 minutes between alerts
    max_pools_per_user: int = 10  # Maximum pools to monitor per user
    check_interval: int = 60  # Check every minute

@dataclass
class Config:
    """Main configuration class."""
    # Sub-configurations with proper default factories
    trading: TradingConfig = field(default_factory=default_trading_config)
    risk: RiskConfig = field(default_factory=default_risk_config)
    monitor: MonitorConfig = field(default_factory=lambda: MonitorConfig())
    
    # API Keys and URLs
    telegram_token: str = field(default_factory=lambda: os.getenv('TELEGRAM_BOT_TOKEN', ''))
    solana_rpc_url: str = field(default_factory=lambda: os.getenv('SOLANA_RPC_URL', ''))
    wallet_id: str = field(default_factory=lambda: os.getenv('WALLET_ID', ''))
    wallet_seed_phrase: str = field(default_factory=lambda: os.getenv('WALLET_SEED_PHRASE', ''))
    admin_chat_id: str = field(default_factory=lambda: os.getenv('ADMIN_CHAT_ID', ''))
    birdeye_api_key: str = field(default_factory=lambda: os.getenv('BIRDEYE_API_KEY', ''))

    def validate(self) -> bool:
        """Validate the configuration."""
        if not self.telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment")
        if not self.solana_rpc_url:
            raise ValueError("SOLANA_RPC_URL not found in environment")
        if not self.wallet_id:
            raise ValueError("WALLET_ID not found in environment")
        if not self.wallet_seed_phrase:
            raise ValueError("WALLET_SEED_PHRASE not found in environment")
        return True

# Global configuration instance
config = Config()
