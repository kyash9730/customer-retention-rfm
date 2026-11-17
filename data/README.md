# Data folder

`demo_transactions.csv` is synthetic data used for the first run. It is included so the dashboard, report and tests work without a download.

To run the analysis on the actual public dataset, use:

```bash
python run_project.py --source real --download
```

The downloader retrieves the UCI Online Retail II workbook into `data/raw/online_retail_II.xlsx`. The workbook is not committed to Git; `data/raw/` is ignored so it is not accidentally uploaded.
