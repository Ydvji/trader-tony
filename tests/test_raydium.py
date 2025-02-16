"""
Test Raydium DEX integration.
"""
import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from utils.wallet import setup_wallet
from trading.raydium import RaydiumClient
from solders.pubkey import Pubkey as PublicKey

async def test_raydium_connection():
    """Test basic Raydium program connection."""
    try:
        print("Setting up wallet connection...")
        wallet, client = await setup_wallet()
        
        print("\nInitializing Raydium client...")
        raydium = RaydiumClient(client, wallet)
        
        print("\nVerifying Raydium program connection...")
        is_valid = await raydium.verify_program_connection()
        
        if is_valid:
            print("✅ Raydium program connection verified")
            
            # Test liquidity monitoring
            print("\nTesting liquidity monitoring...")
            bonk_address = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263"  # BONK token
            min_liquidity = 1000.0  # Minimum 1000 SOL liquidity
            
            print(f"Checking liquidity for BONK (minimum: {min_liquidity} SOL)...")
            has_liquidity = await raydium.monitor_liquidity(
                token_address=bonk_address,
                min_liquidity=min_liquidity
            )
            
            if has_liquidity:
                print("✅ Token has sufficient liquidity")
                
                # Test swap instruction creation
                print("\nTesting swap instruction creation...")
                amount = 0.1  # 0.1 SOL
                slippage = 1.0  # 1% slippage
                
                print(f"Creating swap instruction for {amount} SOL -> BONK (slippage: {slippage}%)...")
                transaction = await raydium.create_swap_instruction(
                    token_address=bonk_address,
                    amount=amount,
                    slippage=slippage
                )
                
                if transaction:
                    print("✅ Successfully created swap instruction")
                    print(f"Target token: {bonk_address}")
                    print(f"Amount: {amount} SOL (slippage: {slippage}%)")
                    print(f"Transaction contains {len(transaction.instructions)} instruction(s)")
                else:
                    print("❌ Failed to create swap instruction")
            else:
                print("❌ Insufficient liquidity for safe trading")
        else:
            print("❌ Raydium program connection failed")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'client' in locals():
            await client.close()

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_raydium_connection())
