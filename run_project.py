from __future__ import annotations
import argparse
import json
from pathlib import Path
import pandas as pd
from src.analysis import run_analysis, SEGMENT_ACTIONS
from src.build_dashboard import build_dashboard
from src.build_report import build_report
from src.generate_demo_data import make_demo

ROOT = Path(__file__).resolve().parent


def write_insight_summary():
    out = ROOT / "outputs"
    metrics = json.loads((out/"metrics.json").read_text(encoding="utf-8"))
    seg = pd.read_csv(out/"segment_summary.csv")
    mode = metrics.get("source_mode", "demo")
    lines = []
    lines.append("# Findings and business implications\n")
    if mode == "demo":
        lines.append("> **Synthetic demo output.** The values below come from generated teaching data and are not findings about the real UCI retailer. Replace them by running the project with the original dataset before using them in a portfolio or interview.\n")
    else:
        lines.append("> Analysis of the UCI Online Retail II dataset. Historic spend means observed transaction value and does not mean profit or predicted future customer value.\n")
    lines.append("## What the numbers say in this run\n")
    lines.append(f"- The customer file contains **{metrics.get('known_customers',0):,} identified customers** over **{metrics.get('data_start')} to {metrics.get('data_end')}**.\n")
    lines.append(f"- Identified customers placed **{metrics.get('identified_order_count',0):,} distinct orders** with **£{metrics.get('identified_customer_historic_value_gbp',0):,.0f}** of observed purchase value.\n")
    lines.append(f"- **{metrics.get('repeat_customer_rate_pct',0):.1f}%** of identified customers made at least two purchases in the window.\n")
    lines.append(f"- The top 10% by observed historic value account for **{metrics.get('top_10pct_customer_value_share_pct',0):.1f}%** of identified customer value in this run.\n")
    if metrics.get("median_days_to_second_purchase") is not None:
        lines.append(f"- Among customers who returned, the median gap from first to second purchase was **{metrics.get('median_days_to_second_purchase'):.0f} days**. This excludes one-time customers.\n")
    if not seg.empty:
        lead = seg.iloc[0]
        lines.append(f"- **{lead.segment}** has the highest total historic value in this run at **£{lead.historic_value_gbp:,.0f}** ({lead.historic_value_share_pct:.1f}% of identified customer value).\n")
    model = metrics.get("repeat_model",{})
    lines.append("\n## What to do with this analysis\n")
    lines.append("1. **Protect valuable, active customers without defaulting to discounts.** Test recognition, service and relevant product suggestions against a holdout group.\n")
    lines.append("2. **Look for value that has gone quiet.** Combine past value and recency when prioritising a win-back list; do not treat the value-at-risk proxy as guaranteed lost revenue.\n")
    lines.append("3. **Build a better second purchase habit.** Use the observed first-to-second purchase timing to choose a sensible follow-up window, then compare contacted and holdout customers.\n")
    lines.append("4. **Keep the model in its lane.** The repeat score ranks the chance of a purchase in one 90-day window. It is not a lifetime-value forecast or proof that a campaign will work.\n")
    lines.append("\n## Model check\n")
    lines.append(f"- Status: {model.get('status','Not available')}\n")
    if model.get("roc_auc") is not None:
        lines.append(f"- Holdout ROC-AUC: **{model.get('roc_auc')}**; baseline heuristic ROC-AUC: **{model.get('heuristic_roc_auc')}**; top-decile lift: **{model.get('top_decile_lift')}x**.\n")
    lines.append("\n## Limits worth saying out loud\n")
    lines.append("- The source contains transaction price, not product cost or contribution margin. The work therefore reports observed purchase value, not profit.\n")
    lines.append("- Customer IDs are absent on some source lines. Those lines remain in the transaction-quality file but cannot be assigned to a known customer for RFM.\n")
    lines.append("- RFM segments are relative groups based on quintiles. Their definitions should be checked when a new time period or market is added.\n")
    lines.append("- The fixed-window model is evaluated on held-out customers from one snapshot. A real campaign still needs a controlled test.\n")
    (out/"insight_summary.md").write_text("".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Run the customer segmentation, retention and value analysis.")
    parser.add_argument("--source", choices=["demo", "real"], default="demo", help="Use the included synthetic demo or the original UCI workbook.")
    parser.add_argument("--download", action="store_true", help="Download the original UCI workbook before a real-data run.")
    parser.add_argument("--force-download", action="store_true", help="Replace the local UCI workbook if it already exists.")
    args = parser.parse_args()
    if args.source == "real" and args.download:
        from src.download_data import download
        download(force=args.force_download)
    if args.source == "demo" and not (ROOT/"data"/"demo_transactions.csv").exists():
        demo = make_demo()
        demo.to_csv(ROOT/"data"/"demo_transactions.csv", index=False)
        print(f"Created synthetic demo data: {len(demo):,} lines")
    metrics = run_analysis(args.source)
    build_dashboard()
    build_report()
    write_insight_summary()
    print("\nProject run completed.")
    print(f"Mode: {metrics['source_label']}")
    print(f"Customers: {metrics['known_customers']:,} | Orders: {metrics['identified_order_count']:,} | Historic value: £{metrics['identified_customer_historic_value_gbp']:,.0f}")
    print("Open outputs/dashboard.html and reports/customer_retention_strategy_report.pdf")
    if args.source == "demo":
        print("Reminder: demo figures are synthetic. Run --source real --download to reproduce results from UCI Online Retail II.")

if __name__ == "__main__":
    main()
