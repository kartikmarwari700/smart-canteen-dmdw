"""
Synthetic data generator for the Smart Canteen DW project.

Generates rule-driven (NOT random) supporting data:
  students, menu items, calendar/weather/events, sales lines, waste, inventory.

Business rules (documented so the report can cite them as "ground truth"):
  R1  Weekends / exam weeks / holidays reduce footfall; fest days raise it.
  R2  Rain and cold weather raise tea/coffee/pakora/maggi demand, cut cold drinks.
  R3  Hot days (>33C) raise cold drinks / ice cream, cut hot snacks.
  R4  Hostel students eat dinner/breakfast more; day-scholars eat lunch/snacks.
  R5  Students belong to latent preference segments (ground truth for clustering).
  R6  Combo rules (samosa+chai, burger+coke, ...) create association patterns.
  R7  Canteen preps using a naive rule (last-7-day avg x 1.25 + noise), so
      over-prep happens on low-demand days and shortages on high-demand days.
  R8  Perishable items (higher spoilage) waste more; waste is also kept
      realistic via unsold-leftover reuse factor.

Output: CSVs in data/synthetic/. Fully reproducible via SEED.
"""
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42
START, END = "2025-08-01", "2025-11-30"
N_STUDENTS = 600
OUT = Path(__file__).resolve().parents[1] / "data" / "synthetic"

rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------- menu
# name, category, cuisine, veg, healthy, price, cost, slots, base_pop, perishable
MENU = [
    ("Poha",            "Breakfast",  "North Indian", 1, 1, 25, 10, ["breakfast"],           1.0, 0.6),
    ("Aloo Paratha",    "Breakfast",  "North Indian", 1, 0, 35, 15, ["breakfast"],           1.1, 0.5),
    ("Idli Sambar",     "Breakfast",  "South Indian", 1, 1, 30, 12, ["breakfast"],           0.9, 0.7),
    ("Bread Omelette",  "Breakfast",  "Continental",  0, 1, 30, 14, ["breakfast","snacks"],  0.8, 0.5),
    ("Veg Thali",       "Meals",      "North Indian", 1, 1, 70, 32, ["lunch","dinner"],      1.6, 0.8),
    ("Rajma Chawal",    "Meals",      "North Indian", 1, 1, 55, 24, ["lunch","dinner"],      1.3, 0.8),
    ("Chole Bhature",   "Meals",      "North Indian", 1, 0, 60, 26, ["lunch"],               1.4, 0.7),
    ("Chicken Biryani", "Meals",      "Mughlai",      0, 0, 90, 45, ["lunch","dinner"],      1.2, 0.9),
    ("Paneer Wrap",     "Fast Food",  "Continental",  1, 0, 60, 27, ["lunch","snacks"],      1.0, 0.6),
    ("Veg Burger",      "Fast Food",  "Continental",  1, 0, 45, 19, ["lunch","snacks"],      1.1, 0.5),
    ("French Fries",    "Fast Food",  "Continental",  1, 0, 40, 15, ["snacks"],              1.1, 0.4),
    ("Veg Maggi",       "Fast Food",  "Indo-Chinese", 1, 0, 35, 13, ["snacks","dinner"],     1.5, 0.3),
    ("Veg Momos",       "Fast Food",  "Indo-Chinese", 1, 0, 50, 21, ["snacks","dinner"],     1.2, 0.5),
    ("Fried Rice",      "Fast Food",  "Indo-Chinese", 1, 0, 55, 23, ["lunch","dinner"],      0.9, 0.6),
    ("Samosa",          "Snacks",     "North Indian", 1, 0, 15,  6, ["snacks","breakfast"],  1.8, 0.4),
    ("Pakora",          "Snacks",     "North Indian", 1, 0, 30, 11, ["snacks"],              0.9, 0.4),
    ("Sandwich",        "Snacks",     "Continental",  1, 1, 40, 17, ["breakfast","snacks"],  1.0, 0.5),
    ("Fruit Salad",     "Snacks",     "Healthy",      1, 1, 40, 20, ["lunch","snacks"],      0.5, 0.9),
    ("Tea",             "Beverages",  "Beverage",     1, 1, 10,  3, ["breakfast","snacks"],  2.2, 0.1),
    ("Coffee",          "Beverages",  "Beverage",     1, 1, 20,  7, ["breakfast","snacks"],  1.4, 0.1),
    ("Cold Drink",      "Beverages",  "Beverage",     1, 0, 25, 17, ["lunch","snacks","dinner"], 1.3, 0.05),
    ("Lassi",           "Beverages",  "Beverage",     1, 1, 30, 12, ["lunch","snacks"],      0.8, 0.8),
    ("Cold Coffee",     "Beverages",  "Beverage",     1, 0, 40, 16, ["snacks"],              0.9, 0.3),
    ("Ice Cream",       "Desserts",   "Dessert",      1, 0, 30, 15, ["lunch","snacks","dinner"], 0.8, 0.2),
    ("Gulab Jamun",     "Desserts",   "Dessert",      1, 0, 25, 10, ["lunch","dinner"],      0.6, 0.6),
]
menu = pd.DataFrame(MENU, columns=["name","category","cuisine","is_veg","is_healthy",
                                   "price","unit_cost","slots","base_pop","perishability"])
