import random
import datetime
import json
from faker import Faker
import psycopg2
from psycopg2.extras import execute_values, Json

fake = Faker()

# Database connection
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="unlockit",
    dbname="VoiceCart"
)
cur = conn.cursor()

# Specific product types including apples
specific_products = [
    # Apples - for testing
    {"name": "Red Apples", "category": "Food", "price": (2, 5), "brand": "Fresh Farm"},
    {"name": "Green Apples", "category": "Food", "price": (2, 5), "brand": "Organic Valley"},
    {"name": "Gala Apples", "category": "Food", "price": (3, 6), "brand": "Local Farm"},
    {"name": "Fuji Apples", "category": "Food", "price": (3, 6), "brand": "Premium Fruits"},
    
    # Other food items
    {"name": "Milk", "category": "Food", "price": (2, 4), "brand": "Dairy Fresh"},
    {"name": "Bread", "category": "Food", "price": (1, 3), "brand": "Wonder"},
    {"name": "Cheese", "category": "Food", "price": (4, 8), "brand": "Kraft"},
    
    # Electronics
    {"name": "Smartphone", "category": "Electronics", "price": (200, 800), "brand": "Samsung"},
    {"name": "Laptop", "category": "Electronics", "price": (500, 1500), "brand": "Dell"},
]

rows = []

print("Generating specific products including apples...")

# Add specific products first
for product in specific_products:
    # Create 2-3 variants of each product
    for variant in range(random.randint(2, 3)):
        variant_suffix = ["", "Premium", "Organic", "Fresh"][variant % 4]
        name = f"{variant_suffix} {product['name']}".strip()
        
        specs_json = {
            "category": product['category'],
            "weight": f"{round(random.uniform(0.5, 2.0), 1)} kg",
            "origin": fake.country(),
            "organic": random.choice([True, False]),
            "features": [fake.word() for _ in range(2)]
        }
        
        price = round(random.uniform(product['price'][0], product['price'][1]), 2)
        
        rows.append(
            (
                name,                                         # name
                fake.sentence(),                              # description
                Json(specs_json),                             # specs
                price,                                        # price
                True,                                         # for_sale
                random.randint(50, 200),                      # stock
                None,                                         # image
                product['brand'],                             # brand_name
                datetime.datetime.utcnow()
                    - datetime.timedelta(days=random.randint(0, 30)),  # created_at
                round(random.uniform(3.5, 5.0), 1),           # avg_rating
                random.randint(10, 100),                      # num_reviews
                random.randint(20, 300)                       # num_sold
            )
        )

# Add more random products
brands = ["acme", "globex", "initech", "umbrella", "stark"]
categories = ["Electronics", "Food", "Clothing", "Books", "Home"]

for i in range(70):  # Add 70 more random products
    specs_json = {
        "category": random.choice(categories),
        "weight": f"{round(random.uniform(0.1, 10.0), 2)} kg",
        "dimensions": f"{random.randint(10, 50)}x{random.randint(10, 50)}x{random.randint(5, 30)} cm",
        "material": random.choice(["plastic", "metal", "wood", "fabric", "glass"]),
        "color": fake.color_name()
    }
    
    rows.append(
        (
            fake.unique.word().title(),                       # name
            fake.sentence(),                                  # description
            Json(specs_json),                                 # specs
            round(random.uniform(10, 100), 2),                # price
            random.random() < 0.9,                            # for_sale
            random.randint(0, 100),                           # stock
            None,                                             # image
            random.choice(brands),                            # brand_name
            datetime.datetime.utcnow()
                - datetime.timedelta(days=random.randint(0, 30)),  # created_at
            round(random.uniform(1.0, 5.0), 1),               # avg_rating
            random.randint(0, 500),                           # num_reviews
            random.randint(0, 200)                            # num_sold
        )
    )

# SQL Insert statement
sql = """
INSERT INTO products
       (name, description, specs, price, for_sale, stock, image, brand_name, created_at, avg_rating, num_reviews, num_sold)
VALUES %s
"""

try:
    print(f"Inserting {len(rows)} products into database...")
    execute_values(cur, sql, rows)
    conn.commit()
    print(f"✅ Successfully inserted {len(rows)} products!")
    
    # Verify the insert
    cur.execute("SELECT COUNT(*) FROM products")
    total_count = cur.fetchone()[0]
    print(f"Total products in database: {total_count}")
    
    # Show apple products specifically
    cur.execute("SELECT id, name, price, brand_name FROM products WHERE name ILIKE '%apple%' ORDER BY name")
    apple_products = cur.fetchall()
    print(f"\nApple products available ({len(apple_products)}):")
    for apple in apple_products:
        print(f"  ID: {apple[0]}, Name: {apple[1]}, Price: ${apple[2]}, Brand: {apple[3]}")
    
except psycopg2.Error as e:
    print(f"❌ Database error: {e}")
    print("Error details:", e.pgcode, e.pgerror)
    conn.rollback()
except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    cur.close()
    conn.close()
    print("Database connection closed.")