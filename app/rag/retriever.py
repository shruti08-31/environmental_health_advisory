# ============================================================
# PART 7 - FAISS RAG RETRIEVER
# ============================================================

from pathlib import Path
import json

import faiss
import numpy as np

from sentence_transformers import SentenceTransformer

from app.rag.knowledge_base import (
    load_knowledge_document,
    split_into_chunks
)


# ------------------------------------------------------------
# DEFAULT MODEL
# ------------------------------------------------------------

DEFAULT_EMBEDDING_MODEL = (
    "sentence-transformers/all-MiniLM-L6-v2"
)


class KnowledgeRetriever:
    """
    FAISS-based environmental-health knowledge retriever.

    This class performs retrieval only.

    It does NOT:
    - generate answers
    - call an LLM
    - call WAQI
    - calculate AQI
    - determine severity
    """

    def __init__(
        self,
        embedding_model=DEFAULT_EMBEDDING_MODEL
    ):
        self.embedding_model_name = (
            embedding_model
        )

        try:
            self.model = SentenceTransformer(
                embedding_model
            )
        except Exception as error:
            raise RuntimeError(
                "Could not load the embedding model."
            ) from error

        self.index = None
        self.chunks = []

    # --------------------------------------------------------
    # CREATE INDEX
    # --------------------------------------------------------

    def build_index(
        self,
        document_path
    ):
        """
        Load document, create chunks, generate embeddings,
        and create the FAISS index.
        """

        text = load_knowledge_document(
            document_path
        )

        chunks = split_into_chunks(
            text
        )

        if not chunks:
            raise ValueError(
                "No chunks were created from the document."
            )

        texts = [
            chunk["text"]
            for chunk in chunks
        ]

        try:
            embeddings = self.model.encode(
                texts,
                convert_to_numpy=True,
                show_progress_bar=False
            )
        except Exception as error:
            raise RuntimeError(
                "Failed to create document embeddings."
            ) from error

        embeddings = np.asarray(
            embeddings,
            dtype="float32"
        )

        if embeddings.ndim != 2:
            raise ValueError(
                "Embedding output has an invalid shape."
            )

        # Normalize vectors so inner product becomes
        # cosine similarity.
        faiss.normalize_L2(
            embeddings
        )

        dimension = embeddings.shape[1]

        self.index = faiss.IndexFlatIP(
            dimension
        )

        self.index.add(
            embeddings
        )

        self.chunks = chunks

        return len(chunks)

    # --------------------------------------------------------
    # SAVE INDEX
    # --------------------------------------------------------

    def save_index(
        self,
        index_path,
        metadata_path
    ):
        """
        Save the FAISS index and chunk metadata.
        """

        if self.index is None:
            raise ValueError(
                "No FAISS index exists. "
                "Build the index first."
            )

        if not self.chunks:
            raise ValueError(
                "No chunk metadata exists."
            )

        index_path = Path(
            index_path
        )

        metadata_path = Path(
            metadata_path
        )

        index_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        metadata_path.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        try:

            faiss.write_index(
                self.index,
                str(index_path)
            )

            metadata = {
                "embedding_model": (
                    self.embedding_model_name
                ),
                "chunks": self.chunks
            }

            metadata_path.write_text(
                json.dumps(
                    metadata,
                    ensure_ascii=False,
                    indent=2
                ),
                encoding="utf-8"
            )

        except Exception as error:

            raise RuntimeError(
                "Failed to save FAISS index."
            ) from error

    # --------------------------------------------------------
    # LOAD INDEX
    # --------------------------------------------------------

    def load_index(
        self,
        index_path,
        metadata_path
    ):
        """
        Load an existing FAISS index and metadata.
        """

        index_path = Path(
            index_path
        )

        metadata_path = Path(
            metadata_path
        )

        if not index_path.exists():
            raise FileNotFoundError(
                f"FAISS index not found: {index_path}"
            )

        if not metadata_path.exists():
            raise FileNotFoundError(
                f"Metadata file not found: {metadata_path}"
            )

        try:

            self.index = faiss.read_index(
                str(index_path)
            )

            metadata = json.loads(
                metadata_path.read_text(
                    encoding="utf-8"
                )
            )

            self.chunks = metadata.get(
                "chunks",
                []
            )

            stored_model = metadata.get(
                "embedding_model"
            )

            if stored_model:
                self.embedding_model_name = (
                    stored_model
                )

        except Exception as error:

            self.index = None
            self.chunks = []

            raise RuntimeError(
                "Failed to load FAISS index or metadata."
            ) from error

        if not self.chunks:
            raise ValueError(
                "Loaded metadata contains no chunks."
            )

    # --------------------------------------------------------
    # RETRIEVE
    # --------------------------------------------------------

    def retrieve(
        self,
        query,
        top_k=5
    ):
        """
        Retrieve the most relevant knowledge chunks.

        Returns:
        {
            "query": "...",
            "results": [
                {
                    "text": "...",
                    "score": ...
                }
            ]
        }
        """

        if not isinstance(query, str):
            raise TypeError(
                "Query must be a string."
            )

        query = query.strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        if self.index is None:
            raise ValueError(
                "FAISS index is not loaded."
            )

        if not self.chunks:
            raise ValueError(
                "No knowledge chunks are available."
            )

        if not isinstance(top_k, int):
            raise TypeError(
                "top_k must be an integer."
            )

        if top_k <= 0:
            raise ValueError(
                "top_k must be greater than zero."
            )

        top_k = min(
            top_k,
            len(self.chunks)
        )

        try:

            query_embedding = self.model.encode(
                [query],
                convert_to_numpy=True,
                show_progress_bar=False
            )

        except Exception as error:

            raise RuntimeError(
                "Failed to create query embedding."
            ) from error

        query_embedding = np.asarray(
            query_embedding,
            dtype="float32"
        )

        faiss.normalize_L2(
            query_embedding
        )

        scores, indices = self.index.search(
            query_embedding,
            top_k
        )

        results = []

        for score, index in zip(
            scores[0],
            indices[0]
        ):

            if index < 0:
                continue

            chunk = self.chunks[index]

            results.append({
                "text": chunk["text"],
                "score": round(
                    float(score),
                    4
                )
            })

        return {
            "query": query,
            "results": results
        }