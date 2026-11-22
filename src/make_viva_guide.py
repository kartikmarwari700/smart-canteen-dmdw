"""Builds documents/Viva_and_Demo_Guide.docx (Hinglish) with numbers pulled from the real results."""
from pathlib import Path
import json
import pandas as pd
from docx import Document
from docx.shared import Pt, Inches, RGBColor

ROOT = Path(__file__).resolve().parents[1]
R, P = ROOT / "reports", ROOT / "data/processed"
res = json.loads((R / "mining_results.json").read_text())
real = json.loads((R / "real_data_results.json").read_text())
sales, waste = pd.read_csv(P / "fact_sales.csv"), pd.read_csv(P / "fact_waste.csv")
wd = pd.read_csv(R / "olap_q7_waste_by_weekday.csv").set_index("day_name").waste_pct
dm, clf, cl, sm, asoc = res["demand_prediction"], res["classification"], res["clustering"], res["simulator"], res["association"]
rc, rm, rmod = real["canteen"], real["messy"], real["messy_models"]
N = dict(txn=sales.transaction_id.nunique(), lines=len(sales), rev=sales.amount.sum(),
         wpct=100 * waste.qty_wasted.sum() / waste.qty_prepared.sum(), wcost=waste.waste_cost.sum())
rf_r2, rf_mae, base_mae = dm["Random Forest"]["R2"], dm["Random Forest"]["MAE"], dm["Baseline (7-day avg)"]["MAE"]
lr_real = rmod["outliers_removed"]["Linear Regression"]

d = Document()
for s in d.sections: s.left_margin = s.right_margin = Inches(0.9); s.top_margin = s.bottom_margin = Inches(0.8)
d.styles["Normal"].font.name = "Calibri"; d.styles["Normal"].font.size = Pt(11)
for lvl, sz in ((1, 17), (2, 13.5), (3, 12)):
    h = d.styles[f"Heading {lvl}"]; h.font.name = "Calibri"; h.font.size = Pt(sz); h.font.color.rgb = RGBColor(0x1F, 0x4E, 0x43)

def H(t, l=1): d.add_heading(t, l)
def Pg(t, b=False, i=False):
    p = d.add_paragraph(); r = p.add_run(t); r.bold, r.italic = b, i; return p
def B(items):
    for x in items: d.add_paragraph(x, style="List Bullet")
def Nn(items):
    for x in items: d.add_paragraph(x, style="List Number")
def code(t):
    p = d.add_paragraph(); r = p.add_run(t); r.font.name = "Consolas"; r.font.size = Pt(10); p.paragraph_format.left_indent = Inches(0.3)
def QA(q, a):
    p = d.add_paragraph(); r = p.add_run("Q. " + q); r.bold = True
    d.add_paragraph("A. " + a).paragraph_format.left_indent = Inches(0.25)

d.add_heading("Smart Canteen DW: Demo aur Viva Guide", 0)
Pg("Is guide me 4 cheezein hain: (1) kal demo se pehle ki taiyari, (2) demo ka step-by-step script, (3) har concept mam ko kaise samjhana hai, (4) viva ke sawaal-jawab.", i=True)

# ====================================================================== PART 1
H("Part 1: Demo se pehle taiyari (aaj raat hi kar lo)")
H("1.1 Laptop par kya kya hona chahiye", 2)
B(["Project folder: Desktop\\smart_canteen_dmdw (poora folder pendrive/Drive par bhi backup rakho).",
   "Power BI Desktop (installed hai) aur Python 3.11 (installed hai).",
   "PostgreSQL optional hai. Demo bina uske chalta hai, isliye uski tension mat lo.",
   "Report, PPT aur synopsis: documents folder me."])
