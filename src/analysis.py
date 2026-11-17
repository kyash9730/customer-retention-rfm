from __future__ import annotations
from pathlib import Path
import json
import warnings
import sqlite3
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
VIZ = ROOT / "visualizations"
PROCESSED = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"

COL_ALIASES = {
    "invoice_no": ["invoice", "invoiceno", "invoice no", "invoice number"],
    "stock_code": ["stockcode", "stock code", "product code"],
    "description": ["description", "product description"],
    "quantity": ["quantity", "qty"],
    "invoice_date": ["invoicedate", "invoice date", "date"],
    "unit_price": ["price", "unitprice", "unit price"],
    "customer_id": ["customer id", "customerid", "customer_id", "customer"],
    "country": ["country", "market"],
}

SEGMENT_ACTIONS = {
    "Champions": ("Protect the relationship", "Early access, recognition and a light-touch service check. Avoid discounting customers who already return."),
    "Loyal Regulars": ("Grow the basket", "Use relevant bundles, replenishment reminders and complementary products. Measure incremental basket value."),
    "Potential Loyalists": ("Help the second habit form", "Offer useful recommendations and a clear reason to return before the next natural buying window."),
    "New Customers": ("Make the first experience count", "Follow up after delivery, reduce purchase friction and make the next useful product easy to find."),
    "At Risk": ("Win back valuable relationships", "Prioritise customers with meaningful past value and long recency. Test a low-cost personal message before a discount."),
    "Need Attention": ("Check for a reason to leave", "Use a helpful service message or short feedback prompt. Do not assume every quiet customer has churned."),
    "Hibernating": ("Use a low-cost reactivation test", "Try one relevant message, set a strict spend cap and stop if the group does not respond."),
    "Developing": ("Learn what builds a habit", "Compare product mix, basket size and purchase spacing. Choose the next action from observed behaviour."),
}


def _norm_column(name: str) -> str:
    return " ".join(str(name).strip().lower().replace("_", " ").split())


def standardize(raw: pd.DataFrame) -> pd.DataFrame:
    lookup = {_norm_column(c): c for c in raw.columns}
    chosen = {}
    for target, aliases in COL_ALIASES.items():
        for alias in aliases:
            alias_norm = _norm_column(alias)
            if alias_norm in lookup:
                chosen[target] = lookup[alias_norm]
                break
    missing = [x for x in COL_ALIASES if x not in chosen]
    if missing:
        raise ValueError(f"Could not find the required source columns: {missing}. Columns found: {list(raw.columns)}")
    frame = raw[[chosen[c] for c in COL_ALIASES]].copy()
    frame.columns = list(COL_ALIASES)
    frame["invoice_no"] = frame["invoice_no"].astype("string").fillna("").str.strip()
    frame["stock_code"] = frame["stock_code"].astype("string").fillna("").str.strip()
    frame["description"] = frame["description"].astype("string").fillna("Unknown item").str.strip()
    frame["quantity"] = pd.to_numeric(frame["quantity"], errors="coerce")
    frame["unit_price"] = pd.to_numeric(frame["unit_price"], errors="coerce")
    frame["invoice_date"] = pd.to_datetime(frame["invoice_date"], errors="coerce")
    customer_num = pd.to_numeric(frame["customer_id"], errors="coerce")
    frame["customer_id"] = customer_num.round().astype("Int64").astype("string").fillna("")
    frame["country"] = frame["country"].astype("string").fillna("Unknown").str.strip()
    return frame


def load_raw(source: str) -> pd.DataFrame:
    if source == "demo":
        p = ROOT / "data" / "demo_transactions.csv"
        if not p.exists():
            from .generate_demo_data import make_demo
            data = make_demo()
            data.to_csv(p, index=False)
        return pd.read_csv(p, dtype={"Customer ID": "string", "Invoice": "string"})
    if source != "real":
        raise ValueError("source must be 'demo' or 'real'")
    workbook = RAW / "online_retail_II.xlsx"
    if not workbook.exists():
        raise FileNotFoundError("Real workbook not found. Run: python run_project.py --source real --download")
    sheets = pd.read_excel(workbook, sheet_name=None, engine="openpyxl")
    frames = [sheet for sheet in sheets.values() if sheet is not None and not sheet.empty]
    if not frames:
        raise ValueError("No transaction sheets found in the UCI workbook.")
    return pd.concat(frames, ignore_index=True)


