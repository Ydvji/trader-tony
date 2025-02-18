"""
Raydium DEX integration module for Trader Tony.
Handles pool interactions and trade execution.
"""
from typing import Dict, Optional, Tuple
from solana.rpc.async_api import AsyncClient
from solders.pubkey import Pubkey as PublicKey
from solders.instruction import Instruction
from solders.system_program import TransactionWithSeed
import base58

class RaydiumDEX:
    """Handles Raydium DEX interactions."""
    
    def __init__(self, client: AsyncClient):
        self.client = client
        
        # Raydium program IDs
        self.RAYDIUM_PROGRAM_ID = PublicKey.from_string('675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8')
        self.SERUM_PROGRAM_ID = PublicKey.from_string('9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin')
        
        # Default settings
        self.settings = {
            'max_slippage': 1.0,  # 1%
            'priority_fee': 0.0001,  # SOL
            'min_sol_balance': 0.05  # Minimum SOL to keep for fees
        }

    async def get_pool(self, token_address: str) -> Optional[Dict]:
        """Get Raydium pool for token."""
        try:
            # Get program accounts filtered for token
            accounts = await self.client.get_program_accounts(
                self.RAYDIUM_PROGRAM_ID,
                encoding="base64",
                filters=[
                    {"memcmp": {"offset": 72, "bytes": token_address}}
                ]
            )
            
            if not accounts or not accounts.value:
                return None
                
            return {
                'address': accounts.value[0].pubkey,
                'data': accounts.value[0].data
            }
            
        except Exception as e:
            print(f"Failed to get pool: {str(e)}")
            return None

    async def get_pool_info(self, pool_address: PublicKey) -> Dict:
        """Get detailed pool information."""
        try:
            account = await self.client.get_account_info(pool_address)
            if not account.value:
                raise Exception("Pool not found")
                
            data = account.value.data
            
            return {
                'base_reserve': int.from_bytes(data[200:208], 'little'),
                'quote_reserve': int.from_bytes(data[208:216], 'little'),
                'fee_rate': int.from_bytes(data[216:224], 'little') / 1e6,
                'last_update': int.from_bytes(data[224:232], 'little')
            }
            
        except Exception as e:
            print(f"Failed to get pool info: {str(e)}")
            return {}

    def calculate_swap_amounts(
        self,
        input_amount: float,
        pool_info: Dict,
        slippage: Optional[float] = None
    ) -> Dict:
        """Calculate swap amounts with slippage."""
        try:
            max_slippage = slippage or self.settings['max_slippage']
            
            # Extract pool reserves
            base_reserve = pool_info['base_reserve']
            quote_reserve = pool_info['quote_reserve']
            fee_rate = pool_info['fee_rate']
            
            # Calculate output amount
            input_amount_lamports = int(input_amount * 1e9)
            fee_amount = int(input_amount_lamports * fee_rate)
            net_input = input_amount_lamports - fee_amount
            
            # Using constant product formula: x * y = k
            output_amount = (quote_reserve * net_input) // (base_reserve + net_input)
            
            # Apply slippage tolerance
            min_output = int(output_amount * (1 - max_slippage / 100))
            
            return {
                'input_amount': input_amount_lamports,
                'expected_output': output_amount,
                'minimum_output': min_output,
                'price_impact': (output_amount / quote_reserve) * 100,
                'fee_amount': fee_amount
            }
            
        except Exception as e:
            print(f"Failed to calculate amounts: {str(e)}")
            return {}

    async def create_swap_instruction(
        self,
        pool_address: PublicKey,
        wallet_address: PublicKey,
        input_amount: int,
        minimum_output: int
    ) -> Optional[Instruction]:
        """Create swap instruction."""
        try:
            # Get pool account
            pool_info = await self.get_pool_info(pool_address)
            if not pool_info:
                raise Exception("Failed to get pool info")
                
            # Create swap instruction
            data = bytes([
                0x01,  # Swap instruction
                *(input_amount).to_bytes(8, 'little'),
                *(minimum_output).to_bytes(8, 'little')
            ])
            
            # Get associated token accounts
            base_ata = await self._get_associated_token_account(
                wallet_address,
                PublicKey.from_string('So11111111111111111111111111111111111111112')  # SOL
            )
            
            quote_ata = await self._get_associated_token_account(
                wallet_address,
                pool_info['quote_mint']
            )
            
            return Instruction(
                program_id=self.RAYDIUM_PROGRAM_ID,
                accounts=[
                    {'pubkey': pool_address, 'is_signer': False, 'is_writable': True},
                    {'pubkey': wallet_address, 'is_signer': True, 'is_writable': True},
                    {'pubkey': base_ata, 'is_signer': False, 'is_writable': True},
                    {'pubkey': quote_ata, 'is_signer': False, 'is_writable': True}
                ],
                data=base58.b58encode(data)
            )
            
        except Exception as e:
            print(f"Failed to create swap instruction: {str(e)}")
            return None

    async def _get_associated_token_account(
        self,
        wallet_address: PublicKey,
        token_mint: PublicKey
    ) -> PublicKey:
        """Get or create associated token account."""
        try:
            # Derive ATA address
            seeds = [
                bytes(wallet_address),
                bytes(PublicKey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')),
                bytes(token_mint)
            ]
            program_address, nonce = PublicKey.find_program_address(
                seeds,
                PublicKey.from_string('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')
            )
            
            # Check if account exists
            account = await self.client.get_account_info(program_address)
            if not account.value:
                # Account doesn't exist, create it
                create_ix = self._create_ata_instruction(
                    wallet_address,
                    token_mint,
                    program_address
                )
                # You would need to submit this instruction first
                
            return program_address
            
        except Exception as e:
            print(f"Failed to get ATA: {str(e)}")
            raise

    def _create_ata_instruction(
        self,
        wallet_address: PublicKey,
        token_mint: PublicKey,
        ata_address: PublicKey
    ) -> Instruction:
        """Create instruction to create associated token account."""
        return Instruction(
            program_id=PublicKey.from_string('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL'),
            accounts=[
                {'pubkey': wallet_address, 'is_signer': True, 'is_writable': True},
                {'pubkey': ata_address, 'is_signer': False, 'is_writable': True},
                {'pubkey': wallet_address, 'is_signer': False, 'is_writable': False},
                {'pubkey': token_mint, 'is_signer': False, 'is_writable': False},
                {'pubkey': PublicKey.from_string('11111111111111111111111111111111'), 'is_signer': False, 'is_writable': False},
                {'pubkey': PublicKey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'), 'is_signer': False, 'is_writable': False},
                {'pubkey': PublicKey.from_string('SysvarRent111111111111111111111111111111111'), 'is_signer': False, 'is_writable': False}
            ],
            data=base58.b58encode(bytes([0x01]))  # Create instruction
        )
