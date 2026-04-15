import os
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


RAW_DATA_PATH = Path("/Users/panyue/Desktop/final_data")
PROJECT_ROOT = Path(__file__).resolve().parent


def resolve_existing_path(label, *candidates):
    for candidate in candidates:
        path = Path(candidate)
        if path.exists() and not path.name.startswith("~$"):
            return path
    checked = "\n".join(f"- {Path(candidate)}" for candidate in candidates)
    raise FileNotFoundError(f"Could not find {label}. Checked:\n{checked}")


pp_path = resolve_existing_path(
    "PP results workbook",
    RAW_DATA_PATH / "WOFOST73_PP_results.xlsx",
    RAW_DATA_PATH / "2_yield_data" / "WOFOST73_PP_results.xlsx",
    PROJECT_ROOT / "output" / "model_results" / "WOFOST73_PP_results.xlsx",
    PROJECT_ROOT / "output" / "model_results" / "WOFOST81_PP_results.xlsx",
)
wlp_path = resolve_existing_path(
    "WLP results workbook",
    RAW_DATA_PATH / "WOFOST72_WLP_FD_results.xlsx",
    RAW_DATA_PATH / "2_yield_data" / "WOFOST72_WLP_FD_results.xlsx",
    RAW_DATA_PATH / "2_yield_data" / "WOFOST_WLP_FD_results.xlsx",
    PROJECT_ROOT / "output" / "model_results" / "WOFOST72_WLP_FD_results.xlsx",
    PROJECT_ROOT / "output" / "model_results" / "WOFOST_WLP_FD_results.xlsx",
)
yield_dir = RAW_DATA_PATH / "2_yield_data" / "yield_data_2025"
out_path = RAW_DATA_PATH / "wofost_yield_merged_2025.xlsx"
plot_dir = RAW_DATA_PATH / "2_yield_data" / "yield_plots_2025"

yield_files = {
    "sugarbeet": yield_dir / "yield_sugar_beet_2025.xlsx",
    "potato": yield_dir / "yield_potato_2025.xlsx",
    "cereal": yield_dir / "yield_cereal_2025.xlsx",
    "onion": yield_dir / "yield_onion_2025.xlsx",
}

crop_groups = {
    "sugarbeet": {"sugarbeet"},
    "potato": {"potato"},
    "cereal": {"wheat", "barley"},
    "onion": {"seed_onion"},
}

cereal_subgroups = {
    "wheat": {"wheat"},
    "barley": {"barley"},
}

measured_yield_columns = {
    ("sugarbeet", "Sheet1"): "Average net fresh yield (t/ha)",
    ("potato", "Sheet1"): "Average net fresh yield (t/ha)",
    ("cereal", "Grain"): "Average dry matter yield grain (t/ha)",
    ("cereal", "straw"): "Average dry matter yield straw (t/ha)",
    ("onion", "Sheet1"): "Net average fresh yield (t/ha)",
}

def normalize_crop(value):
    if pd.isna(value):
        return np.nan
    s = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "spring_barley": "barley",
        "winter_barley": "barley",
        "barley": "barley",
        "spring_wheat": "wheat",
        "winter_wheat": "wheat",
        "wheat": "wheat",
        "sugar_beet": "sugarbeet",
        "sugarbeet": "sugarbeet",
        "potato": "potato",
        "seed_onion": "seed_onion",
        "onion": "seed_onion",
    }
    return mapping.get(s, s)

def prep_results(path, prefix):
    df = pd.read_excel(path).copy()

    df["year_key"] = pd.to_datetime(df["year"], errors="coerce").dt.year.astype("Int64").astype(str)
    mask = df["year_key"] == "<NA>"
    if mask.any():
        df.loc[mask, "year_key"] = df.loc[mask, "year"].astype(str).str.extract(r"(\d{4})", expand=False)

    df["field_key"] = df["field_id"].astype(str).str.strip()
    df["crop_norm"] = df["crop_name"].map(normalize_crop)

    rename = {c: f"{prefix}_{c}" for c in df.columns if c not in ("year_key", "field_key")}
    return df.rename(columns=rename)

