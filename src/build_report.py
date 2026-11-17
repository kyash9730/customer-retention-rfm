from pathlib import Path
import json
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak, KeepTogether

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
VIZ = ROOT / "visualizations"
REPORT = ROOT / "reports" / "customer_retention_strategy_report.pdf"

INK = colors.HexColor("#1B3038")
TEAL = colors.HexColor("#126B68")
PALE = colors.HexColor("#EAF2ED")
MUTED = colors.HexColor("#667784")
LINE = colors.HexColor("#DCE3DF")


def money(n):
    return f"£{float(n or 0):,.0f}"


def draw_page(canvas, doc, mode):
    canvas.saveState()
    width, height = A4
    canvas.setStrokeColor(LINE)
    canvas.setLineWidth(0.6)
    canvas.line(18*mm, 15*mm, width-18*mm, 15*mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MUTED)
    label = "SYNTHETIC DEMO DATA - EXAMPLE OUTPUT" if mode == "demo" else "UCI ONLINE RETAIL II - ANALYSIS OUTPUT"
    canvas.drawString(18*mm, 10*mm, label)
    canvas.drawRightString(width-18*mm, 10*mm, f"Page {doc.page}")
    if doc.page > 1:
        canvas.setFillColor(TEAL)
        canvas.setFont("Helvetica-Bold", 8)
        canvas.drawString(18*mm, height-13*mm, "THE REPEAT PURCHASE LAB")
    canvas.restoreState()


