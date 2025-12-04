import os
import sys
from supabase_client import get_supabase_client

def apply_sql(sql_file_path):
    client = get_supabase_client()
    
    with open(sql_file_path, 'r') as f:
        sql_content = f.read()
        
    print(f"Applying SQL from {sql_file_path}...")
    
    try:
        with client.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_content)
                conn.commit()
        print("SQL applied successfully!")
    except Exception as e:
        print(f"Error applying SQL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python apply_sql.py <sql_file_path>")
        sys.exit(1)
        
    apply_sql(sys.argv[1])
