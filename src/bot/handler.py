"""
Telegram bot handler for Trader Tony.
Handles user interactions and command processing.
"""
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
import telebot
from telebot.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from solana.rpc.async_api import AsyncClient

from ..utils.config import config
from ..trading.sniper import Sniper
from ..trading.risk import RiskAnalyzer
from ..trading.monitor import TokenMonitor
from ..trading.raydium import RaydiumDEX

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramHandler:
    """Handles Telegram bot interactions."""

    def __init__(self):
        """Initialize the Telegram bot handler."""
        self.bot = telebot.TeleBot(config.telegram_token)
        self.client = AsyncClient("https://api.mainnet-beta.solana.com")
        self.risk_analyzer = RiskAnalyzer(self.client)
        self.monitor = TokenMonitor(self.client)
        self.raydium = RaydiumDEX(self.client)
        self.sniper = Sniper(self.client)
        
        # Start monitoring
        asyncio.create_task(self.monitor.start_monitoring())
        self.monitor.add_callback(self._handle_new_pool)
        
        self.setup_handlers()

    def setup_handlers(self) -> None:
        """Set up message handlers."""
        # Command handlers
        @self.bot.message_handler(commands=['start'])
        def start(message: Message) -> None:
            """Handle /start command."""
            welcome_text = f"""
👋 Hi {message.from_user.first_name}!

Welcome to Trader Tony Bot. I'm here to help you trade on Solana.

🔥 Features:
• Token sniping with anti-MEV
• Real-time pool monitoring
• Risk analysis and safety checks
• Auto take-profit/stop-loss

Available commands:
/start - Show this welcome message
/help - Show available commands
/status - Check bot status
/snipe <token> <amount> - Snipe a token
/monitor - Start pool monitoring
/settings - Configure bot settings
"""
            # Create inline keyboard
            keyboard = InlineKeyboardMarkup(row_width=2)
            keyboard.add(
                InlineKeyboardButton("💰 Snipe Token", callback_data="cmd_snipe"),
                InlineKeyboardButton("🔍 Monitor Pools", callback_data="cmd_monitor"),
                InlineKeyboardButton("⚙️ Settings", callback_data="cmd_settings"),
                InlineKeyboardButton("ℹ️ Help", callback_data="cmd_help")
            )
            
            self.bot.reply_to(message, welcome_text, reply_markup=keyboard)
            logger.info(f"User {message.from_user.id} started the bot")

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith('cmd_'))
        def handle_command_callback(call):
            """Handle command button callbacks."""
            command = call.data.split('_')[1]
            
            if command == 'snipe':
                snipe_text = """
Enter token to snipe:
• Token address
• Birdeye URL
• DEX Screener URL

Format: /snipe <token> <amount>
Example: /snipe So11111111111111111111111111111111111111112 1.5
"""
                self.bot.edit_message_text(
                    snipe_text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self._get_back_keyboard()
                )
                
            elif command == 'monitor':
                monitor_text = """
🔍 Pool Monitoring Active

Monitoring for:
• New token launches
• Liquidity additions
• Price changes
• Volume spikes

Use /settings to configure alerts
"""
                self.bot.edit_message_text(
                    monitor_text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self._get_back_keyboard()
                )
                
            elif command == 'settings':
                settings_keyboard = InlineKeyboardMarkup(row_width=2)
                settings_keyboard.add(
                    InlineKeyboardButton("🎯 Slippage", callback_data="setting_slippage"),
                    InlineKeyboardButton("💰 Max Amount", callback_data="setting_max_amount"),
                    InlineKeyboardButton("⚡ Priority Fee", callback_data="setting_priority_fee"),
                    InlineKeyboardButton("🔙 Back", callback_data="cmd_back")
                )
                
                self.bot.edit_message_text(
                    "⚙️ Bot Settings:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=settings_keyboard
                )
                
            elif command == 'help':
                help_text = """
🤖 Bot Commands:

/snipe <token> <amount>
Snipe a token with amount in SOL
Example: /snipe So11111111111111111111111111111111111111112 1.5

/monitor
Start monitoring for new pools

/settings
Configure bot settings

/status
Check bot status and network
"""
                self.bot.edit_message_text(
                    help_text,
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=self._get_back_keyboard()
                )
                
            elif command == 'back':
                # Return to main menu
                start(call.message)

        @self.bot.message_handler(commands=['snipe'])
        async def snipe_command(message: Message):
            """Handle snipe command."""
            try:
                # Parse command
                args = message.text.split()
                if len(args) != 3:
                    self.bot.reply_to(
                        message,
                        "❌ Invalid format. Use: /snipe <token> <amount>"
                    )
                    return
                
                token_input = args[1]
                amount = float(args[2])
                
                # Send initial message
                status_msg = self.bot.reply_to(
                    message,
                    "🔍 Analyzing token..."
                )
                
                # Analyze token
                analysis = await self.risk_analyzer.analyze_token_risks(token_input)
                if analysis.risk_level > config.risk.max_risk_score:
                    self.bot.edit_message_text(
                        f"⚠️ High risk token detected!\n\nRisk Score: {analysis.risk_level}/100\nDetails: {analysis.details}",
                        status_msg.chat.id,
                        status_msg.message_id
                    )
                    return
                
                # Update status
                self.bot.edit_message_text(
                    "✅ Token analysis complete\n🔥 Preparing to snipe...",
                    status_msg.chat.id,
                    status_msg.message_id
                )
                
                # Execute snipe
                result = await self.sniper.snipe_token(token_input, amount)
                
                if result['success']:
                    self.bot.edit_message_text(
                        f"🎯 Snipe successful!\n\nToken: {result['token']}\nAmount: {amount} SOL\nTx: {result['signature']}",
                        status_msg.chat.id,
                        status_msg.message_id
                    )
                else:
                    self.bot.edit_message_text(
                        f"❌ Snipe failed: {result['error']}",
                        status_msg.chat.id,
                        status_msg.message_id
                    )
                    
            except Exception as e:
                self.bot.reply_to(message, f"❌ Error: {str(e)}")

        async def _handle_new_pool(self, token_address: str, pool_info: Dict):
            """Handle new pool notification."""
            try:
                # Quick risk check
                analysis = await self.risk_analyzer.analyze_token_risks(token_address)
                
                # Format message
                msg = f"""
🆕 New Token Pool Detected!

Token: {pool_info['token_name']} ({pool_info['token_symbol']})
Address: `{token_address}`
Initial Price: ${pool_info['initial_price']:.6f}
Initial Liquidity: ${pool_info['initial_liquidity']:,.2f}

Risk Score: {analysis.risk_level}/100
{analysis.details}
"""
                # Create snipe button if risk is acceptable
                keyboard = None
                if analysis.risk_level <= config.risk.max_risk_score:
                    keyboard = InlineKeyboardMarkup()
                    keyboard.add(
                        InlineKeyboardButton(
                            "🎯 Snipe",
                            callback_data=f"snipe_{token_address}"
                        )
                    )
                
                # Broadcast to all monitoring users
                # This would normally use a database of subscribed users
                self.bot.send_message(
                    config.admin_chat_id,
                    msg,
                    parse_mode='Markdown',
                    reply_markup=keyboard
                )
                
            except Exception as e:
                logger.error(f"Error handling new pool: {str(e)}")

        def _get_back_keyboard(self):
            """Create back button keyboard."""
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("🔙 Back to Menu", callback_data="cmd_back")
            )
            return keyboard

        # Monitor command
        @self.bot.message_handler(commands=['monitor'])
        async def monitor(message: Message) -> None:
            """Handle /monitor command."""
            try:
                # Parse command arguments
                args = message.text.split()[1:]
                if not args:
                    raise ValueError("Missing token address. Usage: /monitor <token>")

                token_address = args[0]
                
                # Start monitoring
                success = await self.monitor.start_monitoring(token_address, {
                    'price_threshold': 5.0,  # 5% change
                    'liquidity_threshold': 10.0,  # 10% change
                    'volume_threshold': 100.0  # 100% change
                })

                if success:
                    self.bot.reply_to(message, f"🔍 Started monitoring {token_address}")
                    logger.info(f"User {message.from_user.id} started monitoring {token_address}")
                else:
                    self.bot.reply_to(message, f"❌ Failed to start monitoring {token_address}")

            except Exception as e:
                self.bot.reply_to(message, f"❌ Error: {str(e)}")
                logger.error(f"Monitor command error: {str(e)}")

        # Stop monitoring command
        @self.bot.message_handler(commands=['stop'])
        async def stop_monitor(message: Message) -> None:
            """Handle /stop command."""
            try:
                # Parse command arguments
                args = message.text.split()[1:]
                if not args:
                    raise ValueError("Missing token address. Usage: /stop <token>")

                token_address = args[0]
                
                # Stop monitoring
                success = await self.monitor.stop_monitoring(token_address)

                if success:
                    self.bot.reply_to(message, f"✅ Stopped monitoring {token_address}")
                    logger.info(f"User {message.from_user.id} stopped monitoring {token_address}")
                else:
                    self.bot.reply_to(message, f"❌ Token {token_address} was not being monitored")

            except Exception as e:
                self.bot.reply_to(message, f"❌ Error: {str(e)}")
                logger.error(f"Stop monitor command error: {str(e)}")

        # Alerts command
        @self.bot.message_handler(commands=['alerts'])
        def alerts(message: Message) -> None:
            """Handle /alerts command."""
            try:
                # Get recent alerts
                recent_alerts = self.monitor.get_recent_alerts(limit=5)
                
                if not recent_alerts:
                    self.bot.reply_to(message, "No recent alerts.")
                    return

                # Format alerts message
                alerts_text = "Recent Alerts:\n\n"
                for alert in recent_alerts:
                    alerts_text += self.monitor.format_alert_message(alert) + "\n"

                self.bot.reply_to(message, alerts_text)
                logger.info(f"User {message.from_user.id} checked alerts")

            except Exception as e:
                self.bot.reply_to(message, f"❌ Error: {str(e)}")
                logger.error(f"Alerts command error: {str(e)}")

    def start(self) -> None:
        """Start the Telegram bot."""
        logger.info("Starting Telegram bot...")
        self.bot.infinity_polling()

    def stop(self) -> None:
        """Stop the Telegram bot."""
        logger.info("Stopping Telegram bot...")
        self.bot.stop_polling()
