import os
from app import app, db, BlogPost

# Temporarily load .env for local testing of this script, 
# but in Vercel it uses environment variables.
from dotenv import load_dotenv
load_dotenv() 

def setup_database():
    """
    Initializes the Flask app context and creates all database tables 
    if they do not already exist on the remote PostgreSQL server.
    """
    print("Starting database setup...")
    # Ensure app configuration is loaded
    if not app.config.get('SQLALCHEMY_DATABASE_URI'):
         raise EnvironmentError("DATABASE_URL is not configured for the app context.")
         
    with app.app_context():
        try:
            # This creates tables based on the BlogPost model defined in app.py
            db.create_all()
            print("Database tables created or already existed successfully.")
        except Exception as e:
            print(f"Error during database setup: {e}")
            # Re-raise the exception to fail the script if database connection fails
            raise

if __name__ == '__main__':
    setup_database()