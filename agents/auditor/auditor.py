#!/usr/bin/env python3
"""Auditor — validation, cleaning and the audit trail.

Policy (this is a trust product, so the Auditor is conservative):
  * AUTO-FIXED and logged: surrounding whitespace, exact duplicate rows,
    case/spacing variants of the same category label.
  * FLAGGED only, never changed: negative amounts (may be credits/refunds)
    and missing values. A human decides what those mean.

Usage:
    python auditor.py <session-id-or-dir>

Reads  <session>/raw/*.csv (normalised by the Researcher), analysis.json, profile.json
Writes <session>/cleaned_data.csv, <session>/cleaned/<file>, <session>/audit_trail.json
"""

import os
import sys
from collections import Counter
from datetime import datetime

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
from _shared.jsonio import read_json, write_json  # noqa: E402

MAX_LOGGED_CELLS = 250  # cell-level log lines per action per file; totals are always exact


def repo_root():
    return os.path.abspath(os.path.join(HERE, "..", ".."))


def default_sessions_dir():
    return os.environ.get("VERITY_SESSIONS_DIR") or os.path.join(repo_root(), "sessions")


class Auditor:
    def __init__(self, session_dir):
        self.session_dir = session_dir
        self.raw_dir = os.path.join(session_dir, "raw")
        self.profile_path = os.path.join(session_dir, "profile.json")
        self.analysis_path = os.path.join(session_dir, "analysis.json")
        self.cleaned_dir = os.path.join(session_dir, "cleaned")
        self.audit_trail_path = os.path.join(session_dir, "audit_trail.json")
        self.audit_trail = {}
        self.log = []

    def log_change(self, file, row, column, old_value, new_value, reason, auto_fixed=True):
        self.log.append({
            "timestamp": datetime.now().isoformat(),
            "file": file,
            "row": row,
            "column": column,
            "old_value": str(old_value),
            "new_value": str(new_value),
            "reason": reason,
            "auto_fixed": auto_fixed,
        })

    def load_data(self):
        if not os.path.isdir(self.raw_dir):
            return {}
        data = {}
        for f in sorted(os.listdir(self.raw_dir)):
            if not f.endswith((".csv", ".xlsx")):
                continue
            path = os.path.join(self.raw_dir, f)
            try:
                data[f] = pd.read_csv(path) if f.endswith(".csv") else pd.read_excel(path)
            except Exception as exc:  # noqa: BLE001
                print(f"Error loading {f}: {exc}")
        return data

    # -- cleaning steps -------------------------------------------------------

    def _trim_whitespace(self, filename, df, corrections):
        total = 0
        logged = 0
        for col in df.select_dtypes(include=["object"]).columns:
            original = df[col]
            trimmed = original.map(lambda v: v.strip() if isinstance(v, str) else v)
            changed = original.notna() & (original != trimmed)
            n = int(changed.sum())
            if not n:
                continue
            for idx in original[changed].index:
                if logged >= MAX_LOGGED_CELLS:
                    break
                self.log_change(filename, int(idx), col, repr(original[idx]), repr(trimmed[idx]), "Trimmed surrounding whitespace")
                logged += 1
            df[col] = trimmed
            total += n
            corrections.append({
                "field": f"{filename}:{col}:trim_whitespace",
                "file": filename, "column": col, "action": "trim_whitespace",
                "cells_changed": n, "reason": "Trimmed surrounding whitespace",
            })
        return total

    def _drop_duplicates(self, filename, df, corrections):
        dup_mask = df.duplicated(keep="first")
        n = int(dup_mask.sum())
        if not n:
            return df
        removed = [int(i) for i in df.index[dup_mask]]
        for idx in removed[:MAX_LOGGED_CELLS]:
            self.log_change(filename, idx, "all", "duplicate row", "removed", "Removed exact duplicate row")
        corrections.append({
            "field": f"{filename}:all:deduplicate",
            "file": filename, "action": "deduplicate",
            "before": int(len(df)), "after": int(len(df) - n),
            "rows_removed": n, "removed_row_indices": removed[:1000],
            "reason": "Removed exact duplicate rows (first occurrence kept)",
        })
        return df[~dup_mask]

    def _standardize_categories(self, filename, df, corrections):
        for col in df.select_dtypes(include=["object"]).columns:
            values = df[col].dropna()
            counts = Counter(values)
            if not (1 < len(counts) < 100):
                continue
            groups = {}
            for value in counts:
                groups.setdefault(" ".join(str(value).split()).lower(), []).append(value)
            mapping = {}
            for variants in groups.values():
                if len(variants) < 2:
                    continue
                canonical = sorted(variants, key=lambda v: (-counts[v], str(v)))[0]
                for v in variants:
                    if v != canonical:
                        mapping[v] = canonical
            if not mapping:
                continue
            affected = 0
            for old, new in mapping.items():
                n = counts[old]
                affected += n
                self.log_change(filename, "multiple", col, old, new, f"Standardized category spelling ({n} cell(s))")
            df[col] = df[col].replace(mapping)
            corrections.append({
                "field": f"{filename}:{col}:standardize",
                "file": filename, "column": col, "action": "standardize",
                "cells_changed": affected, "mappings": {str(k): str(v) for k, v in mapping.items()},
                "reason": "Merged case/spacing variants of the same category label",
            })

    def _flag_issues(self, filename, df, issues):
        for col in df.columns:
            n_missing = int(df[col].isnull().sum())
            if n_missing:
                issues.append({
                    "file": filename, "column": col, "issue": "Missing value", "count": n_missing,
                    "severity": "medium" if n_missing / max(len(df), 1) < 0.2 else "high",
                    "action": "flagged for review (not changed)",
                })
        for col in df.select_dtypes(include=[np.number]).columns:
            n_neg = int((df[col] < 0).sum())
            if n_neg:
                issues.append({
                    "file": filename, "column": col, "issue": "Negative value", "count": n_neg,
                    "severity": "low",
                    "action": "flagged for review (may be a credit or refund; not changed)",
                })

    # -- driver ---------------------------------------------------------------

    def validate_and_clean(self):
        data = self.load_data()
        if not data:
            raise FileNotFoundError("No raw data found to clean.")

        corrections = []
        issues = []
        cleaned = {}

        for filename, df in data.items():
            df = df.copy()
            self._trim_whitespace(filename, df, corrections)
            df = self._drop_duplicates(filename, df, corrections)
            self._standardize_categories(filename, df, corrections)
            self._flag_issues(filename, df, issues)
            cleaned[filename] = df

        os.makedirs(self.cleaned_dir, exist_ok=True)
        primary_name = next(iter(cleaned))
        cleaned[primary_name].to_csv(os.path.join(self.session_dir, "cleaned_data.csv"), index=False)
        for filename, df in cleaned.items():
            out = os.path.join(self.cleaned_dir, filename)
            df.to_csv(out, index=False) if filename.endswith(".csv") else df.to_excel(out, index=False)

        self.audit_trail = {
            "generated_at": datetime.now().isoformat(),
            "total_corrections": len(corrections),
            "records_affected": sum(c.get("cells_changed", c.get("rows_removed", 0)) for c in corrections),
            "issues_found": len(issues),
            "corrections": corrections,
            "data_quality_issues": issues,
            "standardizations": [c for c in corrections if c["action"] == "standardize"],
            "deduplications": [c for c in corrections if c["action"] == "deduplicate"],
            "log": self.log,
            "log_note": f"Cell-level log is capped at {MAX_LOGGED_CELLS} entries per action per file; "
                        "correction records above always carry exact totals.",
        }
        write_json(self.audit_trail_path, self.audit_trail)
        return f"Cleaning completed. Audit trail saved to {self.audit_trail_path}"


def main():
    if len(sys.argv) < 2:
        print("Usage: python auditor.py <session_id_or_path>")
        return 1
    arg = sys.argv[1]
    session_path = os.path.abspath(arg) if (os.path.isabs(arg) or os.sep in arg) else os.path.join(default_sessions_dir(), arg)
    try:
        print(Auditor(session_path).validate_and_clean())
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
