from telebot import types
from loader import bot, users_col, orders_col
from config import *
import api
from datetime import datetime

# --- ১. সাহায্যকারী ফাংশনসমূহ (Helpers) ---

def get_user(chat_id, name, ref_id=None):
    user = users_col.find_one({"_id": chat_id})
    if not user:
        user = {
            "_id": chat_id, "name": name, "balance": 0.0, "spent": 0.0,
            "ref_by": ref_id, "joined_at": datetime.now()
        }
        users_col.insert_one(user)
        if ref_id:
            try: bot.send_message(ref_id, f"🎉 **নতুন রেফারেল!** {name} আপনার লিঙ্কে জয়েন করেছে।")
            except: pass
    return user

def check_sub(chat_id):
    if not FORCE_SUB_CHANNEL: return True
    try:
        member = bot.get_chat_member(FORCE_SUB_CHANNEL, chat_id)
        if member.status in ['left', 'kicked']: return False
        return True
    except: return True 

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("🚀 New Order", "👤 Profile")
    markup.add("💰 Deposit", "📦 Orders")
    markup.add("🎧 Support")
    return markup

# --- ২. স্টার্ট কমান্ড (Text Style) ---

@bot.message_handler(commands=['start'])
def start(message):
    ref_id = None
    args = message.text.split()
    if len(args) > 1 and args[1].isdigit():
        if int(args[1]) != message.chat.id: ref_id = int(args[1])

    user = get_user(message.chat.id, message.from_user.first_name, ref_id)

    if not check_sub(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        btn_url = f"https://t.me/{FORCE_SUB_CHANNEL.replace('@','')}"
        markup.add(types.InlineKeyboardButton("✈️ Join Channel", url=btn_url))
        markup.add(types.InlineKeyboardButton("✅ Joined", callback_data="CHECK_SUB"))
        bot.send_message(message.chat.id, f"⚠️ **দয়া করে আগে আমাদের চ্যানেলে জয়েন করুন:**\n{FORCE_SUB_CHANNEL}", reply_markup=markup)
        return

    welcome_txt = (
        f"👋 **আসসালামু আলাইকুম, {user['name']}!**\n\n"
        f"সেরা এবং সস্তা SMM প্যানেলে আপনাকে স্বাগতম।\n"
        f"নিচের বাটনগুলো ব্যবহার করে সার্ভিস অর্ডার করুন।\n\n"
        f"🆔 **আপনার আইডি:** `{user['_id']}`"
    )
    bot.send_message(message.chat.id, welcome_txt, reply_markup=main_menu(), parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "CHECK_SUB")
def sub_check(call):
    if check_sub(call.message.chat.id):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "✅ **ভেরিফাইড!**", reply_markup=main_menu())
    else:
        bot.answer_callback_query(call.id, "❌ আপনি এখনো জয়েন করেননি!", show_alert=True)

# --- ৩. প্রোফাইল (Text Only) ---

@bot.message_handler(func=lambda m: m.text == "👤 Profile")
def profile(message):
    user = users_col.find_one({"_id": message.chat.id})
    if not user: return

    profile_txt = (
        f"👤 **আপনার প্রোফাইল তথ্য**\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 **ইউজার আইডি:** `{user['_id']}`\n"
        f"💰 **বর্তমান ব্যালেন্স:** ${user['balance']}\n"
        f"📊 **মোট খরচ:** ${user['spent']}\n"
        f"📅 **যোগদানের তারিখ:** {user['joined_at'].strftime('%d %b, %Y')}\n\n"
        f"🔗 **রেফার লিঙ্ক:**\n`https://t.me/{bot.get_me().username}?start={user['_id']}`"
    )
    bot.send_message(message.chat.id, profile_txt, parse_mode="Markdown")

# --- ৪. অর্ডার সিস্টেম (Text Layout) ---

@bot.message_handler(func=lambda m: m.text == "🚀 New Order")
def categories(message):
    if not check_sub(message.chat.id): return
    msg = bot.send_message(message.chat.id, "🔄 **সার্ভিস লিস্ট লোড হচ্ছে...**")
    
    services = api.get_services()
    if not services:
        bot.edit_message_text("⚠️ **এপিআই এরর!** পরে চেষ্টা করুন।", message.chat.id, msg.message_id)
        return

    cats = sorted(list(set(s['category'] for s in services)))
    markup = types.InlineKeyboardMarkup(row_width=1)
    for i, cat in enumerate(cats[:50]):
        markup.add(types.InlineKeyboardButton(f"📁 {cat}", callback_data=f"CAT|{i}"))
    
    bot.edit_message_text(f"📂 **ক্যাটাগরি সিলেক্ট করুন:**", message.chat.id, msg.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("CAT|"))
