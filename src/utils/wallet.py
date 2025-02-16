"""
Wallet utilities for Trader Tony.
Handles wallet connection and basic transaction functionality.
"""
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from mnemonic import Mnemonic
from utils.config import config

async def setup_wallet():
    """Initialize wallet and RPC client connection."""
    try:
        # Convert mnemonic to seed
        mnemo = Mnemonic("english")
        seed = mnemo.to_seed(config.wallet_seed_phrase)
        
        # Use first 32 bytes of the seed for Keypair
        seed_bytes = seed[:32]
        wallet = Keypair.from_seed(bytes(seed_bytes))
        
        # Initialize RPC client with Helius endpoint
        client = AsyncClient(config.solana_rpc_url)
        
        # Verify connection
        version = await client.get_version()
        print(f"Connected to Solana node version: {version.value.solana_core}")
        
        # Get wallet balance
        balance = await client.get_balance(wallet.pubkey())
        print(f"Wallet balance: {balance.value / 1e9} SOL")
        
        return wallet, client
    except Exception as e:
        raise Exception(f"Failed to setup wallet: {str(e)}")

async def verify_wallet_connection(wallet: Keypair, client: AsyncClient) -> bool:
    """Verify wallet connection and balance."""
    try:
        # Check if wallet has a balance
        balance = await client.get_balance(wallet.pubkey())
        if balance.value == 0:
            print("Warning: Wallet has 0 SOL balance")
            return False
            
        # Verify we can get recent blockhash (tests RPC connection)
        blockhash = await client.get_recent_blockhash()
        if not blockhash:
            print("Error: Could not get recent blockhash")
            return False
            
        return True
    except Exception as e:
        print(f"Error verifying wallet connection: {str(e)}")
        return False
