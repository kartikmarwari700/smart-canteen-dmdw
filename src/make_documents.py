"""Builds Final Report (DOCX), Presentation (PPTX) and Improved Synopsis (DOCX) from real pipeline numbers."""
from pathlib import Path
import json
import pandas as pd
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from pptx import Presentation
from pptx.util import Inches as PI, Pt as PP
from pptx.dml.color import RGBColor as PC

ROOT = Path(__file__).resolve().parents[1]
R, P, FIG = ROOT / "reports", ROOT / "data/processed", ROOT / "reports/figures"
OUTD = ROOT / "documents"; OUTD.mkdir(exist_ok=True)
res = json.loads((R / "mining_results.json").read_text())

# ---------------------------------------------------------------- numbers
sales, waste = pd.read_csv(P / "fact_sales.csv"), pd.read_csv(P / "fact_waste.csv")
N = dict(
    revenue=sales.amount.sum(), txn=sales.transaction_id.nunique(), lines=len(sales),
    days=waste.date_id.nunique(), items=waste.item_id.nunique(), students=pd.read_csv(P / "dim_student.csv").shape[0],
    waste_pct=100 * waste.qty_wasted.sum() / waste.qty_prepared.sum(), waste_cost=waste.waste_cost.sum())
wd = pd.read_csv(R / "olap_q7_waste_by_weekday.csv").set_index("day_name").waste_pct
dm, wm, cl, sm, asoc = res["demand_prediction"], res["waste_prediction"], res["clustering"], res["simulator"], res["association"]
clf = res["classification"]
real = json.loads((R / "real_data_results.json").read_text())
rc, rm, rmod = real["canteen"], real["messy"], real["messy_models"]
rules = pd.read_csv(R / "association_rules.csv").head(6)
profiles = pd.read_csv(R / "student_cluster_profiles.csv")
TEAM = [("Ishita Arora", "2401030253"), ("Priyani Rajvanshi", "2401030256"), ("Kartik Marwari", "2401030279")]
TITLE = "Smart Campus Canteen Data Warehouse for Food Demand, Preference and Waste Prediction"

# ================================================================ DOCX helpers
def new_doc():
    d = Document()
    for s in d.sections: s.left_margin = s.right_margin = Inches(1); s.top_margin = s.bottom_margin = Inches(0.9)
    st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)
    for lvl, sz in ((1, 16), (2, 13)):
        h = d.styles[f"Heading {lvl}"]; h.font.name = "Calibri"; h.font.size = Pt(sz); h.font.color.rgb = RGBColor(0x1F, 0x4E, 0x43)
    return d

def para(d, text, bold=False, italic=False, align=None, size=None):
    p = d.add_paragraph(); r = p.add_run(text); r.bold, r.italic = bold, italic
    if size: r.font.size = Pt(size)
    if align: p.alignment = align
    return p

def bullets(d, items):
    for i in items: d.add_paragraph(i, style="List Bullet")

def table(d, header, rows, widths=None):
    t = d.add_table(rows=1, cols=len(header)); t.style = "Light Grid Accent 1"
    for i, h in enumerate(header):
        t.rows[0].cells[i].text = ""; r = t.rows[0].cells[i].paragraphs[0].add_run(str(h)); r.bold = True
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row): cells[i].text = str(v)
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                for r in p.runs: r.font.size = Pt(9.5)
    d.add_paragraph()
    return t

def fig(d, name, caption, w=5.8):
    d.add_picture(str(FIG / name), width=Inches(w)); d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    para(d, caption, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=9.5)

def cover(d, subtitle):
    para(d, "JAYPEE INSTITUTE OF INFORMATION TECHNOLOGY, NOIDA", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=14)
    para(d, "5th Semester (Odd) | Data Mining and Data Warehousing Lab (26B16CS313)", align=WD_ALIGN_PARAGRAPH.CENTER)
    d.add_paragraph()
    para(d, subtitle.upper(), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=16)
    para(d, TITLE, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=15)
    d.add_paragraph()
    para(d, "Submitted to: Ms. Sayani Ghosal, Ms. Diksha Pandey", align=WD_ALIGN_PARAGRAPH.CENTER)
    para(d, "Team members:", bold=True, align=WD_ALIGN_PARAGRAPH.CENTER)
    for n, e in TEAM: para(d, f"{n} ({e})", align=WD_ALIGN_PARAGRAPH.CENTER)
    d.add_page_break()

