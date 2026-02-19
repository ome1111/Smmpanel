from flask import Flask, request, render_template, session, redirect, url_for, flash
from telebot import types
import os
from config import BOT_TOKEN, ADMIN_PASSWORD, SECRET_KEY
from loader import bot, users_col, orders_col, trx_col
import handlers  # মেইন বটের লজিক

app = Flask(__name__)
app.secret_key = SECRET_KEY

# --- ১. অ্যাডমিন ড্যাশবোর্ড (লগিন চেক সহ) ---
@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'): return redirect('/login')
    
    # স্ট্যাটাস লোড করা
    users = list(users_col.find().sort("joined_at", -1).limit(50)) # শেষ ৫০ জন ইউজার
    stats = {
        'users': users_col.count_documents({}),
        'orders': orders_col.count_documents({}),
        'revenue': sum(u.get('spent', 0) for u in users),
        'api_status': "ONLINE 🟢"
    }
    return render_template('admin.html', stats=stats, users=users)

# --- ২. লগিন সিস্টেম ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect('/admin')
        return render_template('login.html', error="❌ Wrong Password")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect('/login')

# --- ৩. ব্রডকাস্ট (মেসেজ পাঠানো) ---
@app.route('/send_broadcast', methods=['POST'])
def send_broadcast():
    if not session.get('logged_in'): return redirect('/login')
    msg = request.form.get('msg')
    
    # সব ইউজারকে মেসেজ পাঠানো
    users = users_col.find({})
    count = 0
    for user in users:
        try:
            bot.send_message(user['_id'], f"📢 **NOTICE**\n\n{msg}", parse_mode="Markdown")
            count += 1
        except: pass
    
    return redirect('/admin')

# --- ৪. ইউজার কন্ট্রোল (ব্যালেন্স দেওয়া / ব্যান করা) ---
# (এই নতুন ফিচারগুলো প্রো প্যানেলের জন্য)

@app.route('/add_balance/<int:user_id>', methods=['POST'])
def add_balance_web(user_id):
    if not session.get('logged_in'): return redirect('/login')
    amount = float(request.form.get('amount'))
    
    users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})
    bot.send_message(user_id, f"🎉 **Admin added ${amount} to your balance!**")
    return redirect('/admin')

@app.route('/ban_user/<int:user_id>')
def ban_user(user_id):
    if not session.get('logged_in'): return redirect('/login')
    # ব্যান লজিক (ডাটাবেসে ফ্ল্যাগ সেট করা)
    # আপাতত আমরা ব্যালেন্স ০ করে দিচ্ছি বা ওয়ার্নিং দিচ্ছি
    bot.send_message(user_id, "🚫 **You have been BANNED by Admin!**")
    return redirect('/admin')

# --- ৫. টেলিগ্রাম ওয়েবহুক (বট রানিং রাখার জন্য) ---
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def webhook():
    bot.remove_webhook()
    url = os.environ.get('RENDER_EXTERNAL_URL')
    if url:
        bot.set_webhook(url=url + "/" + BOT_TOKEN)
        return "🔥 Bot is Running Smoothly!", 200
    return "⚠️ Please set RENDER_EXTERNAL_URL in settings.", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 5000)))
