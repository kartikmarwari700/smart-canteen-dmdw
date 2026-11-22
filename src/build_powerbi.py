"""
Generates a Power BI Project (PBIP): semantic model (TMDL) + report (PBIR) from the pipeline outputs.
Open powerbi/CanteenDW.pbip in Power BI Desktop. Data = CSVs (path parameter `DataFolder`).
Re-run this script any time; then in Power BI click Refresh.
"""
import json, shutil, uuid
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
P, R = ROOT / "data/processed", ROOT / "reports"
OUT = ROOT / "powerbi"
DATA = Path.home() / "canteen_powerbi_data"      # local (non-OneDrive) copy of every CSV the report uses
if OUT.exists(): shutil.rmtree(OUT)
SM, RP = OUT / "CanteenDW.SemanticModel", OUT / "CanteenDW.Report"
(SM / "definition/tables").mkdir(parents=True); DATA.mkdir(parents=True, exist_ok=True)
(RP / "definition/pages").mkdir(parents=True)

# ------------------------------------------------------------------ sources
SOURCES = {  # table name -> csv path
    "dim_date": P / "dim_date.csv", "dim_meal_slot": P / "dim_meal_slot.csv", "dim_category": P / "dim_category.csv",
    "dim_cuisine": P / "dim_cuisine.csv", "dim_item": P / "dim_item.csv", "dim_student": P / "dim_student.csv",
    "fact_sales": P / "fact_sales.csv", "fact_waste": P / "fact_waste.csv", "fact_inventory": P / "fact_inventory.csv",
    "association_rules": R / "association_rules.csv", "cluster_profiles": R / "student_cluster_profiles.csv",
    "recommendations": R / "recommendations_testperiod.csv",
    "fact_real_canteen_waste": P / "fact_real_canteen_waste.csv", "fact_kitchen_waste": P / "fact_kitchen_waste.csv", "waste_anomalies": R / "daily_waste_anomalies.csv",
}
for n, f in SOURCES.items(): shutil.copy(f, DATA / f"{n}.csv")

BOOL = {"special_event", "is_outlier", "is_weekend", "is_exam_week", "is_fest", "is_rainy", "is_veg", "is_healthy", "is_veg_pref", "anomaly"}
DATE = {"full_date"}
STRING_FORCE = {"segment_true", "segment_mined", "name"}

def col_type(name, s):
    if name in BOOL and pd.api.types.is_bool_dtype(s): return "boolean", "type logical"
    if name in DATE: return "dateTime", "type date"
    if pd.api.types.is_integer_dtype(s): return "int64", "Int64.Type"
    if pd.api.types.is_float_dtype(s): return "double", "type number"
    return "string", "type text"

SORT_BY = {("dim_date", "month_name"): "month", ("dim_date", "day_name"): "day_of_week", ("dim_meal_slot", "slot_name"): "slot_id"}
HIDE = {"date_id", "item_id", "student_id", "slot_id", "category_id", "cuisine_id", "sales_key", "transaction_id"}

# ------------------------------------------------------------------ measures
MEASURES = {
    "fact_sales": [
        ("Revenue", "SUM(fact_sales[amount])", "#,0"),
        ("Units Sold", "SUM(fact_sales[quantity])", "#,0"),
        ("Transactions", "DISTINCTCOUNT(fact_sales[transaction_id])", "#,0"),
        ("Avg Basket Value", "DIVIDE([Revenue], [Transactions])", "#,0.00"),
        ("Revenue Share %", "DIVIDE([Revenue], CALCULATE([Revenue], ALLSELECTED()))", "0.0%"),
    ],
    "fact_waste": [
        ("Qty Prepared", "SUM(fact_waste[qty_prepared])", "#,0"),
        ("Qty Sold", "SUM(fact_waste[qty_sold])", "#,0"),
        ("Qty Wasted", "SUM(fact_waste[qty_wasted])", "#,0"),
        ("Qty Shortage", "SUM(fact_waste[qty_shortage])", "#,0"),
        ("Waste Cost", "SUM(fact_waste[waste_cost])", "#,0"),
        ("Waste %", "DIVIDE([Qty Wasted], [Qty Prepared])", "0.0%"),
    ],
    "fact_real_canteen_waste": [
        ("Real Waste (kg)", "SUM(fact_real_canteen_waste[waste_kg])", "#,0"),
        ("Real Cost Loss (Rs)", "SUM(fact_real_canteen_waste[cost_loss])", "#,0"),
        ("Avg Waste per Record (kg)", "AVERAGE(fact_real_canteen_waste[waste_kg])", "0.00"),
    ],
    "fact_kitchen_waste": [
        ("Avg Kitchen Waste (kg)", "AVERAGE(fact_kitchen_waste[food_waste_kg])", "0.0"),
        ("Avg Meals Served", "AVERAGE(fact_kitchen_waste[meals_served])", "#,0"),
        ("Kitchen Records", "COUNTROWS(fact_kitchen_waste)", "#,0"),
        ("Outlier Records", "CALCULATE(COUNTROWS(fact_kitchen_waste), fact_kitchen_waste[is_outlier] = TRUE())", "#,0"),
    ],
    "recommendations": [
        ("Actual Waste (test days)", "SUM(recommendations[qty_wasted])", "#,0"),
        ("Simulated Waste (model prep)", "SUMX(recommendations, MAX(recommendations[recommended_prep] - recommendations[qty_sold], 0))", "#,0"),
        ("Waste Reduction %", "DIVIDE([Actual Waste (test days)] - [Simulated Waste (model prep)], [Actual Waste (test days)])", "0.0%"),
        ("Actual Prep", "SUM(recommendations[qty_prepared])", "#,0"),
        ("Recommended Prep", "SUM(recommendations[recommended_prep])", "#,0"),
    ],
}

