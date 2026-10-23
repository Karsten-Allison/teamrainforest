import json
import time
from pymongo import MongoClient

client = MongoClient("mongodb://127.0.0.1:27018", serverSelectionTimeoutMS=5000)
db = client.rainforest_simple

if db.products.count_documents({}) > 0:
    print("The data is already loaded. Run queries.py instead.")
    raise SystemExit

start = time.time()
with open("data/products.json", encoding="utf-8") as file:
    products = json.load(file)

db.products.insert_many(products)
db.products.create_index("group")
db.products.create_index("review_count")
db.products.create_index("reviews.customer_id")
seconds = time.time() - start

count = db.products.count_documents({})
example = db.products.find_one({"_id": "0738700797"})
summary = {
    "products_loaded": count,
    "count_matches_file": count == len(products),
    "load_seconds": round(seconds, 3),
    "example_title": example["title"],
    "example_reviews": len(example["reviews"])
}
with open("results/ingestion.json", "w") as file:
    json.dump(summary, file, indent=2)

print(summary)
client.close()
