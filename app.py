"""
E-commerce Return-Rate Profitability Leakage Analyzer — Streamlit web app.

Helps an e-commerce store see not just which products get returned the most,
but which returns are actually costing the most money — and what's driving
them, so they know what to fix first.
"""
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from db.generate_data import DB_PATH, build_database
from scoring import DEFAULT_PARAMS, compute_leakage, monthly_series

st.set_page_config(
    page_title="Return-Rate Leakage Analyzer",
    page_icon="🔁",
    layout="wide",
)

if not Path(DB_PATH).exists():
    build_database()

# ---------------------------------------------------------------- header ---
st.title("🔁 E-commerce Return-Rate Profitability Leakage Analyzer")
st.caption(
    "Not every high return rate is a priority, and not every low return rate is safe. "
    "This ranks products by how much profit their returns actually cost you."
)
st.info(
    "Sales and return data is synthetic, generated with realistic category-level patterns "
    "for demonstration. Replace it with a real store's order/return export before using this "
    "for an actual decision.",
    icon="ℹ️",
)

# --------------------------------------------------------------- sidebar ---
st.sidebar.header("Model settings")
handling_pct = st.sidebar.slider(
    "Return handling cost (% of unit price)", 0, 30, int(DEFAULT_PARAMS["return_handling_cost_pct"] * 100), 1,
    help="Reverse shipping, restocking labor, and inspection cost per returned unit.",
) / 100.0
weight_rate = st.sidebar.slider("Weight: Return-Rate Risk", 0.0, 1.0, DEFAULT_PARAMS["weight_rate"], 0.05)
weight_magnitude = 1.0 - weight_rate
st.sidebar.caption(f"Weight: $ Leakage Magnitude = {weight_magnitude:.2f} (auto-balanced)")

params = {
    "return_handling_cost_pct": handling_pct,
    "weight_rate": weight_rate,
    "weight_magnitude": weight_magnitude,
}
df = compute_leakage(params)

st.sidebar.divider()
categories = ["All categories"] + sorted(df.category.unique().tolist())
selected_category = st.sidebar.selectbox("Filter by category", categories)
filtered = df if selected_category == "All categories" else df[df.category == selected_category]

# ------------------------------------------------------------- KPI cards ---
total_leak = filtered.leaked_profit_total.sum()
overall_rate = filtered.units_returned_total.sum() / filtered.units_sold_total.sum()
top_leak_share = filtered.sort_values("leaked_profit_total", ascending=False).head(5).leaked_profit_total.sum() / total_leak if total_leak else 0

k1, k2, k3 = st.columns(3)
k1.metric("Total profit leaked to returns", f"{total_leak:,.0f}")
k2.metric("Overall return rate", f"{overall_rate:.1%}")
k3.metric("Share of leakage from top 5 products", f"{top_leak_share:.0%}")

# ------------------------------------------------------------ quadrant ---
st.subheader("Return-rate vs. profit leakage — where the real problems are")
fig = px.scatter(
    filtered, x="return_rate", y="leaked_profit_total", size="units_sold_total",
    color="category", hover_name="product_name",
    labels={"return_rate": "Return Rate", "leaked_profit_total": "Profit Leaked (total)"},
)
fig.update_layout(height=450, xaxis_tickformat=".0%", margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)
st.caption(
    "Bubble size = units sold. Top-right = high return rate AND high dollar leakage — "
    "fix these first. A product can sit low on return rate but still leak a lot of profit "
    "if it's high-value or high-volume — worth checking the top of the ranked table below."
)

# --------------------------------------------------------- ranked table ---
st.subheader("Prioritized action list")
display_cols = {
    "rank": "Rank", "product_name": "Product", "category": "Category",
    "return_rate": "Return Rate", "leaked_profit_total": "Profit Leaked",
    "return_rate_risk_score": "Rate Risk Score", "leakage_magnitude_score": "Leakage Score",
    "priority_score": "Priority Score", "dominant_return_reason": "Likely Cause",
    "recommended_action": "Recommended Action",
}
table = filtered[list(display_cols.keys())].rename(columns=display_cols)
st.dataframe(
    table.style
        .format({"Return Rate": "{:.1%}", "Profit Leaked": "{:,.0f}",
                 "Rate Risk Score": "{:.0f}", "Leakage Score": "{:.0f}", "Priority Score": "{:.0f}"})
        .background_gradient(subset=["Priority Score"], cmap="RdYlGn_r", vmin=0, vmax=100),
    use_container_width=True, hide_index=True,
)
st.download_button(
    "⬇️ Download prioritized list as CSV",
    data=table.to_csv(index=False).encode("utf-8"),
    file_name="return_leakage_priority_list.csv",
    mime="text/csv",
)

# ------------------------------------------------------- product drilldown ---
st.subheader("Monthly sales vs. returns for a specific product")
sel_name = st.selectbox("Product", sorted(filtered.product_name.unique()))
row = df[df.product_name == sel_name].iloc[0]
series = monthly_series(int(row.product_id))

fig2 = go.Figure()
fig2.add_trace(go.Bar(x=series.month_number, y=series.units_sold, name="Units Sold", marker_color="#2E5395"))
fig2.add_trace(go.Bar(x=series.month_number, y=series.units_returned, name="Units Returned", marker_color="#E67E22"))
fig2.update_layout(
    barmode="overlay", height=380, margin=dict(l=10, r=10, t=30, b=10),
    xaxis_title="Month", yaxis_title="Units",
    legend=dict(orientation="h", yanchor="bottom", y=1.02),
)
st.plotly_chart(fig2, use_container_width=True)

c1, c2, c3 = st.columns(3)
c1.metric("Return rate", f"{row.return_rate:.1%}")
c2.metric("Profit leaked (12 mo.)", f"{row.leaked_profit_total:,.0f}")
c3.metric("Likely cause", row.dominant_return_reason)
st.markdown(f"**Recommended action:** {row.recommended_action}")

st.divider()
st.caption(
    "Methodology: Profit Leaked = returned units x (lost margin + return-handling cost). "
    "Return-Rate Risk and $ Leakage Magnitude are each min-max normalized 0-100 across the "
    "catalog. Priority Score = weighted blend of the two, adjustable in the sidebar — so a "
    "high-value product with a moderate return rate can outrank a cheap product with a high one."
)
