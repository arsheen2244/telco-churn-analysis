"""Step 3: hypothesis tests, churn model, feature importance, revenue scenario.

Usage: python -I src/03_stats_and_model.py data/telco_clean.csv outputs
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

csv_path, out_dir = sys.argv[1], Path(sys.argv[2])
df = pd.read_csv(csv_path)
y = df["churn_flag"]

# ------------------------------------------------------------------ 1. hypothesis tests
print("=== CHI-SQUARE TESTS: is churn independent of each factor? ===")
rows = []
for col in ["Contract", "InternetService", "PaymentMethod", "TechSupport", "OnlineSecurity",
            "SeniorCitizen", "Partner", "Dependents", "PaperlessBilling", "gender"]:
    table = pd.crosstab(df[col], y)
    chi2, p, dof, _ = stats.chi2_contingency(table)
    n = table.to_numpy().sum()
    cramers_v = np.sqrt(chi2 / (n * (min(table.shape) - 1)))
    rows.append({"factor": col, "chi2": round(chi2, 1), "dof": dof,
                 "p_value": p, "cramers_v": round(cramers_v, 3),
                 "significant_at_0.05": p < 0.05})
tests = pd.DataFrame(rows).sort_values("cramers_v", ascending=False)
tests.to_csv(out_dir / "stat_tests_chi2.csv", index=False)
print(tests.to_string(index=False, float_format=lambda v: f"{v:.3g}"))

print("\n=== MANN-WHITNEY U: do churners differ on tenure / monthly charges? ===")
mw_rows = []
for col in ["tenure", "MonthlyCharges"]:
    a, b = df.loc[y == 1, col], df.loc[y == 0, col]
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    mw_rows.append({"variable": col, "median_churned": a.median(), "median_stayed": b.median(),
                    "p_value": p})
mw = pd.DataFrame(mw_rows)
mw.to_csv(out_dir / "stat_tests_mannwhitney.csv", index=False)
print(mw.to_string(index=False, float_format=lambda v: f"{v:.3g}"))

# ------------------------------------------------------------------ 2. model
cat_cols = ["gender", "SeniorCitizen", "Partner", "Dependents", "PhoneService", "MultipleLines",
            "InternetService", "OnlineSecurity", "OnlineBackup", "DeviceProtection", "TechSupport",
            "StreamingTV", "StreamingMovies", "Contract", "PaperlessBilling", "PaymentMethod"]
num_cols = ["tenure", "MonthlyCharges"]  # TotalCharges ~ tenure x MonthlyCharges, so it is left out
X = df[cat_cols + num_cols]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42)


def make_pipe(model, scale):
    pre = ColumnTransformer([
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols),
        ("num", StandardScaler() if scale else "passthrough", num_cols),
    ])
    return Pipeline([("pre", pre), ("model", model)])


models = {
    "Logistic regression": make_pipe(LogisticRegression(max_iter=1000, class_weight="balanced"), True),
    "Random forest": make_pipe(RandomForestClassifier(
        n_estimators=300, min_samples_leaf=5, class_weight="balanced",
        random_state=42, n_jobs=-1), False),
}

baseline_acc = 1 - y_test.mean()
metrics = {"majority_class_baseline_accuracy": round(baseline_acc, 3)}
print(f"\n=== MODELS (hold-out test set = {len(y_test):,} customers) ===")
print(f"Baseline (always predict 'stays') accuracy: {baseline_acc:.1%}")
skf = StratifiedKFold(5, shuffle=True, random_state=42)
for name, pipe in models.items():
    pipe.fit(X_train, y_train)
    proba = pipe.predict_proba(X_test)[:, 1]
    pred = (proba >= 0.5).astype(int)
    cv_auc = cross_val_score(pipe, X, y, cv=skf, scoring="roc_auc", n_jobs=-1)
    metrics[name] = {
        "test_roc_auc": round(roc_auc_score(y_test, proba), 3),
        "cv_roc_auc_mean": round(cv_auc.mean(), 3),
        "cv_roc_auc_std": round(cv_auc.std(), 3),
        "accuracy": round(accuracy_score(y_test, pred), 3),
        "precision_churn": round(precision_score(y_test, pred), 3),
        "recall_churn": round(recall_score(y_test, pred), 3),
    }
    print(f"{name}: {metrics[name]}")
(out_dir / "model_metrics.json").write_text(json.dumps(metrics, indent=2))

# ---- logistic-regression odds ratios (interpretable drivers)
lr = models["Logistic regression"]
names = lr.named_steps["pre"].get_feature_names_out()
coefs = lr.named_steps["model"].coef_[0]
odds = pd.DataFrame({"feature": names, "odds_ratio": np.exp(coefs)}).sort_values("odds_ratio", ascending=False)
odds["feature"] = odds["feature"].str.replace("cat__", "", regex=False).str.replace("num__", "", regex=False)
odds.to_csv(out_dir / "logit_odds_ratios.csv", index=False)
print("\nTop 6 features that RAISE churn odds (odds ratio, 1 SD for numeric):")
print(odds.head(6).to_string(index=False, float_format=lambda v: f"{v:.2f}"))
print("Top 6 features that LOWER churn odds:")
print(odds.tail(6).to_string(index=False, float_format=lambda v: f"{v:.2f}"))

# ---- permutation importance for the random forest (per original column)
rf = models["Random forest"]
perm = permutation_importance(rf, X_test, y_test, scoring="roc_auc",
                              n_repeats=10, random_state=42, n_jobs=-1)
imp = pd.DataFrame({"feature": X.columns, "auc_drop_when_shuffled": perm.importances_mean,
                    "std": perm.importances_std}).sort_values("auc_drop_when_shuffled", ascending=False)
imp.to_csv(out_dir / "feature_importance.csv", index=False)
print("\nRandom-forest permutation importance (drop in test AUC when column is shuffled):")
print(imp.head(8).to_string(index=False, float_format=lambda v: f"{v:.4f}"))

# ---- out-of-fold risk scores for EVERY customer (no leakage) -> Power BI
oof = cross_val_predict(rf, X, y, cv=skf, method="predict_proba", n_jobs=-1)[:, 1]
scored = df.copy()
scored["churn_risk"] = oof.round(4)
scored["risk_band"] = pd.cut(scored["churn_risk"], bins=[-0.01, 0.35, 0.65, 1.0],
                             labels=["Low", "Medium", "High"]).astype(str)
scored.to_csv(out_dir / "powerbi_dataset.csv", index=False)
band = scored.groupby("risk_band").agg(customers=("churn_flag", "size"),
                                       actual_churn_rate=("churn_flag", "mean")).round(3)
band.to_csv(out_dir / "risk_band_check.csv")
print("\nRisk bands vs what actually happened (sanity check):")
print(band.to_string())

# ------------------------------------------------------------------ 3. revenue scenario
seg = (df["Contract"] == "Month-to-month") & (df["InternetService"] == "Fiber optic") \
      & (df["TechSupport"] == "No") & (df["tenure"] <= 12)
seg_churned = df[seg & (y == 1)]
reduction = 0.10
scenario = {
    "segment_customers": int(seg.sum()),
    "segment_churned": int(len(seg_churned)),
    "segment_churn_rate": round(float(y[seg].mean()), 3),
    "assumed_relative_churn_reduction": reduction,
    "customers_retained": round(len(seg_churned) * reduction, 1),
    "monthly_revenue_retained": round(float(seg_churned["MonthlyCharges"].sum() * reduction), 0),
    "annualised_revenue_retained": round(float(seg_churned["MonthlyCharges"].sum() * reduction * 12), 0),
}
# The segment rule was chosen after exploring the full data, so its churn rate is in-sample.
# Re-checking it on the 20% hold-out split is a (partial) sanity check, not a clean out-of-sample test.
seg_test = seg.loc[y_test.index]
scenario["holdout_check"] = {
    "segment_customers_in_test": int(seg_test.sum()),
    "segment_churn_rate_in_test": round(float(y_test[seg_test].mean()), 3),
    "rest_churn_rate_in_test": round(float(y_test[~seg_test].mean()), 3),
}
(out_dir / "revenue_scenario.json").write_text(json.dumps(scenario, indent=2))
print("\n=== REVENUE SCENARIO ===")
print(json.dumps(scenario, indent=2))
