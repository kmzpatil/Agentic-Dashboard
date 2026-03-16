
import os, sys, json
from dotenv import load_dotenv

load_dotenv(os.path.join("agent", ".env"))
load_dotenv()

sys.path.insert(0, os.path.join(os.getcwd(), "agent"))
from tools.sql_query import execute_sql_query

def run(q):
    res = json.loads(execute_sql_query(q))
    if "error" in res:
        return f"Error: {res['error']}"
    return res.get("data", [])

results = []

results.append("--- PROPER JOIN CHECK (Oct 2025) ---")
q_proper = '''
SELECT COUNT(*) 
FROM published_posts pp
JOIN created_assets ca ON ca."Asset_ID" = pp."Asset_ID"
JOIN raw_videos rv ON rv."Video_ID" = ca."Video_ID"
WHERE pp."Publish_Date" BETWEEN '2025-10-01' AND '2025-10-31'
'''
results.append(json.dumps(run(q_proper), indent=2))

results.append("\n--- AGENT WRONG JOIN CHECK (Oct 2025) ---")
q_wrong = '''
SELECT COUNT(*) 
FROM published_posts pp
JOIN raw_videos rv ON rv."Video_ID" = pp."Asset_ID"
WHERE pp."Publish_Date" BETWEEN '2025-10-01' AND '2025-10-31'
'''
results.append(json.dumps(run(q_wrong), indent=2))

results.append("\n--- TOP 20 CHANNEL/TYPE COUNTS (Oct 2025) ---")
q_data = '''
SELECT pd."Channel_Name", rv."Input_Type", COUNT(*)
FROM published_posts pp
JOIN created_assets ca ON ca."Asset_ID" = pp."Asset_ID"
JOIN raw_videos rv ON rv."Video_ID" = ca."Video_ID"
JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
WHERE pp."Publish_Date" BETWEEN '2025-10-01' AND '2025-10-31'
AND lower(rv."Input_Type") IN ('interview', 'speech')
GROUP BY 1, 2
ORDER BY 3 DESC
LIMIT 20
'''
results.append(json.dumps(run(q_data), indent=2))

with open("join_diagnose_results.txt", "w") as f:
    f.write("\n".join(results))
