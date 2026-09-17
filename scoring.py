"""
Return-rate profitability leakage model.

For each product:
  1. Aggregate 12 months of sales/returns -> total units sold, total returned, return rate.
  2. Compute profit leaked to returns = returned units x (lost margin + return-handling cost).
  3. Score Return-Rate Risk and Leakage Magnitude (0-100, min-max normalized across products).
  4. Composite Priority Score = weighted blend of the two -> tells you what to fix FIRST,
     not just what has the worst return rate (a high rate on a cheap item may matter less
     than a lower rate on an expensive one).
  5. Attach the dominant return reason (from the category's reason mix) and a recommended action.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "db" / "returns.db"

DEFAULT_PARAMS = {
    "return_handling_cost_pct": 0.12,  # % of unit price spent handling/restocking a return
    "weight_rate": 0.40,               # weight of Return-Rate Risk in composite score
    "weight_magnitude": 0.60,          # weight of $ Leakage Magnitude in composite score
}


def load_data(db_path: Path = DB_PATH):
    conn = sqlite3.connect(db_path)
    try:
        products = pd.read_sql_query("SELECT * FROM products", conn)
        sales = pd.read_sql_query("SELECT * FROM monthly_sales", conn)
        reasons = pd.read_sql_query("SELECT * FROM category_return_reasons", conn)
    finally:
        conn.close()
    return products, sales, reasons


RECOMMENDED_ACTION = {
    "Sizing/Fit Issue": "Improve size guide / add a fit-comparison chart",
    "Not as Described": "Improve product photos and description accuracy",
    "Defective/Quality Issue": "Escalate to QA / review supplier quality",
    "Changed Mind": "Tighten the return window or add more pre-purchase info (reviews, videos)",
    "Wrong Item Shipped": "Audit the warehouse picking/packing process",
}


def _dominant_reason(reasons: pd.DataFrame) -> pd.DataFrame:
    idx = reasons.groupby("category")["pct_of_returns"].idxmax()
    dom = reasons.loc[idx, ["category", "reason", "pct_of_returns"]].rename(
        columns={"reason": "dominant_return_reason", "pct_of_returns": "dominant_reason_pct"}
    )
    dom["recommended_action"] = dom["dominant_return_reason"].map(RECOMMENDED_ACTION)
    return dom


def compute_leakage(params: dict | None = None, db_path: Path = DB_PATH) -> pd.DataFrame:
    p = {**DEFAULT_PARAMS, **(params or {})}
    products, sales, reasons = load_data(db_path)

    agg = sales.groupby("product_id").agg(
        units_sold_total=("units_sold", "sum"),
        units_returned_total=("units_returned", "sum"),
    ).reset_index()

    df = products.merge(agg, on="product_id")
    df["return_rate"] = df.units_returned_total / df.units_sold_total.replace(0, pd.NA)
    df["margin_per_unit"] = df.unit_price - df.unit_cost
    df["handling_cost_per_unit"] = df.unit_price * p["return_handling_cost_pct"]
    df["leaked_profit_total"] = df.units_returned_total * (df.margin_per_unit + df.handling_cost_per_unit)
    df["potential_revenue"] = df.units_sold_total * df.unit_price
    df["leakage_pct_of_revenue"] = df.leaked_profit_total / df.potential_revenue.replace(0, pd.NA)

    def norm(col: pd.Series) -> pd.Series:
        lo, hi = col.min(), col.max()
        if hi == lo:
            return pd.Series([50.0] * len(col), index=col.index)
        return 100.0 * (col - lo) / (hi - lo)

    df["return_rate_risk_score"] = norm(df["return_rate"])
    df["leakage_magnitude_score"] = norm(df["leaked_profit_total"])
    df["priority_score"] = (
        df["return_rate_risk_score"] * p["weight_rate"]
        + df["leakage_magnitude_score"] * p["weight_magnitude"]
    )

    dom = _dominant_reason(reasons)
    df = df.merge(dom, on="category", how="left")

    df = df.sort_values("priority_score", ascending=False).reset_index(drop=True)
    df["rank"] = df.index + 1
    return df


def monthly_series(product_id: int, db_path: Path = DB_PATH) -> pd.DataFrame:
    _, sales, _ = load_data(db_path)
    s = sales[sales.product_id == product_id].sort_values("month_number")
    return s[["month_number", "units_sold", "units_returned"]]
