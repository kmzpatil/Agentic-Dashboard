"""
PostgreSQL Query Tool for Agent
Executes read-only SELECT queries and returns data ready for XML conversion.

Usage in agent:
    from Frammer.sql_query import execute_query, query_to_xml
    
    # Simple query
    result = execute_query("SELECT * FROM sales LIMIT 10")
    
    # Query with chart configuration
    chart_config = {
        "chart_type": "bar",
        "title": "Monthly Sales",
        "x_label": "Month",
        "y_label": "Revenue"
    }
    xml_output = query_to_xml("SELECT month, revenue FROM sales", chart_config)
"""

import json
import os
import re
from typing import Dict, Any, List, Optional


# Forbidden SQL operations (read-only queries only)
FORBIDDEN_KEYWORDS = {"DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "CREATE", 
                      "TRUNCATE", "GRANT", "REVOKE", "EXEC", "EXECUTE"}

_FORBIDDEN_RE = re.compile(
    r"\b(" + "|".join(FORBIDDEN_KEYWORDS) + r")\b", re.IGNORECASE
)


def _strip_sql_literals_and_comments(query: str) -> str:
    """Remove quoted strings and comments before keyword safety checks."""
    # Remove single-quoted string literals (handles escaped '' in PostgreSQL)
    without_single_quotes = re.sub(r"'(?:''|[^'])*'", "''", query)
    # Remove double-quoted identifiers
    without_double_quotes = re.sub(r'"(?:""|[^"])*"', '""', without_single_quotes)
    # Remove block comments
    without_block_comments = re.sub(r"/\*.*?\*/", " ", without_double_quotes, flags=re.DOTALL)
    # Remove inline comments
    without_inline_comments = re.sub(r"--.*?$", " ", without_block_comments, flags=re.MULTILINE)
    return without_inline_comments


