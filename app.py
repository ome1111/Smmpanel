import os
import threading
import time
from datetime import datetime

# Flask ও অন্যান্য ওয়েব কম্পোনেন্ট
from flask import Flask, request, render_template, session, redirect, url_for, flash, jsonify
import telebot
from telebot import types

# আপনার নিজস্ব মডিউলগুলো
from config import BOT_TOKEN, ADMIN_PASSWORD, SECRET_KEY, ADMIN_ID
from loader import bot, users_col, orders_col, trx_col
import handlers  # এটি বটের সব কমান্ড হ্যান্ডল করবে
import api       # 1xPanel API কানেকশন

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ---------------------------------------------------------------------
# ১. হোমপেজ এবং স্ট্যাটাস চেক (Index Route)
# ---------------------------------------------------------------------

@app.route("/")
def index():
    """সার্ভার রান হচ্ছে কি না তা চেক করার জন্য মেইন পেজ"""
    render_url = os.environ.get('RENDER_EXTERNAL_URL', 'Your Render URL')
    
    # অটোমেটিক ওয়েবহুক সেট করার চেষ্টা করবে যখনই কেউ হোমপেজে আসবে
    try:
        bot.remove_webhook()
        time.sleep(1)
        bot.set_webhook(url=f"{render_url.rstrip('/')}/{BOT_TOKEN}")
        status = "Webhook Connected ✅"
    except Exception as e:
        status = f"Webhook Error: {e} ❌"

    return render_template('index.html', status=status, url=render_url)

# ---------------------------------------------------------------------
# ২. অ্যাডমিন লগইন ও সিকিউরিটি (Admin Authentication)
# ---------------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        entered_password = request.form.get('password')
        if entered_password == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['login_time'] = str(datetime.now())
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid Security Code! Try again.", "danger")
            return render_template('login.html', error="Wrong Password")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# ---------------------------------------------------------------------
# ৩. অ্যাডমিন ড্যাশবোর্ড লজিক (The Master Control)
# ---------------------------------------------------------------------

@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # ডাটাবেস থেকে রিয়েল-টাইম ডাটা সংগ্রহ
    try:
        total_users = users_col.count_documents({})
        total_orders = orders_col.count_documents({})
        recent_users = list(users_col.find().sort("joined_at", -1).limit(100))
        
        # ক্যালকুলেশন: মোট ইনকাম ও ইউজারের খরচ
        total_revenue = sum(u.get('spent', 0) for u in users_col.find())
        total_wallet_balance = sum(u.get('balance', 0) for u in users_col.find())
        
        # API ব্যালেন্স চেক
        api_balance = api.get_balance()
    except Exception as e:
        print(f"Dashboard Data Error: {e}")
        total_users = 0
        total_orders = 0
        recent_users = []
        total_revenue = 0
        total_wallet_balance = 0
        api_balance = "N/A"

    stats = {
        'users': total_users,
        'orders': total_orders,
        'revenue': round(total_revenue, 2),
        'wallet': round(total_wallet_balance, 2),
        'api_bal': api_balance,
        'time': datetime.now().strftime("%I:%M %p")
    }
    
    return render_template('admin.html', stats=stats, users=recent_users)

# ---------------------------------------------------------------------
# ৪. ইউজার ম্যানেজমেন্ট অ্যাকশন (Web Actions)
# ---------------------------------------------------------------------

@app.route('/add_balance/<int:user_id>', methods=['POST'])
def add_balance_web(user_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    amount = float(request.form.get('amount', 0))
    if amount > 0:
        users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})
        # ইউজারকে টেলিগ্রামে নোটিফাই করা
        try:
            bot.send_message(user_id, f"💳 **Deposit Successful!**\nAdmin added **${amount}** to your account. 🚀", parse_mode="Markdown")
        except: pass
        flash(f"Added ${amount} to User {user_id}", "success")
    return redirect(url_for('admin_dashboard'))

@app.route('/ban_user/<int:user_id>')
def ban_user(user_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    # ব্যালেন্স -৯৯৯৯৯ করে ইউজারকে ইনঅ্যাক্টিভ করা
    users_col.update_one({"_id": user_id}, {"$set": {"is_banned": True, "balance": -99999}})
    flash(f"User {user_id} has been BANNED.", "warning")
    return redirect(url_for('admin_dashboard'))

# ---------------------------------------------------------------------
# ৫. ব্রডকাস্ট সিস্টেম (Broadcast to All Users)
# ---------------------------------------------------------------------

@app.route('/send_broadcast', methods=['POST'])
def send_broadcast():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    msg_text = request.form.get('msg')
    
    def broadcast_task(text):
        all_users = users_col.find({})
        count = 0
        for user in all_users:
            try:
                bot.send_message(user['_id'], f"📢 **IMPORTANT ANNOUNCEMENT**\n\n{text}", parse_mode="Markdown")
                count += 1
                time.sleep(0.1) # টেলিগ্রাম লিমিট এড়াতে ছোট বিরতি
            except:
                continue
        print(f"Broadcast finished. Sent to {count} users.")

    threading.Thread(target=broadcast_task, args=(msg_text,)).start()
    flash("Broadcast started in background...", "info")
    return redirect(url_for('admin_dashboard'))

# ---------------------------------------------------------------------
# ৬. টেলিগ্রাম ওয়েবহুক রিসিভার (Telegram Webhook)
# ---------------------------------------------------------------------

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    else:
        return "Access Denied", 403

# ---------------------------------------------------------------------
# ৭. সার্ভার এবং পোর্ট সেটিংস (Render Deployment Fix)
# ---------------------------------------------------------------------

if __name__ == "__main__":
    # Render অটোমেটিক PORT এনভায়রনমেন্ট ভেরিয়েবল প্রদান করে
    port = int(os.environ.get("PORT", 5000))
    
    # মাল্টি-থ্রেডিং সাপোর্ট সহ ফ্লাস্ক রান করা
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
