# =========================================================
# 📦 IMPORTS
# =========================================================
from datasets import load_dataset, Dataset
import pandas as pd

from sentence_transformers import SentenceTransformer, CrossEncoder
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from rank_bm25 import BM25Okapi
from groq import Groq
from dotenv import load_dotenv
import os
import numpy as np

load_dotenv()

groq_client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
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
rag_dataset.save_to_disk("mental_health_rag_dataset")


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
            row[f"top_{i+1}_score"] = item["rerank_score"]

        logs.append(row)

    return pd.DataFrame(logs)

# =========================================================
# BUILD PROMPT
# =========================================================

def build_prompt(
    query,
    retrieved_contexts,
    emotion,
    language,
    chat_history=""
):
    
    system_prompt = """
You are an expert Mental Health Counselor specialized in providing emotional support, psychological guidance, and evidence-based coping strategies.

Your primary goal is to help the user improve their emotional and psychological well-being in a safe, supportive, and non-judgmental environment.

You must:
- Listen carefully to the user's concerns and emotional state.
- Provide realistic, practical, and compassionate guidance.
- Offer evidence-based coping techniques and exercises when appropriate, especially techniques commonly supported in psychological literature (such as grounding exercises, breathing exercises, journaling, CBT-style reframing, mindfulness, behavioral activation, or stress-management techniques).
- Make the user feel emotionally safe, understood, and supported without judging them or minimizing their feelings.
- Adapt your tone, empathy level, and response style according to the detected emotional state of the user.
- Respond in the SAME language used by the user.
- Use the detected emotion and retrieved counseling examples to generate a supportive and context-aware response.
- Avoid giving harmful, dangerous, or medically unsafe advice.
- If the user's message suggests severe emotional distress, self-harm, or suicidal ideation, prioritize emotional safety, encourage seeking support from trusted people or mental health professionals, and maintain a calm and supportive tone.
"""

    context_text = "\n\n".join([
        f"""
Context {i+1}:
User Problem:
{item['context']}

Therapist Response:
{item['response']}
"""
        for i, item in enumerate(retrieved_contexts)
    ])

    user_prompt = f"""
Detected Language:
{language}

Detected Emotion:
{emotion}

Relevant Counseling Context:
{context_text}

Conversation History:
{chat_history}

User Message:
{query}

Generate a supportive, emotionally aware, and contextually relevant response.
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
    chat_history=""
):

    system_prompt, user_prompt = build_prompt(
        query=query,
        retrieved_contexts=retrieved_contexts,
        emotion=emotion,
        language=language,
        chat_history=chat_history
    )

    completion = groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
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
        temperature=0.5,
        max_tokens=700
    )

    return completion.choices[0].message.content

# =========================================================
# RAG PIPELINE
# =========================================================

def rag_pipeline(query, language=None, emotion=None, chat_history="", return_metadata=False):

    # -----------------------------
    # retrieval + reranking
    # -----------------------------
    retrieved_contexts = retrieve(query, top_k=5)

    # -----------------------------
    # generation
    # -----------------------------
    response = generate_response(
        query=query,
        retrieved_contexts=retrieved_contexts,
        emotion=emotion,
        language=language,
        chat_history=chat_history
    )

    # -----------------------------
    # optional debug metadata
    # -----------------------------
    if return_metadata:

        return {
            "query": query,
            "language": language,
            "emotion": emotion,
            "retrieved_contexts": retrieved_contexts,
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