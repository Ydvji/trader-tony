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

@dataclass
class RiskConfig:
    """Risk management configuration."""
    min_holders: int = 10
    max_risk_score: int = 70
    min_verification_score: int = 80
    suspicious_pattern_threshold: float = 50.0  # 50% price change threshold

from dataclasses import field

def default_trading_config() -> TradingConfig:
    return TradingConfig()

def default_risk_config() -> RiskConfig:
    return RiskConfig()

@dataclass
class Config:
    """Main configuration class."""
    # Sub-configurations with proper default factories
    trading: TradingConfig = field(default_factory=default_trading_config)
    risk: RiskConfig = field(default_factory=default_risk_config)
    
    # API Keys and URLs
    telegram_token: str = field(default_factory=lambda: os.getenv('TELEGRAM_BOT_TOKEN', ''))
    solana_rpc_url: str = field(default_factory=lambda: os.getenv('SOLANA_RPC_URL', ''))
    wallet_id: str = field(default_factory=lambda: os.getenv('WALLET_ID', ''))
    wallet_seed_phrase: str = field(default_factory=lambda: os.getenv('WALLET_SEED_PHRASE', ''))

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
