import os
import asyncio
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv
from src.utils.wallet import Wallet
from src.trading.sniper import Sniper
from src.trading.risk import RiskAnalyzer
from src.trading.monitor import TokenMonitor
from src.trading.raydium import RaydiumDEX

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Initialize Solana client
from solana.rpc.async_api import AsyncClient
client = AsyncClient("https://api.mainnet-beta.solana.com")

# Initialize components
bot = telebot.TeleBot(BOT_TOKEN)
user_wallets = {}  # Store user wallets (in memory for now)

# Initialize trading components
risk_analyzer = RiskAnalyzer(client)
token_monitor = TokenMonitor(client)
raydium = RaydiumDEX(client)

# Start pool monitoring in background
loop = asyncio.get_event_loop()
loop.create_task(token_monitor.start_monitoring())
token_monitor.add_callback(handle_new_pool)

async def handle_new_pool(token_address: str, pool_info: dict):
    """Handle new pool notification"""
    try:
        # Quick risk check
        analysis = await risk_analyzer.analyze_token_risks(token_address)
        
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
        if analysis.risk_level <= 50:  # Threshold for acceptable risk
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton(
                    "🎯 Snipe",
                    callback_data=f"snipe_{token_address}"
                )
            )
        
        # Send notification to all users
        # TODO: Replace with proper user management
        for user_id in user_wallets:
            bot.send_message(
                user_id,
                msg,
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
    except Exception as e:
        print(f"Error handling new pool: {str(e)}")

def create_main_menu(show_monitor: bool = True):
    """Create the main menu inline keyboard"""
    """Create the main menu inline keyboard"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("💰 Buy", callback_data="menu_buy"),
        InlineKeyboardButton("💳 Fund", callback_data="menu_fund"),
        InlineKeyboardButton("👛 Wallet", callback_data="menu_wallet"),
        InlineKeyboardButton("🔄 Refresh", callback_data="menu_refresh")
    ]
    
    if show_monitor:
        buttons.extend([
            InlineKeyboardButton("🔍 Monitor", callback_data="menu_monitor"),
            InlineKeyboardButton("⚙️ Settings", callback_data="menu_settings")
        ])
        
    keyboard.add(*buttons)
    return keyboard

@bot.message_handler(commands=['start'])
async def start_handler(message):
    """Handle /start command"""
    user_id = message.from_user.id
    
    if user_id not in user_wallets:
        # Create new wallet for user
        wallet = Wallet.create_new(client=client)  # Pass shared client
        user_wallets[user_id] = wallet
        
        msg = (
            "Welcome to TraderTony - the fastest and most secure bot for trading "
            "any token on Solana!\n\n"
            "You currently have no SOL in your wallet. To start trading, deposit "
            "SOL to your TraderTony wallet address:\n\n"
            f"`{wallet.address}`\n(tap to copy)\n\n"
            "Or buy SOL with Apple / Google Pay via MoonPay here.\n\n"
            "Once done, tap refresh and your balance will appear here."
        )
    else:
        wallet = user_wallets[user_id]
        balance = await wallet.get_balance()
        msg = (
            "Welcome to TraderTony - the fastest and most secure bot for trading "
            "any token on Solana!\n\n"
            f"Your balance: {balance} SOL"
        )
    
    bot.reply_to(message, msg, parse_mode='Markdown', reply_markup=create_main_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith('menu_'))
async def handle_menu_callback(call):
    """Handle menu button callbacks"""
    action = call.data.split('_')[1]
    
    if action == 'buy':
        msg = (
            "To buy a token: enter a ticker, token address, or URL from:\n"
            "- pump.fun\n"
            "- Birdeye\n"
            "- DEX Screener\n"
            "- Meteora"
        )
        bot.edit_message_text(
            msg, 
            call.message.chat.id, 
            call.message.message_id,
            reply_markup=create_main_menu()
        )
    
    elif action == 'fund':
        user_id = call.from_user.id
        if user_id not in user_wallets:
            bot.answer_callback_query(call.id, "Please use /start first")
            return
            
        wallet = user_wallets[user_id]
        msg = f"Send SOL to your wallet:\n`{wallet.address}`"
        bot.edit_message_text(
            msg, 
            call.message.chat.id, 
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=create_main_menu()
        )
    
    elif action == 'wallet':
        user_id = call.from_user.id
        if user_id not in user_wallets:
            bot.answer_callback_query(call.id, "Please use /start first")
            return
            
        wallet = user_wallets[user_id]
        balance = await wallet.get_balance()
        msg = (
            f"Your wallet address:\n`{wallet.address}`\n\n"
            f"Balance: {balance} SOL"
        )
        bot.edit_message_text(
            msg, 
            call.message.chat.id, 
            call.message.message_id,
            parse_mode='Markdown',
            reply_markup=create_main_menu()
        )
    
    elif action == 'refresh':
        user_id = call.from_user.id
        if user_id not in user_wallets:
            bot.answer_callback_query(call.id, "Please use /start first")
            return
            
        wallet = user_wallets[user_id]
        balance = await wallet.get_balance()
        msg = f"Balance: {balance} SOL"
        bot.edit_message_text(
            msg, 
            call.message.chat.id, 
            call.message.message_id,
            reply_markup=create_main_menu()
        )

@bot.message_handler(func=lambda m: True)
async def handle_token(message):
    """Handle token address/URL input"""
    user_id = message.from_user.id
    if user_id not in user_wallets:
        bot.reply_to(message, "Please use /start first")
        return
        
    text = message.text.strip()
    if len(text) < 32 and not text.startswith('http'):
        return
        
    try:
        # Send analyzing message
        status_msg = bot.reply_to(message, "🔍 Analyzing token...")
        
        # Get token info
        sniper = Sniper(user_wallets[user_id])
        token_info = await sniper.get_token_info(text)
        
        # Get risk analysis
        analysis = await risk_analyzer.analyze_token_risks(text)
        
        # Format message
        msg = (
            f"Token: {token_info['name']} ({token_info['symbol']})\n"
            f"Price: ${token_info['price']:.6f}\n"
            f"Market Cap: ${token_info['market_cap']:,.0f}\n"
            f"24h Volume: ${token_info['volume_24h']:,.0f}\n"
            f"Liquidity: ${token_info['liquidity']:,.0f}\n\n"
            f"Risk Score: {analysis.risk_level}/100\n"
            f"Details: {analysis.details}"
        )
        
        # Create keyboard with buy options
        keyboard = InlineKeyboardMarkup(row_width=2)
        
        # Only show snipe button if risk is acceptable
        if analysis.risk_level <= 50:
            keyboard.add(
                InlineKeyboardButton("🎯 Snipe", callback_data=f"snipe_{text}"),
                InlineKeyboardButton("📈 Chart", url=token_info['chart_url'])
            )
        else:
            keyboard.add(
                InlineKeyboardButton("⚠️ High Risk", callback_data="high_risk"),
                InlineKeyboardButton("📈 Chart", url=token_info['chart_url'])
            )
        
        # Update status message
        bot.edit_message_text(
            msg,
            status_msg.chat.id,
            status_msg.message_id,
            reply_markup=keyboard
        )
        
    except Exception as e:
        bot.edit_message_text(
            f"❌ Error: {str(e)}",
            status_msg.chat.id,
            status_msg.message_id
        )

@bot.callback_query_handler(func=lambda call: call.data.startswith('snipe_'))
async def handle_snipe(call):
    """Handle snipe button callback"""
    try:
        token = call.data.split('_')[1]
        user_id = call.from_user.id
        
        if user_id not in user_wallets:
            bot.answer_callback_query(call.id, "Please use /start first")
            return
            
        # Update message
        bot.edit_message_text(
            "🎯 Preparing to snipe...",
            call.message.chat.id,
            call.message.message_id
        )
        
        # Execute snipe
        sniper = Sniper(user_wallets[user_id])
        result = await sniper.snipe_token(token, amount=0.1)  # Default amount
        
        if result['success']:
            msg = (
                f"✅ Snipe successful!\n\n"
                f"Token: {result['token']}\n"
                f"Amount: {result['amount']} SOL\n"
                f"Tx: {result['signature']}"
            )
        else:
            msg = f"❌ Snipe failed: {result['error']}"
            
        # Update message with result
        bot.edit_message_text(
            msg,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=create_main_menu()
        )
        
    except Exception as e:
        bot.edit_message_text(
            f"❌ Error: {str(e)}",
            call.message.chat.id,
            call.message.message_id
        )

def main():
    """Start the bot"""
    try:
        print("TraderTony is running...")
        print("Press Ctrl+C to stop")
        
        # Start bot
        bot.infinity_polling()
        
    except KeyboardInterrupt:
        print("\nStopping bot...")
        token_monitor.stop_monitoring()
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == '__main__':
    main()