# ================================================================ FINAL REPORT
d = new_doc(); cover(d, "Project Report")
d.add_heading("1. Abstract", 1)
para(d, f"College canteens collect sales, preference and wastage data but rarely use it for decisions. This project builds a Smart Canteen Data Warehouse that integrates "
        f"sales, menu, student, inventory and food-waste data and applies data mining to forecast demand, understand preferences and reduce waste. "
        f"A hybrid data approach is used: two real Kaggle food-waste datasets (analysed and loaded as warehouse facts) are combined with rule-based synthetic supporting data. The warehouse uses a Fact Constellation "
        f"schema with a Snowflake item hierarchy and supports OLAP. Mining covers association rules, classification, clustering, prediction and anomaly detection. "
        f"On held-out days, model-based preparation reduced simulated waste cost by {sm['waste_cost_reduction_pct']}% compared with the current practice (under the generator's assumptions).")
d.add_heading("2. Problem Statement and Objectives", 1)
para(d, "Canteens estimate preparation manually, causing excess food, shortages, unknown preferences and unused history. Objectives:")
bullets(d, ["Integrate sales, waste, preference and menu data (hybrid real + synthetic).", "Clean, transform and load data into a centralised warehouse.",
            "Design Star, Snowflake and Fact Constellation schemas and run OLAP operations.", "Find purchase patterns (association rules) and segment students (clustering).",
            "Classify waste levels and predict demand and waste; evaluate with proper metrics.", "Produce recommendations for preparation, inventory and waste reduction."])
d.add_heading("3. Data and Hybrid Approach", 1)
para(d, "Real data sources: (a) Food Waste Dataset from a University Canteen (Kaggle) and (b) Messy Food Waste Prediction Dataset (Kaggle). "
        "Both were downloaded and analysed (Section 6A). They do not contain students, sales baskets, menus or inventory, so supporting data is generated synthetically and kept in a separate folder (data/synthetic).")
para(d, "The generator is rule-driven, not random. Documented business rules: weekends, exam weeks and fest days change footfall; rain and cold raise tea/pakora/maggi demand; "
        "heat raises cold drinks/ice cream; hostel students eat more breakfast/dinner, day scholars more lunch/snacks; students belong to latent preference segments; "
        "combo rules (samosa+tea, burger+cold drink, chole bhature+lassi); the canteen prepares with a naive rule (7-day average x 1.25 + noise); perishable items waste more.")
table(d, ["Item", "Value"], [["Days simulated", N["days"]], ["Students", N["students"]], ["Menu items", N["items"]], ["Transactions", f"{N['txn']:,}"],
                              ["Sales lines", f"{N['lines']:,}"], ["Revenue (Rs)", f"{N['revenue']:,.0f}"], ["Overall waste %", f"{N['waste_pct']:.1f}%"], ["Waste cost (Rs)", f"{N['waste_cost']:,.0f}"]])
para(d, "Note: Sections 7-9 (OLAP, mining, simulator) are computed on the synthetic canteen data. Section 6A reports results on the real Kaggle data.", italic=True)
d.add_heading("4. System Architecture", 1)
para(d, "CSV / synthetic data -> Python ETL (pandas) -> warehouse tables (PostgreSQL schema canteen_dw or CSV) -> OLAP + mining (scikit-learn, mlxtend) -> Power BI dashboard (also a Streamlit version).")
d.add_heading("5. ETL and Preprocessing", 1)
bullets(d, ["Extract: six source tables (menu, students, calendar, sales, waste, inventory).", "Clean: remove duplicates and nulls, drop non-positive quantities/prices, clip negative waste.",
            "Integrity: assert every sales row maps to a valid item, student and date (no orphan keys).", "Transform: build dimensions with date hierarchy (day, week, month, quarter) and item hierarchy (item, category, cuisine).",
            "Features: lag-1, lag-7, 7-day moving averages for demand and waste per item.", "Load: nine warehouse tables to data/processed and optionally to PostgreSQL."])
