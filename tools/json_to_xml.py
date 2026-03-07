"""
JSON to XML Chart Converter
Converts JSON chart data with format and data fields to XML output for agent state.

Usage in agent workflow:
    from json_to_xml import convert_to_xml
    
    # Your data from agent state
    chart_data = {
        "format": {...},  # chart configuration
        "data": [...]     # data records
    }
    
    # Convert and return to agent
    xml_output = convert_to_xml(chart_data)
    return xml_output  # Pass to next agent or frontend

Input format:
{
    "format": {
        "chart_type": "bar",
        "title": "Monthly Sales",
        "x_label": "Month",
        "y_label": "Revenue ($)",
        "legend": {"position": "top", "enabled": true},
        "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1"]
    },
    "data": [
        {"month": "Jan", "revenue": 15000},
        {"month": "Feb", "revenue": 18000},
        {"month": "Mar", "revenue": 22000}
    ]
}
"""

import json
import xml.etree.ElementTree as ET
from xml.dom import minidom
from typing import Dict, Any, List, Union


def prettify_xml(elem: ET.Element) -> str:
    """Return a pretty-printed XML string."""
    rough_string = ET.tostring(elem, encoding='unicode')
    reparsed = minidom.parseString(rough_string)
    return reparsed.toprettyxml(indent="  ")


def add_configuration_xml(config_node: ET.Element, format_data: Dict[str, Any]) -> None:
    """
    Map format fields to XML configuration nodes.
    
    Supports fields:
    - chart_type / type: Chart type (bar, line, pie, etc.)
    - title: Chart title
    - x_label / x_axis: X-axis label
    - y_label / y_axis: Y-axis label
    - legend: Legend configuration (dict or simple value)
    - colors: List of color hex codes
    - Any additional properties go to <properties>
    """
    # Chart type
    chart_type = ET.SubElement(config_node, "type")
    chart_type.text = str(format_data.get("chart_type", format_data.get("type", "bar")))

    # Title
    if "title" in format_data:
        title = ET.SubElement(config_node, "title")
        title.text = str(format_data["title"])

    # Axes
    axes = ET.SubElement(config_node, "axes")
    if "x_label" in format_data:
        x_axis = ET.SubElement(axes, "x_axis")
        x_axis.text = str(format_data["x_label"])
    elif "x_axis" in format_data:
        x_axis = ET.SubElement(axes, "x_axis")
        x_axis.text = str(format_data["x_axis"])

    if "y_label" in format_data:
        y_axis = ET.SubElement(axes, "y_axis")
        y_axis.text = str(format_data["y_label"])
    elif "y_axis" in format_data:
        y_axis = ET.SubElement(axes, "y_axis")
        y_axis.text = str(format_data["y_axis"])

    # Legend
    if "legend" in format_data:
        legend = ET.SubElement(config_node, "legend")
        legend_cfg = format_data["legend"]
        if isinstance(legend_cfg, dict):
            for key, value in legend_cfg.items():
                elem = ET.SubElement(legend, str(key))
                elem.text = str(value)
        else:
            legend.text = str(legend_cfg)

    # Colors
    if "colors" in format_data and isinstance(format_data["colors"], list):
        colors = ET.SubElement(config_node, "colors")
        for idx, color in enumerate(format_data["colors"]):
            color_elem = ET.SubElement(colors, "color")
            color_elem.set("index", str(idx))
            color_elem.text = str(color)

    # Additional properties
    reserved_keys = ["chart_type", "type", "title", "x_label", "y_label", 
                     "x_axis", "y_axis", "legend", "colors"]
    additional = ET.SubElement(config_node, "properties")
    for key, value in format_data.items():
        if key not in reserved_keys:
            prop = ET.SubElement(additional, str(key))
            if isinstance(value, (dict, list)):
                prop.text = json.dumps(value)
            else:
                prop.text = str(value)


def add_data_xml(root: ET.Element, data_records: List[Dict[str, Any]]) -> None:
    """
    Write tabular records into XML data nodes.
    
    Creates a structure with columns and rows where each row contains cells.
    """
    data_section = ET.SubElement(root, "data")

    # Extract column names from first record
    columns = ET.SubElement(data_section, "columns")
    column_names: List[str] = []
    if data_records:
        first_row = data_records[0]
        if isinstance(first_row, dict):
            column_names = [str(name) for name in first_row.keys()]

    for col_name in column_names:
        col = ET.SubElement(columns, "column")
        col.text = col_name

    # Add rows with cells
    rows = ET.SubElement(data_section, "rows")
    for idx, row in enumerate(data_records):
        if not isinstance(row, dict):
            continue
        row_elem = ET.SubElement(rows, "row")
        row_elem.set("index", str(idx))
        for col_name in column_names:
            cell = ET.SubElement(row_elem, "cell")
            cell.set("column", col_name)
            value = row.get(col_name)
            cell.text = "" if value is None else str(value)


