"""
One-time script to build the RAG index from PostgreSQL docs.
Extracts text from the PDF, chunks with overlap, and stores in ChromaDB.

Run from project root:
    python -m rag.build_index
"""

import pdfplumber
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import config

PDF_PATH = "data/pg_docs_extracted/extracted.pdf"
CHROMA_DIR = config.RAG_CHROMA_DIR
COLLECTION_NAME = config.RAG_COLLECTION_NAME
EMBEDDING_MODEL = config.RAG_EMBEDDING_MODEL
MIN_PAGE_CHARS = 100  # skip pages with too little text (e.g. blank/header-only)
CHUNK_SIZE = 200
CHUNK_OVERLAP = 30
BATCH_SIZE = 50


def chunk_text(text: str) -> list[str]:
    words = text.split()
    if len(words) <= CHUNK_SIZE:
        return [text]
    chunks = []
    i = 0
    while i < len(words):
        chunk = " ".join(words[i:i + CHUNK_SIZE])
        chunks.append(chunk)
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def build_index():
    print(f"Reading: {PDF_PATH}")

    chunks = []
    with pdfplumber.open(PDF_PATH) as pdf:
        for page_i, page in enumerate(pdf.pages):
            text = (page.extract_text() or "").strip()
            if len(text) < MIN_PAGE_CHARS:
                continue
            for chunk_j, chunk in enumerate(chunk_text(text)):
                chunks.append({"id": f"page_{page_i}_chunk_{chunk_j}", "text": chunk})

    print(f"Extracted {len(chunks)} chunks")

    ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(name=COLLECTION_NAME, embedding_function=ef)

    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        collection.add(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
        )
        print(f"  Indexed {min(i + BATCH_SIZE, len(chunks))}/{len(chunks)} chunks")

    print(f"\nIndex saved to {CHROMA_DIR}/")


if __name__ == "__main__":
    build_index()