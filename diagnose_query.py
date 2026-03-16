import os, json, sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "agent", ".env"))
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agent"))
from tools.sql_query import execute_sql_query

# ---- Diagnosis query 1: check what platforms actually exist ----
diag1 = json.loads(execute_sql_query('SELECT DISTINCT "Published_Platform", COUNT(*) as cnt FROM post_distribution GROUP BY "Published_Platform" ORDER BY cnt DESC'))
print("=== Platform distribution ===")
print(json.dumps(diag1.get("data", diag1), indent=2))

# ---- Diagnosis query 2: check what publish_dates look like ----
diag2 = json.loads(execute_sql_query('SELECT MIN("Publish_Date"), MAX("Publish_Date"), COUNT(*) FROM published_posts'))
print("\n=== Publish date range ===")
print(json.dumps(diag2.get("data", diag2), indent=2))

# ---- Diagnosis query 3: check what Input_Types exist ----
diag3 = json.loads(execute_sql_query('SELECT DISTINCT "Input_Type", COUNT(*) as cnt FROM raw_videos GROUP BY "Input_Type" ORDER BY cnt DESC'))
print("\n=== Input_Type values ===")
print(json.dumps(diag3.get("data", diag3), indent=2))

# ---- Original query without the platform filter ----
sql = '''
SELECT pd."Channel_Name", rv."Input_Type", COUNT(*) as post_count, SUM(pp."Published_Duration") as total_seconds
FROM published_posts pp
JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
JOIN created_assets ca ON ca."Asset_ID" = pp."Asset_ID"
JOIN raw_videos rv ON rv."Video_ID" = ca."Video_ID"
WHERE pp."Publish_Date" BETWEEN '2025-02-01' AND '2025-02-28'
  AND rv."Input_Type" IN ('interview', 'speech')
GROUP BY pd."Channel_Name", rv."Input_Type"
ORDER BY pd."Channel_Name"
LIMIT 20
'''
result = json.loads(execute_sql_query(sql))
print("\n=== Original query (no platform filter) ===")
print(json.dumps(result.get("data", result), indent=2))
