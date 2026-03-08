import pandas as pd
import sqlite3

# 1. Define your file names
excel_file_path = 'data.xlsx'  # Replace with your Excel file name
database_name = 'agent_database2.db'    # The name of the DB file to be created
table_name = 'testing_data'            # The name of the table inside the DB

print(f"Reading data from {excel_file_path}...")

# 2. Read the Excel file into a Pandas DataFrame
# If your data is on a specific sheet, add sheet_name='Sheet1'
df = pd.read_excel(excel_file_path)

# 3. Create a connection to the SQLite database
# This will automatically create the .db file if it doesn't exist in the folder
conn = sqlite3.connect(database_name)

print(f"Writing data to table '{table_name}' in {database_name}...")

# 4. Write the DataFrame to the SQLite database
# if_exists='replace' ensures that if you run this script again, it overwrites the old table
df.to_sql(table_name, conn, if_exists='replace', index=False)

# 5. Commit and close the connection
conn.commit()
conn.close()

print("Database successfully generated!")