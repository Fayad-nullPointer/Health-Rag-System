# =========================================================
# 📦 IMPORTS
# =========================================================
import asyncio
from datasets import load_dataset, Dataset
import pandas as pd

from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from difflib import SequenceMatcher

from rank_bm25 import BM25Okapi
from groq import Groq
from dotenv import load_dotenv
import os
import numpy as np
from openai import OpenAI

from functools import lru_cache

load_dotenv("config/.env")

# groq_client = Groq(
#     api_key=os.getenv("GROQ_API_KEY")
# )

groq_client = OpenAI(
    base_url="https://lightning.ai/api/v1/",
    api_key=os.getenv("OPENAI_API_KEY"),
)

EMBEDDINGS_PATH = "./cache/embeddings.npy"

# =========================================================
# LOAD DATASET
# =========================================================
ds = load_dataset("Amod/mental_health_counseling_conversations")
df = ds["train"].to_pandas()

df = df.drop_duplicates(subset=["Context", "Response"]).dropna().reset_index(drop=True)


# =========================================================
# BUILD RAG DATASET (OPTIONAL EXPORT)
# =========================================================
documents = []

for idx, row in df.iterrows():
    documents.append({
        "id": idx,
        "context": row["Context"],
        "response": row["Response"],
        "document": f"""
User Problem:
{row['Context']}

Therapist Response:
{row['Response']}
""".strip()
    })

documents_df = pd.DataFrame(documents)
rag_dataset = Dataset.from_pandas(documents_df)

# Optional save
# rag_dataset.save_to_disk("mental_health_rag_dataset")


# =========================================================
# EMBEDDING MODEL
# =========================================================
model = SentenceTransformer("BAAI/bge-m3")
reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")

# =========================================================
# EMBEDDINGS (CONTEXT ONLY)
# =========================================================
df["embedding_text"] = df["Context"]


if os.path.exists(EMBEDDINGS_PATH):

    print("Loading cached embeddings...")

    embeddings = np.load(EMBEDDINGS_PATH)

else:

    print("Generating embeddings...")

    embeddings = model.encode(
        df["embedding_text"].tolist(),
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True
    )

    os.makedirs("./cache", exist_ok=True)

    np.save(EMBEDDINGS_PATH, embeddings)

    print("Embeddings cached successfully.")


# =========================================================
# BM25 INDEX
# =========================================================
tokenized_corpus = [text.lower().split() for text in df["Context"]]
bm25 = BM25Okapi(tokenized_corpus)


# =========================================================
# QDRANT SETUP
# =========================================================
qdrant_client = QdrantClient(
    path="./cache/qdrant"
)

collection_name = "mental_health_rag"

existing_collections = [
    c.name
    for c in qdrant_client.get_collections().collections
]

if collection_name not in existing_collections:

    print("Creating Qdrant collection...")

    qdrant_client.recreate_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=embeddings.shape[1],
            distance=Distance.COSINE
        )
    )

    points = []

    for i, row in df.iterrows():

        points.append(
            PointStruct(
                id=i,
                vector=embeddings[i].tolist(),
                payload={
                    "context": row["Context"],
                    "response": row["Response"]
                }
            )
        )

    qdrant_client.upsert(
        collection_name=collection_name,
        points=points
    )

    print("Qdrant indexing completed.")

else:

    print("Using existing Qdrant collection.")


# =========================================================
# INDEX DATA INTO QDRANT
# =========================================================
points = []

for i, row in df.iterrows():
    points.append(
        PointStruct(
            id=i,
            vector=embeddings[i].tolist(),
            payload={
                "context": row["Context"],
                "response": row["Response"]
            }
        )
    )

qdrant_client .upsert(collection_name=collection_name, points=points)


# =========================================================
# SEMANTIC SEARCH
# =========================================================
def semantic_search(query, top_k=5):
    query_vec = model.encode(query).tolist()

    results = qdrant_client .query_points(
        collection_name=collection_name,
        query=query_vec,
        limit=top_k,
        with_payload=True
    )

    return results.points


# =========================================================
# BM25 SEARCH
# =========================================================
def bm25_search(query, top_k=5):
    tokens = query.lower().split()
    scores = bm25.get_scores(tokens)

    top_indices = sorted(
        range(len(scores)),
        key=lambda i: scores[i],
        reverse=True
    )[:top_k]

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
        candidates.append({
            "id": i,
            "context": df.iloc[i]["Context"],
            "response": df.iloc[i]["Response"],
            "hybrid_score": score
        })

    return candidates

# =========================================================
# RE-RANKER
# =========================================================

