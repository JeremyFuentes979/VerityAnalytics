"""Analyst — exploratory analysis, anomaly detection and data-quality hypotheses.

Usage:
    python analyst.py <session-dir>

Reads  <session>/profile.json and the normalised data it points at (raw/data.csv)
Writes <session>/analysis.json
"""

import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from _shared.jsonio import read_json, write_json  # noqa: E402

MIN_ROWS_FOR_OUTLIERS = 20
MAX_ANOMALIES = 200


class AnalysisError(Exception):
    pass


def find_data_file(session_dir, profile):
    data_file = profile.get("raw_data_file")
    candidates = []
    if data_file:
        candidates += [
            os.path.join(session_dir, data_file),
            os.path.join(session_dir, "raw", os.path.basename(data_file)),
        ]
    raw_dir = os.path.join(session_dir, "raw")
    if os.path.isdir(raw_dir):
        candidates += [os.path.join(raw_dir, f) for f in sorted(os.listdir(raw_dir))
                       if f.endswith((".csv", ".xlsx", ".xls"))]
    candidates += [os.path.join(session_dir, f) for f in sorted(os.listdir(session_dir))
                   if f.endswith((".csv", ".xlsx", ".xls")) and f != "cleaned_data.csv"]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def load_frame(path):
    if path.endswith(".csv"):
        return pd.read_csv(path)
    return pd.read_excel(path)


def detect_outliers(numeric_df, analysis):
    clean = numeric_df.dropna()
    if len(clean) < MIN_ROWS_FOR_OUTLIERS:
        analysis["patterns"].append(
            f"Outlier detection skipped: needs at least {MIN_ROWS_FOR_OUTLIERS} complete numeric rows "
            f"(found {len(clean)})."
        )
        return

    from sklearn.ensemble import IsolationForest

    model = IsolationForest(contamination=0.05, random_state=42)
    preds = model.fit_predict(clean)
    flagged = clean[preds == -1]

    std = clean.std(ddof=0).replace(0, np.nan)
    zscores = ((flagged - clean.mean()) / std).abs().fillna(0)

    for idx, row in flagged.head(MAX_ANOMALIES).iterrows():
        field = zscores.loc[idx].idxmax()
        analysis["anomalies"].append({
            "row_index": int(idx),
            "reason": f"Statistical outlier (Isolation Forest); most unusual in '{field}'",
            "values": row.to_dict(),
            "field": str(field),
            "column": str(field),
            "severity": "medium",
        })
    if len(flagged) > MAX_ANOMALIES:
        analysis["patterns"].append(
            f"{len(flagged)} outliers detected; the first {MAX_ANOMALIES} are listed."
        )


def run_analysis(session_dir):
    profile = read_json(os.path.join(session_dir, "profile.json"))
    if profile is None:
        raise AnalysisError(f"profile.json not found in {session_dir}")

    data_path = find_data_file(session_dir, profile)
    if data_path is None:
        raise AnalysisError(f"No data file found for session {session_dir}")

    print(f"Loading data from {data_path}...")
    df = load_frame(data_path)

    analysis = {
        "summary": {},
        "correlations": {},
        "anomalies": [],
        "hypotheses": [],
        "key_metrics": {},
        "patterns": [],
        "recommendations": [],
        "data_quality": {},
    }

    analysis["summary"]["row_count"] = len(df)
    analysis["summary"]["col_count"] = len(df.columns)
    analysis["key_metrics"]["row_count"] = len(df)
    analysis["key_metrics"]["col_count"] = len(df.columns)

    numeric_df = df.select_dtypes(include=[np.number])
    if not numeric_df.empty:
        analysis["correlations"] = numeric_df.corr().to_dict()
        analysis["key_metrics"]["numeric_columns"] = list(numeric_df.columns)
        for col in numeric_df.columns:
            series = numeric_df[col].dropna()
            if len(series):
                analysis["key_metrics"][f"{col}_total"] = float(series.sum())
                analysis["key_metrics"][f"{col}_mean"] = float(series.mean())
        detect_outliers(numeric_df, analysis)

        negatives = {str(c): int((numeric_df[c] < 0).sum()) for c in numeric_df.columns if (numeric_df[c] < 0).any()}
        if negatives:
            analysis["data_quality"]["negative_values"] = negatives
            analysis["patterns"].append(
                "Negative values found in: " + ", ".join(f"{c} ({n})" for c, n in negatives.items())
                + ". These may be legitimate credits or refunds, so they are flagged for review, not changed."
            )

    # Hypothesis: duplicate rows
    duplicates = df[df.duplicated(keep=False)]
    if not duplicates.empty:
        analysis["hypotheses"].append({
            "type": "DUPLICATE_ROWS",
            "count": len(duplicates),
            "description": "Found rows with identical values. The Auditor verifies whether these are genuine duplicates.",
            "affected_indices": duplicates.index.tolist()[:1000],
        })
        analysis["data_quality"]["duplicate_rows"] = len(duplicates)

    # Hypothesis: inconsistent category spellings
    for col in df.select_dtypes(include=["object", "string"]).columns:
        unique_vals = df[col].dropna().unique()
        if 1 < len(unique_vals) < 100:
            normalized = {str(v).strip().lower() for v in unique_vals}
            if len(normalized) < len(unique_vals):
                examples = [str(v) for v in unique_vals[:10]]
                analysis["hypotheses"].append({
                    "type": "INCONSISTENT_CATEGORIES",
                    "column": col,
                    "description": f"Potential inconsistent naming in column '{col}'. Multiple variations of the same name may exist.",
                    "examples": examples,
                })
                analysis["data_quality"].setdefault("category_issues", []).append(
                    {"column": col, "examples": examples}
                )

    # Time period
    for col in df.columns:
        if "date" in col.lower() or "time" in col.lower():
            try:
                dates = pd.to_datetime(df[col], errors="coerce")
            except Exception:  # noqa: BLE001
                continue
            if dates.notna().any():
                analysis["summary"]["time_period"] = {
                    "column": col,
                    "start": str(dates.min()),
                    "end": str(dates.max()),
                }
                break

    missing = {str(c): int(n) for c, n in df.isnull().sum().items() if n}
    if missing:
        analysis["data_quality"]["missing_values_by_column"] = missing
    analysis["data_quality"]["missing_values"] = int(df.isnull().sum().sum())

    if not analysis["recommendations"]:
        analysis["recommendations"] = [{
            "source": "Analyst",
            "recommendation": "Review duplicate rows, inconsistent categories, missing values and negative amounts before relying on any result.",
        }]
    if not analysis["patterns"]:
        analysis["patterns"] = [
            "No strong pattern detected beyond basic data quality checks.",
            "Validate subject-matter context before accepting the current summary as final.",
        ]

    output_path = os.path.join(session_dir, "analysis.json")
    write_json(output_path, analysis)
    print(f"Analysis complete. Results saved to {output_path}")
    return analysis


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyst.py <session_dir>")
        return 1
    try:
        run_analysis(sys.argv[1])
    except AnalysisError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
