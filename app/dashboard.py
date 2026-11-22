import json
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
P, R = ROOT / "data/processed", ROOT / "reports"
st.set_page_config(page_title="Smart Canteen DW", layout="wide")
st.title("Smart Canteen – Demand, Preference & Waste Analytics")

@st.cache_data
def load():
    rd = lambda n: pd.read_csv(P / f"{n}.csv")
    item = rd("dim_item").merge(rd("dim_category"), on="category_id")
    sales = (rd("fact_sales").merge(rd("dim_date"), on="date_id")
             .merge(item[["item_id", "item_name", "category_name"]], on="item_id")
             .merge(rd("dim_meal_slot")[["slot_id", "slot_name"]], on="slot_id"))
    waste = rd("fact_waste").merge(rd("dim_date"), on="date_id").merge(item[["item_id", "item_name", "category_name"]], on="item_id")
    return sales, waste, json.loads((R / "mining_results.json").read_text())
sales, waste, res = load()

tab = st.sidebar.radio("Page", ["Overview", "OLAP Explorer", "Association Rules", "Student Segments",
                                "Model Performance", "Waste-Saving Simulator", "Anomalies"])

if tab == "Overview":
    c = st.columns(4)
    c[0].metric("Revenue (Rs)", f"{sales.amount.sum():,.0f}")
    c[1].metric("Transactions", f"{sales.transaction_id.nunique():,}")
    c[2].metric("Waste %", f"{100 * waste.qty_wasted.sum() / waste.qty_prepared.sum():.1f}%")
    c[3].metric("Waste cost (Rs)", f"{waste.waste_cost.sum():,.0f}")
    d = waste.groupby("full_date")[["qty_sold", "qty_wasted"]].sum().reset_index()
    st.plotly_chart(px.line(d, x="full_date", y=["qty_sold", "qty_wasted"], title="Daily demand vs waste"), width='stretch')
    w = waste.groupby("day_name")[["qty_wasted", "qty_prepared"]].sum()
    w["waste_pct"] = 100 * w.qty_wasted / w.qty_prepared
    st.plotly_chart(px.bar(w.reset_index(), x="day_name", y="waste_pct", title="Waste % by weekday"), width='stretch')

elif tab == "OLAP Explorer":
    st.subheader("Slice / Dice / Roll-up / Drill-down / Pivot")
    c = st.columns(4)
    months = c[0].multiselect("Month (slice)", sorted(sales.month_name.unique()), default=list(sales.month_name.unique()))
    slots = c[1].multiselect("Meal slot (dice)", sorted(sales.slot_name.unique()), default=list(sales.slot_name.unique()))
    cats = c[2].multiselect("Category (dice)", sorted(sales.category_name.unique()), default=list(sales.category_name.unique()))
    rainy = c[3].selectbox("Weather", ["All", "Rainy only", "Dry only"])
    df = sales[sales.month_name.isin(months) & sales.slot_name.isin(slots) & sales.category_name.isin(cats)]
    if rainy != "All": df = df[df.is_rainy == (rainy == "Rainy only")]
    level = st.radio("Hierarchy level (roll-up / drill-down)", ["category_name", "item_name"], horizontal=True)
    measure = st.radio("Measure", ["amount", "quantity"], horizontal=True)
    st.plotly_chart(px.bar(df.groupby(level)[measure].sum().sort_values(ascending=False).reset_index(), x=level, y=measure), width='stretch')
    st.write("Pivot: category × meal slot")
    st.dataframe(df.pivot_table(index="category_name", columns="slot_name", values=measure, aggfunc="sum", fill_value=0))

elif tab == "Association Rules":
    r = pd.read_csv(R / "association_rules.csv")
    a = res["association"]
    st.write(f"Apriori {a['apriori_sec']}s vs FP-Growth {a['fpgrowth_sec']}s on {a['n_baskets']:,} baskets (min support {a['min_support']}).")
    st.dataframe(r, width='stretch')
    st.plotly_chart(px.scatter(r, x="support", y="confidence", size="lift", hover_data=["antecedents", "consequents"]), width='stretch')

elif tab == "Student Segments":
    pr = pd.read_csv(R / "student_cluster_profiles.csv")
    cl = res["clustering"]
    st.write(f"K-Means k={cl['k']}, silhouette={cl['silhouette_at_k']}, ARI vs synthetic ground truth={cl['ARI_vs_true_segments']}")
    st.dataframe(pr, width='stretch')
    st.plotly_chart(px.line(x=list(cl["silhouette_by_k"]), y=list(cl["silhouette_by_k"].values()), labels=dict(x="k", y="silhouette"), markers=True), width='stretch')

elif tab == "Model Performance":
    for k, t in [("demand_prediction", "Demand (units sold) – lower MAE/RMSE better"), ("waste_prediction", "Waste % prediction")]:
        st.subheader(t); st.dataframe(pd.DataFrame(res[k]).T)
    st.subheader("Waste-level classification (Low/Medium/High)")
    st.dataframe(pd.DataFrame({m: {"accuracy": v["accuracy"], "f1_macro": v["f1_macro"]} for m, v in res["classification"].items() if m != "thresholds"}).T)
    st.caption("Time-based split: first 80% of days train, last 20% test.")

elif tab == "Waste-Saving Simulator":
    s = res["simulator"]
    st.write(f"Held-out test period: {s['test_days']} days. Prep = predicted demand × buffer.")
    rows = [{"buffer": b, **v} for b, v in s["by_buffer"].items()]
    rows.append({"buffer": "Actual (current practice)", **s["actual"]})
    st.dataframe(pd.DataFrame(rows))
    c = st.columns(2)
    c[0].metric("Waste cost reduction", f"{s['waste_cost_reduction_pct']}%")
    c[1].metric("Waste units reduction", f"{s['waste_units_reduction_pct']}%")
    rec = pd.read_csv(R / "recommendations_testperiod.csv")
    day = st.selectbox("Date", sorted(rec.date_id.unique()))
    st.dataframe(rec[rec.date_id == day][["name", "qty_prepared", "recommended_prep", "qty_sold", "qty_wasted"]])

else:
    a = pd.read_csv(R / "daily_waste_anomalies.csv")
    st.plotly_chart(px.scatter(a, x="date_id", y="waste_cost", color="anomaly", title="Isolation Forest flags unusual waste days"), width='stretch')
    st.dataframe(a[a.anomaly])
