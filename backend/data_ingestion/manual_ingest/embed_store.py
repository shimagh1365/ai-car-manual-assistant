import chromadb
from chromadb.utils import embedding_functions
import os

# Where to store the Chroma database on disk
DB_DIR = os.path.join("backend", "vector_db")
os.makedirs(DB_DIR, exist_ok=True)

# Use a persistent client so data is saved between runs
client = chromadb.PersistentClient(path=DB_DIR)

# OpenAI embedding function
embedding_function = embedding_functions.OpenAIEmbeddingFunction(
    api_key=os.getenv("OPENAI_API_KEY"),
    model_name="text-embedding-3-small",
)

def get_or_create_collection(name: str):
    """
    Get or create a collection for a brand's manuals.
    """
    return client.get_or_create_collection(
        name=name,
        embedding_function=embedding_function,
    )

def add_chunks_to_db(collection_name: str, vehicle_key: str, chunks: list[str]):
    """
    Store chunks for a specific vehicle model into ChromaDB.
    - collection_name: e.g. 'porsche_manuals'
    - vehicle_key: e.g. 'Porsche_911_QSG_MY2023'
    """
    col = get_or_create_collection(collection_name)

    ids = [f"{vehicle_key}_{i}" for i in range(len(chunks))]
    metadatas = [{"source": vehicle_key} for _ in chunks]

    col.add(
        ids=ids,
        metadatas=metadatas,
        documents=chunks,
    )
