from pathlib import Path
import json
import sqlite3
import unittest
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

class CustomerRetentionProjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.metrics = json.loads((ROOT/"outputs"/"metrics.json").read_text(encoding="utf-8"))
        cls.customers = pd.read_csv(ROOT/"outputs"/"customer_metrics.csv")
        cls.cohorts = pd.read_csv(ROOT/"outputs"/"cohort_retention.csv")
        cls.segments = pd.read_csv(ROOT/"outputs"/"segment_summary.csv")

    def test_demo_is_clearly_labelled(self):
        self.assertEqual(self.metrics["source_mode"], "demo")
        self.assertIn("Synthetic", self.metrics["source_label"])

    def test_customer_grain_and_required_metrics(self):
        self.assertEqual(self.customers["customer_id"].nunique(), len(self.customers))
        for col in ["recency_days", "frequency", "historic_value_gbp", "segment", "r_score", "f_score", "m_score"]:
            self.assertIn(col, self.customers.columns)
        self.assertTrue((self.customers["frequency"] >= 1).all())
        self.assertTrue((self.customers["historic_value_gbp"] > 0).all())
        self.assertTrue(self.customers["segment"].notna().all())

    def test_retention_is_bounded_and_age_zero_is_full(self):
        self.assertTrue(((self.cohorts["retention_rate"] >= 0) & (self.cohorts["retention_rate"] <= 100)).all())
        age_zero = self.cohorts[self.cohorts["cohort_age_month"] == 0]
        self.assertTrue((age_zero["retention_rate"].round(2) == 100).all())

    def test_segment_summary_shares_add_up(self):
        self.assertAlmostEqual(float(self.segments["customer_share_pct"].sum()), 100.0, delta=0.2)
        self.assertAlmostEqual(float(self.segments["historic_value_share_pct"].sum()), 100.0, delta=0.2)

    def test_key_artifacts_exist_and_dashboard_is_standalone(self):
        for rel in [
            "outputs/dashboard.html", "outputs/metrics.json", "outputs/customer_retention.sqlite",
            "reports/customer_retention_strategy_report.pdf", "outputs/insight_summary.md",
            "visualizations/segment_value_mix.png", "visualizations/cohort_retention_heatmap.png",
        ]:
            self.assertTrue((ROOT/rel).exists(), rel)
        html = (ROOT/"outputs"/"dashboard.html").read_text(encoding="utf-8")
        self.assertIn("The Repeat Purchase Lab", html)
        self.assertIn("Plotly.newPlot", html)
        self.assertNotIn("__DATA_JSON__", html)

    def test_sql_queries_run(self):
        db = ROOT/"outputs"/"customer_retention.sqlite"
        with sqlite3.connect(db) as conn:
            for query_file in sorted((ROOT/"sql").glob("*.sql")):
                with self.subTest(query=query_file.name):
                    result = conn.execute(query_file.read_text(encoding="utf-8"))
                    result.fetchmany(5)

if __name__ == "__main__":
    unittest.main()
