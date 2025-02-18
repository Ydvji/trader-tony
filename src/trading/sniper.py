"""
Raydium sniping module for Trader Tony.
Handles token info, sniping, and trading functionality.
"""
import asyncio
import json
import random
from typing import Dict, Optional, Tuple
from solana.rpc.async_api import AsyncClient
from solana.rpc.websocket_api import connect
from solana.rpc.commitment import Commitment
from solders.pubkey import Pubkey
from solders.system_program import TransactionWithSeed
from solders.instruction import Instruction
from base58 import b58encode, b58decode
from src.utils.wallet import Wallet
from src.trading.risk import RiskAnalyzer

class Sniper:
    def __init__(self, wallet: Wallet):
        """Initialize sniper with wallet"""
        self.wallet = wallet
        self.client = wallet.client
        self.ws_client = None
        self.risk_analyzer = RiskAnalyzer(self.client)
        
        # Raydium program IDs
        self.RAYDIUM_PROGRAM_ID = Pubkey.from_string('675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8')
        self.POOL_PROGRAM_ID = Pubkey.from_string('9KEPoZmtHUrBbhWN1v1KWLMkkvwY6WLtAVUCPRtRjP4z')
        
        # Mempool monitoring
        self.monitoring = False
        self.new_pool_callbacks = []
        
        # Default sniping settings
        self.settings = {
            'max_slippage': 1.0,  # 1%
            'priority_fee': 0.0001,  # SOL
            'min_liquidity': 1000,  # USD
            'max_buy_amount': 1.0,  # SOL
            'take_profit': 50.0,  # 50%
            'stop_loss': 20.0,  # 20%
            'anti_mev': True
        }

    async def start_mempool_monitoring(self):
        """Start monitoring mempool for new pools"""
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

    async def stop_mempool_monitoring(self):
        """Stop mempool monitoring"""
        self.monitoring = False
        if self.ws_client:
            await self.ws_client.close()
            self.ws_client = None

    async def _handle_new_pool(self, params: Dict):
        """Handle new pool notification"""
        try:
            # Extract pool data
            pool_data = params['result']['value']
            token_address = self._extract_token_from_pool(pool_data)
            
            if not token_address:
                return
                
            # Quick analysis
            analysis = await self._analyze_new_pool(token_address, pool_data)
            
            # Notify callbacks
            for callback in self.new_pool_callbacks:
                await callback(token_address, analysis)
                
        except Exception as e:
            print(f"Error handling new pool: {str(e)}")

    async def snipe_token(self, token_address: str, amount: float, settings: Optional[Dict] = None) -> Dict:
        """Snipe a token with given settings"""
        try:
            # Use provided settings or defaults
            snipe_settings = {**self.settings, **(settings or {})}
            
            # Pre-launch analysis
            analysis = await self._analyze_new_pool(token_address, None)
            if not analysis['safe']:
                return {
                    'success': False,
                    'error': 'Token failed safety checks',
                    'details': analysis
                }
                
            # Prepare transaction
            tx = await self._prepare_buy_transaction(
                token_address,
                amount,
                snipe_settings['max_slippage'],
                snipe_settings['priority_fee'],
                snipe_settings['anti_mev']
            )
            
            # Execute buy
            signature = await self.wallet.send_transaction(tx)
            if not signature:
                return {
                    'success': False,
                    'error': 'Failed to send transaction'
                }
                
            return {
                'success': True,
                'signature': signature,
                'token': token_address,
                'amount': amount,
                'settings': snipe_settings
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    async def get_token_info(self, token_input: str) -> dict:
        """Get token information from address or URL"""
        try:
            # Extract token address from input (could be URL or address)
            token_address = self._extract_token_address(token_input)
            
            # Get token data from Raydium pool
            pool_data = await self._get_pool_data(token_address)
            
            # Get price and liquidity info
            price = self._calculate_price(pool_data)
            liquidity = await self._calculate_liquidity(pool_data)
            
            # Get token metadata
            metadata = await self._get_token_metadata(token_address)
            
            return {
                'name': metadata['name'],
                'symbol': metadata['symbol'],
                'price': price,
                'market_cap': price * metadata['supply'],
                'volume_24h': await self._get_24h_volume(token_address),
                'liquidity': liquidity,
                'chart_url': f"https://birdeye.so/token/{token_address}?chain=solana"
            }
        except Exception as e:
            raise Exception(f"Failed to get token info: {str(e)}")

    def _extract_token_address(self, token_input: str) -> str:
        """Extract token address from input (URL or address)"""
        # Handle different input formats
        if token_input.startswith('http'):
            # Extract from URLs like birdeye.so/token/[address]
            if 'birdeye.so/token/' in token_input:
                return token_input.split('token/')[-1].split('?')[0]
            # Extract from URLs like dexscreener.com/solana/[address]
            elif 'dexscreener.com/solana/' in token_input:
                return token_input.split('solana/')[-1].split('?')[0]
            # Add more URL patterns as needed
        
        # If input is already an address
        return token_input

    async def _get_pool_data(self, token_address: str) -> dict:
        """Get Raydium pool data for token"""
        try:
            # Get program accounts filtered for token
            response = await self.client.get_program_accounts(
                self.RAYDIUM_PROGRAM_ID,
                encoding="base64",
                filters=[
                    {"memcmp": {"offset": 72, "bytes": token_address}}
                ]
            )
            
            if not response.value:
                raise Exception("No liquidity pool found")
                
            return response.value[0]
        except Exception as e:
            raise Exception(f"Failed to get pool data: {str(e)}")

    def _calculate_price(self, pool_data: dict) -> float:
        """Calculate token price from pool data"""
        try:
            # Extract reserves from pool data
            data = pool_data['account']['data'][0]
            base_reserve = int.from_bytes(data[200:208], 'little')
            quote_reserve = int.from_bytes(data[208:216], 'little')
            
            if base_reserve == 0:
                return 0.0
                
            # Calculate price in SOL
            return quote_reserve / base_reserve * 1e9
        except Exception as e:
            raise Exception(f"Failed to calculate price: {str(e)}")

    async def _calculate_liquidity(self, pool_data: dict) -> float:
        """Calculate pool liquidity in USD"""
        try:
            # Get SOL price in USD
            sol_price = await self._get_sol_price()
            
            # Extract SOL liquidity from pool
            data = pool_data['account']['data'][0]
            sol_liquidity = int.from_bytes(data[208:216], 'little') / 1e9
            
            # Calculate total liquidity in USD
            return sol_liquidity * sol_price * 2  # Multiply by 2 for both sides of pool
        except Exception as e:
            raise Exception(f"Failed to calculate liquidity: {str(e)}")

    async def _get_sol_price(self) -> float:
        """Get current SOL price in USD"""
        try:
            # Use Birdeye API for price
            response = await self.client.get_account_info(
                Pubkey.from_string('So11111111111111111111111111111111111111112')
            )
            if not response.value:
                return 0.0
                
            # Extract price from account data
            # This is simplified - you'd want to use a proper price oracle
            return 100.0  # Placeholder - implement real price fetching
        except Exception:
            return 100.0  # Default fallback price

    async def _get_token_metadata(self, token_address: str) -> dict:
        """Get token metadata"""
        try:
            # Get token account info
            response = await self.client.get_account_info(
                Pubkey.from_string(token_address),
                encoding="jsonParsed"
            )
            
            if not response.value:
                raise Exception("Token not found")
                
            data = response.value
            
            return {
                'name': data.get('data', {}).get('parsed', {}).get('info', {}).get('name', 'Unknown Token'),
                'symbol': data.get('data', {}).get('parsed', {}).get('info', {}).get('symbol', 'UNKNOWN'),
                'supply': float(data.get('data', {}).get('parsed', {}).get('info', {}).get('supply', 0))
            }
        except Exception as e:
            # Return default metadata if fetch fails
            return {
                'name': 'Unknown Token',
                'symbol': 'UNKNOWN',
                'supply': 0
            }

    async def _get_24h_volume(self, token_address: str) -> float:
        """Get 24h trading volume"""
        try:
            # This would normally fetch from an API
            # For now return placeholder
            return 10000.0
        except Exception:
            return 0.0

    def _add_anti_mev_protection(self, instructions: list) -> list:
        """Add anti-MEV protection to transaction"""
        # Add random compute units instruction
        compute_units = random.randint(100000, 1000000)
        instructions.insert(0, self._create_compute_budget_ix(compute_units))
        
        # Add random priority fee variation
        fee_variation = random.uniform(0.9, 1.1)
        instructions.insert(1, self._create_priority_fee_ix(
            self.settings['priority_fee'] * fee_variation
        ))
        
        return instructions

    def _create_compute_budget_ix(self, units: int) -> Instruction:
        """Create compute budget instruction"""
        return Instruction(
            program_id=Pubkey.from_string('ComputeBudget111111111111111111111111111111'),
            accounts=[],
            data=b58encode(bytes([0x01]) + units.to_bytes(4, 'little'))
        )

    def _create_priority_fee_ix(self, fee: float) -> Instruction:
        """Create priority fee instruction"""
        fee_lamports = int(fee * 1e9)
        return Instruction(
            program_id=Pubkey.from_string('ComputeBudget111111111111111111111111111111'),
            accounts=[],
            data=b58encode(bytes([0x02]) + fee_lamports.to_bytes(8, 'little'))
        )
