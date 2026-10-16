# Resume bullet and interview prep

## Resume bullet (use it after you have built the Power BI pages and can explain every step)

> Analysed 7,043 telecom customers end to end (SQL, Python, Power BI): found that first-year, month-to-month fibre customers without tech support churn at 71% vs 21% for the rest (32% of all churners); built a churn-risk model (ROC-AUC 0.84, 5-fold CV) and sized a retention offer at ~$58K/year of protected billing.

Keep the numbers; drop any claim you cannot defend. "Sized" is deliberate wording: the $58K is a scenario (10% relative churn reduction, 12 months of retained billing, no cost of the offer), not a measured result.

## Questions you should be ready for

**Why this dataset?** It is the widely used IBM Telco sample, so the data is not the differentiator. What I added was the SQL layer, statistical tests with effect sizes, an out-of-fold risk model, a revenue estimate, and a stated list of limitations.

**Why chi-square and Mann-Whitney?** Churn is binary, so categorical factors go through a chi-square test of independence. Tenure and charges are skewed, so a rank-based test (Mann-Whitney) is safer than a t-test. With 7,043 rows almost everything is "significant", so I also report Cramér's V to show how big each effect is.

**Why not report accuracy?** 73.5% of customers stay, so always predicting "stays" is already 73.5% accurate. I used balanced class weights to catch churners and report AUC, recall and precision instead.

**Why logistic regression and a random forest?** Logistic regression gives directions and odds ratios that a business reader can follow. The random forest checks whether non-linear effects add anything. They score the same AUC (0.84), which tells me the signal is mostly simple.

**Why drop `TotalCharges` from the model?** It is almost tenure x monthly charges, so it adds collinearity and no new information.

**What are out-of-fold scores and why use them?** Each customer is scored by a model trained on the other folds, so the risk score shown in the dashboard is never produced by a model that saw that customer's outcome.

**What would you do next?** Run an A/B test of the support-add-on offer on the high-risk segment. The data shows association, not that the add-ons cause retention.

**What is the weakest part of this project?** The high-risk segment was defined after exploring the whole dataset, so 71% is optimistic. The hold-out split gives 68.6% (172 customers), which is reassuring but not a clean test.

**Why would fibre customers churn more?** The data cannot say. Candidate explanations are price, service quality and competition, and each would need different data to test.
