"""
Data-mining stage. Reads data/processed/, writes results to reports/.
  1 Association rules (Apriori vs FP-Growth)
  2 Classification of waste level (DT / RF / NB)
  3 Clustering of students (KMeans, elbow + silhouette, ARI vs synthetic ground truth)
  4 Demand + waste prediction (LR / RF / GBR), time-based split
  5 Waste-saving simulator (model-driven prep vs canteen's naive prep)
  6 Anomaly detection on daily waste
"""
from pathlib import Path
import json, time, warnings
import numpy as np
import pandas as pd
from mlxtend.frequent_patterns import apriori, fpgrowth, association_rules
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingRegressor, IsolationForest
from sklearn.tree import DecisionTreeClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.linear_model import LinearRegression
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (accuracy_score, f1_score, confusion_matrix, mean_absolute_error,
                             mean_squared_error, r2_score, silhouette_score, adjusted_rand_score)
warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parents[1]
P, R = ROOT / "data/processed", ROOT / "reports"
R.mkdir(exist_ok=True)
res = {}

sales = pd.read_csv(P / "fact_sales.csv")
items = pd.read_csv(P / "dim_item.csv")
cats = pd.read_csv(P / "dim_category.csv")
students = pd.read_csv(P / "dim_student.csv")
flat = pd.read_csv(P / "flat_item_day.csv")
name = dict(zip(items.item_id, items.item_name))
item_cat = items.merge(cats, on="category_id").set_index("item_id").category_name

# ------------------------------------------------ 1 association rules
basket = (sales.assign(v=1).pivot_table(index="transaction_id", columns="item_id", values="v",
                                       aggfunc="max", fill_value=0).astype(bool))
basket.columns = [name[c] for c in basket.columns]
min_sup = 0.006
t0 = time.time(); fi_a = apriori(basket, min_support=min_sup, use_colnames=True); t_ap = time.time() - t0
t0 = time.time(); fi_f = fpgrowth(basket, min_support=min_sup, use_colnames=True); t_fp = time.time() - t0
rules = association_rules(fi_f, metric="lift", min_threshold=1.2)
rules = rules[(rules.confidence >= 0.2)].sort_values("lift", ascending=False)
rules["antecedents"] = rules.antecedents.apply(lambda s: ", ".join(sorted(s)))
rules["consequents"] = rules.consequents.apply(lambda s: ", ".join(sorted(s)))
rules[["antecedents", "consequents", "support", "confidence", "lift"]].round(4).to_csv(R / "association_rules.csv", index=False)
res["association"] = dict(n_baskets=len(basket), min_support=min_sup, itemsets_apriori=len(fi_a),
                          itemsets_fpgrowth=len(fi_f), apriori_sec=round(t_ap, 3), fpgrowth_sec=round(t_fp, 3),
                          n_rules=len(rules), top_rules=rules.head(8)[["antecedents", "consequents", "lift"]].round(2).to_dict("records"))
print("[assoc]", res["association"]["n_rules"], "rules; apriori %.2fs fpgrowth %.2fs" % (t_ap, t_fp))

# ------------------------------------------------ split (time based)
dates = sorted(flat.date_id.unique())
cut = dates[int(len(dates) * 0.8)]
train, test = flat[flat.date_id < cut], flat[flat.date_id >= cut]
feat = ["day_of_week", "month", "is_weekend", "is_exam_week", "is_fest", "temp_c", "is_rainy",
        "price", "perishability", "item_id", "sold_lag1", "sold_lag7", "sold_ma7", "waste_ma7"]
feat_w = feat + ["qty_prepared"]   # prep plan is known before the day -> legit for waste models
def X(df, f=None): return df[f or feat].astype(float)

# ------------------------------------------------ 2 classification of waste level
lo, hi = train.waste_pct.quantile([0.33, 0.66])
lvl = lambda s: pd.cut(s, [-1, lo, hi, 101], labels=["Low", "Medium", "High"])
ytr, yte = lvl(train.waste_pct), lvl(test.waste_pct)
clf = {"Decision Tree": DecisionTreeClassifier(max_depth=6, random_state=1),
       "Random Forest": RandomForestClassifier(300, max_depth=10, random_state=1, n_jobs=-1),
       "Naive Bayes": GaussianNB()}
