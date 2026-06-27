#!/usr/bin/env python3
import os
import json
import pandas as pd
from datetime import datetime

class Auditor:
    def __init__(self, session_dir):
        self.session_dir = session_dir
        self.raw_dir = os.path.join(session_dir, 'raw')
        self.profile_path = os.path.join(session_dir, 'profile.json')
        self.analysis_path = os.path.join(session_dir, 'analysis.json')
        self.cleaned_dir = os.path.join(session_dir, 'cleaned')
        self.audit_trail_path = os.path.join(session_dir, 'audit_trail.json')
        self.audit_trail = []

    def log_change(self, file, row, column, old_value, new_value, reason, auto_fixed=True):
        # Convert pandas/numpy types to native python types for JSON serialization
        def to_native(v):
            if hasattr(v, 'item'):
                return v.item()
            return v

        self.audit_trail.append({
            'timestamp': datetime.now().isoformat(),
            'file': file,
            'row': to_native(row),
            'column': column,
            'old_value': str(old_value),
            'new_value': str(new_value),
            'reason': reason,
            'auto_fixed': auto_fixed
        })

    def load_data(self):
        if not os.path.exists(self.raw_dir):
            return {}
        files = [f for f in os.listdir(self.raw_dir) if f.endswith(('.csv', '.xlsx'))]
        data = {}
        for f in files:
            path = os.path.join(self.raw_dir, f)
            try:
                if f.endswith('.csv'):
                    data[f] = pd.read_csv(path)
                else:
                    data[f] = pd.read_excel(path)
            except Exception as e:
                print(f"Error loading {f}: {e}")
        return data

    def load_analysis(self):
        if os.path.exists(self.analysis_path):
            with open(self.analysis_path, 'r') as f:
                return json.load(f)
        return {}

    def load_profile(self):
        if os.path.exists(self.profile_path):
            with open(self.profile_path, 'r') as f:
                return json.load(f)
        return {}

    def validate_and_clean(self):
        data = self.load_data()
        if not data:
            return "No raw data found to clean."
        
        analysis = self.load_analysis()
        profile = self.load_profile()
        cleaned_data = {}

        for filename, df in data.items():
            file_profile = profile.get('files', {}).get(filename, {})
            pk = file_profile.get('primary_key')
            
            # 1. De-duplication
            initial_count = len(df)
            
            # Check if analysis specifies a subset for de-duplication
            subset = None
            if 'deduplication' in analysis:
                for entry in analysis['deduplication']:
                    if entry.get('file') == filename:
                        subset = entry.get('subset')
                        break
            
            df_cleaned = df.drop_duplicates(subset=subset)
            if len(df_cleaned) < initial_count:
                reason = "Removed exact duplicates" if not subset else f"Removed duplicates based on {subset}"
                self.log_change(filename, "all", "all", initial_count, len(df_cleaned), reason)

            # 2. General Cleaning (Whitespace)
            for col in df_cleaned.select_dtypes(['object']).columns:
                df_cleaned[col] = df_cleaned[col].str.strip()

            # 3. Apply Analyst Findings
            if 'anomalies' in analysis:
                for anomaly in analysis['anomalies']:
                    if anomaly.get('file') == filename:
                        col_name = anomaly.get('column')
                        issue = anomaly.get('issue')
                        
                        # Find the row. Use PK if available, else use index
                        row_found = False
                        if pk and 'pk_value' in anomaly:
                            pk_val = anomaly['pk_value']
                            rows = df_cleaned[df_cleaned[pk] == pk_val]
                            if not rows.empty:
                                row_idx = rows.index[0]
                                row_found = True
                        elif 'row' in anomaly:
                            row_idx = anomaly['row']
                            if row_idx in df_cleaned.index:
                                row_found = True
                        
                        if row_found and col_name in df_cleaned.columns:
                            old_val = df_cleaned.at[row_idx, col_name]
                            
                            # Example fixes
                            if issue == "Negative value" and old_val < 0:
                                new_val = abs(old_val)
                                df_cleaned.at[row_idx, col_name] = new_val
                                self.log_change(filename, row_idx, col_name, old_val, new_val, "Fixed negative value per Analyst finding")
                            elif issue == "Missing value" and 'suggested_value' in anomaly:
                                new_val = anomaly['suggested_value']
                                df_cleaned.at[row_idx, col_name] = new_val
                                self.log_change(filename, row_idx, col_name, old_val, new_val, "Filled missing value per Analyst suggestion")

            # 4. Standardization Rules
            if 'standardization_rules' in analysis:
                for rule in analysis['standardization_rules']:
                    col = rule.get('column')
                    fmt = rule.get('format')
                    if col in df_cleaned.columns:
                        if fmt == "Uppercase 2-letter":
                            original = df_cleaned[col].copy()
                            df_cleaned[col] = df_cleaned[col].str.upper().str[:2]
                            # Simplified logging
                            self.log_change(filename, "all", col, "original", "Standardized to Uppercase 2-letter", "Standardization rule")

            cleaned_data[filename] = df_cleaned

        # Save cleaned data
        if not os.path.exists(self.cleaned_dir):
            os.makedirs(self.cleaned_dir)
        
        for filename, df in cleaned_data.items():
            output_path = os.path.join(self.cleaned_dir, filename)
            if filename.endswith('.csv'):
                df.to_csv(output_path, index=False)
            else:
                df.to_excel(output_path, index=False)

        # Save audit trail
        with open(self.audit_trail_path, 'w') as f:
            json.dump(self.audit_trail, f, indent=2)

        return f"Cleaning completed. Audit trail saved to {self.audit_trail_path}"

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        session_id = sys.argv[1]
        # Check if it's a full path or just an ID
        if os.path.isabs(session_id):
            session_path = session_id
        else:
            session_path = os.path.join('/home/team/shared/sessions', session_id)
        
        auditor = Auditor(session_path)
        print(auditor.validate_and_clean())
    else:
        print("Usage: python auditor.py <session_id_or_path>")
