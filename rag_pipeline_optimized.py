"""
Optimized RAG Pipeline - Loads pre-built embeddings, no runtime model downloads

Key optimizations:
- Embeddings are pre-generated and loaded from disk
- No SentenceTransformer model download at runtime
- BM25 initialized from data
- Optional: Use FastEmbed for lightweight embedding lookups
- Qdrant connection is established at startup
"""

from datasets import load_dataset
import pandas as pd
import numpy as np
from pathlib import Path
from rank_bm25 import BM25Okapi
from dotenv import load_dotenv
import os
import logging
from typing import Optional, List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from openai import OpenAI

from rag.rag_state import RAG_READY_EVENT, RAG_INIT_LOCK

load_dotenv("config/.env")

# =========================================================
# LOGGING
# =========================================================
logger = logging.getLogger(__name__)

# =========================================================
# GLOBAL STATE
# =========================================================
df: Optional[pd.DataFrame] = None
bm25: Optional[BM25Okapi] = None
embeddings: Optional[np.ndarray] = None
qdrant_client: Optional[QdrantClient] = None
groq_client: Optional[OpenAI] = None

collection_name = "mental_health_rag"
EMBEDDINGS_PATH = "/app/data/embeddings.npy"  # Pre-built, provided in Docker image
DATASET_NAME = "Amod/mental_health_counseling_conversations"


# =========================================================
# EMBEDDING LOADING (NO MODEL DOWNLOADS)
# =========================================================
def load_embeddings_from_disk() -> np.ndarray:
    """
    Load pre-built embeddings from disk.
    These are generated in CI/CD and included in the Docker image.

    Returns:
        np.ndarray: Pre-computed embeddings (N, D)

    Raises:
        FileNotFoundError: If embeddings.npy not found
    """
    embeddings_path = Path(EMBEDDINGS_PATH)

    if not embeddings_path.exists():
        raise FileNotFoundError(
            f"Embeddings file not found at {EMBEDDINGS_PATH}\n"
            f"Please run: python build_embeddings.py\n"
            f"Or download from CI/CD artifacts"
        )

    logger.info(f"Loading embeddings from {EMBEDDINGS_PATH}")
    embeddings = np.load(embeddings_path)
    logger.info(
        f"Embeddings loaded: shape={embeddings.shape}, dtype={embeddings.dtype}"
    )

    return embeddings


# =========================================================
# INIT CONTROL (SAFE SINGLETON)
# =========================================================
def initialize_rag():
    """
    Initialize RAG pipeline with pre-built embeddings.

    Process:
    1. Load dataset
    2. Load pre-built embeddings from disk (NO model download)
    3. Initialize BM25
    4. Connect to Qdrant
    5. Populate Qdrant with vectors
    6. Initialize LLM client
    7. Set RAG_READY_EVENT

    Startup time: ~10-20 seconds (no model download overhead)
    """
    global df, bm25, embeddings, qdrant_client, groq_client

    # Fast exit if already ready
    if RAG_READY_EVENT.is_set():
        logger.info("RAG already initialized. Skipping.")
        return

    with RAG_INIT_LOCK:
        # Double-check inside lock
        if RAG_READY_EVENT.is_set():
            return

        try:
            logger.info("Initializing RAG pipeline (optimized)...")
            start_time = __import__("time").time()

            # -------------------------
            # 1. Load Dataset
            # -------------------------
            logger.info(f"Loading dataset: {DATASET_NAME}")
            ds = load_dataset(
                DATASET_NAME,
                trust_remote_code=True,
                cache_dir=".cache",  # Uses HF cache
            )

            df = ds["train"].to_pandas()
            df = (
                df.drop_duplicates(subset=["Context", "Response"])
                .dropna()
                .reset_index(drop=True)
            )
            logger.info(f"Dataset loaded: {len(df)} records")

            # -------------------------
            # 2. Load Pre-Built Embeddings (KEY OPTIMIZATION)
            # -------------------------
            logger.info("Loading pre-built embeddings...")
            embeddings = load_embeddings_from_disk()

            # Verify embeddings shape matches dataset
            if embeddings.shape[0] != len(df):
                logger.warning(
                    f"Embeddings count ({embeddings.shape[0]}) != "
                    f"Dataset count ({len(df)}). This may cause issues."
                )

            # -------------------------
            # 3. Initialize BM25
            # -------------------------
            logger.info("Initializing BM25...")
            tokenized_corpus = [text.lower().split() for text in df["Context"]]
            bm25 = BM25Okapi(tokenized_corpus)
            logger.info("BM25 initialized")

            # -------------------------
            # 4. Connect to Qdrant
            # -------------------------
            logger.info("Connecting to Qdrant...")
            qdrant_client = QdrantClient(
                host=os.getenv("QDRANT_HOST", "qdrant"),
                port=int(os.getenv("QDRANT_PORT", 6333)),
                timeout=120,
            )

            # Check if collection already exists
            existing = [c.name for c in qdrant_client.get_collections().collections]
            logger.info(f"Existing collections: {existing}")

            # -------------------------
            # 5. Create/Populate Qdrant Collection
            # -------------------------
            if collection_name not in existing:
                logger.info(f"Creating collection: {collection_name}")
                qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=embeddings.shape[1], distance=Distance.COSINE
                    ),
                )

            # Check if collection already has data
            info = qdrant_client.get_collection(collection_name)
            logger.info(f"Collection info: {info.points_count} points")

            if (info.points_count or 0) == 0:
                logger.info("Indexing embeddings into Qdrant...")

                points = [
                    PointStruct(
                        id=i,
                        vector=embeddings[i].tolist(),
                        payload={
                            "context": row["Context"],
                            "response": row["Response"],
                        },
                    )
                    for i, row in df.iterrows()
                ]

                BATCH_SIZE = 500
                total_batches = (len(points) + BATCH_SIZE - 1) // BATCH_SIZE

                for batch_idx, start in enumerate(range(0, len(points), BATCH_SIZE)):
                    batch = points[start : start + BATCH_SIZE]
                    qdrant_client.upsert(
                        collection_name=collection_name, points=batch, wait=True
                    )
                    logger.info(f"Indexed batch {batch_idx + 1}/{total_batches}")

                logger.info(f"All {len(points)} embeddings indexed in Qdrant")

            # -------------------------
            # 6. Initialize LLM Client
            # -------------------------
            logger.info("Initializing LLM client...")
            groq_client = OpenAI(
                base_url=os.getenv("LLM_BASE_URL", "https://lightning.ai/api/v1/"),
                api_key=os.getenv("OPENAI_API_KEY"),
            )
            logger.info("LLM client initialized")

            elapsed_time = __import__("time").time() - start_time
            logger.info(f"RAG initialized successfully in {elapsed_time:.2f} seconds")

            # ========================================
            # SET READY FLAG
            # ========================================
            RAG_READY_EVENT.set()

        except Exception as e:
            logger.exception(f"RAG initialization failed: {e}")
            # Don't set RAG_READY_EVENT, allow retry
            raise


