import os
import glob
import numpy as np
from google import genai
from google.genai import types

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_DIR = os.path.join(BASE_DIR, "knowledge_base")
INDEX_PATH = os.path.join(BASE_DIR, "data", "rag_index.npz")


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    """Splits text into overlapping chunks of defined character length."""
    chunks = []
    start = 0
    text_len = len(text)
    
    if text_len <= chunk_size:
        return [text]
        
    while start < text_len:
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
        
    return chunks


def build_index() -> str:
    """Reads documents from knowledge_base, generates embeddings, and saves the index."""
    if not os.path.exists(KB_DIR):
        return "Knowledge base directory not found."

    # Scan for text and markdown files
    files = glob.glob(os.path.join(KB_DIR, "*.txt")) + glob.glob(os.path.join(KB_DIR, "*.md"))
    if not files:
        return "No documents found in knowledge base."

    chunks_list = []
    sources_list = []
    
    for file_path in files:
        source_name = os.path.basename(file_path)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            file_chunks = chunk_text(content)
            for chunk in file_chunks:
                if chunk.strip():
                    chunks_list.append(chunk.strip())
                    sources_list.append(source_name)
        except Exception as e:
            print(f"Error reading {source_name}: {e}")

    if not chunks_list:
        return "No text extracted from documents."

    # Fetch API Key and init Gemini Client
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return "GOOGLE_API_KEY is not configured in .env."

    try:
        client = genai.Client()
        embeddings_list = []

        # Batch embed chunks
        for chunk in chunks_list:
            res = client.models.embed_content(
                model="gemini-embedding-001",
                contents=chunk
            )
            vector = res.embeddings[0].values
            embeddings_list.append(vector)

        # Convert to numpy array and save
        embeddings_arr = np.array(embeddings_list, dtype=np.float32)
        
        # Ensure data dir exists
        os.makedirs(os.path.dirname(INDEX_PATH), exist_ok=True)
        np.savez_compressed(
            INDEX_PATH,
            embeddings=embeddings_arr,
            chunks=np.array(chunks_list),
            sources=np.array(sources_list)
        )
        return "success"
    except Exception as e:
        return f"Failed to generate embeddings: {e}"


def retrieve_knowledge(query: str, top_k: int = 3) -> str:
    """Queries the local NumPy index and returns top matched context chunks.

    Args:
        query: The user query string to search for in the guidelines.
        top_k: Number of relevant context chunks to retrieve. Defaults to 3.

    Returns:
        A formatted string of context chunks matching the query.
    """
    if not os.path.exists(INDEX_PATH):
        # Auto-build index if missing
        status = build_index()
        if status != "success":
            return f"No knowledge index found. (Auto-build status: {status})"

    try:
        # Load index
        data = np.load(INDEX_PATH, allow_pickle=True)
        embeddings = data["embeddings"]
        chunks = data["chunks"]
        sources = data["sources"]

        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            return "GOOGLE_API_KEY not configured. Cannot perform vector retrieval."

        # Embed user query
        client = genai.Client()
        res = client.models.embed_content(
            model="gemini-embedding-001",
            contents=query
        )
        query_vector = np.array(res.embeddings[0].values, dtype=np.float32)

        # Calculate Cosine Similarity
        dot_products = np.dot(embeddings, query_vector)
        embeddings_norms = np.linalg.norm(embeddings, axis=1)
        query_norm = np.linalg.norm(query_vector)
        
        # Guard against zero-division
        norms = embeddings_norms * query_norm
        norms[norms == 0] = 1e-10
        similarities = dot_products / norms

        # Get top-k matches
        top_indices = np.argsort(similarities)[::-1][:top_k]

        contexts = []
        for idx in top_indices:
            score = similarities[idx]
            # Lower threshold to 0.15 for soft matches, displaying similarity metrics
            if score > 0.15:
                contexts.append(f"[{sources[idx]} (Relevance: {score:.2f})]:\n{chunks[idx]}")

        if not contexts:
            return "No matching guidelines found in local files."

        return "\n\n---\n\n".join(contexts)
    except Exception as e:
        return f"Error retrieving context: {e}"
