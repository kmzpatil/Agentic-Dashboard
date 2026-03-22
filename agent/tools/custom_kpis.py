"""
Tool: get_custom_kpi_info
Provides detailed definitions, formulas, and business significance for 
specialized KPIs used in the ATLAS analytics platform.
"""

import json
from typing import Dict, List, Optional

# Extracted from frontend/src/features/overview/kpiDefinitions.js
# SQL queries added to provide the agent with concrete implementation paths.
CUSTOM_KPIS: List[Dict[str, str]] = [
    {
        "id": "uploaded_count",
        "title": "TOTAL UPLOADED",
        "definition": "Full count of raw video files uploaded into the pipeline.",
        "formula": "COUNT(DISTINCT rv.\"Video_ID\")",
        "significance": "Fundamental growth metric showing intake volume.",
        "sql": "SELECT COUNT(DISTINCT \"Video_ID\") FROM raw_videos"
    },
    {
        "id": "processed_count",
        "title": "TOTAL PROCESSED",
        "definition": "Count of unique videos that have passed through the initial processing/slicing stage.",
        "formula": "COUNT(DISTINCT ca.\"Video_ID\")",
        "significance": "Measures the throughput capacity of the processing engine.",
        "sql": "SELECT COUNT(DISTINCT \"Video_ID\") FROM created_assets"
    },
    {
        "id": "created_count",
        "title": "TOTAL CREATED",
        "definition": "Total number of individual clip assets generated from all source videos.",
        "formula": "COUNT(DISTINCT ca.\"Asset_ID\")",
        "significance": "Indicates the direct output volume of the creation stage.",
        "sql": "SELECT COUNT(DISTINCT \"Asset_ID\") FROM created_assets"
    },
    {
        "id": "published_count",
        "title": "TOTAL PUBLISHED",
        "definition": "Total number of posts successfully published to one or more platforms.",
        "formula": "COUNT(DISTINCT pp.\"Asset_ID\")",
        "significance": "The ultimate success metric; represents final content reach.",
        "sql": "SELECT COUNT(DISTINCT \"Asset_ID\") FROM published_posts"
    },
    {
        "id": "publish_conversion",
        "title": "PUBLISH CONVERSION RATE",
        "definition": "The percentage of processed/created clips that actually end up being published.",
        "formula": "(Total Published Clips / Total Created Clips) * 100",
        "significance": "Measures effective utilization of generated clips. Low conversion signals inefficiency in extraction.",
        "sql": "SELECT (COUNT(DISTINCT pp.\"Asset_ID\")::NUMERIC / NULLIF(COUNT(DISTINCT ca.\"Asset_ID\"), 0)) * 100 AS conversion_rate FROM created_assets ca LEFT JOIN published_posts pp ON pp.\"Asset_ID\" = ca.\"Asset_ID\""
    },
    {
        "id": "month_by_month_use_rate",
        "title": "MONTH BY MONTH USE RATE",
        "definition": "The relative growth or decline in the number of uploaded videos compared to the previous month.",
        "formula": "(Current Month Uploads - Previous Month Uploads) / Previous Month Uploads",
        "significance": "Tracks adoption and platform engagement trends.",
        "sql": "WITH monthly AS (SELECT date_trunc('month', to_date(\"Upload_Date\", 'YYYY-MM-DD'))::date AS month, COUNT(*) AS count FROM raw_videos GROUP BY 1) SELECT month, count, (count - LAG(count) OVER (ORDER BY month))::numeric / NULLIF(LAG(count) OVER (ORDER BY month), 0) AS use_rate FROM monthly"
    },
    {
        "id": "processing_efficiency",
        "title": "PROCESSING EFFICIENCY",
        "definition": "The ratio of the total duration of published content to the total duration of created content.",
        "formula": "(Total Published Duration / Total Created Duration) * 100",
        "significance": "Measures temporal waste in the editing stage. High waste means too much footage is generated but ignored.",
        "sql": "SELECT (SUM(pp.\"Published_Duration\")::NUMERIC / NULLIF(SUM(ca.\"Created_Duration\"), 0)) * 100 AS efficiency FROM created_assets ca JOIN published_posts pp ON pp.\"Asset_ID\" = ca.\"Asset_ID\""
    },
    {
        "id": "creation_rate",
        "title": "CREATION RATE",
        "definition": "The average number of short clips generated per single uploaded raw video.",
        "formula": "Total created count / Total uploaded count",
        "significance": "Yield of the slicing/processing engine per video.",
        "sql": "SELECT COUNT(DISTINCT ca.\"Asset_ID\")::NUMERIC / NULLIF(COUNT(DISTINCT rv.\"Video_ID\"), 0) AS creation_rate FROM raw_videos rv LEFT JOIN created_assets ca ON ca.\"Video_ID\" = rv.\"Video_ID\""
    },
    {
        "id": "waste_index",
        "title": "WASTE INDEX",
        "definition": "A logarithmic scale measuring the proportion of created duration that does not get published.",
        "formula": "-log10(1 - ((Total Created Duration - Total Published Duration) / Total Created duration) + 0.001)",
        "significance": "Amplifies high-waste scenarios. Helps flag instances where footage is disproportionately ignored.",
        "sql": "SELECT -LOG10(1 - ((SUM(\"Created_Duration\") - SUM(\"Published_Duration\"))::numeric / NULLIF(SUM(\"Created_Duration\"), 0)) + 0.001) AS waste_index FROM created_assets ca LEFT JOIN published_posts pp ON pp.\"Asset_ID\" = ca.\"Asset_ID\""
    },
    {
        "id": "upload_failure_rate",
        "title": "UPLOAD FAILURE RATE",
        "definition": "Severity of uploads resulting in zero published clips.",
        "formula": "Penalty based on share of users/channels with 0 publishes.",
        "significance": "Identifies 'dead-end' uploads; useful for user training or error diagnosis.",
        "sql": "WITH counts AS (SELECT rv.\"Video_ID\", COUNT(pp.\"Asset_ID\") AS publishes FROM raw_videos rv LEFT JOIN created_assets ca ON ca.\"Video_ID\" = rv.\"Video_ID\" LEFT JOIN published_posts pp ON pp.\"Asset_ID\" = ca.\"Asset_ID\" GROUP BY 1) SELECT AVG(CASE WHEN publishes = 0 THEN 1 ELSE 0 END) * 1000 AS failure_penalty FROM counts"
    },
    {
        "id": "roi",
        "title": "ROI MATRIX",
        "definition": "Evaluates resource cost vs likelihood of publication.",
        "formula": "Resource Intensity vs Selection Success.",
        "significance": "Categorizes content types by ROI profile.",
        "sql": "SELECT ca.\"Output_Type\", AVG(ca.\"Created_Duration\") / (SELECT AVG(\"Created_Duration\") FROM created_assets) AS intensity, COUNT(pp.\"Asset_ID\")::numeric / COUNT(ca.\"Asset_ID\") AS success_rate FROM created_assets ca LEFT JOIN published_posts pp ON pp.\"Asset_ID\" = ca.\"Asset_ID\" GROUP BY 1"
    },
    {
        "id": "dfs",
        "title": "DURATION FIT SCORE (DFS)",
        "definition": "Measures how closely created asset duration aligns with final published asset duration.",
        "formula": "1 - (abs(avg created duration - avg published duration) / avg created duration)",
        "significance": "High score implies high accuracy in initial AI cuts (minimal manual editing needed).",
        "sql": "SELECT 1 - (ABS(AVG(ca.\"Created_Duration\") - AVG(pp.\"Published_Duration\")) / NULLIF(AVG(ca.\"Created_Duration\"), 0)) AS dfs FROM created_assets ca JOIN published_posts pp ON pp.\"Asset_ID\" = ca.\"Asset_ID\""
    },
    {
        "id": "interaction_lift",
        "title": "INTERACTION LIFT",
        "definition": "Correlation between two dimensions (e.g. Input Type & Output Type) and publish rate.",
        "formula": "log(publish rate(I, O) / (publish rate(I) * publish rate(O)))",
        "significance": "Identifies synergies — e.g. finding that Podcasts work best as Reels.",
        "sql": "WITH base AS (SELECT lower(rv.\"Input_Type\") as input, ca.\"Output_Type\" as output, CASE WHEN pp.\"Asset_ID\" IS NOT NULL THEN 1 ELSE 0 END as pub FROM raw_videos rv JOIN created_assets ca ON ca.\"Video_ID\" = rv.\"Video_ID\" LEFT JOIN published_posts pp ON pp.\"Asset_ID\" = ca.\"Asset_ID\") SELECT input, output, LOG(NULLIF(AVG(pub),0) / NULLIF(((SELECT AVG(pub) FROM base b2 WHERE b2.input = base.input) * (SELECT AVG(pub) FROM base b3 WHERE b3.output = base.output)),0)) AS lift FROM base GROUP BY 1, 2"
    },
    {
        "id": "cross_dimension_entropy",
        "title": "CROSS DIMENSION ENTROPY",
        "definition": "Diversity of content created by each user.",
        "formula": "-∑(p_ij * log2(p_ij)) where p_ij is share of duration per category.",
        "significance": "Separates hyper-specialized users from generalists.",
        "sql": "WITH user_shares AS (SELECT \"User_ID\", lower(\"Input_Type\") as cat, SUM(\"Uploaded_Duration\") as cat_dur, SUM(SUM(\"Uploaded_Duration\")) OVER(PARTITION BY \"User_ID\") as tot_dur FROM raw_videos GROUP BY 1, 2), probs AS (SELECT \"User_ID\", cat_dur / NULLIF(tot_dur,0) as p FROM user_shares) SELECT \"User_ID\", -SUM(p * LOG(2, NULLIF(p,0))) as entropy FROM probs GROUP BY 1"
    },
    {
        "id": "publish_dependency_index",
        "title": "PUBLISH DEPENDENCY (V)",
        "definition": "Correlation of categorical sectors with the overall publish rate.",
        "formula": "Cramer's V (chi-square based correlation).",
        "significance": "Predicts which dimensions (Language, User, etc.) strongest impact success.",
        "sql": "SELECT CORR(CASE WHEN pp.\"Asset_ID\" IS NOT NULL THEN 1 ELSE 0 END, rv.\"Uploaded_Duration\") AS length_correlation FROM raw_videos rv LEFT JOIN created_assets ca ON ca.\"Video_ID\" = rv.\"Video_ID\" LEFT JOIN published_posts pp ON pp.\"Asset_ID\" = ca.\"Asset_ID\""
    },
    {
        "id": "point_biserial",
        "title": "POINT BISERIAL CORR.",
        "definition": "Correlation between a continuous variable (length) and publication success (binary).",
        "formula": "r_pb correlation formula.",
        "significance": "Asks: does initial video length impact publication probability?",
        "sql": "SELECT CORR(\"Uploaded_Duration\", CASE WHEN pp.\"Asset_ID\" IS NOT NULL THEN 1 ELSE 0 END) FROM raw_videos rv LEFT JOIN created_assets ca ON ca.\"Video_ID\" = rv.\"Video_ID\" LEFT JOIN published_posts pp ON pp.\"Asset_ID\" = ca.\"Asset_ID\""
    },
    {
        "id": "multidimensional_waste",
        "title": "WASTE INTERACTION",
        "definition": "Compares actual waste of dimension combinations against expected independent waste.",
        "formula": "Actual Waste / Expected Waste.",
        "significance": "Identifies 'toxic' combinations of input/output types with high waste.",
        "sql": "WITH waste AS (SELECT lower(rv.\"Input_Type\") as input, ca.\"Output_Type\" as output, SUM(\"Created_Duration\") - SUM(\"Published_Duration\") as wasted FROM raw_videos rv JOIN created_assets ca ON ca.\"Video_ID\" = rv.\"Video_ID\" LEFT JOIN published_posts pp ON pp.\"Asset_ID\" = ca.\"Asset_ID\" GROUP BY 1, 2) SELECT input, output, wasted / NULLIF((SELECT AVG(wasted) FROM waste w2 WHERE w2.input = waste.input), 0) as waste_ratio FROM waste"
    },
    {
        "id": "ctas",
        "title": "TALENT ALIGNMENT",
        "definition": "Efficiency of channel workload distribution based on user historical success.",
        "formula": "Weighted workload vs success relative to global share.",
        "significance": "Determines if channels are using their best talent effectively.",
        "sql": "SELECT rvc.\"Channel_Name\", rv.\"User_ID\", COUNT(pp.\"Asset_ID\")::numeric / NULLIF(COUNT(ca.\"Asset_ID\"), 0) as user_conversion FROM raw_videos rv JOIN raw_video_channel rvc ON rvc.\"Video_ID\" = rv.\"Video_ID\" JOIN created_assets ca ON ca.\"Video_ID\" = rv.\"Video_ID\" LEFT JOIN published_posts pp ON pp.\"Asset_ID\" = ca.\"Asset_ID\" GROUP BY 1, 2"
    },
    {
        "id": "rei",
        "title": "RELATIVE EFFICIENCY",
        "definition": "Individual user potential adjusted for task difficulty.",
        "formula": "User publish rate / Category baseline rate.",
        "significance": "Fairly evaluates users tasked with difficult/niche content.",
        "sql": "WITH baselines AS (SELECT lower(\"Input_Type\") as cat, COUNT(pp.\"Asset_ID\")::numeric / COUNT(ca.\"Asset_ID\") as base_rate FROM raw_videos rv JOIN created_assets ca ON ca.\"Video_ID\" = rv.\"Video_ID\" LEFT JOIN published_posts pp ON pp.\"Asset_ID\" = ca.\"Asset_ID\" GROUP BY 1), user_rates AS (SELECT \"User_ID\", lower(\"Input_Type\") as cat, COUNT(pp.\"Asset_ID\")::numeric / COUNT(ca.\"Asset_ID\") as user_rate FROM raw_videos rv JOIN created_assets ca ON ca.\"Video_ID\" = rv.\"Video_ID\" LEFT JOIN published_posts pp ON pp.\"Asset_ID\" = ca.\"Asset_ID\" GROUP BY 1, 2) SELECT \"User_ID\", AVG(user_rate / NULLIF(base_rate, 0)) as rei FROM user_rates JOIN baselines USING (cat) GROUP BY 1"
    }
]

def get_custom_kpi_info(kpi_id: Optional[str] = None) -> str:
    """
    Retrieve detailed business context for custom platform KPIs.
    
    If kpi_id is provided, returns the full definition and significance for that KPI.
    If kpi_id is None, returns a summary list of all available custom KPIs.
    """
    if not kpi_id:
        # Return summary
        summary = [{"id": k["id"], "title": k["title"]} for k in CUSTOM_KPIS]
        return json.dumps(summary, indent=2)

    # Find specific KPI
    kpi = next((k for k in CUSTOM_KPIS if k["id"] == kpi_id), None)
    if not kpi:
        return f"Error: KPI '{kpi_id}' not found. Use get_custom_kpi_info() to see valid IDs."

    return json.dumps(kpi, indent=2)
