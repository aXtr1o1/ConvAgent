from config import embed_client as client
from config import azure_emb_deployment
import logging
from tqdm import tqdm
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
import numpy as np

def validate_embeddings(embeddings):
    for i, vec in enumerate(embeddings):
        if not isinstance(vec, list):
            raise ValueError(f"Embedding {i} is not a list")

        for j, val in enumerate(vec):
            if not isinstance(val, (float, int)):
                raise ValueError(f"Invalid value at vec[{i}][{j}] = {val}")
def get_embs(texts):
    response= client.embeddings.create(
        model=azure_emb_deployment,
        input=texts
    )
    vectors =[]
    for d in response.data:

        vec = d.embedding
        if vec is None:
            raise ValueError(f"Embedding for text {d.index} is None")
        norm = np.linalg.norm(vec)
        if norm == 0:
            raise ValueError(f"Embedding for text {d.index} is zero vector")
        vec = (np.array(vec) / norm).astype(float).tolist()
        vectors.append(vec)
    validate_embeddings(vectors)

    return vectors


def build_embedding_text(structured_data):
    embedding_texts =[]

    for dtc in structured_data.get("dtcs", []):
        if not isinstance(dtc, dict):
            logger.warning(f"Skipping non-dict DTC: {dtc}")
            continue

        dtc_code = dtc.get("code","")

        for step in dtc.get("steps", []):
            text  = f"""
            Main DTC: {dtc_code}

            Step {step.get("step_number", "")}: {step.get("title", "")}

            Instructions:
            {step.get("instructions", "")}

            Expected Result:
            {step.get("expected_result", "")}

            Next Action:
            {step.get("next_action", "")}
            """ 
            embedding_texts.append({
                "dtc_code":dtc_code,
                "step_number":step.get("step_number", ""),
                "text":text.strip(),
            })
    return embedding_texts

def insert_to_milvus(collection, chunks, batch_size=32):
    all_texts = [c["text"] for c in chunks]

    for i in tqdm(range(0, len(chunks), batch_size)):
        batch_chunks = chunks[i:i+batch_size]

        batch_text = all_texts[i:i+batch_size]

        embs = get_embs(batch_text)

        dtc_codes = [c["dtc_code"] for c in batch_chunks]
        step_numbers = [c["step_number"] for c in batch_chunks]
        texts = [c["text"] for c in batch_chunks]

        collection.insert([
            dtc_codes,
            step_numbers,
            texts,
            embs
        ])
    collection.flush()
    logger.info(f"Inserted {len(chunks)} chunks into Milvus")
