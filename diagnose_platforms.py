
import os, json, sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "agent", ".env"))
load_dotenv()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "agent"))
from tools.sql_query import execute_sql_query

# Find all platform names
res = json.loads(execute_sql_query('SELECT DISTINCT "Published_Platform", COUNT(*) as cnt FROM post_distribution GROUP BY "Published_Platform" ORDER BY cnt DESC'))
print(json.dumps(res.get("data", []), indent=2))
