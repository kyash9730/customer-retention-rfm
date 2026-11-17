# GitHub upload checklist

- [ ] Run `python run_project.py --source real --download` and confirm the mode label says UCI Online Retail II.
- [ ] Read `outputs/insight_summary.md` and check each number against `outputs/metrics.json`.
- [ ] Open the dashboard in a browser and test the country, value floor and action-scenario controls.
- [ ] Open the PDF report and check the segment table, retention page and model caveats.
- [ ] Run `python -m unittest discover -s tests -v`.
- [ ] Keep `data/raw/`, `data/processed/` and the SQLite database out of Git unless you have a specific reason to include them.
- [ ] Keep attribution and source licensing in the README.
- [ ] Replace demo screenshots in the GitHub README after the real-data run.
- [ ] Do not publish synthetic demo figures as findings about the UCI retailer.
