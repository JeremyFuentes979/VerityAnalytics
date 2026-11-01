"""Researcher ingestion: read CSV / Excel / PDF into a DataFrame and profile it."""

import csv
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from _shared.jsonio import write_json  # noqa: E402

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:  # pragma: no cover - depends on environment
    HAS_PDFPLUMBER = False


class IngestError(Exception):
    """Raised with a message that is safe to show to the customer."""


def read_csv_robust(file_path):
    """Read a CSV, tolerating odd encodings and delimiters."""
    last_error = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            df = pd.read_csv(file_path, sep=None, engine="python", encoding=encoding)
            return df
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        except pd.errors.EmptyDataError:
            raise IngestError("The file is empty.")
        except (pd.errors.ParserError, csv.Error):
            # delimiter sniffing failed; fall back to plain comma-separated
            try:
                return pd.read_csv(file_path, encoding=encoding)
            except pd.errors.EmptyDataError:
                raise IngestError("The file is empty.")
            except Exception as exc:  # noqa: BLE001
                raise IngestError(f"Could not parse the CSV file: {exc}")
    raise IngestError(f"Could not decode the file's text encoding: {last_error}")


def ingest_pdf(file_path):
    """Extract text and tables from a PDF into a DataFrame."""
    if not HAS_PDFPLUMBER:
        raise IngestError("PDF support is not installed on this server (pdfplumber).")

    rows = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                rows.append({"page": i + 1, "text": text.strip()})
                for t_idx, table in enumerate(page.extract_tables()):
                    if not table:
                        continue
                    headers = [str(h) if h is not None else "" for h in table[0]]
                    for r_idx, row in enumerate(table[1:], 1):
                        record = {"page": i + 1, "table": t_idx + 1, "row": r_idx}
                        for h_idx, cell in enumerate(row):
                            name = headers[h_idx] if h_idx < len(headers) and headers[h_idx] else f"col_{h_idx}"
                            record[name] = cell
                        rows.append(record)
    except Exception as exc:  # noqa: BLE001
        raise IngestError(f"Could not read the PDF: {exc}")

    if not rows:
        raise IngestError("The PDF has no pages.")
    return pd.DataFrame(rows)


def read_any(file_path):
    """Return (DataFrame, extension) for a supported file."""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".csv":
        df = read_csv_robust(file_path)
    elif ext in (".xlsx", ".xls"):
        try:
            df = pd.read_excel(file_path)
        except Exception as exc:  # noqa: BLE001
            raise IngestError(f"Could not read the Excel file: {exc}")
    elif ext == ".pdf":
        df = ingest_pdf(file_path)
    else:
        raise IngestError(f"Unsupported file type: {ext or 'unknown'}")

    df.columns = [str(c).strip() if str(c).strip() else f"column_{i}" for i, c in enumerate(df.columns)]
    return df, ext


def profile_dataframe(df):
    profile = {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": {},
    }

    for col in df.columns:
        col_data = df[col]
        null_count = int(col_data.isnull().sum())
        null_percentage = (null_count / len(df)) * 100 if len(df) > 0 else 0
        stats = {
            "dtype": str(col_data.dtype),
            "null_count": null_count,
            "null_percentage": round(null_percentage, 2),
            "unique_count": int(col_data.nunique()),
        }

        if pd.api.types.is_numeric_dtype(col_data) and not pd.api.types.is_bool_dtype(col_data):
            non_null = col_data.dropna()
            if len(non_null):
                stats.update({
                    "min": float(non_null.min()),
                    "max": float(non_null.max()),
                    "mean": float(non_null.mean()),
                    "median": float(non_null.median()),
                    "std": float(non_null.std()) if len(non_null) > 1 else None,
                })
        else:
            top_values = col_data.value_counts().head(5).to_dict()
            stats["top_values"] = {str(k): int(v) for k, v in top_values.items()}

        profile["columns"][col] = stats

    profile["missing_count"] = int(df.isnull().sum().sum())
    profile["duplicate_rows"] = int(df.duplicated().sum())
    return profile


def build_warnings(profile):
    """Human-readable notes shown in the free preview."""
    warnings = []
    if profile["row_count"] == 0:
        warnings.append("The file has column headers but no data rows.")
    if profile["column_count"] == 1:
        warnings.append("Only one column was detected. The file may use an unusual delimiter.")
    if profile["duplicate_rows"]:
        warnings.append(f"{profile['duplicate_rows']:,} fully duplicated row(s) detected.")
    for name, stats in profile["columns"].items():
        if stats["null_percentage"] >= 50:
            warnings.append(f"Column '{name}' is {stats['null_percentage']:.0f}% empty.")
        elif stats["null_percentage"] >= 10:
            warnings.append(f"Column '{name}' has {stats['null_percentage']:.0f}% missing values.")
    return warnings[:25]


def ingest_file(file_path):
    """Back-compat wrapper returning a status dict."""
    try:
        df, ext = read_any(file_path)
        profile = profile_dataframe(df)
        profile["source_type"] = ext
        profile["warnings"] = build_warnings(profile)
        return {"status": "success", "profile": profile, "file_path": file_path, "dataframe": df}
    except IngestError as exc:
        return {"status": "error", "message": str(exc), "file_path": file_path}
    except Exception as exc:  # noqa: BLE001
        return {"status": "error", "message": f"Unexpected error while reading the file: {exc}", "file_path": file_path}


def main():
    if len(sys.argv) < 2:
        print("Usage: python ingest.py <input_file_or_dir> [output_dir]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else os.path.dirname(os.path.abspath(input_path))
    os.makedirs(output_dir, exist_ok=True)

    paths = []
    if os.path.isdir(input_path):
        paths = [os.path.join(input_path, f) for f in sorted(os.listdir(input_path))
                 if f.lower().endswith((".csv", ".xlsx", ".xls", ".pdf"))]
    else:
        paths = [input_path]

    for path in paths:
        print(f"Processing {path}...")
        res = ingest_file(path)
        if res["status"] == "success":
            out = os.path.join(output_dir, f"{os.path.basename(path)}_profile.json")
            write_json(out, res["profile"])
            print(f"Profile saved to {out}")
        else:
            print(f"Error processing {path}: {res['message']}")


if __name__ == "__main__":
    main()
