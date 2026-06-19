import asyncio
from difflib import SequenceMatcher
from functools import lru_cache
import pandas as pd
import os
import gc
import logging

from rag.rag_state import RAG_READY_EVENT, RAG_INIT_LOCK

logger = logging.getLogger(__name__)

collection_name = "mental_health_rag"
EMBEDDINGS_PATH = "./data/embeddings.npy"
DF_CACHE_PATH = "./data/qa_pairs.parquet"

# Populated once RAG finishes initializing. Declared here so other modules
# can `from rag.rag_pipeline import model, qdrant_client, ...` if needed,
# even before initialization completes (they'll just be None until then).
df = None
bm25 = None
model = None
qdrant_client = None
groq_client = None


# =========================================================
# CORPUS LOADING (no network call on a normal boot)
# =========================================================
def _load_corpus():
    """
    Loads the cleaned Q/A dataframe from a local parquet cache built once,
    offline, by scripts/build_embeddings.py. This avoids hitting the HF Hub
    and the heavier `datasets` library on every container start.

    Falls back to the original download path only if the cache is missing,
    so this never hard-breaks an existing setup.
    """
    import pandas as pd

    if os.path.exists(DF_CACHE_PATH):
        logger.info("Loading cached corpus from %s", DF_CACHE_PATH)
        return pd.read_parquet(DF_CACHE_PATH)

    logger.warning(
        "No cached corpus at %s — falling back to HF Hub download (slow path). "
        "Run scripts/build_embeddings.py to create the cache.",
        DF_CACHE_PATH,
    )
    from datasets import load_dataset

    ds = load_dataset("Amod/mental_health_counseling_conversations")
    corpus_df = ds["train"].to_pandas()
    corpus_df = (
        corpus_df[["Context", "Response"]]
        .drop_duplicates(subset=["Context", "Response"])
        .dropna()
        .reset_index(drop=True)
    )

    os.makedirs(os.path.dirname(DF_CACHE_PATH), exist_ok=True)
    corpus_df.to_parquet(DF_CACHE_PATH, index=False)

    del ds
    gc.collect()

    return corpus_df


# =========================================================
# STREAMED QDRANT INDEXING (bounded memory during cold reindex)
# =========================================================
def _stream_points(df_local, embeddings, batch_size):
    """Yields batches of PointStruct instead of building one giant list."""
    from qdrant_client.models import PointStruct

    batch = []
    for i, row in df_local.iterrows():
        batch.append(
            PointStruct(
                id=i,
                vector=embeddings[i].tolist(),
                payload={"context": row["Context"], "response": row["Response"]},
            )
        )
        if len(batch) >= batch_size:
            yield batch
            batch = []
    if batch:
        yield batch


