import os
import psycopg2
from dotenv import load_dotenv
from typing import Optional

# LangChain / LangGraph Imports
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

# Import your database review functions
from reviews_api import get_product_reviews, get_average_rating

load_dotenv()
DB_URL = os.getenv("SUPABASE_URL")

def get_db_connection():
    """Helper function to create a new database connection."""
    return psycopg2.connect(DB_URL)

# ---------------------------------------------------------------------------
# 1. Product & Order Tools (PostgreSQL Updated)
# ---------------------------------------------------------------------------
@tool
def search_products(query: str, max_price: Optional[float] = None) -> str:
    """Search the product database by keyword and optional max price."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        sql = """
            SELECT id, name, description, price, stock 
            FROM products 
            WHERE (name ILIKE %s OR description ILIKE %s OR category ILIKE %s)
        """
        search_term = f"%{query}%"
        params = [search_term, search_term, search_term]
        
        if max_price is not None:
            sql += " AND price <= %s"
            params.append(max_price)
            
        cursor.execute(sql, tuple(params))
        results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not results:
            return "No products found matching your criteria."
            
        formatted_results = []
        for row in results:
            formatted_results.append(f"ID: {row[0]} | Name: {row[1]} | Price: ${row[3]} | Stock: {row[4]}\nDescription: {row[2]}")
            
        return "\n\n".join(formatted_results)
        
    except Exception as e:
        return f"Database error: {e}"

@tool
def place_order(customer_name: str, product_id: int, quantity: int) -> str:
    """Place an order for a product.
    CRITICAL INSTRUCTIONS:
    - You MUST know the exact integer product_id. Use search_products first if needed.
    - You MUST know the customer's real name.
    - NEVER pass placeholder strings like "Unknown".
    - Use this ONLY after the user explicitly confirms the purchase.
    """
    
    # --- HARD GUARDRAILS (Protects the Database from the AI) ---
    invalid_names = ["unknown", "none", "n/a", "guest", ""]
    if customer_name.strip().lower() in invalid_names:
        return "ERROR: Database write blocked. You failed to get the user's real name. You MUST stop and ask the user for their name before trying again."
        
    if quantity <= 0:
        return "ERROR: Quantity must be 1 or greater."
    # -----------------------------------------------------------

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Check stock and price
        cursor.execute("SELECT price, stock FROM products WHERE id = %s", (product_id,))
        product = cursor.fetchone()
        
        if not product:
            return "Error: Product ID not found in the database."
            
        price, stock = product
        
        if stock < quantity:
            return f"Error: Insufficient stock. Only {stock} left."
            
        total_price = price * quantity
        
        # 2. Find or Create the User
        cursor.execute("SELECT id FROM users WHERE name ILIKE %s", (customer_name,))
        user_record = cursor.fetchone()
        
        if user_record:
            db_user_id = user_record[0]
        else:
            fake_email = f"{customer_name.lower().replace(' ', '')}@guest.com"
            cursor.execute("""
                INSERT INTO users (name, email) 
                VALUES (%s, %s) RETURNING id
            """, (customer_name, fake_email))
            db_user_id = cursor.fetchone()[0]
        
        # 3. Insert the new order
        cursor.execute("""
            INSERT INTO orders (user_id, product_id, quantity, total_price, status)
            VALUES (%s, %s, %s, %s, 'Confirmed')
        """, (db_user_id, product_id, quantity, total_price))
        
        # 4. Deduct the purchased quantity from the product stock
        cursor.execute("""
            UPDATE products 
            SET stock = stock - %s 
            WHERE id = %s
        """, (quantity, product_id))
        
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
# 3. Vision Tool
# ---------------------------------------------------------------------------
@tool
def describe_product_image(image_path: str) -> str:
    """Analyze a product image and return search keywords. Pass the exact image path."""
    # Note: If you had a custom implementation for Llama Vision here, replace this function body!
    return "Image analyzed. Use the search_products tool to look for items matching this image."

# ---------------------------------------------------------------------------
# 4. Agent Orchestration
# ---------------------------------------------------------------------------

# Initialize the LLM (Change the model string if you used a different one!)
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)

# Bind all tools to the agent
tools = [
    search_products, 
    place_order, 
    check_reviews, 
    check_average_rating, 
    describe_product_image
]

# Set the guardrails
system_prompt = """You are a highly capable AI shopping assistant.
You help users browse products, read reviews, and check out.

CRITICAL RULES:
1. NEVER guess a product_id. Always use the search_products tool first to find the exact integer ID.
2. NEVER place an order unless the user explicitly confirms the purchase.
3. ALWAYS ask for the user's name before placing an order if you don't know it. DO NOT use placeholders like "Unknown".
4. If you are missing the product_id or the customer_name, ASK the user. Do not call the place_order tool until you have real values.
"""

# Compile the final agent to be imported by app.py
agent = create_react_agent(llm, tools, prompt=system_prompt)