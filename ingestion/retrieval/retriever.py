from __future__ import annotations
import os
import logging
import time
from config import azure_emb_key, azure_emb_endpoint, azure_emb_version, azure_emb_deployment, milvus_host, milvus_port
from openai import AzureOpenAI
from dotenv import load_dotenv
from pymilvus import connections, Collection, utility
from backend.utils.utilities import db

load_dotenv()
logger = logging.getLogger(__name__)



_embed_client = AzureOpenAI(
    api_key=azure_emb_key,
    azure_endpoint=azure_emb_endpoint,
    api_version=azure_emb_version,
)
EMBED_MODEL = azure_emb_deployment

MILVUS_HOST = milvus_host
MILVUS_PORT = milvus_port

ALL_COLLECTIONS = [
    "dtc_explanation",
    "diagnostic_procedures",
    "repair_procedures",
    "symptom_knowledge",
]


# ── Milvus connection ─────────────────────────────────────────────────────────

def _connect():
    try:
        connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT)
    except Exception:
        pass  # already connected


# ── Public: semantic search ───────────────────────────────────────────────────

def semantic_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Embed the query and search across all Milvus collections.
    Returns a ranked list of the most relevant chunks.

    Each result:
    {
        "chunk_text":      str,
        "dtc_code":        str,
        "category":        str,
        "system":          str,
        "source_document": str,
        "score":           float,
    }
    """
    _connect()
    query_vector = _embed(query)

    results = []
    for col_name in ALL_COLLECTIONS:
        if not utility.has_collection(col_name):
            continue
        try:
            col = Collection(col_name)
            col.load()
            hits = col.search(
                data=[query_vector],
                anns_field="embedding",
                param={"metric_type": "COSINE", "params": {"nprobe": 16}},
                limit=top_k,
                output_fields=[
                    "chunk_text", "dtc_code", "category",
                    "system", "source_document",
                ],
            )
            for hit in hits[0]:
                results.append({
                    "chunk_text":      hit.entity.get("chunk_text", ""),
                    "dtc_code":        hit.entity.get("dtc_code", ""),
                    "category":        hit.entity.get("category", ""),
                    "system":          hit.entity.get("system", ""),
                    "source_document": hit.entity.get("source_document", ""),
                    "score":           hit.score,
                })
        except Exception as e:
            logger.warning("Search failed on collection %s: %s", col_name, e)

    # Sort across all collections by score descending, take top_k overall
    results.sort(key=lambda x: x["score"], reverse=True)
    # ── Deduplicate by chunk_text ─────────────────────────────────────
    seen_texts: set[str] = set()
    unique_results = []
    for r in results:
        if r["chunk_text"] not in seen_texts:
            seen_texts.add(r["chunk_text"])
            unique_results.append(r)

    return unique_results[:top_k]

def format_context_for_llm(chunks: list[dict]) -> str:
    """
    Format retrieved chunks into a clean context block for the LLM system prompt.
    """
    if not chunks:
        return ""
    lines = ["Relevant diagnostic knowledge:"]
    for i, c in enumerate(chunks, 1):
        lines.append(
            f"\n[{i}] DTC {c['dtc_code']} ({c['category'].replace('_', ' ')}):\n"
            f"{c['chunk_text']}"
        )
    return "\n".join(lines)


# ── Public: structured decision tree ─────────────────────────────────────────

def get_decision_tree(dtc_code: str) -> dict:

    # Normalise code — accept "P2463" or "P2463-00"
    print(f"Retrieving decision tree for DTC code: {dtc_code}")
    normalised = _normalise_dtc(dtc_code)
    print(f"Normalised DTC code for retrieval: {normalised}")
    # dtc_codes row
    dtc_resp = (
        db.table("dtc_codes")
        .select("*")
        .ilike("dtc_code", f"{normalised}%")
        .limit(1)
        .execute()
    )
    if not dtc_resp.data:
        return {}

    row = dtc_resp.data[0]
    code = row["dtc_code"]

    # possible_cause rows
    causes_resp = (
        db.table("possible_cause")
        .select("cause, check_point")
        .eq("dtc_code", code)
        .execute()
    )

    # diagnostic_steps rows ordered by step_order
    steps_resp = (
        db.table("diagnostic_steps")
        .select("step_order, question, yes_action, no_action")
        .eq("dtc_code", code)
        .order("step_order")
        .execute()
    )
    print(f"Retrieved {steps_resp.data} diagnostic steps for DTC {code}")
    print(f"Retrieved {len(steps_resp.data)} diagnostic steps for DTC {code}")
    # # repair_action rows
    # repairs_resp = (
    #     db.table("repair_action")
    #     .select("repair, cause_ref")
    #     .eq("dtc_code", code)
    #     .execute()
    # )

    return {
        "dtc_code":    code,
        "description": row.get("description", ""),
        "system":      row.get("system", ""),
        "reactions":   row.get("reactions", ""),
        "causes":      causes_resp.data or [],
        "steps":       steps_resp.data or [],
        # "repairs":     repairs_resp.data or [],
    }


def get_dtc_metadata(dtc_code: str) -> dict:
    """Lightweight fetch — just the dtc_codes row, no joins."""
    normalised = _normalise_dtc(dtc_code)
    resp = (
        db.table("dtc_codes")
        .select("dtc_code, description, system, reactions")
        .ilike("dtc_code", f"{normalised}%")
        .limit(1)
        .execute()
    )
    return resp.data[0] if resp.data else {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _embed(text: str) -> list[float]:
    resp = _embed_client.embeddings.create(
        model=EMBED_MODEL,
        input=[text.replace("\n", " ").strip()[:8000]],
    )
    return resp.data[0].embedding


def _normalise_dtc(code: str) -> str:
    """Strip suffix so 'P2463' matches 'P2463-00' via ILIKE."""
    return code.strip().upper().split("-")[0]
