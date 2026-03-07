import sqlite3

def generate_mock_data():
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    # Populate testing table if it exists
    cursor.execute("CREATE TABLE IF NOT EXISTS testing_data (Channel TEXT, User TEXT, Uploaded_Count INTEGER)")
    conn.commit()
    conn.close()

if __name__ == '__main__':
    generate_mock_data()
