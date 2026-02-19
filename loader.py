import telebot
from pymongo import MongoClient
from config import BOT_TOKEN, MONGO_URL

# কানেকশন সেটআপ
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="Markdown")
client = MongoClient(MONGO_URL)
db = client['ultimate_smm_bot']

# কালেকশন (টেবিল)
users_col = db['users']
orders_col = db['orders']
trx_col = db['transactions']

print("✅ System Loaded: Database & Bot Connected!")
