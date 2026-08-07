import os
import psycopg2
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

load_dotenv()
DB_URL = os.getenv("SUPABASE_URL")
PERSIST_DIRECTORY = "./chroma_db"

def fetch_products_from_supabase():
    """Pulls all products from your Supabase cloud database."""
    print("Connecting to Supabase to fetch product catalog...")
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, category, price, description, stock FROM products")
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def build_vector_database():
    rows = fetch_products_from_supabase()
    print(f"Fetched {len(rows)} products from Supabase. Building documents...")
    
    documents = []
    for row in rows:
        product_id, name, category, price, description, stock = row
        
        # Semantic text combination for embeddings
        text = f"Product Name: {name}. Category: {category}. Description: {description}. Price: ${price}"
        
        metadata = {
            "product_id": int(product_id),
            "name": str(name),
            "category": str(category),
            "price": float(price),
            "stock": int(stock)
        }
        documents.append(Document(page_content=text, metadata=metadata))
        
    print("Initializing embedding model (all-MiniLM-L6-v2)...")
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    print(f"Saving vector database to {PERSIST_DIRECTORY}...")
    vector_store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=PERSIST_DIRECTORY
    )
    print("Vector database successfully built and stored!")

if __name__ == "__main__":
    build_vector_db = build_vector_database
    build_vector_db()