from telebot import types
from loader import bot, users_col, orders_col
from config import *
import api
import graphics
from datetime import datetime

# --- HELPERS ---
def get_user(chat_id, name, ref_id=None):
    user = users_col.find_one({"_id": chat_id})
    if not user:
        user = {
            "_id": chat_id, "name": name, "balance": 0.0, "spent": 0.0,
            "ref_by": ref_id, "joined_at": datetime.now()
        }
        users_col.insert_one(user)
        # Referral Bonus Logic
        if ref_id:
            bot.send_message(ref_id, f"🎉 **New Referral!** {name} joined via your link.")
    return user

def check_sub(chat_id):
    try:
        member = bot.get_chat_member(FORCE_SUB_CHANNEL, chat_id)
        if member.status in ['left', 'kicked']: return False
        return True
    except: return True 

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 New Order", "👤 Profile", "💰 Deposit", "📦 Orders", "🎧 Support")
    return markup

# --- START & WELCOME ---
@bot.message_handler(commands=['start'])
def start(message):
    ref_id = None
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        if int(args[1]) != message.chat.id: ref_id = int(args[1])

    user = get_user(message.chat.id, message.from_user.first_name, ref_id)

    if not check_sub(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("✈️ Join Channel", url=f"https://t.me/{FORCE_SUB_CHANNEL.replace('@','')}"))
        markup.add(types.InlineKeyboardButton("✅ Joined", callback_data="CHECK_SUB"))
        bot.send_message(message.chat.id, f"⚠️ **Please join our channel first:**\n{FORCE_SUB_CHANNEL}", reply_markup=markup)
        return

    # Image Generation
    msg = bot.send_message(message.chat.id, "🎨 **Loading...**")
    try:
        photo = graphics.create_welcome(user['name'])
        bot.delete_message(message.chat.id, msg.message_id)
        bot.send_photo(message.chat.id, photo, caption="🚀 **Welcome to the Best SMM Panel!**", reply_markup=main_menu())
    except:
        bot.send_message(message.chat.id, "👋 Welcome!", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda c: c.data == "CHECK_SUB")
def sub_check(call):
    if check_sub(call.message.chat.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ **Verified!**", reply_markup=main_menu())
    else:
        bot.answer_callback_query(call.id, "❌ Not Joined Yet!")

# --- PROFILE ---
@bot.message_handler(func=lambda m: m.text == "👤 Profile")
def profile(message):
    user = users_col.find_one({"_id": message.chat.id})
    msg = bot.send_message(message.chat.id, "🎨 **Generating Card...**")
    photo = graphics.create_profile(user['name'], user['_id'], user['balance'], user['spent'])
    bot.delete_message(message.chat.id, msg.message_id)
    bot.send_photo(message.chat.id, photo, caption=f"🔗 **Referral Link:**\n`https://t.me/{bot.get_me().username}?start={user['_id']}`")

# --- ORDER SYSTEM ---
@bot.message_handler(func=lambda m: m.text == "🚀 New Order")
def categories(message):
    if not check_sub(message.chat.id): return
    msg = bot.send_message(message.chat.id, "🔄 **Fetching Services...**")
    
    services = api.get_services()
    if not services:
        bot.edit_message_text("⚠️ **Server Busy or API Error.** Try again.", message.chat.id, msg.message_id); return

    cats = sorted(list(set(s['category'] for s in services)))
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, cat in enumerate(cats):
        markup.add(types.InlineKeyboardButton(cat, callback_data=f"CAT|{i}"))
    
    bot.edit_message_text(f"📂 **Select Category:**", message.chat.id, msg.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("CAT|"))
def services(call):
    idx = int(call.data.split("|")[1])
    services = api.get_services()
    cats = sorted(list(set(s['category'] for s in services)))
    
    if idx >= len(cats): return # Safety check
    cat_name = cats[idx]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for s in [x for x in services if x['category'] == cat_name]:
        rate = float(s['rate'])
        my_rate = rate + (rate * PROFIT_MARGIN / 100)
        markup.add(types.InlineKeyboardButton(f"ID:{s['service']} | ${my_rate} | {s['name'][:15]}..", callback_data=f"DESC|{s['service']}|{my_rate}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="BACK"))
    bot.edit_message_text(f"📂 **{cat_name}**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("DESC|"))
def desc(call):
    _, sid, rate = call.data.split("|")
    services = api.get_services()
    s = next((x for x in services if str(x['service']) == str(sid)), None)
    
    if not s: return 
    txt = (f"📦 **Service Details**\n\n🏷 **Name:** {s['name']}\n💰 **Price:** ${rate}/1k\n📉 **Min:** {s['min']} | 📈 **Max:** {s['max']}\nℹ️ **Type:** {s['type']}")
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Order Now", callback_data=f"ORD|{sid}|{rate}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data=f"CAT|0"))
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ORD|"))
def order_link(call):
    _, sid, rate = call.data.split("|")
    msg = bot.send_message(call.message.chat.id, "🔗 **Paste the Link:**")
    bot.register_next_step_handler(msg, process_link, sid, rate)

def process_link(message, sid, rate):
    msg = bot.send_message(message.chat.id, "🔢 **Enter Quantity:**")
    bot.register_next_step_handler(msg, process_qty, sid, rate, message.text)

def process_qty(message, sid, rate, link):
    try:
        qty = int(message.text)
        cost = (float(rate) / 1000) * qty
        user = users_col.find_one({"_id": message.chat.id})
        
        if user['balance'] < cost:
            bot.send_message(message.chat.id, "❌ **Insufficient Balance!** Please Deposit.")
            return

        res = api.place_order(sid, link, qty)
        if 'order' in res:
            users_col.update_one({"_id": message.chat.id}, {"$set": {"balance": user['balance']-cost}, "$inc": {"spent": cost}})
            orders_col.insert_one({"oid": res['order'], "uid": message.chat.id, "cost": cost, "status": "pending"})
            
            # Receipt Image
            receipt = graphics.create_receipt(res['order'], f"Service ID {sid}", cost)
            bot.send_photo(message.chat.id, receipt, caption="✅ **Order Successful!**")
            
            # Admin Notify
            bot.send_message(ADMIN_ID, f"🔔 Sale: ${cost} | User: {user['name']}")
            
            # Auto Post to Channel
            if PROOF_CHANNEL_ID:
                bot.send_message(PROOF_CHANNEL_ID, f"🔥 **New Order Received!**\n📦 Service: {sid}\n🔢 Qty: {qty}\n👤 User: {user['name'][0]}***")
        else:
            bot.send_message(message.chat.id, f"⚠️ Error: {res.get('error')}")
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ Invalid Number. Try again.")

# --- DEPOSIT ---
@bot.message_handler(func=lambda m: m.text == "💰 Deposit")
def deposit(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Submit TrxID", callback_data="DEP"))
    bot.send_message(message.chat.id, f"💳 **Send Money:** `01xxxxxxxxx` (Bkash/Nagad)\nRate: $1 = {EXCHANGE_RATE} BDT", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "DEP")
def dep_input(call):
    msg = bot.send_message(call.message.chat.id, "✍️ **Enter TrxID & Amount (BDT):**")
    bot.register_next_step_handler(msg, lambda m: bot.send_message(ADMIN_ID, f"💰 **Deposit Req:**\n{m.text}\nUser: {m.chat.id}"))
