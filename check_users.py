import sqlite3
import os

def check_database():
    base_path = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_path, "school.db")
    
    print(f"Checking database at: {db_path}")
    print("=" * 50)
    
    if not os.path.exists(db_path):
        print("Database file doesn't exist!")
        return
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    print("Tables in database:")
    for table in tables:
        print(f"  - {table[0]}")
    
    print("\n" + "=" * 50)

    if 'users' in [t[0] for t in tables]:
        cur.execute("SELECT * FROM users")
        users = cur.fetchall()
        print(f"Users in database ({len(users)}):")
        for user in users:
            print(f"  ID: {user[0]}, Name: {user[1]}, Email: {user[2]}, Password: {user[3][:20]}...")
    else:
        print("'users' table doesn't exist!")
    
    conn.close()

if __name__ == "__main__":
    check_database()