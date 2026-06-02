import telebot
import os
import sqlite3
import threading
import random
from datetime import datetime, timedelta
from flask import Flask
from threading import Thread

# --- Flask Keep Alive (ضروري لـ Render) ---
app = Flask('')
@app.route('/')
def home(): return "I'am Marco File Host - Online"
def run_flask(): app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))
def keep_alive(): Thread(target=run_flask, daemon=True).start()

# --- Configuration ---
TOKEN = '8452234309:AAHRnslpCnrM2Rjnjj5F3WyyQH30mM-dHBc'
OWNER_ID = 7119011124
ADMIN_IDS = {OWNER_ID}

# إعداد المجلدات وقاعدة البيانات
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
IROTECH_DIR = os.path.join(BASE_DIR, 'inf')
os.makedirs(IROTECH_DIR, exist_ok=True)
DATABASE_PATH = os.path.join(IROTECH_DIR, 'bot_data.db')

bot = telebot.TeleBot(TOKEN)

# --- Database ---
def init_db():
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, approved INTEGER DEFAULT 0, expiry TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS vip_codes (code TEXT PRIMARY KEY, days INTEGER)''')
    conn.commit()
    conn.close()

init_db()

# --- Functions ---
def is_approved(user_id):
    if user_id in ADMIN_IDS: return True
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT approved FROM users WHERE user_id = ?", (user_id,))
    res = c.fetchone()
    conn.close()
    return res and res[0] == 1

# --- Handlers ---
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    expiry = (datetime.now() + timedelta(days=4)).isoformat()
    c.execute("INSERT OR IGNORE INTO users (user_id, approved, expiry) VALUES (?, 0, ?)", (user_id, expiry))
    conn.commit()
    conn.close()

    if not is_approved(user_id):
        bot.reply_to(message, "⏳ أهلاً بك! طلبك قيد الانتظار لموافقة الإدارة.")
        bot.send_message(OWNER_ID, f"🔔 طلب جديد: `{user_id}`", parse_mode="Markdown")
    else:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("📤 رفع ملف", "🎟️ تفعيل كود VIP", "📊 معلوماتي")
        if user_id in ADMIN_IDS: markup.add("👑 لوحة الأدمن")
        bot.reply_to(message, "✅ تم تفعيل حسابك بنجاح.", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🎟️ تفعيل كود VIP")
def vip_code(message):
    msg = bot.reply_to(message, "أرسل كود الـ VIP:")
    bot.register_next_step_handler(msg, process_vip)

def process_vip(message):
    code = message.text
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute("SELECT days FROM vip_codes WHERE code = ?", (code,))
    res = c.fetchone()
    if res:
        c.execute("DELETE FROM vip_codes WHERE code = ?", (code,))
        conn.commit()
        bot.reply_to(message, "✅ تم تفعيل اشتراك VIP!")
    else:
        bot.reply_to(message, "❌ كود غير صالح.")
    conn.close()

@bot.message_handler(func=lambda m: m.text == "👑 لوحة الأدمن" and m.from_user.id in ADMIN_IDS)
def admin(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ موافقة مستخدم", callback_data="adm_approve"))
    markup.add(types.InlineKeyboardButton("🎫 صنع كود VIP", callback_data="adm_gen"))
    bot.reply_to(message, "👑 لوحة الإدارة:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_cb(call):
    if call.data == "adm_gen":
        code = f"VIP-{random.randint(1000,9999)}"
        conn = sqlite3.connect(DATABASE_PATH)
        conn.cursor().execute("INSERT INTO vip_codes VALUES (?, 4)", (code,))
        conn.commit()
        bot.answer_callback_query(call.id, f"تم صنع كود: {code}")
    elif call.data == "adm_approve":
        msg = bot.send_message(call.message.chat.id, "أرسل ID للموافقة:")
        bot.register_next_step_handler(msg, lambda m: approve(m))

def approve(m):
    conn = sqlite3.connect(DATABASE_PATH)
    conn.cursor().execute("UPDATE users SET approved = 1 WHERE user_id = ?", (m.text,))
    conn.commit()
    conn.close()
    bot.send_message(m.chat.id, "✅ تم قبول المستخدم.")

if __name__ == '__main__':
    keep_alive()
    bot.infinity_polling()
