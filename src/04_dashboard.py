"""Step 4: dashboard preview PNG + retention target list (all numbers read from outputs/).

Usage: python -I src/04_dashboard.py data/telco_clean.csv outputs
"""
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.patheffects as pe
from matplotlib.patches import FancyBboxPatch

csv_path, out_dir = sys.argv[1], Path(sys.argv[2])

# ---- palette (light surface): one accent + a quiet context grey, ink tokens for all text
SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
BASE, ACCENT, CONTEXT = "#c3c2b7", "#2a78d6", "#c3c2b7"
ORDINAL = ["#86b6ef", "#2a78d6", "#184f95"]  # blue steps 250 / 450 / 600 for Low / Medium / High

df = pd.read_csv(csv_path)
scored = pd.read_csv(out_dir / "powerbi_dataset.csv")
q1, q2, q3, q4 = (pd.read_csv(out_dir / f"sql_q{i}.csv") for i in (1, 2, 3, 4))
q6 = pd.read_csv(out_dir / "sql_q6.csv").set_index("segment")
imp = pd.read_csv(out_dir / "feature_importance.csv")
bands = pd.read_csv(out_dir / "risk_band_check.csv").set_index("risk_band")

overall = df["churn_flag"].mean() * 100
churned = df[df["churn_flag"] == 1]
mrr_lost = churned["MonthlyCharges"].sum()
mrr_pct = mrr_lost / df["MonthlyCharges"].sum()
hr = q6.loc["High-risk segment"]

plt.rcParams.update({"font.family": "sans-serif", "axes.facecolor": SURFACE})
HALO = [pe.withStroke(linewidth=4, foreground=SURFACE)]  # keeps the reference line from cutting through value labels


def px_per_unit(ax):
    o = ax.transData.transform((0, 0))
    return (ax.transData.transform((1, 0))[0] - o[0],
            abs(ax.transData.transform((0, 1))[1] - o[1]))


def rounded(ax, x0, y0, x1, y1, color, r_px=4):
    """Rect with rounded corners; the part past the axes edge is clipped, so the baseline end stays square."""
    px_x, px_y = px_per_unit(ax)
    patch = FancyBboxPatch(
        (x0, y0), x1 - x0, y1 - y0,
        boxstyle=f"round,pad=0,rounding_size={r_px / px_x}",
        mutation_aspect=px_x / px_y, fc=color, ec="none", zorder=3)
    ax.add_patch(patch)


def panel_header(ax, title, subtitle, x=0):
    ax.text(x, 1.2, title, transform=ax.transAxes, fontsize=13.5, fontweight="bold", color=INK)
    ax.text(x, 1.1, subtitle, transform=ax.transAxes, fontsize=10, color=INK2)


def label_left(ax):
    """Left edge (axes coords) of the y tick labels, so a panel title lines up with its labels."""
    ax.figure.canvas.draw()
    r = ax.figure.canvas.get_renderer()
    left = min(t.get_window_extent(r).x0 for t in ax.get_yticklabels())
    return ax.transAxes.inverted().transform((left, 0))[0]