d.add_heading("6. Data Warehouse Design", 1)
fig(d, "schema_galaxy.png", "Figure 1: Fact Constellation schema with Snowflake item hierarchy", 6.2)
bullets(d, ["Star: fact_sales joined to dim_date, dim_student, dim_meal_slot and a denormalised item view (star_dim_item).", "Snowflake: dim_item -> dim_category and dim_cuisine (normalised hierarchy).",
            "Fact Constellation: fact_sales, fact_waste and fact_inventory share the conformed dimensions dim_date and dim_item; this is why a galaxy schema is natural here."])
d.add_heading("6A. Real Kaggle Data: Profiling, Cleaning and Analysis", 1)
para(d, "Two real datasets were integrated into the warehouse as additional fact tables (fact_real_canteen_waste, fact_kitchen_waste) that share the conformed dim_date. "
        "Together with the three synthetic-data facts this gives a five-fact constellation.")
d.add_heading("Dataset A: Food Waste Dataset from a University Canteen", 2)
para(d, f"{rc['rows']:,} records over {rc['days']} days ({rc['date_from']} to {rc['date_to']}), columns: date, meal, canteen section, food category, waste weight (kg), unit price per kg, cost loss. "
        f"No missing values or duplicates; Cost_Loss = weight x price was verified for every row. Total waste {rc['total_kg']:,.0f} kg, cost loss Rs {rc['total_loss']:,.0f}, average {rc['avg_kg']} kg per record.")
table(d, ["Food category", "Records", "Total kg", "Price/kg", "Total loss (Rs)"], [[r["food_category"], r["records"], f"{r['total_kg']:,.0f}", r["price_per_kg"], f"{r['total_loss']:,.0f}"] for r in rc["by_category"]])
fig(d, "real_canteen_category.png", "Figure R1: Real canteen waste by food category", 6.0)
para(d, f"Finding: waste weight is almost the same across categories, meals and sections (one-way ANOVA p-values: category {rc['anova_food_category_p']}, meal {rc['anova_meal_p']}, section {rc['anova_section_p']}). "
        "Only the meal effect is statistically significant, and it is small. The real cost driver is price: Meat is about 4x costlier per kg, so it causes the largest cost loss "
        f"(Rs {max(x['total_loss'] for x in rc['by_category']):,.0f}) despite similar weight. Implication: reduce meat over-preparation first.")
d.add_heading("Dataset B: Messy Food Waste Prediction Dataset", 2)
para(d, f"train.csv has {rm['rows']} records (meals served, kitchen staff, temperature, humidity, day of week, special event, past waste, staff experience, waste category, food waste kg). "
        "Data-quality problems found and fixed:")
bullets(d, [f"{rm['category_variants_raw']} spellings for 4 food types (MEAT / MeAt, GRAINS ...): standardised to {', '.join(rm['category_clean'])}.",
            f"staff_experience had {rm['missing_raw']} missing values and mixed case (Intermediate / intermediate / EXPERT): normalised; missing labelled 'unknown' (not guessed).",
            f"Outliers: {rm['outliers_meals']} implausible meals_served values (max {rm['max_meals']:,}) and {rm['outliers_temp']} temperature values (max {rm['max_temp']} C), flagged by the 1.5 x IQR rule; {rm['outliers_any']} rows flagged and kept in the warehouse with is_outlier = true.",
            "test.csv has features identical to train.csv (all 911 IDs overlap) and submission.csv repeats train's target, so there is no independent test set; we use train.csv only with 5-fold cross-validation."])
