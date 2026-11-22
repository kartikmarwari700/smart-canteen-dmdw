-- Smart Canteen Data Warehouse (PostgreSQL)
-- Fact Constellation (Galaxy): Fact_Sales, Fact_Waste, Fact_Inventory share conformed dimensions.
-- Snowflake part: Dim_Item -> Dim_Category -> Dim_Cuisine (normalised hierarchy).
-- Star part: Fact_Sales -> Dim_Date / Dim_Student / Dim_MealSlot / Dim_Item (denormalised view below).

DROP SCHEMA IF EXISTS canteen_dw CASCADE;
CREATE SCHEMA canteen_dw;
SET search_path = canteen_dw;

-- ---------------- Dimensions ----------------
CREATE TABLE dim_date (
    date_id        INT PRIMARY KEY,           -- yyyymmdd
    full_date      DATE NOT NULL,
    day_of_week    SMALLINT NOT NULL,         -- 0=Mon
    day_name       VARCHAR(10) NOT NULL,
    week_of_year   SMALLINT NOT NULL,
    month          SMALLINT NOT NULL,
    month_name     VARCHAR(10) NOT NULL,
    quarter        SMALLINT NOT NULL,
    is_weekend     BOOLEAN NOT NULL,
    is_exam_week   BOOLEAN NOT NULL,
    is_fest        BOOLEAN NOT NULL,
    temp_c         NUMERIC(4,1),
    is_rainy       BOOLEAN
);

CREATE TABLE dim_meal_slot (
    slot_id    SMALLINT PRIMARY KEY,
    slot_name  VARCHAR(12) UNIQUE NOT NULL,
    start_time TIME, end_time TIME
);

CREATE TABLE dim_cuisine (
    cuisine_id   SERIAL PRIMARY KEY,
    cuisine_name VARCHAR(30) UNIQUE NOT NULL
);

CREATE TABLE dim_category (
    category_id   SERIAL PRIMARY KEY,
    category_name VARCHAR(30) UNIQUE NOT NULL
);

CREATE TABLE dim_item (
    item_id      INT PRIMARY KEY,
    item_name    VARCHAR(40) NOT NULL,
    category_id  INT REFERENCES dim_category(category_id),
    cuisine_id   INT REFERENCES dim_cuisine(cuisine_id),
    is_veg       BOOLEAN, is_healthy BOOLEAN,
    price        NUMERIC(6,2), unit_cost NUMERIC(6,2),
    perishability NUMERIC(3,2)
);

CREATE TABLE dim_student (
    student_id   INT PRIMARY KEY,
    residence    VARCHAR(12), year SMALLINT, branch VARCHAR(8), gender CHAR(1),
    is_veg_pref  BOOLEAN, avg_budget INT, visit_freq NUMERIC(3,2),
    segment_true VARCHAR(20),                 -- synthetic ground truth (for clustering evaluation only)
    segment_mined VARCHAR(20)                 -- filled by clustering step
);

-- ---------------- Facts ----------------
CREATE TABLE fact_sales (
    sales_key      BIGSERIAL PRIMARY KEY,
    transaction_id INT NOT NULL,
    date_id        INT REFERENCES dim_date(date_id),
    slot_id        SMALLINT REFERENCES dim_meal_slot(slot_id),
    student_id     INT REFERENCES dim_student(student_id),
    item_id        INT REFERENCES dim_item(item_id),
    quantity       INT NOT NULL,
    unit_price     NUMERIC(6,2),
    amount         NUMERIC(8,2)
);

CREATE TABLE fact_waste (
    date_id      INT REFERENCES dim_date(date_id),
    item_id      INT REFERENCES dim_item(item_id),
    qty_prepared INT, qty_sold INT, qty_wasted INT, qty_shortage INT,
    waste_cost   NUMERIC(10,2), waste_pct NUMERIC(5,2),
    PRIMARY KEY (date_id, item_id)
);

CREATE TABLE fact_inventory (
    date_id       INT REFERENCES dim_date(date_id),
    item_id       INT REFERENCES dim_item(item_id),
    opening_stock INT, qty_received INT, qty_used INT, closing_stock INT,
    PRIMARY KEY (date_id, item_id)
);

-- Real (Kaggle) facts, conformed to dim_date
CREATE TABLE fact_real_canteen_waste (
    date_id INT REFERENCES dim_date(date_id),
    meal VARCHAR(12), section CHAR(1), food_category VARCHAR(20),
    waste_kg NUMERIC(6,2), price_per_kg NUMERIC(5,2), cost_loss NUMERIC(8,2)
);
CREATE TABLE fact_kitchen_waste (
    record_id INT, date_id INT REFERENCES dim_date(date_id),
    meals_served INT, kitchen_staff INT, temperature_c NUMERIC(5,1), humidity_percent NUMERIC(5,1),
    special_event BOOLEAN, past_waste_kg NUMERIC(6,2), staff_experience VARCHAR(15),
    waste_category VARCHAR(15), food_waste_kg NUMERIC(7,2), is_outlier BOOLEAN
);

CREATE INDEX ix_sales_date ON fact_sales(date_id);
CREATE INDEX ix_sales_item ON fact_sales(item_id);
CREATE INDEX ix_sales_student ON fact_sales(student_id);

-- ---------------- Star-schema view (denormalised item dimension) ----------------
CREATE VIEW star_dim_item AS
SELECT i.item_id, i.item_name, c.category_name, u.cuisine_name, i.is_veg, i.is_healthy, i.price
FROM dim_item i JOIN dim_category c USING (category_id) JOIN dim_cuisine u USING (cuisine_id);