def hbars(ax, labels, values, colors, fmt, title, subtitle, ref=None, xmax=None):
    n = len(values)
    ax.set_xlim(0, xmax or max(values) * 1.25)
    ax.set_ylim(n - 0.4, -0.85)
    px_x, px_y = px_per_unit(ax)
    thick = min(0.55, 22 / px_y)  # cap bar thickness near 22 px
    if ref is not None:
        ax.axvline(ref, color=MUTED, lw=1, zorder=1)
        ax.text(ref, -0.72, f"avg {ref:.1f}%", ha="center", va="bottom", fontsize=9, color=MUTED)
    for i, (v, c) in enumerate(zip(values, colors)):
        rounded(ax, -12 / px_x, i - thick / 2, v, i + thick / 2, c)
        ax.text(v + 7 / px_x, i, fmt(v), va="center", ha="left", fontsize=11,
                fontweight="bold", color=INK, zorder=4, path_effects=HALO)
    ax.set_yticks(range(n))
    ax.set_yticklabels(labels, fontsize=10.5, color=INK2)
    ax.set_xticks([])
    ax.tick_params(length=0)
    for s in ("top", "right", "bottom"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(BASE)
    panel_header(ax, title, subtitle, x=label_left(ax))


def columns(ax, labels, values, colors, fmt, title, subtitle, ref=None, ref_side="right"):
    n = len(values)
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(0, max(values) * 1.18)
    px_x, px_y = px_per_unit(ax)
    thick = min(0.5, 24 / px_x)
    if ref is not None:
        ax.axhline(ref, color=MUTED, lw=1, zorder=1)
        x, ha = (n - 0.45, "right") if ref_side == "right" else (-0.55, "left")
        ax.text(x, ref + 0.8, f"avg {ref:.1f}%", ha=ha, va="bottom", fontsize=9, color=MUTED)
    for i, (v, c) in enumerate(zip(values, colors)):
        rounded(ax, i - thick / 2, -12 / px_y, i + thick / 2, v, c)
        ax.text(i, v + 6 / px_y, fmt(v), ha="center", va="bottom", fontsize=11,
                fontweight="bold", color=INK, zorder=4, path_effects=HALO)
    ax.set_xticks(range(n))
    ax.set_xticklabels(labels, fontsize=10.5, color=INK2)
    ax.set_yticks([])
    ax.tick_params(length=0)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.spines["bottom"].set_color(BASE)
    panel_header(ax, title, subtitle)


pct = lambda v: f"{v:.1f}%"
top_only = lambda vals: [ACCENT if v == max(vals) else CONTEXT for v in vals]

fig = plt.figure(figsize=(18, 11.6), facecolor=SURFACE)
# Row 0 of the grid is left empty on purpose: the KPI strip is placed over it with its own axes
gs = fig.add_gridspec(3, 3, height_ratios=[0.5, 1, 1], left=0.16, right=0.985,
                      top=0.885, bottom=0.07, hspace=0.62, wspace=0.62)
fig.text(0.045, 0.955, "Telecom customer churn: where customers leave, and what it costs",
         fontsize=21, fontweight="bold", color=INK)
fig.text(0.045, 0.925, f"{len(df):,} customers · IBM Telco sample dataset · churn = customer left in the period",
         fontsize=11.5, color=INK2)

# ---- KPI row
kx = fig.add_axes([0.045, 0.775, 0.94, 0.11])
kx.axis("off")
kx.set_xlim(0, 4)
kx.set_ylim(0, 1)
tiles = [
    ("Customers analysed", f"{len(df):,}", "0 duplicate IDs, 11 blank TotalCharges fixed"),
    ("Overall churn rate", f"{overall:.1f}%", f"{len(churned):,} customers left"),
    ("Monthly revenue lost to churn", f"${mrr_lost / 1000:,.0f}K", f"{mrr_pct:.0%} of summed monthly charges"),
    ("High-risk segment churn", f"{hr['churn_rate_pct']:.1f}%",
     f"{int(hr['customers'])} customers: monthly contract, fibre, no support, year 1"),
]
for i, (label, value, sub) in enumerate(tiles):
    x = i + 0.02
    kx.text(x, 0.80, label, fontsize=11, color=INK2, va="center")
    kx.text(x, 0.46, value, fontsize=30, fontweight="bold", color=INK, va="center")
    kx.text(x, 0.12, sub, fontsize=9.5, color=MUTED, va="center")
    if i:
        kx.plot([i - 0.03, i - 0.03], [0.08, 0.92], color=BASE, lw=1)

# ---- panels
ax = fig.add_subplot(gs[1, 0])
hbars(ax, q1["Contract"], q1["churn_rate_pct"], top_only(list(q1["churn_rate_pct"])), pct,
      "Contract type", "Churn rate by contract", ref=overall, xmax=56)

ax = fig.add_subplot(gs[1, 1])
columns(ax, q2["tenure_band"], q2["churn_rate_pct"], top_only(list(q2["churn_rate_pct"])), pct,
        "Customer tenure", f"Churn rate by months as a customer", ref=overall, ref_side="right")

ax = fig.add_subplot(gs[1, 2])
hbars(ax, q4["PaymentMethod"].str.replace(" (automatic)", " (auto)", regex=False),
      q4["churn_rate_pct"], top_only(list(q4["churn_rate_pct"])), pct,
      "Payment method", "Churn rate by how customers pay", ref=overall, xmax=58)


def combo_label(r):
    svc = "Fibre" if r["InternetService"] == "Fiber optic" else "DSL"
    if r["TechSupport"] == "Yes" and r["OnlineSecurity"] == "Yes":
        extra = "support + security"
    elif r["TechSupport"] == "Yes":
        extra = "tech support only"
    elif r["OnlineSecurity"] == "Yes":
        extra = "security only"
    else:
        extra = "no add-ons"
    return f"{svc}, {extra}"


ax = fig.add_subplot(gs[2, 0])
hbars(ax, [combo_label(r) for _, r in q3.iterrows()], q3["churn_rate_pct"],
      top_only(list(q3["churn_rate_pct"])), pct,
      "Internet service and support add-ons", "Support add-ons cut churn on both services",
      ref=overall, xmax=68)

ax = fig.add_subplot(gs[2, 1])
order = ["Low", "Medium", "High"]
columns(ax, order, [bands.loc[b, "actual_churn_rate"] * 100 for b in order], ORDINAL, pct,
        "Model check: risk bands",
        "Actual churn rate per predicted band (out-of-fold)", ref=overall, ref_side="left")
for i, b in enumerate(order):  # customers per band, small, under the tick label
    ax.text(i, -0.115, f"n = {int(bands.loc[b, 'customers']):,}", transform=ax.get_xaxis_transform(),
            ha="center", va="top", fontsize=9, color=MUTED)

ax = fig.add_subplot(gs[2, 2])
names = {"Contract": "Contract type", "tenure": "Tenure", "InternetService": "Internet service",
         "OnlineSecurity": "Online security", "MonthlyCharges": "Monthly charges",
         "TechSupport": "Tech support", "PaymentMethod": "Payment method", "SeniorCitizen": "Senior citizen"}
top = imp.head(6)
hbars(ax, [names.get(f, f) for f in top["feature"]], list(top["auc_drop_when_shuffled"]),
      [ACCENT] * len(top), lambda v: f"{v:.3f}",
      "What the model relies on", "Drop in test AUC when the column is shuffled")

fig.savefig(out_dir / "dashboard_preview.png", dpi=150, facecolor=SURFACE)
print("saved", out_dir / "dashboard_preview.png")

# ---- retention target list: customers who have NOT churned yet but score as high risk
active_hi = scored[(scored["churn_flag"] == 0) & (scored["risk_band"] == "High")].copy()
active_hi["expected_monthly_loss"] = (active_hi["MonthlyCharges"] * active_hi["churn_risk"]).round(2)
cols = ["customerID", "Contract", "InternetService", "TechSupport", "PaymentMethod", "tenure",
        "MonthlyCharges", "churn_risk", "expected_monthly_loss"]
active_hi = active_hi.sort_values("expected_monthly_loss", ascending=False)[cols]
active_hi.to_csv(out_dir / "retention_target_list.csv", index=False)

numbers = {
    "customers": int(len(df)), "churned": int(len(churned)), "churn_rate_pct": round(overall, 1),
    "monthly_revenue_lost": round(float(mrr_lost), 0), "pct_of_monthly_charges": round(float(mrr_pct) * 100, 1),
    "active_high_risk_customers": int(len(active_hi)),
    "active_high_risk_monthly_charges": round(float(active_hi["MonthlyCharges"].sum()), 0),
    "active_high_risk_expected_monthly_loss": round(float(active_hi["expected_monthly_loss"].sum()), 0),
}
(out_dir / "dashboard_numbers.json").write_text(json.dumps(numbers, indent=2))
print(json.dumps(numbers, indent=2))