def prep_yield_sheet(path, sheet_name):
    df = pd.read_excel(path, sheet_name=sheet_name).copy()

    field_col = "field_ID" if "field_ID" in df.columns else ("ID_field" if "ID_field" in df.columns else None)
    if field_col is None:
        raise ValueError(f"No field ID column found in {path} / {sheet_name}")

    df["year_key"] = pd.to_datetime(df["Measurement_date"], errors="coerce").dt.year.astype("Int64").astype(str)
    df["field_key"] = df[field_col].astype(str).str.strip()

    if "Crop" in df.columns:
        df["yield_crop_norm"] = df["Crop"].map(normalize_crop)

    return df


def filter_results_by_crop(df, crops, prefix):
    crop_col = f"{prefix}_crop_norm"
    return df[df[crop_col].isin(crops)].copy()


def merge_yield_with_results(ydf, pp, wlp, crops):
    pp_filtered = filter_results_by_crop(pp, crops, "PP")
    wlp_filtered = filter_results_by_crop(wlp, crops, "WLP")

    merged = ydf.merge(pp_filtered, on=["year_key", "field_key"], how="left")
    merged = merged.merge(wlp_filtered, on=["year_key", "field_key"], how="left")

    if "yield_crop_norm" in merged.columns:
        merged["PP_crop_match"] = np.where(
            merged["PP_crop_norm"].isna(),
            np.nan,
            merged["yield_crop_norm"] == merged["PP_crop_norm"]
        )
        merged["WLP_crop_match"] = np.where(
            merged["WLP_crop_norm"].isna(),
            np.nan,
            merged["yield_crop_norm"] == merged["WLP_crop_norm"]
        )

    return merged


def get_sheet_tasks(label, sheet_name, ydf):
    if label != "cereal":
        return [(label, sheet_name, crop_groups[label], ydf)]

    tasks = []
    for subgroup_label, subgroup_crops in cereal_subgroups.items():
        subset = ydf[ydf["yield_crop_norm"].isin(subgroup_crops)].copy()
        if not subset.empty:
            tasks.append((f"cereal_{subgroup_label}", sheet_name, subgroup_crops, subset))
    return tasks


def get_measured_yield_column(label, sheet_name):
    base_label = "cereal" if label.startswith("cereal_") else label
    key = (base_label, sheet_name)
    if key not in measured_yield_columns:
        raise KeyError(f"No measured yield column configured for {label} / {sheet_name}")
    return measured_yield_columns[key]


def get_simulated_yield_t_ha(df, prefix, label, sheet_name):
    if label.startswith("cereal") and sheet_name.lower() == "straw":
        series = df[f"{prefix}_TWLV"].fillna(0) + df[f"{prefix}_TWST"].fillna(0)
    else:
        series = df[f"{prefix}_TWSO"]
    return pd.to_numeric(series, errors="coerce") / 1000.0


def build_plot_frame(merged, label, sheet_name):
    measured_col = get_measured_yield_column(label, sheet_name)

    plot_df = merged.copy()
    plot_df["actual_yield_t_ha"] = pd.to_numeric(plot_df[measured_col], errors="coerce")
    plot_df["PP_yield_t_ha"] = get_simulated_yield_t_ha(plot_df, "PP", label, sheet_name)
    plot_df["WLP_yield_t_ha"] = get_simulated_yield_t_ha(plot_df, "WLP", label, sheet_name)

    plot_df = plot_df.dropna(subset=["actual_yield_t_ha", "PP_yield_t_ha", "WLP_yield_t_ha"]).copy()
    plot_df["WLP_yield_t_ha"] = plot_df[["WLP_yield_t_ha", "PP_yield_t_ha"]].min(axis=1)
    plot_df["actual_yield_t_ha"] = plot_df[["actual_yield_t_ha", "WLP_yield_t_ha"]].min(axis=1)

    plot_df["gap_other_t_ha"] = (plot_df["WLP_yield_t_ha"] - plot_df["actual_yield_t_ha"]).clip(lower=0)
    plot_df["gap_water_t_ha"] = (plot_df["PP_yield_t_ha"] - plot_df["WLP_yield_t_ha"]).clip(lower=0)
    plot_df["field_label"] = (
        plot_df["field_key"]
        .astype(str)
        .str.replace(r"[_-]?\d{4}$", "", regex=True)
    )

    plot_df = plot_df.sort_values(["year_key", "field_key"]).reset_index(drop=True)
    return plot_df


