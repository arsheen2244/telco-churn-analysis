-- Telco churn analysis: six business questions (SQLite dialect)
-- Table: customers (one row per customer; churn_flag = 1 if the customer left)

-- Q1: Which contract type loses the most customers?
SELECT Contract,
       COUNT(*)                                   AS customers,
       SUM(churn_flag)                            AS churned,
       ROUND(100.0 * AVG(churn_flag), 1)          AS churn_rate_pct
FROM customers
GROUP BY Contract
ORDER BY churn_rate_pct DESC;

-- Q2: How does churn change with customer tenure, and where do churners concentrate?
SELECT tenure_band,
       COUNT(*)                                   AS customers,
       SUM(churn_flag)                            AS churned,
       ROUND(100.0 * AVG(churn_flag), 1)          AS churn_rate_pct,
       ROUND(100.0 * SUM(churn_flag) / SUM(SUM(churn_flag)) OVER (), 1) AS share_of_all_churners_pct
FROM customers
GROUP BY tenure_band
ORDER BY MIN(tenure);

-- Q3: Do support add-ons (TechSupport, OnlineSecurity) protect internet customers?
SELECT InternetService,
       TechSupport,
       OnlineSecurity,
       COUNT(*)                                   AS customers,
       ROUND(100.0 * AVG(churn_flag), 1)          AS churn_rate_pct
FROM customers
WHERE has_internet = 1
GROUP BY InternetService, TechSupport, OnlineSecurity
HAVING COUNT(*) >= 100
ORDER BY churn_rate_pct DESC;

-- Q4: Is the payment method linked to churn?
SELECT PaymentMethod,
       auto_pay,
       COUNT(*)                                   AS customers,
       ROUND(100.0 * AVG(churn_flag), 1)          AS churn_rate_pct,
       ROUND(AVG(MonthlyCharges), 2)              AS avg_monthly_charge
FROM customers
GROUP BY PaymentMethod, auto_pay
ORDER BY churn_rate_pct DESC;

-- Q5: How much monthly recurring revenue (MRR) walked out the door, by contract?
SELECT Contract,
       ROUND(SUM(CASE WHEN churn_flag = 1 THEN MonthlyCharges END), 0) AS mrr_lost,
       ROUND(SUM(MonthlyCharges), 0)                                   AS total_mrr_ever,
       ROUND(100.0 * SUM(CASE WHEN churn_flag = 1 THEN MonthlyCharges END)
             / SUM(MonthlyCharges), 1)                                 AS pct_mrr_lost
FROM customers
GROUP BY Contract
ORDER BY mrr_lost DESC;

-- Q6: How risky is the "worst-case" segment vs everyone else?
-- Segment: month-to-month + fibre optic + no tech support + first-year customer
WITH flagged AS (
    SELECT *,
           CASE WHEN Contract = 'Month-to-month'
                 AND InternetService = 'Fiber optic'
                 AND TechSupport = 'No'
                 AND tenure <= 12
                THEN 'High-risk segment' ELSE 'Everyone else' END AS segment
    FROM customers
)
SELECT segment,
       COUNT(*)                                   AS customers,
       SUM(churn_flag)                            AS churned,
       ROUND(100.0 * AVG(churn_flag), 1)          AS churn_rate_pct,
       ROUND(100.0 * SUM(churn_flag) / SUM(SUM(churn_flag)) OVER (), 1) AS share_of_all_churners_pct,
       ROUND(SUM(CASE WHEN churn_flag = 1 THEN MonthlyCharges END), 0)  AS mrr_lost
FROM flagged
GROUP BY segment
ORDER BY churn_rate_pct DESC;
