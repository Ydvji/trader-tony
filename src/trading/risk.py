"""
Risk analysis module for Trader Tony.
Handles token risk assessment and pattern detection.
"""
from dataclasses import dataclass
from typing import List, Dict, Optional
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey as PublicKey

from utils.config import config

@dataclass
class RiskAnalysis:
    """Results of token risk analysis."""
    is_honeypot: bool = False
    has_low_liquidity: bool = False
    has_suspicious_activity: bool = False
    risk_level: int = 0
    details: str = ""

@dataclass
class Trade:
    """Represents a trading transaction."""
    block_number: int
    transaction_hash: str
    token_address: str
    type: str  # 'BUY' or 'SELL'
    value: float
    price: float
    timestamp: int

class RiskAnalyzer:
    """Analyzes token risks and trading patterns."""
    
    def __init__(self, client: AsyncClient):
        self.client = client
        self.config = config.risk

    async def analyze_token_risks(self, token_address: str) -> RiskAnalysis:
        """Analyze various risk factors for a token."""
        risks = RiskAnalysis()

        # Check contract code verification
        program_info = await self.client.get_account_info(PublicKey(token_address))
        if not program_info.value:
            risks.risk_level += 50  # Huge red flag if no verified code
            risks.details += "No verified contract code found. "

        # Check holder distribution
        holders = await self.get_token_holders(token_address)
        if len(holders) < self.config.min_holders:
            risks.risk_level += 30  # Very few holders is suspicious
            risks.details += f"Only {len(holders)} holders found. "

        # Check liquidity metrics
        liquidity = await self.get_liquidity_metrics(token_address)
        if liquidity < config.trading.min_liquidity:
            risks.has_low_liquidity = True
            risks.risk_level += 20
            risks.details += f"Low liquidity (${liquidity}). "

        # Check for suspicious trading patterns
        recent_trades = await self.get_recent_trades(token_address)
        patterns = self.analyze_trading_patterns(recent_trades)
        
        if patterns.get('has_pump_and_dump'):
            risks.has_suspicious_activity = True
            risks.risk_level += 40
            risks.details += "Pump and dump pattern detected. "

        # Honeypot detection
        can_sell = await self.test_sellability(token_address)
        if not can_sell:
            risks.is_honeypot = True
            risks.risk_level += 100
            risks.details += "Cannot sell token (possible honeypot). "

        return risks

    async def get_token_holders(self, token_address: str) -> List[str]:
        """Get list of token holders."""
        # Implementation depends on Solana API
        # This is a placeholder
        return []

    async def get_liquidity_metrics(self, token_address: str) -> float:
        """Get token liquidity in USD."""
        # Implementation depends on Raydium API
        # This is a placeholder
        return 0.0

    async def get_recent_trades(self, token_address: str) -> List[Trade]:
        """Get recent trading history."""
        # Implementation depends on Raydium API
        # This is a placeholder
        return []

    async def test_sellability(self, token_address: str) -> bool:
        """Test if token can be sold."""
        # Implementation depends on Raydium API
        # This is a placeholder
        return True

    def analyze_trading_patterns(self, trades: List[Trade]) -> Dict[str, bool]:
        """Analyze trading patterns for suspicious activity."""
        return {
            'has_pump_and_dump': self.detect_pump_and_dump(trades),
            'has_sandwich_pattern': self.detect_sandwich_patterns(trades),
            'has_flash_loan_pattern': self.detect_flash_loan_pattern(trades),
            'only_creator_selling': self.check_creator_only_sells(trades)
        }

    def detect_pump_and_dump(self, trades: List[Trade]) -> bool:
        """Look for sudden price increases followed by large sells."""
        if not trades:
            return False

        suspicious_pattern = False
        price_changes = self.calculate_price_changes(trades)
        
        for i in range(len(price_changes) - 1):
            if (price_changes[i] > self.config.suspicious_pattern_threshold and 
                trades[i + 1].type == 'SELL' and
                trades[i + 1].value > trades[i].value * 2):
                suspicious_pattern = True
                break
        
        return suspicious_pattern

    def detect_flash_loan_pattern(self, trades: List[Trade]) -> bool:
        """Look for large volume spikes within single blocks."""
        if not trades:
            return False

        suspicious_blocks = set()
        
        for trade in trades:
            block_volume = self.calculate_block_volume(trade.block_number, trades)
            average_volume = self.calculate_average_volume(trades, 100)  # 100 block average
            
            if block_volume > average_volume * 10:  # Volume spike threshold
                suspicious_blocks.add(trade.block_number)
        
        return len(suspicious_blocks) > 0

    @staticmethod
    def calculate_price_changes(trades: List[Trade]) -> List[float]:
        """Calculate percentage price changes between trades."""
        if not trades:
            return []
            
        changes = []
        for i in range(1, len(trades)):
            prev_price = trades[i-1].price
            curr_price = trades[i].price
            change = ((curr_price - prev_price) / prev_price) * 100
            changes.append(change)
        return changes

    @staticmethod
    def calculate_block_volume(block_number: int, trades: List[Trade]) -> float:
        """Calculate total trading volume in a specific block."""
        return sum(t.value for t in trades if t.block_number == block_number)

    @staticmethod
    def calculate_average_volume(trades: List[Trade], blocks: int) -> float:
        """Calculate average volume over a number of blocks."""
        if not trades:
            return 0.0
            
        total_volume = sum(t.value for t in trades[:blocks])
        return total_volume / blocks if blocks > 0 else 0

    @staticmethod
    def detect_sandwich_patterns(trades: List[Trade]) -> bool:
        """Detect potential sandwich attack patterns."""
        # Implementation placeholder
        return False

    @staticmethod
    def check_creator_only_sells(trades: List[Trade]) -> bool:
        """Check if only the creator is selling."""
        # Implementation placeholder
        return False
