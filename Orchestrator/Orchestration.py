"""
Orchestrator — Multi-agent pipeline using native google-genai SDK.

Flow:
  User JSON → Orchestrator (with tool calling) → SQL DB → Data Processor
    → Haiku Agent (analysis) + FRT Agent (XML formatting) → Output
"""

import json
from typing import Any, Dict
from dotenv import load_dotenv
from google import genai
from google.genai import types
import os

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

client = genai.Client(api_key=api_key)

MODEL = "gemini-3.1-flash-lite-preview"


# ── Tool definitions ─────────────────────────────────────────────────────────

def mcp_lookup_table_schema(table_name: str) -> str:
    """An MCP tool to look up table schemas. Call this FIRST if you don't know the table schema."""
    print(f"\n   [Tool Execution] -> User called mcp_lookup_table_schema for '{table_name}'")
    if table_name.lower() in ["sales", "sales_data"]:
        return "Schema for sales: id INT, region VARCHAR, quarter VARCHAR, total_amount FLOAT"
    return f"Schema for {table_name}: id INT, name VARCHAR, value FLOAT"


tools = [mcp_lookup_table_schema]


# ── Orchestrator node (with tool-calling loop) ───────────────────────────────

def orchestrator_node(user_json: Dict[str, Any], available_tools: list[str]) -> str:
    """
    Orchestrator: translates user intent into SQL via Gemini with tool calling.
    Loops until Gemini stops calling tools and produces a final SQL query.
    """
    tools_prompt = ""
    if available_tools:
        tools_prompt = "\n    AVAILABLE TOOLS:\n"
        for tool_desc in available_tools:
            tools_prompt += f"    - {tool_desc}\n"

    prompt = f"""
        You are the central Orchestrator Agent. Your primary objective is to translate user intent into precise, executable SQL queries.

        CRITICAL INSTRUCTIONS:
        1. UNDERSTAND: Carefully analyze the provided User JSON Request to determine the core data needed.
        2. EXPLORE: If you do not know the exact schema, use your available tools to look up the correct table and column names before writing the query.{tools_prompt}
        3. GENERATE: Construct a valid SQLite query to fulfill the request.
        4. FORMAT: Return ONLY the raw SQL query string inside your response. Do not include markdown formatting (like ```sql), do not include explanations, and do not include conversational text.
        If you call a tool, I will reply with the tool result. Once you have enough info, output the SQL query.

        User JSON Request: {json.dumps(user_json)}
        """

    config = types.GenerateContentConfig(
        tools=tools,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        temperature=0,
        max_output_tokens=4096,
    )

    contents = [types.Content(role="user", parts=[types.Part.from_text(prompt)])]

    # Tool-calling loop
    max_rounds = 5
    for _ in range(max_rounds):
        response = client.models.generate_content(
            model=MODEL, contents=contents, config=config,
        )

        # Check if the model made a function call
        has_function_call = False
        if response.candidates and response.candidates[0].content and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    has_function_call = True
                    break

        if not has_function_call:
            # Model produced a text response — extract the SQL
            text = response.text or ""
            return text.replace("```sql", "").replace("```", "").strip()

        # Process function calls
        contents.append(response.candidates[0].content)

        for part in response.candidates[0].content.parts:
            if part.function_call:
                fn_name = part.function_call.name
                fn_args = dict(part.function_call.args) if part.function_call.args else {}

                # Execute the tool
                if fn_name == "mcp_lookup_table_schema":
                    result = mcp_lookup_table_schema(**fn_args)
                else:
                    result = f"Unknown tool: {fn_name}"

                # Send function response back
                contents.append(types.Content(role="user", parts=[
                    types.Part.from_function_response(name=fn_name, response={"result": result})
                ]))

    return "-- max tool rounds exceeded --"


def sql_db_node(query: str) -> Dict[str, Any]:
    """Execute SQL and return mixed data + metadata payload."""
    print(f"Executing SQL: {query}")
    return {
        "metadata_json": {"query_time": "0.01s", "rows_returned": 2},
        "raw_data": [
            {"id": 1, "region": "US", "quarter": "Q3", "total_amount": 10500.00},
            {"id": 2, "region": "US", "quarter": "Q3", "total_amount": 20400.00},
        ],
    }


