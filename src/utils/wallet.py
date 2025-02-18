"""
Wallet utilities for Trader Tony.
Handles wallet connection and basic transaction functionality.
"""
from solana.rpc.api import Client
from solders.keypair import Keypair
from mnemonic import Mnemonic
from src.utils.config import config

class Wallet:
    def __init__(self, keypair: Keypair = None, seed_phrase: str = None):
        """Initialize wallet with either keypair or seed phrase"""
        self.client = Client(config.solana_rpc_url)
        
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
    def create_new(cls):
        """Create new wallet instance"""
        return cls()

    def get_balance(self) -> float:
        """Get wallet balance in SOL"""
        try:
            balance = self.client.get_balance(self.keypair.pubkey())
            return balance.value / 1e9  # Convert lamports to SOL
        except Exception as e:
            print(f"Error getting balance: {str(e)}")
            return 0.0

    def verify_connection(self) -> bool:
        """Verify wallet connection and balance"""
        try:
            # Check if we can get balance
            balance = self.get_balance()
            if balance == 0:
                print("Warning: Wallet has 0 SOL balance")
            
            # Verify RPC connection by getting recent blockhash
            blockhash = self.client.get_recent_blockhash()
            if not blockhash:
                print("Error: Could not get recent blockhash")
                return False
                
            return True
        except Exception as e:
            print(f"Error verifying wallet connection: {str(e)}")
            return False

    def get_recent_blockhash(self) -> str:
        """Get recent blockhash"""
        try:
            return self.client.get_recent_blockhash()['result']['value']['blockhash']
        except Exception as e:
            print(f"Error getting recent blockhash: {str(e)}")
            return None

    def sign_transaction(self, transaction):
        """Sign a transaction with wallet keypair"""
        try:
            transaction.sign(self.keypair)
            return transaction
        except Exception as e:
            print(f"Error signing transaction: {str(e)}")
            return None

    def send_transaction(self, transaction):
        """Send a signed transaction"""
        try:
            result = self.client.send_transaction(transaction)
            return result['result']
        except Exception as e:
            print(f"Error sending transaction: {str(e)}")
            return None
