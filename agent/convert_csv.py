import csv
import sqlite3

# Required tables based on sql_query.py schema
TABLE_CREATION_QUERIES = [
    """
    CREATE TABLE IF NOT EXISTS video_list_data (
        video_id INTEGER PRIMARY KEY,
        headline TEXT,
        source TEXT,
        published TEXT,
        team_name TEXT,
        type TEXT,
        uploaded_by TEXT,
        published_platform TEXT,
        published_url TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS channel_metrics (
        channels TEXT PRIMARY KEY,
        facebook INTEGER,
        instagram INTEGER,
        linkedin INTEGER,
        reels INTEGER,
        shorts INTEGER,
        x INTEGER,
        youtube INTEGER,
        threads INTEGER,
        facebook_duration REAL,
        instagram_duration REAL,
        linkedin_duration REAL,
        reels_duration REAL,
        shorts_duration REAL,
        x_duration REAL,
        youtube_duration REAL,
        threads_duration REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS monthly_counts (
        month TEXT PRIMARY KEY,
        total_uploaded INTEGER,
        total_created INTEGER,
        total_published INTEGER,
        total_uploaded_duration REAL,
        total_created_duration REAL,
        total_published_duration REAL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS input_type_data (
        input_type TEXT PRIMARY KEY,
        uploaded_count INTEGER,
        created_count INTEGER,
        published_count INTEGER,
        uploaded_duration TEXT,
        created_duration TEXT,
        published_duration TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS language_data (
        language TEXT PRIMARY KEY,
        uploaded_count INTEGER,
        created_count INTEGER,
        published_count INTEGER,
        uploaded_duration TEXT,
        created_duration TEXT,
        published_duration TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS output_type_data (
        output_type TEXT PRIMARY KEY,
        uploaded_count INTEGER,
        created_count INTEGER,
        published_count INTEGER,
        uploaded_duration TEXT,
        created_duration TEXT,
        published_duration TEXT
    )
    """
]

def load_csv_to_db(csv_path, db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create all base tables
    for query in TABLE_CREATION_QUERIES:
        cursor.execute(query)
    
    # Load CSV data into monthly_counts
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute('''
            INSERT OR REPLACE INTO monthly_counts (
                month, total_uploaded, total_created, total_published,
                total_uploaded_duration, total_created_duration, total_published_duration
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['Month'],
                int(row['Total Uploaded'] or 0),
                int(row['Total Created'] or 0),
                int(row['Total Published'] or 0),
                float(row['Total Uploaded Duration'] or 0.0),
                float(row['Total Created Duration'] or 0.0),
                float(row['Total Published Duration'] or 0.0)
            ))
            
    conn.commit()
    conn.close()
    print("Successfully created database and loaded CSV into monthly_counts.")

if __name__ == '__main__':
    load_csv_to_db("Combined monthly count with duration.csv", "csv_database.db")
