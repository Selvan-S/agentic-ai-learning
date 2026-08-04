import sqlite3
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings # Replace with OpenAIEmbeddings if you are using OpenAI

def build_vector_db():
    print("Fetching products from SQLite database...")
    # 1. Connect to your existing SQLite database
    conn = sqlite3.connect('shopping.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, description, price FROM products")
    products = cursor.fetchall()
    conn.close()

    texts = []
    metadatas = []

    print(f"Found {len(products)} products. Processing...")
    for product in products:
        prod_id, name, description, price = product
        
        # 2. Combine the details into a single text block for the AI to understand semantically
        text_block = f"Name: {name}\nDescription: {description}\nPrice: ${price}"
        texts.append(text_block)
        
        # 3. Save the ID and Name as metadata so we can reference the exact product later
        metadatas.append({"id": prod_id, "name": name})

    print("Generating embeddings and saving to Chroma...")
    # 4. Initialize the embedding model (translates text to numbers)
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # 5. Create the vector store AND persist it to a local folder
    vector_db = Chroma.from_texts(
        texts=texts,
        metadatas=metadatas,
        embedding=embeddings,
        collection_name="shopping_products",
        persist_directory="./chroma_db" # THE FIX: This saves the DB to your hard drive
    )
    
    print("Success! Chroma database built and saved to './chroma_db'.")

if __name__ == "__main__":
    build_vector_db()