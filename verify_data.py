
import os, json, sys
from dotenv import load_dotenv

load_dotenv(os.path.join("agent", ".env"))
load_dotenv()

sys.path.insert(0, "agent")
from tools.sql_query import execute_sql_query

def run(q):
    res = json.loads(execute_sql_query(q))
    if "error" in res:
        return f"Error: {res['error']}"
    return res.get("data", [])

results = []

results.append("--- DATE RANGE IN published_posts ---")
results.append(json.dumps(run('SELECT MIN("Publish_Date"), MAX("Publish_Date"), COUNT(*) FROM published_posts'), indent=2))

results.append("\n--- ANY POSTS IN FEB 2025? ---")
results.append(json.dumps(run('SELECT COUNT(*) FROM published_posts WHERE "Publish_Date" LIKE \'2025-02%\''), indent=2))

results.append("\n--- TOP 10 PUBLISH DATES ---")
results.append(json.dumps(run('SELECT "Publish_Date", COUNT(*) FROM published_posts GROUP BY 1 ORDER BY 1 LIMIT 10'), indent=2))

results.append("\n--- INPUT_TYPE COUNTS ---")
results.append(json.dumps(run('SELECT "Input_Type", COUNT(*) FROM raw_videos GROUP BY 1 ORDER BY 2 DESC'), indent=2))

results.append("\n--- DATE RANGE IN created_assets ---")
results.append(json.dumps(run('SELECT MIN("Create_Date"), MAX("Create_Date"), COUNT(*) FROM created_assets'), indent=2))

with open("verify_results.txt", "w") as f:
    f.write("\n".join(results))
print("✓ Results written to verify_results.txt")
