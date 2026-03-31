import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import config

CHROMA_DIR = config.RAG_CHROMA_DIR
COLLECTION_NAME = config.RAG_COLLECTION_NAME
EMBEDDING_MODEL = config.RAG_EMBEDDING_MODEL

_collection = None


def _get_collection():
    global _collection
    if _collection is None:
        ef = SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = client.get_collection(name=COLLECTION_NAME, embedding_function=ef)
    return _collection


def retrieve(query: str, n_results: int = 3) -> list[str]:
    collection = _get_collection()
    results = collection.query(query_texts=[query], n_results=n_results)
    return results["documents"][0]