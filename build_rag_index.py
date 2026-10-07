from app.rag.retriever import KnowledgeRetriever

DOCUMENT_PATH = "data/health_guidelines.txt"
INDEX_PATH = "rag_index/knowledge.faiss"
METADATA_PATH = "rag_index/metadata.json"


def main():
    print("Loading knowledge document...")

    retriever = KnowledgeRetriever()

    number_of_chunks = retriever.build_index(
        DOCUMENT_PATH
    )

    print(f"Created {number_of_chunks} knowledge chunks.")

    retriever.save_index(
        INDEX_PATH,
        METADATA_PATH
    )

    print("FAISS index saved.")
    print(f"Index: {INDEX_PATH}")
    print(f"Metadata: {METADATA_PATH}")


if __name__ == "__main__":
    main()