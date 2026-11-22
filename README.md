# Smart Campus Canteen Data Warehouse – Demand, Preference & Waste Prediction
DMDW Lab (26B16CS313), JIIT Noida.

## Team setup (any Windows laptop)
1. Install Python 3.11 and Git. Power BI Desktop is needed only for the Power BI dashboard.
2. Clone the repo, then in PowerShell inside the folder:
```powershell
py -3.11 -m pip install -r requirements.txt
```
3. The two Kaggle datasets are already included in `data/raw/` (see `data/raw/SOURCES.md`); nothing to download.
4. Run everything (about 1 minute): `.\run_all.ps1`
5. Dashboards:
   - Streamlit (works anywhere): `py -3.11 -m streamlit run app/dashboard.py`
   - Power BI: `py -3.11 src/build_powerbi.py`, open `powerbi\CanteenDW.pbip`.
     If charts are blank DO NOT press Refresh (cyclic-reference glitch); run `.\powerbi_refresh.ps1`, then File > Save.
6. Documents: `py -3.11 src/make_figures.py` then `py -3.11 src/make_documents.py` (and `src/make_viva_guide.py`).

Generated folders (`data/synthetic`, `data/processed`, `reports`, `powerbi`) are not in Git; `run_all.ps1` recreates them with identical numbers (fixed seed).

## Pipeline
`src/generate_data.py` → `src/etl.py` → (PostgreSQL `canteen_dw` optional) → `src/olap.py` → `src/mining.py` → `app/dashboard.py`

| Step | What it does |
|---|---|
| generate_data | Rule-based synthetic students, menu, sales, waste, inventory (rules R1–R8 documented in file header) |
| etl | Cleaning, integrity checks, dimension building, fact loading, feature table; loads PostgreSQL if `.env` present |
| sql/schema.sql | Fact Constellation: `fact_sales`, `fact_waste`, `fact_inventory` sharing dims; Snowflake `item→category→cuisine`; Star view |
| olap / olap_queries.sql | Roll-up, drill-down, slice, dice, pivot (10 queries) |
| mining | Apriori vs FP-Growth, DT/RF/NB, K-Means, LR/RF/GBR, waste simulator, Isolation Forest |
| dashboard | Streamlit app with 7 pages |

## Run
```powershell
.\run_all.ps1
py -3.11 -m streamlit run app/dashboard.py
```

## Real Kaggle data (hybrid approach)
Download the two Kaggle datasets and put the CSVs in `data/raw/`. The ETL profiles them (rows, missing, duplicates) and logs to `reports/etl_log.txt`.
Without them the project runs on synthetic data only.

## PostgreSQL (optional)
Create `.env` in this folder:
```
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=postgres
```
Then run `py -3.11 src/etl.py`; then run `sql/olap_queries.sql` in pgAdmin.

## Honest notes for the report
- Synthetic data is clearly separated (`data/synthetic/`); `segment_true` exists only to evaluate clustering (ARI), never as a model input.
- Waste classification is moderate by design: waste depends on random prep error, so exact level is hard to predict; demand prediction is strong (R² ≈ 0.95).
- The simulator estimates savings on held-out days under the generator's assumptions; it is not a real-world measurement.

## Power BI and documents
- `powerbi/CanteenDW.pbip` – Power BI dashboard (7 pages). Regenerate with `py -3.11 src/build_powerbi.py`, then Refresh.
- `py -3.11 src/make_figures.py` then `py -3.11 src/make_documents.py` – rebuilds charts and everything in `documents/`
  (final report, presentation, revised synopsis) from the latest results.
- Placeholders to fill by hand: Power BI screenshots in the report and PPT.

## Real data (done)
`data/raw/university_canteen_waste.csv` and `data/raw/messy_zip/train.csv` are cleaned and analysed by `src/real_data.py` and loaded as `fact_real_canteen_waste` and `fact_kitchen_waste` (conformed to `dim_date`). Results: `reports/real_data_results.json`.