def convert_to_xml(input_data: Union[Dict[str, Any], str]) -> str:
    """
    Convert JSON chart data to XML format.
    
    Args:
        input_data: Dictionary or JSON string with 'format' and 'data' fields
        
    Returns:
        Pretty-printed XML string
        
    Example:
        >>> data = {
        ...     "format": {"chart_type": "bar", "title": "Sales"},
        ...     "data": [{"month": "Jan", "revenue": 15000}]
        ... }
        >>> xml = convert_to_xml(data)
    """
    # Parse input if it's a JSON string
    if isinstance(input_data, str):
        try:
            input_data = json.loads(input_data)
        except json.JSONDecodeError as e:
            return f"<error>Invalid JSON: {e}</error>"
    
    if not isinstance(input_data, dict):
        return "<error>Input must be a dictionary or JSON string</error>"
    
    # Extract format and data
    format_config = input_data.get("format", {})
    data_records = input_data.get("data", [])
    
    if not isinstance(format_config, dict):
        return "<error>'format' field must be a dictionary</error>"
    
    if not isinstance(data_records, list):
        return "<error>'data' field must be a list</error>"
    
    if not data_records:
        return "<error>No data records provided</error>"
    
    # Build XML structure
    root = ET.Element("chart")
    
    # Add configuration section
    config = ET.SubElement(root, "configuration")
    add_configuration_xml(config, format_config)
    
    # Add data section
    add_data_xml(root, data_records)
    
    return prettify_xml(root)


def json_db_to_xml(sql_tool_payload: Union[Dict[str, Any], str], sql_query: str = None) -> str:
    """
    Backward-compatible converter used by main_agent/tools.__init__.

    Accepts payload like:
    {
      "data": [...],
      "chart_attributes": {...}
    }

    and maps it to convert_to_xml format:
    {
      "format": {...},
      "data": [...]
    }
    """
    del sql_query  # kept for compatibility with legacy signature

    parsed: Dict[str, Any]
    if isinstance(sql_tool_payload, str):
        try:
            parsed = json.loads(sql_tool_payload)
        except json.JSONDecodeError as exc:
            return f"<error>Invalid SQL tool payload JSON: {exc}</error>"
    elif isinstance(sql_tool_payload, dict):
        parsed = sql_tool_payload
    else:
        return "<error>Invalid input: expected dict or JSON string.</error>"

    if isinstance(parsed, dict) and parsed.get("error"):
        return f"<error>{parsed['error']}</error>"

    mapped = {
        "format": parsed.get("chart_attributes", {}),
        "data": parsed.get("data", []),
    }
    return convert_to_xml(mapped)


def json_file_db_to_xml(json_file_path: str, sql_query: str) -> str:
    """
    Compatibility helper that loads chart attributes from file and runs SQL.
    """
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            chart_attributes = json.load(f)
    except FileNotFoundError:
        return f"<error>File not found: {json_file_path}</error>"
    except json.JSONDecodeError as exc:
        return f"<error>Invalid JSON in file: {exc}</error>"

    try:
        from .sql_query import execute_sql_query
    except ImportError:
        from sql_query import execute_sql_query

    payload_json = execute_sql_query(sql_query, chart_attributes)
    return json_db_to_xml(payload_json)


# Example usage and agent integration
if __name__ == "__main__":
    # Example: Direct conversion for agent state
    sample_data = {
        "format": {
            "chart_type": "bar",
            "title": "Monthly Sales",
            "x_label": "Month",
            "y_label": "Revenue ($)",
            "legend": {
                "position": "top",
                "enabled": True
            },
            "colors": ["#FF6B6B", "#4ECDC4", "#45B7D1"]
        },
        "data": [
            {"month": "Jan", "revenue": 15000},
            {"month": "Feb", "revenue": 18000},
            {"month": "Mar", "revenue": 22000}
        ]
    }
    
    # Convert and return to agent state
    xml_result = convert_to_xml(sample_data)
    print("XML Output for Agent State:")
    print(xml_result)
