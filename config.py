import os

# --- SECRET KEYS (Render Environment Variables থেকে আসবে) ---
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN')
API_KEY = os.environ.get('API_KEY', 'YOUR_API_KEY')
API_URL = "https://1xpanel.com/api/v2" # বা আপনার প্যানেলের লিংক
MONGO_URL = os.environ.get('MONGO_URL', 'YOUR_MONGO_URL')

# --- ADMIN PANEL SECURITY ---
ADMIN_PASSWORD = os.environ.get('ADMIN_PASS', 'admin123') # ওয়েব প্যানেল পাসওয়ার্ড
SECRET_KEY = os.environ.get('SECRET_KEY', 'supersecretkey') # সেশন এর জন্য

# --- TELEGRAM CHANNELS ---
ADMIN_ID = int(os.environ.get('ADMIN_ID', '00000000')) 
FORCE_SUB_CHANNEL = os.environ.get('FORCE_SUB_CHANNEL', '@YourChannel')
PROOF_CHANNEL_ID = os.environ.get('PROOF_CHANNEL_ID', '-100xxxxxxxxxx')

# --- BUSINESS SETTINGS ---
PROFIT_MARGIN = 20   # ২০% লাভ
EXCHANGE_RATE = 120  # ১ ডলার = ১২০ টাকা
MIN_DEPOSIT = 50     # মিনিমাম ডিপোজিট
REF_BONUS = 0.05     # রেফার বোনাস ($)