# ------------------------------------------------------------------ TMDL
def uid(): return str(uuid.uuid4())
(SM / "definition.pbism").write_text(json.dumps({
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
    "version": "4.2", "settings": {}}, indent=2))
(SM / "definition/database.tmdl").write_text("database CanteenDW\n\tcompatibilityLevel: 1600\n")
tables = list(SOURCES)
model = "model Model\n\tculture: en-US\n\tdefaultPowerBIDataSourceVersion: powerBI_V3\n\tdiscourageImplicitMeasures\n\n"
model += "".join(f"ref table {t}\n" for t in tables)
(SM / "definition/model.tmdl").write_text(model)
for t, f in SOURCES.items():
    df = pd.read_csv(f)
    lines = [f"table {t}", f"\tlineageTag: {uid()}"]
    if t == "dim_date": lines.append("\tdataCategory: Time")
    for ms, expr, fmt in MEASURES.get(t, []):
        lines += [f"\tmeasure '{ms}' = {expr}", f"\t\tformatString: {fmt}", f"\t\tlineageTag: {uid()}", ""]
    typed = []
    for c in df.columns:
        dt, mt = col_type(c, df[c]); typed.append((c, mt))
        lines += [f"\tcolumn '{c}'", f"\t\tdataType: {dt}", f"\t\tlineageTag: {uid()}",
                  "\t\tsummarizeBy: none" if (c in HIDE or dt in ("string", "boolean", "dateTime") or c.endswith("_id")) else "\t\tsummarizeBy: sum"]
        if c in HIDE: lines.append("\t\tisHidden")
        if t == "dim_date" and c == "full_date": lines += ["\t\tisKey", "\t\tformatString: Long Date"]
        if (t, c) in SORT_BY: lines.append(f"\t\tsortByColumn: {SORT_BY[(t, c)]}")
        lines += [f"\t\tsourceColumn: {c}", ""]
    types = ", ".join(f'{{"{c}", {m}}}' for c, m in typed)
    lines += [f"\tpartition {t} = m", "\t\tmode: import", "\t\tsource =", "\t\t\tlet",
              f'\t\t\t\t{t}_raw = Csv.Document(File.Contents("' + str(DATA / (t + ".csv")) + '"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),',
              f"\t\t\t\t{t}_hdr = Table.PromoteHeaders({t}_raw, [PromoteAllScalars=true]),",
              f'\t\t\t\t{t}_typed = Table.TransformColumnTypes({t}_hdr, {{{types}}}, "en-US")',
              "\t\t\tin", f"\t\t\t\t{t}_typed", ""]
    (SM / f"definition/tables/{t}.tmdl").write_text("\n".join(lines), encoding="utf-8")

