
import os, json, sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "agent", ".env"))
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agent"))
from tools.sql_query import execute_sql_query

# Find all platform names
res = json.loads(execute_sql_query('SELECT DISTINCT "Published_Platform", COUNT(*) as cnt FROM post_distribution GROUP BY "Published_Platform" ORDER BY cnt DESC'))
data = res.get("data", [])
print("PLAFORMS FOUND:")
for row in data:
    print(f"- {row['Published_Platform']}: {row['cnt']}")

# Find date range
res2 = json.loads(execute_sql_query('SELECT MIN("Publish_Date"), MAX("Publish_Date") FROM published_posts'))
data2 = res2.get("data", [])
print("\nDATE RANGE IN published_posts:")
print(data2)

# Find input types
res3 = json.loads(execute_sql_query('SELECT DISTINCT "Input_Type", COUNT(*) as cnt FROM raw_videos GROUP BY "Input_Type"'))
data3 = res3.get("data", [])
print("\nINPUT TYPES IN raw_videos:")
for row in data3:
    print(f"- {row['Input_Type']}: {row['cnt']}")
