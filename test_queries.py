import asyncio
from backend.db.pool import query
from backend.queries.advanced_kpi_queries import get_publish_conversion_details_query, get_roi_matrix_query

access_filter = {
    "join": "",
    "predicates": [],
    "params": [],
    "next_index": 1,
}

try:
    print("Testing conversion details...")
    res1 = query(get_publish_conversion_details_query(access_filter), [])
    print("Conversion rows:", len(res1.rows))
    
    print("Testing ROI matrix...")
    res2 = query(get_roi_matrix_query(access_filter), [])
    print("ROI rows:", len(res2.rows))
    
    print("Testing waste index...")
    from backend.queries.advanced_kpi_queries import get_waste_index_details_query
    res3 = query(get_waste_index_details_query(access_filter), [])
    print("Waste rows:", len(res3.rows))
    
    print("Testing interaction lift...")
    from backend.queries.advanced_kpi_queries import get_interaction_lift_query
    res4 = query(get_interaction_lift_query(access_filter), [])
    print("Lift rows:", len(res4.rows))

    print("Testing entropy...")
    from backend.queries.advanced_kpi_queries import get_cross_dimension_entropy_query
    res5 = query(get_cross_dimension_entropy_query(access_filter), [])
    print("Entropy rows:", len(res5.rows))
    
    print("Testing dfs...")
    from backend.queries.advanced_kpi_queries import get_dfs_query
    res6 = query(get_dfs_query(access_filter), [])
    print("dfs rows:", len(res6.rows))
    
except Exception as e:
    print(f"Error: {e}")

