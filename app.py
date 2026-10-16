"""Streamlit dashboard for the telecom churn project.

Run locally:  streamlit run app.py
Reads only the pre-computed files in outputs/, so nothing is retrained on load.
"""
import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Telecom Churn Dashboard", layout="wide")

ROOT = Path(__file__).parent
TENURE_ORDER = ["0-12 mo", "13-24 mo", "25-48 mo", "49-72 mo"]


@st.cache_data
def load_data():
    df = pd.read_csv(ROOT / "outputs" / "powerbi_dataset.csv")
    df["expected_monthly_loss"] = (df["churn_risk"] * df["MonthlyCharges"]).round(2)
    return df


def churn_rate_by(df, col, order=None):
    """Churn rate (%) per category."""
    s = df.groupby(col)["churn_flag"].mean().mul(100).round(1)
    if order:
        return s.reindex(order).dropna()
    return s.sort_values(ascending=False)


def in_segment(df):
    """High-risk segment from the README: first-year, month-to-month, fibre, no tech support."""
    return (
        (df["Contract"] == "Month-to-month")
        & (df["InternetService"] == "Fiber optic")
        & (df["TechSupport"] == "No")
        & (df["tenure"] <= 12)
    )


full = load_data()

# ---------------------------------------------------------------- header
st.title("Telecom customer churn")
st.caption(
    "IBM Telco sample dataset (7,043 customers). Churn rates are descriptive; "
    "they show association, not cause. Risk scores are out-of-fold model predictions."
)

# ---------------------------------------------------------------- filters
st.sidebar.header("Filters")
contracts = st.sidebar.multiselect("Contract", sorted(full["Contract"].unique()), default=sorted(full["Contract"].unique()))
internet = st.sidebar.multiselect("Internet service", sorted(full["InternetService"].unique()), default=sorted(full["InternetService"].unique()))
tenures = st.sidebar.multiselect("Tenure band", TENURE_ORDER, default=TENURE_ORDER)

df = full[
    full["Contract"].isin(contracts)
    & full["InternetService"].isin(internet)
    & full["tenure_band"].isin(tenures)
]
if df.empty:
    st.warning("No customers match these filters.")
    st.stop()

lost = df.loc[df["churn_flag"] == 1, "MonthlyCharges"].sum()
k1, k2, k3, k4 = st.columns(4)
k1.metric("Customers", f"{len(df):,}")
k2.metric("Churn rate", f"{df['churn_flag'].mean() * 100:.1f}%")
k3.metric("Monthly billing lost to churn", f"{lost:,.0f}")
k4.metric("Share of monthly billing", f"{lost / df['MonthlyCharges'].sum() * 100:.1f}%")

tab1, tab2, tab3 = st.tabs(["Who churns", "High-risk segment", "Retention list"])

# ---------------------------------------------------------------- tab 1
with tab1:
    st.caption("Churn rate (%) within the filtered customers. Small groups are noisy.")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("By contract")
        st.bar_chart(churn_rate_by(df, "Contract"))
        st.subheader("By internet service")
        st.bar_chart(churn_rate_by(df, "InternetService"))
    with c2:
        st.subheader("By tenure band")
        st.bar_chart(churn_rate_by(df, "tenure_band", TENURE_ORDER))
        st.subheader("By payment method")
        st.bar_chart(churn_rate_by(df, "PaymentMethod"))

# ---------------------------------------------------------------- tab 2
with tab2:
    st.markdown(
        "**Segment:** month-to-month contract, fibre internet, no tech support, first 12 months. "
        "This tab always uses all customers (filters do not apply)."
    )
    mask = in_segment(full)
    seg, rest = full[mask], full[~mask]
    seg_churners = seg[seg["churn_flag"] == 1]

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Customers in segment", f"{len(seg):,}", f"{len(seg) / len(full) * 100:.0f}% of base", delta_color="off")
    m2.metric("Segment churn rate", f"{seg['churn_flag'].mean() * 100:.1f}%")
    m3.metric("Everyone else", f"{rest['churn_flag'].mean() * 100:.1f}%")
    m4.metric("Share of all churners", f"{len(seg_churners) / full['churn_flag'].sum() * 100:.1f}%")

    scenario = json.loads((ROOT / "outputs" / "revenue_scenario.json").read_text())
    holdout = scenario["holdout_check"]
    st.info(
        "The segment was defined after exploring the full data, so its churn rate is optimistic. "
        f"On the 20% hold-out split it churns at {holdout['segment_churn_rate_in_test'] * 100:.1f}% "
        f"({holdout['segment_customers_in_test']} customers) vs {holdout['rest_churn_rate_in_test'] * 100:.1f}% for the rest. "
        "This is a consistency check, not a clean out-of-sample test."
    )

    st.subheader("Revenue scenario")
    reduction = st.slider("Assumed relative reduction in segment churn", 5, 30, 10, step=5, format="%d%%")
    retained = len(seg_churners) * reduction / 100
    avg_charge = seg_churners["MonthlyCharges"].mean()
    monthly = retained * avg_charge
    s1, s2, s3 = st.columns(3)
    s1.metric("Customers retained", f"{retained:,.0f}")
    s2.metric("Monthly billing protected", f"{monthly:,.0f}")
    s3.metric("Over 12 months", f"{monthly * 12:,.0f}")
    st.caption(
        "Scenario, not a measured result: assumes retained customers stay 12 months at today's "
        "charges and ignores the cost of the offer. The dataset does not state a currency."
    )

# ---------------------------------------------------------------- tab 3
with tab3:
    st.markdown(
        "Customers who did **not** churn but score **High** risk, ranked by expected monthly loss "
        "(churn probability x monthly charge)."
    )
    st.caption(
        "Illustrative: in production you would score current customers before their outcome is known."
    )
    target = (
        df[(df["churn_flag"] == 0) & (df["risk_band"] == "High")]
        .sort_values("expected_monthly_loss", ascending=False)
        [["customerID", "Contract", "InternetService", "TechSupport", "PaymentMethod",
          "tenure", "MonthlyCharges", "churn_risk", "expected_monthly_loss"]]
    )
    t1, t2 = st.columns(2)
    t1.metric("Customers listed", f"{len(target):,}")
    t2.metric("Their monthly charges", f"{target['MonthlyCharges'].sum():,.0f}")
    st.dataframe(target, hide_index=True)
    st.download_button(
        "Download as CSV", target.to_csv(index=False).encode("utf-8"),
        file_name="retention_target_list.csv", mime="text/csv",
    )