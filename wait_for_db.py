import os
import time
import psycopg2
from psycopg2 import OperationalError
from app.utils.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

def wait_for_db():
    print(f"Waiting for database at {DB_HOST}:{DB_PORT}...")
    while True:
        try:
            conn = psycopg2.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
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
