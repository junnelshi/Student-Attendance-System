"""
Run this script once to create the default admin user
"""
from dbhelper import init_database, add_user, recordexists
from werkzeug.security import generate_password_hash

def create_default_admin():
    """Create the default admin user"""
    # Initialize database tables
    print("Initializing database...")
    init_database()
    print("Database initialized!")
    
    # Admin credentials
    email = "admin@admin.com"
    password = "admin123"
    name = "Administrator"
    
    # Check if admin user already exists
    if recordexists('users', email=email):
        print(f"\n⚠️  Admin user with email '{email}' already exists.")
        print("\nYou can login using:")
        print(f"Email: {email}")
        print("Password: admin123")
        print("\nIf the password doesn't work, you need to reset it manually.")
        return False
    
    # Create new admin user
    hashed_password = generate_password_hash(password)
    
    if add_user(name, email, hashed_password):
        print("\n✓ Default admin user created successfully!")
        print(f"Email: {email}")
        print(f"Password: {password}")
        print("\nYou can now login to the system using these credentials.")
        return True
    else:
        print("\n✗ Failed to create admin user.")
        print("This usually means the user already exists in the database.")
        return False

if __name__ == "__main__":
    create_default_admin()