# =========================================================
# INIT CONTROL (SAFE SINGLETON)
# =========================================================
def initialize_rag():
    global df, bm25, model, qdrant_client, groq_client

    # fast exit if already ready
    if RAG_READY_EVENT.is_set():
        logger.info("RAG already initialized. Skipping.")
        return

    with RAG_INIT_LOCK:
        # double-check inside lock
        if RAG_READY_EVENT.is_set():
            return

        try:
            logger.info("Initializing RAG pipeline...")

            # ---------------------------------------------------------
            # Heavy imports deferred to here ON PURPOSE.
            # If any of these are missing/incompatible (bad wheel, ABI
            # mismatch, etc.), ONLY this thread fails. The FastAPI
            # process, uvicorn, and /health stay up regardless.
            # ---------------------------------------------------------
            import numpy as np
            from sentence_transformers import SentenceTransformer
            from rank_bm25 import BM25Okapi
            from qdrant_client import QdrantClient
            from qdrant_client.models import VectorParams, Distance
            from openai import OpenAI

            # Avoid HF tokenizers spawning extra worker processes/threads,
            # which adds memory overhead for no benefit in a single request
            # at a time, low-resource container.
            os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

            # -------------------------
            # Corpus (cached parquet, not the full HF dataset)
            # -------------------------
            df = _load_corpus()
            logger.info("Loaded %d records", len(df))

            # -------------------------
            # Model (CPU explicit)
            # -------------------------
            model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu")

            # -------------------------
            # Embeddings (memory-mapped, not fully loaded into RAM)
            # -------------------------
            logger.info("Loading cached embeddings...")
            embeddings = np.load(EMBEDDINGS_PATH, mmap_mode="r")
            logger.info("Embeddings loaded from build cache")

            # -------------------------
            # BM25
            # -------------------------
            tokenized_corpus = [text.lower().split() for text in df["Context"]]
            bm25 = BM25Okapi(tokenized_corpus)
            del tokenized_corpus
            gc.collect()

            # -------------------------
            # Qdrant
            # -------------------------
            qdrant_client = QdrantClient(
                host=os.getenv("QDRANT_HOST", "localhost"),
                port=int(os.getenv("QDRANT_PORT", 6333)),
                timeout=120,
            )
            # qdrant_client = QdrantClient(
            #     host="localhost",
            #     port=6333,
            #     timeout=120,
            # )

            existing = [c.name for c in qdrant_client.get_collections().collections]

            if collection_name not in existing:
                qdrant_client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=embeddings.shape[1], distance=Distance.COSINE
                    ),
                )

            info = qdrant_client.get_collection(collection_name)

            if (info.points_count or 0) == 0:
                logger.info("Indexing vectors into Qdrant...")

                BATCH_SIZE = 500
                for batch in _stream_points(df, embeddings, BATCH_SIZE):
                    qdrant_client.upsert(
                        collection_name=collection_name, points=batch, wait=True
                    )

                gc.collect()

            # -------------------------
            # LLM client (just constructs a client, no network call)
            # -------------------------
            groq_client = OpenAI(
                base_url="https://lightning.ai/api/v1/",
                api_key=os.getenv("OPENAI_API_KEY"),
            )

            logger.info("RAG initialized successfully.")

            # ONLY ONE SOURCE OF TRUTH
            RAG_READY_EVENT.set()

        except Exception as e:
            # important: allow retry on failure
            RAG_READY_EVENT.clear()
            logger.exception("RAG initialization failed: %s", e)
            raise


# =========================================================
# SAFETY CHECK (NO RE-INIT HERE)
# =========================================================
def ensure_rag_initialized(timeout: int = 120):
    """
    Blocks until RAG is ready.
    Prevents race conditions instead of crashing requests.
    """

    if RAG_READY_EVENT.is_set():
        return

    # Wait for initialization to finish (if already running in background)
    ready = RAG_READY_EVENT.wait(timeout=timeout)

    if not ready:
        raise RuntimeError("RAG initialization timeout. Please try again later.")


# =========================================================
# SEMANTIC SEARCH
# =========================================================
def semantic_search(query, top_k=5):
    ensure_rag_initialized()

    query_vec = model.encode(query).tolist()

    results = qdrant_client.query_points(
        collection_name=collection_name,
        query=query_vec,
        limit=top_k,
        with_payload=True,
    )

    return results.points


# =========================================================
# BM25 SEARCH
# =========================================================
def bm25_search(query, top_k=5):
    ensure_rag_initialized()

    tokens = query.lower().split()
    scores = bm25.get_scores(tokens)

    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[
        :top_k
    ]

    return top_indices


# =========================================================
# HYBRID SEARCH (FINAL)
# =========================================================
def hybrid_search(query, top_k=10):
    sem_results = semantic_search(query, top_k=20)
    bm25_results = bm25_search(query, top_k=20)

    scores = {}

    # --- semantic scoring ---
    for rank, r in enumerate(sem_results):
        scores[r.id] = scores.get(r.id, 0) + (1 / (rank + 1))

    # --- BM25 scoring ---
    for rank, idx in enumerate(bm25_results):
        scores[idx] = scores.get(idx, 0) + (1 / (rank + 1))

    # --- fusion ranking ---
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    candidates = []

    for i, score in ranked[:top_k]:
        candidates.append(
            {
                "id": i,
                "context": df.iloc[i]["Context"],
                "response": df.iloc[i]["Response"],
                "hybrid_score": score,
            }
        )

    return candidates


# =========================================================
# RE-RANKER
# =========================================================


# def rerank_results(query, candidates, top_k=5):

#     pairs = [[query, candidate["context"]] for candidate in candidates]

#     rerank_scores = reranker.predict(pairs)

#     for candidate, score in zip(candidates, rerank_scores):
#         candidate["rerank_score"] = float(score)

