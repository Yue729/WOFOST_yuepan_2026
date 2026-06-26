"""
Enrich Best_Worst_Fields with crop_registration_extra data.

Adds two new sheets to performance_scores_detailed_no_sugarbeet.xlsx:
  - Best_Worst_with_extra   : one row per field × year, all extra management columns included
  - Best_Worst_summary_extra: one row per field, summarised management practices (% irrigation,
                               cover crop use, soil cultivation type, straw removal)
"""

from pathlib import Path
import pandas as pd
from openpyxl import load_workbook

PERF_EXCEL   = Path("/Users/panyue/Desktop/final_data/2_yield_data/yield_plots_performance/performance_scores_detailed_no_sugarbeet.xlsx")
EXTRA_EXCEL  = Path("/Users/panyue/Desktop/final_data/1_crop_management_data/crop_registration_extra_combined.xlsx")


def clean_str(s):
    """Strip and lower a string; return NaN for missing."""
    if pd.isna(s):
        return pd.NA
    return str(s).strip().lower()


def main():
    # ── Load data ─────────────────────────────────────────────────────────────
    bw = pd.read_excel(PERF_EXCEL, sheet_name="Best_Worst_Fields")
    extra = pd.read_excel(EXTRA_EXCEL)

    # Normalise string columns in extra
    for col in ["irrigation_main_crop", "cover_crop", "soil_cultivation_type",
                "soil_cultivation_timing", "straw_cereal", "cover_crop_type",
                "cover_crop_succes"]:
        if col in extra.columns:
            extra[col] = extra[col].apply(clean_str)

    # Fix 'yes ' → 'yes', collapse tillage typos
    tillage_map = {
        "tillage ":          "tillage",
        "minimum tillage":   "minimum tillage",
        "miminium tillage":  "minimum tillage",
        "mimimum tillage":   "minimum tillage",
    }
    extra["soil_cultivation_type"] = extra["soil_cultivation_type"].replace(tillage_map)
    extra["cover_crop"] = extra["cover_crop"].str.strip()

    extra["ID_field"] = extra["ID_field"].astype(str).str.strip()
    bw["ID_field"]    = bw["ID_field"].astype(str).str.strip()

    # ── Sheet 1: Best_Worst_with_extra ───────────────────────────────────────
    # Join on ID_field (all years of extra data for each best/worst field)
    detail_cols_from_bw = ["category", "rank", "ID_field", "region", "farm_id",
                           "avg_score", "avg_gap_t_ha", "avg_relative_gap_%", "n_records"]
    detail_cols_from_bw = [c for c in detail_cols_from_bw if c in bw.columns]

    extra_drop = ["source_farm", "ID_all", "ID_farm"]   # redundant with bw columns
    extra_keep = [c for c in extra.columns if c not in extra_drop]

    merged = bw[detail_cols_from_bw].merge(
        extra[extra_keep],
        on="ID_field",
        how="left"
    )
    # Sort: category (Best first), rank, year
    cat_order = {"Best": 0, "Worst": 1}
    merged["_cat_order"] = merged["category"].map(cat_order)
    merged = merged.sort_values(["_cat_order", "rank", "year"]).drop(columns=["_cat_order"])
    merged = merged.reset_index(drop=True)

    print(f"Best_Worst_with_extra: {len(merged)} rows")

    # ── Sheet 2: Best_Worst_summary_extra ────────────────────────────────────
    def pct_yes(series):
        s = series.dropna()
        if len(s) == 0:
            return pd.NA
        return round((s == "yes").sum() / len(s) * 100, 0)

    def most_common(series):
        s = series.dropna()
        return s.mode().iloc[0] if len(s) > 0 else pd.NA

    # Aggregate extra per field
    agg = extra.groupby("ID_field").agg(
        years_in_extra        =("year", lambda x: ", ".join(str(y) for y in sorted(x.dropna().astype(int)))),
        crops_grown           =("crop", lambda x: ", ".join(sorted(set(str(v).strip() for v in x.dropna())))),
        irrigation_pct        =("irrigation_main_crop", pct_yes),
        cover_crop_pct        =("cover_crop", pct_yes),
        cover_crop_types      =("cover_crop_type", lambda x: ", ".join(sorted(set(str(v) for v in x.dropna() if v not in ("not_app", "nan"))))),
        soil_cultivation_type =("soil_cultivation_type", most_common),
        soil_cultivation_timing=("soil_cultivation_timing", most_common),
        straw_removed_pct     =("straw_cereal", lambda x: round((x.dropna() == "removed").sum() / max(len(x.dropna()), 1) * 100, 0)),
    ).reset_index()

    summary = bw[detail_cols_from_bw].merge(agg, on="ID_field", how="left")
    cat_order2 = {"Best": 0, "Worst": 1}
    summary["_cat_order"] = summary["category"].map(cat_order2)
    summary = summary.sort_values(["_cat_order", "rank"]).drop(columns=["_cat_order"])
    summary = summary.reset_index(drop=True)

    print(f"Best_Worst_summary_extra: {len(summary)} rows")

    # ── Append sheets to existing Excel (preserve existing sheets) ───────────
    with pd.ExcelWriter(PERF_EXCEL, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        merged.to_excel(writer,  sheet_name="Best_Worst_with_extra",    index=False)
        summary.to_excel(writer, sheet_name="Best_Worst_summary_extra", index=False)

    print(f"\n✓ Added 2 new sheets to: {PERF_EXCEL}")

    # ── Quick preview ─────────────────────────────────────────────────────────
    print("\n── Summary preview (Best fields) ──")
    print(summary[summary["category"] == "Best"][
        ["rank", "ID_field", "avg_score", "avg_relative_gap_%",
         "irrigation_pct", "cover_crop_pct", "soil_cultivation_type", "crops_grown"]
    ].head(10).to_string(index=False))

    print("\n── Summary preview (Worst fields) ──")
    print(summary[summary["category"] == "Worst"][
        ["rank", "ID_field", "avg_score", "avg_relative_gap_%",
         "irrigation_pct", "cover_crop_pct", "soil_cultivation_type", "crops_grown"]
    ].head(10).to_string(index=False))


if __name__ == "__main__":
    main()