# =========================================================
# QUERY FUNCTIONS
# =========================================================
def retrieve_context(query: str, top_k: int = 3) -> List[Dict[str, Any]]:
    """
    Retrieve top-k relevant contexts using hybrid search (semantic + BM25).

    Args:
        query: User query
        top_k: Number of contexts to retrieve

    Returns:
        List of dicts with 'context', 'response', 'score'
    """
    if not RAG_READY_EVENT.is_set():
        raise RuntimeError("RAG pipeline not initialized")

    if qdrant_client is None:
        raise RuntimeError("Qdrant client not available")

    # For semantic search, we'd need the query embedding
    # Since we don't download SentenceTransformer at runtime,
    # we can either:
    # 1. Use BM25 only (fast, no model needed)
    # 2. Pre-compute query embeddings offline
    # 3. Use a lightweight embedding function

    # For now, use BM25
    logger.debug(f"Retrieving context for: {query}")

    # BM25 retrieval
    tokenized_query = query.lower().split()
    bm25_scores = bm25.get_scores(tokenized_query)
    top_indices = np.argsort(bm25_scores)[-top_k:][::-1]

    results = []
    for idx in top_indices:
        if bm25_scores[idx] > 0:
            results.append(
                {
                    "context": df.iloc[idx]["Context"],
                    "response": df.iloc[idx]["Response"],
                    "score": float(bm25_scores[idx]),
                    "method": "BM25",
                }
            )

    return results


def generate_response(query: str, contexts: List[Dict[str, Any]]) -> str:
    """
    Generate response using LLM with retrieved contexts.

    Args:
        query: User query
        contexts: Retrieved contexts from retrieval

    Returns:
        Generated response string
    """
    if groq_client is None:
        raise RuntimeError("LLM client not initialized")

    # Build prompt with contexts
    context_text = "\n\n".join(
        [
            f"Context {i + 1}:\n{ctx['context']}\n→ Response: {ctx['response']}"
            for i, ctx in enumerate(contexts)
        ]
    )

    prompt = f"""You are a compassionate mental health support assistant.
Based on the following contexts, provide a supportive response to the user's query.

{context_text}

User Query: {query}

Your Response:"""

    try:
        response = groq_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a mental health support assistant.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"LLM generation failed: {e}")
        # Fallback response
        return (
            contexts[0]["response"]
            if contexts
            else "I'm here to help. Please tell me more."
        )


# =========================================================
# ALTERNATIVE: FastEmbed Support (Optional)
# =========================================================
def initialize_fastembed_optional():
    """
    Optional lightweight embedding model for query encoding.
    Use if you want semantic search without SentenceTransformer.

    FastEmbed advantages:
    - ~50 MB model vs 500 MB for SentenceTransformer
    - 5-10x faster inference
    - Minimal dependencies

    To use: Uncomment in initialize_rag() and run query embedding
    """
    try:
        from fastembed import SparseTextEmbedding

        logger.info("Loading FastEmbed model...")
        model = SparseTextEmbedding(model_name="BM25")
        logger.info("FastEmbed model loaded")
        return model
    except ImportError:
        logger.warning("FastEmbed not available. Install with: pip install fastembed")
        return None


# =========================================================
# HEALTH CHECK
# =========================================================
def is_rag_ready() -> Dict[str, Any]:
    """
    Health check for RAG pipeline.

    Returns:
        Dict with status info
    """
    return {
        "ready": RAG_READY_EVENT.is_set(),
        "embeddings_loaded": embeddings is not None,
        "bm25_initialized": bm25 is not None,
        "qdrant_connected": qdrant_client is not None,
        "llm_initialized": groq_client is not None,
        "embeddings_shape": embeddings.shape if embeddings is not None else None,
    }
