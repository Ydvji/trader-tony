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

@dataclass
class Config:
    """Main configuration class."""
    # API Keys and URLs
    telegram_token: str = os.getenv('TELEGRAM_BOT_TOKEN', '')
    solana_rpc_url: str = os.getenv('SOLANA_RPC_URL', '')
    wallet_private_key: str = os.getenv('WALLET_PRIVATE_KEY', '')
    
    # Sub-configurations
    trading: TradingConfig = TradingConfig()
    risk: RiskConfig = RiskConfig()

    def validate(self) -> bool:
        """Validate the configuration."""
        if not self.telegram_token:
            raise ValueError("TELEGRAM_BOT_TOKEN not found in environment")
        if not self.solana_rpc_url:
            raise ValueError("SOLANA_RPC_URL not found in environment")
        if not self.wallet_private_key:
            raise ValueError("WALLET_PRIVATE_KEY not found in environment")
        return True

# Global configuration instance
config = Config()
