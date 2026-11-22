"""
ETL: Extract (synthetic + optional real Kaggle CSVs) -> Clean/Transform -> Load.

Always writes cleaned CSVs to data/processed/.
Loads into PostgreSQL only if a .env file with DB_* values exists.

Real Kaggle data (optional): drop CSVs into data/raw/. If a file with 'waste' in
its name has columns resembling (date, item/food, quantity prepared/sold/wasted),
it is profiled and reported; see load_real_waste() for the mapping.
"""
from pathlib import Path
import os
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SYN, RAW, PROC = ROOT / "data/synthetic", ROOT / "data/raw", ROOT / "data/processed"
PROC.mkdir(parents=True, exist_ok=True)
log = []

def note(msg):
    print(msg); log.append(msg)

# ---------------------------------------------------------------- extract
menu = pd.read_csv(SYN / "menu.csv")
students = pd.read_csv(SYN / "students.csv")
cal = pd.read_csv(SYN / "calendar.csv", parse_dates=["date"])
sales = pd.read_csv(SYN / "sales.csv")
waste = pd.read_csv(SYN / "waste.csv")
inv = pd.read_csv(SYN / "inventory.csv")
note(f"[extract] sales={len(sales)} waste={len(waste)} inv={len(inv)} students={len(students)}")

# ------------------------------------------------- optional real data (hybrid)
def load_real_waste():
    """Profile real Kaggle waste CSVs found in data/raw and compute calibration stats."""
    files = list(RAW.glob("*.csv"))
    if not files:
        note("[real-data] no CSV in data/raw -> running on synthetic data only")
        return None
    out = []
    for f in files:
        df = pd.read_csv(f)
        note(f"[real-data] {f.name}: rows={len(df)} cols={list(df.columns)[:8]} "
             f"missing={int(df.isna().sum().sum())} dup={int(df.duplicated().sum())}")
        out.append(df)
    return out
real = load_real_waste()

# -------------------------------------------------------------- transform
# 1. cleaning + integrity checks
before = len(sales)
sales = sales.drop_duplicates().dropna()
sales = sales[(sales.quantity > 0) & (sales.unit_price > 0)]
note(f"[clean] sales rows {before} -> {len(sales)}")
waste = waste.drop_duplicates(["date_id", "item_id"])
waste["qty_wasted"] = waste.qty_wasted.clip(lower=0)
assert set(sales.item_id) <= set(menu.item_id), "orphan item in sales"
assert set(sales.student_id) <= set(students.student_id), "orphan student in sales"
assert set(sales.date_id) <= set(cal.date_id), "orphan date in sales"

# 2. dimension building
dim_date = pd.DataFrame({
    "date_id": cal.date_id,
    "full_date": cal.date.dt.date,
    "day_of_week": cal.dow,
    "day_name": cal.date.dt.day_name(),
    "week_of_year": cal.date.dt.isocalendar().week.astype(int),
    "month": cal.month,
    "month_name": cal.date.dt.month_name(),
    "quarter": cal.date.dt.quarter,
    "is_weekend": cal.dow >= 5,
    "is_exam_week": cal.is_exam_week.astype(bool),
    "is_fest": cal.is_fest.astype(bool),
    "temp_c": cal.temp_c,
    "is_rainy": cal.is_rainy.astype(bool),
})
# ---- real (Kaggle) facts, conformed to the same dim_date
real_c = PROC / "real_canteen_waste.csv"; real_k = PROC / "real_kitchen_waste.csv"
fact_real_canteen = fact_kitchen = None
if real_c.exists() and real_k.exists():
    rc, rk = pd.read_csv(real_c), pd.read_csv(real_k)
    fact_real_canteen = rc[["date_id", "meal", "section", "food_category", "waste_kg", "price_per_kg", "cost_loss"]]
    fact_kitchen = rk[["ID", "date_id", "meals_served", "kitchen_staff", "temperature_C", "humidity_percent", "special_event",
                       "past_waste_kg", "staff_experience", "waste_category", "food_waste_kg", "is_outlier"]].rename(columns={"ID": "record_id"})
    fact_kitchen["special_event"] = fact_kitchen.special_event.astype(bool); fact_kitchen["is_outlier"] = fact_kitchen.is_outlier.astype(bool)
    new_ids = sorted((set(rc.date_id) | set(rk.date_id)) - set(dim_date.date_id))
    nd = pd.to_datetime([str(i) for i in new_ids])
    extra = pd.DataFrame({"date_id": new_ids, "full_date": nd.date, "day_of_week": nd.dayofweek, "day_name": nd.day_name(),
                          "week_of_year": nd.isocalendar().week.astype(int).values, "month": nd.month, "month_name": nd.month_name(),
                          "quarter": nd.quarter, "is_weekend": nd.dayofweek >= 5, "is_exam_week": False, "is_fest": False,
                          "temp_c": np.nan, "is_rainy": False})
    dim_date = pd.concat([dim_date, extra], ignore_index=True).sort_values("date_id")
    note(f"[real-data] added {len(extra)} real dates to dim_date; fact_real_canteen_waste={len(fact_real_canteen)} fact_kitchen_waste={len(fact_kitchen)}")
