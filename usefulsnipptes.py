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

# First, let's check the exact table structure
print("Checking table structure...")
cur.execute("""
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns 
    WHERE table_name = 'products'
    ORDER BY ordinal_position;
""")

columns = cur.fetchall()
print("Table columns:")
for col in columns:
    print(f"  {col[0]} ({col[1]}) - Nullable: {col[2]}")

# Generate sample data
rows = []
brands = ["acme", "globex", "initech", "umbrella", "stark"]
categories = ["Electronics", "Food", "Clothing", "Books", "Home"]

print("\nGenerating 100 sample products...")

for i in range(100):
    # Create description as JSON object instead of plain text
    description_json = {
        "summary": fake.sentence(),
        "details": fake.text(max_nb_chars=200),
        "features": [fake.word() for _ in range(random.randint(2, 5))],
        "category": random.choice(categories),
        "weight": f"{round(random.uniform(0.1, 10.0), 2)} kg",
        "dimensions": f"{random.randint(10, 50)}x{random.randint(10, 50)}x{random.randint(5, 30)} cm"
    }
    
    rows.append(
        (
            fake.unique.word().title(),                       # name
            Json(description_json),                           # description (JSON)
            round(random.uniform(10, 100), 2),                # price
            random.random() < 0.9,                            # for_sale
            random.randint(0, 100),                           # stock
            random.choice(brands),                            # brand_name
            datetime.datetime.utcnow()
                - datetime.timedelta(days=random.randint(0, 30)),  # created_at
        )
    )

# SQL Insert statement
sql = """
INSERT INTO products
       (name, description, price, for_sale, stock, brand_name, created_at)
VALUES %s
"""

try:
    print("Inserting products into database...")
    execute_values(cur, sql, rows)   # bulk insert
    conn.commit()
    print(f"✅ Successfully inserted {len(rows)} products!")
    
    # Verify the insert
    cur.execute("SELECT COUNT(*) FROM products")
    total_count = cur.fetchone()[0]
    print(f"Total products in database: {total_count}")
    
    # Show a few sample products
    cur.execute("SELECT id, name, price, brand_name, description FROM products ORDER BY id DESC LIMIT 3")
    samples = cur.fetchall()
    print("\nLast 3 products added:")
    for product in samples:
        print(f"  ID: {product[0]}")
        print(f"  Name: {product[1]}")
        print(f"  Price: ${product[2]}")
        print(f"  Brand: {product[3]}")
        print(f"  Description: {json.dumps(product[4], indent=2)}")
        print("-" * 50)
    
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