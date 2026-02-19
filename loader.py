import telebot
from pymongo import MongoClient
import os
from config import BOT_TOKEN, MONGO_URL

# ১. ভেরিয়েবলগুলো আগে থেকেই ডিফাইন করে রাখা (যাতে app.py এরর না দেয়)
bot = None
users_col = None
orders_col = None
trx_col = None

print("🔍 Checking Environment Variables...")

# ২. বোট চেক
if not BOT_TOKEN or ":" not in BOT_TOKEN:
    print("❌ CRITICAL ERROR: BOT_TOKEN is missing or invalid in Render Settings!")
else:
    try:
        bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
        print("✅ Bot is ready.")
    except Exception as e:
        print(f"❌ Bot Error: {e}")

# ৩. ডাটাবেস চেক
if not MONGO_URL or "mongodb" not in MONGO_URL:
    print("❌ CRITICAL ERROR: MONGO_URL is missing or invalid in Render Settings!")
else:
    try:
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        db = client['ultimate_smm_bot']
        users_col = db['users']
        orders_col = db['orders']
        trx_col = db['transactions']
        client.admin.command('ping')
        print("✅ MongoDB is ready.")
    except Exception as e:
        print(f"❌ Database Error: {e}")