res_rows = [[n, v["MAE"], v["R2"], rmod["all_rows"][n]["R2"]] for n, v in rmod["outliers_removed"].items() if n != "n"]
table(d, ["Model (5-fold CV)", "MAE (outliers removed)", "R2 (outliers removed)", "R2 (all rows)"], res_rows)
fig(d, "real_messy_model.png", "Figure R2: Waste vs meals served (outliers in red) and feature importance", 6.0)
para(d, f"Findings: Linear Regression reaches R2 = {rmod['outliers_removed']['Linear Regression']['R2']} (MAE {rmod['outliers_removed']['Linear Regression']['MAE']} kg) after outlier handling, versus R2 close to 0 for the mean baseline. "
        f"Waste is strongly tied to meals served (correlation {rm['corr_with_waste']['meals_served']} on raw data, inflated by outliers) and to past waste ({rm['corr_with_waste']['past_waste_kg']}). "
        f"Special-event days produce about {rm['waste_by_event']['1']/rm['waste_by_event']['0']:.1f}x the waste of normal days ({rm['waste_by_event']['1']} vs {rm['waste_by_event']['0']} kg). "
        "Temperature, humidity, staff count and weekday have almost no effect. With outliers retained, tree models score higher (R2 about 0.9) only because the extreme rows dominate the variance, which is why cleaning matters.")
d.add_heading("7. OLAP Analysis", 1)
para(d, "Ten OLAP queries (sql/olap_queries.sql, pandas equivalent in src/olap.py) implement roll-up, drill-down, slice, dice and pivot.")
table(d, ["Operation", "Example"], [["Roll-up", "Revenue by month -> quarter"], ["Drill-down", "Category -> item revenue"], ["Slice", "Top items on rainy days"],
                                    ["Dice", "Weekday lunch/dinner for Meals and Fast Food"], ["Pivot", "Category x meal slot revenue"]])
fig(d, "olap_pivot.png", "Figure 2: Pivot of revenue by category and meal slot")
fig(d, "waste_weekday.png", f"Figure 3: Waste % by weekday. Saturday waste is {wd['Saturday']:.1f}% vs {wd['Monday']:.1f}-{wd[['Tuesday','Wednesday','Thursday','Friday']].max():.1f}% on other days")
fig(d, "top_wasted.png", "Figure 4: Items with the highest waste cost")
d.add_heading("8. Data Mining Results", 1)
d.add_heading("8.1 Association rule mining", 2)
para(d, f"Apriori and FP-Growth were run on {asoc['n_baskets']:,} baskets (min support {asoc['min_support']}). Both found {asoc['itemsets_apriori']} frequent itemsets; "
        f"Apriori {asoc['apriori_sec']}s vs FP-Growth {asoc['fpgrowth_sec']}s (the dataset is small, so the difference is not significant). {asoc['n_rules']} rules passed lift >= 1.2 and confidence >= 0.2.")
table(d, ["Antecedent", "Consequent", "Support", "Confidence", "Lift"], [[r.antecedents, r.consequents, f"{r.support:.3f}", f"{r.confidence:.2f}", f"{r.lift:.2f}"] for r in rules.itertuples()])
para(d, "These recover the combo rules planted in the generator (e.g. samosa+tea, burger+cold drink), which validates the mining pipeline.")
d.add_heading("8.2 Clustering of students", 2)
para(d, f"K-Means with k=5 on category-spend shares, visit count, average ticket and healthy share (standardised). Silhouette at k=5 is {cl['silhouette_at_k']}; "
        f"silhouette is highest at k=2 ({cl['silhouette_by_k']['2']}) but five clusters are more interpretable and match the five preference segments used for evaluation. "
        f"Agreement with the hidden ground-truth segments: Adjusted Rand Index = {cl['ARI_vs_true_segments']}.")
