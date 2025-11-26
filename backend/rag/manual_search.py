import os
import chromadb
from chromadb.utils import embedding_functions

DB_DIR = os.path.join("backend", "vector_db")

client = chromadb.PersistentClient(path=DB_DIR)

embedding_function = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small",
)

def get_collection(collection_name: str):
    try:
        return client.get_collection(
            name=collection_name,
            embedding_function=embedding_function,
        )
    except Exception:
        return None

def search_manual(brand: str, vehicle_key: str, question: str, top_k: int = 5):
    """
    Searches inside a specific manual for relevant chunks.
    """
    collection_name = f"{brand}_manuals"
    col = get_collection(collection_name)

    if col is None:
        return []

    result = col.query(
        query_texts=[question],
        n_results=top_k,
        where={"source": vehicle_key},
    )

    docs = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]

    combined = []
    for doc, meta in zip(docs, metadatas):
        combined.append(
            {
                "text": doc,
                "source": meta.get("source", ""),
            }
        )

    return combined
