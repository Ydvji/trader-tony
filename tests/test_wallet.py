"""
Test wallet connection functionality.
"""
import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils.wallet import setup_wallet, verify_wallet_connection

async def test_wallet_connection():
    """Test basic wallet connection and functionality."""
    try:
        print("Setting up wallet connection...")
        wallet, client = await setup_wallet()
        
        print(f"\nWallet public key: {wallet.pubkey()}")
        
        print("\nVerifying wallet connection...")
        is_valid = await verify_wallet_connection(wallet, client)
        
        if is_valid:
            print("✅ Wallet connection verified successfully")
        else:
            print("❌ Wallet connection verification failed")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'client' in locals():
            await client.close()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_wallet_connection())
