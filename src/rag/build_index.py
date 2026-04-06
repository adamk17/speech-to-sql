"""
One-time script to build the RAG index from PostgreSQL docs.
Extracts text from the PDF, chunks with overlap, and stores in ChromaDB.

Run from project root:
    python -m src.rag.build_index
"""

import pdfplumber
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import config


class IndexBuilder:
    def __init__(
        self,
        pdf_path: str = "data/pg_docs_extracted/extracted.pdf",
        chroma_dir: str = config.RAG_CHROMA_DIR,
        collection_name: str = config.RAG_COLLECTION_NAME,
        embedding_model: str = config.RAG_EMBEDDING_MODEL,
        min_page_chars: int = 100,
        chunk_size: int = 200,
        chunk_overlap: int = 30,
        batch_size: int = 50,
    ):
        self._pdf_path = pdf_path
        self._chroma_dir = chroma_dir
        self._collection_name = collection_name
        self._embedding_model = embedding_model
        self._min_page_chars = min_page_chars
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        self._batch_size = batch_size

    def _chunk_text(self, text: str) -> list[str]:
        words = text.split()
        if len(words) <= self._chunk_size:
            return [text]
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i:i + self._chunk_size])
            chunks.append(chunk)
            i += self._chunk_size - self._chunk_overlap
        return chunks

    def _extract_chunks(self) -> list[dict]:
        print(f"Reading: {self._pdf_path}")
        chunks = []
        with pdfplumber.open(self._pdf_path) as pdf:
            for page_i, page in enumerate(pdf.pages):
                text = (page.extract_text() or "").strip()
                if len(text) < self._min_page_chars:
                    continue
                for chunk_j, chunk in enumerate(self._chunk_text(text)):
                    chunks.append({"id": f"page_{page_i}_chunk_{chunk_j}", "text": chunk})
        return chunks

    def build(self):
        chunks = self._extract_chunks()
        print(f"Extracted {len(chunks)} chunks")

        ef = SentenceTransformerEmbeddingFunction(model_name=self._embedding_model)
        client = chromadb.PersistentClient(path=self._chroma_dir)

        try:
            client.delete_collection(self._collection_name)
        except ValueError:
            pass

        collection = client.create_collection(name=self._collection_name, embedding_function=ef)

        for i in range(0, len(chunks), self._batch_size):
            batch = chunks[i:i + self._batch_size]
            collection.add(
                ids=[c["id"] for c in batch],
                documents=[c["text"] for c in batch],
            )
            print(f"  Indexed {min(i + self._batch_size, len(chunks))}/{len(chunks)} chunks")

        print(f"\nIndex saved to {self._chroma_dir}/")


if __name__ == "__main__":
    IndexBuilder().build()