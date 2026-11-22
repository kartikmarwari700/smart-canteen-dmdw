"""Creates report/PPT figures into reports/figures from pipeline outputs."""
from pathlib import Path
import json
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
R, P = ROOT / "reports", ROOT / "data/processed"
F = R / "figures"; F.mkdir(parents=True, exist_ok=True)
res = json.loads((R / "mining_results.json").read_text())
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})
C1, C2, C3 = "#2F6B5E", "#E08E45", "#8A9BA8"

def save(name): plt.tight_layout(); plt.savefig(F / name, bbox_inches="tight"); plt.close()

# 1 waste by weekday
w = pd.read_csv(R / "olap_q7_waste_by_weekday.csv")
plt.figure(figsize=(6.5, 3.6)); b = plt.bar(w.day_name, w.waste_pct, color=[C2 if d == "Saturday" else C1 for d in w.day_name])
plt.bar_label(b, fmt="%.1f%%"); plt.ylabel("Waste %"); plt.title("Waste % by weekday"); save("waste_weekday.png")

# 2 category x slot heatmap
pv = pd.read_csv(R / "olap_q5_pivot_category_slot.csv").set_index("category_name")[["breakfast", "lunch", "snacks", "dinner"]].fillna(0) / 1000
plt.figure(figsize=(6.5, 3.6)); plt.imshow(pv.values, cmap="YlGn", aspect="auto")
plt.xticks(range(4), pv.columns); plt.yticks(range(len(pv)), pv.index)
for i in range(pv.shape[0]):
    for j in range(pv.shape[1]): plt.text(j, i, f"{pv.values[i, j]:.0f}", ha="center", va="center", fontsize=9)
plt.title("OLAP pivot: revenue (Rs '000) by category x meal slot"); save("olap_pivot.png")

# 3 waste cost by category + top items
t = pd.read_csv(R / "olap_q8_top_wasted_items.csv").head(8)
plt.figure(figsize=(6.5, 3.6)); plt.barh(t.item_name[::-1], t.waste_cost[::-1] / 1000, color=C1)
plt.xlabel("Waste cost (Rs '000)"); plt.title("Top wasted items by cost"); save("top_wasted.png")

# 4 model comparison (demand)
d = pd.DataFrame(res["demand_prediction"]).T
plt.figure(figsize=(6.5, 3.6)); b = plt.bar(d.index, d.MAE, color=[C3 if "Baseline" in i else C1 for i in d.index])
plt.bar_label(b, fmt="%.2f"); plt.ylabel("MAE (units)"); plt.xticks(rotation=15, ha="right"); plt.title("Demand prediction: lower MAE is better"); save("demand_models.png")

# 5 clustering: silhouette + elbow
cl = res["clustering"]
fig, ax = plt.subplots(1, 2, figsize=(8, 3.3))
ks = list(map(int, cl["silhouette_by_k"])); ax[0].plot(ks, list(cl["inertia_by_k"].values()), "o-", color=C1); ax[0].set_title("Elbow (inertia)"); ax[0].set_xlabel("k")
ax[1].plot(ks, list(cl["silhouette_by_k"].values()), "o-", color=C2); ax[1].set_title("Silhouette"); ax[1].set_xlabel("k"); save("clustering_k.png")

# 6 simulator
s = res["simulator"]; act = s["actual"]
labels = ["Actual\n(current)"] + [f"Model\nx{b}" for b in s["by_buffer"]]
vals = [act["waste_cost"]] + [v["waste_cost"] for v in s["by_buffer"].values()]
plt.figure(figsize=(6.5, 3.6)); b = plt.bar(labels, [v / 1000 for v in vals], color=[C3] + [C1] * len(s["by_buffer"]))
plt.bar_label(b, fmt="%.1f"); plt.ylabel("Waste cost (Rs '000, test days)"); plt.title("Waste-saving simulator"); save("simulator.png")

