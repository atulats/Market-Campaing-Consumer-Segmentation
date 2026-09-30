# Marketing campaign analytics

An end-to-end customer analytics project based on the supplied assignment PDF, `marketing_campaign_data.csv`, and `marketing_data_dictionary.csv`. It includes a Python EDA notebook, a reproducible cleaning pipeline, a SQLite model and analytical SQL, an interactive Streamlit dashboard, and a PDF report.

For the end-to-end process, see the editable [Word workflow document](WORKFLOW.docx) or [Markdown version](WORKFLOW.md). Regenerate the Word file with `python -m src.create_workflow_docx`.

## Quick start

Use Python 3.10 or newer from this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m src.build_data
python -m src.create_report
python -m streamlit run app.py
```

On macOS or Linux, activate with `source .venv/bin/activate`. The dashboard opens at the local address printed by Streamlit. The app can also clean the raw CSV on first launch if `data/cleaned_marketing.csv` has not been created, but running the build command creates both the clean CSV and SQLite database.

Open [notebooks/marketing_eda.ipynb](notebooks/marketing_eda.ipynb) in VS Code or Jupyter and run all cells. If launched from the `notebooks` folder, the notebook automatically locates the CSV one directory above. The notebook can be regenerated with `python notebooks/build_notebook.py`.

## Deliverables

| Item | File | Purpose |
|---|---|---|
| Dashboard | [app.py](app.py) | Filters by country, education, marital status, age band, income band; explores KPIs, campaigns, segments, products, channels, opportunities, and quality |
| Notebook | [notebooks/marketing_eda.ipynb](notebooks/marketing_eda.ipynb) | Source profiling, cleaning audit, charts, response analysis, segmentation, and sensitivity check |
| Cleaning pipeline | [src/marketing.py](src/marketing.py) | Consistent features and segment rules for all outputs |
| SQL build | [src/build_data.py](src/build_data.py) | Loads the clean data into SQLite using parameterized Pandas/SQLite inserts |
| SQL scripts | [sql/schema.sql](sql/schema.sql), [sql/views.sql](sql/views.sql), [sql/analytic_queries.sql](sql/analytic_queries.sql) | DDL, reporting views, KPI, profile, product, channel, and target queries |
| Report | [report/marketing_campaign_report.pdf](report/marketing_campaign_report.pdf) | Three-page business report with findings, a chart, six recommendations, and limitations |
| Report generator | [src/create_report.py](src/create_report.py) | Rebuilds the PDF from the cleaned CSV |

Generated data files are `data/cleaned_marketing.csv`, `data/cleaning_audit.json`, and `data/marketing.db`. They can be rebuilt from the supplied raw CSV by running `python -m src.build_data`.

## Definitions and cleaning decisions

- Each `ID` is one customer. The supplied file has 56,000 unique IDs; no source values are missing.
- Age is calculated at the latest enrollment date in the file, **2014-06-29**, rather than the current date. Tenure uses that same reference date.
- Invalid dates, implausible ages outside 18-100, and rows with unknown or invalid activity/response fields are excluded. Missing income, if it appears in a replacement source, is filled with the country median and then the overall median, with an imputation flag.
- Income values above the 1.5×IQR upper fence are **flagged, not dropped or capped**. In this dataset 14 are flagged. The notebook compares income-band response rates with and without those flagged observations.
- `Total_Spend` sums the six `Mnt*` fields. `Total_Purchases` sums web, catalog, and store purchases. `NumDealsPurchases` is a discount purchase count and is **not** added again.
- `Any_Campaign_Response` equals 1 if any of the five earlier campaigns or latest campaign was accepted. `Campaign_Acceptances` counts accepted campaigns, so one person may contribute more than one acceptance.
- The PDF's rule segments are implemented literally: high income `Income > 75000`, young `Age < 30`, campaign responder `Response = 1`, high web engagement `NumWebVisitsMonth > 5`, family `Children > 0`, and high spender `Total_Spend > 90th percentile` (cutoff 1,564; strict `>`). Segments overlap.
- The diagnostic `Under_Served` flag means below-median total spend, more than five monthly web visits, and no response to the latest campaign. Its response rate is zero by definition.
- The source dictionary does not name a currency. The PDF's rupee examples are treated as illustrative; all income and spend figures are shown in **source units**.

## Inspect the SQL layer

The following command runs all SQL analysis statements against the generated SQLite database:

```powershell
python -c "import sqlite3; c=sqlite3.connect('data/marketing.db'); c.executescript(open('sql/analytic_queries.sql', encoding='utf-8').read()); print(c.execute('SELECT * FROM segment_kpis').fetchall())"
```

The SQL views include one row per customer per campaign for campaign-level analysis and a segment KPI view. The Python build command performs the data-loading DML and recreates the reporting views. Running it again refreshes the table from the supplied CSV.

## Key results

- Latest campaign response: **14.8%**; response to at least one campaign: **36.4%**.
- The `>100k` income band has **27.8%** latest response (7,277 customers), versus **5.6%** for the `≤35k` band (16,786 customers).
- High spenders average **6.3 store**, **5.5 web**, and **3.2 catalog** purchases versus **4.5**, **4.1**, and **2.0** for other customers.
- **16,765 customers (29.9%)** fit the high-visit, low-spend, nonresponder diagnostic rule.

These are descriptive relationships. The dataset lacks campaign exposure, cost, offer content, timestamps per campaign, and a documented currency, so it cannot establish causal lift, return on investment, or the best communication channel. The report recommends controlled tests before rollout.
