import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
from ingestion.data.ingestion.embedding import get_embs
from ingestion.data.ingestion.setup import connect_milvus
from pymilvus import Collection

def search(collection, query, top_k = 5):

    query_emb = get_embs([query])[0]

    collection.load()
    
    logger.info(f"Type of query embedding: {type(query_emb[0])}")
    results = collection.search(
        data=[query_emb],
        anns_field="embedding",
        param={"metric_type": "IP", "params": {"nprobe": 10}},
        limit=top_k,
        output_fields=["dtc_code", "step_number", "text"],
    )
    hits = []

    for hit in results[0]:
        text = hit.entity.get("text", "")
        hits.append({

            "score": hit.score,
            "dtc_code": hit.entity.get("dtc_code", ""),
            "step_number": hit.entity.get("step_number", ""),
            "text":text,
        })
    return hits
def interpret_score(score):
    if score > 0.85:
        return " Very High Match"
    elif score > 0.75:
        return " Good Match"
    elif score > 0.65:
        return " Partial Match"
    else:
        return " Weak Match"