# 7 student segments
sd = pd.read_csv(P / "dim_student.csv").segment_mined.value_counts()
plt.figure(figsize=(5.2, 3.6)); plt.pie(sd.values, labels=sd.index, autopct="%1.0f%%", colors=[C1, C2, C3, "#B5C99A", "#D4A5A5"], startangle=90)
plt.title("Student segments (K-Means, k=5)"); save("segments.png")

# 8 daily anomaly
a = pd.read_csv(R / "daily_waste_anomalies.csv"); a["d"] = pd.to_datetime(a.date_id.astype(str))
plt.figure(figsize=(8, 3.3)); plt.plot(a.d, a.waste_cost, color=C1, lw=1)
plt.scatter(a.d[a.anomaly], a.waste_cost[a.anomaly], color="crimson", zorder=3, label="anomaly"); plt.legend()
plt.ylabel("Waste cost (Rs)"); plt.title("Anomaly detection (Isolation Forest)"); save("anomalies.png")

# 9 schema diagram (galaxy)
fig, ax = plt.subplots(figsize=(9, 5.4)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(-0.3, 6.5)
def box(x, y, w_, h, title, rows, fc):
    ax.add_patch(FancyBboxPatch((x, y), w_, h, boxstyle="round,pad=0.03", fc=fc, ec="#333", lw=1))
    ax.text(x + w_ / 2, y + h - 0.2, title, ha="center", va="top", weight="bold", fontsize=9)
    ax.text(x + 0.1, y + h - 0.5, "\n".join(rows), ha="left", va="top", fontsize=7.5)
facts, dims = "#F6D8B5", "#CFE3DA"
box(3.6, 3.7, 2.8, 1.5, "fact_sales", ["transaction_id", "date_id, slot_id", "student_id, item_id", "quantity, unit_price, amount"], facts)
box(3.6, 1.7, 2.8, 1.5, "fact_waste", ["date_id, item_id", "qty_prepared / sold / wasted", "qty_shortage", "waste_cost, waste_pct"], facts)
box(3.6, 0.0, 2.8, 1.3, "fact_inventory", ["date_id, item_id", "opening / received", "used / closing stock"], facts)
box(0.1, 4.2, 2.4, 1.6, "dim_date", ["date_id, full_date", "day, week, month, quarter", "is_weekend / exam / fest", "temp_c, is_rainy"], dims)
box(0.1, 2.4, 2.4, 1.2, "dim_student", ["student_id, residence", "year, branch, budget", "segment_mined"], dims)
box(0.1, 0.8, 2.4, 1.0, "dim_meal_slot", ["slot_id, slot_name", "start / end time"], dims)
box(7.2, 4.2, 2.6, 1.6, "dim_item", ["item_id, item_name", "category_id, cuisine_id", "price, unit_cost", "is_veg, perishability"], dims)
box(7.2, 2.6, 2.6, 0.9, "dim_category", ["category_id, name"], "#E4EDF5")
box(7.2, 1.2, 2.6, 0.9, "dim_cuisine", ["cuisine_id, name"], "#E4EDF5")
for (x1, y1, x2, y2) in [(2.5, 5.0, 3.6, 4.7), (2.5, 3.0, 3.6, 4.2), (2.5, 1.4, 3.6, 4.0), (6.4, 4.7, 7.2, 4.9),
                         (2.5, 4.6, 3.6, 2.7), (6.4, 2.6, 7.2, 4.5), (2.5, 4.5, 3.6, 0.9), (6.4, 0.9, 7.2, 4.3),
                         (8.5, 4.2, 8.5, 3.5), (8.9, 4.2, 8.9, 2.1)]:
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops=dict(arrowstyle="->", color="#666", lw=0.8))
ax.text(5, 6.3, "Fact Constellation (Galaxy) with Snowflake item hierarchy", ha="center", weight="bold")
save("schema_galaxy.png")
print("figures:", sorted(p.name for p in F.iterdir()))