menu.insert(0, "item_id", range(1, len(menu) + 1))
ITEM = {r.name: r.item_id for r in menu.itertuples()}

# --------------------------------------------------------------- students
# latent segments = ground truth for clustering evaluation
SEGMENTS = {
    "Snack Lover":      dict(w=0.28, cats={"Snacks":2.2,"Fast Food":1.6,"Beverages":1.3}, budget=(40,90)),
    "Health Conscious": dict(w=0.17, cats={"Breakfast":1.4,"Meals":1.2,"Snacks":0.6,"Fast Food":0.4}, budget=(60,120), healthy=2.2),
    "Meal Regular":     dict(w=0.30, cats={"Meals":2.4,"Beverages":0.9}, budget=(60,130)),
    "Budget Saver":     dict(w=0.15, cats={"Snacks":1.8,"Beverages":1.6,"Breakfast":1.2}, budget=(20,50), cheap=2.0),
    "Foodie":           dict(w=0.10, cats={"Fast Food":1.8,"Desserts":2.2,"Meals":1.2}, budget=(90,200)),
}
seg_names = list(SEGMENTS)
seg_p = np.array([SEGMENTS[s]["w"] for s in seg_names]); seg_p /= seg_p.sum()

students = pd.DataFrame({
    "student_id": np.arange(1, N_STUDENTS + 1),
    "segment_true": rng.choice(seg_names, N_STUDENTS, p=seg_p),
    "residence": rng.choice(["Hostel", "Day Scholar"], N_STUDENTS, p=[0.55, 0.45]),
    "year": rng.choice([1, 2, 3, 4], N_STUDENTS, p=[0.32, 0.28, 0.24, 0.16]),
    "branch": rng.choice(["CSE", "ECE", "BT", "Civil", "Mech"], N_STUDENTS, p=[0.40, 0.25, 0.12, 0.10, 0.13]),
    "gender": rng.choice(["M", "F"], N_STUDENTS, p=[0.58, 0.42]),
})
students["is_veg_pref"] = (rng.random(N_STUDENTS) < 0.55).astype(int)
students["avg_budget"] = [rng.integers(*SEGMENTS[s]["budget"]) for s in students.segment_true]
students["visit_freq"] = np.clip(rng.normal(0.55, 0.15, N_STUDENTS), 0.15, 0.95).round(2)  # P(visit canteen/day)

# ----------------------------------------------------------- calendar
dates = pd.bdate_range(START, END, freq="C", weekmask="Mon Tue Wed Thu Fri Sat")
cal = pd.DataFrame({"date": dates})
cal["dow"] = cal.date.dt.dayofweek
cal["month"] = cal.date.dt.month
doy = cal.date.dt.dayofyear.values
temp = 31 - 0.17 * (doy - 213) + 3 * np.sin(doy / 4) + rng.normal(0, 1.8, len(cal))  # cools after Aug
cal["temp_c"] = np.round(temp, 1)
rain_p = np.where(cal.month <= 9, 0.28, 0.06)
cal["is_rainy"] = (rng.random(len(cal)) < rain_p).astype(int)
cal.loc[cal.is_rainy == 1, "temp_c"] -= 3
cal["is_exam_week"] = ((cal.date >= "2025-09-22") & (cal.date <= "2025-09-30")) | \
                      ((cal.date >= "2025-11-17") & (cal.date <= "2025-11-29"))