fig(d, "clustering_k.png", "Figure 5: Elbow and silhouette analysis", 5.6)
table(d, ["Cluster", "Label", "Size", "Avg ticket (Rs)", "Healthy share"], [[r.cluster, r.label, r.size, f"{r.avg_ticket:.1f}", f"{r.healthy:.2f}"] for r in profiles.itertuples()])
d.add_heading("8.3 Classification of waste level", 2)
para(d, f"Waste % was binned into Low/Medium/High using training-set terciles ({clf['thresholds'][0]}% and {clf['thresholds'][1]}%). Time-based split: first 80% of days for training, last 20% for testing.")
table(d, ["Model", "Accuracy", "F1 (macro)"], [[m, clf[m]["accuracy"], clf[m]["f1_macro"]] for m in ["Decision Tree", "Random Forest", "Naive Bayes"]])
para(d, "Performance is moderate. Waste depends strongly on random preparation error, which no model can foresee, so exact level prediction is inherently hard. Random Forest is best. This is reported as a limitation, not hidden.")
d.add_heading("8.4 Demand and waste prediction", 2)
table(d, ["Model", "MAE", "RMSE", "R2"], [[m, v["MAE"], v["RMSE"], v["R2"]] for m, v in dm.items()])
fig(d, "demand_models.png", "Figure 6: Demand prediction error (lower is better)")
para(d, f"Random Forest predicts daily item demand with R2 = {dm['Random Forest']['R2']} and cuts MAE from {dm['Baseline (7-day avg)']['MAE']} (7-day average baseline) to {dm['Random Forest']['MAE']}. "
        f"Waste-% regression is weaker (best R2 = {max(v['R2'] for v in wm.values())}) for the same reason as classification.")
d.add_heading("8.5 Anomaly detection", 2)
para(d, f"Isolation Forest on daily waste/sales flagged {res['anomaly']['n_flagged']} unusual days (5% contamination), useful for alerting kitchen managers.")
fig(d, "anomalies.png", "Figure 7: Daily waste cost with flagged anomalies", 5.8)
d.add_heading("9. Recommendations and Waste-Saving Simulator", 1)
para(d, f"For the {sm['test_days']} held-out days, preparation was set to ceil(predicted demand x buffer) and compared with the canteen's actual preparation.")
rows = [["Actual (current)", f"{sm['actual']['waste_units']:.0f}", f"{sm['actual']['waste_cost']:,.0f}", f"{sm['actual']['lost_sales_rs']:,.0f}"]]
rows += [[f"Model x{b}", f"{v['waste_units']:.0f}", f"{v['waste_cost']:,.0f}", f"{v['lost_sales_rs']:,.0f}"] for b, v in sm["by_buffer"].items()]
table(d, ["Policy", "Waste units", "Waste cost (Rs)", "Lost sales (Rs)"], rows)
fig(d, "simulator.png", "Figure 8: Waste cost under actual vs model-based preparation")
para(d, f"Best trade-off (waste cost + 50% of lost sales margin) is buffer x{sm['best_buffer']}: waste cost falls by {sm['waste_cost_reduction_pct']}% and waste units by {sm['waste_units_reduction_pct']}%. "
        "Actionable outputs: (1) prepare quantity = predicted demand; (2) reduce Saturday preparation; (3) stock tea/pakora/maggi on rainy days and cold drinks on hot days; "
        "(4) place high-lift pairs together (Lassi+Chole Bhature, Burger+Cold Drink); (5) review Veg Thali and Rajma Chawal preparation, the top waste-cost items.")
d.add_heading("10. Power BI Dashboard", 1)
para(d, "An eight-page Power BI report (powerbi/CanteenDW.pbip) is built on the warehouse tables with DAX measures (Revenue, Waste %, Waste Cost, Avg Basket Value, Waste Reduction %). "
        "Pages: Overview, OLAP Explorer (slicers + category-to-item drill-down matrix), Waste Analysis, Association Rules, Student Segments, Waste-Saving Simulator, Anomalies, Real Data (Kaggle). "
        "[Insert Power BI screenshots here.]")
d.add_heading("11. Limitations", 1)
bullets(d, ["Sales, student, menu and inventory data are synthetic, so Sections 7-9 show that the pipeline works, not real-world canteen performance.", "The real datasets are small and weakly structured (university canteen: near-uniform waste; messy: no independent test set).", "The simulator's savings depend on the generator's assumptions about prep error and spoilage.",
            "Waste-level prediction is only moderately accurate because waste is driven by random prep error.", "Only about 100 days of data; seasonal effects beyond one semester are not captured."])
