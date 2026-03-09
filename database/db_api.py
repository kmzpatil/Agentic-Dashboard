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

# Create all tables on initialization so we can test SQLite without separate migrations
Base.metadata.create_all(bind=engine)

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
# 4. FastAPI App & Routes
# ---------------------------------
app = FastAPI()

@app.get("/")
def read_root(db: Session = Depends(get_db)): #write the full function instead of hardcoding. Test every single database directly. 
    try:
        # Test counting rows in all 6 tables dynamically
        tables = [
            "video_list_data",
            "channel_metrics",
            "monthly_counts",
            "input_type_data",
            "language_data",
            "output_type_data"
        ]
        counts = {}
        for table in tables:
            result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts[table] = result.scalar()
        
        return {
            "message": "API with 6 tables is successfully connected!",
            "database_status": "Connected",
            "table_counts": counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection or query failed: {str(e)}")

@app.get("/videos/", response_model=list[VideoResponse])
def get_videos(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(VideoData).offset(skip).limit(limit).all()

@app.get("/channels/", response_model=list[ChannelMetricsResponse])
def get_channels(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(ChannelMetrics).offset(skip).limit(limit).all()

@app.get("/monthly-counts/", response_model=list[MonthlyCountResponse])
def get_monthly_counts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(MonthlyCount).offset(skip).limit(limit).all()

@app.get("/input-types/", response_model=list[InputTypeResponse])
def get_input_types(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(InputTypeData).offset(skip).limit(limit).all()

@app.get("/languages/", response_model=list[LanguageResponse])
def get_languages(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(LanguageData).offset(skip).limit(limit).all()

@app.get("/output-types/", response_model=list[OutputTypeResponse])
def get_output_types(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(OutputTypeData).offset(skip).limit(limit).all()