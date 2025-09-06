import telebot
import os
from telebot import types
from dotenv import load_dotenv
from database import DatabaseManager
import random
import sqlite3
import logging
from datetime import datetime
import json
import time
import re
import asyncio
from urllib.parse import urlparse
import json
import requests
import html
# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# تحميل المتغيرات البيئية
load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = os.getenv('ADMIN_ID')
PARENT_ID = os.getenv('PARENT_ID', '1871332')
AGENT_USERNAME = os.getenv('AGENT_USERNAME') 
AGENT_PASSWORD = os.getenv('AGENT_PASSWORD')

if not BOT_TOKEN:
    logger.error("❌ خطأ: BOT_TOKEN غير محدد في ملف .env")
    exit(1)

# إنشاء البوت وقاعدة البيانات
bot = telebot.TeleBot(BOT_TOKEN)
db = DatabaseManager()

# متغير لتخزين حالة إنشاء الحسابات
user_states = {}
user_data = {}

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user = message.from_user
    referral_code = None
    
    # التحقق من وجود كود إحالة
    if len(message.text.split()) > 1:
        referral_code = message.text.split()[1]
    
    # تسجيل المستخدم
    db.create_user(user.id, user.username, user.first_name, user.last_name, referral_code)
    
    # إنشاء القائمة الرئيسية
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('💰 محفظتي'),
        types.KeyboardButton('👥 الإحالات'),
        types.KeyboardButton('إنشاء حساب'),
        types.KeyboardButton('💳 إيداع'),
        types.KeyboardButton('📤 سحب'),
        types.KeyboardButton('📊 سجل العمليات'),
        types.KeyboardButton('👤 ملفي')
    )
    
    welcome_text = f"""
🌟 مرحباً بك {user.first_name}!

اختر من القائمة أدناه ما تريد:
"""
    
    bot.reply_to(message, welcome_text, reply_markup=markup)

# معالجة الضغط على الأزرار
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    text = message.text.strip()
    logger.info(f"مستخدم {user_id} أرسل رسالة: {text}")
    
    # التحقق مما إذا كان المستخدم في حالة إنشاء حساب
    if user_id in user_states:
        current_state = user_states[user_id]
        logger.info(f"حالة المستخدم {user_id}: {current_state}")
        
        if current_state == 'waiting_username':
            handle_username_input(message)
            return
        elif current_state == 'waiting_password':
            handle_password_input(message)
            return
    
    # معالجة الأزرار الأساسية
    if text == '💰 محفظتي':
        show_wallet(message)
    elif text == '👥 الإحالات':
        show_referrals(message)
    elif text == 'إنشاء حساب':
        show_ichancy_account(message)
    elif text == '💳 إيداع':
        show_deposit(message)
    elif text == '📤 سحب':
        show_withdrawal(message)
    elif text == '📊 سجل العمليات':
        show_transactions(message)
    elif text == '👤 ملفي':
        show_profile(message)
    elif text == 'حسابي':
        show_ichancy_account(message)
    else:
        bot.reply_to(message, "❌ زر غير مدعوم!")

def show_ichancy_account(message):
    user_id = message.from_user.id
    logger.info(f"عرض حساب ichancy للمستخدم {user_id}")
    
    conn = sqlite3.connect('ichanci_bot.db')
    c = conn.cursor()
    c.execute("SELECT * FROM ichancy_accounts WHERE telegram_id = ?", (user_id,))
    existing_account = c.fetchone()
    conn.close()
    
    if existing_account:
        username = existing_account[3]
        email = existing_account[4] 
        password = existing_account[5]
        response = f'''✅ حسابك في ichancy

📧 البريد: {email}
👤 اسم المستخدم: {username}
🔑 كلمة المرور: {password}

🔗 رابط تسجيل الدخول:
https://www.ichancy.com/'''
        bot.reply_to(message, response)
        logger.info(f"عرض حساب موجود للمستخدم {user_id}")
    else:
        user_states[user_id] = 'waiting_username'
        if user_id not in user_data:
            user_data[user_id] = {}
        logger.info(f"بدء إنشاء حساب جديد للمستخدم {user_id}")
        bot.reply_to(message, "📝 يرجى ادخال اسم المستخدم:")

