"""
Wallet utilities for Trader Tony.
Handles wallet connection and basic transaction functionality.
"""
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solders.transaction import Transaction
from mnemonic import Mnemonic
from src.utils.config import config

class Wallet:
    def __init__(self, keypair: Keypair = None, seed_phrase: str = None, client: AsyncClient = None):
        """Initialize wallet with either keypair or seed phrase"""
        self.client = client or AsyncClient(config.solana_rpc_url)
        
        if keypair:
            self.keypair = keypair
        elif seed_phrase:
            self.keypair = self._create_from_seed(seed_phrase)
        else:
            self.keypair = self._create_new()
            
        self.address = str(self.keypair.pubkey())

    @staticmethod
    def _create_from_seed(seed_phrase: str) -> Keypair:
        """Create keypair from seed phrase"""
        mnemo = Mnemonic("english")
        seed = mnemo.to_seed(seed_phrase)
        seed_bytes = seed[:32]
        return Keypair.from_seed(bytes(seed_bytes))

    @staticmethod
    def _create_new() -> Keypair:
        """Create new random keypair"""
        return Keypair()

    @classmethod
    def create_new(cls, client: AsyncClient = None):
        """Create new wallet instance"""
        return cls(client=client)

    async def get_balance(self) -> float:
        """Get wallet balance in SOL"""
        try:
            response = await self.client.get_balance(self.keypair.pubkey())
            if response.value is not None:
                return response.value / 1e9  # Convert lamports to SOL
            return 0.0
        except Exception as e:
            print(f"Error getting balance: {str(e)}")
            return 0.0

    async def verify_connection(self) -> bool:
        """Verify wallet connection and balance"""
        try:
            # Check if we can get balance
            balance = await self.get_balance()
            if balance == 0:
                print("Warning: Wallet has 0 SOL balance")
            
            # Verify RPC connection by getting recent blockhash
            blockhash = await self.get_recent_blockhash()
            if not blockhash:
                print("Error: Could not get recent blockhash")
                return False
                
            return True
        except Exception as e:
            print(f"Error verifying wallet connection: {str(e)}")
            return False

    async def get_recent_blockhash(self) -> str:
        """Get recent blockhash"""
        try:
            response = await self.client.get_recent_blockhash()
            if response.value:
                return response.value.blockhash
            return None
        except Exception as e:
            print(f"Error getting recent blockhash: {str(e)}")
            return None

    def sign_transaction(self, transaction: Transaction) -> Transaction:
        """Sign a transaction with wallet keypair"""
        try:
            transaction.sign([self.keypair])
            return transaction
        except Exception as e:
            print(f"Error signing transaction: {str(e)}")
            return None

    async def send_transaction(self, transaction: Transaction) -> str:
        """Send a signed transaction"""
        try:
            # Get recent blockhash
            blockhash = await self.get_recent_blockhash()
            if not blockhash:
                raise Exception("Could not get recent blockhash")
                
            # Update transaction blockhash
            transaction.recent_blockhash = blockhash
            
            # Sign and send
            signed_tx = self.sign_transaction(transaction)
            if not signed_tx:
                raise Exception("Failed to sign transaction")
                
            response = await self.client.send_transaction(signed_tx)
            if response.value:
                return response.value
            raise Exception("No transaction signature returned")
            
        except Exception as e:
            print(f"Error sending transaction: {str(e)}")
            return None

    async def build_transaction(self, instructions: list) -> Transaction:
        """Build a transaction from instructions"""
        try:
            # Get recent blockhash
            blockhash = await self.get_recent_blockhash()
            if not blockhash:
                raise Exception("Could not get recent blockhash")
                
            # Create transaction
            transaction = Transaction()
            transaction.recent_blockhash = blockhash
            
            # Add instructions
            for ix in instructions:
                transaction.add(ix)
                
            return transaction
            
        except Exception as e:
            print(f"Error building transaction: {str(e)}")
            return None
