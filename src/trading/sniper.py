"""
Raydium sniping module for Trader Tony.
Handles token info and trading functionality.
"""
from solana.rpc.api import Client
from solders.pubkey import Pubkey
from src.utils.wallet import Wallet

class Sniper:
    def __init__(self, wallet: Wallet):
        """Initialize sniper with wallet"""
        self.wallet = wallet
        self.client = wallet.client
        self.RAYDIUM_PROGRAM_ID = Pubkey.from_string('675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8')

    def get_token_info(self, token_input: str) -> dict:
        """Get token information from address or URL"""
        try:
            # Extract token address from input (could be URL or address)
            token_address = self._extract_token_address(token_input)
            
            # Get token data from Raydium pool
            pool_data = self._get_pool_data(token_address)
            
            # Get price and liquidity info
            price = self._calculate_price(pool_data)
            liquidity = self._calculate_liquidity(pool_data)
            
            # Get token metadata
            metadata = self._get_token_metadata(token_address)
            
            return {
                'name': metadata['name'],
                'symbol': metadata['symbol'],
                'price': price,
                'market_cap': price * metadata['supply'],
                'volume_24h': self._get_24h_volume(token_address),
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

    def _get_pool_data(self, token_address: str) -> dict:
        """Get Raydium pool data for token"""
        try:
            # Get program accounts filtered for token
            accounts = self.client.get_program_accounts(
                self.RAYDIUM_PROGRAM_ID,
                encoding="base64",
                filters=[
                    {"memcmp": {"offset": 72, "bytes": token_address}}
                ]
            )
            
            if not accounts or not accounts['result']:
                raise Exception("No liquidity pool found")
                
            return accounts['result'][0]
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

    def _calculate_liquidity(self, pool_data: dict) -> float:
        """Calculate pool liquidity in USD"""
        try:
            # Get SOL price in USD
            sol_price = self._get_sol_price()
            
            # Extract SOL liquidity from pool
            data = pool_data['account']['data'][0]
            sol_liquidity = int.from_bytes(data[208:216], 'little') / 1e9
            
            # Calculate total liquidity in USD
            return sol_liquidity * sol_price * 2  # Multiply by 2 for both sides of pool
        except Exception as e:
            raise Exception(f"Failed to calculate liquidity: {str(e)}")

    def _get_sol_price(self) -> float:
        """Get current SOL price in USD"""
        try:
            # Use Birdeye API for price
            response = self.client.get_account_info(
                Pubkey.from_string('So11111111111111111111111111111111111111112')
            )
            if not response or not response['result']:
                return 0.0
                
            # Extract price from account data
            # This is simplified - you'd want to use a proper price oracle
            return 100.0  # Placeholder - implement real price fetching
        except Exception:
            return 100.0  # Default fallback price

    def _get_token_metadata(self, token_address: str) -> dict:
        """Get token metadata"""
        try:
            # Get token account info
            response = self.client.get_account_info(
                Pubkey.from_string(token_address),
                encoding="jsonParsed"
            )
            
            if not response or not response['result']:
                raise Exception("Token not found")
                
            data = response['result']['value']
            
            return {
                'name': data.get('data', {}).get('name', 'Unknown Token'),
                'symbol': data.get('data', {}).get('symbol', 'UNKNOWN'),
                'supply': float(data.get('data', {}).get('supply', 0))
            }
        except Exception as e:
            # Return default metadata if fetch fails
            return {
                'name': 'Unknown Token',
                'symbol': 'UNKNOWN',
                'supply': 0
            }

    def _get_24h_volume(self, token_address: str) -> float:
        """Get 24h trading volume"""
        try:
            # This would normally fetch from an API
            # For now return placeholder
            return 10000.0
        except Exception:
            return 0.0
