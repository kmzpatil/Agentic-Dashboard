import os
from pathlib import Path
from urllib.parse import quote_plus, urlencode

from dotenv import load_dotenv
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, Text, Float, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parents[1]
load_dotenv(ROOT_DIR / ".env")
load_dotenv()

# ---------------------------------
# 1. Database Connection
# ---------------------------------
def _env(*names):
    for name in names:
        value = os.getenv(name)
        if value is None:
            continue
        normalized = value.strip()
        if normalized:
            return normalized
    return None


def _resolve_database_url():
    explicit_url = _env("POSTGRES_URL", "PGDATABASE_URL")
    if explicit_url:
        return explicit_url

    host = _env("PGHOST", "POSTGRES_HOST")
    user = _env("PGUSER", "POSTGRES_USER")
    database = _env("PGDATABASE", "POSTGRES_DB")
    password = _env("PGPASSWORD", "POSTGRES_PASSWORD")
    port = _env("PGPORT", "POSTGRES_PORT") or "5432"
    sslmode = _env("PGSSLMODE", "POSTGRES_SSLMODE", "DB_SSLMODE")

    if host and user and database:
        credentials = quote_plus(user)
        if password is not None:
            credentials = f"{credentials}:{quote_plus(password)}"

        query = {}
        target_host = host
        if host.startswith("/"):
            target_host = "localhost"
            query["host"] = host
        if sslmode:
            query["sslmode"] = sslmode

        query_string = f"?{urlencode(query)}" if query else ""
        return f"postgresql+psycopg2://{credentials}@{target_host}:{port}/{quote_plus(database)}{query_string}"

    return _env("DATABASE_URL") or f"sqlite:///{ROOT_DIR / 'database' / 'frammer_database.sqlite'}"


DATABASE_URL = _resolve_database_url()

if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False}, pool_pre_ping=True)
else:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

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

class Channel(Base):
    __tablename__ = "channels"
    # Assuming Channel_Name is unique and can be used as primary key.
    # If not, you may need a composite key or a surrogate key. SQLite allows rowid.
    Channel_Name = Column(String, primary_key=True, index=True)
    Client_Name = Column(String)

class Client(Base):
    __tablename__ = "clients"
    Client_Name = Column(String, primary_key=True, index=True)

class CreatedAsset(Base):
    __tablename__ = "created_assets"
    Asset_ID = Column(Integer, primary_key=True, index=True)
    Video_ID = Column(Integer)
    Output_Type = Column(String)
    Create_Date = Column(String)
    Created_Duration = Column(Integer)

class PostDistribution(Base):
    __tablename__ = "post_distribution"
    Post_ID = Column(Integer, primary_key=True, index=True)
    Channel_Name = Column(String)
    Published_Platform = Column(String)
    Published_URL = Column(String)

class PublishedPost(Base):
    __tablename__ = "published_posts"
    Post_ID = Column(Integer, primary_key=True, index=True)
    Asset_ID = Column(Integer)
    Publish_Date = Column(String)
    Published_Duration = Column(Integer)

class RawVideoChannel(Base):
    __tablename__ = "raw_video_channel"
    Video_ID = Column(Integer, primary_key=True) # Using Video_ID and Channel_Name as composite might be better, picking Video_ID for now
    Channel_Name = Column(String, primary_key=True)

class RawVideo(Base):
    __tablename__ = "raw_videos"
    Video_ID = Column(Integer, primary_key=True, index=True)
    User_ID = Column(Integer)
    Headline = Column(Text, nullable=True)
    Source_URL = Column(String)
    Upload_Date = Column(String)
    Input_Type = Column(String)
    Language = Column(String)
    Uploaded_Duration = Column(Integer)

class User(Base):
    __tablename__ = "users"
    User_ID = Column(Integer, primary_key=True, index=True)
    User_Name = Column(String)
    Team_Name = Column(String)
    Client_Name = Column(String)

# Create all tables on initialization so we can test SQLite without separate migrations
Base.metadata.create_all(bind=engine)

# ---------------------------------
# 3. Pydantic Schemas (API Validation)
# ---------------------------------

class ChannelResponse(BaseModel):
    Channel_Name: str | None
    Client_Name: str | None
    class Config: from_attributes = True

class ClientResponse(BaseModel):
    Client_Name: str | None
    class Config: from_attributes = True

class CreatedAssetResponse(BaseModel):
    Asset_ID: int | None
    Video_ID: int | None
    Output_Type: str | None
    Create_Date: str | None
    Created_Duration: int | None
    class Config: from_attributes = True

class PostDistributionResponse(BaseModel):
    Post_ID: int | None
    Channel_Name: str | None
    Published_Platform: str | None
    Published_URL: str | None
    class Config: from_attributes = True

class PublishedPostResponse(BaseModel):
    Post_ID: int | None
    Asset_ID: int | None
    Publish_Date: str | None
    Published_Duration: int | None
    class Config: from_attributes = True

class RawVideoChannelResponse(BaseModel):
    Video_ID: int | None
    Channel_Name: str | None
    class Config: from_attributes = True

class RawVideoResponse(BaseModel):
    Video_ID: int | None
    User_ID: int | None
    Headline: str | None
    Source_URL: str | None
    Upload_Date: str | None
    Input_Type: str | None
    Language: str | None
    Uploaded_Duration: int | None
    class Config: from_attributes = True

class UserResponse(BaseModel):
    User_ID: int | None
    User_Name: str | None
    Team_Name: str | None
    Client_Name: str | None
    class Config: from_attributes = True


# ---------------------------------
# 4. FastAPI App & Routes
# ---------------------------------
app = FastAPI()

@app.get("/")
def read_root(db: Session = Depends(get_db)):
    try:
        tables = [
            "channels", "clients", "created_assets", "post_distribution",
            "published_posts", "raw_video_channel", "raw_videos", "users"
        ]
        counts = {}
        for table in tables:
            result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts[table] = result.scalar()
        
        return {
            "message": "API with 8 tables successfully connected!",
            "database_status": "Connected",
            "table_counts": counts
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection or query failed: {str(e)}")

@app.get("/raw-videos/", response_model=list[RawVideoResponse])
def get_raw_videos(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(RawVideo).offset(skip).limit(limit).all()

@app.get("/created-assets/", response_model=list[CreatedAssetResponse])
def get_created_assets(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(CreatedAsset).offset(skip).limit(limit).all()

@app.get("/published-posts/", response_model=list[PublishedPostResponse])
def get_published_posts(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(PublishedPost).offset(skip).limit(limit).all()

@app.get("/channels/", response_model=list[ChannelResponse])
def get_channels(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(Channel).offset(skip).limit(limit).all()

@app.get("/users/", response_model=list[UserResponse])
def get_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(User).offset(skip).limit(limit).all()

@app.get("/clients/", response_model=list[ClientResponse])
def get_clients(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    return db.query(Client).offset(skip).limit(limit).all()
