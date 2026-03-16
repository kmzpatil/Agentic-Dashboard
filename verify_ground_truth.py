
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

print("--- ACTUAL DATA FOR OCT 2025 ---")
q_correct = '''
SELECT pd."Channel_Name", lower(rv."Input_Type") as type, COUNT(*) as count
FROM published_posts pp
JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
JOIN created_assets ca ON ca."Asset_ID" = pp."Asset_ID"
JOIN raw_videos rv ON rv."Video_ID" = ca."Video_ID"
WHERE pp."Publish_Date" BETWEEN '2025-10-01' AND '2025-10-31'
  AND lower(rv."Input_Type") IN ('interview', 'speech')
GROUP BY 1, 2
ORDER BY 3 DESC
'''
print(json.dumps(run(q_correct), indent=2))

print("\n--- AGENT FAULTY SQL RESULTS ---")
q_agent = '''
SELECT pd."Channel_Name", raw."Input_Type", COUNT(*) AS publish_count
FROM published_posts pp
JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
JOIN raw_video_channel ca ON ca."Video_ID" = (SELECT rv."Video_ID" FROM raw_videos rv WHERE  
rv."Video_ID" = ca."Video_ID")
JOIN raw_videos raw ON raw."Video_ID" = ca."Video_ID"
WHERE to_date(pp."Publish_Date", 'YYYY-MM-DD') BETWEEN '2025-10-01' AND '2025-10-31'
  AND lower(raw."Input_Type") IN ('interview', 'speech')
GROUP BY pd."Channel_Name", raw."Input_Type"
ORDER BY pd."Channel_Name", publish_count DESC
'''
print(json.dumps(run(q_agent), indent=2))
