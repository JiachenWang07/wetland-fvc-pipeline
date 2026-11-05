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
    }
    missing = sorted(name for name in required if not (analysis / name).is_file())
    if missing:
        raise AssertionError(f"missing canonical analysis tables: {missing}")
    for region in REGIONS:
        left = pd.read_csv(analysis / f"{region}_WetlandTransitionStructure.csv")
        right = pd.read_csv(DATA / "transition" / f"{region}_WetlandTransitionStructure.csv")
        if not left.equals(right):
            raise AssertionError(f"{region}: transition table copies differ")


def main() -> None:
    validate_regional()
    validate_city()
    validate_derived()
    print("Repository validation passed: reviewed public-data contract is consistent.")


if __name__ == "__main__":
    main()
