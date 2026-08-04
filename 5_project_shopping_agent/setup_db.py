import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Get the Supabase connection string
DB_URL = os.getenv("SUPABASE_URL")

def setup_database():
    try:
        print("Connecting to Supabase...")
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()

        print("Wiping old tables for a clean slate...")
        cursor.execute("DROP TABLE IF EXISTS reviews, orders, products, users CASCADE;")

        print("Creating new tables...")
        cursor.execute("""
            CREATE TABLE users (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE products (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                category TEXT,
                price NUMERIC(10, 2),
                stock INTEGER DEFAULT 0
            )
        """)

        cursor.execute("""
            CREATE TABLE reviews (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                rating NUMERIC(2, 1) CHECK (rating >= 1 AND rating <= 5),
                comment TEXT,
                review_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE orders (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
                product_id INTEGER REFERENCES products(id) ON DELETE CASCADE,
                quantity INTEGER,
                total_price NUMERIC(10, 2),
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'Pending'
            )
        """)
        
        print("Inserting 32 realistic dummy products...")
        realistic_products = [
            # Honey (IDs 1-8)
            ("Raw Organic Manuka Honey", "Premium antibacterial Manuka honey from New Zealand.", "Honey", 35.99, 50),
            ("Wildflower Raw Honey", "Unfiltered, cold-pressed wildflower honey.", "Honey", 12.50, 100),
            ("Clover Pure Honey", "Classic sweet clover honey, great for baking.", "Honey", 9.99, 150),
            ("Acacia Light Honey", "Mild and clear acacia honey, perfect for tea.", "Honey", 14.00, 80),
            ("Buckwheat Dark Honey", "Robust, dark honey with high antioxidant levels.", "Honey", 11.50, 60),
            ("Orange Blossom Honey", "Light, citrus-infused raw honey.", "Honey", 13.99, 90),
            ("Creamed Spun Honey", "Smooth and spreadable raw creamed honey.", "Honey", 15.50, 75),
            ("Eucalyptus Honey", "Distinctive herbal and fruity flavor.", "Honey", 16.00, 40),
            
            # Oils (IDs 9-12)
            ("Extra Virgin Olive Oil", "Cold-pressed, organic EVOO from Italy.", "Oils", 22.99, 85),
            ("Avocado Oil", "High heat cooking oil with neutral flavor.", "Oils", 18.50, 110),
            ("Cold-Pressed Coconut Oil", "Unrefined organic coconut oil for cooking and skin.", "Oils", 14.99, 200),
            ("Toasted Sesame Oil", "Aromatic finishing oil for Asian cuisine.", "Oils", 10.50, 65),
            
            # Nuts & Seeds (IDs 13-16)
            ("Raw Almonds", "Unsalted, organic raw California almonds.", "Nuts & Seeds", 15.99, 120),
            ("Roasted Cashews", "Lightly sea-salted roasted cashews.", "Nuts & Seeds", 17.50, 90),
            ("Organic Chia Seeds", "High-fiber, omega-3 rich raw chia seeds.", "Nuts & Seeds", 11.99, 150),
            ("Premium Trail Mix", "Energy mix of walnuts, pecans, almonds, and dried cranberries.", "Nuts & Seeds", 19.99, 80),
            
            # Grains (IDs 17-20)
            ("Organic White Quinoa", "Gluten-free, high-protein ancient grain.", "Grains", 8.99, 200),
            ("Steel Cut Oats", "Hearty, unrefined steel cut oats for a classic breakfast.", "Grains", 6.50, 250),
            ("Jasmine Brown Rice", "Aromatic, whole grain Thai jasmine rice.", "Grains", 10.99, 140),
            ("Farro", "Nutty and chewy whole grain, excellent for salads.", "Grains", 7.99, 100),
            
            # Tea & Coffee (IDs 21-24)
            ("Sencha Green Tea", "Fresh, loose-leaf Japanese Sencha.", "Tea & Coffee", 19.50, 70),
            ("Chamomile Herbal Tea", "Caffeine-free whole chamomile flowers.", "Tea & Coffee", 12.00, 130),
            ("Ethiopian Single Origin Coffee", "Light roast, whole bean coffee with floral notes.", "Tea & Coffee", 21.99, 85),
            ("French Roast Espresso Blend", "Dark, bold, and oily beans for the perfect pull.", "Tea & Coffee", 18.99, 110),
            
            # Snacks (IDs 25-28)
            ("Almond Butter Granola", "Oven-baked clusters with almond butter and honey.", "Snacks", 9.50, 160),
            ("Sea Salt Rice Cakes", "Light, airy, and low-calorie snacking.", "Snacks", 4.99, 200),
            ("Dried Mango Slices", "Unsweetened, chewy, and naturally sweet dried mango.", "Snacks", 14.50, 95),
            ("Dark Chocolate Almond Bark", "Crispy snack with 70% dark chocolate and roasted almonds.", "Snacks", 11.99, 120),
            
            # Dairy Alternatives (IDs 29-32)
            ("Unsweetened Almond Milk", "Creamy, dairy-free milk alternative (1L).", "Dairy Alternatives", 4.50, 300),
            ("Barista Blend Oat Milk", "Specially formulated to froth perfectly for lattes.", "Dairy Alternatives", 5.99, 250),
            ("Full Fat Coconut Milk", "Canned organic coconut milk for cooking and curries.", "Dairy Alternatives", 3.50, 400),
            ("Vanilla Soy Milk", "Fortified soy milk with a hint of natural vanilla.", "Dairy Alternatives", 4.99, 220)
        ]

        # Insert realistic products safely
        for product in realistic_products:
            cursor.execute("""
                INSERT INTO products (name, description, category, price, stock)
                VALUES (%s, %s, %s, %s, %s)
            """, product)

        print("Processing raw reviews and creating user accounts...")
        raw_reviews = [
            (1, 5.0, "Alice",   "Amazing honey! Best I've ever tried."),
            (1, 4.0, "Bob",     "Good quality, will buy again."),
            (1, 5.0, "Carol",   "Excellent raw flavor, very pure."),
            (1, 4.5, "Dave",    "Very good, love that it's unfiltered."),
            (2, 4.0, "Eve",     "Decent honey for the price."),
            (2, 3.5, "Frank",   "Average, nothing special."),
            (2, 4.0, "Grace",   "Good everyday honey."),
            (3, 5.0, "Henry",   "Worth every penny, incredible quality."),
            (3, 4.5, "Iris",    "Excellent antibacterial properties."),
            (3, 5.0, "Jack",    "Best honey I have ever tasted."),
            (4, 3.5, "Kate",    "Okay for cooking, nothing fancy."),
            (4, 3.5, "Leo",     "Nothing special, pretty generic."),
            (4, 3.5, "Mia",     "Average clover honey."),
            (5, 5.0, "Noah",    "Rich bold flavor, great in tea."),
            (5, 4.0, "Olivia",  "Good strong honey, unique taste."),
            (5, 5.0, "Paul",    "Love the dark color and depth."),
            (5, 4.5, "Quinn",   "Great organic option at this price."),
            (6, 4.0, "Rachel",  "Nice floral flavor."),
            (6, 4.5, "Sam",     "Lovely and delicate."),
            (6, 4.0, "Tina",    "Good for baking."),
            (7, 5.0, "Uma",     "Perfect mild flavor, love it!"),
            (7, 4.5, "Victor",  "Excellent light honey."),
            (7, 4.5, "Wendy",   "Great product, very pure taste."),
            (7, 5.0, "Xavier",  "Wonderful, highly recommend."),
            (8, 4.0, "Yvonne",  "Nice spreadable texture."),
            (8, 4.0, "Zack",    "Good on toast."),
            (8, 4.0, "Amy",     "Decent creamed honey."),
            (9,  5.0, "Brian",  "Best olive oil I've used, very fresh."),
            (9,  4.5, "Clara",  "Great flavor, organic certified."),
            (9,  4.5, "Derek",  "Excellent quality, love it."),
            (10, 4.0, "Elena",  "Good for frying, neutral taste."),
            (10, 3.5, "Felix",  "Does the job, nothing exciting."),
            (10, 3.5, "Gina",   "Decent but slightly greasy."),
            (11, 5.0, "Harry",  "Great for smoothies, very fresh."),
            (11, 4.0, "Isla",   "Good omega-3 source, mild flavor."),
            (11, 4.5, "James",  "Love this for salad dressings."),
            (12, 4.5, "Karen",  "Excellent smoke point, tastes great."),
            (12, 4.0, "Liam",   "Good all-purpose oil."),
            (12, 4.5, "Maya",   "Great for cooking and salads."),
            (13, 5.0, "Nate",   "Crunchy and fresh, great snack."),
            (13, 4.5, "Olivia", "Love that they're organic and raw."),
            (13, 4.5, "Peter",  "Perfect size, very fresh."),
            (13, 5.0, "Rita",   "Best almonds I've bought online."),
            (14, 4.0, "Steve",  "Good cashews, nice crunch."),
            (14, 4.0, "Tara",   "Tasty but slightly over-salted."),
            (14, 4.0, "Ursula", "Good value for the quantity."),
            (15, 4.5, "Vince",  "Easy to add to smoothies, love it."),
            (15, 4.5, "Wanda",  "Great fiber source, very fresh."),
            (15, 4.5, "Xena",   "Good quality organic chia seeds."),
            (16, 4.0, "Yuri",   "Good mix, well-balanced variety."),
            (16, 3.5, "Zara",   "A bit too many peanuts for my taste."),
            (16, 4.0, "Alex",   "Nice mix for snacking."),
            (16, 3.5, "Blake",  "Would prefer fewer raisins."),
            (17, 5.0, "Chloe",  "Cooks perfectly, great nutty flavor."),
            (17, 4.5, "Dylan",  "Excellent protein content, love it."),
            (17, 4.5, "Ella",   "Best quinoa I've tried."),
            (18, 4.5, "Finn",   "Great oats, cook quickly and evenly."),
            (18, 4.0, "Gabi",   "Good quality, nice texture."),
            (18, 4.5, "Hugo",   "Reliable everyday oats."),
            (19, 4.5, "Irene",  "Nice chewy texture, great organic choice."),
            (19, 4.5, "Jake",   "Good quality, cooks evenly."),
            (19, 4.5, "Kara",   "Love the organic certification."),
            (20, 4.0, "Lars",   "Great texture, a bit longer to cook."),
            (20, 3.5, "Mona",   "Takes forever to cook but tastes good."),
            (20, 4.0, "Ned",    "Hearty and filling."),
            (21, 5.0, "Opal",   "Delicate flavor, very smooth."),
            (21, 4.5, "Phil",   "Best green tea I've had, very fresh."),
            (21, 4.5, "Quinn",  "Great quality, calming and tasty."),
            (22, 4.0, "Rose",   "Very soothing before bed."),
            (22, 4.5, "Seth",   "Lovely floral notes, very relaxing."),
            (22, 4.0, "Tess",   "Good chamomile, nice and mild."),
            (23, 5.0, "Uri",    "Best coffee I've ever brewed at home."),
            (23, 4.5, "Vera",   "Amazing single-origin flavor."),
            (23, 4.5, "Will",   "Very smooth with great aroma."),
            (23, 5.0, "Xara",   "Exceptional quality, worth every penny."),
            (24, 4.0, "Yael",   "Strong and bold, perfect espresso."),
            (24, 4.0, "Zion",   "Good dark roast, consistent grind."),
            (24, 4.0, "Abe",    "Solid everyday espresso blend."),
            (25, 4.5, "Beth",   "Delicious and not too sweet."),
            (25, 4.5, "Cole",   "Great texture, love the almonds."),
            (25, 4.5, "Dana",   "My go-to breakfast granola."),
            (26, 4.0, "Earl",   "Light and crispy, good for dieting."),
            (26, 3.5, "Faye",   "A bit bland but does the job."),
            (26, 4.0, "Glen",   "Good value, decent snack."),
            (27, 5.0, "Hope",   "So sweet and chewy, love these!"),
            (27, 4.5, "Ivan",   "Great that there's no added sugar."),
            (27, 4.5, "Jade",   "Perfect snack, very natural taste."),
            (28, 4.0, "Kent",   "Good mix, great for hiking."),
            (28, 3.5, "Luna",   "Too many M&Ms, prefer less candy."),
            (28, 3.5, "Marc",   "Decent but not my favorite mix."),
            (29, 4.5, "Nina",   "Great in coffee, smooth texture."),
            (29, 4.5, "Omar",   "Love the organic certification."),
            (29, 4.5, "Pam",    "Tastes great and not too thin."),
            (30, 4.5, "Rex",    "Perfect for lattes, froths well."),
            (30, 4.0, "Sara",   "Good oat milk, slightly sweet."),
            (30, 4.5, "Tom",    "Best barista oat milk I've tried."),
            (31, 4.5, "Una",    "Creamy and rich, great for curries."),
            (31, 4.5, "Vito",   "Full fat and delicious."),
            (31, 4.5, "Wren",   "Perfect coconut milk, great quality."),
            (32, 4.0, "Xio",    "Good protein content, mild flavor."),
            (32, 3.5, "Yosef",  "Slightly thin but good for cereal."),
            (32, 3.5, "Zola",   "Decent soy milk, nothing special."),
        ]

        unique_names = list(set([r[2] for r in raw_reviews]))
        
        # FIX: Using bulletproof for loop
        for name in unique_names:
            fake_email = f"{name.lower().replace(' ', '')}@example.com"
            cursor.execute("""
                INSERT INTO users (name, email)
                VALUES (%s, %s)
            """, (name, fake_email))

        cursor.execute("SELECT name, id FROM users")
        name_to_id = dict(cursor.fetchall())

        print("Inserting mapped reviews...")
        # FIX: Using bulletproof for loop
        for prod_id, rating, name, comment in raw_reviews:
            user_id = name_to_id[name]
            cursor.execute("""
                INSERT INTO reviews (product_id, user_id, rating, comment)
                VALUES (%s, %s, %s, %s)
            """, (prod_id, user_id, rating, comment))

        conn.commit()
        cursor.close()
        conn.close()
        print("Database setup complete! Your robust schema is live in Supabase.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    setup_database()