cal["is_exam_week"] = cal.is_exam_week.astype(int)
fest = pd.to_datetime(["2025-10-15", "2025-10-16", "2025-10-17"])
holiday = pd.to_datetime(["2025-10-02", "2025-10-20", "2025-11-05"])
cal["is_fest"] = cal.date.isin(fest).astype(int)
cal["is_holiday"] = cal.date.isin(holiday).astype(int)
cal = cal[cal.is_holiday == 0].reset_index(drop=True)
cal["date_id"] = cal.date.dt.strftime("%Y%m%d").astype(int)

# --------------------------------------------------------- footfall rules
def day_factor(r):
    f = 1.0
    if r.dow == 5: f *= 0.55            # Saturday
    if r.is_exam_week: f *= 0.80        # R1
    if r.is_fest: f *= 1.55
    return f
cal["footfall_factor"] = cal.apply(day_factor, axis=1)

def item_weather_mult(name, temp_c, rainy):
    m = 1.0
    hot_snack = {"Tea","Coffee","Pakora","Veg Maggi","Samosa","Veg Momos"}
    cold = {"Cold Drink","Ice Cream","Lassi","Cold Coffee","Fruit Salad"}
    if name in hot_snack:
        if rainy: m *= 1.55
        if temp_c < 24: m *= 1.25
        if temp_c > 33: m *= 0.8
    if name in cold:
        if temp_c > 33: m *= 1.7
        elif temp_c > 29: m *= 1.2
        if rainy or temp_c < 22: m *= 0.55
    return m

SLOT_SHARE = {"breakfast": 0.17, "lunch": 0.33, "snacks": 0.30, "dinner": 0.20}
HOSTEL_SLOT = {"breakfast": 1.25, "lunch": 0.85, "snacks": 0.95, "dinner": 1.45}
SCHOLAR_SLOT = {"breakfast": 0.55, "lunch": 1.3, "snacks": 1.2, "dinner": 0.15}

# R6 combo rules: if first picked, add second with probability p
COMBOS = [("Samosa","Tea",0.55), ("Pakora","Tea",0.45), ("Veg Burger","Cold Drink",0.55),
          ("French Fries","Cold Drink",0.50), ("Veg Maggi","Coffee",0.30),
          ("Chole Bhature","Lassi",0.45), ("Veg Thali","Gulab Jamun",0.22),
          ("Chicken Biryani","Cold Drink",0.40), ("Paneer Wrap","Cold Coffee",0.30),
          ("Poha","Tea",0.50), ("Aloo Paratha","Lassi",0.35), ("Idli Sambar","Coffee",0.40),
          ("Veg Momos","Cold Drink",0.35), ("Sandwich","Coffee",0.35)]

# --------------------------------------------------------- sales lines
slot_items = {s: menu[menu.slots.apply(lambda x: s in x)] for s in SLOT_SHARE}
seg_cache = {}
def seg_pref(seg, slot, student_veg):
    key = (seg, slot, student_veg)
    if key in seg_cache: return seg_cache[key]
    cfg = SEGMENTS[seg]; df = slot_items[slot]
    w = df.base_pop.values.astype(float).copy()
    w *= df.category.map(lambda c: cfg["cats"].get(c, 1.0)).values
    if "healthy" in cfg: w *= np.where(df.is_healthy == 1, cfg["healthy"], 0.6)
    if "cheap" in cfg:   w *= np.where(df.price <= 30, cfg["cheap"], 0.6)
    if student_veg:      w *= np.where(df.is_veg == 1, 1.0, 0.05)
    p = w / w.sum(); seg_cache[key] = (df.item_id.values, p, df.name.values)
    return seg_cache[key]

