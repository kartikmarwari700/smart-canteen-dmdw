SET search_path = canteen_dw;

-- Q1 ROLL-UP: revenue by month -> quarter (total)
SELECT d.quarter, d.month_name, SUM(f.amount) AS revenue
FROM fact_sales f JOIN dim_date d USING (date_id)
GROUP BY ROLLUP (d.quarter, d.month_name) ORDER BY 1, 2;

-- Q2 DRILL-DOWN: category -> item revenue
SELECT c.category_name, i.item_name, SUM(f.amount) AS revenue
FROM fact_sales f JOIN dim_item i USING (item_id) JOIN dim_category c USING (category_id)
GROUP BY ROLLUP (c.category_name, i.item_name) ORDER BY 1, 3 DESC;

-- Q3 SLICE: only Rainy days
SELECT i.item_name, SUM(f.quantity) AS qty
FROM fact_sales f JOIN dim_date d USING (date_id) JOIN dim_item i USING (item_id)
WHERE d.is_rainy GROUP BY i.item_name ORDER BY qty DESC LIMIT 10;

-- Q4 DICE: weekday lunch/dinner AND Meals/Fast Food categories
SELECT d.day_name, s.slot_name, c.category_name, SUM(f.amount) AS revenue
FROM fact_sales f JOIN dim_date d USING (date_id) JOIN dim_meal_slot s USING (slot_id)
JOIN dim_item i USING (item_id) JOIN dim_category c USING (category_id)
WHERE NOT d.is_weekend AND s.slot_name IN ('lunch','dinner') AND c.category_name IN ('Meals','Fast Food')
GROUP BY d.day_name, s.slot_name, c.category_name ORDER BY revenue DESC;

-- Q5 PIVOT: category x meal slot revenue
SELECT c.category_name,
  SUM(f.amount) FILTER (WHERE s.slot_name='breakfast') AS breakfast,
  SUM(f.amount) FILTER (WHERE s.slot_name='lunch')     AS lunch,
  SUM(f.amount) FILTER (WHERE s.slot_name='snacks')    AS snacks,
  SUM(f.amount) FILTER (WHERE s.slot_name='dinner')    AS dinner
FROM fact_sales f JOIN dim_meal_slot s USING (slot_id) JOIN dim_item i USING (item_id)
JOIN dim_category c USING (category_id) GROUP BY c.category_name;

-- Q6 Galaxy join (Sales + Waste share dim_date/dim_item): sold vs wasted per category
SELECT c.category_name, SUM(w.qty_sold) sold, SUM(w.qty_wasted) wasted,
       ROUND(100.0*SUM(w.qty_wasted)/SUM(w.qty_prepared),1) AS waste_pct, SUM(w.waste_cost) AS waste_cost
FROM fact_waste w JOIN dim_item i USING (item_id) JOIN dim_category c USING (category_id)
GROUP BY c.category_name ORDER BY waste_cost DESC;

-- Q7 Waste by weekday (is waste worst on low-footfall days?)
SELECT d.day_name, ROUND(100.0*SUM(w.qty_wasted)/SUM(w.qty_prepared),1) AS waste_pct
FROM fact_waste w JOIN dim_date d USING (date_id) GROUP BY d.day_name, d.day_of_week ORDER BY d.day_of_week;

-- Q8 Top 10 wasted items by cost (with window rank)
SELECT item_name, waste_cost, RANK() OVER (ORDER BY waste_cost DESC) AS rnk FROM (
  SELECT i.item_name, SUM(w.waste_cost) AS waste_cost FROM fact_waste w JOIN dim_item i USING (item_id) GROUP BY i.item_name) t
ORDER BY rnk LIMIT 10;

-- Q9 Impact of exam week / fest on revenue per day
SELECT CASE WHEN d.is_fest THEN 'Fest' WHEN d.is_exam_week THEN 'Exam week' ELSE 'Normal' END AS day_type,
       ROUND(SUM(f.amount)/COUNT(DISTINCT d.date_id)) AS avg_daily_revenue
FROM fact_sales f JOIN dim_date d USING (date_id) GROUP BY 1;

-- Q10 Hostel vs Day-scholar spend by slot
SELECT st.residence, s.slot_name, SUM(f.amount) AS revenue
FROM fact_sales f JOIN dim_student st USING (student_id) JOIN dim_meal_slot s USING (slot_id)
GROUP BY st.residence, s.slot_name ORDER BY 1, 3 DESC;
