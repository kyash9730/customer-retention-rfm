"""Download UCI Online Retail II. The original workbook is kept outside Git."""
from pathlib import Path
import argparse
import shutil
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TARGET = RAW / "online_retail_II.xlsx"
URLS = [
    "https://archive.ics.uci.edu/static/public/502/online+retail+ii.zip",
    "https://archive.ics.uci.edu/ml/machine-learning-databases/00502/online_retail_II.xlsx",
]


def download(force: bool = False) -> Path:
    RAW.mkdir(parents=True, exist_ok=True)
    if TARGET.exists() and not force:
        print(f"Already downloaded: {TARGET}")
        return TARGET
    errors = []
    for url in URLS:
        temporary = RAW / ("download.tmp" + (".zip" if url.endswith(".zip") else ".xlsx"))
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "customer-retention-portfolio/1.0 (educational project)"})
            with urllib.request.urlopen(req, timeout=90) as response, open(temporary, "wb") as out:
                shutil.copyfileobj(response, out)
            if url.lower().endswith(".zip"):
                with zipfile.ZipFile(temporary) as zf:
                    candidates = [n for n in zf.namelist() if n.lower().endswith((".xlsx", ".xls"))]
                    if not candidates:
                        raise RuntimeError("The downloaded ZIP did not contain an Excel workbook.")
                    with zf.open(candidates[0]) as src, open(TARGET, "wb") as dst:
                        shutil.copyfileobj(src, dst)
            else:
                # An .xlsx workbook is itself a ZIP container internally. Do not
                # treat it as the outer download archive merely because zipfile
                # recognises it as ZIP formatted.
                shutil.move(str(temporary), str(TARGET))
            temporary.unlink(missing_ok=True)
            print(f"Downloaded UCI workbook to {TARGET}")
            return TARGET
        except Exception as exc:
            errors.append(f"{url}: {exc}")
            temporary.unlink(missing_ok=True)
    raise RuntimeError("Could not download the UCI workbook. Check your connection and try again.\n" + "\n".join(errors))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    download(args.force)
