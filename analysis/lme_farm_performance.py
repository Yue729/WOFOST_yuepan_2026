"""
Linear Mixed Effects Model: farm-level performance score
=========================================================
Response  : average performance score per farm × year (excl. sugar beet)
Fixed effects : year (categorical), region (DR / ZW)
Random effect : farm_id (random intercept — accounts for repeated measures
                across years within the same farm)

Model formula (Wilkinson notation):
    performance_score ~ C(year) + region + (1 | farm_id)

statsmodels MixedLM is used (REML by default).
"""

from pathlib import Path
import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from statsmodels.stats.anova import anova_lm
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import warnings
warnings.filterwarnings("ignore")

# ── Paths ─────────────────────────────────────────────────────────────────────
PERF_EXCEL = Path(
    "/Users/panyue/Desktop/final_data/2_yield_data/yield_plots_performance/"
    "performance_scores_detailed_no_sugarbeet.xlsx"
)
OUT_DIR = Path("/Users/panyue/Desktop/final_data/2_yield_data/yield_plots_performance/")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Load field-level records ──────────────────────────────────────────────────
records = pd.read_excel(PERF_EXCEL, sheet_name="All_Records")
records["ID_field"] = records["ID_field"].astype(str).str.strip()
records["farm_id"]  = records["farm_id"].astype(str).str.strip()
records["region"]   = records["ID_field"].str[:2]          # DR or ZW
records["year"]     = records["year"].astype(int)

# ── Aggregate to FARM × YEAR level ───────────────────────────────────────────
farm_year = (
    records
    .groupby(["farm_id", "year", "region"], as_index=False)
    .agg(performance_score=("performance_score", "mean"),
         n_fields=("ID_field", "nunique"))
)

print(f"Farm × year observations: {len(farm_year)}")
print(f"Farms: {farm_year['farm_id'].nunique()}")
print(f"Years: {sorted(farm_year['year'].unique())}")
print(f"Regions: {farm_year['region'].value_counts().to_dict()}")
print()
print(farm_year.groupby(["region", "year"])["performance_score"].describe().round(2))
print()

# ── Encode factors ────────────────────────────────────────────────────────────
# Reference levels: year=2023, region=DR
farm_year["year_cat"] = pd.Categorical(farm_year["year"].astype(str),
                                       categories=["2023", "2024", "2025"])
farm_year["region_cat"] = pd.Categorical(farm_year["region"],
                                         categories=["DR", "ZW"])

# ── Fit Linear Mixed Effects Model ───────────────────────────────────────────
# Fixed: year + region
# Random intercept: farm_id (farms are sampled from a larger population)
formula = "performance_score ~ C(year_cat) + C(region_cat)"

model = smf.mixedlm(formula, data=farm_year, groups=farm_year["farm_id"])
result = model.fit(reml=True)

print("=" * 70)
print("LINEAR MIXED EFFECTS MODEL — Farm performance score ")
print("=" * 70)
print(result.summary())

# ── Extract fixed-effect table ───────────────────────────────────────────────
fe = result.fe_params.to_frame(name="Estimate")
fe["SE"]      = result.bse_fe
fe["z"]       = result.tvalues
fe["p-value"] = result.pvalues
fe["CI_low"]  = result.conf_int().iloc[:len(fe), 0]
fe["CI_high"] = result.conf_int().iloc[:len(fe), 1]
fe = fe.round(4)

print("\n── Fixed Effects Table ──")
print(fe.to_string())

# ── Random effects (farm intercept deviations) ───────────────────────────────
re = pd.DataFrame({"farm_id": list(result.random_effects.keys()),
                   "random_intercept": [v.iloc[0] for v in result.random_effects.values()]})
re = re.sort_values("random_intercept", ascending=False).reset_index(drop=True)
re["region"] = re["farm_id"].str[:2]

print("\n── Random Intercepts (farm deviations from grand mean) ──")
print(re.to_string(index=False))

# ── Model fit statistics ──────────────────────────────────────────────────────
print(f"\nLog-likelihood : {result.llf:.4f}")
print(f"AIC            : {result.aic:.4f}")
print(f"BIC            : {result.bic:.4f}")
print(f"Variance (farm): {result.cov_re.values[0][0]:.4f}")
print(f"Variance (resid): {result.scale:.4f}")

# Intraclass correlation (ICC) = var_farm / (var_farm + var_resid)
var_farm  = result.cov_re.values[0][0]
var_resid = result.scale
icc = var_farm / (var_farm + var_resid)
print(f"ICC (farm)     : {icc:.4f}  ({icc*100:.1f}% of variance explained by farm)")