#     reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)

#     return reranked[:top_k]


# =========================================================
# RETREIVAL PIPELINE
# =========================================================


def retrieve(query, top_k=5):

    # hybrid retrieval
    candidates = hybrid_search(query, top_k=20)

    # reranking
    # reranked = rerank_results(query, candidates, top_k=top_k)

    return candidates


# =========================================================
# TEST EMBEDDINGS
# =========================================================


def run_multilingual_test(queries, top_k=5):

    logs = []

    for q in queries:
        retrieved = retrieve(q, top_k=top_k)

        row = {"query": q}

        for i, item in enumerate(retrieved):
            row[f"top_{i + 1}_response"] = item["response"]
            row[f"top_{i + 1}_score"] = item["hybrid_score"]

        logs.append(row)

    return pd.DataFrame(logs)


# =========================================================
# BUILD PROMPT
# =========================================================


@lru_cache(maxsize=1)
def get_system_prompt():
    return """
You are Serenity, an empathetic AI companion designed to support emotional well-being through thoughtful, compassionate, and grounded conversations.

Knowledge Priority:

1. The user's message and conversation history.
2. Retrieved guidance from Serenity's knowledge base.
3. General mental health communication principles for empathy, validation, and supportive conversation.

When relevant guidance is available from the knowledge base, use it as the primary source for recommendations and support. Adapt its underlying principles to the user's situation rather than copying examples directly.

When retrieved information is unavailable, weakly related, or insufficient:

* Continue the conversation naturally based on the user's message and context.
* Provide emotional validation, empathic reflection, and supportive listening.
* Use general mental health communication knowledge to foster understanding and self-exploration.
* Avoid diagnoses, clinical claims, or treatment recommendations.
* Acknowledge uncertainty when appropriate rather than making assumptions.

Core Principles:

* Listen before advising.
* Seek understanding before offering solutions.
* Validate emotions without judgment.
* Encourage reflection without pressure.
* Respect the user's autonomy and experiences.
* Never assume facts that the user has not shared.

Safety:

* Never present yourself as a licensed mental health professional, therapist, psychologist, or medical provider.
* Never diagnose mental health conditions.
* Never invent facts, memories, symptoms, or personal details about the user.
* If the user expresses suicidal thoughts, self-harm, intent to harm others, or immediate danger, prioritize safety and encourage contacting emergency services, crisis resources, or trusted professional support.

Communication Style:

* Respond in the same language as the user.
* Be warm, calm, respectful, and non-judgmental.
* Sound conversational and human, not clinical or robotic.
* Keep responses concise unless the user asks for more detail.
* Prioritize genuine understanding over excessive advice.
* Create a sense of emotional safety, clarity, and serenity in every interaction.

"""


