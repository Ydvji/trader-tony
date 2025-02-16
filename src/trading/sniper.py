"""
Raydium sniping module for Trader Tony.
Handles token sniping with risk analysis and position management.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import asyncio
import random
from solana.rpc.async_api import AsyncClient
from solana.transaction import Transaction, AccountMeta
from solders.system_program import transfer, TransferParams
from solders.pubkey import Pubkey as PublicKey
from solders.keypair import Keypair

from trading.risk import RiskAnalyzer
from utils.config import config

@dataclass
class SnipeConfig:
    """Configuration for a snipe operation."""
    token_address: str
    buy_amount: float
    take_profit: float
    stop_loss: float
    slippage: float
    priority_fee: Optional[float] = None
    anti_mev: bool = True
    trailing_take_profit: Optional[float] = None
    trailing_stop_loss: Optional[float] = None

class RaydiumSniper:
    """Implements Raydium sniping functionality."""

    def __init__(self, client: AsyncClient, wallet: Keypair, risk_analyzer: RiskAnalyzer):
        """Initialize the sniper."""
        self.client = client
        self.wallet = wallet
        self.risk_analyzer = risk_analyzer
        self.RAYDIUM_PROGRAM_ID = PublicKey.from_string('675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8')

    async def setup_snipe(self, params: Dict[str, Any]) -> SnipeConfig:
        """Set up a snipe operation."""
        # Validate and create snipe configuration
        snipe_config = SnipeConfig(
            token_address=params['token_address'],
            buy_amount=params['buy_amount'],
            take_profit=params.get('take_profit', config.trading.take_profit),
            stop_loss=params.get('stop_loss', config.trading.stop_loss),
            slippage=params.get('slippage', config.trading.max_slippage),
            priority_fee=params.get('priority_fee', config.trading.priority_fee),
            anti_mev=params.get('anti_mev', config.trading.anti_mev),
            trailing_take_profit=params.get('trailing_take_profit'),
            trailing_stop_loss=params.get('trailing_stop_loss')
        )

        # Validate configuration
        self.validate_snipe_params(snipe_config)

        # Start monitoring for LP addition
        await self.monitor_lp_addition(snipe_config)

        return snipe_config

    def validate_snipe_params(self, config: SnipeConfig) -> None:
        """Validate snipe parameters."""
        if not config.token_address:
            raise ValueError("Token address is required")
        if config.buy_amount <= 0:
            raise ValueError("Buy amount must be greater than 0")
        if config.slippage < 0 or config.slippage > 100:
            raise ValueError("Invalid slippage value")
        if config.take_profit < 0 or config.stop_loss < 0:
            raise ValueError("Invalid take profit or stop loss values")

    async def monitor_lp_addition(self, config: SnipeConfig) -> None:
        """Monitor Raydium program for LP addition events."""
        try:
            print(f"Starting LP monitoring for token: {config.token_address}")
            
            # Convert token address to PublicKey
            token_mint = PublicKey(config.token_address)
            
            # Subscribe to program account changes
            async def process_account_update(account_info):
                try:
                    if await self.is_lp_addition_event(account_info, token_mint):
                        print(f"🔥 LP Addition detected for {config.token_address}")
                        await self.execute_snipe(config)
                except Exception as e:
                    print(f"Error processing account update: {str(e)}")

            # Set up subscription with specific filters
            await self.client.account_subscribe(
                self.RAYDIUM_PROGRAM_ID,
                process_account_update,
                encoding="base64",
                filters=[
                    {"memcmp": {"offset": 72, "bytes": str(token_mint)}}
                ]
            )
            
            print(f"✅ Monitoring established for {config.token_address}")
            
        except Exception as e:
            print(f"Failed to set up LP monitoring: {str(e)}")
            raise

    async def is_lp_addition_event(self, account_info: Any, token_mint: PublicKey) -> bool:
        """Check if an account update is an LP addition event."""
        try:
            if not account_info or not account_info.data:
                return False
                
            # Parse account data
            data = account_info.data
            
            # Check if this is a pool initialization or LP addition
            # Raydium specific offsets for pool state
            POOL_STATE_LAYOUT = {
                'STATUS_OFFSET': 0,
                'POOL_STATE_ACTIVE': 1,
                'TOKEN_MINT_OFFSET': 72,
                'LP_SUPPLY_OFFSET': 168,
            }
            
            # Verify pool is active
            pool_status = int.from_bytes(data[POOL_STATE_LAYOUT['STATUS_OFFSET']:POOL_STATE_LAYOUT['STATUS_OFFSET']+1], 'little')
            if pool_status != POOL_STATE_LAYOUT['POOL_STATE_ACTIVE']:
                return False
                
            # Verify token mint matches
            pool_token_mint = PublicKey(data[POOL_STATE_LAYOUT['TOKEN_MINT_OFFSET']:POOL_STATE_LAYOUT['TOKEN_MINT_OFFSET']+32])
            if pool_token_mint != token_mint:
                return False
                
            # Check LP supply change
            new_lp_supply = int.from_bytes(data[POOL_STATE_LAYOUT['LP_SUPPLY_OFFSET']:POOL_STATE_LAYOUT['LP_SUPPLY_OFFSET']+8], 'little')
            
            # Store previous LP supply for comparison
            if not hasattr(self, '_previous_lp_supplies'):
                self._previous_lp_supplies = {}
            
            previous_supply = self._previous_lp_supplies.get(str(token_mint), 0)
            self._previous_lp_supplies[str(token_mint)] = new_lp_supply
            
            # Detect significant LP addition (>1% increase)
            if previous_supply > 0:
                supply_increase = (new_lp_supply - previous_supply) / previous_supply
                return supply_increase > 0.01  # 1% threshold
            
            # For new pools, require minimum LP supply
            MIN_LP_SUPPLY = 1000000  # Adjust based on token decimals
            return new_lp_supply >= MIN_LP_SUPPLY
            
        except Exception as e:
            print(f"Error checking LP addition event: {str(e)}")
            return False

    async def execute_snipe(self, config: SnipeConfig) -> Optional[str]:
        """Execute the snipe operation."""
        try:
            # Perform pre-trade risk checks
            risk_analysis = await self.risk_analyzer.analyze_token_risks(config.token_address)
            
            if risk_analysis.risk_level > config.trading.risk.max_risk_score:
                print(f'❌ Snipe cancelled - High risk detected: {risk_analysis.details}')
                return None

            # Build and execute transaction
            transaction = await self.build_snipe_transaction(config)

            # Add priority fee if specified
            if config.priority_fee:
                transaction.recent_blockhash = await self.client.get_recent_blockhash()
                transaction.priority_fee = int(config.priority_fee * 1e9)  # Convert to lamports

            # Add anti-MEV protection if enabled
            if config.anti_mev:
                self.add_anti_mev_protection(transaction)

            # Sign and send transaction
            signature = await self.send_and_confirm_transaction(transaction)

            # Set up post-trade monitoring
            await self.setup_post_trade_monitoring(config, signature)

            return signature

        except Exception as e:
            print(f'Snipe execution failed: {str(e)}')
            return None

    async def build_snipe_transaction(self, config: SnipeConfig) -> Transaction:
        """Build the snipe transaction."""
        transaction = Transaction()

        # Add Raydium swap instructions
        instructions = await self.create_raydium_swap_instructions(
            config.token_address,
            config.buy_amount,
            config.slippage
        )

        # Add instructions to transaction
        transaction.add(*instructions)

        return transaction

    def add_anti_mev_protection(self, transaction: Transaction) -> None:
        """Add anti-MEV protection to transaction."""
        # Add random delay
        random_delay = random.randint(1, 3)
        
        # Add dummy instructions to confuse MEV bots
        transaction.add(
            transfer(
                TransferParams(
                    from_pubkey=self.wallet.public_key(),
                    to_pubkey=self.wallet.public_key(),
                    lamports=0
                )
            )
        )

    async def setup_post_trade_monitoring(self, config: SnipeConfig, entry_signature: str) -> None:
        """Set up monitoring for take profit and stop loss."""
        # Get entry price
        entry_price = await self.get_transaction_price(entry_signature)

        # Calculate exit prices
        take_profit_price = entry_price * (1 + config.take_profit / 100)
        stop_loss_price = entry_price * (1 - config.stop_loss / 100)

        # Start price monitoring
        await self.monitor_price_for_exits({
            **config.__dict__,
            'entry_price': entry_price,
            'take_profit_price': take_profit_price,
            'stop_loss_price': stop_loss_price
        })

    async def monitor_price_for_exits(self, exit_config: Dict[str, Any]) -> None:
        """Monitor price for exit conditions."""
        highest_price = exit_config['entry_price']
        lowest_price = exit_config['entry_price']

        while True:
            try:
                current_price = await self.get_current_price(exit_config['token_address'])

                # Update trailing values if enabled
                if exit_config['trailing_take_profit']:
                    if current_price > highest_price:
                        highest_price = current_price
                        exit_config['take_profit_price'] = highest_price * (
                            1 - exit_config['trailing_take_profit'] / 100
                        )

                if exit_config['trailing_stop_loss']:
                    if current_price < lowest_price:
                        lowest_price = current_price
                        exit_config['stop_loss_price'] = lowest_price * (
                            1 + exit_config['trailing_stop_loss'] / 100
                        )

                # Check exit conditions
                if current_price >= exit_config['take_profit_price']:
                    await self.execute_sell(exit_config, 'TAKE_PROFIT')
                    break
                elif current_price <= exit_config['stop_loss_price']:
                    await self.execute_sell(exit_config, 'STOP_LOSS')
                    break

            except Exception as e:
                print(f'Error in price monitoring: {str(e)}')

            await asyncio.sleep(1)  # Check every second

    async def execute_sell(self, config: Dict[str, Any], exit_type: str) -> Optional[str]:
        """Execute a sell operation."""
        try:
            transaction = await self.build_sell_transaction(
                token_address=config['token_address'],
                slippage=config.get('slippage', 1.0)  # Default 1% slippage for exits
            )
            signature = await self.send_and_confirm_transaction(transaction)
            
            print(f'{exit_type} executed successfully:', {
                'signature': signature,
                'token': config['token_address'],
                'exit_type': exit_type,
                'price': await self.get_current_price(config['token_address'])
            })

            return signature

        except Exception as e:
            print(f'Sell execution failed: {str(e)}')
            return None

    async def build_sell_transaction(self, token_address: str, slippage: float) -> Transaction:
        """Build a transaction to sell tokens back to SOL."""
        try:
            # Convert addresses to PublicKey
            token_mint = PublicKey(token_address)
            
            # Get token account
            token_account = await self._find_associated_token_address(
                self.wallet.public_key(),
                token_mint
            )
            
            # Get token balance
            account_info = await self.client.get_account_info(token_account)
            if not account_info:
                raise Exception("No token account found")
                
            # Get token amount to sell (full balance)
            token_balance = int.from_bytes(
                account_info.data[64:72],  # Token amount offset in account data
                'little'
            )
            
            if token_balance == 0:
                raise Exception("No tokens to sell")
                
            # Create swap instructions for selling
            instructions = await self.create_raydium_swap_instructions_for_sell(
                token_address=token_address,
                amount=token_balance,
                slippage=slippage
            )
            
            # Build transaction
            transaction = Transaction()
            transaction.add(*instructions)
            
            return transaction
            
        except Exception as e:
            raise Exception(f"Failed to build sell transaction: {str(e)}")
            
    async def create_raydium_swap_instructions_for_sell(
        self,
        token_address: str,
        amount: int,
        slippage: float
    ) -> list:
        """Create Raydium swap instructions for token sale."""
        try:
            # Convert token address to PublicKey
            token_mint = PublicKey.from_string(token_address)
            
            # Get pool state accounts
            pool_keys = await self._get_pool_keys(token_mint)
            
            # Calculate minimum output amount with slippage
            current_price = await self.get_current_price(token_address)
            expected_sol = amount * current_price
            min_amount_out = int(expected_sol * (1 - slippage / 100))
            
            # Build swap instruction
            swap_instruction = await self._build_swap_instruction(
                amount_in=amount,
                min_amount_out=min_amount_out,
                pool_keys=pool_keys,
                is_sol_input=False  # We're selling tokens for SOL
            )
            
            # Get token account
            token_account = await self._find_associated_token_address(
                self.wallet.public_key(),
                token_mint
            )
            
            # Build complete instruction set
            instructions = [
                # Approve token spending
                self._create_token_approve_instruction(
                    token_account=token_account,
                    delegate=pool_keys['authority'],
                    amount=amount
                ),
                # Execute swap
                swap_instruction
            ]
            
            return instructions
            
        except Exception as e:
            raise Exception(f"Failed to create sell instructions: {str(e)}")
            
    def _create_token_approve_instruction(
        self,
        token_account: PublicKey,
        delegate: PublicKey,
        amount: int
    ) -> Transaction:
        """Create instruction to approve token spending."""
        TOKEN_PROGRAM_ID = PublicKey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')
        
        # Build approve instruction
        data = bytes([
            3,  # Approve instruction index
            *amount.to_bytes(8, 'little')  # Amount to approve
        ])
        
        accounts = [
            AccountMeta(pubkey=token_account, is_signer=False, is_writable=True),
            AccountMeta(pubkey=delegate, is_signer=False, is_writable=False),
            AccountMeta(pubkey=self.wallet.public_key(), is_signer=True, is_writable=False)
        ]
        
        return Transaction().add(
            TOKEN_PROGRAM_ID,
            accounts,
            data
        )

    async def create_raydium_swap_instructions(self, token_address: str, amount: float, slippage: float):
        """Create Raydium swap instructions for token purchase."""
        try:
            # Convert token address to PublicKey
            token_mint = PublicKey(token_address)
            
            # Constants for Raydium V4
            RAYDIUM_AMM_PROGRAM_ID = PublicKey.from_string('675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8')
            SOL_MINT = PublicKey.from_string('So11111111111111111111111111111111111111112')
            
            # Get pool state accounts
            pool_keys = await self._get_pool_keys(token_mint)
            
            # Calculate amounts with slippage
            amount_in = int(amount * 1e9)  # Convert SOL to lamports
            min_amount_out = int(amount_in * (1 - slippage / 100))
            
            # Build swap instruction
            swap_instruction = await self._build_swap_instruction(
                amount_in=amount_in,
                min_amount_out=min_amount_out,
                pool_keys=pool_keys,
                is_sol_input=True
            )
            
            # Create associated token account if needed
            token_account = await self._get_or_create_associated_token_account(token_mint)
            
            # Build complete instruction set
            instructions = [
                # Transfer SOL to AMM authority
                transfer(
                    TransferParams(
                        from_pubkey=self.wallet.public_key(),
                        to_pubkey=pool_keys['authority'],
                        lamports=amount_in
                    )
                ),
                # Execute swap
                swap_instruction
            ]
            
            return instructions
            
        except Exception as e:
            raise Exception(f"Failed to create swap instructions: {str(e)}")
            
    async def _get_pool_keys(self, token_mint: PublicKey) -> Dict[str, PublicKey]:
        """Get Raydium pool accounts for a given token."""
        try:
            # Get program accounts filtered for the token mint
            accounts = await self.client.get_program_accounts(
                self.RAYDIUM_PROGRAM_ID,
                encoding="base64",
                filters=[
                    {"memcmp": {"offset": 72, "bytes": str(token_mint)}}
                ]
            )
            
            if not accounts:
                raise Exception(f"No liquidity pool found for token {token_mint}")
                
            # Parse pool data
            pool_data = accounts[0]
            
            return {
                'id': PublicKey(pool_data.pubkey),
                'authority': PublicKey(pool_data.account.owner),
                'base_vault': PublicKey(pool_data.account.data['baseVault']),
                'quote_vault': PublicKey(pool_data.account.data['quoteVault']),
                'lp_mint': PublicKey(pool_data.account.data['lpMint']),
                'open_orders': PublicKey(pool_data.account.data['openOrders']),
                'target_orders': PublicKey(pool_data.account.data['targetOrders']),
                'base_mint': PublicKey(pool_data.account.data['baseMint']),
                'quote_mint': PublicKey(pool_data.account.data['quoteMint']),
            }
            
        except Exception as e:
            raise Exception(f"Failed to get pool keys: {str(e)}")
            
    async def _build_swap_instruction(
        self,
        amount_in: int,
        min_amount_out: int,
        pool_keys: Dict[str, PublicKey],
        is_sol_input: bool
    ):
        """Build Raydium swap instruction."""
        # Define accounts needed for swap
        accounts = [
            AccountMeta(pubkey=pool_keys['id'], is_signer=False, is_writable=True),
            AccountMeta(pubkey=pool_keys['authority'], is_signer=False, is_writable=False),
            AccountMeta(pubkey=pool_keys['open_orders'], is_signer=False, is_writable=True),
            AccountMeta(pubkey=pool_keys['target_orders'], is_signer=False, is_writable=True),
            AccountMeta(pubkey=pool_keys['base_vault'], is_signer=False, is_writable=True),
            AccountMeta(pubkey=pool_keys['quote_vault'], is_signer=False, is_writable=True),
            AccountMeta(pubkey=self.wallet.public_key(), is_signer=True, is_writable=False),
        ]
        
        # Build instruction data
        instruction_data = bytes([
            1,  # Instruction index for swap
            *amount_in.to_bytes(8, 'little'),  # Amount in
            *min_amount_out.to_bytes(8, 'little'),  # Minimum amount out
        ])
        
        return Transaction().add(
            self.RAYDIUM_PROGRAM_ID,
            accounts,
            instruction_data
        )
        
    async def _get_or_create_associated_token_account(self, token_mint: PublicKey) -> PublicKey:
        """Get or create associated token account for wallet."""
        try:
            # Get associated token account address
            ata = await self._find_associated_token_address(
                self.wallet.public_key(),
                token_mint
            )
            
            # Check if account exists
            account_info = await self.client.get_account_info(ata)
            
            if not account_info:
                # Create new associated token account
                create_ata_ix = self._create_associated_token_account_instruction(
                    payer=self.wallet.public_key(),
                    owner=self.wallet.public_key(),
                    mint=token_mint
                )
                
                # Send and confirm transaction
                await self.send_and_confirm_transaction(
                    Transaction().add(create_ata_ix)
                )
                
            return ata
            
        except Exception as e:
            raise Exception(f"Failed to get/create token account: {str(e)}")
            
    async def _find_associated_token_address(
        self,
        wallet_address: PublicKey,
        token_mint: PublicKey
    ) -> PublicKey:
        """Find the associated token account address."""
        seeds = [
            bytes(wallet_address),
            bytes(PublicKey.from_string('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA')),  # Token program ID
            bytes(token_mint)
        ]
        
        program_id = PublicKey.from_string('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')  # Associated token program ID
        
        return PublicKey.find_program_address(seeds, program_id)[0]

    async def get_transaction_price(self, signature: str) -> float:
        """Get price from a transaction."""
        try:
            # Get transaction details
            tx_details = await self.client.get_transaction(
                signature,
                encoding="jsonParsed",
                max_supported_transaction_version=0
            )
            
            if not tx_details:
                raise Exception(f"Transaction {signature} not found")
                
            # Extract price from post balances
            pre_balance = tx_details.value.meta.pre_balances[0]  # Wallet's pre-balance
            post_balance = tx_details.value.meta.post_balances[0]  # Wallet's post-balance
            
            # Calculate amount spent in SOL
            amount_spent = (pre_balance - post_balance) / 1e9
            
            # Get token amount from token balances
            token_balance_change = None
            for token_balance in tx_details.value.meta.post_token_balances:
                if token_balance.owner == str(self.wallet.public_key()):
                    token_balance_change = float(token_balance.ui_token_amount.amount)
                    
            if not token_balance_change:
                raise Exception("Could not determine token amount from transaction")
                
            # Calculate price per token in SOL
            return amount_spent / token_balance_change
            
        except Exception as e:
            print(f"Error getting transaction price: {str(e)}")
            return 0.0

    async def get_current_price(self, token_address: str) -> float:
        """Get current token price from Raydium pool."""
        try:
            # Convert token address to PublicKey
            token_mint = PublicKey(token_address)
            
            # Get pool accounts
            pool_keys = await self._get_pool_keys(token_mint)
            
            # Get pool state data
            pool_info = await self.client.get_account_info(
                pool_keys['id'],
                encoding="base64"
            )
            
            if not pool_info or not pool_info.data:
                raise Exception("Could not fetch pool data")
                
            # Extract reserves from pool data
            # Note: Actual offsets depend on Raydium pool layout
            BASE_RESERVE_OFFSET = 200
            QUOTE_RESERVE_OFFSET = 208
            
            base_reserve = int.from_bytes(
                pool_info.data[BASE_RESERVE_OFFSET:BASE_RESERVE_OFFSET+8],
                'little'
            )
            quote_reserve = int.from_bytes(
                pool_info.data[QUOTE_RESERVE_OFFSET:QUOTE_RESERVE_OFFSET+8],
                'little'
            )
            
            if base_reserve == 0:
                return 0.0
                
            # Calculate price (in SOL)
            # Adjust decimals based on token decimals
            return quote_reserve / base_reserve * 1e9
            
        except Exception as e:
            print(f"Error getting current price: {str(e)}")
            return 0.0

    async def send_and_confirm_transaction(self, transaction: Transaction) -> str:
        """Send and confirm a transaction."""
        try:
            # Get recent blockhash
            recent_blockhash = await self.client.get_recent_blockhash()
            transaction.recent_blockhash = recent_blockhash.value.blockhash
            
            # Sign transaction
            transaction.sign(self.wallet)
            
            # Send transaction
            signature = await self.client.send_transaction(
                transaction,
                self.wallet,
                opts={
                    'skip_preflight': True,  # Skip preflight for faster execution
                    'max_retries': 3,  # Retry on failure
                }
            )
            
            # Wait for confirmation
            confirmation = await self.client.confirm_transaction(
                signature.value,
                commitment="confirmed"
            )
            
            if confirmation.value.err:
                raise Exception(f"Transaction failed: {confirmation.value.err}")
                
            return str(signature.value)
            
        except Exception as e:
            raise Exception(f"Failed to send transaction: {str(e)}")