H("1.2 Ek baar poora pipeline chalake dekh lo (50 second lagte hain)", 2)
Pg("PowerShell kholo, project folder me jao aur ye chalao:")
code("cd C:\\Users\\karti\\OneDrive\\Desktop\\smart_canteen_dmdw\n.\\run_all.ps1")
Pg("Ye 5 kaam karta hai: data generate -> real Kaggle data clean -> ETL (warehouse tables) -> OLAP -> mining models. Aakhir me 'Done' likhta hai. Numbers har baar same aate hain (seed fixed hai), isliye report ke numbers kabhi nahi badlenge.")
H("1.3 Power BI kholne ka sahi tarika (ZAROORI)", 2)
Nn(["Folder powerbi me CanteenDW.pbip par double-click karo.",
    "Agar charts me data dikhe to kuch mat karo. Bas File > Save.",
    "Agar charts khali hon (Blank dikhe), to Refresh button MAT dabao. Refresh dabane se 'cyclic reference' error aata hai (Power BI ka parallel loading glitch).",
    "Iski jagah PowerShell me ye chalao (Power BI khula rehna chahiye):"])
code("cd C:\\Users\\karti\\OneDrive\\Desktop\\smart_canteen_dmdw\n.\\powerbi_refresh.ps1")
Pg("Ye saari tables ek-ek karke load karta hai. Phir File > Save karo.")
H("1.4 Backup plan (agar Power BI hang ho jaye)", 2)
code("py -3.11 -m streamlit run app/dashboard.py")
Pg("Browser me wahi dashboard khulta hai (7 pages). Demo ke pehle ek baar dono chalake dekh lo.")
H("1.5 Demo se pehle 5-minute checklist", 2)
B(["Power BI file khuli hai aur 8 pages me data dikh raha hai.", "Streamlit backup ek baar chalake dekha.", "Report, PPT, synopsis files khulne wali jagah par hain.",
   "Laptop charge/charger saath, internet ki zaroorat nahi hai.", "README.md ek baar padh lo, usme pipeline ka poora flow likha hai."])

# ====================================================================== PART 2
H("Part 2: Demo script (10-12 minute)")
Pg("Mam ko ye order me dikhao. Har step me 'kya dikhana hai' aur 'kya bolna hai' diya hai.", i=True)
H("Step 1: Problem (1 min)", 2)
Pg("Bolo: 'Mam, college canteens manually decide karte hain ki kitna khana banana hai. Isse ya to khana waste hota hai ya kam padta hai. Hamare data me waste lagbhag %.0f%% hai aur uski cost Rs %s hai. Hamne ek data warehouse banaya jo sales, waste aur preferences ko jodta hai, aur data mining se demand predict karta hai.'" % (N["wpct"], f"{N['wcost']:,.0f}"))
H("Step 2: Data (1.5 min)", 2)
Pg("Dikhao: data folder. Bolo: 'Humne hybrid approach li. Real data: 2 Kaggle datasets. Synthetic data: students, menu, sales aur inventory, kyunki Kaggle me ye available nahi tha. Synthetic data random nahi hai, usme rules hain (barish me chai zyada, exam week me kam bheed, samosa ke saath chai).'")
B(["data\\raw: real Kaggle files", "data\\synthetic: generate_data.py ka output", "src\\generate_data.py ke upar rules (R1 se R8) likhe hain, wahi dikha do."])
H("Step 3: ETL (1 min)", 2)
Pg("Dikhao: src\\etl.py aur reports\\etl_log.txt. Bolo: 'Ye cleaning karta hai (duplicates, nulls, invalid values), integrity check karta hai ki koi orphan key na ho, dimensions banata hai aur 11 warehouse tables save karta hai.'")
H("Step 4: Warehouse schema (1.5 min)", 2)
Pg("Dikhao: report ya PPT me schema diagram (reports\\figures\\schema_galaxy.png) ya Power BI me Model view (left side ka 3rd icon).")
B(["3 fact tables (sales, waste, inventory) + 2 real facts: ye Fact Constellation (Galaxy) hai kyunki facts same dimensions share karte hain.",
   "Item -> Category -> Cuisine: ye Snowflake hai (normalised hierarchy).",
   "Sales ko dim_date, dim_student, dim_meal_slot, dim_item se jodna: ye Star hai."])
