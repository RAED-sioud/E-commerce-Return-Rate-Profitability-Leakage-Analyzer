"""
Builds db/returns.db: creates the schema, then generates a realistic
synthetic e-commerce dataset — products across 6 categories, 12 months of
sales/returns history with holiday seasonality and category-appropriate
return-rate baselines, and a category-level return-reason mix.

This is illustrative example data for demonstration. Replace with a real
store's order/return export before using this for an actual decision.
"""
import random
import sqlite3
from pathlib import Path

DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "returns.db"

random.seed(7)

# category: (baseline_return_rate, price_range, cost_pct_of_price)
CATEGORIES = {
    "Apparel":        (0.22, (20, 80),   0.42),
    "Shoes":          (0.25, (60, 180),  0.45),
    "Electronics":    (0.10, (100, 900), 0.65),
    "Home & Kitchen": (0.06, (20, 150),  0.50),
    "Beauty":         (0.04, (15, 90),   0.35),
    "Accessories":    (0.05, (10, 60),   0.40),
}

PRODUCT_NAMES = {
    "Apparel": ["Slim-Fit Jeans", "Cotton T-Shirt", "Wool Sweater", "Summer Dress", "Hoodie"],
    "Shoes": ["Running Sneakers", "Leather Boots", "Casual Loafers", "Sandals", "High Heels"],
    "Electronics": ["Wireless Earbuds", "Bluetooth Speaker", "Smartwatch", "Phone Case Kit", "Tablet Stand"],
    "Home & Kitchen": ["Non-Stick Pan Set", "Blender", "Bedsheet Set", "Table Lamp", "Storage Boxes"],
    "Beauty": ["Face Serum", "Lipstick Set", "Shampoo Bundle", "Perfume", "Skincare Kit"],
    "Accessories": ["Leather Wallet", "Sunglasses", "Tote Bag", "Watch Strap", "Phone Charm"],
}

# Return reason mix per category (must sum to 1.0 per category)
CATEGORY_REASON_MIX = {
    "Apparel":        {"Sizing/Fit Issue": 0.55, "Not as Described": 0.20, "Changed Mind": 0.15, "Defective/Quality Issue": 0.07, "Wrong Item Shipped": 0.03},
    "Shoes":          {"Sizing/Fit Issue": 0.60, "Defective/Quality Issue": 0.15, "Not as Described": 0.15, "Changed Mind": 0.07, "Wrong Item Shipped": 0.03},
    "Electronics":    {"Defective/Quality Issue": 0.45, "Not as Described": 0.25, "Changed Mind": 0.20, "Wrong Item Shipped": 0.07, "Sizing/Fit Issue": 0.03},
    "Home & Kitchen": {"Defective/Quality Issue": 0.35, "Not as Described": 0.30, "Changed Mind": 0.20, "Wrong Item Shipped": 0.10, "Sizing/Fit Issue": 0.05},
    "Beauty":         {"Changed Mind": 0.40, "Not as Described": 0.30, "Defective/Quality Issue": 0.20, "Wrong Item Shipped": 0.07, "Sizing/Fit Issue": 0.03},
    "Accessories":    {"Changed Mind": 0.35, "Not as Described": 0.30, "Defective/Quality Issue": 0.20, "Wrong Item Shipped": 0.10, "Sizing/Fit Issue": 0.05},
}

RECOMMENDED_ACTION = {
    "Sizing/Fit Issue": "Improve size guide / add a fit-comparison chart",
    "Not as Described": "Improve product photos and description accuracy",
    "Defective/Quality Issue": "Escalate to QA / review supplier quality",
    "Changed Mind": "Tighten the return window or add more pre-purchase info (reviews, videos)",
    "Wrong Item Shipped": "Audit the warehouse picking/packing process",
}

N_MONTHS = 12


def seasonal_sales_multiplier(month: int) -> float:
    """Nov/Dec holiday sales spike."""
    if month in (11, 12):
        return 1.7
    if month == 1:
        return 0.9  # post-holiday dip
    return 1.0


def seasonal_return_multiplier(month: int) -> float:
    """January sees a post-holiday returns spike relative to that month's (lower) sales."""
    if month == 1:
        return 1.5
    return 1.0


def build_products():
    products = []
    pid = 1
    for category, (base_rate, price_range, cost_pct) in CATEGORIES.items():
        for name in PRODUCT_NAMES[category]:
            price = round(random.uniform(*price_range), 2)
            cost = round(price * cost_pct * random.uniform(0.9, 1.1), 2)
            products.append((pid, name, category, price, cost, base_rate))
            pid += 1
    return products


def generate_monthly_sales(cur: sqlite3.Cursor, products) -> None:
    rows = []
    for pid, name, category, price, cost, base_rate in products:
        base_monthly_units = random.randint(40, 200)
        # cheaper categories sell more units
        base_monthly_units = int(base_monthly_units * (100 / max(price, 20)) ** 0.3)
        for month in range(1, N_MONTHS + 1):
            sales_mult = seasonal_sales_multiplier(month)
            units_sold = max(1, round(base_monthly_units * sales_mult * random.gauss(1.0, 0.15)))

            return_mult = seasonal_return_multiplier(month)
            product_rate = max(0.005, base_rate * random.gauss(1.0, 0.2))
            effective_rate = min(0.85, product_rate * return_mult)
            units_returned = min(units_sold, round(units_sold * effective_rate))

            rows.append((pid, month, units_sold, units_returned))
    cur.executemany(
        "INSERT INTO monthly_sales (product_id, month_number, units_sold, units_returned) VALUES (?,?,?,?)",
        rows,
    )


def generate_reason_mix(cur: sqlite3.Cursor) -> None:
    rows = []
    for category, mix in CATEGORY_REASON_MIX.items():
        for reason, pct in mix.items():
            rows.append((category, reason, pct))
    cur.executemany(
        "INSERT INTO category_return_reasons (category, reason, pct_of_returns) VALUES (?,?,?)",
        rows,
    )


def build_database(db_path: Path = DB_PATH) -> None:
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.executescript((DB_DIR / "schema.sql").read_text())
        products = build_products()
        cur.executemany(
            "INSERT INTO products (product_id, product_name, category, unit_price, unit_cost) VALUES (?,?,?,?,?)",
            [(p[0], p[1], p[2], p[3], p[4]) for p in products],
        )
        generate_monthly_sales(cur, products)
        generate_reason_mix(cur)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    build_database()
    print(f"Database built at {DB_PATH}")
