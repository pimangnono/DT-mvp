# build_rag_database.py
"""
A one-time utility script to set up and populate the PGVector database
with embeddings from the flows.xlsx file.

You only need to run this script once, or whenever you update flows.xlsx.
"""
import pandas as pd
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import time

# --- Database Configuration ---
DB_CONFIG = {
    "dbname": "lca_data",
    "user": "lca_user",
    "password": "lca_password",
    "host": "localhost",
    "port": "5432"
}

# --- Global Variables ---
MODEL = SentenceTransformer('all-MiniLM-L6-v2')

def setup_pgvector_database(conn):
    """Creates the necessary table and extension in PostgreSQL."""
    with conn.cursor() as cur:
        print(" - Enabling PGVector extension...")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print(" - Creating 'flows' table (dropping if it exists to ensure a clean slate)...")
        cur.execute("DROP TABLE IF EXISTS flows;") # Drop old table for a clean rebuild
        embedding_dim = MODEL.get_sentence_embedding_dimension()
        cur.execute(f"""
            CREATE TABLE flows (
                id UUID PRIMARY KEY, name TEXT, name_embedding VECTOR({embedding_dim}),
                flow_type TEXT, location TEXT, category TEXT
            );
        """)
        conn.commit()

def populate_database_from_excel(conn, excel_path="flows.xlsx"):
    """Reads flows.xlsx, creates embeddings, and populates the PGVector DB."""
    try:
        df = pd.read_excel(excel_path)
    except FileNotFoundError:
        print(f"FATAL: {excel_path} not found.")
        return
        
    print(f"Populating database with {len(df)} flows. This will take a few minutes...")
    df['combined_text'] = df['name'].fillna('') + ' | ' + df['location'].fillna('') + ' | ' + df['category'].fillna('')
    embeddings = MODEL.encode(df['combined_text'].tolist(), show_progress_bar=True)
    
    with conn.cursor() as cur:
        for index, row in df.iterrows():
            cur.execute(
                "INSERT INTO flows (id, name, name_embedding, flow_type, location, category) VALUES (%s, %s, %s, %s, %s, %s)",
                (row['id'], row['name'], embeddings[index], row['flow_type'], row['location'], row['category'])
            )
        conn.commit()
    print("\nDatabase population complete.")

def main():
    """Main function to run the database setup."""
    print("--- [RAG DATABASE BUILD SCRIPT] ---")
    start_time = time.time()
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        register_vector(conn)
        
        setup_pgvector_database(conn)
        populate_database_from_excel(conn)
        
        conn.close()
        end_time = time.time()
        print(f"\n--- [BUILD COMPLETE in {end_time - start_time:.2f} seconds] ---")
    except Exception as e:
        print(f"\n--- [BUILD FAILED] ---")
        print(f"An error occurred: {e}")
        print("Please ensure your PostgreSQL Docker container is running and the credentials in DB_CONFIG are correct.")

if __name__ == "__main__":
    main()