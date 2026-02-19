from flask import Flask, request, render_template, session, redirect, url_for
import telebot
from telebot import types
import os
import threading
from datetime import datetime

# আপনার অন্য ফাইলগুলো থেকে প্রয়োজনীয় সবকিছু ইম্পোর্ট করা হচ্ছে
from config import BOT_TOKEN, ADMIN_PASSWORD, SECRET_KEY, ADMIN_ID
from loader import bot, users_col, orders_col, trx_col
import handlers  # এটি আপনার বটের মেসেজ হ্যান্ডলারগুলো সচল রাখবে
import api       # এটি 1xPanel API কানেকশন সামলাবে

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ---------------------------------------------------------------------
# ১. অ্যাডমিন ড্যাশবোর্ড লজিক (WEB ADMIN PANEL)
# ---------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # এখানে পাসওয়ার্ড চেক করা হয় (যা আপনি Render Env এ দিয়েছেন)
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('login.html', error="Invalid Security Code!")
    return render_template('login.html')

@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # ডাটাবেস থেকে রিয়েল-টাইম তথ্য সংগ্রহ
    total_users = users_col.count_documents({})
    total_orders = orders_col.count_documents({})
    
    # মোট কত টাকা খরচ হয়েছে (Revenue) তা ক্যালকুলেট করা
    all_users = list(users_col.find().sort("joined_at", -1))
    revenue = sum(u.get('spent', 0) for u in all_users)
    
    # API ব্যালেন্স চেক (1xPanel থেকে)
    try:
        api_bal = api.get_balance()
        api_status = f"ONLINE (${api_bal})"
    except:
        api_status = "OFFLINE 🔴"

    stats = {
        'users': total_users,
        'orders': total_orders,
        'revenue': round(revenue, 2),
        'api_status': api_status
    }
    
    # ড্যাশবোর্ডে শেষ ৫০ জন ইউজারের লিস্ট পাঠানো হচ্ছে
    return render_template('admin.html', stats=stats, users=all_users[:50])

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# --- ব্রডকাস্ট (ওয়েব প্যানেল থেকে সবাইকে মেসেজ পাঠানো) ---
@app.route('/send_broadcast', methods=['POST'])
def send_broadcast():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    msg_text = request.form.get('msg')
    users = users_col.find({})
    
    def run_broadcast():
        for user in users:
            try:
                bot.send_message(user['_id'], f"📢 **ADMIN MESSAGE**\n\n{msg_text}", parse_mode="Markdown")
            except:
                pass # ব্লকড ইউজারদের জন্য স্কিপ করবে
    
    # ব্যাকগ্রাউন্ডে ব্রডকাস্ট চলবে যাতে ওয়েব পেজ হ্যাং না হয়
    threading.Thread(target=run_broadcast).start()
    return redirect(url_for('admin_dashboard'))

# --- ইউজারকে ব্যালেন্স দেওয়া (Web Action) ---
@app.route('/add_balance/<int:user_id>', methods=['POST'])
def add_balance_web(user_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    try:
        amount = float(request.form.get('amount'))
        users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})
        
        # ইউজারকে নোটিফিকেশন পাঠানো
        bot.send_message(user_id, f"💰 **Admin added ${amount} to your wallet!**\nHappy Ordering! 🚀")
    except:
        pass
        
    return redirect(url_for('admin_dashboard'))

# --- ইউজার ব্যান করা ---
@app.route('/ban_user/<int:user_id>')
def ban_user(user_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    # ইউজারের ব্যালেন্স লক করা (ব্যান করার একটি উপায়)
    users_col.update_one({"_id": user_id}, {"$set": {"balance": -999999}})
    try:
        bot.send_message(user_id, "🚫 **Your account has been BANNED by the Admin.**")
    except:
        pass
    
    return redirect(url_for('admin_dashboard'))

# ---------------------------------------------------------------------
# ২. টেলিগ্রাম ওয়েবহুক সেটিংস (BOT CONNECTION)
# ---------------------------------------------------------------------

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        return "Forbidden", 403

@app.route("/")
def index():
    # এটি আপনার বটের হোমপেজ এবং এটি অটোমেটিক ওয়েবহুক সেট করবে
    bot.remove_webhook()
    render_url = os.environ.get('RENDER_EXTERNAL_URL')
    
    if render_url:
        # শেষে স্ল্যাশ থাকলে তা সরিয়ে ফেলা হচ্ছে সেফটির জন্য
        clean_url = render_url.rstrip('/')
        bot.set_webhook(url=f"{clean_url}/{BOT_TOKEN}")
        return f"<body style='background:#0f172a; color:white; text-align:center; padding-top:100px; font-family:sans-serif;'>" \
               f"<h1 style='color:#38bdf8;'>🚀 SMM Bot System is ONLINE!</h1>" \
               f"<p>Connected to Telegram Webhook successfully.</p>" \
               f"<p>Webhook URL: {clean_url}</p></body>", 200
    else:
        return "❌ ERROR: RENDER_EXTERNAL_URL is not set in Environment Variables!", 500

# ---------------------------------------------------------------------
# ৩. সার্ভার রান করা
# ---------------------------------------------------------------------

if __name__ == "__main__":
    # Render পোর্ট ম্যানেজমেন্ট
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