def handle_username_input(message):
    user_id = message.from_user.id
    username = message.text.strip()
    logger.info(f"مستخدم {user_id} أدخل اسم المستخدم: {username}")
    
    if len(username) < 3:
        bot.reply_to(message, "❌ اسم المستخدم قصير جداً، يجب أن يكون 3 أحرف على الأقل")
        cleanup_user_state(user_id)
        return
    
    if not re.match("^[a-zA-Z0-9_-]+$", username):
        bot.reply_to(message, "❌ اسم المستخدم يجب أن يحتوي على أحرف وأرقام وشرطات فقط")
        cleanup_user_state(user_id)
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['username'] = username
    
    user_states[user_id] = 'waiting_password'
    logger.info(f"حفظ اسم المستخدم للمستخدم {user_id}: {username}")
    bot.reply_to(message, "🔑 ادخل كلمة المرور:")

def handle_password_input(message):
    user_id = message.from_user.id
    password = message.text.strip()
    logger.info(f"مستخدم {user_id} أدخل كلمة المرور")
    
    if len(password) < 6:
        bot.reply_to(message, "❌ كلمة المرور قصيرة جداً، يجب أن تكون 6 أحرف على الأقل")
        cleanup_user_state(user_id)
        return
    
    if user_id not in user_data:
        user_data[user_id] = {}
    user_data[user_id]['password'] = password
    
    username = user_data[user_id].get('username', '')
    if not username:
        username = message.from_user.username or f"user{user_id}"
        user_data[user_id]['username'] = username
    
    email = f"{username}_{random.randint(1000, 9999)}@gmail.com"
    enhanced_password = password + "@" + str(random.randint(100, 999))
    
    user_data[user_id]['email'] = email
    user_data[user_id]['enhanced_password'] = enhanced_password
    
    logger.info(f"بيانات الحساب النهائية للمستخدم {user_id}: {user_data[user_id]}")
    
    # بدء عملية إنشاء الحساب
    create_ichancy_account_with_requests(message, username, email, enhanced_password)
    
    cleanup_user_state(user_id)

def cleanup_user_state(user_id):
    """تنظيف حالة المستخدم"""
    if user_id in user_states:
        del user_states[user_id]
    if user_id in user_data:
        del user_data[user_id]

def detect_cloudflare(page):
    """كشف وجود Cloudflare"""
    try:
        content = page.content().lower()
        cloudflare_indicators = [
            'cloudflare',
            'checking your browser',
            'please wait while',
            'ray id',
            'ddos protection',
            'verifying you are human',
            'challenge-form',
            'cf-browser-verification'
        ]
        return any(indicator in content for indicator in cloudflare_indicators)
    except:
        return False

def wait_for_cloudflare_bypass(page, timeout=45):
    """انتظار تجاوز Cloudflare"""
    start_time = time.time()
    logger.info("⏳ انتظار تجاوز Cloudflare...")
    
    while time.time() - start_time < timeout:
        try:
            if not detect_cloudflare(page):
                logger.info("✅ تم تجاوز Cloudflare بنجاح""Azxs@0987")
                return True
            
            # محاولة التفاعل مع عناصر Cloudflare
            try:
                # البحث عن checkbox
                checkbox = page.query_selector('input[type="checkbox"]')
                if checkbox and checkbox.is_visible():
                    checkbox.click()
                    logger.info("✅ تم النقر على checkbox التحقق")
                    page.wait_for_timeout(3000)
            except:
                pass
            
            # البحث عن أزرار Verify
            verify_selectors = [
                'button[type="submit"]',
                'input[type="submit"]',
                'button:has-text("Verify")',
                'button:has-text("Continue")',
                'input[value="Verify"]'
            ]
            
            for selector in verify_selectors:
                try:
                    button = page.query_selector(selector)
                    if button and button.is_visible():
                        button.click()
                        logger.info(f"✅ تم النقر على زر: {selector}")
                        page.wait_for_timeout(3000)
                        break
                except:
                    continue
            
            page.wait_for_timeout(2000)
            
        except Exception as e:
            logger.warning(f"⚠️ خطأ أثناء انتظار Cloudflare: {e}")
            page.wait_for_timeout(2000)
    
    logger.error("❌ انتهى الوقت المخصص لتجاوز Cloudflare")
    return False