def prepare(raw: pd.DataFrame):
    df = standardize(raw)
    quality = {"raw_lines": int(len(df))}
    quality["exact_duplicate_lines"] = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()
    df = df.dropna(subset=["invoice_date", "quantity", "unit_price"])
    quality["cancellation_lines"] = int(df["invoice_no"].str.upper().str.startswith("C").sum())
    quality["negative_or_zero_quantity_lines"] = int((df["quantity"] <= 0).sum())
    quality["zero_or_negative_price_lines"] = int((df["unit_price"] <= 0).sum())
    quality["missing_customer_id_lines"] = int((df["customer_id"] == "").sum())
    cancelled = df["invoice_no"].str.upper().str.startswith("C") | (df["quantity"] <= 0)
    returns = df.loc[cancelled].copy()
    sales = df.loc[(~cancelled) & (df["quantity"] > 0) & (df["unit_price"] > 0)].copy()
    sales["line_value"] = sales["quantity"] * sales["unit_price"]
    sales["invoice_date"] = pd.to_datetime(sales["invoice_date"])
    sales["invoice_month"] = sales["invoice_date"].dt.to_period("M").astype(str)
    quality["clean_sales_lines"] = int(len(sales))
    quality["customer_identified_sales_lines"] = int((sales["customer_id"] != "").sum())
    quality["distinct_invoices"] = int(sales["invoice_no"].nunique())
    quality["distinct_known_customers"] = int(sales.loc[sales.customer_id != "", "customer_id"].nunique())
    quality["gross_sales_value_gbp"] = float(sales["line_value"].sum())
    return sales, returns, quality


def build_orders(sales: pd.DataFrame) -> pd.DataFrame:
    known = sales.loc[sales.customer_id != ""].copy()
    if known.empty:
        return pd.DataFrame(columns=["customer_id", "invoice_no", "order_date", "order_value", "country", "unique_items"])
    orders = (known.groupby(["customer_id", "invoice_no"], as_index=False)
        .agg(order_date=("invoice_date", "min"), order_value=("line_value", "sum"), country=("country", "first"), unique_items=("stock_code", "nunique")))
    return orders.sort_values(["customer_id", "order_date", "invoice_no"]).reset_index(drop=True)


def assign_segments(c: pd.DataFrame) -> pd.DataFrame:
    c = c.copy()
    n = len(c)
    if n == 0:
        return c
    # Score by percentile rank rather than splitting ties. Customers with the
    # same purchase frequency receive the same frequency score.
    r_pct = c["recency_days"].rank(method="average", pct=True)
    f_pct = c["frequency"].rank(method="average", pct=True)
    m_pct = c["historic_value_gbp"].rank(method="average", pct=True)
    c["r_score"] = (6 - np.ceil(r_pct * 5).clip(1, 5)).astype(int)
    c["f_score"] = np.ceil(f_pct * 5).clip(1, 5).astype(int)
    c["m_score"] = np.ceil(m_pct * 5).clip(1, 5).astype(int)
    c["rfm_score"] = c["r_score"] + c["f_score"] + c["m_score"]
    def choose(row):
        r, f, m = int(row.r_score), int(row.f_score), int(row.m_score)
        if r >= 4 and f >= 4 and m >= 4: return "Champions"
        if f >= 4 and r >= 3: return "Loyal Regulars"
        if r >= 4 and f >= 2: return "Potential Loyalists"
        if r >= 4 and f == 1: return "New Customers"
        if r <= 2 and f >= 3: return "At Risk"
        if r <= 2 and f == 2: return "Need Attention"
        if r <= 2 and f == 1: return "Hibernating"
        return "Developing"
    c["segment"] = c.apply(choose, axis=1)
    value_decile_num = np.ceil(c["historic_value_gbp"].rank(method="average", pct=True) * 10).clip(1, 10).astype(int)
    c["value_decile"] = value_decile_num.map(lambda x: f"D{x}")
    c["repeat_buyer"] = c["frequency"] >= 2
    c["risk_score"] = (100 * (0.60 * c["recency_percentile"] + 0.20 * (1 - c["frequency_percentile"]) + 0.20 * (1 - c["value_percentile"]))).round(1)
    c["historical_value_at_risk_proxy_gbp"] = (c["historic_value_gbp"] * c["risk_score"] / 100).round(2)
    c["recommended_action"] = c["segment"].map(lambda x: SEGMENT_ACTIONS.get(x, SEGMENT_ACTIONS["Developing"])[0])
    return c


