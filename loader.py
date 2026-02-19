import telebot
from pymongo import MongoClient
import os
from config import BOT_TOKEN, MONGO_URL

# শুরুতে সব ভেরিয়েবল খালি (None) হিসেবে ডিফাইন করা হলো
bot = None
users_col = None
orders_col = None
trx_col = None

# --- বোট সেটআপ ---
if BOT_TOKEN and ":" in BOT_TOKEN:
    try:
        bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
        print("✅ Bot Initialization Successful.")
    except Exception as e:
        print(f"❌ Bot Error: {e}")
else:
    print("❌ ERROR: BOT_TOKEN missing or invalid format (needs ':')")

# --- ডাটাবেস সেটআপ ---
if MONGO_URL and "mongodb" in MONGO_URL:
    try:
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        db = client['ultimate_smm_bot']
        
        # কালেকশনগুলো ডিফাইন করা হলো
        users_col = db['users']
        orders_col = db['orders']
        trx_col = db['transactions']
        
        # চেক করা হচ্ছে কানেকশন কাজ করছে কি না
        client.admin.command('ping')
        print("✅ MongoDB Connected Successfully.")
    except Exception as e:
        print(f"❌ Database Connection Error: {e}")
else:
    print("❌ ERROR: MONGO_URL missing or invalid format!")
