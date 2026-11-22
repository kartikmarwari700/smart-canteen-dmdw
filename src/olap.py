"""OLAP operations in pandas (same logic as sql/olap_queries.sql) -> reports/olap_*.csv"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P, R = ROOT / "data/processed", ROOT / "reports"
R.mkdir(exist_ok=True)
rd = lambda n: pd.read_csv(P / f"{n}.csv")
fs, fw = rd("fact_sales"), rd("fact_waste")
dd, it, ca, sl, st = rd("dim_date"), rd("dim_item"), rd("dim_category"), rd("dim_meal_slot"), rd("dim_student")

item = it.merge(ca, on="category_id")
sales = (fs.merge(dd, on="date_id").merge(item[["item_id", "item_name", "category_name"]], on="item_id")
           .merge(sl[["slot_id", "slot_name"]], on="slot_id").merge(st[["student_id", "residence"]], on="student_id"))
waste = fw.merge(dd, on="date_id").merge(item[["item_id", "item_name", "category_name"]], on="item_id")

out = {}
out["q1_rollup_month"] = sales.groupby(["quarter", "month_name"]).amount.sum().reset_index()
out["q2_drilldown_category_item"] = sales.groupby(["category_name", "item_name"]).amount.sum().reset_index().sort_values(["category_name", "amount"], ascending=[True, False])
out["q3_slice_rainy"] = sales[sales.is_rainy].groupby("item_name").quantity.sum().sort_values(ascending=False).head(10).reset_index()
out["q4_dice"] = (sales[(~sales.is_weekend) & sales.slot_name.isin(["lunch", "dinner"]) & sales.category_name.isin(["Meals", "Fast Food"])]
                  .groupby(["day_name", "slot_name", "category_name"]).amount.sum().reset_index().sort_values("amount", ascending=False))
out["q5_pivot_category_slot"] = sales.pivot_table(index="category_name", columns="slot_name", values="amount", aggfunc="sum").reset_index()
g = waste.groupby("category_name")[["qty_sold", "qty_wasted", "qty_prepared", "waste_cost"]].sum()
g["waste_pct"] = (100 * g.qty_wasted / g.qty_prepared).round(1)
out["q6_galaxy_category_waste"] = g.sort_values("waste_cost", ascending=False).reset_index()
w = waste.groupby(["day_of_week", "day_name"])[["qty_wasted", "qty_prepared"]].sum()
w["waste_pct"] = (100 * w.qty_wasted / w.qty_prepared).round(1)
out["q7_waste_by_weekday"] = w.reset_index()
out["q8_top_wasted_items"] = waste.groupby("item_name").waste_cost.sum().sort_values(ascending=False).head(10).reset_index()
sales["day_type"] = sales.apply(lambda r: "Fest" if r.is_fest else "Exam week" if r.is_exam_week else "Normal", axis=1)
x = sales.groupby("day_type").agg(rev=("amount", "sum"), days=("date_id", "nunique"))
out["q9_daytype_revenue"] = (x.rev / x.days).round(0).rename("avg_daily_revenue").reset_index()
out["q10_residence_slot"] = sales.groupby(["residence", "slot_name"]).amount.sum().reset_index()

for k, v in out.items():
    v.to_csv(R / f"olap_{k}.csv", index=False)
    print(f"--- {k}\n{v.head(6).to_string(index=False)}\n")