def get_database_connection():
    """
    Create PostgreSQL connection using environment variables or defaults.
    
    Environment variables:
        DATABASE_URL: Full connection string (postgresql://user:pass@host:port/db)
        Or individual variables:
        PGHOST: Database host (default: localhost)
        PGPORT: Database port (default: 5432)
        PGDATABASE: Database name (default: gc_data)
        PGUSER: Database user (default: postgres)
        PGPASSWORD: Database password (default: postgres)
    
    Returns:
        Connection object or None if dependencies not available
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
    except ImportError:
        return None, "psycopg2 not installed. Install with: pip install psycopg2-binary"
    
    # Try DATABASE_URL first
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        try:
            conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
            return conn, None
        except Exception as e:
            return None, f"Connection error: {e}"
    
    # Fall back to individual environment variables
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "5432")
    database = os.getenv("PGDATABASE", "gc_data")
    user = os.getenv("PGUSER", "postgres")
    password = os.getenv("PGPASSWORD", "1234567890")
    
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
            cursor_factory=RealDictCursor
        )
        return conn, None
    except Exception as e:
        return None, f"Connection error: {e}"


def validate_query(query: str) -> Optional[str]:
    """
    Validate that query is safe (read-only SELECT).
    
    Args:
        query: SQL query string
        
    Returns:
        Error message if invalid, None if valid
    """
    if not query or not query.strip():
        return "Empty query provided"

    cleaned_query = _strip_sql_literals_and_comments(query).strip()

    # Guard against multi-statement execution.
    if ";" in cleaned_query.rstrip(";"):
        return "Only a single read-only query is allowed."
    
    # Check for forbidden operations
    if _FORBIDDEN_RE.search(cleaned_query):
        return "Only read-only SELECT queries are allowed. No modifications permitted."
    
    # Ensure query starts with SELECT or a CTE (WITH ... SELECT)
    if not re.match(r"^\s*(SELECT|WITH)\s+", cleaned_query, re.IGNORECASE):
        return "Query must be a SELECT statement (WITH ... SELECT is also allowed)."
    
    return None


def execute_query(query: str, params: tuple = None) -> Dict[str, Any]:
    """
    Execute a SELECT query against PostgreSQL database.
    
    Args:
        query: SQL SELECT query
        params: Optional tuple of parameters for parameterized queries
        
    Returns:
        Dictionary with 'data' (list of records) and 'error' (if any)
        
    Example:
        result = execute_query("SELECT * FROM products WHERE category = %s", ("Electronics",))
        if result['error']:
            print(result['error'])
        else:
            print(result['data'])
    """
    # Validate query
    validation_error = validate_query(query)
    if validation_error:
        return {"data": [], "error": validation_error}
    
    # Get database connection
    conn, error = get_database_connection()
    if error:
        return {"data": [], "error": error}
    
    try:
        cursor = conn.cursor()
        
        # Execute query
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        # Fetch all results
        rows = cursor.fetchall()
        
        # Convert RealDictRow to regular dict
        data_records = [dict(row) for row in rows]
        
        cursor.close()
        conn.close()
        
        return {
            "data": data_records,
            "error": None,
            "row_count": len(data_records)
        }
        
    except Exception as e:
        if conn:
            conn.close()
        return {"data": [], "error": f"Query execution error: {str(e)}"}


def execute_query_with_format(query: str, chart_config: Dict[str, Any] = None, 
                               params: tuple = None) -> Dict[str, Any]:
    """
    Execute query and return data with chart configuration (ready for XML conversion).
    
    Args:
        query: SQL SELECT query
        chart_config: Chart configuration dictionary
        params: Optional query parameters
        
    Returns:
        Dictionary with 'format' and 'data' keys (compatible with json_to_xml)
        
    Example:
        config = {
            "chart_type": "bar",
            "title": "Sales Report",
            "x_label": "Month",
            "y_label": "Revenue"
        }
        result = execute_query_with_format(
            "SELECT month, revenue FROM sales",
            config
        )
    """
    result = execute_query(query, params)
    
    if result['error']:
        return {
            "format": chart_config or {},
            "data": [],
            "error": result['error']
        }
    
    return {
        "format": chart_config or {},
        "data": result['data']
    }


def execute_sql_query(query: str, chart_attributes: Dict[str, Any] = None) -> str:
    """
    Backward-compatible tool entrypoint used by main_agent.

    Returns a JSON string with keys:
    - data: list of row objects
    - chart_attributes: chart config dict
    or
    - error: message
    """
    result = execute_query(query)
    if result.get("error"):
        return json.dumps({"error": result["error"]})

    payload = {
        "data": result.get("data", []),
        "chart_attributes": chart_attributes or {},
    }
    return json.dumps(payload)


def query_to_xml(query: str, chart_config: Dict[str, Any] = None, 
                 params: tuple = None) -> str:
    """
    Execute query and convert directly to XML format.
    
    Args:
        query: SQL SELECT query
        chart_config: Chart configuration
        params: Optional query parameters
        
    Returns:
        XML string ready for frontend rendering
        
    Example:
        config = {"chart_type": "line", "title": "Trends"}
        xml = query_to_xml("SELECT date, value FROM metrics", config)
    """
    # Get data with format
    result = execute_query_with_format(query, chart_config, params)
    
    # Check for errors
    if result.get('error'):
        return f"<error>{result['error']}</error>"
    
    # Import and use the XML converter
    try:
        from json_to_xml import convert_to_xml
        return convert_to_xml(result)
    except ImportError:
        return "<error>json_to_xml module not found</error>"
    except Exception as e:
        return f"<error>XML conversion error: {str(e)}</error>"


def test_connection() -> Dict[str, Any]:
    """
    Test database connection and return status.
    
    Returns:
        Dictionary with connection status and info
    """
    conn, error = get_database_connection()
    
    if error:
        return {
            "connected": False,
            "error": error,
            "message": "Failed to connect to PostgreSQL"
        }
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return {
            "connected": True,
            "message": "Successfully connected to PostgreSQL",
            "version": dict(version).get('version', 'Unknown') if version else 'Unknown'
        }
    except Exception as e:
        if conn:
            conn.close()
        return {
            "connected": False,
            "error": str(e),
            "message": "Connection test failed"
        }


# Example usage and testing
if __name__ == "__main__":
    print("PostgreSQL Query Tool - Testing")
    print("=" * 60)
    
    # Test 1: Connection test
    print("\n1. Testing database connection...")
    status = test_connection()
    print(f"   Connected: {status['connected']}")
    print(f"   Message: {status['message']}")
    if status.get('error'):
        print(f"   Error: {status['error']}")
    if status.get('version'):
        print(f"   PostgreSQL Version: {status['version'][:50]}...")
    
    # Test 2: Simple query
    print("\n2. Testing simple query...")
    result = execute_query("SELECT 1 as test_number, 'Hello' as test_text")
    if result['error']:
        print(f"   Error: {result['error']}")
    else:
        print(f"   Success! Rows: {result['row_count']}")
        print(f"   Data: {result['data']}")
    
    # Test 3: Query with chart config
    print("\n3. Testing query with chart configuration...")
    chart_config = {
        "chart_type": "bar",
        "title": "Test Chart",
        "x_label": "Category",
        "y_label": "Value"
    }
    result = execute_query_with_format(
        "SELECT 'A' as category, 100 as value UNION SELECT 'B', 200",
        chart_config
    )
    if result.get('error'):
        print(f"   Error: {result['error']}")
    else:
        print(f"   Success! Data ready for XML conversion")
        print(f"   Format: {result['format']}")
        print(f"   Data rows: {len(result['data'])}")
    
    print("\n" + "=" * 60)
    print("Testing complete!")
