# Data source and licence

## Original dataset

This project is designed to use **Online Retail II** from the UCI Machine Learning Repository, created by Daqing Chen.

- Source: https://archive.ics.uci.edu/dataset/502/online+retail+ii
- DOI: https://doi.org/10.24432/C5CG6D
- Licence: Creative Commons Attribution 4.0 International (CC BY 4.0), as stated by UCI.
- Coverage: transactions from 1 December 2009 through 9 December 2011.
- Size listed by UCI: 1,067,371 transaction rows.

Suggested attribution: Chen, D. (2012). *Online Retail II* [Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5CG6D

Please check the source page when downloading, retain attribution, and follow the applicable licence terms.

## Included demo file

`data/demo_transactions.csv` is a **synthetic teaching sample generated for this project**. It is not a sample extracted from the original UCI file and should not be described as real customer behaviour. It lets the pipeline and dashboard run immediately without an internet connection.

## Why the original workbook is not bundled

The full original workbook is about 43.5 MB. This repository keeps it out of Git history and provides `src/download_data.py` to fetch it directly from UCI. Run the project in real-data mode after downloading it to reproduce the analysis on the original transactions.

## Software licence

The code in this repository is available under the MIT License. That software licence does not replace the separate licence and attribution requirements for the UCI dataset.