d.add_heading("12. Conclusion and Future Work", 1)
para(d, "The project demonstrates the full Data Warehousing and Data Mining lifecycle: integration, ETL, galaxy-schema warehouse, OLAP, five mining techniques, evaluation and a decision-support dashboard. "
        "Future work: replace synthetic tables with real canteen POS data, add weather API and academic-calendar features, deploy a daily preparation recommendation, and track real waste reduction.")
d.add_heading("References", 1)
bullets(d, ["Han, Kamber, Pei. Data Mining: Concepts and Techniques. Morgan Kaufmann.", "Kimball, Ross. The Data Warehouse Toolkit. Wiley.",
            "Kaggle: Food Waste Dataset from a University Canteen; Messy Food Waste Prediction Dataset.", "scikit-learn and mlxtend documentation."])
d.save(OUTD / "Final_Report_Smart_Canteen_DMDW.docx")

# ================================================================ IMPROVED SYNOPSIS
s = new_doc(); cover(s, "Synopsis (Revised)")
s.add_heading("1. Abstract", 1)
para(s, "Canteen data on sales, preferences, preparation, inventory and wastage is scattered and rarely used. This project integrates it in a Smart Canteen Data Warehouse and applies "
        "data mining to forecast demand, discover purchase patterns, segment students and reduce food waste, using a hybrid of real Kaggle waste datasets and documented rule-based synthetic data.")
s.add_heading("2. Problem Statement", 1)
bullets(s, ["Manual estimation causes excess food and shortages.", "Popular and unpopular items are not systematically identified.", "Sales, inventory and wastage are not analysed together.", "Recurring buying patterns and student preferences are unknown."])
s.add_heading("3. Objectives and Measurable Targets", 1)
table(s, ["Objective", "Success measure"], [
    ["Integrated warehouse (Galaxy + Snowflake + Star)", "3 fact tables, 6 dimensions, 10 OLAP queries"], ["Demand forecasting", "Beat 7-day-average baseline on MAE (time-based split)"],
    ["Waste level classification", "Compare DT / RF / NB by accuracy and macro-F1"], ["Student segmentation", "K-Means with silhouette and ARI vs ground truth"],
    ["Purchase patterns", "Apriori vs FP-Growth; rules by support, confidence, lift"], ["Waste reduction", "Simulated waste cost reduction on held-out days (target >= 20%)"]])
s.add_heading("4. Data Sources and Hybrid Strategy", 1)
bullets(s, ["Real: Food Waste Dataset from a University Canteen (Kaggle); Messy Food Waste Prediction Dataset (Kaggle).",
            "Synthetic (clearly separated): students, menu, sales baskets, inventory, calendar/weather/events.",
            "Synthetic data follows documented business rules (footfall, weather, exam/fest, meal-slot behaviour, combo purchases, naive prep rule, perishability) so mined patterns can be validated against known ground truth."])
s.add_heading("5. Methodology", 1)
bullets(s, ["Data collection and integration -> cleaning and preprocessing -> ETL -> warehouse (PostgreSQL).", "OLAP: roll-up, drill-down, slice, dice, pivot.",
            "Mining: association rules, classification, clustering, regression, anomaly detection; evaluation with MAE, RMSE, R2, accuracy, F1, silhouette.",
            "Decision support: waste-saving simulator and Power BI dashboard."])
s.add_heading("6. Tools", 1)
para(s, "Python (pandas, scikit-learn, mlxtend), PostgreSQL, Power BI Desktop, Streamlit.")
s.add_heading("7. Expected Outcomes", 1)
bullets(s, ["Working warehouse with galaxy schema and OLAP queries.", "Demand and waste models with documented evaluation.", "Interactive dashboard and actionable preparation recommendations."])
s.add_heading("8. Timeline", 1)
table(s, ["Week", "Task"], [["1", "Data collection, synthetic generator, profiling"], ["2", "ETL and warehouse schema"], ["3", "OLAP queries"], ["4", "Mining models and evaluation"], ["5", "Dashboard, simulator, report"]])
s.save(OUTD / "Improved_Synopsis_Smart_Canteen_DMDW.docx")

