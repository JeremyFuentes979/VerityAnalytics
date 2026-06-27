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
    if not data_file:
        # Fallback: look for csv or xlsx files
        files = [f for f in os.listdir(session_dir) if f.endswith(('.csv', '.xlsx', '.xls'))]
        if not files:
            print(f"Error: No data file found in {session_dir}")
            return
        data_file = files[0]

    data_path = os.path.join(session_dir, data_file)
    
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
        "hypotheses": []
    }

    # Basic stats
    analysis["summary"]["row_count"] = len(df)
    analysis["summary"]["col_count"] = len(df.columns)
    
    # Numeric analysis
    numeric_df = df.select_dtypes(include=[np.number])
    if not numeric_df.empty:
        # Correlations
        corr = numeric_df.corr().to_dict()
        analysis["correlations"] = corr
        
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
                    "values": row.to_dict()
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
