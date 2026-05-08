from pymilvus import connections

from pymilvus import Collection

connections.connect(
    alias="default",
    host="13.234.112.186",
    port="19530"
)

collection = Collection("dtc_embeddings")

# Delete everything
collection.delete(expr="id >= 0")

# Optional: compact to reclaim space
collection.compact()

print("All embeddings deleted")