import os
import time
import psycopg2
from psycopg2 import OperationalError

DB_HOST = os.getenv("DB_HOST", "db")
DB_PORT = int(os.getenv("DB_PORT", 5432))
DB_USER = os.getenv("DB_USER", "myuser")
DB_PASS = os.getenv("DB_PASS", "mypassword")
DB_NAME = os.getenv("DB_NAME", "mydb")

def wait_for_db():
    print(f"Waiting for database at {DB_HOST}:{DB_PORT}...")
    while True:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASS,
                dbname=DB_NAME,
            )
            conn.close()
            print("Database is available!")
            break
        except OperationalError:
            print("Database not ready, sleeping 2 seconds...")
            time.sleep(2)

if __name__ == "__main__":
    wait_for_db()