else:
    note("[real-data] real processed tables not found (run src/real_data.py first)")

slots = ["breakfast", "lunch", "snacks", "dinner"]
dim_slot = pd.DataFrame({"slot_id": range(1, 5), "slot_name": slots,
                         "start_time": ["08:00", "12:00", "15:30", "19:00"],
                         "end_time": ["10:30", "14:30", "18:00", "21:30"]})
dim_cuisine = pd.DataFrame({"cuisine_id": range(1, menu.cuisine.nunique() + 1),
                            "cuisine_name": sorted(menu.cuisine.unique())})
dim_category = pd.DataFrame({"category_id": range(1, menu.category.nunique() + 1),
                             "category_name": sorted(menu.category.unique())})
dim_item = (menu.merge(dim_category, left_on="category", right_on="category_name")
                .merge(dim_cuisine, left_on="cuisine", right_on="cuisine_name"))
dim_item = dim_item.rename(columns={"name": "item_name", "perishability": "perishability"})[
    ["item_id", "item_name", "category_id", "cuisine_id", "is_veg", "is_healthy",
     "price", "unit_cost", "perishability"]].sort_values("item_id")
dim_student = students.drop(columns=[]).assign(segment_mined=None)

fact_sales = sales.merge(dim_slot[["slot_id", "slot_name"]], left_on="meal_slot", right_on="slot_name")
fact_sales = fact_sales[["transaction_id", "date_id", "slot_id", "student_id", "item_id",
                         "quantity", "unit_price", "amount"]]
fact_waste, fact_inv = waste, inv

# 3. flat analytical table used by ML (one row per date x item)
flat = (fact_waste.merge(dim_date, on="date_id").merge(menu[["item_id", "name", "category", "price", "perishability"]], on="item_id"))
flat = flat.sort_values(["item_id", "date_id"])
g = flat.groupby("item_id")
flat["sold_lag1"] = g.qty_sold.shift(1)
flat["sold_lag7"] = g.qty_sold.shift(7)
flat["sold_ma7"] = g.qty_sold.transform(lambda s: s.shift(1).rolling(7, min_periods=3).mean())
flat["waste_ma7"] = g.waste_pct.transform(lambda s: s.shift(1).rolling(7, min_periods=3).mean())
flat = flat.dropna().reset_index(drop=True)
flat.to_csv(PROC / "flat_item_day.csv", index=False)
note(f"[transform] flat_item_day rows={len(flat)}")

tables = dict(dim_date=dim_date, dim_meal_slot=dim_slot, dim_cuisine=dim_cuisine, dim_category=dim_category,
              dim_item=dim_item, dim_student=dim_student, fact_sales=fact_sales,
              fact_waste=fact_waste, fact_inventory=fact_inv)
if fact_real_canteen is not None:
    tables["fact_real_canteen_waste"] = fact_real_canteen; tables["fact_kitchen_waste"] = fact_kitchen
for k, v in tables.items():
    v.to_csv(PROC / f"{k}.csv", index=False)
note(f"[load-files] wrote {len(tables)} warehouse tables to data/processed/")

# ------------------------------------------------------------------- load
def load_postgres():
    try:
        from dotenv import load_dotenv
        from sqlalchemy import create_engine, text
    except ImportError:
        return
    load_dotenv(ROOT / ".env")
    if not os.getenv("DB_PASSWORD"):
        note("[load-db] no .env / DB_PASSWORD -> skipped PostgreSQL load (CSV warehouse written)")
        return
    url = "postgresql+psycopg2://{u}:{p}@{h}:{port}/{d}".format(
        u=os.getenv("DB_USER", "postgres"), p=os.getenv("DB_PASSWORD"), h=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"), d=os.getenv("DB_NAME", "postgres"))
    eng = create_engine(url)
    with eng.begin() as c:
        c.execute(text((ROOT / "sql/schema.sql").read_text()))
    order = ["dim_date", "dim_meal_slot", "dim_cuisine", "dim_category", "dim_item", "dim_student",
             "fact_sales", "fact_waste", "fact_inventory"] + [t for t in ("fact_real_canteen_waste", "fact_kitchen_waste") if t in tables]
    for t in order:
        df = tables[t]
        for col in df.columns:
            if col in ("is_veg", "is_healthy", "is_veg_pref"):
                df[col] = df[col].astype(bool)
        df.to_sql(t, eng, schema="canteen_dw", if_exists="append", index=False, chunksize=5000, method="multi")
        note(f"[load-db] canteen_dw.{t}: {len(df)} rows")
load_postgres()

(ROOT / "reports").mkdir(exist_ok=True)
(ROOT / "reports/etl_log.txt").write_text("\n".join(log), encoding="utf-8")