# ================================================================ PPTX
prs = Presentation(); prs.slide_width, prs.slide_height = PI(13.333), PI(7.5)
GREEN, DARK, GREY = PC(0x1F, 0x4E, 0x43), PC(0x22, 0x22, 0x22), PC(0x66, 0x66, 0x66)

def slide(title, bullets_=None, img=None, img_w=6.2, notes=None, sub=None):
    sl = prs.slides.add_slide(prs.slide_layouts[6])
    bar = sl.shapes.add_shape(1, 0, 0, prs.slide_width, PI(1.0)); bar.fill.solid(); bar.fill.fore_color.rgb = GREEN; bar.line.fill.background()
    tb = sl.shapes.add_textbox(PI(0.5), PI(0.18), PI(12), PI(0.7)).text_frame; tb.text = title
    tb.paragraphs[0].font.size, tb.paragraphs[0].font.bold, tb.paragraphs[0].font.color.rgb = PP(30), True, PC(255, 255, 255)
    left_w = 6.3 if img else 12.2
    if bullets_:
        tf = sl.shapes.add_textbox(PI(0.6), PI(1.5), PI(left_w), PI(5.4)).text_frame; tf.word_wrap = True
        for i, b in enumerate(bullets_):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = "• " + b; p.font.size = PP(26); p.font.color.rgb = DARK; p.space_after = PP(16)
    if img: sl.shapes.add_picture(str(FIG / img), PI(7.0), PI(1.5), width=PI(img_w))
    if sub:
        t2 = sl.shapes.add_textbox(PI(0.6), PI(6.85), PI(12), PI(0.4)).text_frame; t2.text = sub; t2.paragraphs[0].font.size = PP(12); t2.paragraphs[0].font.color.rgb = GREY
    return sl

s0 = prs.slides.add_slide(prs.slide_layouts[6])
bg = s0.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height); bg.fill.solid(); bg.fill.fore_color.rgb = GREEN; bg.line.fill.background()
t = s0.shapes.add_textbox(PI(0.8), PI(2.0), PI(11.7), PI(3.5)).text_frame; t.word_wrap = True
t.text = "Smart Canteen Data Warehouse"; t.paragraphs[0].font.size, t.paragraphs[0].font.bold, t.paragraphs[0].font.color.rgb = PP(46), True, PC(255, 255, 255)
for line, sz in [("Food Demand, Preference and Waste Prediction", 26), ("Data Mining and Data Warehousing Lab (26B16CS313) | JIIT Noida", 16),
                 ("  |  ".join(f"{n} ({e})" for n, e in TEAM), 14)]:
    p = t.add_paragraph(); p.text = line; p.font.size = PP(sz); p.font.color.rgb = PC(0xDD, 0xEE, 0xE8)

slide("Problem", ["Canteens decide preparation by manual estimation", f"Result: {N['waste_pct']:.0f}% of prepared food wasted (Rs {N['waste_cost']/1000:,.0f}k in our data)",
                  "Shortages of high-demand items", "Preferences and buying patterns unknown", "Sales, inventory and waste never analysed together"])
slide("Hybrid data approach", ["Real: two Kaggle datasets, cleaned and loaded as facts", "Synthetic (separate folder): students, menu, sales, inventory, weather, events",
                               "Rule-driven, not random: weather, exam/fest, meal slot, combos, perishability", "Hidden ground truth lets us validate the mining",
                               f"{N['txn']:,} transactions, {N['students']} students, {N['items']} items, {N['days']} days"])
