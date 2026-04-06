import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import config


class DocumentRetriever:
    def __init__(
        self,
        chroma_dir: str = config.RAG_CHROMA_DIR,
        collection_name: str = config.RAG_COLLECTION_NAME,
        embedding_model: str = config.RAG_EMBEDDING_MODEL,
    ):
        self._chroma_dir = chroma_dir
        self._collection_name = collection_name
        self._embedding_model = embedding_model
        self._collection = None

    def _get_collection(self):
        if self._collection is None:
            ef = SentenceTransformerEmbeddingFunction(model_name=self._embedding_model)
            client = chromadb.PersistentClient(path=self._chroma_dir)
            try:
                self._collection = client.get_collection(
                    name=self._collection_name,
                    embedding_function=ef,
                )
            except ValueError:
                raise RuntimeError("RAG index not found. Run 'python -m src.rag.build_index' to build it first.")
        return self._collection

    def retrieve(self, query: str, n_results: int = 3) -> list[str]:
        results = self._get_collection().query(query_texts=[query], n_results=n_results)
        return results["documents"][0]
