"""
Token monitoring and alert system for Trader Tony.
Based on the monitoring system from trading-agent.
"""
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass
from datetime import datetime
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey as PublicKey

from ..utils.config import config

logger = logging.getLogger(__name__)

@dataclass
class TokenAlert:
    """Represents a token alert."""
    token_address: str
    alert_type: str
    details: str
    timestamp: datetime
    risk_level: Optional[int] = None
    price_change: Optional[float] = None
    liquidity_change: Optional[float] = None

class TokenMonitor:
    """Monitors tokens for various events and conditions."""
    
    def __init__(self, client: AsyncClient):
        """Initialize the token monitor."""
        self.client = client
        self.active_monitors: Dict[str, Dict] = {}
        self.alerts: List[TokenAlert] = []

    async def start_monitoring(self, token_address: str, params: Dict) -> bool:
        """Start monitoring a token with specified parameters."""
        try:
            # Validate token
            token_pubkey = PublicKey(token_address)
            
            # Set up monitoring parameters
            monitor_config = {
                'token_address': token_address,
                'price_threshold': params.get('price_threshold', 5.0),  # 5% change
                'liquidity_threshold': params.get('liquidity_threshold', 10.0),  # 10% change
                'volume_threshold': params.get('volume_threshold', 100.0),  # 100% change
                'check_interval': params.get('check_interval', 60),  # 60 seconds
                'last_check': datetime.now(),
                'last_price': await self.get_token_price(token_address),
                'last_liquidity': await self.get_token_liquidity(token_address)
            }

            self.active_monitors[token_address] = monitor_config
            logger.info(f"Started monitoring {token_address}")
            return True

        except Exception as e:
            logger.error(f"Error starting monitor for {token_address}: {str(e)}")
            return False

    async def stop_monitoring(self, token_address: str) -> bool:
        """Stop monitoring a token."""
        if token_address in self.active_monitors:
            del self.active_monitors[token_address]
            logger.info(f"Stopped monitoring {token_address}")
            return True
        return False

    async def check_token(self, token_address: str) -> List[TokenAlert]:
        """Check a token for alert conditions."""
        if token_address not in self.active_monitors:
            return []

        config = self.active_monitors[token_address]
        alerts = []

        try:
            # Get current metrics
            current_price = await self.get_token_price(token_address)
            current_liquidity = await self.get_token_liquidity(token_address)

            # Check price change
            if current_price and config['last_price']:
                price_change = ((current_price - config['last_price']) / config['last_price']) * 100
                if abs(price_change) >= config['price_threshold']:
                    alerts.append(TokenAlert(
                        token_address=token_address,
                        alert_type='PRICE_CHANGE',
                        details=f"Price changed by {price_change:.2f}%",
                        timestamp=datetime.now(),
                        price_change=price_change
                    ))

            # Check liquidity change
            if current_liquidity and config['last_liquidity']:
                liquidity_change = ((current_liquidity - config['last_liquidity']) / config['last_liquidity']) * 100
                if abs(liquidity_change) >= config['liquidity_threshold']:
                    alerts.append(TokenAlert(
                        token_address=token_address,
                        alert_type='LIQUIDITY_CHANGE',
                        details=f"Liquidity changed by {liquidity_change:.2f}%",
                        timestamp=datetime.now(),
                        liquidity_change=liquidity_change
                    ))

            # Update last values
            config['last_price'] = current_price
            config['last_liquidity'] = current_liquidity
            config['last_check'] = datetime.now()

            # Store alerts
            self.alerts.extend(alerts)
            return alerts

        except Exception as e:
            logger.error(f"Error checking token {token_address}: {str(e)}")
            return []

    async def get_token_price(self, token_address: str) -> Optional[float]:
        """Get current token price."""
        # Implementation depends on Raydium API
        # This is a placeholder
        return 0.0

    async def get_token_liquidity(self, token_address: str) -> Optional[float]:
        """Get current token liquidity."""
        # Implementation depends on Raydium API
        # This is a placeholder
        return 0.0

    def get_recent_alerts(self, limit: int = 10) -> List[TokenAlert]:
        """Get recent alerts."""
        return sorted(self.alerts, key=lambda x: x.timestamp, reverse=True)[:limit]

    def format_alert_message(self, alert: TokenAlert) -> str:
        """Format an alert for Telegram message."""
        message = f"""
🚨 {alert.alert_type}

Token: {alert.token_address}
Time: {alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
Details: {alert.details}
"""
        if alert.price_change is not None:
            message += f"Price Change: {'🔴' if alert.price_change < 0 else '🟢'} {alert.price_change:.2f}%\n"
        
        if alert.liquidity_change is not None:
            message += f"Liquidity Change: {'🔴' if alert.liquidity_change < 0 else '🟢'} {alert.liquidity_change:.2f}%\n"
        
        if alert.risk_level is not None:
            message += f"Risk Level: {'🔴 HIGH' if alert.risk_level > 70 else '🟡 MEDIUM' if alert.risk_level > 30 else '🟢 LOW'}\n"

        return message
