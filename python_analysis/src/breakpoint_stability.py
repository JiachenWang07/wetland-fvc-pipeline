"""Offline breakpoint and leave-one-year-out stability checks for Stage 5 FVC."""
from __future__ import annotations

import math
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs" / "stage5_final"
OUT = DATA / "analysis"
FIG = ROOT / "docs" / "assets" / "publication" / "breakpoint_stability.png"
REGIONS = ("YRD", "GBA", "BTH")
BREAK_YEARS = range(2011, 2016)


def sen_slope(series: list[tuple[int, float]]) -> float:
    slopes = sorted(
        (b[1] - a[1]) / (b[0] - a[0])
        for index, a in enumerate(series) for b in series[index + 1:]
    )
    middle = len(slopes) // 2
    return slopes[middle] if len(slopes) % 2 else (slopes[middle - 1] + slopes[middle]) / 2


def mann_kendall(series: list[tuple[int, float]]) -> tuple[float, float]:
    values = [value for _, value in series]
    n = len(values)
    score = sum(
        (values[j] > values[i]) - (values[j] < values[i])
        for i in range(n - 1) for j in range(i + 1, n)
    )
    counts = Counter(values)
    variance = (
        n * (n - 1) * (2 * n + 5)
        - sum(count * (count - 1) * (2 * count + 5) for count in counts.values() if count > 1)
    ) / 18
    z = (score - 1) / math.sqrt(variance) if score > 0 else (score + 1) / math.sqrt(variance) if score < 0 else 0
    return z, math.erfc(abs(z) / math.sqrt(2))


def tfpw(series: list[tuple[int, float]]) -> tuple[float, float, float]:
    slope = sen_slope(series)
    first_year = series[0][0]
    residuals = [value - slope * (year - first_year) for year, value in series]
    mean = sum(residuals) / len(residuals)
    denominator = sum((value - mean) ** 2 for value in residuals)
    rho = (
        sum((residuals[i] - mean) * (residuals[i - 1] - mean) for i in range(1, len(residuals))) / denominator
        if denominator else 0
    )
    rho = max(-0.99, min(0.99, rho))
    whitened = [
        (series[i][0], residuals[i] - rho * residuals[i - 1] + slope * (series[i][0] - first_year))
        for i in range(1, len(series))
    ]
    z, p = mann_kendall(whitened)
    return rho, z, p


def test(series: list[tuple[int, float]]) -> dict:
    slope = sen_slope(series)
    rho, z, p = tfpw(series)
    return {
        "n_years": len(series), "sen_slope": slope,
        "direction": "up" if slope > 0 else "down" if slope < 0 else "flat",
        "lag1_detrended": rho, "tfpw_z": z, "tfpw_p": p,
    }


def load_region(region: str) -> list[tuple[int, float]]:
    frame = pd.read_csv(DATA / f"Stage5_Final_Regional30m_36Years_{region}.csv")
    frame = frame.dropna(subset=["fvc_mean_area_weighted"]).sort_values("year")
    return list(zip(frame["year"].astype(int), frame["fvc_mean_area_weighted"].astype(float)))


def analyze() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    breakpoint_rows, loo_rows = [], []
    for region in REGIONS:
        series = load_region(region)
        for breakpoint in BREAK_YEARS:
            segments = {
                "before": [item for item in series if item[0] < breakpoint],
                "after": [item for item in series if item[0] >= breakpoint],
            }
            for segment, subset in segments.items():
                breakpoint_rows.append({"region": region, "break_year": breakpoint, "segment": segment, **test(subset)})

        official = {
            "1985-2012": [item for item in series if item[0] < 2013],
            "2013-2020": [item for item in series if item[0] >= 2013],
        }
        for period, subset in official.items():
            baseline = test(subset)
            for omitted_year, _ in subset:
                reduced = [item for item in subset if item[0] != omitted_year]
                loo_rows.append({
                    "region": region, "period": period, "omitted_year": omitted_year,
                    "baseline_direction": baseline["direction"], "baseline_tfpw_p": baseline["tfpw_p"],
                    **test(reduced),
                })

    breakpoints = pd.DataFrame(breakpoint_rows)
    loo = pd.DataFrame(loo_rows)
    summaries = []
    for (region, period), group in loo.groupby(["region", "period"]):
        summaries.append({
            "region": region, "period": period, "leave_one_out_runs": len(group),
            "direction_agreement_share": (group["direction"] == group["baseline_direction"]).mean(),
            "significant_share_tfpw_p_lt_0_05": (group["tfpw_p"] < 0.05).mean(),
            "sen_slope_min": group["sen_slope"].min(), "sen_slope_max": group["sen_slope"].max(),
            "tfpw_p_min": group["tfpw_p"].min(), "tfpw_p_max": group["tfpw_p"].max(),
        })
    return breakpoints, loo, pd.DataFrame(summaries)


def plot(breakpoints: pd.DataFrame) -> None:
    colors = {"YRD": "#2F6F6D", "GBA": "#B96D52", "BTH": "#526F8C"}
    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.8), sharex=True)
    for ax, segment in zip(axes, ("before", "after")):
        for region in REGIONS:
            data = breakpoints[(breakpoints["region"] == region) & (breakpoints["segment"] == segment)]
            ax.plot(data["break_year"], data["sen_slope"] * 1000, marker="o", lw=2, color=colors[region], label=region)
            sig = data["tfpw_p"] < 0.05
            ax.scatter(data.loc[sig, "break_year"], data.loc[sig, "sen_slope"] * 1000,
                       s=70, facecolors="none", edgecolors=colors[region], linewidths=1.5)
        ax.axhline(0, color="#6B7280", lw=.8)
        ax.axvline(2013, color="#111827", lw=.9, ls="--")
        ax.set_title("Years before breakpoint" if segment == "before" else "Years from breakpoint onward", loc="left", fontweight="bold")
        ax.set_xlabel("Candidate breakpoint year")
        ax.grid(axis="y", alpha=.18)
    axes[0].set_ylabel("Sen slope ×10⁻³ yr⁻¹")
    axes[0].legend(frameon=False, ncol=3)
    fig.suptitle("Regional trend sensitivity to the selected breakpoint", x=.07, ha="left", fontsize=16, fontweight="bold")
    fig.text(.07, .02, "Open rings indicate TFPW Mann–Kendall p < 0.05. This is a robustness diagnostic, not a data-derived breakpoint selection.", fontsize=8.8, color="#5B6662")
    fig.tight_layout(rect=(0, .06, 1, .92))
    FIG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(FIG, dpi=300, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main() -> None:
    breakpoints, loo, summary = analyze()
    OUT.mkdir(parents=True, exist_ok=True)
    breakpoints.to_csv(OUT / "breakpoint_sensitivity_2011_2015.csv", index=False)
    loo.to_csv(OUT / "leave_one_year_out_trends.csv", index=False)
    summary.to_csv(OUT / "leave_one_year_out_summary.csv", index=False)
    plot(breakpoints)
    print(summary.to_string(index=False))
    print(f"Generated offline robustness outputs in {OUT}")


if __name__ == "__main__":
    main()