lines, tid = [], 0
stu = students.to_dict("records")
for d in cal.itertuples():
    for slot, share in SLOT_SHARE.items():
        for s in stu:
            slot_w = (HOSTEL_SLOT if s["residence"] == "Hostel" else SCHOLAR_SLOT)[slot]
            p_visit = s["visit_freq"] * d.footfall_factor * slot_w * share * 2.2
            if rng.random() > min(p_visit, 0.95): continue
            ids, p, names = seg_pref(s["segment_true"], slot, s["is_veg_pref"])
            # weather adjustment on top of preference
            wm = np.array([item_weather_mult(n, d.temp_c, d.is_rainy) for n in names])
            pp = p * wm; pp /= pp.sum()
            tid += 1
            basket = {int(rng.choice(ids, p=pp)): 1}
            if rng.random() < 0.35:
                basket[int(rng.choice(ids, p=pp))] = 1
            for a, b, prob in COMBOS:
                if ITEM[a] in basket and rng.random() < prob:
                    if b in set(names): basket[ITEM[b]] = 1
            # budget constraint: drop priciest extras if over 1.6x budget
            tot = sum(menu.price[i - 1] for i in basket)
            while tot > s["avg_budget"] * 1.6 and len(basket) > 1:
                drop = max(basket, key=lambda i: menu.price[i - 1]); basket.pop(drop)
                tot = sum(menu.price[i - 1] for i in basket)
            for i in basket:
                q = 1 + (rng.random() < 0.12)
                lines.append((tid, d.date_id, slot, s["student_id"], i, int(q), int(menu.price[i - 1])))

sales = pd.DataFrame(lines, columns=["transaction_id","date_id","meal_slot","student_id","item_id","quantity","unit_price"])
sales["amount"] = sales.quantity * sales.unit_price

# ---------------------------------------------- prep / waste / inventory
daily = sales.groupby(["date_id", "item_id"]).quantity.sum().unstack(fill_value=0)
daily = daily.reindex(index=cal.date_id, columns=menu.item_id, fill_value=0)
rows_w, rows_i = [], []
hist = daily.rolling(7, min_periods=1).mean().shift(1).bfill()
for d in cal.itertuples():
    for it in menu.itertuples():
        sold = int(daily.at[d.date_id, it.item_id])
        if sold == 0 and it.base_pop < 0.7: pass
        est = hist.at[d.date_id, it.item_id]
        prepared = max(int(round(est * 1.25 + rng.normal(0, 0.12 * max(est, 3)))), sold if rng.random() < 0.35 else 0)
        prepared = max(prepared, 1)
        unsold = max(prepared - sold, 0)
        reusable = 1 - it.perishability * 0.85            # R8
        wasted = int(round(unsold * (1 - reusable * 0.45)))
        wasted = min(wasted, unsold)
        shortage = max(sold - prepared, 0)  # demand beyond prep (lost sales proxy)
        rows_w.append((d.date_id, it.item_id, prepared, min(sold, prepared), wasted,
                       round(wasted * it.unit_cost, 2), shortage))
        recv = prepared + int(rng.integers(0, 4))
        rows_i.append((d.date_id, it.item_id, 0, recv, prepared, 0))
waste = pd.DataFrame(rows_w, columns=["date_id","item_id","qty_prepared","qty_sold","qty_wasted","waste_cost","qty_shortage"])
waste["waste_pct"] = (waste.qty_wasted / waste.qty_prepared * 100).round(2)

inv = pd.DataFrame(rows_i, columns=["date_id","item_id","opening_stock","qty_received","qty_used","closing_stock"])
inv["closing_stock"] = inv.qty_received - inv.qty_used
inv["opening_stock"] = inv.groupby("item_id").closing_stock.shift(1).fillna(0).astype(int).clip(upper=6)
inv["closing_stock"] = inv.opening_stock + inv.qty_received - inv.qty_used

# ------------------------------------------------------------- export
OUT.mkdir(parents=True, exist_ok=True)
menu_out = menu.assign(slots="|".join([""])).drop(columns="slots")
menu_out["slots"] = ["|".join(x) for x in menu.slots]
menu_out.to_csv(OUT / "menu.csv", index=False)
students.to_csv(OUT / "students.csv", index=False)
cal.drop(columns=["footfall_factor"]).to_csv(OUT / "calendar.csv", index=False)
sales.to_csv(OUT / "sales.csv", index=False)
waste.to_csv(OUT / "waste.csv", index=False)
inv.to_csv(OUT / "inventory.csv", index=False)

print(f"days={len(cal)} students={len(students)} items={len(menu)}")
print(f"transactions={sales.transaction_id.nunique()} sales_lines={len(sales)} revenue=Rs{sales.amount.sum():,}")
print(f"overall waste% = {waste.qty_wasted.sum() / waste.qty_prepared.sum() * 100:.1f}  waste cost = Rs{waste.waste_cost.sum():,.0f}")
print("files written to", OUT)
