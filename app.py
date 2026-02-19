from flask import Flask, request, render_template, session, redirect, url_for, flash
import telebot
from telebot import types
import os
import threading
from datetime import datetime

# আপনার অন্য ফাইলগুলো থেকে ইম্পোর্ট (নিশ্চিত করুন এই ফাইলগুলো একই ফোল্ডারে আছে)
from config import BOT_TOKEN, ADMIN_PASSWORD, SECRET_KEY, ADMIN_ID
from loader import bot, users_col, orders_col, trx_col
import handlers  # এটি আপনার বটের হ্যান্ডলার ফাইল লোড করবে
import api       # API কানেকশন

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ---------------------------------------------------------
# ১. অ্যাডমিন প্যানেল লজিক (WEB INTERFACE)
# ---------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('login.html', error="Invalid Security Code!")
    return render_template('login.html')

@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    # ডাটাবেস থেকে সব ডাটা সংগ্রহ
    total_users = users_col.count_documents({})
    total_orders = orders_col.count_documents({})
    
    # রেভিনিউ ক্যালকুলেশন
    all_users = list(users_col.find().sort("joined_at", -1))
    revenue = sum(u.get('spent', 0) for u in all_users)
    
    # API স্ট্যাটাস চেক
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
    
    return render_template('admin.html', stats=stats, users=all_users[:50]) # শেষ ৫০ জন ইউজার

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# --- ব্রডকাস্টিং (সবাইকে মেসেজ পাঠানো) ---
@app.route('/send_broadcast', methods=['POST'])
def send_broadcast():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    msg_text = request.form.get('msg')
    users = users_col.find({})
    
    def broadcast_task():
        success = 0
        failed = 0
        for user in users:
            try:
                bot.send_message(user['_id'], f"📢 **ADMIN MESSAGE**\n\n{msg_text}", parse_mode="Markdown")
                success += 1
            except:
                failed += 1
        print(f"Broadcast Finished. Success: {success}, Failed: {failed}")

    # ব্রডকাস্ট ব্যাকগ্রাউন্ডে চলবে যাতে ওয়েব পেজ লোড হতে দেরি না হয়
    threading.Thread(target=broadcast_task).start()
    return redirect(url_for('admin_dashboard'))

# --- ব্যালেন্স অ্যাড করা (Web Action) ---
@app.route('/add_balance/<int:user_id>', methods=['POST'])
def add_balance_web(user_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    try:
        amount = float(request.form.get('amount'))
        users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})
        
        # ইউজারকে টেলিগ্রামে জানানো
        bot.send_message(user_id, f"💰 **Admin added ${amount} to your balance!**\nKeep ordering! 🚀")
    except Exception as e:
        print(f"Error adding balance: {e}")
        
    return redirect(url_for('admin_dashboard'))

# --- ইউজার ব্যান করা ---
@app.route('/ban_user/<int:user_id>')
def ban_user(user_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    # ব্যালেন্স মাইনাস করে দেওয়া বা ব্লকলিস্টে রাখা (আপনার পছন্দমতো)
    users_col.update_one({"_id": user_id}, {"$set": {"balance": -999999}})
    bot.send_message(user_id, "🚫 **You have been BANNED from using this bot!**")
    
    return redirect(url_for('admin_dashboard'))

# ---------------------------------------------------------
# ২. টেলিগ্রাম ওয়েবহুক (WEBHOOK SETTINGS)
# ---------------------------------------------------------

@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    json_string = request.get_data().decode('utf-8')
    update = types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/")
def webhook():
    # পুরনো ওয়েবহুক রিমুভ করে নতুন করে সেট করা
    bot.remove_webhook()
    render_url = os.environ.get('RENDER_EXTERNAL_URL') # Render এটি অটোমেটিক দেয়
    
    if render_url:
        bot.set_webhook(url=render_url + "/" + BOT_TOKEN)
        return f"<h1 style='color:green; text-align:center;'>🚀 SMM Bot System is LIVE!</h1><p style='text-align:center;'>Webhook set to: {render_url}</p>", 200
    else:
        return "<h1 style='color:red; text-align:center;'>❌ Error: RENDER_EXTERNAL_URL not found!</h1>", 500

# ---------------------------------------------------------
# ৩. সার্ভার স্টার্ট
# ---------------------------------------------------------

if __name__ == "__main__":
    # Render-এর জন্য পোর্ট সেটআপ
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