H("Step 5: Power BI dashboard (4 min), page by page", 2)
Nn(["Overview: KPI cards (revenue, waste %%, waste cost). Bolo: 'Total revenue Rs %s, waste %.1f%%.' Month slicer dabake dikhao ki sab charts filter hote hain." % (f"{N['rev']:,.0f}", N["wpct"]),
    "OLAP Explorer: yahan OLAP hai. Matrix me category par click karke item level tak drill-down karo (+ ya expand icon). Slicers = slice/dice. Matrix me rows=category, columns=meal slot = pivot.",
    "Waste Analysis: 'Saturday ko waste %.0f%% hai jabki baaki din 10 se 13%%. Matlab canteen weekday pattern ignore karta hai.' Top wasted item: Veg Thali." % wd["Saturday"],
    "Association Rules: 'Chole Bhature aur Lassi ka lift 6.1 hai, yani log inhe saath khareedte hain.'",
    "Student Segments: 5 segments (Snack Lover, Health Conscious, Meal Regular, Budget Saver, Foodie).",
    "Waste-Saving Simulator: 'Model ke hisaab se prepare karne par test dino me waste cost %s%% kam hoti.'" % sm["waste_cost_reduction_pct"],
    "Anomalies: Isolation Forest ne unusual waste days flag kiye.",
    "Real Data (Kaggle): real data ke results. 'Meat sabse zyada cost loss deta hai kyunki uska price/kg 4 guna hai.'"])
H("Step 6: Mining code ek baar dikhao (1.5 min)", 2)
Pg("src\\mining.py kholo. Sirf section headings dikhao (1 Association rules, 2 Classification, 3 Clustering, 4 Prediction, 5 Simulator, 6 Anomaly). Results reports\\mining_results.json me hain.")
H("Step 7: Limitations (1 min, ye bahut zaroori hai)", 2)
Pg("Khud bolo (mam poochhe usse pehle): 'Sales data synthetic hai, isliye 66%% saving real-world proof nahi hai, ye model ki potential dikhata hai. Waste classification sirf %s%% accurate hai kyunki waste random prep error par depend karta hai.' Ye honesty achha impression deti hai." % round(100 * clf["Random Forest"]["accuracy"]))

# ====================================================================== PART 3
H("Part 3: Har concept mam ko kaise samjhana hai")
H("3.1 Data Warehouse kya hai aur humne kyun banaya", 2)
Pg("Warehouse ek central database hai jahan alag-alag source ka data clean karke jodte hain, taaki analysis aasan ho. Canteen me sales, waste aur inventory alag jagah hote hain. Warehouse me inhe jodke hum sawaal pooch sakte hain: 'Kis din kaunsa item kitna bika aur kitna waste hua?'")
H("3.2 Star, Snowflake aur Galaxy ka fark", 2)
table = d.add_table(rows=1, cols=3); table.style = "Light Grid Accent 1"
for i, h in enumerate(["Schema", "Kya hai", "Humare project me"]): table.rows[0].cells[i].text = h
for row in [("Star", "Ek fact table, charo taraf denormalised dimensions", "fact_sales + date, student, slot, item (star_dim_item view)"),
            ("Snowflake", "Dimension ko aur tables me normalise karna", "dim_item -> dim_category aur dim_cuisine"),
            ("Galaxy / Fact Constellation", "Kai fact tables, shared dimensions", "fact_sales, fact_waste, fact_inventory (+2 real) share dim_date aur dim_item")]:
    c = table.add_row().cells
    for i, v in enumerate(row): c[i].text = v
d.add_paragraph()
H("3.2b Fact aur dimension", 2)
Pg("Fact table me numbers (measures) hote hain jo hum jodte hain: quantity, amount, waste. Dimension table me describing cheezein hoti hain: date, item, student. Fact table dimensions ko foreign key se jodta hai.")
H("3.3 ETL", 2)
Pg("Extract (files se data lena), Transform (clean, validate, dimensions banana, lag features), Load (warehouse tables me save). Humne duplicates hataye, invalid values filter kiye, aur assert se check kiya ki sales me koi item/student/date aisa na ho jo dimension me na ho.")
H("3.4 OLAP operations (Power BI me dikhane ke liye)", 2)
table = d.add_table(rows=1, cols=3); table.style = "Light Grid Accent 1"
for i, h in enumerate(["Operation", "Matlab", "Dashboard me kahan"]): table.rows[0].cells[i].text = h
for row in [("Roll-up", "Detail se summary: item -> category -> total", "OLAP page matrix collapse karo"),
            ("Drill-down", "Summary se detail: category -> item", "OLAP page matrix expand karo"),
            ("Slice", "Ek dimension ek value par filter", "Rainy day slicer"),
            ("Dice", "Kai dimensions par filter", "Month + slot + category slicers saath"),
            ("Pivot", "Rows aur columns badalna", "Category x meal slot matrix")]:
    c = table.add_row().cells
    for i, v in enumerate(row): c[i].text = v