res["classification"] = {"thresholds": [round(lo, 2), round(hi, 2)]}
for n, m in clf.items():
    m.fit(X(train, feat_w), ytr); p = m.predict(X(test, feat_w))
    res["classification"][n] = dict(accuracy=round(accuracy_score(yte, p), 3), f1_macro=round(f1_score(yte, p, average="macro"), 3),
                                    confusion=confusion_matrix(yte, p, labels=["Low", "Medium", "High"]).tolist())
    print(f"[clf] {n}: acc={res['classification'][n]['accuracy']} f1={res['classification'][n]['f1_macro']}")
rf = clf["Random Forest"]
pd.Series(rf.feature_importances_, index=feat_w).sort_values(ascending=False).round(4).to_csv(R / "feature_importance_waste_class.csv")

# ------------------------------------------------ 3 clustering students
cat_share = (sales.assign(cat=sales.item_id.map(item_cat)).pivot_table(index="student_id", columns="cat",
             values="amount", aggfunc="sum", fill_value=0))
cat_share = cat_share.div(cat_share.sum(1), axis=0)
it = items.set_index("item_id")
s2 = sales.assign(healthy=sales.item_id.map(it.is_healthy), veg=sales.item_id.map(it.is_veg))
agg = s2.groupby("student_id").agg(visits=("transaction_id", "nunique"), spend=("amount", "sum"),
                                   healthy=("healthy", "mean"), veg=("veg", "mean"))
agg["avg_ticket"] = agg.spend / agg.visits
F = cat_share.join(agg[["visits", "avg_ticket", "healthy"]]).fillna(0)
Z = StandardScaler().fit_transform(F)
ks = range(2, 9); inertia, sil = [], []
for k in ks:
    km = KMeans(k, n_init=10, random_state=1).fit(Z); inertia.append(km.inertia_); sil.append(silhouette_score(Z, km.labels_))
best_k = 5
km = KMeans(best_k, n_init=20, random_state=1).fit(Z)
F["cluster"] = km.labels_
truth = students.set_index("student_id").loc[F.index, "segment_true"]
ari = adjusted_rand_score(truth, F.cluster)
prof = F.groupby("cluster").mean().round(3)
prof["size"] = F.groupby("cluster").size()
# unique labels via optimal assignment of cluster -> segment by trait scores
from scipy.optimize import linear_sum_assignment
zp = (prof[["avg_ticket", "healthy", "Meals", "Snacks", "Desserts", "Fast Food", "Beverages"]] -
      prof[["avg_ticket", "healthy", "Meals", "Snacks", "Desserts", "Fast Food", "Beverages"]].mean()) /      prof[["avg_ticket", "healthy", "Meals", "Snacks", "Desserts", "Fast Food", "Beverages"]].std().replace(0, 1)
seg_score = {"Snack Lover": zp["Snacks"] + 0.5 * zp["Fast Food"], "Health Conscious": zp["healthy"],
             "Meal Regular": zp["Meals"], "Budget Saver": -zp["avg_ticket"] + 0.5 * zp["Beverages"],
             "Foodie": zp["avg_ticket"] + zp["Desserts"]}
names_ = list(seg_score)
M = np.array([[seg_score[n].loc[c] for n in names_] for c in prof.index])
ri, ci = linear_sum_assignment(-M)
prof["label"] = pd.Series({prof.index[r]: names_[c] for r, c in zip(ri, ci)})
prof.to_csv(R / "student_cluster_profiles.csv")
seg = F[["cluster"]].assign(segment_mined=F.cluster.map(prof.label))
seg.to_csv(P / "student_segments.csv")
_ds = pd.read_csv(P / "dim_student.csv").drop(columns=["segment_mined"], errors="ignore")
_ds.merge(seg[["segment_mined"]], left_on="student_id", right_index=True, how="left").to_csv(P / "dim_student.csv", index=False)
res["clustering"] = dict(k=best_k, silhouette_by_k=dict(zip(map(int, ks), np.round(sil, 3).tolist())),
                         inertia_by_k=dict(zip(map(int, ks), np.round(inertia, 1).tolist())),
                         silhouette_at_k=round(float(sil[best_k - 2]), 3), ARI_vs_true_segments=round(float(ari), 3))
