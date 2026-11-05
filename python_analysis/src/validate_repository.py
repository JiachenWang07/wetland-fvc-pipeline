"""Validate the committed Stage 5 public-data contract."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "outputs" / "stage5_final"
REGIONS = ("YRD", "GBA", "BTH")


def require_columns(frame: pd.DataFrame, columns: set[str], label: str) -> None:
    missing = columns.difference(frame.columns)
    if missing:
        raise AssertionError(f"{label}: missing columns {sorted(missing)}")


def validate_regional() -> None:
    for region in REGIONS:
        path = DATA / f"Stage5_Final_Regional30m_36Years_{region}.csv"
        frame = pd.read_csv(path)
        require_columns(frame, {"region", "year", "fvc_mean_area_weighted"}, path.name)
        if frame["year"].tolist() != list(range(1985, 2021)):
            raise AssertionError(f"{path.name}: expected ordered years 1985–2020")
        if set(frame["region"].dropna()) != {region}:
            raise AssertionError(f"{path.name}: region mismatch")
        if not frame["fvc_mean_area_weighted"].dropna().between(0, 1).all():
            raise AssertionError(f"{path.name}: FVC outside [0, 1]")
        first = frame.loc[frame["year"] == 1985, "fvc_mean_area_weighted"].iloc[0]
        if region == "GBA" and pd.notna(first):
            raise AssertionError("GBA 1985 must remain missing")


def validate_city() -> None:
    path = DATA / "Stage5_QA_City_FVC_8Nodes_30m.csv"
    frame = pd.read_csv(path)
    require_columns(frame, {"region", "name", "year", "fvc_mean_area_weighted", "valid_fraction"}, path.name)
    if set(frame["region"].dropna()) != set(REGIONS):
        raise AssertionError(f"{path.name}: unexpected region set")
    if frame["name"].nunique() != 64:
        raise AssertionError(f"{path.name}: expected 64 unique city names")
    for column in ("fvc_mean_area_weighted", "valid_fraction"):
        if not frame[column].dropna().between(0, 1).all():
            raise AssertionError(f"{path.name}: {column} outside [0, 1]")


def validate_derived() -> None:
    analysis = DATA / "analysis"
    required = {
        "regional_trends_mk_tfpw.csv",
        "city_endpoint_direction_agreement_summary.csv",
        "city_area_fvc_change_qc50.csv",
        "breakpoint_sensitivity_2011_2015.csv",
        "leave_one_year_out_trends.csv",
        "leave_one_year_out_summary.csv",
    }
    missing = sorted(name for name in required if not (analysis / name).is_file())
    if missing:
        raise AssertionError(f"missing canonical analysis tables: {missing}")
    for region in REGIONS:
        left = pd.read_csv(analysis / f"{region}_WetlandTransitionStructure.csv")
        right = pd.read_csv(DATA / "transition" / f"{region}_WetlandTransitionStructure.csv")
        if not left.equals(right):
            raise AssertionError(f"{region}: transition table copies differ")
    breakpoint = pd.read_csv(analysis / "breakpoint_sensitivity_2011_2015.csv")
    leave_one_out = pd.read_csv(analysis / "leave_one_year_out_summary.csv")
    if len(breakpoint) != 30:
        raise AssertionError("breakpoint sensitivity: expected 30 region/segment/breakpoint rows")
    if len(leave_one_out) != 6:
        raise AssertionError("leave-one-year-out summary: expected six region/period rows")
    if not leave_one_out["direction_agreement_share"].between(0, 1).all():
        raise AssertionError("leave-one-year-out direction agreement outside [0, 1]")


def validate_documented_findings() -> None:
    """Recompute the headline numeric claims from their canonical tables."""
    scale = pd.read_csv(DATA / "Stage5_QA_Scale_30_100_250_500m.csv")
    base = scale.loc[scale["scale_m"] == 30, ["region", "year", "fvc_mean_area_weighted"]]
    base = base.rename(columns={"fvc_mean_area_weighted": "fvc_30"})
    coarse = scale.loc[scale["scale_m"] == 500, ["region", "year", "fvc_mean_area_weighted"]]
    coarse = coarse.rename(columns={"fvc_mean_area_weighted": "fvc_500"})
    paired = base.merge(coarse, on=["region", "year"]).dropna()
    differences = (paired["fvc_30"] - paired["fvc_500"]).abs()
    if len(differences) != 14:
        raise AssertionError("scale comparison: expected 14 valid 30 m versus 500 m pairs")
    if abs(differences.mean() - 0.02238313635922321) > 1e-12:
        raise AssertionError("scale comparison: documented mean absolute difference changed")
    if abs(differences.max() - 0.058985434804979586) > 1e-12:
        raise AssertionError("scale comparison: documented maximum difference changed")

    agreement = pd.read_csv(DATA / "analysis" / "city_endpoint_direction_agreement_summary.csv")
    all_qc50 = agreement[(agreement["scenario"] == "qc50") & (agreement["region"] == "ALL")]
    if len(all_qc50) != 1:
        raise AssertionError("endpoint agreement: expected one qc50/ALL summary row")
    row = all_qc50.iloc[0]
    expected = {
        "cities": 64,
        "direction_consistent": 48,
        "direction_flips": 16,
        "direction_consistency_share": 0.75,
        "fixed_tfpw_fdr_sig": 0,
        "dynamic_tfpw_fdr_sig": 0,
    }
    for column, value in expected.items():
        if row[column] != value:
            raise AssertionError(f"endpoint agreement: documented {column} changed")


def main() -> None:
    validate_regional()
    validate_city()
    validate_derived()
    validate_documented_findings()
    print("Repository validation passed: reviewed public-data contract is consistent.")


if __name__ == "__main__":
    main()
