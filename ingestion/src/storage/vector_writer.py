from __future__ import annotations
import os
import uuid
import logging
import time

from openai import AzureOpenAI
from dotenv import load_dotenv
from pymilvus import (
    connections, Collection, CollectionSchema,
    FieldSchema, DataType, utility,
)

load_dotenv()
logger = logging.getLogger(__name__)

# ── Azure OpenAI embedding client ─────────────────────────────────────────────
_embed_client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_VERSION"),
)
EMBED_MODEL = os.getenv("AZURE_EMBEDDING_DEPLOYMENT", "text-embedding-ada-002")
EMBED_DIM   = 1536

# ── Milvus settings ───────────────────────────────────────────────────────────
MILVUS_HOST  = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT  = int(os.getenv("MILVUS_PORT", "19530"))
MILVUS_TOKEN = os.getenv("MILVUS_TOKEN", "")

# ── Collection routing ────────────────────────────────────────────────────────
CATEGORY_TO_COLLECTION = {
    "dtc_explanation": "dtc_explanation",
    "possible_cause":  "diagnostic_procedures",
    "diagnostic_step": "diagnostic_procedures",
    "repair_action":   "repair_procedures",
}
SYMPTOM_COLLECTION = "symptom_knowledge"

ALL_COLLECTIONS = [
    "dtc_explanation",
    "diagnostic_procedures",
    "repair_procedures",
    "symptom_knowledge",
]


# ── Connection & setup ────────────────────────────────────────────────────────

def connect_milvus() -> None:
    connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
    logger.info("Connected to Milvus at %s:%s", MILVUS_HOST, MILVUS_PORT)


def ensure_collections() -> None:
    """Create all 4 collections if they do not already exist."""
    for name in ALL_COLLECTIONS:
        if not utility.has_collection(name):
            _create_collection(name)
            logger.info("Created Milvus collection: %s", name)
        else:
            logger.debug("Milvus collection already exists: %s", name)
        Collection(name).load()


def _create_collection(name: str) -> Collection:
    fields = [
        FieldSchema("id",              DataType.VARCHAR, is_primary=True, max_length=64),
        FieldSchema("dtc_code",        DataType.VARCHAR, max_length=32),
        FieldSchema("system",          DataType.VARCHAR, max_length=64),
        FieldSchema("component",       DataType.VARCHAR, max_length=128),
        FieldSchema("source_document", DataType.VARCHAR, max_length=256),
        FieldSchema("category",        DataType.VARCHAR, max_length=64),
        FieldSchema("chunk_text",      DataType.VARCHAR, max_length=4096),
        FieldSchema("embedding",       DataType.FLOAT_VECTOR, dim=EMBED_DIM),
    ]
    schema = CollectionSchema(fields, description=f"DTC knowledge — {name}")
    col = Collection(name, schema=schema)
    col.create_index("embedding", {
        "index_type": "IVF_FLAT",
        "metric_type": "COSINE",
        "params": {"nlist": 128},
    })
    return col


# ── Main write function ───────────────────────────────────────────────────────

def write_to_vector_db(chunks: list[dict], batch_size: int = 16) -> dict:
    """
    Embed all chunks and insert them into the appropriate Milvus collections.
    Returns a summary of records written per collection.
    """
    connect_milvus()
    ensure_collections()

    # Delete existing vectors for this DTC so re-ingest is idempotent
    if chunks:
        dtc_code = chunks[0]["dtc_code"]
        _delete_existing(dtc_code)

    # Group chunks by target collection
    collection_batches: dict[str, list[dict]] = {c: [] for c in ALL_COLLECTIONS}

    for chunk in chunks:
        cat = chunk["category"]
        target = CATEGORY_TO_COLLECTION.get(cat, "dtc_explanation")
        collection_batches[target].append(chunk)

        # DTC explanation chunks also go into symptom_knowledge
        if cat == "dtc_explanation":
            collection_batches[SYMPTOM_COLLECTION].append(chunk)

    # Embed and insert per collection
    summary: dict[str, int] = {}
    for col_name, col_chunks in collection_batches.items():
        if not col_chunks:
            summary[col_name] = 0
            continue

        texts = [c["chunk_text"] for c in col_chunks]
        embeddings = _embed_batch(texts, batch_size)

        _insert_records(col_name, col_chunks, embeddings)
        summary[col_name] = len(col_chunks)
        logger.info("Inserted %d records into %s", len(col_chunks), col_name)

    return summary


# ── Embedding ─────────────────────────────────────────────────────────────────

def _embed_batch(texts: list[str], batch_size: int = 16) -> list[list[float]]:
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = [t.replace("\n", " ").strip()[:8000] for t in texts[i:i + batch_size]]
        resp = _embed_client.embeddings.create(model=EMBED_MODEL, input=batch)
        sorted_data = sorted(resp.data, key=lambda x: x.index)
        all_embeddings.extend(item.embedding for item in sorted_data)
        if i + batch_size < len(texts):
            time.sleep(0.3)
    return all_embeddings


# ── Milvus CRUD ───────────────────────────────────────────────────────────────

def _delete_existing(dtc_code: str) -> None:
    """Remove all existing vectors for a DTC code across all collections."""
    for col_name in ALL_COLLECTIONS:
        if not utility.has_collection(col_name):
            continue
        col = Collection(col_name)
        col.load()
        try:
            col.delete(f'dtc_code == "{dtc_code}"')
        except Exception as e:
            logger.warning("Could not delete from %s: %s", col_name, e)


def _insert_records(
    col_name: str,
    chunks: list[dict],
    embeddings: list[list[float]],
) -> None:
    col = Collection(col_name)
    data = [
        [str(uuid.uuid4())        for _ in chunks],   # id
        [c["dtc_code"]            for c in chunks],   # dtc_code
        [c["system"]              for c in chunks],   # system
        [c["component"]           for c in chunks],   # component
        [c["source_document"]     for c in chunks],   # source_document
        [c["category"]            for c in chunks],   # category
        [c["chunk_text"][:4096]   for c in chunks],   # chunk_text
        embeddings,                                    # embedding
    ]
    col.insert(data)
    col.flush()
