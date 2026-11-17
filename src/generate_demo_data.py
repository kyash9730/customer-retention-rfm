"""Create a synthetic transaction file for an offline, immediate demo run.

The generated rows are deliberately labelled as synthetic. They are not a sample
of the UCI dataset and should never be reported as findings about the real retailer.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "demo_transactions.csv"


def make_demo(seed: int = 47, customers_n: int = 3200) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    start = pd.Timestamp("2009-12-01")
    end = pd.Timestamp("2011-12-09")
    days = (end - start).days
    profiles = np.array(["champion", "loyal", "promising", "new", "at_risk", "hibernating", "one_time"])
    probs = np.array([0.09, 0.20, 0.16, 0.17, 0.16, 0.12, 0.10])
    assigned = rng.choice(profiles, size=customers_n, p=probs)
    country_names = np.array(["United Kingdom", "Germany", "France", "EIRE", "Spain", "Netherlands", "Belgium", "Australia", "Portugal", "Sweden"])
    country_probs = np.array([0.75, 0.06, 0.045, 0.04, 0.025, 0.02, 0.018, 0.015, 0.012, 0.015])
    country_probs = country_probs / country_probs.sum()
    categories = {
        "Giftware": ["HEART T-LIGHT HOLDER", "HANGING HEART JAR T-LIGHT HOLDER", "CERAMIC HEART FAIRY CAKE CASES", "WOODEN STAR CHRISTMAS SCANDINAVIAN"],
        "Home decor": ["REGENCY CAKESTAND 3 TIER", "VINTAGE UNION JACK MEMOBOARD", "WHITE HANGING HEART T-LIGHT HOLDER", "GARDENERS KNEELING PAD"],
        "Kitchen": ["SET OF 3 CAKE TINS PANTRY DESIGN", "JAM MAKING SET PRINTED", "PACK OF 72 RETROSPOT CAKE CASES", "GINGHAM HEART DOORSTOP"],
        "Stationery": ["RETROSPOT TEA SET CERAMIC 11 PC", "PAPER CHAIN KIT 50'S CHRISTMAS", "PACK OF 12 LONDON TISSUES", "VINTAGE SNAP CARDS"],
        "Seasonal": ["CHRISTMAS CRAFT TREE TOP ANGEL", "SET OF 20 VINTAGE CHRISTMAS NAPKINS", "PINK CHRISTMAS FLOCK DROPPED BAUBLE", "CHRISTMAS LIGHTS 10 REINDEER"],
        "Accessories": ["RED RETROSPOT UMBRELLA", "BLUE POLKADOT WRAP", "LUNCH BAG RED RETROSPOT", "JUMBO BAG RED RETROSPOT"],
    }
    cat_names = list(categories)
    all_products = [(c, p) for c, vals in categories.items() for p in vals]
    rows = []
    invoice_counter = 500000
    # Country is assigned at customer level to make it stable across orders.
    customer_country = rng.choice(country_names, size=customers_n, p=country_probs)

    for i in range(customers_n):
        cid = f"{12000 + i:05d}"
        profile = assigned[i]
        if profile == "champion":
            n_orders = int(np.clip(rng.poisson(13) + 3, 6, 25))
            first_day = int(rng.integers(0, max(1, days - 500)))
            last_day = days - int(rng.integers(0, 70))
            aov_scale = 1.35
        elif profile == "loyal":
            n_orders = int(np.clip(rng.poisson(6) + 1, 3, 15))
            first_day = int(rng.integers(0, max(1, days - 320)))
            last_day = days - int(rng.integers(0, 140))
            aov_scale = 1.0
        elif profile == "promising":
            n_orders = int(np.clip(rng.poisson(2.0) + 2, 2, 7))
            first_day = int(rng.integers(max(0, days - 300), max(1, days - 60)))
            last_day = days - int(rng.integers(0, 70))
            aov_scale = 0.95
        elif profile == "new":
            n_orders = int(rng.choice([1, 1, 1, 2], p=[0.65, 0.15, 0.10, 0.10]))
            first_day = int(rng.integers(max(0, days - 120), days))
            last_day = min(days, first_day + int(rng.integers(5, 80)))
            aov_scale = 0.85
        elif profile == "at_risk":
            n_orders = int(np.clip(rng.poisson(3) + 2, 3, 10))
            first_day = int(rng.integers(0, max(1, days - 400)))
            last_day = max(first_day + 1, days - int(rng.integers(100, 250)))
            aov_scale = 1.1
        elif profile == "hibernating":
            n_orders = int(np.clip(rng.poisson(1) + 1, 1, 4))
            first_day = int(rng.integers(0, max(1, days - 250)))
            last_day = max(first_day + 1, days - int(rng.integers(250, 600)))
            aov_scale = 0.9
        else:  # one-time buyers
            n_orders = 1
            first_day = int(rng.integers(0, days))
            last_day = first_day
            aov_scale = 0.75
        first_day = min(first_day, days)
        last_day = min(max(last_day, first_day), days)
        if n_orders == 1:
            order_days = [int(rng.integers(first_day, last_day + 1))]
        else:
            order_days = sorted(rng.choice(np.arange(first_day, last_day + 1), size=min(n_orders, max(1, last_day-first_day+1)), replace=False).tolist())
        if len(order_days) == 0:
            order_days = [first_day]
        # Customer-level basket tendencies introduce stable but imperfect patterns.
        preferred_cat = rng.choice(cat_names)
        for od in order_days:
            invoice_counter += 1
            n_lines = int(rng.integers(1, 5))
            hour = int(rng.integers(7, 21))
            minute = int(rng.integers(0, 60))
            invoice_dt = start + pd.Timedelta(days=int(od), hours=hour, minutes=minute)
            invoice_customer_field = "" if rng.random() < 0.06 else cid
            for _ in range(n_lines):
                if rng.random() < 0.48:
                    cat = preferred_cat
                    product = rng.choice(categories[cat])
                else:
                    cat, product = all_products[int(rng.integers(0, len(all_products)))]
                base_price = {
                    "Giftware": 4.2, "Home decor": 8.8, "Kitchen": 6.5,
                    "Stationery": 3.0, "Seasonal": 5.2, "Accessories": 7.0
                }[cat]
                unit_price = float(np.clip(rng.lognormal(np.log(base_price), 0.55) * aov_scale, 0.35, 65.0))
                quantity = int(np.clip(rng.negative_binomial(2, 0.45) + 1, 1, 18))
                # A small number of bulk buyers have large baskets, matching the data's wholesale context.
                if profile == "champion" and rng.random() < 0.08:
                    quantity = int(rng.integers(20, 90))
                # Keep about 6% of whole invoices unassigned. All lines in an invoice
                # share the same key, which avoids partially attributing a basket.
                rows.append({
                    "Invoice": str(invoice_counter),
                    "StockCode": f"{10000 + cat_names.index(cat)*100 + categories[cat].index(product):05d}",
                    "Description": product,
                    "Quantity": quantity,
                    "InvoiceDate": invoice_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "Price": round(unit_price, 2),
                    "Customer ID": invoice_customer_field,
                    "Country": customer_country[i],
                })

    # Add a small, explicit cancellation/return slice so cleaning logic is exercised.
    valid_sample = [r for r in rows if r["Customer ID"]]
    add_n = max(80, int(len(rows) * 0.018))
    for j in range(add_n):
        original = valid_sample[int(rng.integers(0, len(valid_sample)))]
        cancel = dict(original)
        cancel["Invoice"] = "C" + str(invoice_counter + j + 1)
        cancel["Quantity"] = -int(max(1, original["Quantity"]))
        cancel["InvoiceDate"] = (pd.Timestamp(original["InvoiceDate"]) + pd.Timedelta(days=int(rng.integers(1, 25)))).strftime("%Y-%m-%d %H:%M:%S")
        rows.append(cancel)

    df = pd.DataFrame(rows)
    # Add a few exact duplicates to make duplicate-removal checks visible.
    if len(df) > 50:
        dupes = df.sample(frac=0.002, random_state=seed)
        df = pd.concat([df, dupes], ignore_index=True)
    df = df.sort_values("InvoiceDate", kind="stable").reset_index(drop=True)
    return df


if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    frame = make_demo()
    frame.to_csv(OUT, index=False)
    print(f"Wrote {len(frame):,} synthetic demo lines to {OUT.relative_to(ROOT)}")
