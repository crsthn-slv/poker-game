import os
import sys
from supabase_client import get_supabase_client

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def setup_database():
    print("Setting up database...")
    
    # Get client
    try:
        client = get_supabase_client()
        conn = client.connect()
        cursor = conn.cursor()
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        return

    # Read schema file
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    try:
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
    except FileNotFoundError:
        print(f"Schema file not found at {schema_path}")
        return

    # Execute schema
    try:
        print("Executing schema...")
        cursor.execute(schema_sql)
        conn.commit()
        print("Database setup completed successfully!")
    except Exception as e:
        conn.rollback()
        print(f"Error executing schema: {e}")
    finally:
        cursor.close()
        client.close()

if __name__ == "__main__":
    setup_database()