def make_customer_features(orders: pd.DataFrame, snapshot: pd.Timestamp | None = None) -> pd.DataFrame:
    if orders.empty:
        return pd.DataFrame()
    if snapshot is None:
        snapshot = pd.to_datetime(orders["order_date"]).max().normalize() + pd.Timedelta(days=1)
    orders = orders.copy()
    orders["order_date"] = pd.to_datetime(orders["order_date"])
    groups = orders.groupby("customer_id")
    agg = groups.agg(
        first_purchase=("order_date", "min"),
        last_purchase=("order_date", "max"),
        frequency=("invoice_no", "nunique"),
        historic_value_gbp=("order_value", "sum"),
        avg_order_value_gbp=("order_value", "mean"),
        country=("country", lambda s: s.mode().iloc[0] if not s.mode().empty else "Unknown"),
        unique_products=("unique_items", "sum"),
        countries_seen=("country", "nunique"),
    ).reset_index()
    agg["recency_days"] = (snapshot.normalize() - agg["last_purchase"].dt.normalize()).dt.days.clip(lower=0)
    agg["tenure_days"] = (agg["last_purchase"].dt.normalize() - agg["first_purchase"].dt.normalize()).dt.days.clip(lower=0)
    agg["lifetime_days_in_window"] = (snapshot.normalize() - agg["first_purchase"].dt.normalize()).dt.days.clip(lower=1)
    agg["annualised_historic_value_proxy_gbp"] = (agg["historic_value_gbp"] / (agg["lifetime_days_in_window"] / 365.25).clip(lower=0.25)).round(2)
    order_gap = groups["order_date"].apply(lambda x: x.sort_values().drop_duplicates().diff().dt.days.dropna().mean() if x.nunique() > 1 else np.nan).rename("avg_days_between_orders").reset_index()
    agg = agg.merge(order_gap, on="customer_id", how="left")
    agg["avg_days_between_orders"] = agg["avg_days_between_orders"].round(1)
    for col in ["recency_days", "frequency", "historic_value_gbp"]:
        agg[col + "_rank"] = agg[col].rank(pct=True, method="average")
    agg["recency_percentile"] = agg["recency_days_rank"]
    agg["frequency_percentile"] = agg["frequency_rank"]
    agg["value_percentile"] = agg["historic_value_gbp_rank"]
    agg = agg.rename(columns={
        "recency_days_rank": "_recency_rank",
        "frequency_rank": "_frequency_rank",
        "historic_value_gbp_rank": "_value_rank",
    })
    agg = assign_segments(agg)
    agg["historic_value_gbp"] = agg["historic_value_gbp"].round(2)
    agg["avg_order_value_gbp"] = agg["avg_order_value_gbp"].round(2)
    agg["annualised_historic_value_proxy_gbp"] = agg["annualised_historic_value_proxy_gbp"].round(2)
    agg["first_purchase_month"] = agg["first_purchase"].dt.to_period("M").astype(str)
    agg["last_purchase_month"] = agg["last_purchase"].dt.to_period("M").astype(str)
    return agg


def cohort_analysis(orders: pd.DataFrame) -> pd.DataFrame:
    if orders.empty:
        return pd.DataFrame(columns=["cohort_month", "cohort_age_month", "active_customers", "cohort_size", "retention_rate"])
    o = orders[["customer_id", "invoice_no", "order_date"]].copy()
    o["order_date"] = pd.to_datetime(o["order_date"])
    o["order_month"] = o["order_date"].dt.to_period("M")
    first = o.groupby("customer_id")["order_month"].min().rename("cohort_month")
    main_country = orders.groupby("customer_id")["country"].agg(lambda s: s.mode().iloc[0] if not s.mode().empty else "Unknown").rename("country")
    o = o.join(first, on="customer_id").join(main_country, on="customer_id")
    o["cohort_age_month"] = ((o["order_month"].dt.year - o["cohort_month"].dt.year) * 12 + (o["order_month"].dt.month - o["cohort_month"].dt.month)).astype(int)
    active = o.groupby(["country", "cohort_month", "cohort_age_month"])["customer_id"].nunique().rename("active_customers").reset_index()
    size = o.groupby(["country", "cohort_month"])["customer_id"].nunique().rename("cohort_size").reset_index()
    active = active.merge(size, on=["country", "cohort_month"], how="left")
    active["retention_rate"] = (100 * active["active_customers"] / active["cohort_size"]).round(2)
    active["cohort_month"] = active["cohort_month"].astype(str)
    return active.sort_values(["country", "cohort_month", "cohort_age_month"])


