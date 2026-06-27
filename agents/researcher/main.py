import os
import sys
import json
import subprocess
import ingest
import reference_data

def run_sql(sql):
    try:
        result = subprocess.check_output(["team-db", sql], stderr=subprocess.STDOUT)
        return json.loads(result)
    except subprocess.CalledProcessError as e:
        print(f"SQL Error: {e.output.decode()}")
        return None

def run_session(session_id):
    session_dir = f"/home/team/shared/sessions/{session_id}"
    input_file = os.path.join(session_dir, "input.csv")
    profile_output = os.path.join(session_dir, "profile.json")
    
    if not os.path.exists(session_dir):
        os.makedirs(session_dir)

    print(f"Processing session {session_id}...")
    run_sql(f"UPDATE sessions SET status = 'processing' WHERE id = '{session_id}'")

    if os.path.exists(input_file):
        print(f"Ingesting {input_file}...")
        result = ingest.ingest_file(input_file)
        if result.get("status") == "success":
            with open(profile_output, 'w') as out_f:
                json.dump(result["profile"], out_f, indent=2)
            print(f"Saved profile to {profile_output}")
            run_sql(f"UPDATE sessions SET status = 'completed', profile_path = '{profile_output}' WHERE id = '{session_id}'")
        else:
            print(f"Error ingesting: {result.get('message')}")
            run_sql(f"UPDATE sessions SET status = 'error' WHERE id = '{session_id}'")
    else:
        # Fallback to directory scanning if input.csv doesn't exist
        input_dir = os.path.join(session_dir, "input")
        output_dir = os.path.join(session_dir, "output")
        profiles_dir = os.path.join(output_dir, "profiles")
        
        if not os.path.exists(profiles_dir):
            os.makedirs(profiles_dir)
            
        print(f"Scanning {input_dir} for files...")
        if os.path.exists(input_dir):
            for f in os.listdir(input_dir):
                if f.endswith(('.csv', '.xlsx', '.xls')):
                    file_path = os.path.join(input_dir, f)
                    print(f"Ingesting {file_path}...")
                    result = ingest.ingest_file(file_path)
                    if result.get("status") == "success":
                        output_file = os.path.join(profiles_dir, f"{f}_profile.json")
                        with open(output_file, 'w') as out_f:
                            json.dump(result["profile"], out_f, indent=2)
                        print(f"Saved profile to {output_file}")
                    else:
                        print(f"Error ingesting {f}: {result.get('message')}")
            
            # Check for reference data request
            req_file = os.path.join(input_dir, "reference_data_request.json")
            if os.path.exists(req_file):
                process_reference_data(input_dir, output_dir)
            
            run_sql(f"UPDATE sessions SET status = 'completed' WHERE id = '{session_id}'")
        else:
            print(f"No input found for session {session_id}")
            run_sql(f"UPDATE sessions SET status = 'failed', data_path = 'not found' WHERE id = '{session_id}'")

def process_reference_data(input_dir, output_dir):
    req_file = os.path.join(input_dir, "reference_data_request.json")
    print(f"Processing reference data request from {req_file}...")
    with open(req_file, 'r') as f:
        requests = json.load(f)
        
    results = {}
    for req in requests:
        rtype = req.get("type")
        if rtype == "fx":
            res = reference_data.get_fx_rate(req["base"], req["target"], req.get("date"))
            key = f"fx_{req['base']}_{req['target']}"
        elif rtype == "benchmark":
            res = reference_data.get_benchmark(req["symbol"], req.get("period", "1mo"))
            key = f"benchmark_{req['symbol']}"
        else:
            res = {"error": f"Unknown type: {rtype}"}
            key = "error"
        results[key] = res
        
    ref_output = os.path.join(output_dir, "reference_data_results.json")
    with open(ref_output, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"Saved reference data to {ref_output}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py <session_id>")
        sys.exit(1)
        
    session_id = sys.argv[1]
    
    # If the argument is a full path, extract the last part as session_id if it's in /shared/sessions/
    if "/home/team/shared/sessions/" in session_id:
        session_id = os.path.basename(session_id.rstrip("/"))
        
    run_session(session_id)

if __name__ == "__main__":
    main()
