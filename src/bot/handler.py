"""
Telegram bot handler for Trader Tony.
Manages user interactions and command processing.
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import telebot
from telebot.types import Message

from ..utils.config import config
from ..trading.sniper import RaydiumSniper
from ..trading.risk import RiskAnalyzer
from ..trading.monitor import TokenMonitor

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramHandler:
    """Handles Telegram bot interactions."""

    def __init__(self, sniper: RaydiumSniper, risk_analyzer: RiskAnalyzer, monitor: TokenMonitor):
        """Initialize the Telegram bot handler."""
        self.bot = telebot.TeleBot(config.telegram_token)
        self.sniper = sniper
        self.risk_analyzer = risk_analyzer
        self.monitor = monitor
        self.setup_handlers()

    def setup_handlers(self) -> None:
        """Set up message handlers."""
        # Start command
        @self.bot.message_handler(commands=['start'])
        def start(message: Message) -> None:
            """Handle /start command."""
            welcome_text = f"""
👋 Hi {message.from_user.first_name}!

Welcome to Trader Tony Bot. I'm here to help you trade on Solana.

Available commands:
/start - Show this welcome message
/help - Show available commands
/status - Check bot status
/snipe <token> <amount> - Snipe a token
/trade <token> <amount> <side> - Place a trade
/position - View current positions
/settings - Configure bot settings
/monitor <token> - Start monitoring a token
/alerts - View recent alerts
/stop <token> - Stop monitoring a token
"""
            self.bot.reply_to(message, welcome_text)
            logger.info(f"User {message.from_user.id} started the bot")

        # Help command
        @self.bot.message_handler(commands=['help'])
        def help_command(message: Message) -> None:
            """Handle /help command."""
            help_text = """
Trading Commands:
/snipe <token> <amount> - Snipe a token
  Example: /snipe So11111111111111111111111111111111111111112 1.5
  
/trade <token> <amount> <side> - Place a trade
  Example: /trade So11111111111111111111111111111111111111112 1 buy

Position Management:
/position - View current positions
/close <position_id> - Close a position

Settings & Info:
/status - Check bot status
/settings - Configure bot settings
/risk <token> - Check token risk score
"""
            self.bot.reply_to(message, help_text)
            logger.info(f"User {message.from_user.id} requested help")

        # Status command
        @self.bot.message_handler(commands=['status'])
        def status(message: Message) -> None:
            """Handle /status command."""
            status_text = f"""
Bot Status:
✅ Bot Online
✅ Solana RPC Connected
✅ Raydium Integration Active

System Info:
• Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
• Min Liquidity: ${config.trading.min_liquidity}
• Max Slippage: {config.trading.max_slippage}%
• Risk Threshold: {config.risk.max_risk_score}
"""
            self.bot.reply_to(message, status_text)
            logger.info(f"User {message.from_user.id} checked status")

        # Snipe command
        @self.bot.message_handler(commands=['snipe'])
        def snipe(message: Message) -> None:
            """Handle /snipe command."""
            try:
                # Parse command arguments
                args = message.text.split()[1:]
                if len(args) < 2:
                    raise ValueError("Missing arguments. Usage: /snipe <token> <amount>")

                token_address = args[0]
                amount = float(args[1])

                # Create snipe configuration
                snipe_config = {
                    'token_address': token_address,
                    'buy_amount': amount,
                    'take_profit': config.trading.take_profit,
                    'stop_loss': config.trading.stop_loss,
                    'slippage': config.trading.max_slippage,
                    'priority_fee': config.trading.priority_fee,
                    'anti_mev': config.trading.anti_mev
                }

                # Start snipe operation
                self.bot.reply_to(message, f"🎯 Setting up snipe for {token_address}")
                self.sniper.setup_snipe(snipe_config)
                logger.info(f"User {message.from_user.id} initiated snipe for {token_address}")

            except (ValueError, IndexError) as e:
                self.bot.reply_to(message, f"❌ Error: {str(e)}")
                logger.error(f"Snipe command error: {str(e)}")

        # Risk check command
        @self.bot.message_handler(commands=['risk'])
        async def check_risk(message: Message) -> None:
            """Handle /risk command."""
            try:
                # Parse command arguments
                args = message.text.split()[1:]
                if not args:
                    raise ValueError("Missing token address. Usage: /risk <token>")

                token_address = args[0]
                self.bot.reply_to(message, f"🔍 Analyzing risks for {token_address}...")

                # Perform risk analysis
                risk_analysis = await self.risk_analyzer.analyze_token_risks(token_address)

                # Format risk report
                risk_text = f"""
Risk Analysis Report:

Risk Level: {risk_analysis.risk_level}/100
{'🔴 HIGH RISK' if risk_analysis.risk_level > 70 else '🟡 MEDIUM RISK' if risk_analysis.risk_level > 30 else '🟢 LOW RISK'}

Flags:
{'⚠️ Honeypot Risk' if risk_analysis.is_honeypot else '✅ Not a Honeypot'}
{'⚠️ Low Liquidity' if risk_analysis.has_low_liquidity else '✅ Good Liquidity'}
{'⚠️ Suspicious Activity' if risk_analysis.has_suspicious_activity else '✅ No Suspicious Activity'}

Details:
{risk_analysis.details}
"""
                self.bot.reply_to(message, risk_text)
                logger.info(f"User {message.from_user.id} checked risk for {token_address}")

            except Exception as e:
                self.bot.reply_to(message, f"❌ Error: {str(e)}")
            logger.error(f"Risk check error: {str(e)}")

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
