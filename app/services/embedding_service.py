# import the dependencies 

from sentence_transformers import SentenceTransformer
import chromadb
import os 


# path hwere chromaDB stores its data 
CHROMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "chroma_db")


# load the model once, module level, so it's loaded when the service is first imported 
_model = None 

# ChromaDB client + collection 
_client = None
_collection = None

def init_embedding_service():
    """Call once at startup. Loads model and connects to ChromaDB"""

    global _model, _client, _collection

    _model = SentenceTransformer("all-MiniLM-L6-v2")
    _client = chromadb.PersistentClient(path = CHROMA_PATH)
    _collection = _client.get_or_create_collection(name = "messages")


def generate_embedding(text): 
    """Convert text to a vector."""
    assert _model is not None, "init_embedding_service() must be called first"
    return _model.encode(text).tolist()

def store_embedding(message_id, text, session_id, role):
    """Generate embedding and store in Chromadb with metadata"""
    embedding = generate_embedding(text)
    assert _collection is not None, "init_embedding_service() must be called"
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

