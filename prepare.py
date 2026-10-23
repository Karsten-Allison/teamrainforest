import json
from datetime import datetime

# currnetly uses the sample data
with open("data/sample.txt", encoding="utf-8") as file:
    text = file.read()

text = text.replace("\x85", " ")
blocks = text.strip().split("\n\n")
products = []
review_count = 0
duplicates = 0

for block in blocks:
    product = {
        "_id": "", "title": "Discontinued product", "group": "Unknown",
        "salesrank": None, "avg_rating": None,
        "similar": [], "categories": [], "reviews": []
    }

    for line in block.split("\n"):
        line = line.strip()
        if line == "":
            continue

        if line.startswith("ASIN:"):
            product["_id"] = line.split(":", 1)[1].strip()
        elif line.startswith("title:"):
            product["title"] = line.split(":", 1)[1].strip()
        elif line.startswith("group:"):
            product["group"] = line.split(":", 1)[1].strip()
        elif line.startswith("salesrank:"):
            rank = int(line.split(":")[1])
            if rank > 0:
                product["salesrank"] = rank
        elif line.startswith("similar:"):
            product["similar"] = line.split()[2:]
        elif line.startswith("|"):
            product["categories"].append(line)
        elif line.startswith("reviews:"):
            parts = line.split()
            if int(parts[2]) > 0:
                product["avg_rating"] = float(parts[7])
        elif line[0].isdigit():
            parts = line.split()
            review = {
                "date": datetime.strptime(parts[0], "%Y-%m-%d").strftime("%Y-%m-%d"),
                "customer_id": parts[2],
                "rating": int(parts[4]),
                "votes": int(parts[6]),
                "helpful": int(parts[8])
            }
            if review["rating"] < 1 or review["rating"] > 5:
                continue
            if review["helpful"] < 0 or review["helpful"] > review["votes"]:
                continue
            if review in product["reviews"]:
                duplicates += 1
            else:
                product["reviews"].append(review)

    if product["_id"] != "":
        product["review_count"] = len(product["reviews"])
        review_count += product["review_count"]
        products.append(product)

with open("data/products.json", "w", encoding="utf-8") as file:
    json.dump(products, file)

summary = {
    "products": len(products),
    "reviews": review_count,
    "duplicate_reviews_removed": duplicates
}
with open("results/preparation.json", "w") as file:
    json.dump(summary, file, indent=2)

print(summary)