def second_purchase_analysis(orders: pd.DataFrame) -> pd.DataFrame:
    delays = []
    for cid, group in orders.groupby("customer_id"):
        dates = pd.to_datetime(group["order_date"]).drop_duplicates().sort_values()
        if len(dates) >= 2:
            country_modes = group["country"].mode()
            country = country_modes.iloc[0] if not country_modes.empty else "Unknown"
            delays.append({"customer_id": cid, "country": country, "days_to_second_purchase": int((dates.iloc[1].normalize() - dates.iloc[0].normalize()).days)})
    return pd.DataFrame(delays, columns=["customer_id", "country", "days_to_second_purchase"])


def repeat_model(orders: pd.DataFrame, snapshot_days: int = 90):
    empty_metrics = {"status": "Not enough data", "snapshot_date": None, "horizon_days": snapshot_days}
    if orders.empty:
        return pd.DataFrame(), pd.DataFrame(), empty_metrics
    order_dates = pd.to_datetime(orders["order_date"])
    min_date = order_dates.min().normalize()
    max_date = order_dates.max().normalize()
    # A calendar window with 90 dates starts 89 days before the final observed date.
    test_cutoff = max_date - pd.Timedelta(days=snapshot_days - 1)
    test_end_exclusive = max_date + pd.Timedelta(days=1)
    feature_cols = ["recency_days", "frequency", "historic_value_gbp", "avg_order_value_gbp", "tenure_days", "unique_products", "countries_seen"]

    def snapshot_frame(cutoff: pd.Timestamp, end_exclusive: pd.Timestamp) -> pd.DataFrame:
        history = orders.loc[pd.to_datetime(orders["order_date"]) < cutoff].copy()
        future = orders.loc[(pd.to_datetime(orders["order_date"]) >= cutoff) & (pd.to_datetime(orders["order_date"]) < end_exclusive)].copy()
        if history.empty:
            return pd.DataFrame()
        features = make_customer_features(history, snapshot=cutoff)
        labels = future.groupby("customer_id").agg(
            repeat_orders_90d=("invoice_no", "nunique"),
            next_90d_value_gbp=("order_value", "sum"),
        ).reset_index()
        features = features.merge(labels, on="customer_id", how="left")
        features["repeat_next_90d"] = features["repeat_orders_90d"].fillna(0).gt(0).astype(int)
        features["next_90d_value_gbp"] = features["next_90d_value_gbp"].fillna(0.0)
        features["snapshot_date"] = str(cutoff.date())
        features = features.replace([np.inf, -np.inf], np.nan)
        return features.dropna(subset=feature_cols).copy()

    test_examples = snapshot_frame(test_cutoff, test_end_exclusive)
    # Earlier, non-overlapping 90-day snapshots supply training examples. Training labels
    # finish before the latest test window starts, which gives the model a time-based test.
    min_training_cutoff = min_date + pd.Timedelta(days=120)
    training_cutoffs = []
    cutoff = test_cutoff - pd.Timedelta(days=snapshot_days)
    while cutoff >= min_training_cutoff:
        training_cutoffs.append(cutoff)
        cutoff -= pd.Timedelta(days=snapshot_days)
    training_cutoffs = sorted(training_cutoffs)
    training_frames = []
    for train_cutoff in training_cutoffs:
        end_exclusive = train_cutoff + pd.Timedelta(days=snapshot_days)
        frame = snapshot_frame(train_cutoff, end_exclusive)
        if not frame.empty:
            training_frames.append(frame)
    if not training_frames or test_examples.empty:
        return test_examples, pd.DataFrame(), {**empty_metrics, "status": "Not enough history to create separate training and future test windows", "snapshot_date": str(test_cutoff.date()), "eligible_customers": int(len(test_examples))}
    training = pd.concat(training_frames, ignore_index=True)
    y_train = training["repeat_next_90d"].astype(int)
    y_test = test_examples["repeat_next_90d"].astype(int)
    if len(training) < 100 or y_train.nunique() < 2 or y_train.value_counts().min() < 8 or y_test.nunique() < 2:
        return test_examples, pd.DataFrame(), {**empty_metrics, "status": "Not enough labelled examples for a stable time-based model check", "snapshot_date": str(test_cutoff.date()), "eligible_customers": int(len(test_examples)), "training_examples": int(len(training)), "training_snapshots": [str(x.date()) for x in training_cutoffs]}
    X_train = training[feature_cols].replace([np.inf, -np.inf], np.nan)
    X_test = test_examples[feature_cols].replace([np.inf, -np.inf], np.nan)
    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scale", StandardScaler()),
        ("logit", LogisticRegression(max_iter=1500, class_weight="balanced", C=0.6, random_state=41)),
    ])
    model.fit(X_train, y_train)
    probs = model.predict_proba(X_test)[:, 1]
    heuristic = (1 / (1 + np.exp((X_test["recency_days"].to_numpy() - 45) / 35))) * np.log1p(X_test["frequency"].to_numpy())
    y_test_arr = y_test.to_numpy()
    auc = float(roc_auc_score(y_test_arr, probs))
    ap = float(average_precision_score(y_test_arr, probs))
    brier = float(brier_score_loss(y_test_arr, probs))
    heur_auc = float(roc_auc_score(y_test_arr, heuristic))
    test_scores = pd.DataFrame({
        "customer_id": test_examples["customer_id"].astype(str).to_numpy(),
        "actual_repeat_next_90d": y_test_arr,
        "predicted_probability": probs,
        "heuristic_score": heuristic,
        "observed_next_90d_value_gbp": test_examples["next_90d_value_gbp"].to_numpy(),
    })
    test_scores["score_decile"] = pd.qcut(test_scores["predicted_probability"].rank(method="first"), 10, labels=False) + 1
    decile = test_scores.groupby("score_decile", as_index=False).agg(
        customers=("actual_repeat_next_90d", "size"),
        observed_repeat_rate=("actual_repeat_next_90d", "mean"),
        observed_next_90d_value_gbp=("observed_next_90d_value_gbp", "sum"),
        mean_predicted_probability=("predicted_probability", "mean"),
    )
    decile["observed_repeat_rate"] = (decile["observed_repeat_rate"] * 100).round(2)
    top = test_scores.loc[test_scores["score_decile"] == test_scores["score_decile"].max()]
    top_rate = float(top["actual_repeat_next_90d"].mean()) if len(top) else 0
    base_rate = float(y_test.mean())
    # These are scores for the most recent test window, not a model for all-history CLV.
    test_examples = test_examples.copy()
    test_examples["repeat_probability_90d"] = probs
    test_examples["score_decile"] = test_scores["score_decile"].to_numpy()
    metrics = {
        "status": "Evaluated on the latest 90-day window; trained only on earlier non-overlapping windows",
        "snapshot_date": str(test_cutoff.date()), "test_end_date": str(max_date.date()), "horizon_days": snapshot_days,
        "eligible_customers": int(len(test_examples)), "train_examples": int(len(training)),
        "train_unique_customers": int(training["customer_id"].nunique()), "test_customers": int(len(test_examples)),
        "training_snapshots": [str(x.date()) for x in training_cutoffs],
        "positive_rate_test_pct": round(100 * base_rate, 2), "roc_auc": round(auc, 4), "average_precision": round(ap, 4),
        "brier_score": round(brier, 4), "heuristic_roc_auc": round(heur_auc, 4),
        "top_decile_repeat_rate_pct": round(100 * top_rate, 2), "top_decile_lift": round(top_rate / base_rate, 2) if base_rate > 0 else None,
        "model_features": feature_cols,
        "note": "Time-based evaluation: all training label windows end before the latest 90-day test window. This is a historical validation, not a live campaign experiment, and it does not predict lifetime value."
    }
    return test_examples, decile, metrics