@lru_cache(maxsize=1)
def get_prompt_instructions():
    return """
Grounding Rules:
- Use retrieved counseling examples as supporting guidance, not as scripts to copy.
- Identify which retrieved examples are most relevant.
- Extract emotional insights and recommendations ONLY from the retrieved examples.
- Do not introduce new coping techniques, exercises, journaling suggestions, communication strategies, psychological explanations, or therapeutic recommendations that do not appear in the retrieved examples.
- Never assume facts that are not explicitly stated by the user.
- Retrieved examples are analogies, not facts about the current user.
- Never transfer specific circumstances, details, symptoms, relationships, events, or assumptions from a retrieved example to the user.
- Only use information explicitly provided by the user.

Abstraction Permission (IMPORTANT):
- You ARE allowed to extract general emotional or relational principles from retrieved examples.
- Examples:
    - trust
    - emotional openness
    - self-compassion
    - giving relationships time
    - emotional processing
    - seeking support
- These principles must NOT be turned into new step-by-step techniques.
- Use them only as gentle framing for emotional support.

Therapeutic Conversation Rules:
- Behave like a supportive therapist having a conversation, not like a self-help article.
- Do not immediately jump to advice or solutions.
- First understand the user's experience.
- Acknowledge emotions before offering guidance.
- Reflect back what the user seems to be feeling.
- Show curiosity about the user's experience.
- Prefer understanding over immediate solutions.
- Exploration is optional, not mandatory.
- Use gentle, open-ended questions when appropriate.
- If the user shares a painful experience, focus first on the emotional impact rather than fixing the problem.
- Advice should feel earned by the conversation, not automatically generated.

Question Balance Rules:
- Do NOT ask questions in every response.
- Only ask a question when it meaningfully advances understanding.
- Maximum ONE question per response.
- If the user has already expressed clear intent or emotion, prefer reflection instead of questions.
- If you already asked a question in the previous assistant message, do NOT ask another one unless necessary.
- It is acceptable to respond without any questions.

Natural Conversation Ending:
- Some responses should end without questions.
- It is okay to simply reflect and validate without prompting the user.
- Avoid turning every message into a continuation hook.

Low-Confidence Retrieval:
- If Retrieval Quality is LOW, or if the retrieved examples are weakly related to the user's situation:
    * Explicitly acknowledge that the available guidance may not closely match the user's situation.
    * Do NOT provide detailed or structured coping strategies.
    * Focus on understanding the user's experience.
    * You MAY offer:
        - emotional validation
        - empathic reflections
        - gentle exploratory questions
        - supportive observations based on retrieved principles
    * Invite the user to share additional context when appropriate.

High-Confidence Retrieval:
- If Retrieval Quality is HIGH:
    * Use retrieved examples as background knowledge, not responses to copy.
    * Adapt the emotional principle behind the example, not the exact wording.
    * Do NOT repeat specific details from retrieved examples unless the user also mentioned them.
    * Prioritize understanding the user's unique situation.
    * Recommendations may be included ONLY if they genuinely fit the user's situation and are supported by retrieved examples.
    * Validation and exploration should generally come before recommendations.

Empty Retrieval Handling:

If no retrieved counseling examples are available:

    * Continue the conversation naturally using the user's message and conversation history.

    * You may rely on general mental-health communication knowledge to:
        - validate emotions
        - reflect feelings
        - show empathy
        - encourage healthy self-exploration
        - support emotional expression

    * Do not:
        - invent clinical facts
        - diagnose mental-health conditions
        - claim certainty about causes or outcomes
        - provide medical or therapeutic instructions

    * Recommendations should remain:
        - gentle
        - optional
        - non-clinical
        - proportionate to the user's situation

    * If the user explicitly requests advice, provide reasonable supportive guidance while clearly avoiding diagnostic or professional treatment claims.

Response Style:
- Be empathetic, supportive, and non-judgmental.
- Respond in the same language as the user.
- Sound natural and conversational.
- Keep responses concise unless the user asks for more detail.
- Avoid bullet points unless they genuinely improve clarity.
- Avoid turning every response into advice.
- Avoid repeating recommendations across multiple turns.
- If the user's name is available, use it naturally and sparingly.
- Do not overuse the user's name.
"""


def build_prompt(
    query,
    retrieved_contexts,
    emotion,
    language,
    chat_history="",
    system_context="",
    retrieval_quality="HIGH",
):

    system_prompt = get_system_prompt()
    instructions = get_prompt_instructions()

    context_text = "\n\n".join(
        [
            f"""
Retrieved Example {i + 1}

Situation:
{item["context"]}

Suggested Guidance:
{item["response"]}
"""
            for i, item in enumerate(retrieved_contexts)
        ]
    )

    user_prompt = f"""
{system_context}

Language:
{language}

Detected Emotion (may be imperfect):
{emotion}

Retrieval Quality:
{retrieval_quality}

Retrieved Counseling Examples:
{context_text}

Instructions:
{instructions}

Conversation History:
{chat_history}

User Message:
{query}

Generate a supportive, empathetic, grounded, and contextually relevant response.
"""

    return system_prompt, user_prompt


# =========================================================
# RESPONSE
# =========================================================


def generate_response(
    query,
    retrieved_contexts,
    emotion,
    language,
    chat_history="",
    system_context="",
    retrieval_quality="HIGH",
):

    system_prompt, user_prompt = build_prompt(
        query=query,
        retrieved_contexts=retrieved_contexts,
        emotion=emotion,
        language=language,
        chat_history=chat_history,
        system_context=system_context,
        retrieval_quality=retrieval_quality,
    )

    completion = groq_client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=800,
    )

    return completion.choices[0].message.content


