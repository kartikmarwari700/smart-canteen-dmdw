"""
Real (Kaggle) data: profiling, cleaning, analysis and models.

  data/raw/university_canteen_waste.csv   Food Waste Dataset from a University Canteen
  data/raw/messy_zip/train.csv            Messy Food Waste Prediction Dataset (train only)

Finding: messy test.csv has features identical to train.csv (all 911 IDs overlap) and
submission.csv equals train's target, so there is no independent test set. We therefore use
5-fold cross-validation on train.csv only.

Outputs: data/processed/real_canteen_waste.csv, real_kitchen_waste.csv,
         reports/real_data_results.json, reports/figures/real_*.png
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.dummy import DummyRegressor
from sklearn.model_selection import KFold, cross_validate

ROOT = Path(__file__).resolve().parents[1]
RAW, PROC, R = ROOT / "data/raw", ROOT / "data/processed", ROOT / "reports"
FIG = R / "figures"; PROC.mkdir(parents=True, exist_ok=True); FIG.mkdir(parents=True, exist_ok=True)
out, prof = {}, []
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 150})
C1, C2, C3 = "#2F6B5E", "#E08E45", "#8A9BA8"

# ===================================================== 1. University canteen waste
a = pd.read_csv(RAW / "university_canteen_waste.csv", parse_dates=["Date"])
prof.append(f"canteen: rows={len(a)} missing={int(a.isna().sum().sum())} dups={int(a.duplicated().sum())}")
a = a.drop_duplicates().dropna()
a["cost_check"] = (a.Waste_Weight_kg * a.Unit_Price_per_kg - a.Cost_Loss).abs()
assert a.cost_check.max() < 0.01, "Cost_Loss != weight x price"
a = a.drop(columns="cost_check")
a.columns = ["full_date", "meal", "section", "food_category", "waste_kg", "price_per_kg", "cost_loss"]
a["date_id"] = a.full_date.dt.strftime("%Y%m%d").astype(int)
a["day_name"] = a.full_date.dt.day_name()
a.to_csv(PROC / "real_canteen_waste.csv", index=False)
g = a.groupby("food_category").agg(records=("waste_kg", "size"), total_kg=("waste_kg", "sum"), avg_kg=("waste_kg", "mean"),
                                   price_per_kg=("price_per_kg", "mean"), total_loss=("cost_loss", "sum")).round(2)
out["canteen"] = dict(rows=len(a), days=int(a.full_date.nunique()), date_from=str(a.full_date.min().date()), date_to=str(a.full_date.max().date()),
                      total_kg=round(a.waste_kg.sum(), 1), total_loss=round(a.cost_loss.sum(), 1), avg_kg=round(a.waste_kg.mean(), 2),
                      by_category=g.reset_index().to_dict("records"),
                      by_meal=a.groupby("meal").waste_kg.mean().round(2).to_dict(), by_section=a.groupby("section").waste_kg.mean().round(2).to_dict(),
                      by_day=a.groupby("day_name").waste_kg.mean().round(2).to_dict())
# is the category/meal effect statistically meaningful? (one-way ANOVA F-test via scipy)
from scipy import stats
for col in ("food_category", "meal", "section"):
    f, p = stats.f_oneway(*[x.waste_kg.values for _, x in a.groupby(col)])
    out["canteen"][f"anova_{col}_p"] = round(float(p), 4)

fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
ax[0].bar(g.index, g.total_kg, color=C1); ax[0].set_title("Total waste (kg) by food category"); ax[0].set_ylabel("kg")
ax[1].bar(g.index, g.total_loss / 1000, color=C2); ax[1].set_title("Cost loss (Rs '000) by category")
plt.tight_layout(); plt.savefig(FIG / "real_canteen_category.png", bbox_inches="tight"); plt.close()

# ===================================================== 2. Messy food-waste (train only)
m = pd.read_csv(RAW / "messy_zip/train.csv")
t = pd.read_csv(RAW / "messy_zip/test.csv")
leak = bool(m.drop(columns="food_waste_kg").equals(t)) and len(set(m.ID) & set(t.ID)) == len(m)
raw_miss = int(m.isna().sum().sum())
prof.append(f"messy train: rows={len(m)} missing={raw_miss} dups={int(m.duplicated().sum())} "
            f"category_variants={m.waste_category.nunique()} experience_variants={m.staff_experience.nunique()} test_identical_to_train={leak}")
# cleaning
m["waste_category"] = m.waste_category.str.strip().str.lower().replace({"grains": "grains"})
m["staff_experience"] = m.staff_experience.str.strip().str.lower().fillna("unknown")
m["date"] = pd.to_datetime(m.date)
def iqr_flag(s, k=1.5):
    q1, q3 = s.quantile([.25, .75]); i = q3 - q1; return (s < q1 - k * i) | (s > q3 + k * i)
m["outlier_meals"] = iqr_flag(m.meals_served)
m["outlier_temp"] = iqr_flag(m.temperature_C)
m["outlier_waste"] = iqr_flag(m.food_waste_kg, 3)
m["is_outlier"] = m.outlier_meals | m.outlier_temp
m["date_id"] = m.date.dt.strftime("%Y%m%d").astype(int)
m = m.rename(columns={"date": "full_date"})
m.to_csv(PROC / "real_kitchen_waste.csv", index=False)
out["messy"] = dict(rows=len(m), missing_raw=raw_miss, category_variants_raw=int(pd.read_csv(RAW / "messy_zip/train.csv").waste_category.nunique()),
                    category_clean=sorted(m.waste_category.unique()), experience_clean=sorted(m.staff_experience.unique()),
                    outliers_meals=int(m.outlier_meals.sum()), outliers_temp=int(m.outlier_temp.sum()), outliers_any=int(m.is_outlier.sum()),
                    max_meals=int(m.meals_served.max()), max_temp=round(float(m.temperature_C.max()), 1),
                    test_identical_to_train=leak,
                    corr_with_waste=m[["meals_served", "kitchen_staff", "temperature_C", "humidity_percent", "day_of_week", "special_event",
                                       "past_waste_kg", "food_waste_kg"]].corr()["food_waste_kg"].drop("food_waste_kg").round(3).to_dict(),
                    waste_by_category=m.groupby("waste_category").food_waste_kg.mean().round(2).to_dict(),
                    waste_by_event=m.groupby("special_event").food_waste_kg.mean().round(2).to_dict())

# models: 5-fold CV, with and without outlier rows
FEATS = ["meals_served", "kitchen_staff", "temperature_C", "humidity_percent", "day_of_week", "special_event", "past_waste_kg"]
def design(df): return pd.concat([df[FEATS], pd.get_dummies(df[["waste_category", "staff_experience"]], dtype=float)], axis=1)
models = {"Baseline (mean)": DummyRegressor(), "Linear Regression": LinearRegression(),
          "Random Forest": RandomForestRegressor(300, max_depth=8, random_state=1, n_jobs=-1),
          "Gradient Boosting": GradientBoostingRegressor(n_estimators=200, max_depth=3, random_state=1)}
cv = KFold(5, shuffle=True, random_state=1); res = {}
for label, df in (("all_rows", m), ("outliers_removed", m[~m.is_outlier])):
    X, y = design(df), df.food_waste_kg; res[label] = {"n": len(df)}
    for n, mod in models.items():
        s = cross_validate(mod, X, y, cv=cv, scoring=("neg_mean_absolute_error", "r2"))
        res[label][n] = dict(MAE=round(-s["test_neg_mean_absolute_error"].mean(), 2), MAE_std=round(s["test_neg_mean_absolute_error"].std(), 2),
                             R2=round(s["test_r2"].mean(), 3), R2_std=round(s["test_r2"].std(), 3))
        print(f"[real:{label}] {n}: {res[label][n]}")
out["messy_models"] = res
rf = RandomForestRegressor(300, max_depth=8, random_state=1, n_jobs=-1).fit(design(m[~m.is_outlier]), m[~m.is_outlier].food_waste_kg)
imp = pd.Series(rf.feature_importances_, index=design(m).columns).sort_values(ascending=False).round(4)
out["messy_importance"] = imp.head(8).to_dict()

fig, ax = plt.subplots(1, 2, figsize=(9, 3.4))
ax[0].scatter(m.meals_served[~m.is_outlier], m.food_waste_kg[~m.is_outlier], s=8, color=C1, alpha=.5, label="normal")
ax[0].scatter(m.meals_served[m.is_outlier], m.food_waste_kg[m.is_outlier], s=14, color="crimson", label="outlier"); ax[0].legend()
ax[0].set_xlabel("meals served"); ax[0].set_ylabel("food waste (kg)"); ax[0].set_title("Waste vs meals served")
ax[1].barh(imp.head(6).index[::-1], imp.head(6).values[::-1], color=C2); ax[1].set_title("Random Forest feature importance")
plt.tight_layout(); plt.savefig(FIG / "real_messy_model.png", bbox_inches="tight"); plt.close()

cmp = pd.DataFrame(res["outliers_removed"]).T.drop(index="n")
plt.figure(figsize=(6.5, 3.4)); b = plt.bar(cmp.index, cmp.R2, color=[C3 if "Baseline" in i else C1 for i in cmp.index]); plt.bar_label(b, fmt="%.2f")
plt.ylabel("R2 (5-fold CV)"); plt.xticks(rotation=15, ha="right"); plt.title("Real data: food waste prediction"); plt.tight_layout()
plt.savefig(FIG / "real_messy_cv.png", bbox_inches="tight"); plt.close()

(R / "real_data_results.json").write_text(json.dumps(out, indent=2, default=str))
(R / "real_data_profile.txt").write_text("\n".join(prof), encoding="utf-8")
print("\n".join(prof)); print("saved real_data_results.json")