# ── Save results to Excel ─────────────────────────────────────────────────────
out_excel = OUT_DIR / "lme_farm_performance_results.xlsx"
with pd.ExcelWriter(out_excel, engine="openpyxl") as writer:
    farm_year.to_excel(writer, sheet_name="Farm_Year_Data", index=False)
    fe.reset_index().rename(columns={"index": "term"}).to_excel(
        writer, sheet_name="Fixed_Effects", index=False)
    re.to_excel(writer, sheet_name="Random_Effects", index=False)

    # Model summary as text
    summary_df = pd.DataFrame({
        "Metric": ["Log-likelihood", "AIC", "BIC",
                   "Var(farm intercept)", "Var(residual)", "ICC"],
        "Value":  [round(result.llf, 4), round(result.aic, 4), round(result.bic, 4),
                   round(var_farm, 4), round(var_resid, 4), round(icc, 4)]
    })
    summary_df.to_excel(writer, sheet_name="Model_Fit", index=False)

print(f"\n✓ Saved results: {out_excel}")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 1: Full fixed-effects table plot — Estimate, SE, CI, z, p-value
# ══════════════════════════════════════════════════════════════════════════════

# Clean labels for all terms including Intercept
def clean_label(term):
    term = str(term)
    term = term.replace("C(year_cat)[T.", "Year ")
    # Replace region term (e.g. "C(region_cat)[T.ZW]") with just "Region"
    import re as _re
    term = _re.sub(r"C\(region_cat\)\[T\.[^\]]+\]", "Region", term)
    term = term.replace("]", "")
    return term

all_fe = fe.copy()
all_fe.index = [clean_label(i) for i in all_fe.index]

def sig_stars(p):
    if p < 0.001: return "***"
    if p < 0.01:  return "**"
    if p < 0.05:  return "*"
    if p < 0.1:   return "."
    return "n.s."

all_fe["stars"] = all_fe["p-value"].apply(sig_stars)