print(f"[cluster] k={best_k} silhouette={res['clustering']['silhouette_at_k']} ARI={ari:.3f}")

# ------------------------------------------------ 4 demand + waste prediction
def reg_eval(target, models, f=None):
    out = {}
    for n, m in models.items():
        m.fit(X(train, f), train[target]); p = m.predict(X(test, f)); p = np.clip(p, 0, None)
        out[n] = dict(MAE=round(mean_absolute_error(test[target], p), 3),
                      RMSE=round(float(np.sqrt(mean_squared_error(test[target], p))), 3), R2=round(r2_score(test[target], p), 3))
        print(f"[reg:{target}] {n}: {out[n]}")
    return out
mk = lambda: {"Linear Regression": LinearRegression(),
              "Random Forest": RandomForestRegressor(300, max_depth=12, random_state=1, n_jobs=-1),
              "Gradient Boosting": GradientBoostingRegressor(n_estimators=250, max_depth=3, random_state=1)}
res["demand_prediction"] = reg_eval("qty_sold", mk())
res["waste_prediction"] = reg_eval("waste_pct", mk(), feat_w)
# naive baseline = last-7-day average (what the canteen effectively does)
res["demand_prediction"]["Baseline (7-day avg)"] = dict(
    MAE=round(mean_absolute_error(test.qty_sold, test.sold_ma7), 3),
    RMSE=round(float(np.sqrt(mean_squared_error(test.qty_sold, test.sold_ma7))), 3),
    R2=round(r2_score(test.qty_sold, test.sold_ma7), 3))

# ------------------------------------------------ 5 waste-saving simulator
best = RandomForestRegressor(300, max_depth=12, random_state=1, n_jobs=-1).fit(X(train), train.qty_sold)
pred = np.clip(best.predict(X(test)), 0, None)
t = test.copy(); t["pred"] = pred
cost = items.set_index("item_id").unit_cost
price = items.set_index("item_id").price
sim = {}
for buf in (1.0, 1.05, 1.10, 1.15, 1.20):
    prep = np.ceil(t.pred * buf)
    sold = np.minimum(t.qty_sold, prep)
    waste_units = prep - sold
    sim[buf] = dict(waste_units=float(waste_units.sum()),
                    waste_cost=float((waste_units * t.item_id.map(cost)).sum()),
                    lost_sales_rs=float(((t.qty_sold - sold) * t.item_id.map(price)).sum()))
act = dict(waste_units=float(t.qty_wasted.sum()), waste_cost=float(t.waste_cost.sum()),
           lost_sales_rs=float((t.qty_shortage * t.item_id.map(price)).sum()))
def net(d): return d["waste_cost"] + d["lost_sales_rs"] * 0.5      # lost margin ~50% of price
best_buf = min(sim, key=lambda b: net(sim[b]))
res["simulator"] = dict(actual=act, by_buffer=sim, best_buffer=best_buf,
                        waste_cost_reduction_pct=round(100 * (1 - sim[best_buf]["waste_cost"] / act["waste_cost"]), 1),
                        waste_units_reduction_pct=round(100 * (1 - sim[best_buf]["waste_units"] / act["waste_units"]), 1),
                        test_days=int(test.date_id.nunique()))
print("[sim] best buffer", best_buf, "waste cost reduction %", res["simulator"]["waste_cost_reduction_pct"])
t.assign(recommended_prep=np.ceil(t.pred * best_buf)).loc[:, ["date_id", "item_id", "name", "qty_prepared", "qty_sold", "qty_wasted", "pred", "recommended_prep"]]\
    .round(1).to_csv(R / "recommendations_testperiod.csv", index=False)

# ------------------------------------------------ 6 anomaly detection
daily = flat.groupby("date_id").agg(waste_units=("qty_wasted", "sum"), waste_cost=("waste_cost", "sum"), sold=("qty_sold", "sum"))
iso = IsolationForest(contamination=0.05, random_state=1).fit(daily)
daily["anomaly"] = iso.predict(daily) == -1
daily.to_csv(R / "daily_waste_anomalies.csv")
res["anomaly"] = dict(n_flagged=int(daily.anomaly.sum()), flagged_dates=[int(d) for d in daily.index[daily.anomaly]])

(R / "mining_results.json").write_text(json.dumps(res, indent=2, default=str))
print("saved reports/mining_results.json")