def plot_yield_comparison(plot_df, label, sheet_name):
    if plot_df.empty:
        return None

    x = np.arange(len(plot_df))
    actual = plot_df["actual_yield_t_ha"].to_numpy()
    gap_other = plot_df["gap_other_t_ha"].to_numpy()
    gap_water = plot_df["gap_water_t_ha"].to_numpy()
    wlp_yield = plot_df["WLP_yield_t_ha"].to_numpy()
    pp_yield = plot_df["PP_yield_t_ha"].to_numpy()

    denom = np.where(pp_yield > 0, pp_yield, np.nan)
    actual_pct = actual / denom * 100
    gap_other_pct = gap_other / denom * 100
    gap_water_pct = gap_water / denom * 100
    wlp_pct = wlp_yield / denom * 100

    width = max(14, len(plot_df) * 0.7)
    fig, axes = plt.subplots(1, 2, figsize=(width, 7), constrained_layout=True)

    colors = {
        "actual": "#5B88D7",
        "other": "#F6A21A",
        "water": "#F2E4CB",
    }

    axes[0].bar(x, actual, color=colors["actual"], edgecolor="#333333", label="Actual yield")
    axes[0].bar(
        x,
        gap_water + gap_other,
        bottom=np.minimum(actual, wlp_yield),
        color=colors["water"],
        edgecolor="#333333",
        label="Gap to PP",
    )
    axes[0].plot(
        x,
        wlp_yield,
        linestyle=":",
        linewidth=2.0,
        marker="o",
        markersize=4.5,
        color="#C77600",
        label="WLP yield",
        zorder=4,
    )
    axes[0].set_ylabel("Yield and yield gap (t ha$^{-1}$)")
    axes[0].set_title("Absolute yield")

    axes[1].bar(x, actual_pct, color=colors["actual"], edgecolor="#333333", label="Actual yield")
    axes[1].bar(
        x,
        gap_water_pct + gap_other_pct,
        bottom=np.minimum(actual_pct, wlp_pct),
        color=colors["water"],
        edgecolor="#333333",
        label="Yield gap: PP - WLP",
    )
    axes[1].plot(
        x,
        wlp_pct,
        linestyle=":",
        linewidth=2.0,
        marker="o",
        markersize=4.5,
        color="#C77600",
        label="WLP yield",
        zorder=4,
    )
    axes[1].set_ylabel("Share of PP yield (%)")
    axes[1].set_ylim(0, 100)
    axes[1].set_title("Relative to PP")

    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(plot_df["field_label"], rotation=55, ha="right")
        ax.tick_params(axis="x", labelsize=9, pad=6)
        ax.margins(x=0.02)
        ax.grid(axis="y", alpha=0.25)
        ax.set_axisbelow(True)

    pretty_sheet = "grain" if sheet_name.lower() == "grain" else sheet_name.lower()
    fig.suptitle(f"{label.capitalize()} {pretty_sheet}: actual vs WLP vs PP", fontsize=14)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=3, frameon=False)

    safe_sheet = sheet_name.lower().replace(" ", "_")
    plot_path = plot_dir / f"{label}_{safe_sheet}_yield_comparison.png"
    fig.savefig(plot_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    return plot_path

def main():
    pp = prep_results(pp_path, "PP")
    wlp = prep_results(wlp_path, "WLP")
    plot_dir.mkdir(parents=True, exist_ok=True)
    plot_paths = []

    with pd.ExcelWriter(out_path, engine="openpyxl") as writer:
        for label, path in yield_files.items():
            if not os.path.exists(path):
                continue

            xls = pd.ExcelFile(path)
            for sheet_name in xls.sheet_names:
                ydf = prep_yield_sheet(path, sheet_name)
                for task_label, task_sheet_name, crops, task_df in get_sheet_tasks(label, sheet_name, ydf):
                    merged = merge_yield_with_results(task_df, pp, wlp, crops)

                    out_sheet = f"{task_label[:12]}_{task_sheet_name[:18]}"
                    merged.to_excel(writer, sheet_name=out_sheet, index=False)

                    plot_df = build_plot_frame(merged, task_label, task_sheet_name)
                    plot_path = plot_yield_comparison(plot_df, task_label, task_sheet_name)
                    if plot_path is not None:
                        plot_paths.append(plot_path)

    print(f"Written: {out_path}")
    for plot_path in plot_paths:
        print(f"Saved plot: {plot_path}")


if __name__ == "__main__":
    main()
