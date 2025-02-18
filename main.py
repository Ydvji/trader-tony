import os
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from src.utils.wallet import Wallet
from src.trading.sniper import Sniper

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Initialize bot
bot = telebot.TeleBot(BOT_TOKEN)

# Store user wallets (in memory for now)
user_wallets = {}

def create_keyboard():
    """Create the main keyboard"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.row(KeyboardButton('Buy'), KeyboardButton('Fund'))
    keyboard.row(KeyboardButton('Help'), KeyboardButton('Refer Friends'))
    keyboard.row(KeyboardButton('Alerts'), KeyboardButton('Wallet'))
    keyboard.row(KeyboardButton('Settings'), KeyboardButton('DCA Orders'))
    keyboard.row(KeyboardButton('Limit Orders'), KeyboardButton('Refresh'))
    return keyboard

@bot.message_handler(commands=['start'])
def start_handler(message):
    """Handle /start command"""
    user_id = message.from_user.id
    
    if user_id not in user_wallets:
        # Create new wallet for user
        wallet = Wallet.create_new()
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
        balance = wallet.get_balance()
        msg = (
            "Welcome to TraderTony - the fastest and most secure bot for trading "
            "any token on Solana!\n\n"
            f"Your balance: {balance} SOL"
        )
    
    bot.reply_to(message, msg, parse_mode='Markdown', reply_markup=create_keyboard())

@bot.message_handler(func=lambda m: m.text == 'Buy')
def buy_handler(message):
    """Handle Buy button"""
    msg = (
        "To buy a token: enter a ticker, token address, or URL from:\n"
        "- pump.fun\n"
        "- Birdeye\n"
        "- DEX Screener\n"
        "- Meteora"
    )
    bot.reply_to(message, msg)

@bot.message_handler(func=lambda m: m.text == 'Fund')
def fund_handler(message):
    """Handle Fund button"""
    user_id = message.from_user.id
    if user_id not in user_wallets:
        bot.reply_to(message, "Please use /start first")
        return
        
    wallet = user_wallets[user_id]
    msg = f"Send SOL to your wallet:\n`{wallet.address}`"
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == 'Wallet')
def wallet_handler(message):
    """Handle Wallet button"""
    user_id = message.from_user.id
    if user_id not in user_wallets:
        bot.reply_to(message, "Please use /start first")
        return
        
    wallet = user_wallets[user_id]
    balance = wallet.get_balance()
    msg = (
        f"Your wallet address:\n`{wallet.address}`\n\n"
        f"Balance: {balance} SOL\n\n"
        "For more info and to export your seed phrase, tap 'Wallet' below."
    )
    bot.reply_to(message, msg, parse_mode='Markdown')

@bot.message_handler(func=lambda m: m.text == 'Refresh')
def refresh_handler(message):
    """Handle Refresh button"""
    user_id = message.from_user.id
    if user_id not in user_wallets:
        bot.reply_to(message, "Please use /start first")
        return
        
    wallet = user_wallets[user_id]
    balance = wallet.get_balance()
    msg = f"Balance: {balance} SOL"
    bot.reply_to(message, msg)

@bot.message_handler(func=lambda m: True)
def handle_token(message):
    """Handle token address/URL input"""
    user_id = message.from_user.id
    if user_id not in user_wallets:
        bot.reply_to(message, "Please use /start first")
        return
        
    text = message.text.strip()
    if len(text) < 32 and not text.startswith('http'):
        return
        
    try:
        sniper = Sniper(user_wallets[user_id])
        token_info = sniper.get_token_info(text)
        
        msg = (
            f"Token: {token_info['name']} ({token_info['symbol']})\n"
            f"Price: ${token_info['price']:.6f}\n"
            f"Market Cap: ${token_info['market_cap']:,.0f}\n"
            f"24h Volume: ${token_info['volume_24h']:,.0f}\n"
            f"Liquidity: ${token_info['liquidity']:,.0f}"
        )
        
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.row(
            telebot.types.InlineKeyboardButton("Buy", callback_data=f"buy_{text}"),
            telebot.types.InlineKeyboardButton("Chart", url=token_info['chart_url'])
        )
        
        bot.reply_to(message, msg, reply_markup=keyboard)
    except Exception as e:
        bot.reply_to(message, f"Error: {str(e)}")

def main():
    """Start the bot"""
    print("TraderTony is running...")
    bot.infinity_polling()

if __name__ == '__main__':
    main()