d.add_paragraph()
Pg("SQL versions: sql\\olap_queries.sql me 10 queries hain (ROLLUP, FILTER, window RANK).")
H("3.5 Data mining techniques", 2)
B(["Association rules: 'jo log A khareedte hain wo B bhi khareedte hain'. Support = kitni baar saath aaye, confidence = A ke baad B ki probability, lift = random se kitna zyada (lift > 1 matlab sach me relation hai). Humne Apriori aur FP-Growth dono chalaye; FP-Growth tree se kaam karta hai, bade data par tez hota hai.",
   "Classification: waste ko Low/Medium/High me baantna. Decision Tree, Random Forest, Naive Bayes compare kiye.",
   "Clustering: bina labels ke students ke group banana (K-Means). 5 groups mile.",
   "Regression / prediction: kal kitna bikega ya kitna waste hoga, ek number predict karna.",
   "Anomaly detection: Isolation Forest unusual waste days pakadta hai."])
H("3.6 Evaluation metrics, seedhe shabdon me", 2)
B(["MAE: average galti kitni units. Chhota achha.", "RMSE: MAE jaisa, par badi galtiyon ko zyada penalty.", "R2: 1 ke paas matlab model data ko achhe se samajhta hai, 0 matlab bekaar (average se bhi kharab).",
   "Accuracy / F1: classification me kitne sahi. F1 imbalance me zyada bharosemand.", "Silhouette: cluster kitne alag hain (-1 se 1).", "ARI (Adjusted Rand Index): clustering asli groups se kitni match karti hai (1 = perfect)."])

