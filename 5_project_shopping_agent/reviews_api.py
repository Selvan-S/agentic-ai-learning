import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
DB_URL = os.getenv("SUPABASE_URL")

def get_db_connection():
    """Helper function to get a database connection."""
    return psycopg2.connect(DB_URL)

def get_product_reviews(product_id: int) -> str:
    """Fetch all reviews for a specific product."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # PROPER RELATIONAL QUERY: JOIN reviews with users to get the name
        query = """
            SELECT u.name, r.rating, r.comment, r.review_date 
            FROM reviews r
            JOIN users u ON r.user_id = u.id
            WHERE r.product_id = %s
            ORDER BY r.review_date DESC
        """
        cursor.execute(query, (product_id,))
        reviews = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not reviews:
            return "No reviews found for this product."
            
        formatted_reviews = []
        for review in reviews:
            name, rating, comment, date = review
            date_str = date.strftime("%Y-%m-%d")
            formatted_reviews.append(f"- {name} ({rating}/5 on {date_str}): {comment}")
            
        return "\n".join(formatted_reviews)
        
    except Exception as e:
        return f"Error fetching reviews: {e}"

def get_average_rating(product_id: int) -> str:
    """Fetch the average rating and total review count for a product."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT AVG(rating), COUNT(*) 
            FROM reviews 
            WHERE product_id = %s
        """
        cursor.execute(query, (product_id,))
        result = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if result and result[1] > 0:
            avg_rating = round(result[0], 1)
            count = result[1]
            return f"Average Rating: {avg_rating}/5 (based on {count} reviews)"
        else:
            return "No ratings available for this product."
            
    except Exception as e:
        return f"Error fetching average rating: {e}"

if __name__ == "__main__":
    print("Testing get_average_rating for Product ID 1...")
    print(get_average_rating(1))
    print("\nTesting get_product_reviews for Product ID 1...")
    print(get_product_reviews(1))