def human_like_type(element, text, delay_range=(50, 150)):
    """كتابة نص بشكل بشري مع تأخيرات عشوائية"""
    for char in text:
        element.type(char, delay=random.randint(*delay_range))
        time.sleep(random.uniform(0.05, 0.15))

def create_ichancy_account_with_requests(message, username, email, password):
    """إنشاء حساب باستخدام requests مع الكوكيز المحفوظة"""
    user_id = message.from_user.id
    logger.info(f"بدء إنشاء حساب باستخدام requests للمستخدم {user_id}")
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://agents.ichancy.com",
        "Referer": "https://agents.ichancy.com/",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Pragma": "no-cache",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive"
    }
    login_url = "https://agents.ichancy.com/global/api/User/signIn"
    login_data = {
        "username": AGENT_USERNAME,
        "password": AGENT_PASSWORD
    }
    print("🔐 جاري تسجيل الدخول...")
    login_response = session.post(login_url, json=login_data, headers=headers)
    if login_response.status_code != 200:
        print("❌ فشل تسجيل الدخول:", login_response.status_code)
        try:
            print("📄 التفاصيل:", login_response.json())
        except:
            print("📄 التفاصيل (نص):", login_response.text)
        return False
    print("✅ تم تسجيل الدخول بنجاح!")


    

    URL = "https://agents.ichancy.com/global/api/Player/registerPlayer"

    # --- الطلب ---
    payload = {
        "player": {
            "email": email,
            "password": password,
            "parentId": PARENT_ID,
            "login": username
        }
    }

    

    try:
        logger.info(f"إرسال طلب تسجيل لاعب: {payload}")
        response = session.post(URL, json=payload, timeout=30)

        logger.info(f"الحالة: {response.status_code}, الرد: {response.text}")

        if response.status_code == 200:
            # نجاح
            conn = sqlite3.connect('ichanci_bot.db')
            c = conn.cursor()
            c.execute("""INSERT INTO ichancy_accounts 
                        (user_id, telegram_id, username, email, password, status, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     (user_id, user_id, username, email, password, 'created', datetime.now()))
            conn.commit()
            conn.close()

            logger.info(f"✅ تم إنشاء الحساب بنجاح للمستخدم {user_id}")

            response_text = f'''✅ تم إنشاء حسابك بنجاح!

📧 البريد: {email}
👤 اسم المستخدم: {username}
🔑 كلمة المرور: <code>{password}</code>

🔗 رابط تسجيل الدخول:
<a href="https://www.ichancy.com/">https://www.ichancy.com/</a>  

⚠️ ملاحظات مهمة:
• غيّر كلمة المرور فور تسجيل الدخول
• سيتم تفعيل الحساب خلال ساعات قليلة
• احتفظ بهذه المعلومات في مكان آمن'''

            bot.reply_to(message, response_text, parse_mode='Markdown')
            update_menu_after_account_creation(message)

        elif response.status_code == 403:
            logger.warning(f"❌ رفض من Cloudflare للمستخدم {user_id}")
            bot.reply_to(message, "❌ تم رفض الطلب من قبل الحماية. يرجى المحاولة لاحقًا.")
        elif response.status_code == 400:
            logger.warning(f"❌ بيانات غير صحيحة للمستخدم {user_id}: {response.text}")
            bot.reply_to(message, "❌ بيانات غير صحيحة. يرجى المحاولة مرة أخرى.")
        else:
            logger.error(f"❌ خطأ غير متوقع: {response.status_code} - {response.text}")
            bot.reply_to(message, f"❌ خطأ: {response.status_code}. يرجى المحاولة لاحقًا.")

    except requests.exceptions.RequestException as e:
        logger.error(f"❌ خطأ في الاتصال: {e}")
        bot.reply_to(message, "❌ تعذر الاتصال بالخادم. تحقق من الإنترنت أو حاول لاحقًا.")

    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع: {e}")
        bot.reply_to(message, "❌ حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")
def update_menu_after_account_creation(message):
    """تحديث القائمة بعد إنشاء الحساب"""
    user = message.from_user
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton('💰 محفظتي'),
        types.KeyboardButton('👥 الإحالات'),
        types.KeyboardButton('حسابي'),
        types.KeyboardButton('💳 إيداع'),
        types.KeyboardButton('📤 سحب'),
        types.KeyboardButton('📊 سجل العمليات'),
        types.KeyboardButton('👤 ملفي')
    )

# دوال عرض الصفحات
def show_wallet(message):
    user_id = message.from_user.id
    user_info = db.get_user_info(user_id)
    
    if user_info:
        response = f'''💰 محفظتك

📊 الإحصائيات المالية:
• الرصيد الحالي: {user_info['balance']:.2f} دولار
• إجمالي الأرباح: {user_info['total_earnings']:.2f} دولار
• إجمالي الإيداعات: {user_info['total_deposits']:.2f} دولار
• إجمالي السحوبات: {user_info['total_withdrawals']:.2f} دولار

📈 معدل الإحالة: 5% من كل عملية شحن'''
    else:
        response = "❌ لم يتم العثور على حسابك!"
    
    bot.reply_to(message, response)

def show_referrals(message):
    user_id = message.from_user.id
    user_info = db.get_user_info(user_id)
    referrals = db.get_user_referrals(user_id)
    
    if user_info:
        referral_link = f"https://t.me/{bot.get_me().username}?start={user_info['referral_code']}"
        
        response = f'''👥 إحالاتك

📊 الإحصائيات الإحالات:
• عدد الإحالات: {len(referrals)}
• أرباح الإحالات: {user_info['total_earnings']:.2f} دولار

🔗 رابط الإحالة الخاص بك:
{referral_link}

💰 كيفية الكسب:
• احصل على 5% من كل عملية شحن لمن ت أحالهم

أحدث الإحالات:'''
        
        if referrals:
            for i, referral in enumerate(referrals[:5]):
                username = referral[0] or referral[1] or "مستخدم"
                earned = referral[3] or 0
                response += f"\n{i+1}. {username}: {earned:.2f} دولار"
        else:
            response += "\nلا توجد إحالات بعد"
        
        bot.reply_to(message, response)
    else:
        bot.reply_to(message, "❌ لم يتم العثور على حسابك!")

def show_deposit(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💳 USDT", callback_data="deposit_usdt"),
        types.InlineKeyboardButton("📱 شام كاش", callback_data="deposit_shamcash"),
        types.InlineKeyboardButton("📱 سيرتيل كاش", callback_data="deposit_certil")
    )
    
    response = '''💳 طرق الإيداع المتاحة:

اختر طريقة الإيداع التي تريدها:'''
    
    bot.reply_to(message, response, reply_markup=markup)

def show_withdrawal(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("💳 USDT", callback_data="withdraw_usdt"),
        types.InlineKeyboardButton("📱 شام كاش", callback_data="withdraw_shamcash"),
        types.InlineKeyboardButton("📱 سيرتيل كاش", callback_data="withdraw_certil")
    )
    
    response = '''📤 طرق السحب المتاحة:

اختر طريقة السحب التي تريدها:'''
    
    bot.reply_to(message, response, reply_markup=markup)

def show_transactions(message):
    transactions = db.get_user_transactions(message.from_user.id, 10)
    
    response = "📊 سجل العمليات\n\n"
    
    if transactions:
        for transaction in transactions:
            trans_type, amount, method, status, date = transaction
            type_text = {
                'deposit': '📥 إيداع',
                'withdrawal': '📤 سحب',
                'referral_bonus': '💰 مكافأة إحالة'
            }.get(trans_type, trans_type)
            
            method_text = {
                'usdt': 'USDT',
                'shamcash': 'شام كاش',
                'certil': 'سيرتيل كاش'
            }.get(method, method or 'غير محدد')
            
            status_text = {
                'pending': 'قيد الانتظار',
                'completed': 'مكتمل',
                'failed': 'فشل',
                'cancelled': 'ملغى'
            }.get(status, status)
            
            response += f"• {type_text}: {amount:.2f} دولار\n"
            response += f"  الطريقة: {method_text} | الحالة: {status_text}\n"
            response += f"  التاريخ: {date[:10]}\n\n"
    else:
        response += "📋 لا توجد عمليات حتى الآن"
    
    bot.reply_to(message, response)

def show_profile(message):
    user = message.from_user
    user_info = db.get_user_info(user.id)
    
    if user_info:
        conn = sqlite3.connect('ichanci_bot.db')
        c = conn.cursor()
        c.execute("SELECT username, email, password, status FROM ichancy_accounts WHERE telegram_id = ?", 
                  (user.id,))
        account = c.fetchone()
        conn.close()
        
        account_button_text = "حسابي" if account else "إنشاء حساب"
        
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(
            types.KeyboardButton('💰 محفظتي'),
            types.KeyboardButton('👥 الإحالات'),
            types.KeyboardButton(account_button_text),
            types.KeyboardButton('💳 إيداع'),
            types.KeyboardButton('📤 سحب'),
            types.KeyboardButton('📊 سجل العمليات'),
            types.KeyboardButton('👤 ملفي')
        )
        
        response = f'''👤 ملفك الشخصي

🆔 المعرف: {user_info['telegram_id']}
📝 الاسم: {user_info['first_name']} {user_info['last_name'] or ''}
👥 اسم المستخدم: @{user_info['username'] or 'غير متوفر'}
🔗 كود الإحالة: {user_info['referral_code']}

💰 الرصيد: {user_info['balance']:.2f} دولار
📈 إجمالي الأرباح: {user_info['total_earnings']:.2f} دولار

📅 تاريخ التسجيل: {user_info['created_at'][:10]}'''
        
        bot.reply_to(message, response, reply_markup=markup)
        
    else:
        bot.reply_to(message, "❌ لم يتم العثور على حسابك!")

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    if call.data.startswith('deposit_'):
        method = call.data.replace('deposit_', '')
        methods = {
            'usdt': 'USDT',
            'shamcash': 'شام كاش',
            'certil': 'سيرتيل كاش'
        }
        
        response = f'''💳 إيداع عبر {methods.get(method, method)}

لإتمام عملية الإيداع:
1. أرسل المبلغ الذي تريد إيداعه
2. سيتم تزويدك بتفاصيل الدفع
3. بعد التأكيد، سيتم إضافة الرصيد لمحفظتك

⚠️ ملاحظة: هذه الميزة قيد التطوير وسيتم تفعيلها قريباً!'''
        bot.answer_callback_query(call.id, f"سيتم إضافة طريقة {methods.get(method, method)} قريباً!")
        bot.send_message(user_id, response)
    
    elif call.data.startswith('withdraw_'):
        method = call.data.replace('withdraw_', '')
        methods = {
            'usdt': 'USDT',
            'shamcash': 'شام كاش',
            'certil': 'سيرتيل كاش'
        }
        
        response = f'''📤 سحب عبر {methods.get(method, method)}

لإتمام عملية السحب:
1. أدخل المبلغ الذي تريد سحبه
2. قم بتقديم تفاصيل الدفع
3. سيتم معالجة الطلب خلال 24 ساعة

⚠️ ملاحظة: هذه الميزة قيد التطوير وسيتم تفعيلها قريباً!'''
        bot.answer_callback_query(call.id, f"سيتم إضافة طريقة {methods.get(method, method)} قريباً!")
        bot.send_message(user_id, response)

# تشغيل البوت
if __name__ == "__main__":
    print("🚀 بوت ichanci قيد التشغيل...")
    print("✅ انتظر الرسائل...")
    print("📝 سجل العمليات متوفر في ملف bot.log")
    
   
    try:
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ خطأ: {e}")
        logger.error(f"خطأ في تشغيل البوت: {e}")