# =========================================================
# DEDUPLICATION
# =========================================================


def deduplicate_contexts(retrieved_contexts):
    seen = set()
    unique_contexts = []

    for item in retrieved_contexts:
        key = (item["context"].strip().lower(), item["response"].strip().lower())

        if key not in seen:
            seen.add(key)
            unique_contexts.append(item)

    return unique_contexts


def deduplicate_similar_contexts(contexts, threshold=0.90):
    unique = []

    for item in contexts:
        is_duplicate = False

        for existing in unique:
            similarity = SequenceMatcher(
                None, item["context"], existing["context"]
            ).ratio()

            if similarity >= threshold:
                is_duplicate = True
                break

        if not is_duplicate:
            unique.append(item)

    return unique


# =========================================================
# RETRIEVAL FILTERING
# =========================================================

MIN_RERANK_SCORE = 0.18


def filter_retrievals(retrieved_contexts):
    return [
        item for item in retrieved_contexts if item["hybrid_score"] >= MIN_RERANK_SCORE
    ]


# =========================================================
# RAG PIPELINE
# =========================================================


def rag_pipeline(
    query,
    language=None,
    emotion=None,
    chat_history="",
    system_context="",
    return_metadata=False,
):

    # -----------------------------
    # retrieval
    # -----------------------------
    retrieved_contexts = retrieve(query, top_k=10)

    # -----------------------------
    # rerank filtering
    # -----------------------------
    retrieved_contexts = filter_retrievals(retrieved_contexts)

    # -----------------------------
    # exact deduplication
    # -----------------------------
    retrieved_contexts = deduplicate_contexts(retrieved_contexts)

    # -----------------------------
    # near-duplicate removal
    # -----------------------------
    retrieved_contexts = deduplicate_similar_contexts(
        retrieved_contexts, threshold=0.90
    )

    # -----------------------------
    # keep top examples
    # -----------------------------
    retrieved_contexts = retrieved_contexts[:5]

    # -----------------------------
    # retrieval confidence
    # -----------------------------
    if retrieved_contexts:
        top_score = retrieved_contexts[0]["rerank_score"]
    else:
        top_score = 0

    retrieval_quality = "HIGH" if top_score >= 0.40 else "LOW"

    # -----------------------------
    # generation
    # -----------------------------
    response = generate_response(
        query=query,
        retrieved_contexts=retrieved_contexts,
        emotion=emotion,
        language=language,
        chat_history=chat_history,
        system_context=system_context,
        retrieval_quality=retrieval_quality,
    )

    # -----------------------------
    # debug metadata
    # -----------------------------
    if return_metadata:
        return {
            "query": query,
            "language": language,
            "emotion": emotion,
            "retrieved_contexts": retrieved_contexts,
            "retrieval_quality": retrieval_quality,
            "response": response,
        }

    return response


# =========================================================
# RAG TESTS
# =========================================================


def run_rag_tests(queries):

    logs = []

    for q in queries:
        result = rag_pipeline(q, return_metadata=True)

        logs.append(
            {
                "query": result["query"],
                "language": result["language"],
                "emotion": result["emotion"],
                "response": result["response"],
                "top_context_1": (
                    result["retrieved_contexts"][0]["context"]
                    if len(result["retrieved_contexts"]) > 0
                    else ""
                ),
                "top_score_1": (
                    result["retrieved_contexts"][0]["hybrid_score"]
                    if len(result["retrieved_contexts"]) > 0
                    else ""
                ),
            }
        )

    return pd.DataFrame(logs)


# =========================================================
# ASYNC FUNCTIONS
# =========================================================


async def semantic_search_async(query, top_k=5):
    return await asyncio.to_thread(semantic_search, query, top_k)


async def bm25_search_async(query, top_k=5):
    return await asyncio.to_thread(bm25_search, query, top_k)


async def hybrid_search_async(query, top_k=5):
    sem_results, bm25_results = await asyncio.gather(
        asyncio.to_thread(semantic_search, query, 8),
        asyncio.to_thread(bm25_search, query, 8),
    )

    scores = {}

    # --- semantic scoring ---
    for rank, r in enumerate(sem_results):
        scores[r.id] = scores.get(r.id, 0) + (1 / (rank + 1))

    # --- BM25 scoring ---
    for rank, idx in enumerate(bm25_results):
        scores[idx] = scores.get(idx, 0) + (1 / (rank + 1))

    # --- fusion ranking ---
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    candidates = []

    for i, score in ranked[:top_k]:
        candidates.append(
            {
                "id": i,
                "context": df.iloc[i]["Context"],
                "response": df.iloc[i]["Response"],
                "hybrid_score": score,
            }
        )

    return candidates


