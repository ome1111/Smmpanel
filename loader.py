import telebot
from pymongo import MongoClient
import os
import sys
from config import BOT_TOKEN, MONGO_URL

# --- ১. বোট চেক এবং ইনিশিয়াল (Error handling সহ) ---
if not BOT_TOKEN or ":" not in BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN is missing or invalid in Render Environment Variables!")
    print("👉 Please make sure your token looks like '123456:ABC-def...'")
    # টোকেন ভুল হলে সার্ভার যাতে ক্র্যাশ না করে ক্লিনার ভাবে বন্ধ হয়
    bot = None 
else:
    try:
        # বোট অবজেক্ট তৈরি
        bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
        print("✅ Bot Object Created Successfully!")
    except Exception as e:
        print(f"❌ Bot Initialization Failed: {e}")
        bot = None

# --- ২. ডাটাবেস কানেকশন (MongoDB) ---
try:
    if not MONGO_URL or "mongodb" not in MONGO_URL:
        print("❌ ERROR: MONGO_URL is missing or invalid!")
        client = None
        db = None
    else:
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
        # ডাটাবেস নাম (এটি আপনার ইচ্ছামতো পরিবর্তন করতে পারেন)
        db = client['ultimate_smm_bot']
        
        # টেবিল বা কালেকশনগুলো ডিফাইন করা
        users_col = db['users']
        orders_col = db['orders']
        trx_col = db['transactions']
        
        # কানেকশন চেক করা
        client.admin.command('ping')
        print("✅ MongoDB Connected Successfully!")
except Exception as e:
    print(f"❌ Database Connection Error: {e}")
    db = None

# --- ৩. ক্রিটিক্যাল এরর চেক ---
# যদি বোট বা ডাটাবেস কোনোটিই কানেক্ট না হয়, তবে সিস্টেম চলবে না
if bot is None or db is None:
    print("🚨 CRITICAL: System failed to start. Check your Environment Variables on Render.")
