"""Embedding provider adapter using a real multilingual SentenceTransformer model."""
from typing import Protocol
from sentence_transformers import SentenceTransformer


class Embedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Return one vector per input text, in the same order."""
        ...

    def embed_query(self, question: str) -> list[float]:
        """Return a query vector compatible with the stored document vectors."""
        ...


class SentenceTransformerEmbedder:
    """Real local embedding adapter using sentence-transformers."""

    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2") -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        # Dimensions for paraphrase-multilingual-MiniLM-L12-v2 is 384
        test_vec = self.model.encode("test", normalize_embeddings=True)
        self.dimensions = len(test_vec)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(
            texts,
            batch_size=32,
            show_progress_bar=False,
            normalize_embeddings=True
        )
        return embeddings.tolist()

    def embed_query(self, question: str) -> list[float]:
        embedding = self.model.encode(
            question,
            show_progress_bar=False,
            normalize_embeddings=True
        )
        return embedding.tolist()


# Alias for starter compatibility
MyEmbedder = SentenceTransformerEmbedder
