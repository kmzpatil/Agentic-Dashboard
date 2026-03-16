
import httpx
import json

sql = '''
SELECT pd."Channel_Name", rv."Input_Type", SUM(pp."Published_Duration") / 3600.0 AS publish_hours
FROM published_posts pp
JOIN post_distribution pd ON pd."Post_ID" = pp."Post_ID"
JOIN created_assets ca ON ca."Asset_ID" = pp."Asset_ID"
JOIN raw_videos rv ON rv."Video_ID" = ca."Video_ID"
WHERE pd."Published_Platform" = 'channel'
  AND pp."Publish_Date" BETWEEN '2025-02-01' AND '2025-02-28'
  AND rv."Input_Type" IN ('interview', 'speech')
GROUP BY pd."Channel_Name", rv."Input_Type"
ORDER BY pd."Channel_Name"
'''

url = "http://localhost:4001/api/data"
try:
    resp = httpx.post(url, json={"sql": sql}, timeout=10.0)
    print(f"Status: {resp.status_code}")
    print(json.dumps(resp.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
