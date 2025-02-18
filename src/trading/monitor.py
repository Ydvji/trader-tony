"""
Monitoring module for Trader Tony.
Handles mempool monitoring and new pool detection.
"""
import asyncio
import json
from typing import Dict, List, Optional, Callable
from solana.rpc.async_api import AsyncClient
from solana.rpc.websocket_api import connect
from solana.rpc.commitment import Commitment
from solders.pubkey import Pubkey as PublicKey
from src.utils.config import config

class TokenMonitor:
    """Monitors mempool and new token launches."""
    
    def __init__(self, client: AsyncClient):
        self.client = client
        self.ws_client = None
        self.monitoring = False
        self.callbacks: List[Callable] = []
        
        # Raydium program IDs
        self.RAYDIUM_PROGRAM_ID = PublicKey.from_string('675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8')
        self.POOL_PROGRAM_ID = PublicKey.from_string('9KEPoZmtHUrBbhWN1v1KWLMkkvwY6WLtAVUCPRtRjP4z')
        
        # Monitoring settings
        self.settings = {
            'min_liquidity': config.trading.min_liquidity,
            'min_holders': config.risk.min_holders,
            'check_interval': 1000,  # 1 second
            'price_change_threshold': 5.0,  # 5%
            'volume_change_threshold': 100.0  # 100%
        }

    async def start_monitoring(self):
        """Start monitoring mempool for new pools."""
        if self.monitoring:
            return
            
        self.monitoring = True
        self.ws_client = await connect("wss://api.mainnet-beta.solana.com")
        
        # Subscribe to program subscription
        await self.ws_client.program_subscribe(
            self.POOL_PROGRAM_ID,
            commitment=Commitment("confirmed"),
            encoding="base64"
        )
        
        # Start processing notifications
        while self.monitoring:
            try:
                msg = await self.ws_client.recv()
                if msg and 'params' in msg:
                    await self._handle_new_pool(msg['params'])
            except Exception as e:
                print(f"Mempool monitoring error: {str(e)}")
                await asyncio.sleep(1)

    async def stop_monitoring(self):
        """Stop mempool monitoring."""
        self.monitoring = False
        if self.ws_client:
            await self.ws_client.close()
            self.ws_client = None

    def add_callback(self, callback: Callable):
        """Add callback for new pool notifications."""
        self.callbacks.append(callback)

    def remove_callback(self, callback: Callable):
        """Remove callback from notifications."""
        if callback in self.callbacks:
            self.callbacks.remove(callback)

    async def _handle_new_pool(self, params: Dict):
        """Handle new pool notification."""
        try:
            # Extract pool data
            pool_data = params['result']['value']
            token_address = self._extract_token_from_pool(pool_data)
            
            if not token_address:
                return
                
            # Quick analysis
            pool_info = await self._analyze_pool(token_address, pool_data)
            
            # Notify callbacks if pool meets criteria
            if self._meets_criteria(pool_info):
                for callback in self.callbacks:
                    await callback(token_address, pool_info)
                    
        except Exception as e:
            print(f"Error handling new pool: {str(e)}")

    def _extract_token_from_pool(self, pool_data: Dict) -> Optional[str]:
        """Extract token address from pool data."""
        try:
            # Extract token mint from pool account data
            data = pool_data['data'][0]
            token_offset = 72  # Token mint offset in pool data
            token_bytes = data[token_offset:token_offset + 32]
            return str(PublicKey.from_bytes(token_bytes))
        except Exception:
            return None

    async def _analyze_pool(self, token_address: str, pool_data: Dict) -> Dict:
        """Analyze new pool data."""
        try:
            # Extract initial liquidity
            liquidity = self._calculate_initial_liquidity(pool_data)
            
            # Get token metadata
            metadata = await self._get_token_metadata(token_address)
            
            # Calculate initial price
            price = self._calculate_initial_price(pool_data)
            
            return {
                'token_address': token_address,
                'token_name': metadata.get('name', 'Unknown'),
                'token_symbol': metadata.get('symbol', 'UNKNOWN'),
                'initial_liquidity': liquidity,
                'initial_price': price,
                'timestamp': pool_data.get('blockTime', 0)
            }
            
        except Exception as e:
            return {
                'token_address': token_address,
                'error': str(e)
            }

    def _calculate_initial_liquidity(self, pool_data: Dict) -> float:
        """Calculate initial pool liquidity in USD."""
        try:
            data = pool_data['data'][0]
            sol_reserve = int.from_bytes(data[208:216], 'little') / 1e9
            return sol_reserve * 100.0  # Assuming $100 SOL price
        except Exception:
            return 0.0

    def _calculate_initial_price(self, pool_data: Dict) -> float:
        """Calculate initial token price."""
        try:
            data = pool_data['data'][0]
            base_reserve = int.from_bytes(data[200:208], 'little')
            quote_reserve = int.from_bytes(data[208:216], 'little')
            
            if base_reserve == 0:
                return 0.0
                
            return quote_reserve / base_reserve * 1e9
        except Exception:
            return 0.0

    async def _get_token_metadata(self, token_address: str) -> Dict:
        """Get token metadata."""
        try:
            response = await self.client.get_account_info(
                PublicKey(token_address),
                encoding="jsonParsed"
            )
            
            if not response.value:
                return {}
                
            data = response.value
            
            return {
                'name': data.get('data', {}).get('parsed', {}).get('info', {}).get('name', 'Unknown'),
                'symbol': data.get('data', {}).get('parsed', {}).get('info', {}).get('symbol', 'UNKNOWN'),
                'supply': float(data.get('data', {}).get('parsed', {}).get('info', {}).get('supply', 0))
            }
        except Exception:
            return {}

    def _meets_criteria(self, pool_info: Dict) -> bool:
        """Check if pool meets monitoring criteria."""
        if 'error' in pool_info:
            return False
            
        return (
            pool_info['initial_liquidity'] >= self.settings['min_liquidity'] and
            pool_info['initial_price'] > 0
        )
