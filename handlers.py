from telebot import types
from loader import bot, users_col, orders_col
from config import *
import api
import graphics
from datetime import datetime
import time

# --- ১. সাহায্যকারী ফাংশনসমূহ (Helpers) ---

def get_user(chat_id, name, ref_id=None):
    """ইউজার ডাটাবেসে না থাকলে নতুন ইউজার তৈরি করে"""
    user = users_col.find_one({"_id": chat_id})
    if not user:
        user = {
            "_id": chat_id, 
            "name": name, 
            "balance": 0.0, 
            "spent": 0.0,
            "ref_by": ref_id, 
            "joined_at": datetime.now()
        }
        users_col.insert_one(user)
        # রেফারেল বোনাস নোটিফিকেশন
        if ref_id:
            try:
                bot.send_message(ref_id, f"🎉 **New Referral!** {name} joined via your link.")
            except: pass
    return user

def check_sub(chat_id):
    """ফোর্স সাবস্ক্রাইব চেক করা"""
    if not FORCE_SUB_CHANNEL: return True
    try:
        member = bot.get_chat_member(FORCE_SUB_CHANNEL, chat_id)
        if member.status in ['left', 'kicked']: return False
        return True
    except:
        return True # এরর হলে আমরা ইউজারকে আটকে দেব না

