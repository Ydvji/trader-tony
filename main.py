"""
Main entry point for Trader Tony.
"""
import asyncio
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair

from src.utils.config import config
from src.trading.risk import RiskAnalyzer
from src.trading.sniper import RaydiumSniper
from src.trading.monitor import TokenMonitor
from src.bot.handler import TelegramHandler

async def main():
    """Initialize and start the trading bot."""
    try:
        # Validate configuration
        config.validate()

        # Initialize Solana client
        client = AsyncClient(config.solana_rpc_url)

        # Initialize wallet from private key
        wallet = Keypair.from_bytes(bytes.fromhex(config.wallet_private_key))

        # Initialize components
        risk_analyzer = RiskAnalyzer(client)
        sniper = RaydiumSniper(client, wallet, risk_analyzer)
        monitor = TokenMonitor(client)
        
        # Initialize and start Telegram bot
        telegram_handler = TelegramHandler(sniper, risk_analyzer, monitor)
        
        print("🤖 Trader Tony is starting up...")
        print(f"✅ Connected to Solana RPC: {config.solana_rpc_url}")
        print(f"✅ Wallet loaded: {wallet.public_key()}")
        print("✅ Risk analyzer initialized")
        print("✅ Raydium sniper initialized")
        print("🚀 Starting Telegram bot...")
        
        # Start the bot
        telegram_handler.start()

    except Exception as e:
        print(f"❌ Error starting bot: {str(e)}")
        raise

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
