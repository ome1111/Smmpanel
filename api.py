from flask import Flask, request, render_template, session, redirect, url_for, flash
from telebot import types
import os
import time
from config import BOT_TOKEN, ADMIN_PASSWORD, SECRET_KEY
from loader import bot, users_col, orders_col, trx_col
import handlers  # এটি বটের মেসেজ হ্যান্ডলারগুলোকে সচল রাখে
import api       # SMM API কানেকশন

app = Flask(__name__)
app.secret_key = SECRET_KEY

# ---------------------------------------------------------------------
# ১. হোমপেজ ও ওয়েব-হুক সেটআপ (Index Route)
# ---------------------------------------------------------------------
@app.route("/")
def index():
    """এই লিঙ্কটি ব্রাউজারে ওপেন করলেই বট টেলিগ্রামের সাথে কানেক্ট হবে"""
    raw_url = os.environ.get('RENDER_EXTERNAL_URL')
    
    if not raw_url:
        return "<h1>⚠️ Error</h1><p>RENDER_EXTERNAL_URL is not set in Render Settings!</p>", 500

    # স্ল্যাশ ঝামেলা এড়াতে rstrip ব্যবহার
    base_url = raw_url.rstrip('/')
    webhook_url = f"{base_url}/{BOT_TOKEN}"
    
    try:
        # পুরনো ওয়েব-হুক সরিয়ে নতুনটি সেট করা
        bot.remove_webhook()
        time.sleep(1) 
        bot.set_webhook(url=webhook_url)
        status = "✅ Webhook Connected Successfully!"
    except Exception as e:
        status = f"❌ Webhook Error: {str(e)}"

    # সরাসরি হোমপেজ ডিজাইন (Template ছাড়াও কাজ করবে)
    return f"""
    <body style='background:#0f172a; color:white; font-family:sans-serif; text-align:center; padding-top:100px;'>
        <h1 style='color:#38bdf8;'>🚀 SMM Bot System</h1>
        <p style='font-size:18px;'>Status: <b>{status}</b></p>
        <p>Target URL: <code style='background:#1e293b; padding:5px;'>{webhook_url}</code></p>
        <hr style='width:300px; border:0.5px solid #334155; margin: 20px auto;'>
        <a href='/admin' style='color:#38bdf8; text-decoration:none;'>Go to Admin Dashboard &rarr;</a>
    </body>
    """, 200

# ---------------------------------------------------------------------
# ২. টেলিগ্রাম ওয়েব-হুক রিসিভার (POST Method)
# ---------------------------------------------------------------------
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        
        # Render লগে মেসেজ ট্র্যাকিং (Debug)
        print(f"📩 Incoming Message: {json_string[:100]}...") 
        
        update = types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

# ---------------------------------------------------------------------
# ৩. অ্যাডমিন প্যানেল লজিক
# ---------------------------------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form.get('password') == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        return render_template('login.html', error="❌ Invalid Password")
    return render_template('login.html')

@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'): 
        return redirect(url_for('login'))
    
    try:
        # ডাটাবেস থেকে তথ্য আনা
        all_users = list(users_col.find().sort("joined_at", -1).limit(100))
        stats = {
            'users': users_col.count_documents({}),
            'orders': orders_col.count_documents({}),
            'revenue': round(sum(u.get('spent', 0) for u in users_col.find()), 2),
            'api_bal': api.get_balance()
        }
    except Exception as e:
        print(f"DB Error: {e}")
        stats = {'users': 0, 'orders': 0, 'revenue': 0, 'api_bal': "Error"}
        all_users = []

    return render_template('admin.html', stats=stats, users=all_users)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# ---------------------------------------------------------------------
# ৪. ইউজার কন্ট্রোল ও ব্রডকাস্ট
# ---------------------------------------------------------------------
@app.route('/add_balance/<int:user_id>', methods=['POST'])
def add_balance_web(user_id):
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    amount = float(request.form.get('amount', 0))
    if amount > 0:
        users_col.update_one({"_id": user_id}, {"$inc": {"balance": amount}})
        try:
            bot.send_message(user_id, f"💰 **Deposit Success!**\nAdmin added **${amount}** to your balance.", parse_mode="Markdown")
        except: pass
    return redirect(url_for('admin_dashboard'))

@app.route('/send_broadcast', methods=['POST'])
def send_broadcast():
    if not session.get('logged_in'): return redirect(url_for('login'))
    
    msg_text = request.form.get('msg')
    def run_broadcast():
        for user in users_col.find({}):
            try:
                bot.send_message(user['_id'], f"📢 **NOTICE**\n\n{msg_text}", parse_mode="Markdown")
            except: pass
            
    import threading
    threading.Thread(target=run_broadcast).start()
    return redirect(url_for('admin_dashboard'))

# ---------------------------------------------------------------------
# ৫. সার্ভার রান করা
# ---------------------------------------------------------------------
if __name__ == "__main__":
    # Render-এর জন্য PORT এবং host সেটআপ
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
