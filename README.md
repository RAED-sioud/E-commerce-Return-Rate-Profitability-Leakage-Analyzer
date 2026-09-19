# 🔁 E-commerce Return-Rate Profitability Leakage Analyzer

A BI tool that ranks products not by *how often* they're returned, but by *how much profit
their returns actually cost* — because the two aren't the same thing. A cheap item with a
high return rate can matter less than an expensive item with a moderate one.


## What it does

- Aggregates 12 months of sales/returns per product into a **return rate** and a **total
  profit leaked to returns** (lost margin + return-handling cost per returned unit)
- Scores every product on **Return-Rate Risk** and **$ Leakage Magnitude** (0–100, normalized
  across the catalog), then blends them into a single **Priority Score** — so the ranked list
  reflects real financial impact, not just the raw return percentage
- Attaches a **likely root cause** per category (sizing issue, defective/quality, not as
  described, changed mind, wrong item shipped) and a matching **recommended action**
- Includes a return-rate-vs-leakage scatter plot, a per-product monthly sales/returns chart,
  and CSV export of the prioritized list

## Tech stack

- **Python** — analysis model (`pandas`)
- **Streamlit** — web app / UI
- **SQLite** — data warehouse (products, monthly sales/returns, category return-reason mix)
- **Plotly** — scatter and bar charts

## Project structure

```
.
├── app.py                 # Streamlit app (UI)
├── scoring.py               # Return-leakage scoring model
├── db/
│   ├── schema.sql            # Data warehouse schema
│   ├── generate_data.py      # Builds returns.db with realistic synthetic data
├── requirements.txt
└── README.md
```

## Run it locally

```bash
git clone https://github.com/RAED-sioud/Return-Rate-Leakage-Analyzer.git
cd Return-Rate-Leakage-Analyzer
python -m venv venv
venv\Scripts\activate        # on Windows; use `source venv/bin/activate` on Mac/Linux
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

The app builds its SQLite database automatically on first run — 30 products across 6
categories (Apparel, Shoes, Electronics, Home & Kitchen, Beauty, Accessories) with
category-appropriate return-rate baselines and holiday-season sales/returns seasonality.

## About the data

All product, sales, and return figures are **synthetic**, generated with realistic
category-level return-rate patterns for demonstration. Before using this for a real
decision, replace `db/generate_data.py`'s data with a real store's order/return export.

## Methodology

For each product:
1. Return rate = total units returned ÷ total units sold (12 months)
2. Profit leaked = returned units × (lost margin per unit + return-handling cost per unit)
3. Return-Rate Risk and $ Leakage Magnitude are each min-max normalized 0–100 across the catalog
4. Priority Score = weighted blend of the two (default 40% rate / 60% magnitude, adjustable)
5. Dominant return reason and recommended action are attached from the product's category

## License

MIT — see [LICENSE](LICENSE).
