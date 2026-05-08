import json
import logging
logger = logging.getLogger(__name__)
from ingestion.collectors.pdf_parser import parse_docs, process_all, merge_results, build_llm_blocks, validate_steps
from ingestion.data.ingestion.embedding import build_embedding_text
logging.basicConfig(level = logging.INFO)


def run_pipeline(filepath):


    logger.info("Pipeline Starting")

    blocks = parse_docs(filepath)

    llm_blocks = build_llm_blocks(blocks)
    logger.info(f"Parsed {len(llm_blocks)} blocks from {filepath}")

    res = process_all(llm_blocks)

    logger.info(f"Processed {len(res)} LLM Responses")
    logger.info(f"First response: {res[0]}")
    structured_data = merge_results(res)
    validate_steps(structured_data)
    logger.info(f"First structured DTC: {structured_data}")
    logger.info(f"Merged {len(structured_data['dtcs'])} structured DTCs")

    embedding_texts = build_embedding_text(structured_data)
    logger.info(f"Built {len(embedding_texts)} embedding texts")

    return embedding_texts

if __name__ == "__main__":
    file_path = "C:\\Users\\praga\\Downloads\\DCT-P2463-KowledgeBase_Updated.docx"
    emb_texts = run_pipeline(file_path)


    for i, text in enumerate(emb_texts[-3:]):
        print(f"\n Chunck {i+1}")
        print(text)