def make_visualizations(customers: pd.DataFrame, cohorts: pd.DataFrame, delays: pd.DataFrame, value_curve: pd.DataFrame, model_deciles: pd.DataFrame, mode: str):
    VIZ.mkdir(parents=True, exist_ok=True)
    prefix = "SYNTHETIC DEMO DATA" if mode == "demo" else "UCI ONLINE RETAIL II"
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold"})
    # 1. Segment share versus value share
    seg = customers.groupby("segment", as_index=False).agg(customers=("customer_id", "nunique"), value=("historic_value_gbp", "sum"), avg_recency=("recency_days", "mean"), avg_frequency=("frequency", "mean"))
    seg["customer_share_pct"] = seg["customers"] / max(1, seg["customers"].sum()) * 100
    seg["value_share_pct"] = seg["value"] / max(1e-9, seg["value"].sum()) * 100
    seg = seg.sort_values("value_share_pct", ascending=False)
    fig, ax = plt.subplots(figsize=(10.5, 5.7))
    x = np.arange(len(seg)); w = .38
    ax.bar(x-w/2, seg.customer_share_pct, width=w, label="Share of customers")
    ax.bar(x+w/2, seg.value_share_pct, width=w, label="Share of historic value")
    ax.set_xticks(x); ax.set_xticklabels(seg.segment, rotation=28, ha="right")
    ax.set_ylabel("Share (%)"); ax.set_title("Some customer groups carry more value than their size suggests")
    ax.legend(frameon=False, ncol=2); ax.text(.01, -.27, prefix + " | Historic purchase value; not profit", transform=ax.transAxes, fontsize=8)
    fig.tight_layout(); fig.savefig(VIZ/"segment_value_mix.png", dpi=170, bbox_inches="tight"); plt.close(fig)
    # 2. Cohort retention heatmap using matplotlib only.
    if not cohorts.empty:
        active_total = cohorts.groupby(["cohort_month", "cohort_age_month"], as_index=False)["active_customers"].sum()
        size_total = cohorts.groupby(["country", "cohort_month"], as_index=False)["cohort_size"].first().groupby("cohort_month", as_index=False)["cohort_size"].sum()
        matrix_long = active_total.merge(size_total, on="cohort_month", how="left")
        matrix_long["retention_rate"] = 100 * matrix_long["active_customers"] / matrix_long["cohort_size"].replace(0, np.nan)
        matrix = matrix_long.pivot(index="cohort_month", columns="cohort_age_month", values="retention_rate").sort_index()
        matrix = matrix.reindex(columns=list(range(min(19, int(matrix.columns.max())+1))), fill_value=np.nan)
        fig, ax = plt.subplots(figsize=(10.5, max(5.2, min(12, 0.25*len(matrix)+2))))
        im = ax.imshow(matrix.values, aspect="auto", vmin=0, vmax=100, cmap="YlGnBu")
        ax.set_xticks(np.arange(len(matrix.columns))); ax.set_xticklabels([f"M{c}" for c in matrix.columns])
        ax.set_yticks(np.arange(len(matrix.index))); ax.set_yticklabels(matrix.index, fontsize=8)
        ax.set_xlabel("Months since first purchase"); ax.set_ylabel("First purchase month")
        ax.set_title("Cohort retention: which first-purchase groups keep coming back?")
        cb = fig.colorbar(im, ax=ax, fraction=.03, pad=.02); cb.set_label("Customers active in month (%)")
        ax.text(.01, -.12, prefix + " | Later cohorts have fewer observable months", transform=ax.transAxes, fontsize=8)
        fig.tight_layout(); fig.savefig(VIZ/"cohort_retention_heatmap.png", dpi=170, bbox_inches="tight"); plt.close(fig)
    # 3. Pareto curve
    if not value_curve.empty:
        fig, ax = plt.subplots(figsize=(8.8, 5.8))
        ax.plot(value_curve.customer_share_pct, value_curve.cumulative_value_share_pct, linewidth=2.6)
        ax.plot([0,100],[0,100], linestyle="--", linewidth=1.2, label="Even distribution")
        ax.axvline(20, linestyle=":", linewidth=1); ax.axhline(80, linestyle=":", linewidth=1)
        ax.set_xlim(0,100); ax.set_ylim(0,100); ax.set_xlabel("Cumulative share of customers (ranked by value)"); ax.set_ylabel("Cumulative share of historic value")
        ax.set_title("How concentrated is customer value?"); ax.legend(frameon=False)
        ax.text(.01, -.18, prefix + " | Describes observed history, not future revenue", transform=ax.transAxes, fontsize=8)
        fig.tight_layout(); fig.savefig(VIZ/"customer_value_concentration.png", dpi=170, bbox_inches="tight"); plt.close(fig)
    # 4. Time to second purchase
    if not delays.empty:
        vals = delays["days_to_second_purchase"].clip(upper=365)
        fig, ax = plt.subplots(figsize=(8.8, 5.3))
        ax.hist(vals, bins=[0,15,30,45,60,90,120,180,270,365], edgecolor="white")
        ax.set_xlabel("Days between first and second distinct purchase"); ax.set_ylabel("Customers")
        ax.set_title("The second purchase is a key moment to understand")
        ax.text(.01, -.18, prefix + " | Customers who made at least two purchases; 365+ days capped at 365", transform=ax.transAxes, fontsize=8)
        fig.tight_layout(); fig.savefig(VIZ/"second_purchase_timing.png", dpi=170, bbox_inches="tight"); plt.close(fig)
    # 5. Recency vs historic value map
    sample = customers.sample(min(3500, len(customers)), random_state=17) if len(customers) else customers
    palette = {"Champions":"#167D8D", "Loyal Regulars":"#2D9D78", "Potential Loyalists":"#70B77E", "New Customers":"#B7C96B", "At Risk":"#D89E44", "Need Attention":"#D77744", "Hibernating":"#C75B62", "Developing":"#7F84A8"}
    fig, ax = plt.subplots(figsize=(9.5, 5.6))
    for segname, group in sample.groupby("segment"):
        ax.scatter(group.recency_days, np.log1p(group.historic_value_gbp), s=np.clip(group.frequency*7, 14, 130), alpha=.62, label=segname, color=palette.get(segname))
    ax.set_xlabel("Days since last purchase (further right = quieter customer)"); ax.set_ylabel("Log of historic customer value")
    ax.set_title("The retention map: value and silence are different things")
    ax.legend(frameon=False, ncol=2, fontsize=8, loc="best")
    ax.text(.01, -.18, prefix + " | Bubble size reflects purchase frequency", transform=ax.transAxes, fontsize=8)
    fig.tight_layout(); fig.savefig(VIZ/"retention_value_map.png", dpi=170, bbox_inches="tight"); plt.close(fig)
    # 6. Holdout model repeat rate by score decile
    if not model_deciles.empty:
        fig, ax = plt.subplots(figsize=(8.8, 5.2))
        ax.bar(model_deciles.score_decile.astype(str), model_deciles.observed_repeat_rate)
        ax.set_xlabel("Predicted score decile (10 = highest predicted likelihood)"); ax.set_ylabel("Observed repeat rate in holdout (%)")
        ax.set_title("Does the repeat score rank customers usefully?")
        ax.text(.01, -.18, prefix + " | Fixed 90-day horizon; customer holdout, not a live campaign test", transform=ax.transAxes, fontsize=8)
        fig.tight_layout(); fig.savefig(VIZ/"repeat_model_decile_lift.png", dpi=170, bbox_inches="tight"); plt.close(fig)
    return seg