def rerank_results(query, candidates, top_k=5):

    pairs = [
        [query, candidate["context"]]
        for candidate in candidates
    ]

    rerank_scores = reranker.predict(pairs)

    for candidate, score in zip(candidates, rerank_scores):
        candidate["rerank_score"] = float(score)

    reranked = sorted(
        candidates,
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    return reranked[:top_k]

# =========================================================
# RETREIVAL PIPELINE
# =========================================================

def retrieve(query, top_k=5):

    # hybrid retrieval
    candidates = hybrid_search(query, top_k=20)

    # reranking
    reranked = rerank_results(query, candidates, top_k=top_k)

    return reranked

# =========================================================
# TEST EMBEDDINGS
# =========================================================

def run_multilingual_test(queries, top_k=5):

    logs = []

    for q in queries:

        retrieved = retrieve(q, top_k=top_k)

        row = {
            "query": q
        }

        for i, item in enumerate(retrieved):

            row[f"top_{i+1}_response"] = item["response"]
            row[f"top_{i+1}_score"] = item["hybrid_score"]

        logs.append(row)

    return pd.DataFrame(logs)

# =========================================================
# BUILD PROMPT
# =========================================================

@lru_cache(maxsize=1)
def get_system_prompt():
    return """
You are MindCare AI, a compassionate mental health support assistant.

Use retrieved counseling information as your primary source of guidance.

Guidelines:
- Respond in the same language as the user.
- Be empathetic, supportive, and non-judgmental.
- Use ONLY recommendations that appear in the retrieved examples.
If no suitable recommendation exists:
    - acknowledge the limitation
    - provide emotional validation only
    - ask for more context
- Do not invent diagnoses, psychological explanations, or recommendations unsupported by the retrieved information.
- If the retrieved information is incomplete, weakly related, or does not fully match the user's situation, explicitly acknowledge this limitation before providing guidance.
- In such cases, avoid making assumptions and invite the user to share more details if they feel comfortable.
- If the user expresses self-harm, suicidal thoughts, or immediate danger, prioritize safety and encourage professional or emergency support.
- Keep responses concise and helpful.
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

Empty Retrieval Handling (IMPORTANT):

If no retrieved counseling examples are available:

    * First respond naturally to the user's message and current conversation context.

    * Use a therapist-like conversational style:
        - listen first
        - acknowledge emotions
        - reflect what the user is expressing
        - show curiosity
        - invite exploration

    * Prioritize:
        - emotional validation
        - empathic reflection
        - thoughtful follow-up questions

    * Do NOT automatically provide:
        - breathing exercises
        - journaling suggestions
        - coping techniques
        - action plans
        - motivational advice

    * Only offer coping suggestions when:
        - the user explicitly asks for advice or help
        - OR the user is expressing significant distress, anxiety, sadness, overwhelm, or emotional suffering

    * When offering suggestions:
        - keep them brief
        - present them as options, not instructions
        - avoid sounding prescriptive

    * Avoid:
        - diagnosis
        - assumptions
        - excessive reassurance
        - generic motivational statements
        - repetitive recommendations

    * If the user's emotional state is unclear:
        - ask a thoughtful follow-up question instead of giving advice.

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
    retrieval_quality="HIGH"
):

    system_prompt = get_system_prompt()
    instructions = get_prompt_instructions()

    context_text = "\n\n".join([
    f"""
Retrieved Example {i+1}

Situation:
{item['context']}

Suggested Guidance:
{item['response']}
"""
    for i, item in enumerate(retrieved_contexts)
])

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
    retrieval_quality="HIGH"
):

    system_prompt, user_prompt = build_prompt(
        query=query,
        retrieved_contexts=retrieved_contexts,
        emotion=emotion,
        language=language,
        chat_history=chat_history,
        system_context=system_context,
        retrieval_quality=retrieval_quality
    )

    completion = groq_client.chat.completions.create(
        model="openai/gpt-4o",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.3,
        max_tokens=800
    )

    return completion.choices[0].message.content

# =========================================================
# DEDUPLICATION
# =========================================================

def deduplicate_contexts(retrieved_contexts):
    seen = set()
    unique_contexts = []

    for item in retrieved_contexts:
        key = (
            item["context"].strip().lower(),
            item["response"].strip().lower()
        )

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
                None,
                item["context"],
                existing["context"]
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
        item
        for item in retrieved_contexts
        if item["rerank_score"] >= MIN_RERANK_SCORE
    ]

# =========================================================
# RAG PIPELINE
# =========================================================

def rag_pipeline(query, language=None, emotion=None, chat_history="", system_context="", return_metadata=False):

    # -----------------------------
    # retrieval
    # -----------------------------
    retrieved_contexts = retrieve(query, top_k=10)

    # -----------------------------
    # rerank filtering
    # -----------------------------
    retrieved_contexts = filter_retrievals(
        retrieved_contexts
    )

    # -----------------------------
    # exact deduplication
    # -----------------------------
    retrieved_contexts = deduplicate_contexts(
        retrieved_contexts
    )

    # -----------------------------
    # near-duplicate removal
    # -----------------------------
    retrieved_contexts = deduplicate_similar_contexts(
        retrieved_contexts,
        threshold=0.90
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

    retrieval_quality = (
        "HIGH"
        if top_score >= 0.30
        else "LOW"
    )

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
        retrieval_quality=retrieval_quality
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
            "response": response
        }

    return response

# =========================================================
# RAG TESTS
# =========================================================

def run_rag_tests(queries):

    logs = []

    for q in queries:

        result = rag_pipeline(
            q,
            return_metadata=True
        )

        logs.append({
            "query": result["query"],
            "language": result["language"],
            "emotion": result["emotion"],
            "response": result["response"],

            "top_context_1":
                result["retrieved_contexts"][0]["context"]
                if len(result["retrieved_contexts"]) > 0 else "",

            "top_score_1":
                result["retrieved_contexts"][0]["rerank_score"]
                if len(result["retrieved_contexts"]) > 0 else "",
        })

    return pd.DataFrame(logs)


# =========================================================
# ASYNC FUNCTIONS
# =========================================================

async def semantic_search_async(query, top_k=5):
    return await asyncio.to_thread(semantic_search, query, top_k)


async def bm25_search_async(query, top_k=5):
    return await asyncio.to_thread(bm25_search, query, top_k)


async def hybrid_search_async(query, top_k=10):
    sem_results, bm25_results = await asyncio.gather(
        asyncio.to_thread(semantic_search, query, 15),
        asyncio.to_thread(bm25_search, query, 15)
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
        candidates.append({
            "id": i,
            "context": df.iloc[i]["Context"],
            "response": df.iloc[i]["Response"],
            "hybrid_score": score
        })

    return candidates


async def rerank_results_async(query, candidates, top_k=5):
    pairs = [
        [query, candidate["context"]]
        for candidate in candidates
    ]

    rerank_scores = await asyncio.to_thread(reranker.predict, pairs)

    for candidate, score in zip(candidates, rerank_scores):
        candidate["rerank_score"] = float(score)

    reranked = sorted(
        candidates,
        key=lambda x: x["rerank_score"],
        reverse=True
    )

    return reranked[:top_k]


async def retrieve_async(query, top_k=5):
    # hybrid retrieval
    candidates = await hybrid_search_async(query, top_k=10)

    # reranking
    reranked = await rerank_results_async(query, candidates, top_k=top_k)

    return reranked


async def generate_response_async(
    query,
    retrieved_contexts,
    emotion,
    language,
    chat_history="",
    system_context="",
    retrieval_quality="HIGH"
):
    system_prompt, user_prompt = build_prompt(
        query=query,
        retrieved_contexts=retrieved_contexts,
        emotion=emotion,
        language=language,
        chat_history=chat_history,
        system_context=system_context,
        retrieval_quality=retrieval_quality
    )

    completion = await asyncio.to_thread(
        groq_client.chat.completions.create,
        model="openai/gpt-4o",
        messages=[
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": user_prompt
            }
        ],
        temperature=0.3,
        max_tokens=800
    )

    return completion.choices[0].message.content


async def rag_pipeline_async(query, language=None, emotion=None, chat_history="", system_context="", return_metadata=False):

    # -----------------------------
    # retrieval
    # -----------------------------
    retrieved_contexts = await retrieve_async(query, top_k=8)

    # -----------------------------
    # rerank filtering
    # -----------------------------
    retrieved_contexts = filter_retrievals(
        retrieved_contexts
    )

    # -----------------------------
    # exact deduplication
    # -----------------------------
    retrieved_contexts = deduplicate_contexts(
        retrieved_contexts
    )

    # -----------------------------
    # near-duplicate removal
    # -----------------------------
    retrieved_contexts = deduplicate_similar_contexts(
        retrieved_contexts,
        threshold=0.90
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

    retrieval_quality = (
        "HIGH"
        if top_score >= 0.30
        else "LOW"
    )

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
        retrieval_quality=retrieval_quality
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
            "response": response
        }

    return response


# =========================================================
# 🧪 TEST QUERY
# =========================================================
if __name__ == "__main__":
    test_queries = [
        "Hello how are?",
        # 🇬🇧 English (mental health + safety)
        "I feel like giving up on everything and I don't see a point to being here anymore.",
        "My workload is causing me to miss deadlines and I'm losing sleep over it. How do I start managing this?",
       
        # 🇸🇦 Arabic
        "أشعر أنني أريد الاستسلام ولا أرى أي معنى للحياة الآن",

        # 🇪🇸 Spanish
        "Siento que quiero rendirme y no veo sentido a seguir viviendo",
        "Tengo mucho estrés con el trabajo y no duermo bien, ¿cómo empiezo a organizarme?"
    ]

    df_results = run_rag_tests(test_queries)

    os.makedirs(
        "./mental_health_emb_tests",
        exist_ok=True
    )

    df_results.to_csv(
        "./mental_health_emb_tests/full_rag_results.csv",
        index=False
    )

    print(df_results)