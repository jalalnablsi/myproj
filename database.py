import sqlite3
import logging
import uuid
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_path='ichanci_bot.db'):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self):
        return sqlite3.connect(self.db_path)
    
    def init_database(self):
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            # جدول المستخدمين
            c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                referral_code TEXT UNIQUE NOT NULL,
                referred_by INTEGER,
                balance REAL DEFAULT 0.0,
                total_earnings REAL DEFAULT 0.0,
                total_deposits REAL DEFAULT 0.0,
                total_withdrawals REAL DEFAULT 0.0,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')
            
            # جدول الإحالات
            c.execute('''CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL,
                earned_amount REAL DEFAULT 0.0,
                commission_rate REAL DEFAULT 0.05,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (id),
                FOREIGN KEY (referred_id) REFERENCES users (id)
            )''')
            
            # جدول العمليات المالية
            c.execute('''CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                type TEXT NOT NULL, -- deposit, withdrawal, referral_bonus
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'USD',
                payment_method TEXT, -- usdt, shamcash, certil
                payment_address TEXT,
                transaction_hash TEXT,
                status TEXT DEFAULT 'pending',
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )''')
            
            # جدول طلبات السحب
            c.execute('''CREATE TABLE IF NOT EXISTS withdrawal_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                payment_method TEXT NOT NULL,
                payment_details TEXT,
                status TEXT DEFAULT 'pending',
                admin_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )''')
            
            # جدول حسابات ichancy (الجدول المفقود)
            c.execute('''CREATE TABLE IF NOT EXISTS ichancy_accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                telegram_id INTEGER NOT NULL,
                username TEXT,
                email TEXT,
                password TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )''')
            
            conn.commit()
            conn.close()
            logger.info("✅ قاعدة البيانات جاهزة")
            
        except Exception as e:
            logger.error(f"❌ خطأ في قاعدة البيانات: {e}")
    
    def create_user(self, telegram_id, username, first_name, last_name, referral_code=None):
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            # التحقق من وجود المستخدم
            c.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            if c.fetchone():
                conn.close()
                return True
            
            # إنشاء كود إحالة فريد
            user_referral_code = str(uuid.uuid4())[:12].upper()
            
            # إنشاء المستخدم
            c.execute("""INSERT INTO users 
                        (telegram_id, username, first_name, last_name, referral_code)
                        VALUES (?, ?, ?, ?, ?)""",
                     (telegram_id, username, first_name, last_name, user_referral_code))
            
            user_id = c.lastrowid
            
            # ربط الإحالة إذا وجدت
            if referral_code:
                c.execute("SELECT id FROM users WHERE referral_code = ?", (referral_code,))
                referrer = c.fetchone()
                if referrer:
                    referrer_id = referrer[0]
                    c.execute("UPDATE users SET referred_by = ? WHERE id = ?", (referrer_id, user_id))
                    logger.info(f"مستخدم {telegram_id} انضم عبر إحالة {referrer_id}")
            
            conn.commit()
            conn.close()
            logger.info(f"✅ مستخدم جديد: {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء المستخدم: {e}")
            return False
    
    def get_user_info(self, telegram_id):
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            c.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
            result = c.fetchone()
            conn.close()
            
            if result:
                return {
                    'id': result[0],
                    'telegram_id': result[1],
                    'username': result[2],
                    'first_name': result[3],
                    'last_name': result[4],
                    'referral_code': result[5],
                    'referred_by': result[6],
                    'balance': result[7],
                    'total_earnings': result[8],
                    'total_deposits': result[9],
                    'total_withdrawals': result[10],
                    'status': result[11],
                    'created_at': result[12],
                    'updated_at': result[13]
                }
            return None
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على معلومات المستخدم: {e}")
            return None
    
    def get_user_balance(self, telegram_id):
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            c.execute("SELECT balance, total_earnings FROM users WHERE telegram_id = ?", 
                     (telegram_id,))
            result = c.fetchone()
            conn.close()
            return result
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على الرصيد: {e}")
            return None
    
    def get_user_referrals(self, telegram_id):
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            # الحصول على معرف المستخدم
            c.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user_result = c.fetchone()
            if not user_result:
                conn.close()
                return []
            
            user_id = user_result[0]
            
            # الحصول على الإحالات
            c.execute("""SELECT u.username, u.first_name, u.created_at, r.earned_amount 
                        FROM referrals r 
                        JOIN users u ON r.referred_id = u.id 
                        WHERE r.referrer_id = ? 
                        ORDER BY r.created_at DESC""", (user_id,))
            
            referrals = c.fetchall()
            conn.close()
            return referrals
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على الإحالات: {e}")
            return []
    
    def add_transaction(self, user_id, transaction_type, amount, payment_method=None, description=None):
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            c.execute("""INSERT INTO transactions 
                        (user_id, type, amount, payment_method, description)
                        VALUES (?, ?, ?, ?, ?)""",
                     (user_id, transaction_type, amount, payment_method, description))
            
            transaction_id = c.lastrowid
            conn.commit()
            conn.close()
            return transaction_id
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة عملية: {e}")
            return None
    
    def get_user_transactions(self, telegram_id, limit=10):
        try:
            conn = self.get_connection()
            c = conn.cursor()
            
            c.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
            user_result = c.fetchone()
            if not user_result:
                conn.close()
                return []
            
            user_id = user_result[0]
            
            c.execute("""SELECT type, amount, payment_method, status, created_at 
                        FROM transactions 
                        WHERE user_id = ? 
                        ORDER BY created_at DESC 
                        LIMIT ?""", (user_id, limit))
            
            transactions = c.fetchall()
            conn.close()
            return transactions
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على العمليات: {e}")
            return []

# اختبار سريع
if __name__ == "__main__":
    db = DatabaseManager()
    print("✅ قاعدة البيانات جاهزة!  ")