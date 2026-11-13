"""SQLite schema, connection helper, and sample data for Smart Fertilizer Finder."""

import os
import sqlite3

from werkzeug.security import generate_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DB_PATH = os.path.join(INSTANCE_DIR, "fertilizer.db")

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin@123"
DEFAULT_FARMER_NAME = "Ravi Patel"
DEFAULT_FARMER_EMAIL = "farmer@example.com"
DEFAULT_FARMER_MOBILE = "9876543210"
DEFAULT_FARMER_PASSWORD = "Farmer@123"

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    mobile TEXT NOT NULL,
    password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS admin (
    admin_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS fertilizers (
    fertilizer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    usage TEXT NOT NULL,
    price REAL NOT NULL CHECK (price > 0),
    stock INTEGER NOT NULL CHECK (stock >= 0),
    image TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shops (
    shop_id INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_name TEXT NOT NULL,
    owner_name TEXT NOT NULL,
    address TEXT NOT NULL,
    village TEXT NOT NULL,
    mobile TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS shop_fertilizers (
    shop_id INTEGER NOT NULL,
    fertilizer_id INTEGER NOT NULL,
    PRIMARY KEY (shop_id, fertilizer_id),
    FOREIGN KEY (shop_id) REFERENCES shops(shop_id) ON DELETE CASCADE,
    FOREIGN KEY (fertilizer_id) REFERENCES fertilizers(fertilizer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS cart (
    cart_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    fertilizer_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    UNIQUE (user_id, fertilizer_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (fertilizer_id) REFERENCES fertilizers(fertilizer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total_amount REAL NOT NULL CHECK (total_amount >= 0),
    order_date TEXT NOT NULL,
    order_status TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    fertilizer_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    price REAL NOT NULL CHECK (price >= 0),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (fertilizer_id) REFERENCES fertilizers(fertilizer_id)
);

CREATE TABLE IF NOT EXISTS contact (
    contact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    message TEXT NOT NULL,
    submitted_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_fertilizers_category ON fertilizers(category);
CREATE INDEX IF NOT EXISTS idx_shops_village ON shops(village);
CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);
"""

FERTILIZERS = [
    {
        "name": "Urea",
        "category": "Nitrogen",
        "description": "Pack size: 45 kg. Urea (46% N) is a concentrated nitrogen fertilizer used for wheat, rice, maize, vegetables, and fodder. It dissolves quickly and supports leafy growth while the crop is actively growing.",
        "usage": "Apply in two or three split doses instead of one heavy dose. Spread it on moist soil and give light irrigation afterwards. Keep granules off the leaves, and store the bag closed, dry, and away from children and animals.",
        "price": 266,
        "stock": 200,
        "image": "urea.jpg",
    },
    {
        "name": "DAP",
        "category": "Phosphatic",
        "description": "Pack size: 50 kg. DAP (18-46-0) supplies nitrogen and a high amount of phosphorus. Farmers mainly place it as a basal fertilizer at sowing for cereals, pulses, and oilseeds.",
        "usage": "Place it near the seed row at sowing, not in direct contact with the seed. It works best in moist soil. Balance later nitrogen with urea when the crop still needs leaf growth.",
        "price": 1350,
        "stock": 120,
        "image": "dap.jpg",
    },
    {
        "name": "NPK",
        "category": "Complex",
        "description": "Pack size: 50 kg. NPK 19:19:19 is a balanced complex fertilizer with nitrogen, phosphorus, and potassium. It suits vegetables, sugarcane, cotton, and fruit crops that need all three major nutrients.",
        "usage": "Apply as a basal dose or during early crop growth, then irrigate. A fully dissolved solution can also go through drip. Follow the dose on your soil-health card when you have one.",
        "price": 1470,
        "stock": 90,
        "image": "npk.jpg",
    },
    {
        "name": "Potash",
        "category": "Potassic",
        "description": "Pack size: 50 kg. Muriate of Potash (60% K2O) strengthens stems, improves grain filling, and helps crops handle dry spells. It is widely used for potato, banana, sugarcane, and vegetables.",
        "usage": "Mix it into the soil before planting or with the first top dressing. Do not place it against the seed. On light soils, split the dose through the season.",
        "price": 1700,
        "stock": 80,
        "image": "potash.jpg",
    },
    {
        "name": "Organic Fertilizers",
        "category": "Organic",
        "description": "Pack size: 25 kg. This blend of vermicompost and well-rotted compost adds organic matter, improves soil structure, and feeds soil life. It supports vegetables, nurseries, and orchards.",
        "usage": "Mix it into the top soil before sowing or place it in planting pits, then water. It complements mineral fertilizers. Heavy cereal crops usually still need a nitrogen source such as urea.",
        "price": 480,
        "stock": 150,
        "image": "organic.jpg",
    },
    {
        "name": "Super Phosphate",
        "category": "Phosphatic",
        "description": "Pack size: 50 kg. Single Super Phosphate (16% P2O5) supplies phosphorus plus calcium and sulphur. It is useful for oilseeds, pulses, groundnut, and other sulphur-loving crops.",
        "usage": "Apply it as a basal dose at sowing and mix it into the soil. It is most useful where soils are low in phosphorus or sulphur. Do not leave it on the surface.",
        "price": 450,
        "stock": 140,
        "image": "ssp.jpg",
    },
    {
        "name": "Micronutrients",
        "category": "Micronutrient",
        "description": "Pack size: 1 kg. This mix contains zinc, iron, and boron for soils and crops that show deficiency symptoms such as yellow new leaves or poor flowering.",
        "usage": "Use only the labeled dose. Extra micronutrients can harm the crop. Apply to soil before sowing, or spray in the early morning. Do not spray in strong midday sun.",
        "price": 220,
        "stock": 300,
        "image": "micro.jpg",
    },
    {
        "name": "Neem Cake",
        "category": "Organic",
        "description": "Pack size: 5 kg. Neem cake is the residue left after oil is pressed from neem seed. It releases nitrogen slowly and is mixed into vegetable beds, coconut basins, and nursery soil.",
        "usage": "Mix the cake into soil 7 to 10 days before sowing so it can decompose. Keep it slightly away from young stems. Store the packet dry. Use it as a soil input, not as a spray.",
        "price": 260,
        "stock": 100,
        "image": "neem.jpg",
    },
]

SHOPS = [
    {
        "shop_name": "Krishi Seva Kendra",
        "owner_name": "Ramesh Patel",
        "address": "12 Market Road, Anand",
        "village": "Rampura",
        "mobile": "9876500101",
        "fertilizers": ["Urea", "DAP", "NPK", "Super Phosphate"],
    },
    {
        "shop_name": "Green Leaf Fertilizers",
        "owner_name": "Sita Devi",
        "address": "44 Village Bazaar, Nadiad",
        "village": "Nandigram",
        "mobile": "9876500102",
        "fertilizers": ["Organic Fertilizers", "Neem Cake", "Micronutrients"],
    },
    {
        "shop_name": "Bharat Agro Store",
        "owner_name": "Mahesh Kumar",
        "address": "8 Station Road, Vadodara",
        "village": "Shivpur",
        "mobile": "9876500103",
        "fertilizers": [
            "Urea",
            "DAP",
            "NPK",
            "Potash",
            "Organic Fertilizers",
            "Super Phosphate",
            "Micronutrients",
            "Neem Cake",
        ],
    },
    {
        "shop_name": "Kisan Mitra Centre",
        "owner_name": "Farida Khan",
        "address": "19 Bus Stand Road, Rajkot",
        "village": "Lakhanpur",
        "mobile": "9876500104",
        "fertilizers": ["Urea", "Potash", "NPK"],
    },
    {
        "shop_name": "Annadata Traders",
        "owner_name": "Joseph Dsouza",
        "address": "3 Gandhi Chowk, Surat",
        "village": "Devgarh",
        "mobile": "9876500105",
        "fertilizers": ["Super Phosphate", "DAP", "Micronutrients"],
    },
    {
        "shop_name": "Harvest Hub",
        "owner_name": "Lakshmi Nair",
        "address": "27 Temple Street, Mehsana",
        "village": "Kheda",
        "mobile": "9876500106",
        "fertilizers": ["Organic Fertilizers", "Neem Cake", "Urea", "Potash"],
    },
]


def connect():
    """Open SQLite with foreign keys enabled and dictionary-style rows."""
    os.makedirs(INSTANCE_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL").fetchone()
    return conn


def seed(conn):
    """Insert the admin, a demo farmer, fertilizers, and shops on a fresh database."""
    existing = conn.execute("SELECT COUNT(*) FROM fertilizers").fetchone()[0]
    if existing:
        return

    conn.execute(
        "INSERT INTO admin (username, password) VALUES (?, ?)",
        (DEFAULT_ADMIN_USERNAME, generate_password_hash(DEFAULT_ADMIN_PASSWORD)),
    )
    conn.execute(
        "INSERT INTO users (name, email, mobile, password) VALUES (?, ?, ?, ?)",
        (
            DEFAULT_FARMER_NAME,
            DEFAULT_FARMER_EMAIL,
            DEFAULT_FARMER_MOBILE,
            generate_password_hash(DEFAULT_FARMER_PASSWORD),
        ),
    )

    fertilizer_ids = {}
    for item in FERTILIZERS:
        cursor = conn.execute(
            """
            INSERT INTO fertilizers (name, category, description, usage, price, stock, image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item["name"],
                item["category"],
                item["description"],
                item["usage"],
                item["price"],
                item["stock"],
                item["image"],
            ),
        )
        fertilizer_ids[item["name"]] = cursor.lastrowid

    for shop in SHOPS:
        cursor = conn.execute(
            """
            INSERT INTO shops (shop_name, owner_name, address, village, mobile)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                shop["shop_name"],
                shop["owner_name"],
                shop["address"],
                shop["village"],
                shop["mobile"],
            ),
        )
        shop_id = cursor.lastrowid
        for name in shop["fertilizers"]:
            conn.execute(
                "INSERT INTO shop_fertilizers (shop_id, fertilizer_id) VALUES (?, ?)",
                (shop_id, fertilizer_ids[name]),
            )


def initialize():
    """Create tables and sample records if the database is empty."""
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        conn.execute("PRAGMA foreign_keys = ON")
        seed(conn)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    initialize()
    print(f"Database ready: {DB_PATH}")
    print(f"Admin login: {DEFAULT_ADMIN_USERNAME} / {DEFAULT_ADMIN_PASSWORD}")
    print(f"Demo farmer: {DEFAULT_FARMER_EMAIL} / {DEFAULT_FARMER_PASSWORD}")
