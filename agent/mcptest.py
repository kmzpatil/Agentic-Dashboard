from mcp.server.fastmcp import FastMCP
import sqlite3
import pandas as pd
import plotly.express as px
import json

# Initialize the MCP Server
mcp = FastMCP("Frammer_Analytics_Server")

# Path to your Frammer database
DB_PATH = "frammer_analytics.db"

def get_connection():
    """Establish a read-only connection to the database."""
    uri = f"file:{DB_PATH}?mode=ro"
    return sqlite3.connect(uri, uri=True)

@mcp.tool()
def retrieve_metric_definitions(search_term: str) -> str:
    """
    Simulates a Vector Search Semantic Layer.
    Use this tool to look up exact business definitions and formulas for Frammer AI metrics 
    (e.g., 'conversion rate', 'drop-off', 'usage hours') before writing SQL.
    """
    # In a full production app, this would query ChromaDB or FAISS.
    # For the competition, a dictionary lookup handles the core NLQ requirements.
    dictionary = {
        "conversion": "Publish Conversion Rate = (COUNT(published_url) / COUNT(video_id)) * 100",
        "drop-off": "Processed vs Published Gap = Count of processed_at IS NOT NULL minus Count of published_flag = 1",
        "usage": "Usage Hours = SUM(duration) / 60 for a given dimension",
        "gap": "Look at the difference between uploaded, processed, and published counts."
    }
    
    # Return matched definitions or a default fallback
    results = [desc for term, desc in dictionary.items() if term in search_term.lower()]
    if results:
        return " | ".join(results)
    return "No specific metric definition found. Use standard SQL counting/summing."

@mcp.tool()
def get_frammer_schema() -> str:
    """
    Retrieves the database schema, including tables and columns.
    Always use this before writing a new SQL query to ensure column names are correct.
    """
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        schema_info = "Frammer AI Database Schema:\n"
        for table in tables:
            table_name = table[0]
            schema_info += f"\nTable: {table_name}\nColumns: "
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            col_details = [f"{col[1]} ({col[2]})" for col in columns]
            schema_info += ", ".join(col_details) + "\n"
            
        conn.close()
        return schema_info
    except Exception as e:
        return f"Error retrieving schema: {str(e)}"

@mcp.tool()
def execute_sql_query(query: str) -> str:
    """
    Executes a SELECT SQL query and returns the raw data as a JSON string.
    Use this when you need to analyze data to generate business insights.
    """
    forbidden_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
    if any(keyword in query.upper() for keyword in forbidden_keywords):
        return "Error: Only read-only SELECT queries are allowed."
    
    try:
        conn = get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df.to_json(orient="records")
    except Exception as e:
        return f"SQL Execution Error: {str(e)}"

@mcp.tool()
def generate_plotly_chart(query: str) -> str:
    """
    Executes a SELECT SQL query and automatically generates a Plotly chart.
    Use this when the user explicitly asks for a visual, chart, or trend.
    Returns the JSON representation of the chart to be rendered by the frontend.
    """
    forbidden_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE"]
    if any(keyword in query.upper() for keyword in forbidden_keywords):
        return "Error: Only read-only SELECT queries are allowed."

    try:
        conn = get_connection()
        df = pd.read_sql_query(query, conn)
        conn.close()

        if df.empty or len(df.columns) < 2:
            return "Error: Query returned insufficient data to plot (need at least 2 columns)."

        # Simple heuristic: Column 1 is X-axis, Column 2 is Y-axis
        x_col = df.columns[0]
        y_col = df.columns[1]
        
        # Determine chart type based on data types
        if pd.api.types.is_numeric_dtype(df[y_col]):
            # If the x-axis is a date, use a line chart for trends
            if 'date' in x_col.lower() or 'time' in x_col.lower() or pd.api.types.is_datetime64_any_dtype(df[x_col]):
                fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
            else:
                fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
        else:
            return "Error: Second column must be numeric to generate a meaningful chart."

        # Return the serialized chart JSON
        return fig.to_json()
    
    except Exception as e:
        return f"Chart Generation Error: {str(e)}"

if __name__ == "__main__":
    print("Starting Frammer Analytics MCP Server...")
    mcp.run("streamable-http")