n_terms = len(all_fe)
row_colors = ["#f0f4ff", "#ffffff"] * (n_terms // 2 + 1)
row_colors = row_colors[:n_terms]

# Color rows by factor group
group_colors = []
for label in all_fe.index:
    if label == "Intercept":
        group_colors.append("#e8f5e9")   # light green
    elif "Year" in label:
        group_colors.append("#e3f2fd")   # light blue
    elif "Region" in label:
        group_colors.append("#fff3e0")   # light orange
    else:
        group_colors.append("#fce4ec")   # light red

fig, (ax_forest, ax_table) = plt.subplots(
    2, 1,
    figsize=(14, max(10, n_terms * 1.8 + 4)),
    gridspec_kw={"height_ratios": [1, 1]},
)
fig.subplots_adjust(hspace=0.55)

# ── Left panel: forest plot ───────────────────────────────────────────────────
y_pos = np.arange(n_terms)
bar_colors = []
for label in all_fe.index:
    if label == "Intercept":      bar_colors.append("#4caf50")
    elif "Year" in label:         bar_colors.append("#1f77b4")
    elif "Region" in label:       bar_colors.append("#ff7f0e")
    else:                         bar_colors.append("#9c27b0")

ax_forest.barh(
    y_pos, all_fe["Estimate"],
    xerr=[all_fe["Estimate"] - all_fe["CI_low"],
          all_fe["CI_high"] - all_fe["Estimate"]],
    color=bar_colors, alpha=0.75, edgecolor="#333", linewidth=0.7,
    error_kw=dict(ecolor="#333333", lw=1.5, capsize=5)
)
ax_forest.axvline(0, color="black", lw=1.2, linestyle="--", alpha=0.5)

# Add significance star next to each bar
for i, (_, row) in enumerate(all_fe.iterrows()):
    xpos = row["CI_high"] + 0.03 if row["Estimate"] >= 0 else row["CI_low"] - 0.03
    ha   = "left" if row["Estimate"] >= 0 else "right"
    color = "red" if row["stars"] not in ("n.s.",) else "#888"
    ax_forest.text(xpos, i, row["stars"], va="center", ha=ha,
                   fontsize=14, color=color, fontweight="bold")

ax_forest.set_yticks(y_pos)
ax_forest.set_yticklabels(all_fe.index, fontsize=14)
ax_forest.tick_params(axis="x", labelsize=13)
ax_forest.invert_yaxis()
ax_forest.set_xlabel("Estimate  (95% CI)", fontsize=15, fontweight="bold")
ax_forest.set_title("Fixed Effects at Farm Level", fontsize=16, fontweight="bold")
ax_forest.grid(axis="x", alpha=0.3)

legend_handles = [
    mpatches.Patch(facecolor="#4caf50", alpha=0.75, label="Intercept"),
    mpatches.Patch(facecolor="#1f77b4", alpha=0.75, label="Year"),
    mpatches.Patch(facecolor="#ff7f0e", alpha=0.75, label="Region"),
]
ax_forest.legend(handles=legend_handles, fontsize=13, loc="lower right")

# ── Right panel: numeric table ────────────────────────────────────────────────
ax_table.axis("off")

col_labels = ["Term", "Estimate", "SE", "z", "p-value", "Sig.", "CI low", "CI high"]
table_data = []
for label, row in all_fe.iterrows():
    table_data.append([
        label,
        f"{row['Estimate']:.4f}",
        f"{row['SE']:.4f}",
        f"{row['z']:.3f}",
        "<0.001" if row['p-value'] < 0.001 else f"{row['p-value']:.4f}",
        row["stars"],
        f"{row['CI_low']:.4f}",
        f"{row['CI_high']:.4f}",
    ])

tbl = ax_table.table(
    cellText=table_data,
    colLabels=col_labels,
    cellLoc="center",
    loc="center",
    bbox=[0, 0, 1, 1]
)
tbl.auto_set_font_size(False)
tbl.set_fontsize(13)

# Style header
for j in range(len(col_labels)):
    tbl[0, j].set_facecolor("#37474f")
    tbl[0, j].set_text_props(color="white", fontweight="bold", fontsize=13)

# Style data rows
sig_col_idx = col_labels.index("Sig.")
pval_col_idx = col_labels.index("p-value")
for i, (label, _) in enumerate(all_fe.iterrows()):
    row_bg = group_colors[i]
    for j in range(len(col_labels)):
        tbl[i + 1, j].set_facecolor(row_bg)
        tbl[i + 1, j].set_text_props(fontsize=13)
    # Bold + red the significance column if significant
    stars_val = all_fe.iloc[i]["stars"]
    if stars_val != "n.s.":
        tbl[i + 1, sig_col_idx].set_text_props(color="red", fontweight="bold", fontsize=13)
    # Bold p-value if significant
    if all_fe.iloc[i]["p-value"] < 0.05:
        tbl[i + 1, pval_col_idx].set_text_props(fontweight="bold", fontsize=13)

# Column widths
col_widths = [0.22, 0.10, 0.08, 0.08, 0.10, 0.07, 0.10, 0.10]
for j, w in enumerate(col_widths):
    tbl.auto_set_column_width(j)

ax_table.set_title("Fixed Effects Table",
                   fontsize=16, fontweight="bold", pad=12)



plot1_path = OUT_DIR / "lme_fixed_effects_forest.png"
fig.savefig(plot1_path, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved: {plot1_path}")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 2: Random intercepts (caterpillar plot)
# ══════════════════════════════════════════════════════════════════════════════
fig, ax = plt.subplots(figsize=(10, 7), constrained_layout=True)

region_colors = {"DR": "#ff7f0e", "ZW": "#1f77b4"}
colors_re = [region_colors[r] for r in re["region"]]

y_pos2 = np.arange(len(re))
ax.barh(y_pos2, re["random_intercept"], color=colors_re, alpha=0.7,
        edgecolor="#333", linewidth=0.5)
ax.axvline(0, color="black", lw=1.2, linestyle="--", alpha=0.7)
ax.set_yticks(y_pos2)
ax.set_yticklabels(re["farm_id"], fontsize=9)
ax.set_xlabel("Random intercept (deviation from grand mean)", fontsize=12, fontweight="bold")
ax.set_title("Farm Random Intercepts — LME Model\n"
             "Positive = above-average performance; Negative = below-average",
             fontsize=13, fontweight="bold")
ax.grid(axis="x", alpha=0.3)
ax.invert_yaxis()

legend_elements2 = [
    mpatches.Patch(facecolor="#1f77b4", alpha=0.7, label="ZW farms"),
    mpatches.Patch(facecolor="#ff7f0e", alpha=0.7, label="DR farms"),
]
ax.legend(handles=legend_elements2, fontsize=10)

plot2_path = OUT_DIR / "lme_random_intercepts.png"
fig.savefig(plot2_path, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved: {plot2_path}")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 3: Observed vs predicted (model fit check)
# ══════════════════════════════════════════════════════════════════════════════
farm_year["predicted"] = result.fittedvalues
farm_year["residual"]  = result.resid

fig, axes = plt.subplots(1, 2, figsize=(12, 5), constrained_layout=True)

region_colors_scatter = [region_colors[r] for r in farm_year["region"]]

# Observed vs fitted
axes[0].scatter(farm_year["predicted"], farm_year["performance_score"],
                c=region_colors_scatter, alpha=0.6, edgecolors="#333", linewidths=0.4, s=50)
lim = [farm_year[["predicted", "performance_score"]].min().min() - 0.2,
       farm_year[["predicted", "performance_score"]].max().max() + 0.2]
axes[0].plot(lim, lim, "k--", lw=1, alpha=0.6)
axes[0].set_xlabel("Fitted values", fontsize=12, fontweight="bold")
axes[0].set_ylabel("Observed performance score", fontsize=12, fontweight="bold")
axes[0].set_title("Observed vs Fitted", fontsize=13, fontweight="bold")
axes[0].grid(alpha=0.3)

# Residuals vs fitted
axes[1].scatter(farm_year["predicted"], farm_year["residual"],
                c=region_colors_scatter, alpha=0.6, edgecolors="#333", linewidths=0.4, s=50)
axes[1].axhline(0, color="black", lw=1, linestyle="--", alpha=0.6)
axes[1].set_xlabel("Fitted values", fontsize=12, fontweight="bold")
axes[1].set_ylabel("Residuals", fontsize=12, fontweight="bold")
axes[1].set_title("Residuals vs Fitted", fontsize=13, fontweight="bold")
axes[1].grid(alpha=0.3)

for ax in axes:
    legend_elements3 = [
        mpatches.Patch(facecolor="#1f77b4", alpha=0.7, label="ZW"),
        mpatches.Patch(facecolor="#ff7f0e", alpha=0.7, label="DR"),
    ]
    ax.legend(handles=legend_elements3, fontsize=10)

plot3_path = OUT_DIR / "lme_model_fit_check.png"
fig.savefig(plot3_path, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved: {plot3_path}")

# ══════════════════════════════════════════════════════════════════════════════
# PLOT 4: Heatmap — Farm × Year performance score
# ══════════════════════════════════════════════════════════════════════════════
import seaborn as sns

# Pivot: rows = year, columns = farm_id, values = performance_score
pivot = farm_year.pivot_table(index="year", columns="farm_id", values="performance_score")

# Sort farms by region then by mean score (best at left)
farm_meta = farm_year.groupby("farm_id").agg(
    region=("region", "first"),
    mean_score=("performance_score", "mean")
).reset_index()
farm_meta = farm_meta.sort_values("mean_score", ascending=True)   # low → left, high → right
pivot = pivot[farm_meta["farm_id"]]

# Region annotation (DR / ZW)
region_order = farm_meta.set_index("farm_id")["region"]
region_palette = {"DR": "#ff7f0e", "ZW": "#1f77b4"}

n_farms = len(pivot.columns)
fig_width = max(10, n_farms * 0.55)
fig, ax_heat = plt.subplots(figsize=(fig_width, 8))
fig.subplots_adjust(left=0.06, right=0.92, top=0.88, bottom=0.30)

# Draw heatmap  (low score = green/left, high score = red/right → RdYlGn_r)
sns.heatmap(
    pivot,
    annot=True,
    fmt=".2f",
    cmap="coolwarm",
    vmin=1,
    vmax=5,
    linewidths=0.5,
    linecolor="#cccccc",
    annot_kws={"size": 11, "weight": "bold"},
    cbar_kws={"label": "Performance Score", "shrink": 0.6},
    ax=ax_heat
)

ax_heat.set_ylabel("Year", fontsize=13, fontweight="bold")
ax_heat.set_xlabel("")
ax_heat.set_title("Farm Performance Score by Year\n(blue = low score, red = high score; excl. sugar beet)",
                  fontsize=14, fontweight="bold", pad=12)
ax_heat.tick_params(axis="y", labelsize=12, rotation=0)
ax_heat.tick_params(axis="x", labelsize=11, rotation=90)

# Colour the x-axis tick labels by region
for tick_label in ax_heat.get_xticklabels():
    farm = tick_label.get_text()
    region = region_order.get(farm, "DR")
    tick_label.set_color(region_palette[region])
    tick_label.set_fontweight("bold")

# Colorbar label font
cbar = ax_heat.collections[0].colorbar
cbar.ax.tick_params(labelsize=11)
cbar.set_label("Performance Score", fontsize=12, fontweight="bold")

plot4_path = OUT_DIR / "lme_farm_year_heatmap.png"
fig.savefig(plot4_path, dpi=300, bbox_inches="tight")
plt.close(fig)
print(f"✓ Saved: {plot4_path}")
