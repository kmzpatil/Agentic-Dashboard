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
    __tablename__ = "monthly_counts_duration"
    
    month = Column(String, primary_key=True, index=True)
    total_uploaded = Column(Integer)
    total_created = Column(Integer)
    total_published = Column(Integer)
    total_uploaded_duration = Column(Float)
    total_created_duration = Column(Float)
    total_published_duration = Column(Float)

# Table 4: Input Type Data
class InputTypeData(Base):
    __tablename__ = "input_type_metrics"
    
    input_type = Column(String, primary_key=True, index=True)
    uploaded_count = Column(Integer)
    created_count = Column(Integer)
    published_count = Column(Integer)
    uploaded_duration = Column(Float)
    created_duration = Column(Float)
    published_duration = Column(Float)

# Table 5: Language Data
class LanguageData(Base):
    __tablename__ = "language_statistics"
    
    language = Column(String, primary_key=True, index=True)
    uploaded_count = Column(Integer)
    created_count = Column(Integer)
    published_count = Column(Integer)
    uploaded_duration = Column(Float)
    created_duration = Column(Float)
    published_duration = Column(Float)

# Table 6: Output Type Data
class OutputTypeData(Base):
    __tablename__ = "output_type_statistics"
    
    output_type = Column(String, primary_key=True, index=True)

    uploaded_count = Column(Integer)
    created_count = Column(Integer)
    published_count = Column(Integer)
    uploaded_duration = Column(Float)
    created_duration = Column(Float)
    published_duration = Column(Float)

# NOTE: Removed Base.metadata.create_all() — tables should already exist in production.

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
    uploaded_count: int | None
    created_count: int | None
    published_count: int | None
    uploaded_duration: float | None
    created_duration: float | None
    published_duration: float | None
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
def read_root(db: Session = Depends(get_db)):
    try:
        models = [
            ("video_list_data", VideoData),
            ("channel_metrics", ChannelMetrics),
            ("monthly_counts_duration", MonthlyCount),
            ("input_type_metrics", InputTypeData),
            ("language_statistics", LanguageData),
            ("output_type_statistics", OutputTypeData),
        ]
        counts = {}
        for name, model in models:
            counts[name] = db.query(model).count()
        
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