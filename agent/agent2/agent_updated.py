import os
from logger_setup import get_logger

logger = get_logger(__name__)

from dotenv import load_dotenv
from typing import TypedDict, Annotated, Dict, Any
from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
import pandas as pd
import plotly.express as px
import sqlite3
import json

load_dotenv()

# 1. Updated Agent State (Added chart_type)
class AgentState(TypedDict):
    question: str
    semantic_context: str  
    sql_query: str
    data: pd.DataFrame
    chart_json: str        
    insights: str
    error: str             
    chart_type: str        # New: Stores the LLM's chosen chart type

# Setup LLM
my_api_key = os.getenv("GROQ_API_KEY")
llm = ChatGroq(
    model_name="llama3-70b-8192", 
    api_key=my_api_key
)

# --- Define Pydantic Model for Tool 3 ---
class ChartSelection(BaseModel):
    chart_type: str = Field(description="One of: 'bar', 'line', 'pie', 'funnel', 'scatter', 'table'")


# 2. Define the Nodes (Functions)

def retrieve_context(state: AgentState):
    """Simulates vector search retrieval for metric definitions."""
    context = "Assume 'conversion' means published divided by processed."
    return {"semantic_context": context}

def generate_sql(state: AgentState):
    """Generates or corrects SQL based on the prompt and schema."""
    prompt = PromptTemplate.from_template(
        "Schema: Table `video_data` (channel, input_type, output_type, processed_count, published_count, published_date).\n"
        "Context: {context}\n"
        "Error to fix (if any): {error}\n"
        "Question: {question}\n"
        "Write a valid SQLite query to answer this. Return ONLY the SQL code without markdown wrappers."
    )
    query = llm.invoke(prompt.format(
        context=state.get("semantic_context", ""),
        error=state.get("error", ""),
        question=state["question"]
    )).content.strip("```sql").strip("```").strip()
    
    return {"sql_query": query, "error": ""}

def execute_sql(state: AgentState):
    """Executes the query and catches errors."""
    query = state["sql_query"]
    try:
        # Create a dummy in-memory database for testing purposes so it doesn't crash if you don't have the db file yet
        conn = sqlite3.connect(":memory:") 
        # Dummy data to prevent execution failure during testing
        pd.DataFrame({
            "channel": ["A", "A", "B", "B"], 
            "input_type": ["Speech", "Interview", "Speech", "Interview"],
            "processed_count": [10, 15, 20, 25]
        }).to_sql("video_data", conn, index=False)

        df = pd.read_sql_query(query, conn)
        conn.close()
        return {"data": df, "error": ""}
    except Exception as e:
        return {"error": str(e), "data": pd.DataFrame()}

# --- TOOL 2: Multi-Dimensional Pivot ---
def process_multidimensional_data(state: AgentState):
    """Reshapes the DataFrame if multiple dimensions are detected in the SQL output."""
    df = state.get("data", pd.DataFrame())
    
    # Auto-detect if we have 2 dimensions + 1 metric (e.g., 3 columns total)
    if not df.empty and len(df.columns) == 3:
        try:
            dim1, dim2, metric = df.columns[0], df.columns[1], df.columns[2]
            
            # Reshape data using pivot_table so it charts beautifully
            pivoted_df = pd.pivot_table(
                df, 
                values=metric, 
                index=dim1, 
                columns=dim2, 
                aggfunc='sum',
                fill_value=0
            ).reset_index()
            
            return {"data": pivoted_df}
        except Exception as e:
            logger.warning(f"Pivot failed: {e}")
            return {"data": df} # Fallback to original if pivot fails
            
    return {"data": df}

