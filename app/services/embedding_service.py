import os

CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db")

_model = None
_client = None
_collection = None


def init_embedding_service():
    if os.environ.get("SKIP_EMBEDDINGS") == "true":
        return
    from sentence_transformers import SentenceTransformer
    import chromadb

    global _model, _client, _collection

    _model = SentenceTransformer("all-MiniLM-L6-v2")
    _client = chromadb.PersistentClient(path=CHROMA_PATH)
    _collection = _client.get_or_create_collection(name="messages")


def generate_embedding(text): 
    """Convert text to a vector."""
    if _model is None:
        return [0.0] * 384
    return _model.encode(text).tolist()

def store_embedding(message_id, text, session_id, role):
    """Generate embedding and store in Chromadb with metadata"""
    embedding = generate_embedding(text)
    if _collection is None:
        return
    _collection.add(
        embeddings=[embedding], 
        ids = [str(message_id)],
        metadatas = [{"session_id": session_id, "role": role}]
    )

def semantic_search(query, limit = 10):
    """Search ChromaDB for messages similar to the query."""
    query_embedding = generate_embedding(query)
    assert _collection is not None, "init_embedding_service() mmust be called first."
    
    results = _collection.query(
        query_embeddings=[query_embedding], 
        n_results=limit
    )
    return results

