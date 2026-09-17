-- =========================================================================
-- E-commerce Return-Rate Profitability Leakage Analyzer — Schema (SQLite)
-- =========================================================================

CREATE TABLE IF NOT EXISTS products (
    product_id     INTEGER PRIMARY KEY,
    product_name    TEXT NOT NULL,
    category        TEXT NOT NULL,
    unit_price      REAL NOT NULL,
    unit_cost       REAL NOT NULL
);

-- Monthly sales & returns per product (12 months)
CREATE TABLE IF NOT EXISTS monthly_sales (
    product_id    INTEGER NOT NULL REFERENCES products(product_id),
    month_number  INTEGER NOT NULL,   -- 1-12
    units_sold    INTEGER NOT NULL,
    units_returned INTEGER NOT NULL,
    PRIMARY KEY (product_id, month_number)
);

-- Distribution of return reasons per category (percent of returns attributable to each reason)
CREATE TABLE IF NOT EXISTS category_return_reasons (
    category   TEXT NOT NULL,
    reason      TEXT NOT NULL,
    pct_of_returns REAL NOT NULL,
    PRIMARY KEY (category, reason)
);
