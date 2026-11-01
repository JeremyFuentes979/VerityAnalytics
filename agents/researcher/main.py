"""Researcher — data ingestion and profiling.

Usage:
    python main.py <session-id-or-session-dir>

Reads  <session>/input.(csv|xlsx|xls|pdf)
Writes <session>/raw/data.csv   normalised copy every later agent reads
       <session>/profile.json   profile shown in the free preview
On failure writes <session>/profile_error.json {"message": ...} and exits 1.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))

import ingest  # noqa: E402
import reference_data  # noqa: E402
from _shared.jsonio import read_json, write_json  # noqa: E402

INPUT_NAMES = ("input.csv", "input.xlsx", "input.xls", "input.pdf")


def repo_root():
    return os.path.abspath(os.path.join(HERE, "..", ".."))


def default_sessions_dir():
    return os.environ.get("VERITY_SESSIONS_DIR") or os.path.join(repo_root(), "sessions")


def resolve_session_dir(arg):
    if os.path.isabs(arg) or os.sep in arg:
        return os.path.abspath(arg)
    return os.path.join(default_sessions_dir(), arg)


def fail(session_dir, message):
    print(f"ERROR: {message}")
    write_json(os.path.join(session_dir, "profile_error.json"), {"message": message})
    return 1


def run_session(session_dir):
    if not os.path.isdir(session_dir):
        print(f"ERROR: session directory not found: {session_dir}")
        return 1

    error_path = os.path.join(session_dir, "profile_error.json")
    if os.path.exists(error_path):
        os.unlink(error_path)

    input_path = next((os.path.join(session_dir, n) for n in INPUT_NAMES
                       if os.path.exists(os.path.join(session_dir, n))), None)
    if input_path is None:
        return fail(session_dir, "No uploaded file was found for this session.")

    print(f"Ingesting {input_path}...")
    result = ingest.ingest_file(input_path)
    if result["status"] != "success":
        return fail(session_dir, result.get("message", "The file could not be read."))

    df = result.pop("dataframe")
    profile = result["profile"]

    raw_dir = os.path.join(session_dir, "raw")
    os.makedirs(raw_dir, exist_ok=True)
    df.to_csv(os.path.join(raw_dir, "data.csv"), index=False)

    session = read_json(os.path.join(session_dir, "session.json"), {}) or {}
    profile["source"] = session.get("fileName") or os.path.basename(input_path)
    profile["file_size_bytes"] = os.path.getsize(input_path)
    profile["raw_data_file"] = "raw/data.csv"
    if profile["source_type"] == ".pdf" and not any(
        str(v).strip() for v in df.get("text", []) if v is not None
    ):
        profile["warnings"].append("No extractable text found. Scanned PDFs need OCR, which is not supported yet.")

    write_json(os.path.join(session_dir, "profile.json"), profile)
    print(f"Saved profile to {os.path.join(session_dir, 'profile.json')}")

    request_path = os.path.join(session_dir, "reference_data_request.json")
    if os.path.exists(request_path):
        process_reference_data(session_dir, request_path)
    return 0


def process_reference_data(session_dir, request_path):
    requests = read_json(request_path, []) or []
    results = {}
    for req in requests:
        rtype = req.get("type")
        try:
            if rtype == "fx":
                res = reference_data.get_fx_rate(req["base"], req["target"], req.get("date"))
                key = f"fx_{req['base']}_{req['target']}"
            elif rtype == "benchmark":
                res = reference_data.get_benchmark(req["symbol"], req.get("period", "1mo"))
                key = f"benchmark_{req['symbol']}"
            else:
                res, key = {"error": f"Unknown type: {rtype}"}, "error"
        except Exception as exc:  # noqa: BLE001
            res, key = {"error": str(exc)}, f"{rtype}_error"
        results[key] = res
    write_json(os.path.join(session_dir, "reference_data_results.json"), results)


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <session-id-or-dir>")
        sys.exit(1)
    sys.exit(run_session(resolve_session_dir(sys.argv[1])))


if __name__ == "__main__":
    main()
