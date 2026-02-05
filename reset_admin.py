"""
Reset the admin password
"""
import sqlite3
import os
from werkzeug.security import generate_password_hash

def reset_admin_password():
    """Reset admin password to default"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_path, "school.db")
    
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    email = "admin@admin.com"
    new_password = "admin123"
    hashed_password = generate_password_hash(new_password)
    
    cur.execute("SELECT id FROM users WHERE email=?", (email,))
    user = cur.fetchone()
    
    if user:
        cur.execute("UPDATE users SET password=? WHERE email=?", (hashed_password, email))
        conn.commit()
        print(f"✓ Admin password reset successfully!")
        print(f"Email: {email}")
        print(f"New Password: {new_password}")
    else:
        cur.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            ('Administrator', email, hashed_password)
        )
        conn.commit()
        print(f"✓ Admin user created!")
        print(f"Email: {email}")
        print(f"Password: {new_password}")
    
    conn.close()

if __name__ == "__main__":
    reset_admin_password()