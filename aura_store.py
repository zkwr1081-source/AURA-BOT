"""SQLite persistence for the AURA Commerce Telegram storefront."""
from decimal import Decimal, InvalidOperation
import sqlite3
from pathlib import Path


ORDER_STATUSES = {"new", "contacted", "confirmed", "completed", "cancelled"}


class Store:
    def __init__(self, database_path: str = "aura_store.db"):
        self.database_path = database_path
        if database_path != ":memory:":
            Path(database_path).expanduser().parent.mkdir(parents=True, exist_ok=True)
        self.initialize()

    def _connect(self):
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self):
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    telegram_user_id INTEGER NOT NULL,
                    customer_name TEXT NOT NULL,
                    username TEXT NOT NULL DEFAULT '',
                    product_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    unit_price TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'new',
                    contact TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(product_id) REFERENCES products(id)
                );
                CREATE INDEX IF NOT EXISTS idx_orders_status_created
                    ON orders(status, created_at);
                """
            )

    @staticmethod
    def _validated_price(value):
        try:
            price = Decimal(str(value).strip())
        except (InvalidOperation, ValueError):
            raise ValueError("السعر يجب أن يكون رقماً صالحاً.")
        if not price.is_finite() or price <= 0:
            raise ValueError("السعر يجب أن يكون أكبر من صفر.")
        return format(price.quantize(Decimal("0.01")), "f")

    def add_product(self, name, price, description=""):
        name = str(name).strip()
        if not name or len(name) > 120:
            raise ValueError("اسم المنتج مطلوب وبحد أقصى 120 حرفاً.")
        if len(str(description)) > 1000:
            raise ValueError("الوصف طويل جداً (الحد 1000 حرف).")
        price_text = self._validated_price(price)
        with self._connect() as db:
            cursor = db.execute(
                "INSERT INTO products(name, price, description) VALUES (?, ?, ?)",
                (name, price_text, str(description).strip()),
            )
            return cursor.lastrowid

    def get_product(self, product_id, active_only=True):
        query = "SELECT * FROM products WHERE id = ?"
        params = [int(product_id)]
        if active_only:
            query += " AND active = 1"
        with self._connect() as db:
            row = db.execute(query, params).fetchone()
            return dict(row) if row else None

    def list_products(self, active_only=True):
        query = "SELECT * FROM products"
        if active_only:
            query += " WHERE active = 1"
        query += " ORDER BY id DESC"
        with self._connect() as db:
            return [dict(row) for row in db.execute(query).fetchall()]

    def create_order(self, product_id, telegram_user_id, customer_name, username="", currency="USD"):
        with self._connect() as db:
            product = db.execute(
                "SELECT * FROM products WHERE id = ? AND active = 1",
                (int(product_id),),
            ).fetchone()
            if not product:
                raise ValueError("المنتج غير موجود أو غير متاح.")
            cursor = db.execute(
                """INSERT INTO orders
                   (telegram_user_id, customer_name, username, product_id,
                    product_name, unit_price, currency)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    int(telegram_user_id),
                    str(customer_name)[:160],
                    str(username)[:80],
                    product["id"],
                    product["name"],
                    product["price"],
                    str(currency)[:8],
                ),
            )
            return cursor.lastrowid

    def attach_contact(self, order_id, telegram_user_id, contact):
        with self._connect() as db:
            cursor = db.execute(
                """UPDATE orders SET contact = ?, status = 'contacted'
                   WHERE id = ? AND telegram_user_id = ? AND status = 'new'""",
                (str(contact).strip()[:200], int(order_id), int(telegram_user_id)),
            )
            return cursor.rowcount == 1

    def list_orders(self, limit=20):
        with self._connect() as db:
            rows = db.execute(
                "SELECT * FROM orders ORDER BY id DESC LIMIT ?",
                (max(1, min(int(limit), 100)),),
            ).fetchall()
            return [dict(row) for row in rows]

    def update_order_status(self, order_id, status):
        if status not in ORDER_STATUSES:
            raise ValueError("حالة الطلب غير صالحة.")
        with self._connect() as db:
            cursor = db.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                (status, int(order_id)),
            )
            return cursor.rowcount == 1