REL = [("fact_sales", "date_id", "dim_date", "date_id"), ("fact_sales", "slot_id", "dim_meal_slot", "slot_id"),
       ("fact_sales", "student_id", "dim_student", "student_id"), ("fact_sales", "item_id", "dim_item", "item_id"),
       ("fact_waste", "date_id", "dim_date", "date_id"), ("fact_waste", "item_id", "dim_item", "item_id"),
       ("fact_inventory", "date_id", "dim_date", "date_id"), ("fact_inventory", "item_id", "dim_item", "item_id"),
       ("dim_item", "category_id", "dim_category", "category_id"), ("dim_item", "cuisine_id", "dim_cuisine", "cuisine_id"),
       ("recommendations", "date_id", "dim_date", "date_id"), ("recommendations", "item_id", "dim_item", "item_id"),
       ("waste_anomalies", "date_id", "dim_date", "date_id"),
       ("fact_real_canteen_waste", "date_id", "dim_date", "date_id"), ("fact_kitchen_waste", "date_id", "dim_date", "date_id")]
rel = []
for a, ac, b, bc in REL:
    rel += [f"relationship {uid()}", f"\tfromColumn: {a}.{ac}", f"\ttoColumn: {b}.{bc}", ""]
(SM / "definition/relationships.tmdl").write_text("\n".join(rel))

# ------------------------------------------------------------------ report (PBIR)
SCH = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
(OUT / "CanteenDW.pbip").write_text(json.dumps({
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
    "version": "1.0", "artifacts": [{"report": {"path": "CanteenDW.Report"}}], "settings": {"enableAutoRecovery": True}}, indent=2))
(RP / "definition.pbir").write_text(json.dumps({
    "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
    "version": "4.0", "datasetReference": {"byPath": {"path": "../CanteenDW.SemanticModel"}}}, indent=2))
