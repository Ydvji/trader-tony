import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from trading.sniper import RaydiumSniper
from trading.risk import RiskAnalyzer

async def test_sniper():
    # Initialize RPC client with Helius endpoint
    client = AsyncClient("https://mainnet.helius-rpc.com/?api-key=cb561e5e-d40a-4330-bfda-ab65bda271f4")
    
    # Create wallet from seed phrase
    # Note: In production, load this from environment variables
    from mnemonic import Mnemonic
    import hashlib

    # Convert mnemonic to seed
    mnemo = Mnemonic("english")
    seed = mnemo.to_seed("erode able universe shiver trick obscure smooth wheel frown badge rural bar")
    
    # Use first 32 bytes of the seed for Keypair
    seed_bytes = seed[:32]
    wallet = Keypair.from_seed(bytes(seed_bytes))
    
    # Initialize risk analyzer
    risk_analyzer = RiskAnalyzer(client)
    
    # Create sniper instance
    sniper = RaydiumSniper(client, wallet, risk_analyzer)
    
    # Configure snipe parameters
    snipe_config = {
        "token_address": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",  # BONK token for testing
        "buy_amount": 0.1,  # Amount in SOL
        "take_profit": 50,  # 50% take profit
        "stop_loss": 25,    # 25% stop loss
        "slippage": 10      # 10% slippage
    }
    
    try:
        # Start sniping
        print("Setting up snipe...")
        result = await sniper.setup_snipe(snipe_config)
        print(f"Snipe setup result: {result}")
        
        # Keep script running to monitor
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping sniper...")
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        await client.close()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_sniper())
