from pymilvus import connections, FieldSchema, CollectionSchema, DataType, Collection, utility
from config import milvus_host, milvus_port

COLLECTION_NAME ="dtc_embeddings"
def connect_milvus():
    connections.connect("default", host= milvus_host, port= milvus_port)


def create_collections(dim=1536):
    if utility.has_collection(COLLECTION_NAME):
        return Collection(COLLECTION_NAME)

    fields =[
        FieldSchema(name="id", dtype= DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="dtc_code", dtype=DataType.VARCHAR, max_length=50),
        FieldSchema(name="step_number",dtype=DataType.INT64),
        FieldSchema(name="text",dtype=DataType.VARCHAR,max_length=65535),
        FieldSchema(name="embedding",dtype=DataType.FLOAT_VECTOR,dim=dim),
    ]
    schema = CollectionSchema(fields, description="DTC diagnostic embeddings")
    collection = Collection(name=COLLECTION_NAME, schema = schema)

    index_params = {
        "metric_type":"IP",
        "index_type":"IVF_FLAT",
        "params":{"nlist":128},
    }
    collection.create_index(field_name="embedding", index_params=index_params)

    return collection

    