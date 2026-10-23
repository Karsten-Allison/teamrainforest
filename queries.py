import json
import time
from pymongo import MongoClient

client = MongoClient("mongodb://127.0.0.1:27018", serverSelectionTimeoutMS=5000)
db = client.rainforest_simple
fields = {"title": 1, "group": 1, "avg_rating": 1, "review_count": 1}
results = {}

if db.products.count_documents({}) == 0:
    print("Run prepare.py and load.py first.")
    raise SystemExit

def show(name, query):
    start = time.time()
    rows = list(query)
    milliseconds = (time.time() - start) * 1000
    print("\n" + name)
    for row in rows:
        print(row)
    print("Time:", round(milliseconds, 3), "ms")
    results[name] = {"milliseconds": round(milliseconds, 3), "products": rows}

show("Find one product", db.products.find({"_id": "0738700797"}, fields))

show("DVDs rated at least 4.5", db.products.find(
    {"group": "DVD", "avg_rating": {"$gte": 4.5}}, fields
).sort("_id", 1).limit(5))

show("Products with at least 100 reviews", db.products.find(
    {"review_count": {"$gte": 100}}, fields
).sort("review_count", -1).limit(5))

show("Products reviewed by one customer", db.products.find(
    {"reviews.customer_id": "A14OJS0VWMOSWO"}, fields
).sort("_id", 1).limit(5))

# Find the starting product, then search for its related ASINs.
product = db.products.find_one({"_id": "0876053886"})
show("Related products", db.products.find(
    {"_id": {"$in": product["similar"]}}, fields
).sort("_id", 1).limit(5))

with open("results/queries.json", "w") as file:
    json.dump(results, file, indent=2)

client.close()

