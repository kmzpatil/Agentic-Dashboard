import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, Text, Float, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel

load_dotenv()

# ---------------------------------
# 1. Database Connection
# ---------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db") #confirm the URL 

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
else:
    engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ---------------------------------
# 2. SQLAlchemy Models (Database Mappings)
# ---------------------------------
# Table 1: Video List
class VideoData(Base):
    __tablename__ = "video_list_data"
    
    video_id = Column(BigInteger, primary_key=True, index=True)
    headline = Column(Text, nullable=True)
    source = Column(Text)
    published = Column(String)  # or Integer depending on how it's saved in DB
    team_name = Column(String)
    type = Column(String)
    uploaded_by = Column(String)
    published_platform = Column(String, nullable=True)
    published_url = Column(String, nullable=True)

# Table 2: Channel Metrics
class ChannelMetrics(Base):
    __tablename__ = "channel_metrics" # Adjust if your exact table name is different
    
    channels = Column(String, primary_key=True, index=True)
    facebook = Column(Integer)
    instagram = Column(Integer)
    linkedin = Column(Integer)
    reels = Column(Integer)
    shorts = Column(Integer)
    x = Column(Integer)
    youtube = Column(Integer)
    threads = Column(Integer)
    facebook_duration = Column(Float)
    instagram_duration = Column(Float)
    linkedin_duration = Column(Float)
    reels_duration = Column(Float)
    shorts_duration = Column(Float)
    x_duration = Column(Float)
    youtube_duration = Column(Float)
    threads_duration = Column(Float)

# Table 3: Monthly Counts
class MonthlyCount(Base):
    __tablename__ = "monthly_counts" # Adjust if your exact table name is different
    
    month = Column(String, primary_key=True, index=True)
    total_uploaded = Column(Integer)
    total_created = Column(Integer)
    total_published = Column(Integer)
    total_uploaded_duration = Column(Float)
    total_created_duration = Column(Float)
    total_published_duration = Column(Float)

# Table 4: Input Type Data
class InputTypeData(Base):
    __tablename__ = "input_type_data"
    
    input_type = Column(String, primary_key=True, index=True)
    uploaded_count = Column(Integer)
    created_count = Column(Integer)
    published_count = Column(Integer)
    uploaded_duration = Column(String)
    created_duration = Column(String)
    published_duration = Column(String)

# Table 5: Language Data
class LanguageData(Base):
    __tablename__ = "language_data"
    
    language = Column(String, primary_key=True, index=True)
    uploaded_count = Column(Integer)
    created_count = Column(Integer)
    published_count = Column(Integer)
    uploaded_duration = Column(String)
    created_duration = Column(String)
    published_duration = Column(String)

# Table 6: Output Type Data
class OutputTypeData(Base):
    __tablename__ = "output_type_data"
    
    output_type = Column(String, primary_key=True, index=True)

    uploaded_count = Column(Integer)
    created_count = Column(Integer)
    published_count = Column(Integer)
    uploaded_duration = Column(String)
    created_duration = Column(String)
    published_duration = Column(String)

# Avoid connecting to DB at import-time. This keeps master agent startup resilient
# even when credentials are missing/invalid.
def initialize_database() -> None:
    """Create tables only when explicitly requested by caller."""
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        # SQL tool functions handle connection/query errors and return JSON error payloads.
        # Swallow here to avoid import-time hard failures in orchestrator startup.
        pass

# ---------------------------------
# 3. Pydantic Schemas (API Validation)
# ---------------------------------
class VideoResponse(BaseModel):
    video_id: int
    headline: str | None
    source: str | None
    published: str | None
    team_name: str | None
    type: str | None
    uploaded_by: str | None
    published_platform: str | None
    published_url: str | None
    class Config: from_attributes = True

class ChannelMetricsResponse(BaseModel):
    channels: str
    facebook: int | None
    instagram: int | None
    linkedin: int | None
    reels: int | None
    shorts: int | None
    x: int | None
    youtube: int | None
    threads: int | None
    facebook_duration: float | None
    instagram_duration: float | None
    linkedin_duration: float | None
    reels_duration: float | None
    shorts_duration: float | None
    x_duration: float | None
    youtube_duration: float | None
    threads_duration: float | None
    class Config: from_attributes = True

class MonthlyCountResponse(BaseModel):
    month: str
    total_uploaded: int | None
    total_created: int | None
    total_published: int | None
    total_uploaded_duration: float | None
    total_created_duration: float | None
    total_published_duration: float | None
    class Config: from_attributes = True

class MetricResponse(BaseModel):
    # This single schema works for Input, Output, and Language since they share column structures
    uploaded_count: int | None
    created_count: int | None
    published_count: int | None
    uploaded_duration: str | None
    created_duration: str | None
    published_duration: str | None
    class Config: from_attributes = True

# Extended Schemas to include their specific Primary Keys
class InputTypeResponse(MetricResponse):
    input_type: str

class LanguageResponse(MetricResponse):
    language: str

class OutputTypeResponse(MetricResponse):
    output_type: str


# ---------------------------------
# 4. LangChain Agent SQL Query Function
# ---------------------------------
import json

def execute_sql_query_for_posts(sql_query: str) -> str:
    """
    Execute a SQL query and return results as JSON string with config and data sections.
    
    This function is designed to be called by a LangChain master agent.
    The master agent will send the returned JSON to json_to_xml.py to generate posts.
    
    Args:
        sql_query (str): The SQL query to execute
        
    Returns:
        str: JSON string containing config and data sections, ready for json_to_xml.py
        
    Example:
        >>> json_result = execute_sql_query_for_posts("SELECT * FROM video_list_data LIMIT 5")
        >>> # Master agent sends json_result to json_to_xml.py
    """
    try:
        with engine.connect() as connection:
            # Execute the query
            result = connection.execute(text(sql_query))
            
            # Fetch all rows
            rows = result.fetchall()
            
            # Get column names if query returns rows
            if result.returns_rows:
                column_names = result.keys()
                
                # Format results as a list of dictionaries
                results_list = []
                for row in rows:
                    row_dict = {}
                    for col in column_names:
                        value = getattr(row, col)
                        # Convert to JSON-serializable types
                        if value is None:
                            row_dict[col] = None
                        elif isinstance(value, (int, float, str, bool)):
                            row_dict[col] = value
                        else:
                            row_dict[col] = str(value)
                    results_list.append(row_dict)
                
                response = {
                    "config": {
                        "success": True,
                        "total_count": len(rows),
                        "query": sql_query,
                        "columns": list(column_names),
                        "timestamp": None,  # Can add timestamp if needed
                        "source": "database"
                    },
                    "data": results_list
                }
                
                # Return as JSON string
                return json.dumps(response, indent=2, ensure_ascii=False)
            else:
                # For queries that don't return rows
                response = {
                    "config": {
                        "success": True,
                        "total_count": 0,
                        "rows_affected": result.rowcount,
                        "query": sql_query,
                        "message": "Query executed successfully (no data returned)",
                        "source": "database"
                    },
                    "data": []
                }
                return json.dumps(response, indent=2, ensure_ascii=False)
                
    except Exception as e:
        error_response = {
            "config": {
                "success": False,
                "error": str(e),
                "total_count": 0,
                "query": sql_query,
                "source": "database"
            },
            "data": []
        }
        return json.dumps(error_response, indent=2, ensure_ascii=False)
