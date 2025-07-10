
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from backend.app.database import engine
from backend.app.models import Base

def reset_database():
    """Drop all tables and recreate them"""
    try:
        print("Dropping all tables...")
        Base.metadata.drop_all(bind=engine)
        print("✅ All tables dropped successfully")
        
        print("Creating all tables...")
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully")
        
        print("🎉 Database reset complete!")
        
    except Exception as e:
        print(f"❌ Error resetting database: {e}")

if __name__ == "__main__":
    reset_database()