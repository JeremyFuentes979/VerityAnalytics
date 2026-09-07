import os
import json
import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
import sys

def run_analysis(session_dir):
    profile_path = os.path.join(session_dir, 'profile.json')
    if not os.path.exists(profile_path):
        print(f"Error: profile.json not found in {session_dir}")
        return

    with open(profile_path, 'r') as f:
        profile = json.load(f)

    # Find the data file
    data_file = profile.get('raw_data_file')
    candidate_paths = []
    if data_file:
        candidate_paths.extend([
            os.path.join(session_dir, data_file),
            os.path.join(session_dir, 'raw', data_file),
            os.path.join(session_dir, 'raw', os.path.basename(data_file)),
        ])

    if not data_file:
        # Fallback: look for csv or xlsx files
        files = [f for f in os.listdir(session_dir) if f.endswith(('.csv', '.xlsx', '.xls'))]
        if not files:
            raw_files = [f for f in os.listdir(os.path.join(session_dir, 'raw')) if f.endswith(('.csv', '.xlsx', '.xls'))] if os.path.isdir(os.path.join(session_dir, 'raw')) else []
            if not raw_files:
                print(f"Error: No data file found in {session_dir}")
                return
            files = raw_files
        candidate_paths = [os.path.join(session_dir, f) for f in files] + [os.path.join(session_dir, 'raw', f) for f in files]

    data_path = None
    for candidate in candidate_paths:
        if os.path.exists(candidate):
            data_path = candidate
            break

    if data_path is None:
        print(f"Error: Data file not found for session {session_dir}")
        return
    
    # Load data
    print(f"Loading data from {data_path}...")
    if data_file.endswith('.csv'):
        df = pd.read_csv(data_path)
    else:
        df = pd.read_excel(data_path)

    analysis = {
        "summary": {},
        "correlations": {},
        "anomalies": [],
        "hypotheses": [],
        "key_metrics": {},
        "patterns": [],
        "recommendations": [],
        "data_quality": {}
    }

    # Basic stats
    analysis["summary"]["row_count"] = len(df)
    analysis["summary"]["col_count"] = len(df.columns)
    analysis["key_metrics"]["row_count"] = len(df)
    analysis["key_metrics"]["col_count"] = len(df.columns)
    
    # Numeric analysis
    numeric_df = df.select_dtypes(include=[np.number])
    if not numeric_df.empty:
        # Correlations
        corr = numeric_df.corr().to_dict()
        analysis["correlations"] = corr
        analysis["key_metrics"]["numeric_columns"] = list(numeric_df.columns)

        # Anomaly detection (Isolation Forest)
        # Drop rows with NaNs for IF
        clean_numeric = numeric_df.dropna()
        if not clean_numeric.empty:
            model = IsolationForest(contamination=0.05, random_state=42)
            preds = model.fit_predict(clean_numeric)
            anomalies = clean_numeric[preds == -1]

            for idx, row in anomalies.iterrows():
                analysis["anomalies"].append({
                    "row_index": int(idx),
                    "reason": "Statistical outlier (Isolation Forest)",
                    "values": row.to_dict(),
                    "field": row.index[0] if len(row) > 0 else "unknown",
                    "severity": "medium"
                })

    # Hypotheses generation
    # 1. Check for potential duplicates
    duplicates = df[df.duplicated(keep=False)]
    if not duplicates.empty:
        # Group duplicates to show them together
        dup_indices = duplicates.index.tolist()
        analysis["hypotheses"].append({
            "type": "DUPLICATE_ROWS",
            "count": len(duplicates),
            "description": "Found rows with identical values. Auditor should verify if these are genuine duplicates.",
            "affected_indices": dup_indices
        })
        analysis["data_quality"]["duplicate_rows"] = len(duplicates)

    # 2. Check for inconsistent categories (case sensitivity, trailing spaces)
    cat_cols = df.select_dtypes(include=['object', 'string']).columns
    for col in cat_cols:
        unique_vals = df[col].dropna().unique()
        if len(unique_vals) > 1 and len(unique_vals) < 100: # Only check columns with reasonable number of categories
            normalized_vals = [str(v).strip().lower() for v in unique_vals]
            if len(set(normalized_vals)) < len(unique_vals):
                analysis["hypotheses"].append({
                    "type": "INCONSISTENT_CATEGORIES",
                    "column": col,
                    "description": f"Potential inconsistent naming in column '{col}'. Multiple variations of the same name may exist.",
                    "examples": [str(v) for v in unique_vals[:10]]
                })
                analysis["data_quality"].setdefault("category_issues", []).append({
                    "column": col,
                    "examples": [str(v) for v in unique_vals[:10]]
                })

    # 3. Trends (if date column exists)
    for col in df.columns:
        if 'date' in col.lower() or 'time' in col.lower():
            try:
                temp_dates = pd.to_datetime(df[col], errors='coerce')
                if temp_dates.notna().any():
                    analysis["summary"]["time_period"] = {
                        "column": col,
                        "start": str(temp_dates.min()),
                        "end": str(temp_dates.max())
                    }
                break
            except:
                pass

    if not analysis["recommendations"]:
        analysis["recommendations"] = [{
            "source": "Analyst",
            "recommendation": "Review duplicate rows and inconsistent categorical values before publishing any result."
        }]
    if not analysis["patterns"]:
        analysis["patterns"] = [
            "No strong pattern detected beyond basic data quality checks.",
            "Validate subject-matter context before accepting the current summary as final."
        ]
    if not analysis["data_quality"]:
        analysis["data_quality"] = {
            "status": "No material quality issues detected in the current dataset.",
            "missing_values": int(df.isnull().sum().sum())
        }

    # Save analysis.json
    output_path = os.path.join(session_dir, 'analysis.json')
    with open(output_path, 'w') as f:
        json.dump(analysis, f, indent=2, default=str)

    print(f"Analysis complete. Results saved to {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyst.py <session_dir>")
    else:
        run_analysis(sys.argv[1])