# ====================================================================== PART 4
H("Part 4: Viva ke sawaal aur jawab")
H("A. Project overview", 2)
QA("Project ka main idea kya hai?", "Canteen ka sales, waste, preference aur inventory data ek data warehouse me jodke, data mining se demand aur waste predict karna, taaki canteen sahi quantity me khana banaye aur waste kam ho.")
QA("Is project ka real-world faida kya hai?", f"Over-preparation se paisa aur khana barbaad hota hai, under-preparation se customer chhoot jate hain. Hamare model se simulation me test dino ka waste cost {sm['waste_cost_reduction_pct']}% kam hui. Ye synthetic assumptions par hai, par direction dikhata hai.")
QA("Aapne kya khud banaya aur kya ready-made use kiya?", "Pipeline (generator, ETL, schema, OLAP, mining, dashboard) humne banaya. Libraries (pandas, scikit-learn, mlxtend) standard tools hain. Real data Kaggle se liya.")
H("B. Data aur synthetic data (sabse zyada poochha jaane wala)", 2)
QA("Synthetic data kyun use kiya? Kya ye fake nahi hai?", "Kaggle ke real datasets me sirf waste ka data tha, students, sales baskets, menu aur inventory nahi tha. Real canteen ka POS data private hota hai. Isliye hybrid approach li: real data + rule-based synthetic data. Hum clearly alag rakhte hain (data\\synthetic) aur report me bata dete hain ki synthetic hai. Is project ka maksad DW aur DM techniques demonstrate karna hai.")
QA("Synthetic data random hai ya rules se?", "Rules se. 8 documented rules hain: weekend/exam/fest footfall, barish aur garmi ka item demand par asar, hostel vs day-scholar meal timing, student preference segments, combo purchases, canteen ki naive prep rule (7-din avg x 1.25), aur perishability. Isse mined patterns ko hum ground truth se verify kar sakte hain.")
QA("Agar data aapne hi banaya to model ka accuracy meaningful kaise hai?", "Honest jawab: synthetic data par accuracy ye dikhati hai ki pipeline sahi kaam karti hai (jaise association rules ne wahi combos pakde jo rules me daale the, clustering ne 5 hidden segments wapas pakde, ARI 0.82). Real-world performance prove karne ke liye real POS data chahiye, jo future work hai. Real Kaggle data par alag se results diye hain.")
QA("Real data kitna use hua?", f"Dono Kaggle datasets clean, analyse aur warehouse me facts ke roop me load hue: university canteen ({rc['rows']:,} records) aur messy dataset ({rm['rows']} records). Real data par alag models aur cleaning ke results Section 6A me hain.")
QA("Real datasets me kya problems mili?", f"Messy dataset me {rm['category_variants_raw']} spellings (MEAT/MeAt), {rm['missing_raw']} missing values, aur {rm['outliers_any']} outliers (meals_served {rm['max_meals']:,}, temperature {rm['max_temp']} C). Humne standardise kiya, missing ko 'unknown' rakha aur outliers flag kiye. Aur test.csv bilkul train.csv jaisa tha, isliye alag test set nahi mila.")
QA("test.csv aur train.csv same the to aapne evaluation kaise kiya?", "Sirf train.csv par 5-fold cross-validation kiya, taaki har data point test me ek baar aaye. test.csv use karte to data leakage hota.")
H("C. Warehouse aur ETL", 2)
QA("Fact Constellation kyun chuna?", "Kyunki humare paas teen alag business processes hain (sales, waste, inventory) jo date aur item dimensions share karte hain. Ek hi fact table me sab daalna sahi nahi hota kyunki granularity alag hai (sales line-level, waste date x item level).")
QA("Fact table ki granularity kya hai?", "fact_sales: ek transaction me ek item ki line. fact_waste aur fact_inventory: ek din x ek item.")
QA("Snowflake schema ka fayda aur nuksan?", "Fayda: kam redundancy, hierarchy saaf (item -> category -> cuisine). Nuksan: zyada joins, query thodi slow aur complex.")
QA("Star schema kab behtar hai?", "Jab query speed aur simplicity chahiye, kyunki joins kam hote hain. Isliye humne star_dim_item view bhi banaya.")
QA("ETL me aapne kya-kya kiya?", "Duplicates aur nulls hataye, invalid quantity/price filter kiye, negative waste clip kiya, foreign key integrity assert se check ki, dimensions banaye (date hierarchy, item hierarchy), lag features (lag-1, lag-7, 7-day moving average) banaye, aur 11 tables load kiye.")
QA("Surrogate key vs natural key?", "Humne date_id (yyyymmdd) aur item_id use kiye jo simple integer keys hain. Sales fact me sales_key surrogate key hai.")
QA("PostgreSQL ka kya role hai?", "Schema sql\\schema.sql me hai. Password dene par ETL data PostgreSQL me load kar deta hai. Demo me Power BI seedha CSV se chalta hai.")
H("D. OLAP", 2)
QA("OLAP aur OLTP me fark?", "OLTP daily transactions ke liye (insert/update, fast, normalised). OLAP analysis ke liye (read-heavy, aggregated, multidimensional). Humne OLAP kiya.")
QA("Roll-up aur drill-down ka example do.", "Roll-up: item revenue se category revenue, phir total. Drill-down: category se item level tak. Power BI OLAP page ke matrix me expand/collapse.")
QA("Slice aur dice me fark?", "Slice ek dimension ko ek value par filter karta hai (sirf rainy days). Dice kai dimensions par filter karta hai (weekday lunch aur dinner, Meals aur Fast Food).")
QA("Ek OLAP insight batao.", f"Saturday ko waste {wd['Saturday']:.0f}% hota hai jabki baaki din 10-13%. Fest din ki avg revenue normal din se lagbhag 1.7 guna.")
H("E. Association rules", 2)
QA("Support, confidence aur lift kya hain?", "Support: itemset kitni transactions me aaya. Confidence: A ke saath B aane ki probability. Lift = confidence / P(B). Lift > 1 matlab positive relation.")
QA("Aapke sabse strong rules?", "Chole Bhature <-> Lassi (lift 6.1), Idli Sambar -> Coffee (4.3), Veg Burger -> Cold Drink (3.6), Samosa <-> Tea (3.2).")
QA("Apriori aur FP-Growth me fark?", f"Apriori candidates generate karke baar-baar database scan karta hai. FP-Growth FP-tree banata hai, candidate generation nahi. Humare chhote data par dono ne {asoc['itemsets_apriori']} itemsets diye aur time me fark negligible tha ({asoc['apriori_sec']}s vs {asoc['fpgrowth_sec']}s). Bade data par FP-Growth tez hota.")
QA("Ye rules business ke liye kaise kaam aate hain?", "Combo offers, items ko paas rakhna aur ek item ki demand se dusre ki demand predict karna.")
H("F. Clustering", 2)
QA("K-Means kaise kaam karta hai?", "K centroid chunta hai, har point ko nearest centroid me daalta hai, centroid update karta hai, aur ye tab tak dohrata hai jab tak stable na ho.")
QA("k=5 kyun? Silhouette to k=2 par zyada hai.", f"Elbow aur silhouette dono dekhe. Silhouette k=2 par zyada ({cl['silhouette_by_k']['2']}) hai par sirf 2 groups business ke liye kam useful hain. Hamare 5 students segments business ke hisaab se interpretable hain, aur k=5 ne hidden segments ko achhe se pakda (ARI {cl['ARI_vs_true_segments']}). Ye trade-off report me likha hai.")
QA("ARI kya hai aur 0.82 ka matlab?", "Adjusted Rand Index clustering ko asli labels se compare karta hai. 1 matlab perfect match, 0 matlab random. 0.82 matlab clusters asli segments se bahut milte hain.")
QA("Features kaunse use kiye?", "Category-wise spend share, visit count, average ticket size, healthy-food share, sab standardised.")
H("G. Classification aur prediction", 2)
QA("Waste classification ka accuracy sirf 57% kyun?", f"Waste mostly canteen ki random prep error se aata hai, jo kisi model ko pehle se pata nahi ho sakti. Random Forest best hai (accuracy {clf['Random Forest']['accuracy']}, F1 {clf['Random Forest']['f1_macro']}); 3 classes me random guess 33% hota, isliye model random se behtar hai par bahut strong nahi. Ye hum limitation me honestly likhte hain.")
QA("Demand prediction kaisa raha?", f"Random Forest ka R2 {rf_r2} aur MAE {rf_mae} units; 7-din average baseline ka MAE {base_mae} tha. Yani model galti ko kaafi kam karta hai.")
QA("Train/test split time-based kyun?", "Future predict karna hai, isliye past par train aur baad ke dino par test. Random split karte to future ka data train me leak ho jata.")
QA("Overfitting kaise check kiya?", "Time-based holdout test set aur real data par 5-fold cross-validation. Models me max_depth limit rakhi.")
QA("Random Forest linear regression se kyun behtar hai?", "Random Forest non-linear relationships (weather, weekday, event interaction) pakad leta hai, aur kai trees ka average variance kam karta hai.")
QA("Feature importance me kya mila?", "Real data me past_waste_kg aur meals_served sabse important hain; temperature, humidity aur weekday ka asar lagbhag nahi mila.")
QA("Real data par model kaisa raha?", f"Messy dataset par outliers hatane ke baad Linear Regression R2 {lr_real['R2']}, MAE {lr_real['MAE']} kg (5-fold CV). Mean baseline ka R2 lagbhag 0 tha.")
QA("Outliers ko hatana sahi hai?", "Humne delete nahi kiya, flag kiya (is_outlier). Warehouse me rakhe, par modeling me alag evaluate kiya. Outliers ke saath tree models ka R2 ~0.9 dikhta hai, par wo sirf kuch extreme rows ki wajah se hai, isliye cleaning ke baad ka number zyada bharosemand hai.")
H("H. Simulator aur results", 2)
QA("66% waste reduction kaise nikla?", f"Test period ke {sm['test_days']} dino me hamare model ke predicted demand se prep quantity set ki (ceil(predicted x buffer)) aur canteen ki asli prep se compare kiya. Waste cost asli se {sm['waste_cost_reduction_pct']}% kam aayi.")
QA("Ye number real hai?", "Nahi, ye simulation hai aur generator ki assumptions par depend karta hai. Real canteen me iske liye pilot test chahiye. Report me bhi limitation me likha hai.")
QA("Buffer kya hai?", "Predicted demand par extra percent jo shortage se bachata hai. Humne 1.0 se 1.20 tak test kiya. Best trade-off waste cost aur lost sales ke beech 1.0 aaya.")
QA("Anomaly detection kyun?", "Kitchen manager ko unusual waste din ka alert milna chahiye. Isolation Forest bina labels ke unusual points pakadta hai.")
H("I. Power BI aur tools", 2)
QA("Power BI kyun?", "Industry me common BI tool hai; slicers, drill-down aur DAX measures se OLAP interactive ho jata hai. Backup me Streamlit version bhi banaya.")
QA("DAX measure kya hota hai?", "Power BI ki formula language jo aggregation calculate karti hai, jaise Waste % = Qty Wasted / Qty Prepared. Context (filter) ke hisaab se badalta hai.")
QA("Power BI me data kahan se aata hai?", "Warehouse tables ki CSV files se (11 warehouse tables + 4 mining result tables) jo relationships se jude hain.")
QA("Tools kaunse use kiye?", "Python (pandas, scikit-learn, mlxtend, matplotlib), PostgreSQL schema, Power BI, Streamlit.")
H("J. Tricky / gotcha sawaal", 2)
QA("Aapke project me kya kamzori hai?", "Teen: (1) sales/student/menu data synthetic hai, (2) waste classification moderate hai, (3) real datasets chhote hain aur unme weak patterns hain. Future me real POS data se validate karenge.")
QA("Agar aapko real canteen mila to kya badalte?", "Real POS aur waste logs jodte, weather API aur academic calendar features add karte, daily prep recommendation deploy karte aur sach me waste reduction measure karte.")
QA("Kisne kya kiya (team me)?", "Ye aap apni team ke hisaab se tay kar lo (data, warehouse, mining, dashboard, report). Kuch bhi bolo par code ke kisi bhi hisse ko explain kar paao.")
QA("Ek code line batao jo sabse important hai.", "etl.py me integrity assert (har sales row ka item/student/date valid hona) aur mining.py me time-based split. Dono data quality aur leakage se bachate hain.")
QA("Data leakage kya hai aur aapne kaise roka?", "Jab test ki jankari train me aa jaye. Humne time-based split rakha, lag features sirf pichhle din ke liye (shift) banaye, aur test.csv ko use nahi kiya kyunki wo train jaisa tha.")
QA("Overall accuracy/results ek line me?", f"Demand R2 {rf_r2}, clustering ARI {cl['ARI_vs_true_segments']}, association rules me planted combos wapas mile, aur simulator me waste cost {sm['waste_cost_reduction_pct']}% kam; waste classification moderate (~{round(100*clf['Random Forest']['accuracy'])}%).")

H("Part 5: Yaad rakhne wali 7 baatein")
Nn(["Seedhe bolo ki sales data synthetic hai aur kyun. Ye chhupana nahi hai, apni strength banao.",
    "Numbers: transactions %s, waste %.1f%%, demand R2 %s, ARI %s, simulator %s%%." % (f"{N['txn']:,}", N["wpct"], rf_r2, cl["ARI_vs_true_segments"], sm["waste_cost_reduction_pct"]),
    "Galaxy schema ka reason: 3 facts jo dimensions share karte hain.",
    "k=5 ka reason: interpretability aur ARI, silhouette k=2 par zyada hai.",
    "Waste classification weak hai kyunki waste random prep error se aata hai.",
    "Power BI me Refresh mat dabana. powerbi_refresh.ps1 use karo.",
    "Agar kuch na pata ho to bolo: 'Is hisse ko main code dekhke confirm karke bataunga' aur code kholo. Jhooth mat bolo."])
d.save(ROOT / "documents/Viva_and_Demo_Guide.docx")
print("saved")