# --- TOOL 3: Dynamic Chart Selection ---
def determine_chart_type(state: AgentState):
    """Dynamically selects the Plotly chart type based on the question and data shape."""
    question = state["question"]
    df = state.get("data", pd.DataFrame())
    
    if df.empty:
        return {"chart_type": "table", "chart_json": "{}"}
        
    prompt = f"""
    Based on the user question: '{question}' and the dataframe columns: {list(df.columns)}, 
    what is the best chart type to visualize this? 
    Respond strictly with one of: 'bar', 'line', 'pie', 'funnel'.
    """
    
    # Get structured output from LLM
    structured_llm = llm.with_structured_output(ChartSelection)
    try:
        decision = structured_llm.invoke(prompt)
        chart_type = decision.chart_type
    except Exception:
        chart_type = "bar" # Fallback to bar chart if LLM fails parsing
    
    fig = None
    try:
        if chart_type == "line" and len(df.columns) >= 2:
            fig = px.line(df, x=df.columns[0], y=df.columns[1:])
        elif chart_type == "pie" and len(df.columns) == 2:
            fig = px.pie(df, names=df.columns[0], values=df.columns[1])
        elif chart_type == "funnel" and len(df.columns) == 2:
             fig = px.funnel(df, x=df.columns[1], y=df.columns[0])
        else: 
            # Default to bar (Handles single and multi-dimensional bar charts nicely)
            fig = px.bar(df, x=df.columns[0], y=df.columns[1:], barmode='group')
            
        return {"chart_type": chart_type, "chart_json": fig.to_json() if fig else "{}"}
        
    except Exception as e:
        logger.error(f"Chart generation error: {e}")
        return {"chart_type": "error", "chart_json": "{}"}

def generate_insights(state: AgentState):
    """Generates business insights based on the data."""
    df = state.get("data", pd.DataFrame())
    if df.empty:
        return {"insights": "No data available to generate insights."}
        
    df_string = df.head(10).to_string()
    prompt = PromptTemplate.from_template(
        "Analyze this data and provide 2 brief bullet points of business insights:\n{data}"
    )
    insights = llm.invoke(prompt.format(data=df_string)).content
    return {"insights": insights}

# 3. Define Conditional Edges

def route_sql_execution(state: AgentState):
    """Routes back to SQL generation if there is an error."""
    if state.get("error"):
        return "generate_sql"
    return "process_multidimensional_data" # Route to the new Tool 2

# 4. Build the Graph

workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("retrieve_context", retrieve_context)
workflow.add_node("generate_sql", generate_sql)
workflow.add_node("execute_sql", execute_sql)
workflow.add_node("process_multidimensional_data", process_multidimensional_data) # Tool 2
workflow.add_node("determine_chart_type", determine_chart_type)                   # Tool 3
workflow.add_node("generate_insights", generate_insights)

# Define the flow
workflow.set_entry_point("retrieve_context")
workflow.add_edge("retrieve_context", "generate_sql")
workflow.add_edge("generate_sql", "execute_sql")

# Conditional routing for self-correction
workflow.add_conditional_edges(
    "execute_sql",
    route_sql_execution,
    {
        "generate_sql": "generate_sql",                                    # Loop back on error
        "process_multidimensional_data": "process_multidimensional_data"   # Proceed on success
    }
)

# Continue the linear flow after successful SQL execution
workflow.add_edge("process_multidimensional_data", "determine_chart_type")
workflow.add_edge("determine_chart_type", "generate_insights")
workflow.add_edge("generate_insights", END)

# Compile the agent
app = workflow.compile()

# 5. Run the Agent (Example)
if __name__ == "__main__":
    inputs = {"question": "Show processed count by channel and input_type."}
    
    logger.info("Executing workflow...")
    for output in app.stream(inputs):
        for key, value in output.items():
            logger.info(f"--- Node: {key} ---")
            if "sql_query" in value:
                logger.info(f"Generated SQL: {value['sql_query']}")
            if "error" in value and value["error"]:
                logger.error(f"Error: {value['error']}")
            if "data" in value:
                logger.info(f"Data Shape: {value['data'].shape}")
            if "chart_type" in value:
                logger.info(f"Selected Chart Type: {value['chart_type']}")
            if "insights" in value:
                logger.info(f"Insights:\n{value['insights']}")