def build_report():
    metrics = json.loads((OUT/"metrics.json").read_text(encoding="utf-8"))
    seg = pd.read_csv(OUT/"segment_summary.csv")
    model = metrics.get("repeat_model", {})
    mode = metrics.get("source_mode", "demo")
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Hero", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=28, leading=32, textColor=INK, spaceAfter=10, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="SubHero", parent=styles["Normal"], fontSize=12, leading=17, textColor=MUTED, spaceAfter=11))
    styles.add(ParagraphStyle(name="Section", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=INK, spaceBefore=5, spaceAfter=8))
    styles.add(ParagraphStyle(name="SubSection", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=11, leading=14, textColor=TEAL, spaceBefore=6, spaceAfter=4))
    styles.add(ParagraphStyle(name="Body2", parent=styles["BodyText"], fontSize=9, leading=13, textColor=INK, spaceAfter=6))
    styles.add(ParagraphStyle(name="Small2", parent=styles["BodyText"], fontSize=7.6, leading=10, textColor=MUTED, spaceAfter=4))
    styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=TEAL, backColor=PALE, borderPadding=8, spaceBefore=6, spaceAfter=8))
    doc = SimpleDocTemplate(str(REPORT), pagesize=A4, rightMargin=18*mm, leftMargin=18*mm, topMargin=22*mm, bottomMargin=22*mm, title="The Repeat Purchase Lab - Customer Retention Strategy", author="Customer Analytics Portfolio Project")
    story = []
    tag = "SYNTHETIC DEMO - SWAP IN THE ORIGINAL DATA BEFORE USING ANY FIGURES" if mode == "demo" else "ANALYSIS OF UCI ONLINE RETAIL II"
    story += [Spacer(1, 14*mm), Paragraph("THE REPEAT<br/>PURCHASE LAB", styles["Hero"]), Paragraph("Customer segmentation, retention and lifetime-to-date value", styles["SubHero"]), Paragraph(tag, styles["Callout"]), Spacer(1, 5*mm)]
    story.append(Paragraph("The decision", styles["Section"]))
    story.append(Paragraph("A retailer can tell you how much it sold. The harder question is where to put the next retention effort: protecting strong relationships, helping newer customers buy again, or trying to win back people who have gone quiet. This report turns purchase history into a practical set of choices.", styles["Body2"]))
    story.append(Paragraph("What is measured", styles["SubSection"]))
    story.append(Paragraph("The analysis uses RFM segmentation, first-purchase cohorts, time to second purchase, customer value concentration and a simple ranking model for a repeat purchase in the next 90 days. Historic purchase value is the sum of sales value observed in the file. It is not profit and it is not a forecast of a customer's full future value.", styles["Body2"]))
    kpis = [
        ["Known customers", f"{metrics.get('known_customers',0):,}", "Historic purchase value", money(metrics.get("identified_customer_historic_value_gbp",0))],
        ["Repeat customer share", f"{metrics.get('repeat_customer_rate_pct',0):.1f}%", "Median days since purchase", f"{metrics.get('median_recency_days',0):.0f}"],
        ["Value held by top 10%", f"{metrics.get('top_10pct_customer_value_share_pct',0):.1f}%", "Median first-to-second gap", f"{metrics.get('median_days_to_second_purchase') or 0:.0f} days"],
    ]
    t=Table(kpis, colWidths=[34*mm,28*mm,45*mm,35*mm], rowHeights=[15*mm]*3)
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),PALE),("TEXTCOLOR",(0,0),(-1,-1),INK),("FONTNAME",(0,0),(-1,-1),"Helvetica"),
        ("FONTNAME",(1,0),(1,-1),"Helvetica-Bold"),("FONTNAME",(3,0),(3,-1),"Helvetica-Bold"),
        ("FONTSIZE",(0,0),(-1,-1),8),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("GRID",(0,0),(-1,-1),.4,colors.white),
        ("LEFTPADDING",(0,0),(-1,-1),7),("RIGHTPADDING",(0,0),(-1,-1),6)]))
    story += [Spacer(1,3*mm),t,Spacer(1,5*mm),Paragraph("How to read this report", styles["SubSection"]),Paragraph("If the mode label says synthetic demo, the numbers and charts only show that the workflow runs. Download the original UCI workbook and rerun the project before using any result in a portfolio, interview or business recommendation.", styles["Body2"]),PageBreak()]

    story.append(Paragraph("01 / Where value lives", styles["Section"]))
    story.append(Paragraph("RFM groups customers using how recently they purchased, how often they purchased and how much they spent. The group names are there to make the output easier to act on; the cut-offs are relative to this dataset and will change when the input changes.", styles["Body2"]))
    if (VIZ/"segment_value_mix.png").exists(): story.append(Image(str(VIZ/"segment_value_mix.png"), width=172*mm, height=93*mm))
    data=[["Segment","Customers","Customer share","Historic value","Value share","Median recency"]]
    for _,r in seg.sort_values("historic_value_gbp",ascending=False).head(8).iterrows():
        data.append([str(r.segment),f"{int(r.customers):,}",f"{float(r.customer_share_pct):.1f}%",money(r.historic_value_gbp),f"{float(r.historic_value_share_pct):.1f}%",f"{float(r.median_recency_days):.0f} days"])
    tbl=Table(data,colWidths=[35*mm,21*mm,27*mm,30*mm,22*mm,28*mm],repeatRows=1)
    tbl.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),INK),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),7.3),("GRID",(0,0),(-1,-1),.35,LINE),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor('#F6F8F5')]),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    story += [Spacer(1,2*mm),tbl,Spacer(1,3*mm),Paragraph("Decision to consider",styles["SubSection"]),Paragraph("Do not spend the same amount of effort on every segment. Pair historic value with how long the customer has been quiet: a previously valuable customer who has not returned can deserve a different treatment from a one-time buyer with a small basket.",styles["Body2"]),PageBreak()]

    story.append(Paragraph("02 / Where customers drift", styles["Section"]))
    story.append(Paragraph("Cohort retention groups customers by the month of their first purchase and measures how many of those customers are active in later calendar months. Empty cells near the right edge are unobserved, not zero. The time-to-second-purchase view focuses on customers who did make another order, so it does not include people who never returned.", styles["Body2"]))
    for name, w, h in [("cohort_retention_heatmap.png",172*mm,92*mm),("second_purchase_timing.png",162*mm,86*mm)]:
        p=VIZ/name
        if p.exists(): story.append(Image(str(p),width=w,height=h))
    story += [Paragraph("Interpretation guardrail", styles["SubSection"]),Paragraph("A cohort chart can reveal when activity fades, but it does not by itself explain why. Pricing, delivery, product mix, campaign exposure and seasonality are not randomised here. The next step is to test a specific intervention against a holdout group.", styles["Body2"]),PageBreak()]

    story.append(Paragraph("03 / Can a repeat score help?", styles["Section"]))
    story.append(Paragraph("The project fits a logistic regression model using customer history available before a fixed snapshot date. The label is whether the customer made another purchase in the next 90 days. Training uses earlier, non-overlapping 90-day windows. The latest 90-day window is held back for a time-based check.", styles["Body2"]))
    if (VIZ/"repeat_model_decile_lift.png").exists(): story.append(Image(str(VIZ/"repeat_model_decile_lift.png"),width=164*mm,height=88*mm))
    model_rows=[["Evaluation measure","Result"],["ROC-AUC",str(model.get("roc_auc","Not available"))],["Average precision",str(model.get("average_precision","Not available"))],["Baseline heuristic ROC-AUC",str(model.get("heuristic_roc_auc","Not available"))],["Holdout customers",f"{model.get('test_customers',0):,}"],["Top-decile lift",str(model.get("top_decile_lift","Not available"))]]
    mt=Table(model_rows,colWidths=[69*mm,45*mm])
    mt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),INK),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),("GRID",(0,0),(-1,-1),.4,LINE),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE]),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("LEFTPADDING",(0,0),(-1,-1),7),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    story += [Spacer(1,2*mm),mt,Spacer(1,3*mm),Paragraph("Limits",styles["SubSection"]),Paragraph("The score is a ranking aid, not a promised outcome. A customer may buy again without receiving a message. To learn whether a campaign causes incremental purchases, run a controlled test. The data also lacks product cost and acquisition cost, so true profit-based customer lifetime value cannot be calculated from the source fields alone.",styles["Body2"]),PageBreak()]

    story.append(Paragraph("04 / What to do next", styles["Section"]))
    story.append(Paragraph("Use the segment name to set a working hypothesis, then test it with a small controlled audience. Keep the offer relevant and the cost in proportion to the value at stake.",styles["Body2"]))
    playbook = [
        ["Champions","Protect the relationship","Recognition, early access and reliable service. Avoid unnecessary discounting."],
        ["Loyal Regulars","Grow the basket","Useful bundles or complementary products. Measure additional basket value."],
        ["Potential Loyalists","Build the second habit","A relevant follow-up and a reason to return before the next natural buying window."],
        ["New Customers","Make the first experience count","Follow-up after fulfilment, product guidance and a low-friction next purchase."],
        ["At Risk","Win back valuable relationships","Start with a low-cost personal message, then use a discount only if justified."],
        ["Need Attention","Understand the silence","Ask for feedback or offer service help before assuming the customer has churned."],
        ["Hibernating","Run a small reactivation test","One targeted message with a strict budget cap and clear stop rule."],
    ]
    pt=Table([["Group","Aim","First move"]]+playbook,colWidths=[33*mm,39*mm,79*mm],repeatRows=1)
    pt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),INK),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),7.5),("GRID",(0,0),(-1,-1),.35,LINE),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor('#F6F8F5')]),("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),5),("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
    story += [pt,Spacer(1,5*mm),Paragraph("A simple test plan",styles["SubSection"]),Paragraph("1. Pick one segment and define the action. 2. Randomly hold out a comparable share of customers. 3. Use the same observation window for both groups. 4. Compare incremental repeat purchase and contribution after contact cost. 5. Record unsubscribes and complaints alongside revenue. 6. Continue only if the result is worth the cost and the customer experience is acceptable.",styles["Body2"]),Paragraph("Suggested interview summary",styles["SubSection"]),Paragraph("I built a customer analytics workflow that turns transaction lines into RFM segments, cohort retention measures and a 90-day repeat-purchase ranking. The output is designed for a business decision: which customer groups to protect, grow or reactivate, and how to test an intervention without confusing historical spend with profit or causal impact.",styles["Body2"]),Spacer(1,3*mm),Paragraph("Source: Chen, D. (2012). Online Retail II [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D. The included CSV is synthetic and is marked as such; switch to the original source before using reported figures as findings.",styles["Small2"])]
    REPORT.parent.mkdir(parents=True,exist_ok=True)
    doc.build(story, onFirstPage=lambda c,d: draw_page(c,d,mode), onLaterPages=lambda c,d: draw_page(c,d,mode))
    print(f"Built report: {REPORT}")

if __name__ == "__main__":
    build_report()
