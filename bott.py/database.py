import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_path="bot.db"):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id     INTEGER PRIMARY KEY,
                    username    TEXT DEFAULT '',
                    first_name  TEXT DEFAULT '',
                    balance     REAL DEFAULT 0,
                    join_time   TEXT
                );

                CREATE TABLE IF NOT EXISTS accounts (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone       TEXT UNIQUE,
                    code        TEXT,
                    country     TEXT,
                    sold        INTEGER DEFAULT 0,
                    buyer_id    INTEGER,
                    sold_date   TEXT
                );

                CREATE TABLE IF NOT EXISTS countries (
                    country     TEXT PRIMARY KEY,
                    price       REAL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS purchases (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id     INTEGER,
                    phone       TEXT,
                    country     TEXT,
                    price       REAL,
                    date        TEXT
                );
            """)

    # ─────────────────────── USERS ───────────────────────

    def register_user(self, user_id, username, first_name):
        with self._connect() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name, balance, join_time)
                VALUES (?, ?, ?, 0, ?)
            """, (user_id, username, first_name, datetime.now().strftime("%Y-%m-%d %H:%M")))

    def get_user(self, user_id):
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def get_all_users(self):
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM users ORDER BY user_id").fetchall()
            return [dict(r) for r in rows]

    def get_balance(self, user_id):
        with self._connect() as conn:
            row = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return row["balance"] if row else 0

    def add_balance(self, user_id, amount):
        with self._connect() as conn:
            conn.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))

    def deduct_balance(self, user_id, amount):
        with self._connect() as conn:
            conn.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, user_id))

    # ─────────────────────── ACCOUNTS ───────────────────────

    def add_account(self, phone, country, code=None):
        """أضف رقم — يقبل فورمات رقم:كود أو رقم بدون كود"""
        try:
            with self._connect() as conn:
                conn.execute("""
                    INSERT OR IGNORE INTO accounts (phone, code, country, sold)
                    VALUES (?, ?, ?, 0)
                """, (phone, code, country))
                # تأكد إن الدولة موجودة في جدول countries
                conn.execute("INSERT OR IGNORE INTO countries (country, price) VALUES (?, 0)", (country,))
            return True
        except Exception:
            return False

    def get_available_account(self, country):
        with self._connect() as conn:
            row = conn.execute("""
                SELECT * FROM accounts WHERE country = ? AND sold = 0 LIMIT 1
            """, (country,)).fetchone()
            return dict(row) if row else None

    def mark_account_sold(self, account_id, buyer_id):
        with self._connect() as conn:
            conn.execute("""
                UPDATE accounts SET sold = 1, buyer_id = ?, sold_date = ? WHERE id = ?
            """, (buyer_id, datetime.now().strftime("%Y-%m-%d %H:%M"), account_id))

    def get_country_count(self, country):
        with self._connect() as conn:
            row = conn.execute("""
                SELECT COUNT(*) as cnt FROM accounts WHERE country = ? AND sold = 0
            """, (country,)).fetchone()
            return row["cnt"] if row else 0

    # ─────────────────────── COUNTRIES ───────────────────────

    def get_all_countries_with_prices(self):
        """جلب كل الدول المضافة مع أسعارها (حتى لو ما فيها أرقام في المخزن)"""
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT country, price FROM countries ORDER BY price ASC
            """).fetchall()
            return [dict(r) for r in rows]

    def get_available_countries(self):
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT c.country, c.price
                FROM countries c
                WHERE EXISTS (
                    SELECT 1 FROM accounts a WHERE a.country = c.country AND a.sold = 0
                )
                ORDER BY c.price ASC
            """).fetchall()
            return [dict(r) for r in rows]

    def get_countries_sorted_by_price(self):
        return self.get_available_countries()

    def get_country_price(self, country):
        with self._connect() as conn:
            row = conn.execute("SELECT price FROM countries WHERE country = ?", (country,)).fetchone()
            return row["price"] if row else 0

    def set_country_price(self, country, price):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO countries (country, price) VALUES (?, ?)
                ON CONFLICT(country) DO UPDATE SET price = excluded.price
            """, (country, price))

    # ─────────────────────── PURCHASES ───────────────────────

    def add_purchase(self, user_id, phone, country, price):
        with self._connect() as conn:
            conn.execute("""
                INSERT INTO purchases (user_id, phone, country, price, date)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, phone, country, price, datetime.now().strftime("%Y-%m-%d %H:%M")))

    def get_user_purchases(self, user_id):
        with self._connect() as conn:
            rows = conn.execute("""
                SELECT p.phone, p.country, p.price, p.date, a.code
                FROM purchases p
                LEFT JOIN accounts a ON a.phone = p.phone
                WHERE p.user_id = ?
                ORDER BY p.id DESC
            """, (user_id,)).fetchall()
            return [dict(r) for r in rows]

    # ─────────────────────── STATS ───────────────────────

    def get_stats(self):
        with self._connect() as conn:
            users = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
            available = conn.execute("SELECT COUNT(*) as c FROM accounts WHERE sold = 0").fetchone()["c"]
            sold = conn.execute("SELECT COUNT(*) as c FROM accounts WHERE sold = 1").fetchone()["c"]
            revenue = conn.execute("SELECT COALESCE(SUM(price), 0) as s FROM purchases").fetchone()["s"]
            return {"users": users, "available": available, "sold": sold, "revenue": revenue}
