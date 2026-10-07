from app.rag.retriever import KnowledgeRetriever


INDEX_PATH = "rag_index/knowledge.faiss"
METADATA_PATH = "rag_index/metadata.json"


def main():

    print("=" * 60)
    print("PART 7 - FAISS RAG TEST")
    print("=" * 60)

    retriever = KnowledgeRetriever()

    print()
    print("Loading FAISS index...")

    retriever.load_index(
        INDEX_PATH,
        METADATA_PATH
    )

    print(
        f"Loaded {len(retriever.chunks)} knowledge chunks."
    )

    query = "What are the health effects of PM2.5?"

    print()
    print("Query:")
    print(query)

    result = retriever.retrieve(
        query,
        top_k=3
    )

    print()
    print("Retrieved results:")
    print()

    for number, item in enumerate(
        result["results"],
        start=1
    ):

        print(f"--- Result {number} ---")

        print(f"Score: {item['score']}")

        print(
            f"Section: {item.get('section', 'Unknown')}"
        )

        print()

        print(item["text"])

        print()


if __name__ == "__main__":
    main()