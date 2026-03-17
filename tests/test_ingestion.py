import unittest
from unittest.mock import MagicMock, patch, call
import os

# -----------------------------
# PIPELINE (unchanged)
# -----------------------------
class RAGPipeline:
    def __init__(self, parser, embedder, vector_store):
        self.parser = parser
        self.embedder = embedder
        self.vector_store = vector_store

    def ingest(self, file_path):
        chunks = self.parser.parse(file_path)
        for chunk in chunks:
            embedding = self.embedder.embed(chunk["text"])
            self.vector_store.upsert({
                "id": chunk["id"],
                "embedding": embedding,
                "metadata": chunk
            })
        return {"chunks_ingested": len(chunks)}

    def query(self, query_text):
        embedding = self.embedder.embed(query_text)
        return self.vector_store.query(embedding)

    def delete_chunk(self, chunk_id):
        self.vector_store.delete(chunk_id)


# -----------------------------
# TESTS
# -----------------------------
class TestRAGPipeline(unittest.TestCase):

    def setUp(self):
        self.env_patcher = patch.dict(os.environ, {
            "OPENAI_API_KEY": "fake-key",
            "VECTOR_DB_HOST": "localhost",
            "VECTOR_DB_KEY":  "fake-db-key"
        })
        self.env_patcher.start()

        self.mock_parser = MagicMock()
        self.mock_parser.parse.return_value = [
            {"id": "chunk-1", "text": "DPF fault P2463"}
        ]

        self.mock_embedder = MagicMock()
        self.mock_embedder.embed.return_value = [0.1] * 5

        self.mock_vector_store = MagicMock()
        self.mock_vector_store.query.return_value = [
            {"metadata": {"text": "DPF fault P2463"}}
        ]

        self.pipeline = RAGPipeline(
            self.mock_parser,
            self.mock_embedder,
            self.mock_vector_store
        )

    def tearDown(self):
        self.env_patcher.stop()

    # -----------------------------
    # CORE TESTS
    # -----------------------------
    def test_ingestion_calls_parser(self):
        self.pipeline.ingest("test.docx")
        self.mock_parser.parse.assert_called_once_with("test.docx")

    def test_ingestion_embeds_chunk_text(self):
        """Embedder must be called with the actual chunk text, not just called."""
        self.pipeline.ingest("test.docx")
        self.mock_embedder.embed.assert_called_once_with("DPF fault P2463")

    def test_ingestion_upserts_correct_payload(self):
        """Upsert payload must contain id, embedding, and metadata."""
        self.pipeline.ingest("test.docx")
        args, _ = self.mock_vector_store.upsert.call_args
        payload = args[0]
        self.assertEqual(payload["id"], "chunk-1")
        self.assertEqual(payload["embedding"], [0.1] * 5)
        self.assertIn("metadata", payload)

    def test_ingestion_returns_chunk_count(self):
        result = self.pipeline.ingest("test.docx")
        self.assertEqual(result["chunks_ingested"], 1)

    def test_query_embeds_query_text(self):
        self.pipeline.query("DPF issue")
        self.mock_embedder.embed.assert_called_once_with("DPF issue")

    def test_query_passes_embedding_to_store(self):
        """Vector store must receive the embedding, not the raw query string."""
        self.pipeline.query("DPF issue")
        self.mock_vector_store.query.assert_called_once_with([0.1] * 5)

    def test_query_returns_store_results(self):
        """Pipeline must return exactly what the vector store returns."""
        results = self.pipeline.query("DPF issue")
        self.assertEqual(results, [{"metadata": {"text": "DPF fault P2463"}}])

    def test_delete_calls_store_with_id(self):
        self.pipeline.delete_chunk("chunk-1")
        self.mock_vector_store.delete.assert_called_once_with("chunk-1")

    # -----------------------------
    # ENV TESTS
    # -----------------------------
    def test_env_api_key(self):
        self.assertEqual(os.getenv("OPENAI_API_KEY"), "fake-key")

    def test_env_vector_db_host(self):
        self.assertEqual(os.getenv("VECTOR_DB_HOST"), "localhost")

    def test_env_vector_db_key(self):
        self.assertEqual(os.getenv("VECTOR_DB_KEY"), "fake-db-key")

    # -----------------------------
    # EDGE CASES
    # -----------------------------
    def test_empty_file_no_upsert(self):
        self.mock_parser.parse.return_value = []
        result = self.pipeline.ingest("empty.docx")
        self.assertEqual(result["chunks_ingested"], 0)
        self.mock_vector_store.upsert.assert_not_called()

    def test_empty_file_no_embed(self):
        """Embedder must not be called if there are no chunks."""
        self.mock_parser.parse.return_value = []
        self.pipeline.ingest("empty.docx")
        self.mock_embedder.embed.assert_not_called()

    def test_multiple_chunks_all_upserted(self):
        """Every chunk must be embedded and upserted — not just the first."""
        self.mock_parser.parse.return_value = [
            {"id": "chunk-1", "text": "P2463 soot"},
            {"id": "chunk-2", "text": "P245E voltage low"},
            {"id": "chunk-3", "text": "Regen inhibit switch"},
        ]
        result = self.pipeline.ingest("multi.docx")
        self.assertEqual(result["chunks_ingested"], 3)
        self.assertEqual(self.mock_embedder.embed.call_count, 3)
        self.assertEqual(self.mock_vector_store.upsert.call_count, 3)

    def test_query_no_results(self):
        self.mock_vector_store.query.return_value = []
        results = self.pipeline.query("unknown query")
        self.assertEqual(results, [])

    def test_parser_exception_propagates(self):
        """Pipeline must not silently swallow a parser failure."""
        self.mock_parser.parse.side_effect = FileNotFoundError("file not found")
        with self.assertRaises(FileNotFoundError):
            self.pipeline.ingest("missing.docx")

    def test_embedder_exception_propagates(self):
        """Pipeline must not silently swallow an embedder failure."""
        self.mock_embedder.embed.side_effect = RuntimeError("embedding failed")
        with self.assertRaises(RuntimeError):
            self.pipeline.ingest("test.docx")


# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    unittest.main(verbosity=2)