def data_processor_node(db_result_mixed: Dict[str, Any]) -> str:
    """Extract pure data from mixed payload."""
    pure_data = db_result_mixed.get("raw_data", [])
    return json.dumps(pure_data)


def haiku_node(data: str) -> str:
    """Haiku Sub-Agent: quick data analysis."""
    prompt = f"""
    You are the Haiku Sub-Agent, a specialized data analyst.
    Review the following raw data extracted from the application's database:
    {data}

    Your task is to provide a brief, high-level analytical summary of this data.
    - Identify key trends, totals, or anomalies.
    - Keep your response structured, concise, and business-focused.
    - Do not output code; only provide natural language insights.
    """
    response = client.models.generate_content(
        model=MODEL, contents=prompt,
        config=types.GenerateContentConfig(temperature=0.5, max_output_tokens=4096),
    )
    return response.text or ""


def frt_node(data: str) -> str:
    """FRT Sub-Agent: format data as XML."""
    prompt = f"""
    You are the FRT (Format Rendering Tool) Sub-Agent.
    Your strict objective is to convert raw application data into well-formed, valid XML.

    Data payload to convert:
    {data}

    CRITICAL INSTRUCTIONS:
    1. Structure the output with a root element `<response>` and wrap each data item in a nested `<item>` container.
    2. Convert dictionary keys into XML tags and dictionary values into text nodes.
    3. Return ONLY the raw XML string. Do not include markdown code block syntax (like ```xml), do not include any preamble, and do not include any conversational text.
    """
    response = client.models.generate_content(
        model=MODEL, contents=prompt,
        config=types.GenerateContentConfig(temperature=0.1, max_output_tokens=4096),
    )
    text = response.text or ""
    return text.replace("```xml", "").replace("```", "").strip()


# ── Pipeline execution ───────────────────────────────────────────────────────

def run_pipeline(user_json: Dict[str, Any], available_tools: list[str]) -> Dict[str, Any]:
    """Run the full orchestration pipeline."""
    # Step 1: Orchestrator generates SQL
    sql_query = orchestrator_node(user_json, available_tools)

    # Step 2: Execute SQL
    db_result = sql_db_node(sql_query)

    # Step 3: Process data
    processed_data = data_processor_node(db_result)

    # Step 4: Run sub-agents in parallel (simulated — sequential for simplicity)
    haiku_analysis = haiku_node(processed_data)
    frt_xml = frt_node(processed_data)

    return {
        "sql_query": sql_query,
        "db_result_mixed": db_result,
        "processed_data": processed_data,
        "haiku_analysis": haiku_analysis,
        "frt_xml": frt_xml,
    }


# ── CLI entry point ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("--- Starting Orchestration Flow ---")

    initial_user_input = {
        "intent": "Get total sales figures",
        "parameters": {"region": "US", "quarter": "Q3"},
    }

    available_tools_desc = [
        "mcp_lookup_table_schema(table_name: str) -> str: Use this tool to look up table schemas if you don't know the columns. Call this FIRST if you need to construct a query.",
    ]

    print("\n[User Input] (JSON):")
    print(json.dumps(initial_user_input, indent=2))

    print("\n--- Executing Pipeline ---")
    try:
        result = run_pipeline(initial_user_input, available_tools_desc)

        print("\n\n--- Final Outputs ---")
        print(f"\n[Generated Query]:\n{result['sql_query']}")
        print(f"\n[Haiku Sub-Agent Analysis]:\n{result['haiku_analysis']}")
        print(f"\n[FRT Sub-Agent Output] (XML sent to User):\n{result['frt_xml']}")

    except BaseException as e:
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print("\n--- API Rate Limit Reached (429 RESOURCE_EXHAUSTED).")
            print("The orchestration logic is correct, but your LLM API quota is currently maxed out.")
            print("Please wait a minute and run the script again.")
        else:
            print(f"\nAn error occurred during execution: {e}")
