import pandas as pd
import json
import os
import sys
from datetime import datetime

def profile_dataframe(df):
    profile = {
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": {}
    }

    for col in df.columns:
        col_data = df[col]
        dtype = str(col_data.dtype)
        null_count = int(col_data.isnull().sum())
        null_percentage = (null_count / len(df)) * 100 if len(df) > 0 else 0
        unique_count = int(col_data.nunique())

        stats = {
            "dtype": dtype,
            "null_count": null_count,
            "null_percentage": round(null_percentage, 2),
            "unique_count": unique_count
        }

        if pd.api.types.is_numeric_dtype(col_data):
            stats.update({
                "min": float(col_data.min()) if not col_data.empty else None,
                "max": float(col_data.max()) if not col_data.empty else None,
                "mean": float(col_data.mean()) if not col_data.empty else None,
                "median": float(col_data.median()) if not col_data.empty else None,
                "std": float(col_data.std()) if not col_data.empty else None
            })
        else:
            # Categorical or other
            top_values = col_data.value_counts().head(5).to_dict()
            stats["top_values"] = {str(k): int(v) for k, v in top_values.items()}

        profile["columns"][col] = stats

    return profile

def ingest_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    try:
        if ext == '.csv':
            df = pd.read_csv(file_path)
        elif ext in ['.xlsx', '.xls']:
            df = pd.read_excel(file_path)
        else:
            return {"error": f"Unsupported file extension: {ext}"}
        
        profile = profile_dataframe(df)
        return {"status": "success", "profile": profile, "file_path": file_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <input_file_or_dir> [output_dir]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(input_path)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    results = []
    if os.path.isdir(input_path):
        for f in os.listdir(input_path):
            if f.endswith(('.csv', '.xlsx', '.xls')):
                full_path = os.path.join(input_path, f)
                print(f"Processing {full_path}...")
                results.append(ingest_file(full_path))
    else:
        print(f"Processing {input_path}...")
        results.append(ingest_file(input_path))

    for res in results:
        if res.get("status") == "success":
            base_name = os.path.basename(res["file_path"])
            output_file = os.path.join(output_dir, f"{base_name}_profile.json")
            with open(output_file, 'w') as f:
                json.dump(res["profile"], f, indent=2)
            print(f"Profile saved to {output_file}")
        else:
            print(f"Error processing {res.get('file_path', 'unknown')}: {res.get('message')}")

if __name__ == "__main__":
    main()