# async def rerank_results_async(query, candidates, top_k=5):
#     pairs = [[query, candidate["context"]] for candidate in candidates]

#     rerank_scores = await asyncio.to_thread(reranker.predict, pairs)

#     for candidate, score in zip(candidates, rerank_scores):
#         candidate["rerank_score"] = float(score)

#     reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)

#     return reranked[:top_k]


async def retrieve_async(query, top_k=5):
    candidates = await hybrid_search_async(query, top_k=top_k)

    return candidates


async def generate_response_async(
    query,
    retrieved_contexts,
    emotion,
    language,
    chat_history="",
    system_context="",
    retrieval_quality="HIGH",
):
    system_prompt, user_prompt = build_prompt(
        query=query,
        retrieved_contexts=retrieved_contexts,
        emotion=emotion,
        language=language,
        chat_history=chat_history,
        system_context=system_context,
        retrieval_quality=retrieval_quality,
    )

    completion = await asyncio.to_thread(
        groq_client.chat.completions.create,
        model="openai/gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
        max_tokens=800,
    )

    return completion.choices[0].message.content


async def rag_pipeline_async(
    query,
    language=None,
    emotion=None,
    chat_history="",
    system_context="",
    return_metadata=False,
):

    # -----------------------------
    # retrieval
    # -----------------------------
    retrieved_contexts = await retrieve_async(query, top_k=5)

    # -----------------------------
    # rerank filtering
    # -----------------------------
    retrieved_contexts = filter_retrievals(retrieved_contexts)

    # -----------------------------
    # exact deduplication
    # -----------------------------
    retrieved_contexts = deduplicate_contexts(retrieved_contexts)

    # -----------------------------
    # near-duplicate removal
    # -----------------------------
    retrieved_contexts = deduplicate_similar_contexts(
        retrieved_contexts, threshold=0.90
    )

    # -----------------------------
    # keep top examples
    # -----------------------------
    retrieved_contexts = retrieved_contexts[:5]

    # -----------------------------
    # retrieval confidence
    # -----------------------------
    if retrieved_contexts:
        top_score = retrieved_contexts[0]["hybrid_score"]
    else:
        top_score = 0

    retrieval_quality = "HIGH" if top_score >= 0.30 else "LOW"

    # -----------------------------
    # generation
    # -----------------------------
    response = await generate_response_async(
        query=query,
        retrieved_contexts=retrieved_contexts,
        emotion=emotion,
        language=language,
        chat_history=chat_history,
        system_context=system_context,
        retrieval_quality=retrieval_quality,
    )

    # -----------------------------
    # debug metadata
    # -----------------------------
    if return_metadata:
        return {
            "query": query,
            "language": language,
            "emotion": emotion,
            "retrieved_contexts": retrieved_contexts,
            "retrieval_quality": retrieval_quality,
            "response": response,
        }

    return response


# =========================================================
# 🧪 TEST QUERY
# =========================================================
if __name__ == "__main__":
    initialize_rag()

    test_queries = [
        "Hello how are?",
        # 🇬🇧 English (mental health + safety)
        "I feel like giving up on everything and I don't see a point to being here anymore.",
        "My workload is causing me to miss deadlines and I'm losing sleep over it. How do I start managing this?",
        # 🇸🇦 Arabic
        "أشعر أنني أريد الاستسلام ولا أرى أي معنى للحياة الآن",
        # 🇪🇸 Spanish
        "Siento que quiero rendirme y no veo sentido a seguir viviendo",
        "Tengo mucho estrés con el trabajo y no duermo bien, ¿cómo empiezo a organizarme?",
    ]

    df_results = run_rag_tests(test_queries)

    os.makedirs("./mental_health_emb_tests", exist_ok=True)

    df_results.to_csv("./mental_health_emb_tests/full_rag_results.csv", index=False)

    print(df_results)
