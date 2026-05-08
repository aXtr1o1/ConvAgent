from ingestion.data.ingestion.chunk_pipeline import run_pipeline
from ingestion.collectors.pdf_parser import merge_results, parse_docs, build_llm_blocks, process_all
from ingestion.data.ingestion.embedding import build_embedding_text, insert_to_milvus
from ingestion.data.ingestion.setup import create_collections, connect_milvus
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
def full_ingestion(filepath):
    try:
        connect_milvus()
        collection = create_collections()
        blocks = parse_docs(filepath)
        llm_blocks = build_llm_blocks(blocks)
        res = process_all(llm_blocks)
        structured_data = merge_results(res)
        chunk_texts = build_embedding_text(structured_data)
        logger.info(f"Built {len(chunk_texts)} embedding texts")
        insert_to_milvus(collection,  chunk_texts)
        logger.info("Inserted chunks into Milvus")

        return {
            "status": "success",
            "chunk_count": len(chunk_texts),
        }
    except Exception as e:
        logger.error(f"Error during full ingestion: {e}")
        return {
            "status": "error",
            "error": str(e),
        }
if __name__ == "__main__":
    filepath = "C:\\Users\\praga\\Downloads\\DCT-P2463-KowledgeBase_Updated.docx"
    result = full_ingestion(filepath)
    print(result)
    