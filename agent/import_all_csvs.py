import sqlite3
import csv
import os

csv_files = [
    r"c:\Users\kmzpa\Desktop\DFF\Combined monthly count with duration (1).csv",
    r"c:\Users\kmzpa\Desktop\DFF\Combined monthly count with duration.csv",
    r"c:\Users\kmzpa\Desktop\DFF\input_type vs channel user count.csv",
    r"c:\Users\kmzpa\Desktop\DFF\user multiple channel and multi types.csv"
]

db_path = r"c:\Users\kmzpa\Desktop\DFF\analytics_data.db"

def sanitize_name(name):
    """Convert filename or column name to a valid SQLite identifier."""
    # Remove extension if it's a file name
    if name.endswith('.csv'):
        name = name[:-4]
    
    # Replace spaces and special characters with underscores
    sanitized = "".join([c if c.isalnum() else '_' for c in name])
    
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = 't_' + sanitized
        
    # Collapse multiple underscores
    import re
    sanitized = re.sub(r'_+', '_', sanitized)
    return sanitized.strip('_').lower()

def import_csv_to_db(csv_path, conn):
    if not os.path.exists(csv_path):
        print(f"File not found: {csv_path}")
        return

    table_name = sanitize_name(os.path.basename(csv_path))
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            print(f"Empty file: {csv_path}")
            return
            
        sanitized_headers = [sanitize_name(h) for h in headers]
        
        # Create table
        columns_def = ", ".join([f"{h} TEXT" for h in sanitized_headers])
        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_def});"
        
        cursor = conn.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
        cursor.execute(create_sql)
        
        # Insert data
        placeholders = ", ".join(["?" for _ in sanitized_headers])
        insert_sql = f"INSERT INTO {table_name} VALUES ({placeholders})"
        
        rows = []
        for row in reader:
            # Pad row if it has fewer columns than headers
            if len(row) < len(sanitized_headers):
                row.extend([''] * (len(sanitized_headers) - len(row)))
            # Truncate row if it has more columns
            elif len(row) > len(sanitized_headers):
                row = row[:len(sanitized_headers)]
            rows.append(row)
            
        cursor.executemany(insert_sql, rows)
        conn.commit()
        print(f"Imported {len(rows)} rows into table '{table_name}' from {os.path.basename(csv_path)}")

def main():
    print(f"Creating database at {db_path}")
    conn = sqlite3.connect(db_path)
    
    for csv_file in csv_files:
        import_csv_to_db(csv_file, conn)
        
    conn.close()
    print("All CSV files imported successfully!")

if __name__ == "__main__":
    main()
