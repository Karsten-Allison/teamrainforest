import csv
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from pymongo import MongoClient
from pyspark.ml.fpm import FPGrowth
from pyspark.sql import SparkSession, functions as F

start = perf_counter()
client = MongoClient("mongodb://127.0.0.1:27018")
products = client.rainforest_simple.products

# read the customer id and product id from each review into our mongodb
with TemporaryDirectory() as folder:
    path = Path(folder) / "reviews.csv"
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        for product in products.find({}, {"reviews.customer_id": 1}):
            for review in product["reviews"]:
                writer.writerow([review["customer_id"], product["_id"]])

    spark = (SparkSession.builder.master("local[2]").appName("Rainforest pairs")
             .config("spark.driver.extraJavaOptions", "-Xss8m")
             .config("spark.sql.shuffle.partitions", "4").getOrCreate())
    reviews = spark.read.schema("customer string, product string").csv(path.as_uri())

    # make a list of the different products they reviewed
    baskets = reviews.groupBy("customer").agg(F.collect_set("product").alias("items"))

    # customers split into two groups
    group_number = F.pmod(F.xxhash64("customer"), F.lit(5))
    baskets = baskets.withColumn("bucket", group_number).cache()
    # 80% go into training baskets (not group 0) [0,1,2,3,4]
    training_baskets = baskets.filter("bucket != 0")
    # 20% go into testing baskets (group 0) [0,1,2,3,4]
    testing_baskets = baskets.filter("bucket = 0")
    train_count = training_baskets.count()
    test_count = testing_baskets.count()

    # use FPGrowth to find common product groups from the training lists
    support = 0.0005
    model = FPGrowth(minSupport=support, numPartitions=4).fit(training_baskets)

    # keep groups with two products
    pairs = model.freqItemsets.filter(F.size("items") == 2)
    pairs = pairs.select(F.sort_array("items").alias("pair"), "freq")

    # rank the pairs by how many training customers reviewed both
    pairs = pairs.orderBy(F.desc("freq"), "pair")

    # take the top five pairs
    top_five_pairs = pairs.limit(5).collect()
    results = []

    # for each of those five pairs
    for pair, frequency in top_five_pairs:
        # find the testing customers who reviewed both products
        first, second = pair
        matches = testing_baskets.filter(F.array_contains("items", first) & F.array_contains("items", second))
        # count them and save their ids
        customers = sorted(row.customer for row in matches.select("customer").collect())
        titles = []
        for product_id in pair:
            product = products.find_one({"_id": product_id}, {"title": 1})
            titles.append(product["title"])

        # check whether the pair is common in the testing group too
        pair_result = {
            "products": pair,
            "titles": titles,
            "train_customers": frequency,
            "test_customers": len(customers),
            "frequent_in_test": len(customers) >= support * test_count,
            "matching_test_customers": customers,
        }
        results.append(pair_result)
        print(titles, "training:", frequency, "testing:", len(customers))

    seconds = round(perf_counter() - start, 2)

# print the five pairs and save the results
with open("results/patterns.json", "w", encoding="utf-8") as file:
    json.dump({"train_customers": train_count, "test_customers": test_count,
               "min_support": support, "seconds": seconds, "pairs": results}, file, indent=2)
print("saved into results/patterns.json")