def show_services(call):
    idx = int(call.data.split("|")[1])
    services = api.get_services()
    cats = sorted(list(set(s['category'] for s in services)))
    cat_name = cats[idx]
    
    markup = types.InlineKeyboardMarkup(row_width=1)
    for s in [x for x in services if x['category'] == cat_name][:25]:
        rate = float(s['rate'])
        my_rate = round(rate + (rate * PROFIT_MARGIN / 100), 3)
        markup.add(types.InlineKeyboardButton(f"⚡ ID:{s['service']} | ${my_rate} | {s['name'][:20]}..", callback_data=f"DESC|{s['service']}|{my_rate}"))
    
    markup.add(types.InlineKeyboardButton("🔙 ফিরে যান", callback_data="BACK_TO_CATS"))
    bot.edit_message_text(f"📂 **{cat_name}**", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("DESC|"))
def desc(call):
    _, sid, rate = call.data.split("|")
    services = api.get_services()
    s = next((x for x in services if str(x['service']) == str(sid)), None)
    
    if not s: return 
    txt = (
        f"📦 **সার্ভিস ডিটেইলস**\n\n"
        f"🏷 **নাম:** {s['name']}\n"
        f"💰 **মূল্য:** ${rate} (প্রতি ১০০০)\n"
        f"📉 **মিনিমাম:** {s['min']}\n"
        f"📈 **ম্যাক্সিমাম:** {s['max']}\n"
        f"ℹ️ **বিস্তারিত:** {s.get('description', 'নাই')}"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ অর্ডার করুন", callback_data=f"ORD|{sid}|{rate}"))
    markup.add(types.InlineKeyboardButton("🔙 ফিরে যান", callback_data="BACK_TO_CATS"))
    bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ORD|"))
def order_link(call):
    msg = bot.send_message(call.message.chat.id, "🔗 **লিঙ্ক দিন:**\n(যেমন: প্রোফাইল বা পোস্ট লিঙ্ক)")
    bot.register_next_step_handler(msg, process_link, call.data.split("|")[1], call.data.split("|")[2])

def process_link(message, sid, rate):
    link = message.text
    msg = bot.send_message(message.chat.id, "🔢 **পরিমাণ লিখুন (Quantity):**")
    bot.register_next_step_handler(msg, process_qty, sid, rate, link)

def process_qty(message, sid, rate, link):
    try:
        qty = int(message.text)
        cost = round((float(rate) / 1000) * qty, 3)
        user = users_col.find_one({"_id": message.chat.id})
        
        if user['balance'] < cost:
            bot.send_message(message.chat.id, f"❌ **ব্যালেন্স নাই!**\nপ্রয়োজন: ${cost}\nআপনার আছে: ${user['balance']}")
            return

        res = api.place_order(sid, link, qty)
        if 'order' in res:
            users_col.update_one({"_id": message.chat.id}, {"$inc": {"balance": -cost, "spent": cost}})
            orders_col.insert_one({"oid": res['order'], "uid": message.chat.id, "sid": sid, "cost": cost, "status": "pending", "date": datetime.now()})
            
            # সাকসেস টেক্সট
            success_txt = (
                f"✅ **অর্ডার সফল হয়েছে!**\n"
                f"━━━━━━━━━━━━━━━━━━━━\n"
                f"🆔 **অর্ডার আইডি:** `{res['order']}`\n"
                f"📦 **সার্ভিস আইডি:** {sid}\n"
                f"🔢 **পরিমাণ:** {qty}\n"
                f"💰 **খরচ:** ${cost}"
            )
            bot.send_message(message.chat.id, success_txt, parse_mode="Markdown")
        else:
            bot.send_message(message.chat.id, f"⚠️ **এপিআই এরর:** {res.get('error')}")
    except:
        bot.send_message(message.chat.id, "⚠️ সঠিক পরিমাণ লিখুন।")

# --- ৫. ডিপোজিট ও সাপোর্ট ---

@bot.message_handler(func=lambda m: m.text == "💰 Deposit")
def deposit(message):
    txt = (
        f"💰 **ডিপোজিট ব্যালেন্স**\n\n"
        f"💵 **রেট:** $1 = {EXCHANGE_RATE} BDT\n"
        f"🏦 **মেথড:** বিকাশ/নগদ/রকেট\n"
        f"📞 **নাম্বার:** `{PAYMENT_NUMBER}`\n\n"
        f"টাকা পাঠানোর পর নিচের বাটনে ক্লিক করে TrxID এবং Amount জমা দিন।"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Submit TrxID", callback_data="SUBMIT_TRX"))
    bot.send_message(message.chat.id, txt, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda c: c.data == "SUBMIT_TRX")
def trx_input(call):
    msg = bot.send_message(call.message.chat.id, "✍️ **আপনার TrxID এবং টাকার পরিমাণ লিখুন:**\nউদাহরণ: `TX12345 500`")
    bot.register_next_step_handler(msg, lambda m: bot.send_message(ADMIN_ID, f"💰 **ডিপোজিট রিকোয়েস্ট:**\n{m.text}\nইউজার আইডি: {m.chat.id}"))

@bot.message_handler(func=lambda m: m.text == "🎧 Support")
def support(message):
    bot.send_message(message.chat.id, "🎧 **সাপোর্ট দরকার?**\nআমাদের এডমিনের সাথে যোগাযোগ করুন।")