slide("Real data: university canteen", [f"{rc['rows']:,} records, {rc['total_kg']:,.0f} kg wasted", "Weight similar across categories", "Meat costs ~4x per kg", f"Meat loss Rs {max(x['total_loss'] for x in rc['by_category']):,.0f}: top cost driver", "Plan: cut meat over-preparation first"], "real_canteen_category.png", 6.0)
slide("Real data: messy dataset", [f"{rm['rows']} rows, {rm['missing_raw']} missing, 5 spellings for 4 food types", f"{rm['outliers_any']} outliers flagged (meals up to {rm['max_meals']:,})", "test.csv equals train.csv: 5-fold CV only", f"Linear Regression R2 = {rmod['outliers_removed']['Linear Regression']['R2']}", f"Special events: ~{rm['waste_by_event']['1']/rm['waste_by_event']['0']:.1f}x waste"], "real_messy_model.png", 6.0)
slide("Warehouse: Galaxy schema", ["3 fact tables: sales, waste, inventory", "Shared conformed dimensions: date, item", "Snowflake: item → category → cuisine", "Star view for sales analysis"], "schema_galaxy.png", 6.1)
slide("ETL pipeline", ["Extract six sources", "Clean: duplicates, nulls, invalid values", "Integrity checks: no orphan keys", "Transform: date and item hierarchies, lag features", "Load: 9 tables (PostgreSQL / CSV)"])
slide("OLAP insights", ["Roll-up, drill-down, slice, dice, pivot (10 queries)", f"Saturday waste {wd['Saturday']:.0f}% vs ~{wd[['Tuesday','Wednesday','Thursday','Friday']].mean():.0f}% on weekdays",
                        "Meals earn the most revenue at lunch", "Fest days earn about 1.7x a normal day"], "waste_weekday.png")
slide("Association rules", [f"Apriori vs FP-Growth on {asoc['n_baskets']:,} baskets", "Chole Bhature ↔ Lassi: lift 6.1", "Idli Sambar → Coffee: lift 4.3", "Veg Burger → Cold Drink: lift 3.6", "Samosa ↔ Tea: lift 3.2",
                            "Recovers planted combos: pipeline validated"])
slide("Student segmentation", [f"K-Means, k=5, ARI vs truth = {cl['ARI_vs_true_segments']}", "Snack Lover, Health Conscious, Meal Regular, Budget Saver, Foodie", f"Silhouette {cl['silhouette_at_k']} at k=5 (interpretability over k=2)"], "segments.png", 5.4)
slide("Demand prediction", [f"Random Forest R2 = {dm['Random Forest']['R2']}", f"MAE {dm['Baseline (7-day avg)']['MAE']} → {dm['Random Forest']['MAE']} vs 7-day baseline", "Time-based split (no leakage)", "Compared Linear, RF, Gradient Boosting"], "demand_models.png")
slide("Waste classification", [f"Low / Medium / High waste", f"Random Forest: accuracy {clf['Random Forest']['accuracy']}, F1 {clf['Random Forest']['f1_macro']}", f"Decision Tree {clf['Decision Tree']['accuracy']}, Naive Bayes {clf['Naive Bayes']['accuracy']}",
                               "Moderate: waste driven by random prep error (honest limitation)"])
slide("Waste-saving simulator", [f"Model-based prep on {sm['test_days']} held-out days", f"Waste cost down {sm['waste_cost_reduction_pct']}%", f"Waste units down {sm['waste_units_reduction_pct']}%", "Under generator assumptions, not a field measurement"], "simulator.png")
slide("Recommendations", ["Prepare predicted demand, not last week's average", "Cut Saturday preparation", "Rainy day: stock tea, pakora, maggi; hot day: cold drinks", "Bundle Lassi + Chole Bhature, Burger + Cold Drink", "Review Veg Thali and Rajma Chawal quantities"])
slide("Power BI dashboard", ["8 pages: Overview, OLAP, Waste, Rules, Segments, Simulator, Anomalies, Real Data", "DAX measures: Revenue, Waste %, Waste Cost, Waste Reduction %", "Slicers for month, slot, category, weather", "[Insert dashboard screenshots]"])
slide("Limitations and future work", ["Supporting data is synthetic", "Savings depend on generator assumptions", "Real POS data, weather API and academic calendar next", "Deploy daily prep recommendation and track real savings"])
slide("Thank you", ["Questions?"])
prs.save(OUTD / "Presentation_Smart_Canteen_DMDW.pptx")
print("saved:", sorted(p.name for p in OUTD.iterdir()))
