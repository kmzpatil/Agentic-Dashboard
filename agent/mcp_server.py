import json
from typing import Any, Dict

from mcp.server.fastmcp import FastMCP

from sql_query import execute_sql_query_for_posts
from json_to_xml import json_to_xml_payload
from agentic_analytics import semantic_retrieve, plan_nl_query, run_nl_query


server = FastMCP("dff-post-tools")


@server.tool()
def run_sql_query(sql_query: str) -> Dict[str, Any]:
    """
    Execute SQL and return JSON object containing `config` and `data`.
    """
    raw = execute_sql_query_for_posts(sql_query)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "config": {
                "success": False,
                "error": "SQL tool returned invalid JSON"
            },
            "data": []
        }


@server.tool()
def convert_json_to_xml(payload: str, root_tag: str = "post_payload") -> str:
    """
    Convert a JSON string payload to XML.

    The payload should contain both `config` and `data`.
    """
    return json_to_xml_payload(payload, root_tag=root_tag)


@server.tool()
def run_sql_to_xml(sql_query: str, root_tag: str = "post_payload") -> Dict[str, Any]:
    """
    Execute SQL and return both JSON and XML in one MCP call.
    """
    raw = execute_sql_query_for_posts(sql_query)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {
            "config": {
                "success": False,
                "error": "SQL tool returned invalid JSON"
            },
            "data": []
        }
        raw = json.dumps(parsed)

    xml_output = json_to_xml_payload(raw, root_tag=root_tag)

    return {
        "json": parsed,
        "xml": xml_output
    }


@server.tool()
def analytics_semantic_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    Retrieve relevant analytics definitions/logic for natural-language queries.
    """
    hits = semantic_retrieve(query=query, top_k=top_k)
    return {
        "query": query,
        "hits": hits,
        "count": len(hits),
    }


@server.tool()
def analytics_plan_nlq(question: str, filters_json: str = "{}") -> Dict[str, Any]:
    """
    Plan an explainable NLQ analytics query and return generated SQL + mapping details.
    """
    try:
        filters = json.loads(filters_json) if filters_json else {}
        if not isinstance(filters, dict):
            filters = {}
    except json.JSONDecodeError:
        filters = {}

    plan = plan_nl_query(question=question, filters=filters)
    return plan


@server.tool()
def analytics_run_nlq(question: str, filters_json: str = "{}", root_tag: str = "post_payload") -> Dict[str, Any]:
    """
    Execute a natural-language analytics query end-to-end and return JSON + XML output.
    """
    try:
        filters = json.loads(filters_json) if filters_json else {}
        if not isinstance(filters, dict):
            filters = {}
    except json.JSONDecodeError:
        filters = {}

    output = run_nl_query(question=question, filters=filters)
    result_json = output.get("result", {})
    xml_output = json_to_xml_payload(json.dumps(result_json), root_tag=root_tag)

    return {
        "plan": output.get("plan", {}),
        "json": result_json,
        "xml": xml_output,
    }


if __name__ == "__main__":
    server.run()
