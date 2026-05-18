"""Quick script to test Redshift password auth and discover available databases."""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

import redshift_connector

host = os.getenv("REDSHIFT_HOST", "")
port = int(os.getenv("REDSHIFT_PORT", "5439"))
dbname = os.getenv("REDSHIFT_DBNAME", "dev")
user = os.getenv("REDSHIFT_USER", "")
password = os.getenv("REDSHIFT_PASSWORD", "")

if not host or not user or not password:
    print("ERROR: Set REDSHIFT_HOST, REDSHIFT_USER, REDSHIFT_PASSWORD in .env")
    sys.exit(1)

conn = redshift_connector.connect(host=host, port=port, database=dbname, user=user, password=password)
cursor = conn.cursor()

cursor.execute("SELECT current_database()")
print(f"Connected to DB: {cursor.fetchone()[0]}\n")

cursor.execute("""
    SELECT schemaname, tablename
    FROM pg_tables
    WHERE schemaname NOT IN ('pg_catalog','information_schema','pg_internal')
    ORDER BY schemaname, tablename
""")
tables = cursor.fetchall()
print(f"All tables ({len(tables)} total):")
for schema, table in tables:
    print(f"  {schema}.{table}")

# Show columns for each table
print("\n--- COLUMN DETAILS ---")
for schema, table in tables:
    cursor.execute(f"""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = '{schema}' AND table_name = '{table}'
        ORDER BY ordinal_position
    """)
    cols = cursor.fetchall()
    print(f"\n{schema}.{table}:")
    for col, dtype in cols:
        print(f"  {col} ({dtype})")

conn.close()
