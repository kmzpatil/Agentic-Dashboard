import pytest
import pandas as pd
from unittest.mock import MagicMock
from mcp_server.database import DatabaseClient

class MockAuth:
    def __init__(self, role, client_name=None, user_id=None):
        self.role = role
        self.client_name = client_name
        self.user_id = user_id

def test_run_read_only_query_scoping():
    # Setup
    db = DatabaseClient("duckdb:///:memory:", "main")
    
    # We need to mock the engine.connect() so it doesn't actually try to run SQL
    # but we want to see the SQL it passes to read_sql_query.
    db.engine.connect = MagicMock()
    
    # Mocking pd.read_sql_query to return an empty DF and capture the statement
    captured_stmt = []
    def mock_read_sql(stmt, conn, params=None):
        captured_stmt.append(str(stmt))
        return pd.DataFrame()
    
    import pandas as pd
    pd.read_sql_query = mock_read_sql
    
    # 1. Test Admin (No Scoping)
    auth_admin = MockAuth("website_admin")
    db.run_read_only_query("SELECT * FROM raw_videos", limit=10, auth=auth_admin)
    assert "scoped_videos" not in captured_stmt[0]
    
    # 2. Test Client Admin (Scoping required)
    auth_client = MockAuth("client_admin", client_name="Client 1")
    db.run_read_only_query("SELECT * FROM raw_videos", limit=10, auth=auth_client)
    last_stmt = captured_stmt[1]
    assert "scoped_videos" in last_stmt
    assert "Client 1" in last_stmt
    assert "raw_videos AS (SELECT * FROM scoped_videos)" in last_stmt
    
    # 3. Test User (Scoping required)
    auth_user = MockAuth("user", user_id=123)
    db.run_read_only_query("SELECT * FROM raw_videos", limit=10, auth=auth_user)
    last_stmt = captured_stmt[2]
    assert "scoped_videos" in last_stmt
    assert "123" in last_stmt
    assert "raw_videos AS (SELECT * FROM scoped_videos)" in last_stmt

if __name__ == "__main__":
    test_run_read_only_query_scoping()
    print("All auth scoping tests passed!")
