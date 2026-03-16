
import os, json, sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "agent", ".env"))
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agent"))
from tools.sql_query import execute_sql_query

def run(q):
    res = json.loads(execute_sql_query(q))
    return res.get("data", [])

print("=== PLATFORMS ===")
for row in run('SELECT DISTINCT "Published_Platform" FROM post_distribution'):
    print(f"- {row['Published_Platform']}")

print("\n=== DATE RANGE (published_posts) ===")
print(run('SELECT MIN("Publish_Date"), MAX("Publish_Date") FROM published_posts'))

print("\n=== INPUT TYPES (raw_videos) ===")
for row in run('SELECT DISTINCT "Input_Type" FROM raw_videos'):
    print(f"- {row['Input_Type']}")

print("\n=== SAMPLE DATA for February 2025 (any platform) ===")
q = '''
SELECT pd."Published_Platform", rv."Input_Type", pp."Publish_Date"
FROM published_posts pp
JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
JOIN created_assets ca ON ca."Asset_ID" = pp."Asset_ID"
JOIN raw_videos rv ON rv."Video_ID" = ca."Video_ID"
WHERE pp."Publish_Date" BETWEEN '2025-02-01' AND '2025-02-28'
LIMIT 5
'''
print(run(q))