(RP / "definition/version.json").write_text(json.dumps({"$schema": f"{SCH}/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}))
(RP / "definition/report.json").write_text(json.dumps({
    "$schema": f"{SCH}/report/3.0.0/schema.json",
    "themeCollection": {"baseTheme": {"name": "CY24SU10", "reportVersionAtImport": {"visual": "2.0.0", "report": "3.0.0", "page": "2.0.0"}, "type": "SharedResources"}}}, indent=2))

def _src(e): return {"Expression": {"SourceRef": {"Entity": e}}}
def C(e, p): return {"field": {"Column": {**_src(e), "Property": p}}, "queryRef": f"{e}.{p}", "nativeQueryRef": p}
def M(e, p): return {"field": {"Measure": {**_src(e), "Property": p}}, "queryRef": f"{e}.{p}", "nativeQueryRef": p}
lit = lambda s: {"expr": {"Literal": {"Value": f"'{s}'"}}}

class Page:
    def __init__(self, pid, title): self.id, self.title, self.v = pid, title, []
    def add(self, vtype, x, y, w, h, title=None, **roles):
        name = f"{self.id}_v{len(self.v) + 1}"
        qs = {role: {"projections": fields} for role, fields in roles.items()}
        vis = {"visualType": vtype, "query": {"queryState": qs}, "drillFilterOtherVisuals": True}
        if title: vis["visualContainerObjects"] = {"title": [{"properties": {"text": lit(title), "show": {"expr": {"Literal": {"Value": "true"}}}}}]}
        self.v.append({"$schema": f"{SCH}/visualContainer/2.0.0/schema.json", "name": name,
                       "position": {"x": x, "y": y, "width": w, "height": h, "z": len(self.v) * 1000, "tabOrder": len(self.v) * 1000},
                       "visual": vis})

pages = []
# 1 Overview
p = Page("p1", "Overview"); pages.append(p)
for i, (m, t) in enumerate([("Revenue", "Revenue (Rs)"), ("Transactions", "Transactions"), ("Waste %", "Waste %"), ("Waste Cost", "Waste Cost (Rs)")]):
    ent = "fact_waste" if m.startswith("Waste") else "fact_sales"
    p.add("card", 20 + i * 260, 20, 245, 95, t, Values=[M(ent, m)])
p.add("lineChart", 20, 130, 780, 300, "Daily demand vs waste (units)", Category=[C("dim_date", "full_date")], Y=[M("fact_waste", "Qty Sold"), M("fact_waste", "Qty Wasted")])
p.add("columnChart", 20, 440, 520, 260, "Waste % by weekday", Category=[C("dim_date", "day_name")], Y=[M("fact_waste", "Waste %")])
p.add("columnChart", 550, 440, 250, 260, "Revenue by month", Category=[C("dim_date", "month_name")], Y=[M("fact_sales", "Revenue")])
p.add("slicer", 820, 20, 440, 140, "Month", Values=[C("dim_date", "month_name")])
p.add("slicer", 820, 170, 440, 140, "Category", Values=[C("dim_category", "category_name")])
p.add("donutChart", 820, 320, 440, 380, "Revenue by meal slot", Category=[C("dim_meal_slot", "slot_name")], Y=[M("fact_sales", "Revenue")])
# 2 OLAP
p = Page("p2", "OLAP Explorer"); pages.append(p)
p.add("slicer", 20, 20, 300, 130, "Month (slice)", Values=[C("dim_date", "month_name")])
p.add("slicer", 330, 20, 300, 130, "Meal slot (dice)", Values=[C("dim_meal_slot", "slot_name")])
p.add("slicer", 640, 20, 300, 130, "Category (dice)", Values=[C("dim_category", "category_name")])
p.add("slicer", 950, 20, 310, 130, "Rainy day (slice)", Values=[C("dim_date", "is_rainy")])
p.add("pivotTable", 20, 165, 760, 535, "Pivot: category > item (drill) x meal slot",
      Rows=[C("dim_category", "category_name"), C("dim_item", "item_name")], Columns=[C("dim_meal_slot", "slot_name")], Values=[M("fact_sales", "Revenue")])
p.add("clusteredBarChart", 790, 165, 470, 535, "Revenue by item", Category=[C("dim_item", "item_name")], Y=[M("fact_sales", "Revenue")])
# 3 Waste
p = Page("p3", "Waste Analysis"); pages.append(p)
p.add("card", 20, 20, 240, 90, "Waste Cost (Rs)", Values=[M("fact_waste", "Waste Cost")])
p.add("card", 270, 20, 240, 90, "Units Wasted", Values=[M("fact_waste", "Qty Wasted")])
p.add("card", 520, 20, 240, 90, "Units Short (lost demand)", Values=[M("fact_waste", "Qty Shortage")])
p.add("card", 770, 20, 240, 90, "Waste %", Values=[M("fact_waste", "Waste %")])
p.add("clusteredBarChart", 20, 125, 620, 575, "Waste cost by item", Category=[C("dim_item", "item_name")], Y=[M("fact_waste", "Waste Cost")])
p.add("columnChart", 650, 125, 610, 280, "Waste % by category", Category=[C("dim_category", "category_name")], Y=[M("fact_waste", "Waste %")])
p.add("columnChart", 650, 415, 610, 285, "Waste % by weekday (Saturday spike)", Category=[C("dim_date", "day_name")], Y=[M("fact_waste", "Waste %")])
# 4 Association rules
p = Page("p4", "Association Rules"); pages.append(p)
p.add("tableEx", 20, 20, 700, 680, "Rules (support / confidence / lift)",
      Values=[C("association_rules", "antecedents"), C("association_rules", "consequents"), C("association_rules", "support"), C("association_rules", "confidence"), C("association_rules", "lift")])
p.add("scatterChart", 730, 20, 530, 680, "Support vs confidence (size = lift)",
      Category=[C("association_rules", "antecedents")], X=[C("association_rules", "support")], Y=[C("association_rules", "confidence")], Size=[C("association_rules", "lift")])
# 5 Segments
p = Page("p5", "Student Segments"); pages.append(p)
p.add("donutChart", 20, 20, 400, 330, "Students by segment", Category=[C("dim_student", "segment_mined")], Y=[C("dim_student", "student_id")])
p.add("clusteredBarChart", 430, 20, 420, 330, "Revenue by segment", Category=[C("dim_student", "segment_mined")], Y=[M("fact_sales", "Revenue")])
p.add("clusteredBarChart", 860, 20, 400, 330, "Avg basket value by segment", Category=[C("dim_student", "segment_mined")], Y=[M("fact_sales", "Avg Basket Value")])
p.add("tableEx", 20, 360, 1240, 340, "Cluster profiles (category spend share, ticket, healthy share)",
      Values=[C("cluster_profiles", c) for c in pd.read_csv(R / "student_cluster_profiles.csv").columns])
# 6 Simulator
p = Page("p6", "Waste-Saving Simulator"); pages.append(p)
p.add("card", 20, 20, 300, 100, "Actual waste (units, test days)", Values=[M("recommendations", "Actual Waste (test days)")])
p.add("card", 330, 20, 300, 100, "Waste with model-based prep", Values=[M("recommendations", "Simulated Waste (model prep)")])
p.add("card", 640, 20, 300, 100, "Waste reduction %", Values=[M("recommendations", "Waste Reduction %")])
p.add("slicer", 950, 20, 310, 100, "Category", Values=[C("dim_category", "category_name")])
p.add("clusteredBarChart", 20, 135, 620, 565, "Actual vs recommended prep by item", Category=[C("dim_item", "item_name")], Y=[M("recommendations", "Actual Prep"), M("recommendations", "Recommended Prep")])
p.add("tableEx", 650, 135, 610, 565, "Daily prep recommendation (use date slicer on Overview to filter)",
      Values=[C("dim_date", "full_date"), C("recommendations", "name"), C("recommendations", "qty_prepared"), C("recommendations", "recommended_prep"), C("recommendations", "qty_sold")])
# 7 Anomalies
p = Page("p7", "Anomalies"); pages.append(p)
p.add("columnChart", 20, 20, 1240, 350, "Daily waste cost (flagged = anomaly)", Category=[C("dim_date", "full_date")], Y=[C("waste_anomalies", "waste_cost")])
p.add("tableEx", 20, 380, 1240, 320, "Flagged anomaly days",
      Values=[C("dim_date", "full_date"), C("dim_date", "day_name"), C("waste_anomalies", "waste_units"), C("waste_anomalies", "waste_cost"), C("waste_anomalies", "anomaly")])

# 8 Real data
p = Page("p8", "Real Data (Kaggle)"); pages.append(p)
p.add("card", 20, 20, 240, 90, "Real waste (kg) - canteen", Values=[M("fact_real_canteen_waste", "Real Waste (kg)")])
p.add("card", 270, 20, 240, 90, "Cost loss (Rs)", Values=[M("fact_real_canteen_waste", "Real Cost Loss (Rs)")])
p.add("card", 520, 20, 240, 90, "Avg kitchen waste (kg)", Values=[M("fact_kitchen_waste", "Avg Kitchen Waste (kg)")])
p.add("card", 770, 20, 240, 90, "Outlier records flagged", Values=[M("fact_kitchen_waste", "Outlier Records")])
p.add("columnChart", 20, 125, 400, 280, "Waste (kg) by food category", Category=[C("fact_real_canteen_waste", "food_category")], Y=[M("fact_real_canteen_waste", "Real Waste (kg)")])
p.add("columnChart", 430, 125, 400, 280, "Cost loss by food category", Category=[C("fact_real_canteen_waste", "food_category")], Y=[M("fact_real_canteen_waste", "Real Cost Loss (Rs)")])
p.add("columnChart", 840, 125, 420, 280, "Avg waste per record by meal", Category=[C("fact_real_canteen_waste", "meal")], Y=[M("fact_real_canteen_waste", "Avg Waste per Record (kg)")])
p.add("scatterChart", 20, 415, 620, 285, "Messy dataset: waste vs meals served", Category=[C("fact_kitchen_waste", "record_id")], X=[C("fact_kitchen_waste", "meals_served")], Y=[C("fact_kitchen_waste", "food_waste_kg")])
p.add("clusteredBarChart", 650, 415, 300, 285, "Avg waste by food type", Category=[C("fact_kitchen_waste", "waste_category")], Y=[M("fact_kitchen_waste", "Avg Kitchen Waste (kg)")])
p.add("clusteredBarChart", 960, 415, 300, 285, "Avg waste by special event", Category=[C("fact_kitchen_waste", "special_event")], Y=[M("fact_kitchen_waste", "Avg Kitchen Waste (kg)")])

for pg in pages:
    d = RP / f"definition/pages/{pg.id}"; (d / "visuals").mkdir(parents=True)
    (d / "page.json").write_text(json.dumps({"$schema": f"{SCH}/page/2.0.0/schema.json", "name": pg.id,
                                             "displayName": pg.title, "displayOption": "FitToPage", "height": 720, "width": 1280}, indent=2))
    for v in pg.v:
        vd = d / "visuals" / v["name"]; vd.mkdir()
        (vd / "visual.json").write_text(json.dumps(v, indent=2))
(RP / "definition/pages/pages.json").write_text(json.dumps({
    "$schema": f"{SCH}/pagesMetadata/1.0.0/schema.json", "pageOrder": [p.id for p in pages], "activePageName": "p1"}, indent=2))
print("built", OUT / "CanteenDW.pbip", "pages:", len(pages), "visuals:", sum(len(p.v) for p in pages))
