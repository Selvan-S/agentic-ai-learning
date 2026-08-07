import os
import base64
import psycopg2
from dotenv import load_dotenv
from typing import Optional

# LangChain / LangGraph Imports
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Import your database review functions
from reviews_api import get_product_reviews, get_average_rating

load_dotenv()
DB_URL = os.getenv("SUPABASE_URL")
PERSIST_DIRECTORY = "./chroma_db"

def get_db_connection():
    return psycopg2.connect(DB_URL)

# Load Vector Store for Semantic Search
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_store = Chroma(persist_directory=PERSIST_DIRECTORY, embedding_function=embeddings)

# ---------------------------------------------------------------------------
# 1. Semantic Search & Order Tools
# ---------------------------------------------------------------------------
@tool
def search_products(query: str, max_price: Optional[float] = None) -> str:
    """Search the product catalog using intelligent semantic search (finds items by meaning, not just exact keywords)."""
    try:
        # Perform vector similarity search
        docs = vector_store.similarity_search(query, k=5)
        
        if not docs:
            return "No products found matching your search."
            
        formatted_results = []
        for doc in docs:
            meta = doc.metadata
            # Optional price filter post-retrieval
            if max_price is not None and meta["price"] > max_price:
                continue
            formatted_results.append(
                f"ID: {meta['product_id']} | Name: {meta['name']} | Category: {meta['category']} | Price: ${meta['price']} | Stock: {meta['stock']}\nDetails: {doc.page_content}"
            )
            
        if not formatted_results:
            return "No products found within your price range."
            
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        return f"Search error: {e}"

@tool
def place_order(customer_name: str, product_id: int, quantity: int) -> str:
    """Place an order for a product. Requires valid customer name, integer product_id, and user confirmation."""
    invalid_names = ["unknown", "none", "n/a", "guest", ""]
    if customer_name.strip().lower() in invalid_names:
        return "ERROR: Database write blocked. You must ask the user for their real name before checking out."
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT price, stock FROM products WHERE id = %s", (product_id,))
        product = cursor.fetchone()
        
        if not product:
            return "Error: Product ID not found in the database."
            
        price, stock = product
        if stock < quantity:
            return f"Error: Insufficient stock. Only {stock} left."
            
        total_price = price * quantity
        
        cursor.execute("SELECT id FROM users WHERE name ILIKE %s", (customer_name,))
        user_record = cursor.fetchone()
        
        if user_record:
            db_user_id = user_record[0]
        else:
            fake_email = f"{customer_name.lower().replace(' ', '')}@guest.com"
            cursor.execute("INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id", (customer_name, fake_email))
            db_user_id = cursor.fetchone()[0]
        
        cursor.execute("""
            INSERT INTO orders (user_id, product_id, quantity, total_price, status)
            VALUES (%s, %s, %s, %s, 'Confirmed')
        """, (db_user_id, product_id, quantity, total_price))
        
        cursor.execute("UPDATE products SET stock = stock - %s WHERE id = %s", (quantity, product_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return f"Success! Order placed for {quantity} unit(s) under the name '{customer_name}'. Total charged: ${total_price:.2f}."
        
    except Exception as e:
        return f"Database error during checkout: {e}"

# ---------------------------------------------------------------------------
# 2. Review Tools
# ---------------------------------------------------------------------------
@tool
def check_reviews(product_id: int) -> str:
    """Fetch all reviews and comments for a specific product ID."""
    return get_product_reviews(product_id)

@tool
def check_average_rating(product_id: int) -> str:
    """Fetch the average rating and review count for a specific product ID."""
    return get_average_rating(product_id)

# ---------------------------------------------------------------------------
# 3. Vision Tool (Multimodal Groq Integration)
# ---------------------------------------------------------------------------
@tool
def describe_product_image(image_path: str) -> str:
    """Analyze an uploaded product image using a vision model to extract search keywords. Pass the exact image file path."""
    try:
        with open(image_path, "rb") as image_file:
            encoded_image = base64.b64encode(image_file.read()).decode('utf-8')
            
        # FIX 1: Updated to Groq's current supported multimodal model
        vision_llm = ChatGroq(model="qwen/qwen3.6-27b", temperature=0)
        
        # FIX 2: Strict prompt to prevent chatty paragraphs from ruining the vector search
        message = {
            "role": "user",
            "content": [
                {"type": "text", "text": "What is the primary grocery item in this image? Reply ONLY with 2-3 concise search keywords (e.g., 'Raw Almonds' or 'Green Tea'). Do not include any conversational text, descriptions, or punctuation."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{encoded_image}"}}
            ]
        }
        
        response = vision_llm.invoke([message])
        return f"Image analysis complete. Suggested search terms: {response.content}"
    except Exception as e:
        return f"Failed to analyze image: {e}"

# ---------------------------------------------------------------------------
# 4. Agent Orchestration
# ---------------------------------------------------------------------------
llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0)

tools = [
    search_products, 
    place_order, 
    check_reviews, 
    check_average_rating, 
    describe_product_image
]

system_prompt = """You are a highly capable AI shopping assistant for an organic grocery store.
You help users browse products semantically, check reviews, analyze uploaded product images, and check out safely.

CRITICAL RULES:
1. NEVER guess a product_id. Always use the search_products tool first to find the exact integer ID.
2. NEVER place an order unless the user explicitly confirms the purchase.
3. ALWAYS ask for the user's name before placing an order if you don't know it. Never use placeholder strings like "Unknown".
4. If a user uploads an image, use the describe_product_image tool, then automatically execute a search_products query based on the result.
"""

agent = create_react_agent(llm, tools, prompt=system_prompt)