def main_menu():
    """বটের মেইন রিপ্লাই কিবোর্ড"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 New Order", "👤 Profile")
    markup.add("💰 Deposit", "📦 Orders")
    markup.add("🎧 Support")
    return markup

# --- ২. স্টার্ট কমান্ড ও চ্যানেল সাবস্ক্রিপশন ---

@bot.message_handler(commands=['start'])
def start(message):
    try:
        ref_id = None
        args = message.text.split()
        # রেফারেল আইডি চেক
        if len(args) > 1 and args[1].isdigit():
            if int(args[1]) != message.chat.id:
                ref_id = int(args[1])

        user = get_user(message.chat.id, message.from_user.first_name, ref_id)

        # সাবস্ক্রিপশন চেক
        if not check_sub(message.chat.id):
            markup = types.InlineKeyboardMarkup()
            btn_url = f"https://t.me/{FORCE_SUB_CHANNEL.replace('@','')}"
            markup.add(types.InlineKeyboardButton("✈️ Join Channel", url=btn_url))
            markup.add(types.InlineKeyboardButton("✅ Joined", callback_data="CHECK_SUB"))
            bot.send_message(message.chat.id, f"⚠️ **Please join our channel first:**\n{FORCE_SUB_CHANNEL}", reply_markup=markup)
            return

        # ওয়েলকাম ইমেজ পাঠানো (নিরাপদভাবে)
        try:
            photo = graphics.create_welcome(user['name'])
            bot.send_photo(message.chat.id, photo, caption="🚀 **Welcome to the Best SMM Panel!**", reply_markup=main_menu())
        except Exception as e:
            print(f"Graphics Error: {e}")
            bot.send_message(message.chat.id, f"👋 Welcome **{user['name']}**!", reply_markup=main_menu())
    except Exception as e:
        print(f"General Start Error: {e}")

@bot.callback_query_handler(func=lambda c: c.data == "CHECK_SUB")
def sub_check_callback(call):
    if check_sub(call.message.chat.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ **Verified!**", reply_markup=main_menu())
    else:
        bot.answer_callback_query(call.id, "❌ Not Joined Yet!", show_alert=True)

# --- ৩. প্রোফাইল সেকশন ---

@bot.message_handler(func=lambda m: m.text == "👤 Profile")
def profile(message):
    user = users_col.find_one({"_id": message.chat.id})
    if not user: return
    
    try:
        photo = graphics.create_profile(user['name'], user['_id'], user['balance'], user['spent'])
        bot.send_photo(message.chat.id, photo, caption=f"🔗 **Referral Link:**\n`https://t.me/{bot.get_me().username}?start={user['_id']}`", parse_mode="Markdown")
    except:
        txt = f"👤 **Profile Info**\n\n🆔 ID: `{user['_id']}`\n💰 Balance: ${user['balance']}\n📊 Spent: ${user['spent']}"
        bot.send_message(message.chat.id, txt, parse_mode="Markdown")

# --- ৪. অর্ডার সিস্টেম (New Order) ---

@bot.message_handler(func=lambda m: m.text == "🚀 New Order")
def show_categories(message):
    if not check_sub(message.chat.id): return
    
    msg = bot.send_message(message.chat.id, "🔄 **Fetching Services...**")
    services = api.get_services()
    
    if not services:
        bot.edit_message_text("⚠️ **Server Busy or API Error.** Try again.", message.chat.id, msg.message_id)
        return

    cats = sorted(list(set(s['category'] for s in services)))
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, cat in enumerate(cats[:50]): # লিমিট রাখা যাতে বাটন এরর না হয়
        markup.add(types.InlineKeyboardButton(cat, callback_data=f"CAT|{i}"))
    
    bot.edit_message_text(f"📂 **Select Category:**", message.chat.id, msg.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("CAT|"))
def show_services(call):
    idx = int(call.data.split("|")[1])
    services = api.get_services()
    cats = sorted(list(set(s['category'] for s in services)))
    
    if idx >= len(cats): return
    cat_name = cats[idx]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    # ক্যাটাগরি অনুযায়ী সার্ভিস ফিল্টার
    filtered_services = [s for s in services if s['category'] == cat_name]
    
    for s in filtered_services[:20]: # এক পেজে ২০টির বেশি বাটন না দেওয়াই ভালো
        rate = float(s['rate'])
        # প্রফিট মার্জিন যোগ করা (config থেকে)
        my_rate = round(rate + (rate * PROFIT_MARGIN / 100), 3)
        markup.add(types.InlineKeyboardButton(f"ID:{s['service']} | ${my_rate} | {s['name'][:20]}..", callback_data=f"DESC|{s['service']}|{my_rate}"))
    
    markup.add(types.InlineKeyboardButton("🔙 Back to Categories", callback_data="BACK_TO_CATS"))
    bot.edit_message_text(f"📂 **{cat_name}**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "BACK_TO_CATS")
def back_cats(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_categories(call.message)

@bot.callback_query_handler(func=lambda c: c.data.startswith("DESC|"))
def service_desc(call):
    _, sid, rate = call.data.split("|")
    services = api.get_services()
    s = next((x for x in services if str(x['service']) == str(sid)), None)
    
    if not s: return 
    txt = (f"📦 **Service Details**\n\n🏷 **Name:** {s['name']}\n💰 **Price:** ${rate}/1k\n📉 **Min:** {s['min']} | 📈 **Max:** {s['max']}\nℹ️ **Description:** {s.get('description', 'No description available.')}")
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ Order Now", callback_data=f"ORD|{sid}|{rate}"))
    markup.add(types.InlineKeyboardButton("🔙 Back", callback_data="BACK_TO_CATS"))
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ORD|"))
def order_link_input(call):
    _, sid, rate = call.data.split("|")
    msg = bot.send_message(call.message.chat.id, "🔗 **Paste the Link:**\n(Example: Instagram profile or post link)")
    bot.register_next_step_handler(msg, process_link, sid, rate)

def process_link(message, sid, rate):
    link = message.text
    msg = bot.send_message(message.chat.id, "🔢 **Enter Quantity:**")
    bot.register_next_step_handler(msg, process_qty, sid, rate, link)

def process_qty(message, sid, rate, link):
    try:
        qty = int(message.text)
        cost = round((float(rate) / 1000) * qty, 3)
        user = users_col.find_one({"_id": message.chat.id})
        
        if user['balance'] < cost:
            bot.send_message(message.chat.id, f"❌ **Insufficient Balance!**\nRequired: ${cost}\nYour Balance: ${user['balance']}\n\nPlease /deposit first.")
            return

        # এপিআই এর মাধ্যমে অর্ডার দেওয়া
        res = api.place_order(sid, link, qty)
        
        if 'order' in res:
            # ডাটাবেস আপডেট
            users_col.update_one({"_id": message.chat.id}, {"$inc": {"balance": -cost, "spent": cost}})
            orders_col.insert_one({
                "oid": res['order'], "uid": message.chat.id, "sid": sid, 
                "link": link, "qty": qty, "cost": cost, "status": "pending", "date": datetime.now()
            })
            
            # সাকসেস মেসেজ ও ইমেজ
            try:
                receipt = graphics.create_receipt(res['order'], f"Service ID {sid}", cost)
                bot.send_photo(message.chat.id, receipt, caption=f"✅ **Order Successful!**\nOrderID: `{res['order']}`")
            except:
                bot.send_message(message.chat.id, f"✅ **Order Successful!**\nOrderID: `{res['order']}`\nCost: ${cost}")
            
            # অ্যাডমিন নোটিফিকেশন
            try: bot.send_message(ADMIN_ID, f"🔔 **New Order!**\nUser: {user['name']} ({message.chat.id})\nCost: ${cost}\nService: {sid}")
            except: pass
            
        else:
            bot.send_message(message.chat.id, f"⚠️ **API Error:** {res.get('error', 'Unknown Error')}")
    except ValueError:
        bot.send_message(message.chat.id, "⚠️ Invalid quantity. Please enter a number.")

# --- ৫. ডিপোজিট ও সাপোর্ট ---

@bot.message_handler(func=lambda m: m.text == "💰 Deposit")
def deposit_menu(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Submit Transaction ID", callback_data="SUBMIT_TRX"))
    bot.send_message(message.chat.id, f"💳 **Deposit Balance**\n\nRate: $1 = {EXCHANGE_RATE} BDT\nMethods: Bkash/Nagad/Rocket\nNumber: `{PAYMENT_NUMBER}`\n\nSend money then submit TrxID below.", reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "SUBMIT_TRX")
def trx_input(call):
    msg = bot.send_message(call.message.chat.id, "✍️ **Enter TrxID and Amount (BDT):**\nExample: `TRX12345 500`")
    bot.register_next_step_handler(msg, process_deposit_request)

def process_deposit_request(message):
    bot.send_message(ADMIN_ID, f"💰 **Deposit Request!**\nUser: {message.chat.id}\nDetails: {message.text}")
    bot.send_message(message.chat.id, "✅ **Request Sent!** Admin will verify and add balance soon.")

@bot.message_handler(func=lambda m: m.text == "🎧 Support")
def support(message):
    bot.send_message(message.chat.id, "👨‍💻 **Need Help?**\nContact our Admin: @YourAdminUsername")