def build_value_curve(customers: pd.DataFrame) -> pd.DataFrame:
    if customers.empty:
        return pd.DataFrame(columns=["customer_rank", "customer_share_pct", "cumulative_value_share_pct"])
    c = customers.sort_values("historic_value_gbp", ascending=False).copy()
    c["customer_rank"] = np.arange(1, len(c)+1)
    total = c["historic_value_gbp"].sum()
    c["cumulative_value_share_pct"] = (100 * c["historic_value_gbp"].cumsum() / total).round(3) if total else 0
    c["customer_share_pct"] = 100 * c["customer_rank"] / len(c)
    return c[["customer_id", "customer_rank", "customer_share_pct", "cumulative_value_share_pct", "historic_value_gbp"]]


def run_analysis(source: str = "demo") -> dict:
    for folder in [OUT, VIZ, PROCESSED]: folder.mkdir(parents=True, exist_ok=True)
    raw = load_raw(source)
    sales, returns, quality = prepare(raw)
    orders = build_orders(sales)
    if orders.empty:
        raise ValueError("No customer-identifiable orders remain after cleaning.")
    snapshot = pd.to_datetime(sales.invoice_date).max().normalize() + pd.Timedelta(days=1)
    customers = make_customer_features(orders, snapshot=snapshot)
    cohorts = cohort_analysis(orders)
    delays = second_purchase_analysis(orders)
    scores, model_deciles, model_metrics = repeat_model(orders, 90)
    value_curve = build_value_curve(customers)
    segment_summary = customers.groupby("segment", as_index=False).agg(
        customers=("customer_id", "nunique"), historic_value_gbp=("historic_value_gbp", "sum"), average_value_gbp=("historic_value_gbp", "mean"),
        median_recency_days=("recency_days", "median"), average_frequency=("frequency", "mean"), repeat_customer_rate=("repeat_buyer", "mean"),
        value_at_risk_proxy_gbp=("historical_value_at_risk_proxy_gbp", "sum")
    )
    segment_summary["customer_share_pct"] = (100 * segment_summary.customers / segment_summary.customers.sum()).round(2)
    segment_summary["historic_value_share_pct"] = (100 * segment_summary.historic_value_gbp / segment_summary.historic_value_gbp.sum()).round(2)
    segment_summary["repeat_customer_rate_pct"] = (100 * segment_summary.repeat_customer_rate).round(2)
    segment_summary["historic_value_gbp"] = segment_summary.historic_value_gbp.round(2)
    segment_summary["average_value_gbp"] = segment_summary.average_value_gbp.round(2)
    segment_summary["value_at_risk_proxy_gbp"] = segment_summary.value_at_risk_proxy_gbp.round(2)
    segment_summary = segment_summary.sort_values("historic_value_gbp", ascending=False)
    # Return analysis is kept separate from sales value; source cancellation lines are not used in customer RFM.
    return_value = float((returns["quantity"].fillna(0) * returns["unit_price"].fillna(0)).sum()) if not returns.empty else 0.0
    total_value = float(orders["order_value"].sum())
    top10_share = float(customers.sort_values("historic_value_gbp", ascending=False).head(max(1, int(np.ceil(len(customers)*0.10)))).historic_value_gbp.sum() / total_value * 100) if total_value else 0
    top20_share = float(customers.sort_values("historic_value_gbp", ascending=False).head(max(1, int(np.ceil(len(customers)*0.20)))).historic_value_gbp.sum() / total_value * 100) if total_value else 0
    metrics = {
        "source_mode": source,
        "source_label": "Synthetic demo data - not actual retailer results" if source == "demo" else "UCI Online Retail II real public dataset",
        "data_start": str(pd.to_datetime(sales.invoice_date).min().date()),
        "data_end": str(pd.to_datetime(sales.invoice_date).max().date()),
        "known_customers": int(customers.customer_id.nunique()),
        "clean_sales_lines": int(len(sales)),
        "identified_order_count": int(orders.invoice_no.nunique()),
        "customer_identified_orders": int(orders.invoice_no.nunique()),
        "identified_customer_historic_value_gbp": round(float(total_value),2),
        "average_order_value_gbp": round(float(orders.order_value.mean()),2),
        "repeat_customer_rate_pct": round(float((customers.frequency >= 2).mean()*100),2),
        "one_order_customer_share_pct": round(float((customers.frequency == 1).mean()*100),2),
        "top_10pct_customer_value_share_pct": round(top10_share,2),
        "top_20pct_customer_value_share_pct": round(top20_share,2),
        "median_recency_days": round(float(customers.recency_days.median()),1),
        "median_days_to_second_purchase": round(float(delays.days_to_second_purchase.median()),1) if len(delays) else None,
        "cancellation_and_return_line_value_gbp": round(return_value,2),
        "quality": quality,
        "repeat_model": model_metrics,
        "business_note": "Historic value is observed item revenue for identified customers. It is not contribution profit and is not a predictive lifetime value estimate."
    }
    # Outputs
    sales.to_csv(PROCESSED/"clean_sales_lines.csv", index=False)
    orders.to_csv(PROCESSED/"customer_orders.csv", index=False)
    customers.to_csv(OUT/"customer_metrics.csv", index=False)
    segment_summary.to_csv(OUT/"segment_summary.csv", index=False)
    cohorts.to_csv(OUT/"cohort_retention.csv", index=False)
    delays.to_csv(OUT/"second_purchase_delays.csv", index=False)
    value_curve.to_csv(OUT/"customer_value_concentration.csv", index=False)
    model_deciles.to_csv(OUT/"repeat_model_deciles.csv", index=False)
    scores.to_csv(OUT/"repeat_model_customer_scores.csv", index=False)
    (OUT/"metrics.json").write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
    # Segment recommendations as an action-oriented table.
    actions = segment_summary.copy()
    actions["recommended_action"] = actions.segment.map(lambda x: SEGMENT_ACTIONS.get(x, SEGMENT_ACTIONS["Developing"])[0])
    actions["how_to_test"] = actions.segment.map(lambda x: SEGMENT_ACTIONS.get(x, SEGMENT_ACTIONS["Developing"])[1])
    actions.to_csv(OUT/"segment_action_plan.csv", index=False)
    segviz = make_visualizations(customers, cohorts, delays, value_curve, model_deciles, source)
    metrics["segment_count"] = int(customers.segment.nunique())
    metrics["model_status"] = model_metrics.get("status")
    (OUT/"metrics.json").write_text(json.dumps(metrics, indent=2, default=str), encoding="utf-8")
    # Create a small SQLite warehouse for query practice.
    db = OUT/"customer_retention.sqlite"
    db.unlink(missing_ok=True)
    with sqlite3.connect(db) as conn:
        sales.rename(columns={"customer_id":"customer_id", "invoice_no":"invoice_no"}).to_sql("clean_sales_lines", conn, index=False)
        orders.to_sql("customer_orders", conn, index=False)
        customers.to_sql("customer_metrics", conn, index=False)
        segment_summary.to_sql("segment_summary", conn, index=False)
        cohorts.to_sql("cohort_retention", conn, index=False)
    return metrics
